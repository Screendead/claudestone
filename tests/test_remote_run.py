"""scripts.remote_run offline: the real worker runs here under this python, with the
container's volumes as symlinks into a temporary directory in place of `ssh ... docker run`."""

import base64
import io
import json
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

    # The files copied back are new content, so the next run uploads again; one after it
    # that changes nothing does not.
    run(work, "a")
    assert len(desk.runs) == 6
    run(work, "a")
    assert len(desk.runs) == 7 and (work / "result.txt").read_text() == "found a"


def test_new_content_gets_a_new_volume_and_the_old_one_is_dropped(desk, work):
    run(work)
    first = desk.volumes()
    (work / "keep.txt").write_text("edited")
    run(work)
    second = [v for v in desk.volumes() if v not in first]
    assert len(second) == 1 and second[0].rsplit("-", 1)[0] == first[0].rsplit("-", 1)[0]
    assert ("docker", "volume", "rm", *first) in desk.ssh


def test_the_container_limits_come_from_jobs(desk, work):
    rr.execute(HOST, work, [sys.executable, "job.py", "x", "0"], 3, "3g", out=io.BytesIO(), err=io.BytesIO())
    argv = desk.runs[-1]
    assert "--cpus=3" in argv and "--memory=3g" in argv and "--rm" in argv and rr.LABEL in argv
    assert not set("".join(argv)) & set(' "^&|<>%')


def test_a_missing_command_is_exit_127(desk, work):
    out, err = io.BytesIO(), io.BytesIO()
    assert rr.execute(HOST, work, ["no-such-command-here"], 1, "1g", out=out, err=err) == 127
    assert b"No such file" in err.getvalue()


def test_closing_stdin_stops_the_command(desk, work, tmp_path):
    """What a killed laptop process looks like from the container: stdin reaches EOF."""
    (work / "slow.py").write_text("import os, time, pathlib\n"
                                  f"pathlib.Path({str(tmp_path / 'pid')!r}).write_text(str(os.getpid()))\n"
                                  "print('started', flush=True)\n"
                                  "time.sleep(60)\n")
    run(work)  # uploads the source
    job = {"mode": "run", **rr.CONTAINER, "cmd": [sys.executable, "slow.py"], "jobs": 1}
    p = desk(rr.docker_run_argv(HOST, "rr-x", [f"{desk.volumes()[0]}:{rr.CONTAINER['src']}"]),
             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.stdin.write(rr.program(job))
    p.stdin.flush()
    assert b"started" in base64.b64decode(json.loads(p.stdout.readline())["o"])
    pid = int((tmp_path / "pid").read_text())
    p.stdin.close()
    assert p.wait(20) == 143
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        os.kill(pid, signal.SIGKILL)
        pytest.fail("the command outlived its container's stdin")


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
    run(work)
    monkeypatch.setattr(rr, "SILENCE", 0.3)
    monkeypatch.setattr(docker_sats, "_probe", lambda: False)
    (work / "hang.py").write_text("import time\ntime.sleep(5)\n")
    real = desk.__call__

    def silent(argv, **kw):
        p = real(argv, **kw)
        r, w = os.pipe()
        p.stdout = os.fdopen(r, "rb")  # never written: silence
        p._keep = w
        return p

    monkeypatch.setattr(rr, "popen", silent)
    with pytest.raises(rr.Unreachable, match="stopped answering"):
        rr.execute(HOST, work, [sys.executable, "hang.py"], 1, "1g", out=io.BytesIO(), err=io.BytesIO())
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
    for _ in range(3):
        pidfile.unlink(missing_ok=True)
        root = tmp_path / f"run{_}"
        root.mkdir()
        p = subprocess.Popen([sys.executable, "-c", driver, str(root), str(work), str(pidfile)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert p.stdout.readline().startswith(b"tick")
        p.send_signal(sig)
        out, err = p.communicate(timeout=60)
        assert p.returncode == 130, err.decode()
        assert b"Fatal Python error" not in err and b"interrupted" in err
        assert _gone(int(pidfile.read_text())), "the command outlived the interrupted run"


def test_the_worker_never_aborts_at_exit(desk, work, tmp_path):
    """Worker processes, ended by their stdin closing mid-stream and by their command
    finishing, exit with their code and no fatal error, many times over."""
    (work / "chatty.py").write_text(CHATTY)
    run(work)
    volume = f"{desk.volumes()[0]}:{rr.CONTAINER['src']}"
    for i in range(6):
        cmd = [sys.executable, "chatty.py", str(tmp_path / "pid")] if i % 2 else [sys.executable, "job.py", "x", "5"]
        p = desk(rr.docker_run_argv(HOST, "rr-x", [volume]), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE)
        p.stdin.write(rr.program({"mode": "run", **rr.CONTAINER, "cmd": cmd, "jobs": 1}))
        p.stdin.flush()
        if i % 2:
            p.stdout.readline()
            want = 143
        else:
            while b'"exit"' not in p.stdout.readline():
                pass
            want = 5
        p.stdin.close()
        err = p.stderr.read()
        p.stdout.read()
        assert p.wait(30) == want and b"Fatal Python error" not in err, err.decode()


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
