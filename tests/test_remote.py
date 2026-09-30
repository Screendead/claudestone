"""redstone.remote offline: serve() runs against the fake Rig of test_spec_offline, and the
laptop side reads serve's real output through a fake ssh process."""

import base64
import io
import subprocess
import sys
import threading

import pytest

from redstone import docker_sats as ds, remote, spec as spec_module, watch
from redstone import rcon as rcon_module
from redstone.plots import PLOTS
from test_spec_offline import OUT, FakeRig, make_spec, square

PLOT = PLOTS["not"]


class Rig(FakeRig):
    def __init__(self, script=lambda tick: {}):
        super().__init__(script)
        self.plot, self.released = PLOT.name, 0

    def release(self):
        self.released += 1


def made(rig):
    """A stand-in for Rig's constructor that hands back `rig`, wired as Rig would be."""
    def make(rcon, origin, size, plot, server, display):
        rig.origin, rig.server, rig.display = origin, server, display
        return rig
    return make


class Display:
    def __init__(self):
        self.sent = []

    def cmd(self, command):
        self.sent.append(command)
        return ""


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """serve() rewires module globals as the container's process may; undo that here."""
    for mod, name in ((watch, "emit"), (watch, "set_status"), (rcon_module, "PROPERTIES"), (sys, "stdout")):
        monkeypatch.setattr(mod, name, getattr(mod, name))
    monkeypatch.setattr(remote, "CONTAINER_LOCK", tmp_path / "harness.lock")
    monkeypatch.setattr(remote, "NO_PYTHON", set())
    monkeypatch.setattr(ds, "HOST", "user@desktop.invalid")
    events = []
    monkeypatch.setattr(watch, "emit", lambda kind, **f: events.append((kind, f)))
    monkeypatch.setattr(watch, "set_status", lambda plot, text: events.append(("status", plot, text)))
    return events


class Sat:
    name = "dsat1"


def serve_lines(monkeypatch, s, script, owner=None) -> tuple[list[bytes], Rig]:
    """serve()'s stdout for spec s run on a fake Rig."""
    rig = Rig(script)
    monkeypatch.setattr(remote, "Rig", made(rig))
    out = io.StringIO()
    rr = remote.RemoteRig(Sat, PLOT, Display(), None)
    rr.heading, rr.owner = [{"text": "fake\n"}], owner
    with monkeypatch.context() as m:  # serve's own rewiring stays inside
        for mod, name in ((watch, "emit"), (watch, "set_status"), (sys, "stdout"), (spec_module, "TRACE_DIR")):
            m.setattr(mod, name, getattr(mod, name))
        remote.serve(rr.job(s, s.tests[0], False), out=out, rcon_factory=lambda port: None)
    return [line.encode() + b"\n" for line in out.getvalue().splitlines()], rig


class FakeProc:
    """subprocess.Popen for `ssh ... docker exec`: stdout gives `lines`, then waits for
    kill() if `hang`, else ends with `code`."""

    def __init__(self, lines=(), code=0, stderr=b"", hang=False):
        self.lines, self.code, self.hang = list(lines), code, hang
        self.killed = threading.Event()
        self.stdin = io.BytesIO()
        self.stdin.close = lambda: None
        self.stderr = io.BytesIO(stderr)
        self.argv = None
        self.returncode = None

    @property
    def stdout(self):
        yield from self.lines
        if self.hang:
            self.killed.wait(10)

    def __call__(self, argv, **kw):
        self.argv = argv
        return self

    def wait(self):
        self.returncode = -9 if self.killed.is_set() else self.code
        return self.returncode

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed.set()


def local(s, script, traces):
    """Result or exception, the trace text, and the sign commands, of spec.run on a fake Rig here."""
    rig = Rig(script)
    rig.server, rig.origin, rig.display, rig.heading = Sat, PLOT.origin, Display(), [{"text": "fake\n"}]
    try:
        got = spec_module._run(rig, s, s.tests[0], False)
    except AssertionError as e:
        got = e
    return got, (traces / s.name / "t.json").read_text(), rig.display.sent


def test_a_passing_test_matches_a_local_run(monkeypatch, tmp_path, isolated):
    s = make_spec([{"wait": 3}, {"expect": {"out": 1}}])
    monkeypatch.setattr(spec_module, "TRACE_DIR", tmp_path / "local")
    want, want_trace, want_signs = local(s, square(2, 99), tmp_path / "local")
    lines, rig = serve_lines(monkeypatch, s, square(2, 99))
    assert rig.released == 1
    proc = FakeProc(lines)
    monkeypatch.setattr(remote, "popen", proc)
    monkeypatch.setattr(spec_module, "TRACE_DIR", tmp_path / "remote")
    isolated.clear()
    rr = remote.RemoteRig(Sat, PLOT, Display(), None)
    rr.heading = [{"text": "fake\n"}]
    assert rr.run_spec(s, s.tests[0], False) == want
    assert (tmp_path / "remote" / s.name / "t.json").read_text() == want_trace
    assert rr.display.sent == want_signs and want_signs
    assert proc.argv == ["ssh", "-o", "ConnectTimeout=10", "user@desktop.invalid", "docker", "exec", "-i", "dsat1", "python3", "-c", remote.BOOT]
    assert rr.loaded is not None
    rr.release()


