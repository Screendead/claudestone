"""Runs a spec test inside a Docker satellite's container, next to its server.

Over the SSH forward every RCON command costs a round trip to the desktop, and a test sends
hundreds of them, most waiting on the reply before the next. So for a dsat the laptop sends
the whole test instead: one `ssh <host> docker exec -i dsatN python3 -c <BOOT>`, whose first
stdin line is a small program carrying this package (redstone/*.py, gzipped) and the pickled
job. In the container `serve` builds a Rig on the server's own RCON and runs spec._run as a local test
would; the laptop reads its stdout as it goes:

    {"display": command}          a status sign update, replayed on main's RCON
    {"watch": [fn, args, kwargs]} a watch.emit / watch.set_status, replayed here
    {"alive": 1}                  every HEARTBEAT seconds, so a lost desktop is noticed
    {"done": base64 pickle}       result or exception, the loaded build, the trace text

and does everything else (locks, plot records, events, showroom, mirroring) itself. The
trace is written here from the container's text, so it is byte for byte the local one.

A container of an image without python3 (built before this) runs the test the old way,
command by command through the forward.
"""

import base64
import contextlib
import fcntl
import io
import json
import os
import pickle
import queue
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import traceback
from functools import cache
from pathlib import Path

from . import spec as spec_module, watch
from .build import Build
from .harness import Rig, checked
from .rcon import Rcon, port_turn
from .servers import Server

PACKAGE = Path(__file__).resolve().parent
ENABLED = os.environ.get("REDSTONE_REMOTE", "1").lower() not in ("0", "off", "false", "no")
HEARTBEAT = 5
# Seconds without a line before the desktop is probed. A heartbeat thread sends one every
# HEARTBEAT seconds whatever the test is doing, so silence means a dead connection or a
# starved container; if the desktop still answers, the wait goes on up to STALL seconds.
SILENCE = 45
STALL = 300
CONTAINER_PROPERTIES = Path("/srv/server.properties")
CONTAINER_LOCK = Path("/tmp/redstone-harness.lock")
RCON_WAIT = 60  # a container just started by another process may not listen yet

popen = subprocess.Popen  # replaced by a fake in the offline tests

# The desktop's shell is cmd.exe, so the command line has no spaces or double quotes, and
# the program comes as one base64 line: reading it needs no EOF on stdin.
BOOT = "exec(__import__('base64').b64decode(__import__('sys').stdin.readline()))"
PROGRAM = """\
import base64, io, pickle, shutil, sys, tarfile, tempfile
d = tempfile.mkdtemp(prefix="redstone-")
try:
    tarfile.open(fileobj=io.BytesIO(base64.b64decode({code!r})), mode="r:gz").extractall(d, filter="data")
    sys.path.insert(0, d)
    from redstone.remote import serve
    serve(pickle.loads(base64.b64decode({job!r})))
finally:
    shutil.rmtree(d, ignore_errors=True)
"""


# ---- in the container -----------------------------------------------------------------------

class Display:
    """Stands in for main's RCON: the sign commands go back to the laptop."""

    def __init__(self, send):
        self.send = send

    def cmd(self, command: str) -> str:
        self.send({"display": command})
        return ""


def _portable(e: BaseException) -> BaseException:
    """e if it survives pickling, else a RuntimeError with its type and message."""
    try:
        return pickle.loads(pickle.dumps(e))
    except Exception:
        return RuntimeError(f"{type(e).__name__}: {e}")


def _rcon(factory, wait: float = RCON_WAIT):
    deadline = time.time() + wait
    while True:
        try:
            return factory(port=25575)
        except ConnectionRefusedError:
            if time.time() > deadline:
                raise
            time.sleep(0.2)


