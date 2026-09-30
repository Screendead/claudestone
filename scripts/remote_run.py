"""Run a CPU-heavy offline job (a search, a SAT solve; no Minecraft) on the desktop instead of
this laptop:

    python -m scripts.remote_run <dir> [--jobs N] [--memory SIZE] -- <cmd> [args]...

<dir> is copied to the desktop (a Docker volume per content hash, so a repeat run of the
same files uploads nothing) and <cmd> runs in it, in a throwaway container of the satellite
image (python3, python-sat), with the cwd a private copy of <dir>. A requirements.txt in
<dir> is pip-installed once per content and put on PYTHONPATH. stdout and stderr stream back
live; when the command ends, the files it created or changed are copied back into <dir>, and
its exit code is this one's. `$REMOTE_RUN_JOBS` there is N.

The container may use N CPUs and N GB (--memory to change). All runs together hold at most
$REDSTONE_SEARCH_CPUS (default 8) of the desktop's 14 Docker CPUs, so the dsats keep
headroom; a run waits here for its CPUs. Ctrl-C or a killed process stops the container
(its stdin closes). An unreachable desktop is an error: nothing runs locally.
"""

import argparse
import base64
import fcntl
import hashlib
import io
import json
import os
import queue
import signal
import subprocess
import sys
import tarfile
import threading
import time
import uuid
from pathlib import Path

from redstone import docker_sats
from redstone.docker_sats import IMAGE
from redstone.servers import ROOT

WORKER = Path(__file__).with_name("remote_run_worker.py")
# The desktop's shell is cmd.exe: nothing on the command line may need quoting.
BOOT = "exec(__import__('base64').b64decode(__import__('sys').stdin.buffer.readline()))"
SLOTS = ROOT / "remote_run"
TOTAL_CPUS = int(os.environ.get("REDSTONE_SEARCH_CPUS", "8"))
SKIP = {"__pycache__", ".git", ".venv", "venv", "node_modules"}
SILENCE = 30  # the worker sends a heartbeat every 5 s
# A few seconds for a small dir. Now and then the container never sees stdin that was
# written and closed at once, and waits for its first line for ever.
UPLOAD_TIMEOUT = 90
LABEL = "redstone.remote_run=1"
CONTAINER = {"src": "/src", "work": "/work", "pip": "/pip"}  # paths inside the container

popen = subprocess.Popen  # replaced by a fake in the offline tests


class Unreachable(RuntimeError):
    pass


def files(root: Path) -> list[Path]:
    out = []
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP)
        out += [Path(d, n) for n in sorted(names) if not Path(d, n).is_symlink()]
    return out


def snapshot(root: Path) -> tuple[str, bytes]:
    """The content hash of root's files and a tar.gz of them."""
    h, buf = hashlib.sha256(), io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in files(root):
            rel = f.relative_to(root).as_posix()
            data = f.read_bytes()
            h.update(f"{rel}\0{len(data)}\0{os.access(f, os.X_OK)}\0".encode())
            h.update(data)
            tar.add(f, arcname=rel)
    return h.hexdigest(), buf.getvalue()


def volume_names(root: Path, content: str) -> tuple[str, str]:
    """(prefix shared by every snapshot of this dir, this snapshot's volume)."""
    prefix = f"rr-src-{hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:12]}-"
    return prefix, prefix + content[:20]


def program(job: dict) -> bytes:
    text = WORKER.read_text() + f"\nmain(__import__('json').loads({json.dumps(job)!r}))\n"
    return base64.b64encode(text.encode()) + b"\n"


def take_cpus(n: int, total: int = TOTAL_CPUS, slots: Path = SLOTS, say=print) -> list:
    """Hold n of the `total` CPU slot locks, waiting until they are free."""
    if n > total:
        raise SystemExit(f"remote_run: --jobs {n} is more than the {total} desktop CPUs searches may use "
                         f"($REDSTONE_SEARCH_CPUS)")
    slots.mkdir(parents=True, exist_ok=True)
    told = False
    while True:
        held = []
        for i in range(total):
            f = open(slots / f"cpu{i}.lock", "a")
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held.append(f)
            except BlockingIOError:
                f.close()
            if len(held) == n:
                return held
        for f in held:
            f.close()
        if not told:
            say(f"remote_run: waiting for {n} of the desktop's {total} search CPUs", file=sys.stderr)
            told = True
        time.sleep(1)


def docker_run_argv(host: str, name: str, volumes: list[str], cpus: int | None = None,
                    memory: str | None = None) -> list[str]:
    limits = ([f"--cpus={cpus}"] if cpus else []) + ([f"--memory={memory}"] if memory else [])
    mounts = [a for v in volumes for a in ("-v", v)]
    return ["ssh", "-o", "ConnectTimeout=10", host, "docker", "run", "-i", "--rm", "--name", name, "--label", LABEL, *limits, *mounts,
            IMAGE, "python3", "-c", BOOT]


def ssh(host: str, *args: str, timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "-o", "ConnectTimeout=10", host, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)