def test_a_failure_raises_the_same_error_and_keeps_the_trace(monkeypatch, tmp_path):
    s = make_spec([{"expect": {"out": 1}}, {"wait": 2}])
    monkeypatch.setattr(spec_module, "TRACE_DIR", tmp_path / "local")
    want, want_trace, _ = local(s, lambda tick: {}, tmp_path / "local")
    lines, _ = serve_lines(monkeypatch, s, lambda tick: {})
    monkeypatch.setattr(remote, "popen", FakeProc(lines))
    monkeypatch.setattr(spec_module, "TRACE_DIR", tmp_path / "remote")
    with pytest.raises(AssertionError) as e:
        remote.RemoteRig(Sat, PLOT, Display(), None).run_spec(s, s.tests[0], False)
    assert str(e.value) == str(want) and "expected out=1" in str(want)
    assert (tmp_path / "remote" / s.name / "t.json").read_text() == want_trace


def test_watch_events_are_replayed_here(monkeypatch, isolated):
    s = make_spec([{"wait": 1}])
    lines, _ = serve_lines(monkeypatch, s, lambda tick: {})
    monkeypatch.setattr(remote, "popen", FakeProc(lines))
    isolated.clear()
    rr = remote.RemoteRig(Sat, PLOT, Display(), None)
    rr.run_spec(s, s.tests[0], False)
    assert [e[0] for e in isolated] == ["test"] and isolated[0][1]["server"] == "dsat1"
    assert "owner" not in isolated[0][1]


def test_the_owner_reaches_the_container(monkeypatch, isolated):
    s = make_spec([{"wait": 1}])
    lines, rig = serve_lines(monkeypatch, s, lambda tick: {}, owner="wf-42")
    assert rig.owner == "wf-42"
    monkeypatch.setattr(remote, "popen", FakeProc(lines))
    isolated.clear()
    remote.RemoteRig(Sat, PLOT, Display(), None).run_spec(s, s.tests[0], False)
    assert isolated[0][1]["owner"] == "wf-42"


def test_an_error_setting_up_is_reported(monkeypatch):
    s = make_spec([{"wait": 1}])

    def broken(*a, **k):
        raise ConnectionRefusedError("no server")

    monkeypatch.setattr(remote, "Rig", broken)
    out = io.StringIO()
    with monkeypatch.context() as m:
        m.setattr(sys, "stdout", sys.stdout)
        remote.serve(remote.RemoteRig(Sat, PLOT, Display(), None).job(s, s.tests[0], False), out=out,
                     rcon_factory=lambda port: None)
    monkeypatch.setattr(remote, "popen", FakeProc([l.encode() + b"\n" for l in out.getvalue().splitlines()]))
    with pytest.raises(ConnectionRefusedError, match="no server") as e:
        remote.RemoteRig(Sat, PLOT, Display(), None).run_spec(s, s.tests[0], False)
    assert "dsat1's container" in "".join(e.value.__notes__)


def test_a_release_failure_surfaces_in_release(monkeypatch):
    s = make_spec([{"wait": 1}])
    rig = Rig()

    def fail():
        raise TimeoutError("tick unfreeze")

    rig.release = fail
    monkeypatch.setattr(remote, "Rig", made(rig))
    out = io.StringIO()
    with monkeypatch.context() as m:
        m.setattr(sys, "stdout", sys.stdout)
        remote.serve(remote.RemoteRig(Sat, PLOT, Display(), None).job(s, s.tests[0], False), out=out,
                     rcon_factory=lambda port: None)
    monkeypatch.setattr(remote, "popen", FakeProc([l.encode() + b"\n" for l in out.getvalue().splitlines()]))
    rr = remote.RemoteRig(Sat, PLOT, Display(), None)
    rr.run_spec(s, s.tests[0], False)
    with pytest.raises(TimeoutError):
        rr.release()


def test_a_container_without_python_runs_the_test_through_the_forward(monkeypatch):
    s = make_spec([{"wait": 3}, {"expect": {"out": 1}}])
    missing = FakeProc(code=127, stderr=b'OCI runtime exec failed: exec: "python3": executable file not found in $PATH')
    monkeypatch.setattr(remote, "popen", missing)
    here = Rig(square(2, 99))
    monkeypatch.setattr(remote, "Rig", made(here))
    rr = remote.RemoteRig(Sat, PLOT, Display(), lambda: "rcon")
    rr.run_spec(s, s.tests[0], False)
    assert remote.NO_PYTHON == {"dsat1"} and here.tick == 3
    rr.release()
    assert here.released == 1
    monkeypatch.setattr(remote, "popen", lambda *a, **k: pytest.fail("asked the container again"))
    remote.RemoteRig(Sat, PLOT, Display(), lambda: "rcon").run_spec(s, s.tests[0], False)


