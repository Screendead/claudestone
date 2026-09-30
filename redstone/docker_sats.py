"""Satellites in Docker on the desktop, reached over SSH.

Each dsatN is a `redstone-satellite` container (docker/satellite/) whose RCON is
published on the desktop's loopback and forwarded to the same port here through the
shared SSH ControlMaster. To the harness it is a satellite like any other: its rig.lock
and harness.log live in server/satellites/dsatN/ on this machine, and the data pack Rig
writes there is pushed into the container with push_datapack. Importing this module
adds dsat1..dsat6 to servers.SERVERS.

A forward accepts TCP whether or not the container is up, so readiness is always an RCON
login and a command, never a port check.

The desktop's SSH login (user@host) comes from REDSTONE_DOCKER_HOST, else the one line
in server/docker_host (gitignored). With neither, the backend is unavailable: reachable()
is False and every ssh or docker call raises DesktopError.

    python -m redstone.docker_sats {start,stop,status,reap} [dsatN...]
"""

import errno
import fcntl
import io
import os
import re
import socket
import subprocess
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from . import servers
from .rcon import PROPERTIES, Rcon
from .servers import ROOT, Server

HOST_FILE = ROOT / "docker_host"


def configured_host(path: Path = HOST_FILE) -> str | None:
    host = os.environ.get("REDSTONE_DOCKER_HOST", "").strip()
    if not host:
        try:
            host = path.read_text().strip()
        except FileNotFoundError:
            pass
    return host or None


HOST = configured_host()
CONTEXT = "desktop"
IMAGE = "redstone-satellite:26.3"
LEVEL = "testworld"
REMOTE_PACKS = f"/srv/{LEVEL}/datapacks"
REMOTE_CRASHES = "/srv/crash-reports"
IDLE_MINUTES = 8
REAPER_GIVE_UP = 24 * 3600  # seconds of an unreachable desktop before the reaper exits
REAPER_LOCK = ROOT / "satellites" / "dsat_reaper.lock"
# stderr of an ssh or docker call that failed because the connection to the desktop did,
# rather than because of the command.
TRANSPORT_ERRORS = ("control socket", "mux_client", "muxclient", "read from master", "broken pipe",
                    "connection reset", "connection refused", "connection closed", "timed out",
                    "error during connect", "host is down", "no route to host", "ssh: ")

run = subprocess.run  # replaced by a fake in the offline tests


class DesktopError(RuntimeError):
    pass


def _password() -> str:
    return re.search(r"^rcon\.password=(.*)$", PROPERTIES.read_text(), re.M).group(1)


def _once(argv: list[str], timeout: float, stdin: bytes | None = None, merge: bool = False,
          env: dict | None = None):
    if HOST is None and argv[0] in ("ssh", "docker"):
        raise DesktopError("no Docker host: set REDSTONE_DOCKER_HOST or write user@host to server/docker_host")
    return run(argv, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT if merge else subprocess.PIPE,
               timeout=timeout, env=env)


def _transport_failed(p) -> bool:
    if p.returncode == 0:
        return False
    err = (p.stderr or p.stdout or b"").decode(errors="replace").lower()
    return (p.args[0] == "ssh" and p.returncode == 255) or any(m in err for m in TRANSPORT_ERRORS)


def master_pid() -> int | None:
    """The pid of the running ControlMaster for HOST, or None."""
    try:
        p = _once(["ssh", "-O", "check", HOST], 5)
    except subprocess.TimeoutExpired:
        return None
    m = re.search(rb"pid=(\d+)", (p.stderr or b"") + (p.stdout or b""))
    return int(m.group(1)) if p.returncode == 0 and m else None


