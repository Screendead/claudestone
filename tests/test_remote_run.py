"""scripts.remote_run offline: the real worker runs here under this python, with the
container's volumes as symlinks into a temporary directory in place of `ssh ... docker run`."""

import io
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from redstone import docker_sats
from scripts import remote_run as rr

HOST = "user@desktop.invalid"


class Ssh(subprocess.Popen):
    """The worker as `ssh ... docker run -i` would run it: killing ssh closes the
    container's stdin, it does not kill the worker."""

    def kill(self):
        try:
            self.stdin.close()
        except (OSError, ValueError):
            pass
        try:
            self.wait(15)
        except subprocess.TimeoutExpired:
            super().kill()


class FakeDocker:
    """popen for `ssh HOST docker run ... -v vol:path ... IMAGE python3 -c BOOT`: each
    mount becomes a symlink from its path to vols/<vol>, and the worker runs locally."""

    def __init__(self, root):
        self.root, self.vols = root, root / "vols"
        self.vols.mkdir()
        self.runs = []

    def __call__(self, argv, **kw):
        assert argv[:4] == ["ssh", "-o", "ConnectTimeout=10", HOST] and argv[-2:] == ["-c", rr.BOOT]
        self.runs.append(argv)
        shutil.rmtree(rr.CONTAINER["work"], ignore_errors=True)  # a fresh container
        for i, a in enumerate(argv):
            if a == "-v":
                vol, path = argv[i + 1].split(":")
                (self.vols / vol).mkdir(exist_ok=True)
                if os.path.lexists(path):
                    os.unlink(path)
                os.symlink(self.vols / vol, path)
        return Ssh([sys.executable, "-c", rr.BOOT], **kw)

    def volumes(self):
        return sorted(p.name for p in self.vols.iterdir())


@pytest.fixture
def desk(tmp_path, monkeypatch):
    box = tmp_path / "container"
    box.mkdir()
    monkeypatch.setattr(rr, "CONTAINER", {k: str(box / k) for k in ("src", "work", "pip")})
    fake = FakeDocker(tmp_path)
    monkeypatch.setattr(rr, "popen", fake)
    fake.ssh = []

    def ssh(host, *args, timeout=30):
        fake.ssh.append(args)
        out = "\n".join(fake.volumes()) if args[:3] == ("docker", "volume", "ls") else ""
        return subprocess.CompletedProcess(args, 0, out.encode(), b"")

    monkeypatch.setattr(rr, "ssh", ssh)
    monkeypatch.setattr(docker_sats, "_probe", lambda: True)
    return fake


@pytest.fixture
def work(tmp_path):
    d = tmp_path / "search"
    d.mkdir()
    (d / "job.py").write_text(
        "import sys, pathlib\n"
        "print('out line', flush=True)\n"
        "print('err line', file=sys.stderr, flush=True)\n"
        "pathlib.Path('result.txt').write_text('found ' + sys.argv[1])\n"
        "pathlib.Path('sub').mkdir(exist_ok=True)\n"
        "pathlib.Path('sub/deep.txt').write_text('deep')\n"
        "sys.exit(int(sys.argv[2]))\n")
    (d / "keep.txt").write_text("untouched")
    (d / "__pycache__").mkdir()
    (d / "__pycache__" / "junk.pyc").write_bytes(b"x")
    return d


def run(d, *args, code="0"):
    out, err = io.BytesIO(), io.BytesIO()
    got = rr.execute(HOST, d, [sys.executable, "job.py", *args, code] if args else [sys.executable, "job.py", "x", code],
                     1, "1g", out=out, err=err)
    return got, out.getvalue(), err.getvalue()