def test_a_silent_desktop_fails_the_test_and_is_marked_down(monkeypatch):
    s = make_spec([{"wait": 1}])
    proc = FakeProc([b'{"alive": 1}\n'], hang=True)
    monkeypatch.setattr(remote, "popen", proc)
    monkeypatch.setattr(remote, "SILENCE", 0.2)
    monkeypatch.setattr(ds, "_probe", lambda: False)
    marked = []
    monkeypatch.setattr(ds, "_mark_down", lambda: marked.append(1))
    with pytest.raises(ds.DesktopError, match="lost the desktop"):
        remote.RemoteRig(Sat, PLOT, Display(), None).run_spec(s, s.tests[0], False)
    assert proc.killed.is_set() and marked


def test_a_stall_with_the_desktop_answering_waits_then_fails(monkeypatch):
    s = make_spec([{"wait": 1}])
    proc = FakeProc(hang=True)
    monkeypatch.setattr(remote, "popen", proc)
    monkeypatch.setattr(remote, "SILENCE", 0.1)
    monkeypatch.setattr(remote, "STALL", 0.35)
    probes = []
    monkeypatch.setattr(ds, "_probe", lambda: probes.append(1) or True)
    monkeypatch.setattr(ds, "_mark_down", lambda: pytest.fail("marked a desktop that answers"))
    with pytest.raises(ds.DesktopError, match="never started"):
        remote.RemoteRig(Sat, PLOT, Display(), None).run_spec(s, s.tests[0], False)
    assert len(probes) == 4 and proc.killed.is_set()


def test_a_stream_that_resumes_after_a_stall_completes(monkeypatch):
    s = make_spec([{"wait": 1}])
    lines, _ = serve_lines(monkeypatch, s, lambda tick: {})

    class Slow(FakeProc):
        @property
        def stdout(self):
            import time
            time.sleep(0.3)
            yield from self.lines

    monkeypatch.setattr(remote, "popen", Slow(lines))
    monkeypatch.setattr(remote, "SILENCE", 0.1)
    monkeypatch.setattr(ds, "_probe", lambda: True)
    assert remote.RemoteRig(Sat, PLOT, Display(), None).run_spec(s, s.tests[0], False) == {}


def test_ssh_dying_mid_test_is_a_clear_failure(monkeypatch):
    s = make_spec([{"wait": 1}])
    monkeypatch.setattr(remote, "popen", FakeProc([b'{"alive": 1}\n'], code=255, stderr=b"Connection reset"))
    monkeypatch.setattr(ds, "_probe", lambda: True)
    monkeypatch.setattr(ds, "_mark_down", lambda: pytest.fail("marked a desktop that answers"))
    with pytest.raises(ds.DesktopError, match="lost the desktop.*Connection reset"):
        remote.RemoteRig(Sat, PLOT, Display(), None).run_spec(s, s.tests[0], False)


def test_a_stopped_container_is_not_mistaken_for_an_old_image(monkeypatch):
    s = make_spec([{"wait": 1}])
    monkeypatch.setattr(remote, "popen", FakeProc(code=1, stderr=b"Error response from daemon: container abc is not running"))
    with pytest.raises(ds.DesktopError, match="is not running"):
        remote.RemoteRig(Sat, PLOT, Display(), None).run_spec(s, s.tests[0], False)
    assert not remote.NO_PYTHON


def test_no_host_fails_without_running_anything(monkeypatch):
    s = make_spec([{"wait": 1}])
    monkeypatch.setattr(ds, "HOST", None)
    monkeypatch.setattr(remote, "popen", lambda *a, **k: pytest.fail("ran ssh"))
    with pytest.raises(ds.DesktopError, match="no Docker host"):
        remote.RemoteRig(Sat, PLOT, Display(), None).run_spec(s, s.tests[0], False)


def test_the_program_unpacks_this_package_and_calls_serve(tmp_path):
    """BOOT and its stdin line, run by a real python with serve() stubbed in the shipped
    copy, and stdin left open: nothing may wait for EOF."""
    prog = base64.b64decode(remote.program({"spec": None})).decode()
    stub = prog.replace("from redstone.remote import serve",
                        "import redstone.spec, redstone.harness\n    serve = lambda job: print(sorted(job), redstone.spec.__file__, flush=True)")
    p = subprocess.Popen([sys.executable, "-c", remote.BOOT], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, cwd=tmp_path)
    try:
        p.stdin.write(base64.b64encode(stub.encode()) + b"\n")
        p.stdin.flush()
        got = {}
        reader = threading.Thread(target=lambda: got.setdefault("line", p.stdout.readline()))
        reader.start()
        reader.join(20)
        keys, where = got["line"].decode().rsplit(" ", 1)
        assert keys == "['spec']" and "redstone-" in where
    finally:
        p.kill()


def test_nothing_in_the_program_needs_quoting_for_cmd_exe(monkeypatch):
    proc = FakeProc(code=127, stderr=b"executable file not found")
    monkeypatch.setattr(remote, "popen", proc)
    rr = remote.RemoteRig(Sat, PLOT, Display(), lambda: "rcon")
    monkeypatch.setattr(remote, "Rig", made(Rig()))
    s = make_spec([{"wait": 1}])
    rr.run_spec(s, s.tests[0], False)
    assert not set("".join(proc.argv)) & set(' "^&|<>%')