def _probe() -> bool:
    """A no-op ssh command: through the master when there is one, else a fresh connection
    (which leaves a master behind)."""
    try:
        # The desktop's sshd runs cmd.exe, which has no `true`; `exit` is a builtin there and in sh.
        return _once(["ssh", "-o", "ConnectTimeout=5", HOST, "exit"], 8).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def call(argv: list[str], timeout: float = 30, stdin: bytes | None = None, merge: bool = False,
         env: dict | None = None, check: bool = True, retry: bool = True):
    """Run an ssh or docker command. After a hang or a connection failure the connection is
    probed: a healthy master means the command itself failed (Docker Desktop stopped, a
    slow daemon), so a transport error is retried once and a hang is not. A master that no
    longer answers (the desktop rebooted or slept) is closed, and the command retried once
    if a fresh connection works. Closing it drops every forward on it and every connection
    through them, in every process, so nothing else closes it. `retry=False` is for
    commands that must not run twice."""
    def attempt():
        try:
            return _once(argv, timeout, stdin, merge, env)
        except subprocess.TimeoutExpired:
            return None

    p = attempt()
    if retry and (p is None or _transport_failed(p)):
        had_master = master_pid() is not None
        if _probe():
            if p is not None:
                p = attempt()
        elif had_master:
            try:
                _once(["ssh", "-O", "exit", HOST], 5)
            except subprocess.TimeoutExpired:
                pass
            if _probe():
                p = attempt()
    if p is None:
        raise DesktopError(f"{' '.join(argv[:4])}...: timed out")
    if check and p.returncode != 0:
        raise DesktopError(f"{' '.join(argv[:4])}...: {(p.stderr or p.stdout or b'').decode(errors='replace').strip()}")
    return p


def docker(*args: str, **kw):
    return call(["docker", "--context", CONTEXT, *args], **kw)


def reachable(timeout: float = 5) -> bool:
    """Whether the desktop's Docker answers."""
    try:
        return docker("version", "--format", "{{.Server.Version}}", timeout=timeout).returncode == 0
    except DesktopError:
        return False


def running(timeout: float = 30) -> set[str]:
    """Names of the dsat containers running on the desktop."""
    out = docker("ps", "--filter", "name=^dsat", "--format", "{{.Names}}", timeout=timeout).stdout.decode()
    return set(out.split())


def running_satellites(timeout: float = 5) -> list["DockerSatellite"]:
    """The dsats whose containers are running, busy or not, in order. Makes sure a reaper
    is watching them: containers can outlive the process that started them."""
    names = running(timeout)
    if names:
        _spawn_reaper()
    return [s for s in DOCKER_SATELLITES if s.name in names]


def rcon_ready(port: int, timeout: float = 3) -> bool:
    try:
        r = Rcon(port=port, timeout=timeout)
        try:
            return re.search(r"\d", r.cmd("time query gametime")) is not None
        finally:
            r.close()
    except Exception:
        return False


def _listeners(port: int) -> set[int] | None:
    """Pids listening on 127.0.0.1:port, or None when it is free."""
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return None
    except OSError as e:
        if e.errno != errno.EADDRINUSE:
            raise
    finally:
        s.close()
    p = _once(["lsof", "-nP", "-t", f"-iTCP@127.0.0.1:{port}", "-sTCP:LISTEN"], 5)
    return {int(x) for x in p.stdout.split()}