def serve(job: dict, out=None, rcon_factory=None, server_dir: Path = Path("/srv")) -> None:
    """Run one test on this machine's server and report on `out` (the real stdout)."""
    from . import rcon as rcon_module

    out = out or sys.stdout
    sys.stdout = sys.stderr  # only protocol lines on out
    lock = threading.Lock()

    def send(obj) -> None:
        try:
            with lock:
                out.write(json.dumps(obj) + "\n")
                out.flush()
        except (OSError, ValueError):
            pass  # the laptop is gone; finish the test so the server is released

    done = threading.Event()

    def beat():
        while not done.wait(HEARTBEAT):
            send({"alive": 1})

    beating = threading.Thread(target=beat)
    beating.start()
    watch.emit = lambda kind, **fields: send({"watch": ["emit", [kind], fields]})
    watch.set_status = lambda plot, text: send({"watch": ["set_status", [plot, text], {}]})
    rcon_module.PROPERTIES = server_dir / CONTAINER_PROPERTIES.name
    spec, test = job["spec"], job["test"]
    report: dict = {"result": None, "error": None, "release_error": None, "loaded": Build(), "trace": None}
    try:
        with tempfile.TemporaryDirectory(prefix="redstone-traces-") as traces, open(CONTAINER_LOCK, "a") as held:
            spec_module.TRACE_DIR = Path(traces)
            # A test whose laptop vanished may still be running here.
            fcntl.flock(held, fcntl.LOCK_EX)
            rig = None
            try:
                server = Server(job["server"], server_dir, 25565, 25575, "1G")
                rig = Rig(_rcon(rcon_factory or Rcon), tuple(job["origin"]), tuple(job["size"]), job["plot"],
                          server=server, display=Display(send))
                rig.heading, rig.owner = job["heading"], job.get("owner")
                report["result"] = spec_module._run(rig, spec, test, job["trace"])
            except BaseException as e:
                report["error"], report["traceback"] = _portable(e), traceback.format_exc()
            finally:
                if rig is not None:
                    report["loaded"] = rig.loaded
                    try:
                        rig.release()
                    except BaseException as e:
                        report["release_error"] = _portable(e)
            written = Path(traces) / spec.name / f"{test['name']}.json"
            if written.exists():
                report["trace"] = written.read_text()
    finally:
        done.set()
        beating.join()
    send({"done": base64.b64encode(pickle.dumps(report)).decode()})


# ---- on the laptop --------------------------------------------------------------------------