class Session:
    """One `docker run` on the desktop, its frames read as they come."""

    def __init__(self, host: str, argv: list[str], line: bytes, rest: bytes | None = None):
        self.host = host
        self.name = argv[argv.index("--name") + 1]
        try:
            self.p = popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as e:
            raise Unreachable(f"ssh: {e}") from e
        self.frames: queue.Queue = queue.Queue()
        self.err: list[bytes] = []
        self.threads = [threading.Thread(target=self._read, daemon=True),
                        threading.Thread(target=lambda: self.err.append(self.p.stderr.read()), daemon=True)]
        for t in self.threads:
            t.start()
        try:
            self.p.stdin.write(line)
            if rest is not None:
                self.p.stdin.write(rest)
                self.p.stdin.close()
            else:
                self.p.stdin.flush()  # left open: its EOF stops the container
        except OSError:
            pass

    def _read(self):
        for line in self.p.stdout:
            line = line.strip()
            if line.startswith(b"{"):
                self.frames.put(json.loads(line))
        self.frames.put(None)

    def __iter__(self):
        quiet = 0
        while True:
            try:
                frame = self.frames.get(timeout=SILENCE)
            except queue.Empty:
                quiet += SILENCE
                if docker_sats._probe():
                    continue
                self.kill()
                raise Unreachable(f"the desktop stopped answering during the run ({quiet} s without a word)")
            if frame is None:
                return
            yield frame

    def close(self) -> int:
        try:
            self.p.stdin.close()
        except OSError:
            pass
        code = self.p.wait()
        self._join()
        return code

    def _join(self) -> None:
        """The readers end at the pipes' EOF; none may be left inside a read at exit."""
        for t in self.threads:
            t.join(5)

    def failure(self) -> str:
        return b"".join(self.err).decode(errors="replace").strip()[-2000:]

    def kill(self) -> None:
        """Stop the ssh client, whose closed stdin stops the container, and remove the
        container too in case the desktop missed that."""
        if self.p.poll() is None:
            self.p.kill()
        try:
            ssh(self.host, "docker", "rm", "-f", self.name, timeout=15)
        except Exception:
            pass
        self.p.wait()
        self._join()


def upload(host: str, root: Path, content: str, data: bytes) -> None:
    prefix, volume = volume_names(root, content)
    for attempt in range(3):
        s = Session(host, docker_run_argv(host, f"rr-up-{uuid.uuid4().hex[:12]}", [f"{volume}:{CONTAINER['src']}"]),
                    program({"mode": "upload", "src": CONTAINER["src"]}), data)
        timer = threading.Timer(UPLOAD_TIMEOUT, s.kill)
        timer.start()
        try:
            ok = any("ok" in f for f in s)
        finally:
            timer.cancel()
        code = s.close()
        if ok:
            break
    else:
        raise Unreachable(f"upload of {root} failed (exit {code}): {s.failure()}")
    # Earlier snapshots of the same dir; a volume a run still uses refuses removal.
    listed = ssh(host, "docker", "volume", "ls", "-q", "--filter", f"name={prefix}")
    stale = [v for v in listed.stdout.decode().split() if v.startswith(prefix) and v != volume]
    if stale:
        ssh(host, "docker", "volume", "rm", *stale)


def execute(host: str, root: Path, cmd: list[str], jobs: int, memory: str, out=None, err=None) -> int:
    out = out or sys.stdout.buffer
    err = err or sys.stderr.buffer
    content, data = snapshot(root)
    _, volume = volume_names(root, content)
    volumes = [f"{volume}:{CONTAINER['src']}"]
    job = {"mode": "run", **CONTAINER, "cmd": cmd, "jobs": jobs}
    req = root / "requirements.txt"
    if req.exists():
        job["req"] = req.read_text()
        volumes.append(f"rr-pip-{hashlib.sha256(job['req'].encode()).hexdigest()[:20]}:{CONTAINER['pip']}")
    for attempt in range(2):
        s = Session(host, docker_run_argv(host, f"rr-{uuid.uuid4().hex[:12]}", volumes, jobs, memory),
                    program(job))
        try:
            code, need, tarball = None, False, bytearray()
            for frame in s:
                if "o" in frame:
                    out.write(base64.b64decode(frame["o"]))
                    out.flush()
                elif "e" in frame:
                    err.write(base64.b64decode(frame["e"]))
                    err.flush()
                elif "f" in frame:
                    tarball += base64.b64decode(frame["f"])
                elif "need" in frame:
                    need = True
                elif "exit" in frame:
                    code = frame["exit"]
                    break
            ended = s.close()
        except BaseException:
            s.kill()
            raise
        if need and attempt == 0:
            upload(host, root, content, data)
            continue
        if code is None:
            what = "the desktop is unreachable" if ended == 255 else f"the run ended without an exit code (exit {ended})"
            raise Unreachable(f"{what}: {s.failure()}")
        if tarball:
            with tarfile.open(fileobj=io.BytesIO(bytes(tarball)), mode="r:gz") as tar:
                tar.extractall(root, filter="data")
        return code
    raise Unreachable("the source upload did not take")


def _interrupt(*_):
    """A plain kill (SIGTERM) unwinds like Ctrl-C, so the container is removed on the way out."""
    raise KeyboardInterrupt


def main(argv: list[str]) -> int:
    if "--" not in argv:
        print(__doc__, file=sys.stderr)
        return 2
    cut = argv.index("--")
    ap = argparse.ArgumentParser(prog="remote_run")
    ap.add_argument("dir", type=Path)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--memory", help="docker --memory for the container (default: N GB for --jobs N)")
    a = ap.parse_args(argv[:cut])
    cmd = argv[cut + 1:]
    if not cmd or not a.dir.is_dir():
        print(__doc__, file=sys.stderr)
        return 2
    host = docker_sats.HOST
    if host is None:
        print("remote_run: no desktop configured: set REDSTONE_DOCKER_HOST or write user@host to server/docker_host",
              file=sys.stderr)
        return 255
    held = take_cpus(a.jobs)
    signal.signal(signal.SIGTERM, _interrupt)
    try:
        return execute(host, a.dir.resolve(), cmd, a.jobs, a.memory or f"{a.jobs}g")
    except Unreachable as e:
        print(f"remote_run: {e}", file=sys.stderr)
        return 255
    except KeyboardInterrupt:
        print("remote_run: interrupted; the container is stopped", file=sys.stderr)
        return 130
    finally:
        for f in held:
            f.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