@dataclass(frozen=True)
class DockerSatellite(Server):
    image: str = IMAGE

    def level_name(self) -> str:
        return LEVEL

    def _forward_spec(self) -> str:
        return f"{self.rcon_port}:127.0.0.1:{self.rcon_port}"

    def forward(self) -> None:
        """Forward rcon_port to the container through the master (idempotent). -O forward
        onto a port something else holds returns 0 and forwards nothing, so check first."""
        pid = master_pid()
        if pid is None:
            if not _probe():
                raise DesktopError(f"ssh {HOST} failed")
            pid = master_pid()
            if pid is None:
                raise DesktopError(f"no ssh ControlMaster for {HOST}; is ControlMaster set in ~/.ssh/config?")
        holders = _listeners(self.rcon_port)
        if holders and pid not in holders:
            raise DesktopError(f"{self.name}: local port {self.rcon_port} is held by pid "
                               f"{','.join(map(str, sorted(holders)))}, not the ssh master {pid}")
        call(["ssh", "-O", "forward", "-L", self._forward_spec(), HOST], timeout=10)

    def unforward(self) -> None:
        call(["ssh", "-O", "cancel", "-L", self._forward_spec(), HOST], timeout=10, check=False)

    def is_up(self) -> bool:
        """RCON answers through the forward. A server busy on its main thread (a reload, a
        big probe) can miss the timeout and read as down. The forward is left in place
        either way: another process may be about to open a connection through it."""
        try:
            self.forward()
        except DesktopError:
            return False
        return rcon_ready(self.rcon_port)

    def start(self, timeout: float = 60) -> str:
        self.dir.mkdir(parents=True, exist_ok=True)
        # Serialises check-remove-run between starters; the second one then finds the
        # container running and waits for it below.
        with open(self.dir / "start.lock", "a") as starting:
            fcntl.flock(starting, fcntl.LOCK_EX)
            if self.is_up():
                self.lock.touch()
                return f"{self.name}: already up"
            began = time.time()
            self.lock.touch()  # the reaper reads a missing or old lock as idle
            # Running but not answering may just be busy (a big reload, warp stepping) under
            # someone else's test: wait for it, never replace it.
            if self.name not in running():
                self._remove()  # a crashed or stopped container of the same name
                self._run()
        _spawn_reaper()  # also stops one that never answers, once its lock is stale
        self.forward()
        deadline = began + timeout
        while not rcon_ready(self.rcon_port, timeout=2):
            if time.time() > deadline:
                raise TimeoutError(f"{self.name} did not answer RCON in {timeout:.0f}s; "
                                   f"`python -m redstone.docker_sats stop {self.name}` saves its log to {self.log}")
            time.sleep(0.3)
        self.lock.touch()  # idle time counts from here
        return f"{self.name}: started in {time.time() - began:.1f}s"

    def _run(self) -> None:
        # Bare `-e NAME` takes the value from this process's environment, which keeps the
        # password off the ssh command line (docker inspect on the desktop still shows it).
        # Not retried: a run that timed out may have started the container anyway.
        try:
            docker("run", "-d", "--name", self.name, "-e", "RCON_PASSWORD", "-e", f"MEMORY={self.memory}",
                   "-p", f"127.0.0.1:{self.rcon_port}:25575",
                   self.image, env={**os.environ, "RCON_PASSWORD": _password()}, retry=False, timeout=60)
        except DesktopError:
            if self.name not in running():
                raise

    @property
    def log(self) -> Path:
        return self.dir / "harness.log"

    def save_logs(self) -> bool:
        """The container's output into harness.log, and its crash reports (a watchdog
        crash's thread dump goes there, not to stdout) into crash-reports/."""
        p = docker("logs", self.name, merge=True, check=False)
        if p.returncode != 0:
            return False
        self.log.write_bytes(p.stdout)
        docker("cp", f"{self.name}:{REMOTE_CRASHES}", str(self.dir), check=False, retry=False)
        return True

    def _remove(self) -> bool:
        """Save the container's logs and remove it. Whether there was one."""
        if not self.save_logs():
            return False
        docker("rm", "-f", self.name, check=False)
        return True

    def stop(self) -> str:
        was = self.name in running()
        docker("stop", "-t", "30", self.name, check=False, timeout=60)
        existed = self._remove()
        self.unforward()
        return f"{self.name}: {'stopped' if was else 'removed' if existed else 'down'}"

    def status(self) -> str:
        where = f"rcon {self.rcon_port}  {self.dir}"
        try:
            if self.name not in running():
                return f"{self.name}: down  {where}"
            _spawn_reaper()
            self.forward()
        except DesktopError as e:
            return f"{self.name}: unknown ({e})  {where}"
        return f"{self.name}: {'up' if rcon_ready(self.rcon_port) else 'running, not answering'}  {where}"

    def push_datapack(self, pack_dir: Path, reload: bool = True) -> None:
        """Replace the container's copy of a data pack with pack_dir, then optionally reload."""
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
            tar.add(pack_dir, arcname=pack_dir.name)
        dest = f"{REMOTE_PACKS}/{pack_dir.name}"
        docker("exec", "-i", self.name, "sh", "-c", f"rm -rf '{dest}' && tar -x -C '{REMOTE_PACKS}'",
               stdin=buf.getvalue(), timeout=60)
        if reload:
            r = Rcon(port=self.rcon_port)
            try:
                r.cmd("reload")
            finally:
                r.close()