def test_a_run_uploads_once_streams_and_copies_changes_back(desk, work):
    before = (work / "keep.txt").stat().st_mtime_ns
    code, out, err = run(work, "a", code="3")
    assert code == 3 and out == b"out line\n" and b"err line\n" in err
    assert (work / "result.txt").read_text() == "found a" and (work / "sub" / "deep.txt").read_text() == "deep"
    assert (work / "keep.txt").stat().st_mtime_ns == before
    assert len(desk.runs) == 3  # run (source missing), upload, run
    src = desk.vols / desk.volumes()[0] / "tree"
    assert (src / "job.py").exists() and not (src / "__pycache__").exists()

    # The files copied back are new content, so the next run uploads again into a new
    # volume and drops the old one; one after it that changes nothing does not upload.
    first = desk.volumes()
    run(work, "a")
    assert len(desk.runs) == 6
    second = [v for v in desk.volumes() if v not in first]
    assert len(second) == 1 and second[0].rsplit("-", 1)[0] == first[0].rsplit("-", 1)[0]
    assert ("docker", "volume", "rm", *first) in desk.ssh
    run(work, "a")
    assert len(desk.runs) == 7 and (work / "result.txt").read_text() == "found a"


def test_the_container_limits_come_from_jobs(monkeypatch, work):
    seen = []

    def session(host, argv, line, rest=None):
        seen.append(argv)
        raise KeyboardInterrupt

    monkeypatch.setattr(rr, "Session", session)
    for gpus in (False, True):
        with pytest.raises(KeyboardInterrupt):
            rr.execute(HOST, work, [sys.executable, "job.py"], 3, "3g", gpus=gpus)
    plain, gpu = seen
    assert "--cpus=3" in plain and "--memory=3g" in plain and "--rm" in plain and rr.LABEL in plain
    assert not set("".join(plain)) & set(' "^&|<>%')
    assert "--gpus" not in plain
    assert gpu[gpu.index("--gpus") + 1] == "all" and gpu.index("--gpus") < gpu.index(rr.IMAGE)


def test_a_missing_command_is_exit_127(desk, work):
    out, err = io.BytesIO(), io.BytesIO()
    assert rr.execute(HOST, work, ["no-such-command-here"], 1, "1g", out=out, err=err) == 127
    assert b"No such file" in err.getvalue()


class Dead:
    """A popen whose ssh fails at once, as with an unreachable desktop."""

    def __call__(self, argv, **kw):
        return subprocess.Popen([sys.executable, "-c", "import sys; sys.stderr.write('ssh: connect: timed out'); sys.exit(255)"],
                                **kw)


def test_an_unreachable_desktop_is_an_error_not_a_local_run(desk, work, monkeypatch):
    monkeypatch.setattr(rr, "popen", Dead())
    with pytest.raises(rr.Unreachable, match="unreachable.*timed out"):
        run(work)
    assert not (work / "result.txt").exists()