@cache
def code() -> str:
    """This package's source and data (door_probe reads blocks.json on import), gzipped and
    base64-encoded, taken once per process so every test of a session runs the same code."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in sorted([*PACKAGE.glob("*.py"), *PACKAGE.glob("*.json")]):
            tar.add(f, arcname=f"redstone/{f.name}")
    return base64.b64encode(buf.getvalue()).decode()


def program(job: dict) -> bytes:
    """The stdin line for BOOT."""
    text = PROGRAM.format(code=code(), job=base64.b64encode(pickle.dumps(job)).decode())
    return base64.b64encode(text.encode()) + b"\n"


# dsats whose container has no python3 (an image from before remote runs), per process.
NO_PYTHON: set[str] = set()


class RemoteRig:
    """What the rig fixture yields for a Docker satellite: the test itself runs in the
    container (run_spec); this side keeps the plot, the display and, afterwards, the build
    that was loaded."""

    def __init__(self, server, plot, display, connect):
        self.server, self.plot, self.display = server, plot.name, display
        self.origin, self.size = plot.origin, plot.size
        self.heading: list[dict] = []
        self.owner: str | None = None
        self.loaded = Build()
        self._connect = connect  # the server's RCON through the forward, for the fallback
        self._local: Rig | None = None
        self._release_error: BaseException | None = None

    def job(self, spec, test: dict, trace: bool) -> dict:
        return {"spec": spec, "test": test, "trace": trace, "plot": self.plot, "origin": self.origin,
                "size": self.size, "server": self.server.name, "heading": self.heading,
                "owner": self.owner}

    def run_spec(self, spec, test: dict, trace: bool) -> dict:
        if self.server.name in NO_PYTHON:
            return self._run_here(spec, test, trace)
        port = getattr(self.server, "rcon_port", None)
        with port_turn(port) if port else contextlib.nullcontext():
            report = self._exchange(program(self.job(spec, test, trace)))
        if report is None:
            NO_PYTHON.add(self.server.name)
            return self._run_here(spec, test, trace)
        self.loaded = report["loaded"]
        self._release_error = report["release_error"]
        if report["trace"] is not None:
            out = spec_module.TRACE_DIR / spec.name / f"{test['name']}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report["trace"])
        error = report["error"] or report.get("display_error")
        if error is not None:
            if not isinstance(error, AssertionError) and report.get("traceback"):
                error.add_note(f"in {self.server.name}'s container:\n{report['traceback']}")
            raise error
        return report["result"]

    def _run_here(self, spec, test: dict, trace: bool) -> dict:
        self._local = Rig(self._connect(), self.origin, self.size, self.plot, server=self.server, display=self.display)
        self._local.heading, self._local.owner = self.heading, self.owner
        try:
            return spec_module._run(self._local, spec, test, trace)
        finally:
            self.loaded = self._local.loaded

    def release(self) -> None:
        if self._local is not None:
            self._local.release()
        elif self._release_error is not None:
            raise self._release_error

    def _exchange(self, prog: bytes) -> dict | None:
        """Run prog in the container, replaying its lines as they come. The report, or None
        when the container has no python3."""
        from . import docker_sats

        if docker_sats.HOST is None:
            raise docker_sats.DesktopError("no Docker host: set REDSTONE_DOCKER_HOST or write user@host to server/docker_host")
        name = self.server.name
        # Straight through ssh, not `docker -H ssh://`, which costs a second connection
        # setup (~0.35 s). The desktop's shell is cmd.exe: no quoting on this line.
        try:
            p = popen(["ssh", "-o", "ConnectTimeout=10", docker_sats.HOST, "docker", "exec", "-i", name, "python3", "-c", BOOT],
                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as e:
            raise docker_sats.DesktopError(f"ssh: {e}") from e
        lines: queue.Queue = queue.Queue()
        err: list[bytes] = []

        def feed():
            try:
                p.stdin.write(prog)
                p.stdin.close()
            except OSError:
                pass

        def read_out():
            for line in p.stdout:
                lines.put(line)
            lines.put(None)

        def read_err():
            err.append(p.stderr.read())

        threads = [threading.Thread(target=f, daemon=True) for f in (feed, read_out, read_err)]
        for t in threads:
            t.start()
        report, heard, display_error, quiet = None, False, None, 0.0
        try:
            while True:
                try:
                    line = lines.get(timeout=SILENCE)
                except queue.Empty:
                    quiet += SILENCE
                    if quiet < STALL and docker_sats._probe():
                        continue
                    p.kill()
                    self._lost(f"no word from {name} for {quiet:.0f} s"
                               + ("" if heard else "; the program never started there"))
                quiet = 0.0
                if line is None:
                    break
                line = line.strip()
                if not line.startswith(b"{"):
                    continue
                heard = True
                msg = json.loads(line)
                if "display" in msg:
                    try:
                        checked(self.display, msg["display"])
                    except Exception as e:
                        display_error = display_error or e
                elif "watch" in msg:
                    fn, args, kwargs = msg["watch"]
                    if fn in ("emit", "set_status"):
                        getattr(watch, fn)(*args, **kwargs)
                elif "done" in msg:
                    report = pickle.loads(base64.b64decode(msg["done"]))
            code_ = p.wait()
        finally:
            if p.poll() is None:
                p.kill()
            for t in threads:
                t.join(5)
        stderr = b"".join(err).decode(errors="replace").strip()
        if report is not None:
            if stderr:
                print(stderr, file=sys.stderr)
            if display_error is not None:
                report["display_error"] = display_error
            return report
        if not heard and (code_ in (126, 127) or "executable file not found" in stderr):
            return None
        if code_ == 255:
            self._lost(f"ssh exited 255: {stderr[-500:]}")
        raise docker_sats.DesktopError(f"{name}: the test in the container ended without a result "
                                       f"(exit {code_}): {stderr[-2000:]}")

    def _lost(self, why: str):
        """The connection to the desktop failed or stalled mid-test: mark it down if it no
        longer answers, so later tests go elsewhere, and fail this one."""
        from . import docker_sats

        if not docker_sats._probe():
            docker_sats._mark_down()
        raise docker_sats.DesktopError(f"{self.server.name}: lost the desktop during the test ({why}); "
                                       f"the test may still finish there, but its result is lost")