DOCKER_SATELLITES = [DockerSatellite(f"dsat{i}", ROOT / "satellites" / f"dsat{i}", 0, 25675 + i, "1G")
                     for i in range(1, 7)]
BY_NAME = {s.name: s for s in DOCKER_SATELLITES}


def idle(sat: DockerSatellite, minutes: float) -> bool:
    try:
        return time.time() - sat.lock.stat().st_mtime > minutes * 60
    except FileNotFoundError:
        return True


def stop_idle(minutes: float = IDLE_MINUTES) -> list[str]:
    """Stop each running dsat whose rig.lock is free and untouched for `minutes`. The lock
    is held while it stops, so no test can take the satellite meanwhile. A held lock is
    touched: conftest writes it only when a test takes it, so a long test would otherwise
    read as idle the moment it ends."""
    done = []
    names = running()
    for name in sorted(names):
        sat = BY_NAME.get(name)
        if sat is None:
            continue
        sat.dir.mkdir(parents=True, exist_ok=True)
        missing = not sat.lock.exists()  # opening creates it, with a fresh mtime
        with open(sat.lock, "a") as lock:  # "a": opening must not count as use
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.utime(sat.lock)
                continue
            if missing or idle(sat, minutes):
                done.append(sat.stop())
    if len(done) < len(names):
        _spawn_reaper()
    return done


def reap(minutes: float = IDLE_MINUTES, every: float = 60) -> None:
    """Stop idle dsats until none is running. One reaper at a time, by REAPER_LOCK. While
    the desktop is unreachable it backs off and keeps trying (a sleeping desktop keeps its
    containers), up to REAPER_GIVE_UP."""
    REAPER_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(REAPER_LOCK, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        delay, lost = every, None
        while True:
            time.sleep(delay)
            try:
                stop_idle(minutes)
                if not running():
                    return
                delay, lost = every, None
            except DesktopError:
                lost = lost or time.time()
                if time.time() - lost > REAPER_GIVE_UP:
                    return
                delay = min(delay * 2, 600)


def _spawn_reaper() -> None:
    REAPER_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(REAPER_LOCK, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return  # one is running
    subprocess.Popen([sys.executable, "-m", "redstone.docker_sats", "reap"], cwd=ROOT.parent,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


ACTIONS = ("start", "stop", "status")


def main(argv: list[str]) -> int:
    action = argv[0] if argv else "status"
    if action == "reap":
        reap()
        return 0
    unknown = [n for n in argv[1:] if n not in BY_NAME]
    if action not in ACTIONS or unknown:
        print(f"usage: python -m redstone.docker_sats {{{','.join(ACTIONS)},reap}} [dsat1..dsat6]", file=sys.stderr)
        return 2
    sats = [BY_NAME[n] for n in argv[1:]] or DOCKER_SATELLITES
    if not reachable():
        print(f"desktop {HOST} unreachable" if HOST else "no Docker host: set REDSTONE_DOCKER_HOST or server/docker_host")
        return 1
    with ThreadPoolExecutor(len(sats)) as pool:
        for line in pool.map(lambda s: getattr(s, action)(), sats):
            print(line)
    return 0


servers.SERVERS.update(BY_NAME)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