def test_main_reports_an_unreachable_desktop_as_255(desk, work, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(rr, "popen", Dead())
    monkeypatch.setattr(docker_sats, "HOST", HOST)
    monkeypatch.setattr(rr, "SLOTS", tmp_path / "slots")
    assert rr.main([str(work), "--", "python3", "job.py"]) == 255
    assert "unreachable" in capsys.readouterr().err


def test_no_host_is_an_error(monkeypatch, work, capsys):
    monkeypatch.setattr(docker_sats, "HOST", None)
    assert rr.main([str(work), "--", "python3", "job.py"]) == 255
    assert "no desktop configured" in capsys.readouterr().err


def test_a_silent_desktop_is_given_up_and_the_container_removed(desk, work, monkeypatch):
    monkeypatch.setattr(rr, "SILENCE", 0.3)
    monkeypatch.setattr(docker_sats, "_probe", lambda: False)
    real = desk.__call__

    def silent(argv, **kw):
        p = real(argv, **kw)
        r, w = os.pipe()
        p.stdout = os.fdopen(r, "rb")  # never written: silence, until the session waits for its end
        wait = p.wait

        def waited(*a):
            if w not in closed:
                closed.append(w)
                os.close(w)
            return wait(*a)

        p.wait = waited
        return p

    closed = []

    monkeypatch.setattr(rr, "popen", silent)
    with pytest.raises(rr.Unreachable, match="stopped answering"):
        rr.execute(HOST, work, [sys.executable, "job.py"], 1, "1g", out=io.BytesIO(), err=io.BytesIO())
    assert any(a[:3] == ("docker", "rm", "-f") for a in desk.ssh)


def test_cpu_slots_cap_all_runs_together(tmp_path):
    held = rr.take_cpus(2, total=3, slots=tmp_path)
    said = []
    start = time.time()

    def free_later():
        time.sleep(0.5)
        for f in held:
            f.close()

    threading.Thread(target=free_later).start()
    got = rr.take_cpus(2, total=3, slots=tmp_path, say=lambda *a, **k: said.append(a))
    assert time.time() - start >= 0.4 and said and len(got) == 2
    with pytest.raises(SystemExit):
        rr.take_cpus(4, total=3, slots=tmp_path)
    for f in got:
        f.close()


CHATTY = ("import os, pathlib, sys, time\n"
          "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n"
          "while True:\n"
          "    print('tick ' * 50, flush=True)\n"
          "    time.sleep(0.001)\n")

DRIVER = """
import pathlib, subprocess, sys
sys.path[:0] = [{tests!r}, {repo!r}]
from test_remote_run import FakeDocker
from redstone import docker_sats
from scripts import remote_run as rr
root = pathlib.Path(sys.argv[1])
box = root / "container"
box.mkdir()
rr.CONTAINER = {{k: str(box / k) for k in ("src", "work", "pip")}}
rr.popen = FakeDocker(root)
rr.ssh = lambda host, *a, timeout=30: subprocess.CompletedProcess(a, 0, b"", b"")
rr.SLOTS = root / "slots"
docker_sats.HOST = {host!r}
docker_sats._probe = lambda: True
sys.exit(rr.main([sys.argv[2], "--", sys.executable, "chatty.py", sys.argv[3]]))
"""


def _gone(pid, within=10) -> bool:
    deadline = time.time() + within
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.1)
    os.kill(pid, signal.SIGKILL)
    return False


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_the_cli_killed_mid_stream_exits_cleanly_and_stops_the_command(tmp_path, work, sig):
    """Run as a real process: an interrupt mid-stream must unwind (exit 130), never end in a
    "Fatal Python error" at interpreter shutdown, and stop the remote command."""
    (work / "chatty.py").write_text(CHATTY)
    driver = DRIVER.format(tests=str(Path(__file__).parent), repo=str(Path(__file__).parent.parent), host=HOST)
    pidfile = tmp_path / "chatty.pid"
    p = subprocess.Popen([sys.executable, "-c", driver, str(tmp_path), str(work), str(pidfile)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p.stdout.readline().startswith(b"tick")
    p.send_signal(sig)
    out, err = p.communicate(timeout=60)
    assert p.returncode == 130, err.decode()
    assert b"Fatal Python error" not in err and b"interrupted" in err
    assert _gone(int(pidfile.read_text())), "the command outlived the interrupted run"


def test_the_worker_ends_with_its_code_and_no_fatal_error(desk, work, tmp_path):
    """Ended by its command finishing, and by its stdin closing mid-stream (what a killed
    laptop process looks like from the container), which also stops the command."""
    (work / "chatty.py").write_text(CHATTY)
    run(work)
    volume = f"{desk.volumes()[0]}:{rr.CONTAINER['src']}"
    pidfile = tmp_path / "pid"
    for cmd, want in (([sys.executable, "job.py", "x", "5"], 5), ([sys.executable, "chatty.py", str(pidfile)], 143)):
        p = desk(rr.docker_run_argv(HOST, "rr-x", [volume]), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE)
        p.stdin.write(rr.program({"mode": "run", **rr.CONTAINER, "cmd": cmd, "jobs": 1}))
        p.stdin.flush()
        if want == 143:
            p.stdout.readline()
        else:
            while b'"exit"' not in p.stdout.readline():
                pass
        p.stdin.close()
        _, err = p.communicate(timeout=30)
        assert p.returncode == want and b"Fatal Python error" not in err, err.decode()
    assert _gone(int(pidfile.read_text())), "the command outlived its container's stdin"


def test_an_upload_the_container_never_reads_is_retried(desk, work, monkeypatch):
    monkeypatch.setattr(rr, "UPLOAD_TIMEOUT", 1)
    hung = []

    def popen(argv, **kw):
        if not hung and any(a.startswith("rr-up-") for a in argv):
            hung.append(argv)
            return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], **kw)
        return desk(argv, **kw)

    monkeypatch.setattr(rr, "popen", popen)
    got, out, _ = run(work)
    assert got == 0 and b"out line" in out and hung
