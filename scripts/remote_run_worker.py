"""The container side of scripts.remote_run: standard library only, sent as the program's
text with `main(JOB)` appended, never imported from the repository.

Frames on stdout, one JSON object a line:
    {"o": b64} / {"e": b64}  the command's stdout / stderr, as it comes
    {"alive": 1}             every HEARTBEAT seconds
    {"need": "src"}          the source volume is empty: upload, then run again
    {"f": b64}               a chunk of a tar.gz of the files the run created or changed
    {"exit": code}           the last frame of a run
    {"ok": 1}                the last frame of an upload

stdin stays open for the whole run: its EOF means the laptop's end is gone, and the command
is stopped then, so a killed laptop process leaves nothing running here.
"""

import base64
import fcntl
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import uuid

HEARTBEAT = 5
CHUNK = 1 << 20
_lock = threading.Lock()


def send(**frame) -> None:
    line = (json.dumps(frame) + "\n").encode()
    with _lock:
        try:
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
        except (OSError, ValueError):
            pass


def upload(job: dict) -> int:
    """Unpack the tar.gz on the rest of stdin as the source tree. Another upload of the same
    content may finish first; either copy will do."""
    tmp = os.path.join(job["src"], f".tree-{uuid.uuid4().hex}")
    os.makedirs(tmp)
    with tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz") as tar:
        tar.extractall(tmp, filter="data")
    try:
        os.rename(tmp, os.path.join(job["src"], "tree"))
    except OSError:
        shutil.rmtree(tmp, ignore_errors=True)
    send(ok=1)
    return 0


def stats(root: str) -> dict:
    found = {}
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            if os.path.isfile(p) and not os.path.islink(p):
                st = os.stat(p)
                found[os.path.relpath(p, root)] = (st.st_size, st.st_mtime_ns)
    return found


def install(job: dict) -> str | None:
    """The site directory for the job's requirements.txt, installed once per content (the
    pip volume is keyed by it). None if pip failed; its output went to stderr frames."""
    site = os.path.join(job["pip"], "site")
    with open(os.path.join(job["pip"], ".lock"), "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        if os.path.isdir(site):
            return site
        tmp = f"{site}-{uuid.uuid4().hex}"
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as req:
            req.write(job["req"])
        p = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "--root-user-action=ignore",
                            "--break-system-packages", "--target", tmp, "-r", req.name],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if p.stdout:
            send(e=base64.b64encode(p.stdout).decode())
        if p.returncode != 0:
            shutil.rmtree(tmp, ignore_errors=True)
            return None
        os.rename(tmp, site)
        return site


def stop(p: subprocess.Popen) -> None:
    for sig, wait in ((signal.SIGTERM, 5), (signal.SIGKILL, None)):
        try:
            os.killpg(p.pid, sig)
        except ProcessLookupError:
            return
        try:
            p.wait(wait)
            return
        except subprocess.TimeoutExpired:
            pass


def run(job: dict) -> int:
    tree = os.path.join(job["src"], "tree")
    if not os.path.isdir(tree):
        send(need="src")
        return 3
    env = dict(os.environ, REMOTE_RUN_JOBS=str(job["jobs"]), PYTHONUNBUFFERED="1")
    if job.get("req"):
        site = install(job)
        if site is None:
            send(e=base64.b64encode(b"remote_run: pip install -r requirements.txt failed\n").decode())
            send(exit=1)
            return 1
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [site, env.get("PYTHONPATH")]))
    work = job["work"]
    shutil.copytree(tree, work, symlinks=True, dirs_exist_ok=True)
    before = stats(work)
    try:
        p = subprocess.Popen(job["cmd"], cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
    except OSError as e:
        send(e=base64.b64encode(f"remote_run: {e}\n".encode()).decode())
        send(exit=127)
        return 127

    def pump(stream, key):
        while chunk := os.read(stream.fileno(), 65536):
            send(**{key: base64.b64encode(chunk).decode()})

    gone = threading.Event()

    def orphaned():
        # The raw fd, not sys.stdin: a thread blocked inside a buffered read makes the
        # interpreter abort when it closes sys.stdin at exit.
        while os.read(0, 65536):
            pass
        gone.set()
        stop(p)

    done = threading.Event()

    def beat():
        while not done.wait(HEARTBEAT):
            send(alive=1)

    pumps = [threading.Thread(target=pump, args=(p.stdout, "o")), threading.Thread(target=pump, args=(p.stderr, "e"))]
    beating = threading.Thread(target=beat)
    for t in pumps + [threading.Thread(target=orphaned, daemon=True), beating]:
        t.start()
    code = p.wait()
    code = 128 - code if code < 0 else code  # killed by a signal, as a shell reports it
    if gone.is_set():
        done.set()
        return 143
    for t in pumps:
        t.join()
    after = stats(work)
    changed = sorted(f for f, s in after.items() if before.get(f) != s)
    if changed:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for f in changed:
                tar.add(os.path.join(work, f), arcname=f)
        data = buf.getvalue()
        for i in range(0, len(data), CHUNK):
            send(f=base64.b64encode(data[i:i + CHUNK]).decode())
    done.set()
    beating.join()
    send(exit=code)
    return code


def main(job: dict) -> None:
    code = upload(job) if job["mode"] == "upload" else run(job)
    # No interpreter shutdown: the stdin watcher may still be blocked in a read, and every
    # frame is already flushed.
    os._exit(code & 0xFF)
