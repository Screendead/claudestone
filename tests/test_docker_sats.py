"""redstone.docker_sats: offline against a fake ssh/docker runner, and live on the desktop
when it is reachable."""

import fcntl
import io
import os
import socket
import subprocess
import sys
import tarfile
import time

import pytest

from redstone import docker_sats as ds
from redstone.build import write_datapack
from redstone.servers import Server


class Fake:
    """Stands in for subprocess.run. `rules` maps an argv prefix to a list of results
    used in turn (the last repeats): (returncode, stdout, stderr) or an exception."""

    def __init__(self, rules=None):
        self.rules = rules or {}
        self.calls = []

    def __call__(self, argv, input=None, stdout=None, stderr=None, timeout=None, env=None):
        self.calls.append({"argv": argv, "input": input, "env": env, "merge": stderr == subprocess.STDOUT})
        for prefix, results in sorted(self.rules.items(), key=lambda kv: -len(kv[0])):
            if tuple(argv[:len(prefix)]) == prefix:
                result = results.pop(0) if len(results) > 1 else results[0]
                if isinstance(result, BaseException):
                    raise result
                code, out, err = result
                return subprocess.CompletedProcess(argv, code, out, err)
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    def argvs(self, *prefix):
        return [c["argv"] for c in self.calls if tuple(c["argv"][:len(prefix)]) == prefix]


D = ("docker", "--context", ds.CONTEXT)
EXIT = ["ssh", "-O", "exit", ds.HOST]
CHECK = ("ssh", "-O", "check", ds.HOST)
PROBE = tuple(ds.PROBE)
MASTER = (0, b"", b"Master running (pid=4242)\r\n")


@pytest.fixture
def fake(monkeypatch):
    f = Fake({CHECK: [MASTER]})
    monkeypatch.setattr(ds, "run", f)
    monkeypatch.setattr(ds, "_listeners", lambda port: None)
    monkeypatch.setattr(ds, "_password", lambda: "s3cret")
    monkeypatch.setattr(ds, "_spawn_reaper", lambda: None)
    return f


@pytest.fixture
def sat(tmp_path):
    return ds.DockerSatellite("dsat1", tmp_path / "dsat1", 0, 25676, "1G")


def test_looks_like_a_satellite(sat):
    assert sat.level_name() == "testworld"
    assert sat.lock == sat.dir / "rig.lock"
    assert isinstance(sat, Server) and sat != Server("dsat1", sat.dir, 0, 25676, "1G")
    names = [s.name for s in ds.DOCKER_SATELLITES]
    ports = {s.rcon_port for s in ds.DOCKER_SATELLITES}
    assert names == [f"dsat{i}" for i in range(1, 7)]
    assert not ports & set(range(25565, 25582))


def test_importing_registers_the_dsats_without_a_cycle():
    code = ("import redstone.docker_sats; from redstone.servers import SERVERS; "
            "assert SERVERS['dsat3'].rcon_port == 25678, SERVERS; import scripts.satellite_image")
    subprocess.run([sys.executable, "-c", code], cwd=ds.ROOT.parent, check=True)


def test_start_runs_the_container_with_the_password_in_env_only(fake, sat, monkeypatch):
    ready = iter([False, False, True])  # is_up, first poll, second poll
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: next(ready))
    fake.rules[(*D, "logs")] = [(1, b"Error: No such container: dsat1", None)]
    assert "started" in sat.start()
    [run] = [c for c in fake.calls if c["argv"][3:4] == ["run"]]
    assert run["argv"] == [*D, "run", "-d", "--name", "dsat1", "-e", "RCON_PASSWORD", "-e", "MEMORY=1G",
                           "-p", "127.0.0.1:25676:25575", ds.IMAGE]
    assert run["env"]["RCON_PASSWORD"] == "s3cret"
    assert not any("s3cret" in " ".join(c["argv"]) for c in fake.calls)
    assert ["ssh", "-O", "forward", "-L", "25676:127.0.0.1:25676", ds.HOST] in fake.argvs("ssh")
    assert sat.lock.exists()


def test_start_saves_a_dead_container_s_logs_before_replacing_it(fake, sat, monkeypatch):
    ready = iter([False, True])
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: next(ready))
    fake.rules[(*D, "logs")] = [(0, b"java crashed\n", None)]
    sat.start()
    assert (sat.dir / "harness.log").read_bytes() == b"java crashed\n"
    order = [c["argv"][3] for c in fake.calls if c["argv"][0] == "docker"]
    assert order.index("logs") < order.index("cp") < order.index("rm") < order.index("run")


def test_start_never_replaces_a_running_container(fake, sat, monkeypatch):
    # Not answering within the probe's timeout may only mean busy under another test.
    ready = iter([False, False, True])
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: next(ready))
    fake.rules[(*D, "ps")] = [(0, b"dsat1\n", b"")]
    assert "started" in sat.start()
    assert not fake.argvs(*D, "rm") and not fake.argvs(*D, "run")


def test_start_holds_its_lock_from_check_to_run(fake, sat, monkeypatch):
    held = []

    def on_run(argv, **kw):
        if argv[3:4] == ["run"]:
            with open(sat.dir / "start.lock", "a") as other:
                try:
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    held.append(False)
                except BlockingIOError:
                    held.append(True)
        return fake(argv, **kw)

    monkeypatch.setattr(ds, "run", on_run)
    ready = iter([False, True])
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: next(ready))
    fake.rules[(*D, "logs")] = [(1, b"No such container", None)]
    sat.start()
    assert held == [True]


def test_start_times_out(fake, sat, monkeypatch):
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: False)
    with pytest.raises(TimeoutError, match="stop dsat1"):
        sat.start(timeout=0.5)


def test_docker_run_is_never_retried(fake, sat, monkeypatch):
    fake.rules[(*D, "run")] = [subprocess.TimeoutExpired("docker", 60)]
    fake.rules[(*D, "ps")] = [(0, b"", b""), (0, b"dsat1\n", b"")]  # before run; after: it started anyway
    fake.rules[(*D, "logs")] = [(1, b"No such container", None)]
    ready = iter([False, True])
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: next(ready))
    assert "started" in sat.start()
    assert len(fake.argvs(*D, "run")) == 1 and not fake.argvs("ssh", "-O", "exit")
    fake.rules[(*D, "ps")] = [(0, b"", b"")]  # and when it did not start, say so
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: False)
    with pytest.raises(ds.DesktopError, match="timed out"):
        sat.start()


def test_is_up_needs_rcon_not_just_the_forward(fake, sat, monkeypatch):
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: False)
    assert not sat.is_up()
    # Kept: a busy server can read as down, and its test may open a connection through it.
    assert not fake.argvs("ssh", "-O", "cancel")
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: True)
    assert sat.is_up()


def test_no_remote_command_needs_a_unix_shell(fake, sat, monkeypatch):
    # The desktop's sshd runs cmd.exe: `true` fails there, `exit` works in both.
    fake.rules[CHECK] = [(255, b"", b"Control socket connect: No such file or directory\r\n"), MASTER]
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: True)
    assert sat.is_up()
    assert fake.argvs(*PROBE) and not any(a[-1] == "true" for a in fake.argvs("ssh"))


def test_a_hung_master_check_reads_as_down(fake, sat, monkeypatch):
    fake.rules[CHECK] = [subprocess.TimeoutExpired("ssh", 5)]
    monkeypatch.setattr(ds, "rcon_ready", lambda port, timeout=3: True)
    assert sat.is_up() is False


def test_forward_refuses_a_port_another_process_holds(fake, sat, monkeypatch):
    monkeypatch.setattr(ds, "_listeners", lambda port: {999})
    with pytest.raises(ds.DesktopError, match="held by pid 999"):
        sat.forward()
    assert not fake.argvs("ssh", "-O", "forward")
    monkeypatch.setattr(ds, "_listeners", lambda port: {4242})  # the master's own forward
    sat.forward()
    assert fake.argvs("ssh", "-O", "forward")


def test_listeners_finds_a_real_listener():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    try:
        assert ds._listeners(s.getsockname()[1]) == {os.getpid()}
    finally:
        s.close()


class FakeRcon:
    def __init__(self, behaviour):
        self.behaviour = behaviour

    def __call__(self, port, timeout):
        if self.behaviour == "refused":
            raise ConnectionRefusedError
        return self

    def cmd(self, command):
        if self.behaviour == "closed":  # the tunnel accepted TCP, nothing behind it
            raise ConnectionResetError
        return "The game time is 91 tick(s)"

    def close(self):
        pass


@pytest.mark.parametrize("behaviour,ok", [("refused", False), ("closed", False), ("up", True)])
def test_rcon_ready(monkeypatch, behaviour, ok):
    monkeypatch.setattr(ds, "Rcon", FakeRcon(behaviour))
    assert ds.rcon_ready(25676) is ok


def test_stale_master_is_closed_and_the_call_retried(fake):
    fake.rules[(*D, "ps")] = [(255, b"", b"mux_client_request_session: read from master failed: Broken pipe"),
                              (0, b"dsat1\n", b"")]
    fake.rules[PROBE] = [subprocess.TimeoutExpired("ssh", 8), (0, b"", b"")]  # stale, then fresh
    assert ds.running() == {"dsat1"}
    assert fake.argvs("ssh", "-O", "exit") == [EXIT]
    assert len(fake.argvs(*D, "ps")) == 2


def test_a_hang_over_a_stale_master_is_retried(fake):
    fake.rules[(*D, "ps")] = [subprocess.TimeoutExpired("docker", 30), (0, b"", b"")]
    fake.rules[PROBE] = [(255, b"", b""), (0, b"", b"")]
    assert ds.running() == set()
    assert fake.argvs("ssh", "-O", "exit") == [EXIT]


def test_a_hang_over_a_healthy_master_is_the_command_s(fake):
    # Closing the master would cut every other process's forwards and RCON sockets.
    fake.rules[(*D, "ps")] = [subprocess.TimeoutExpired("docker", 30), (0, b"", b"")]
    with pytest.raises(ds.DesktopError, match="timed out"):
        ds.running()
    assert not fake.argvs("ssh", "-O", "exit") and len(fake.argvs(*D, "ps")) == 1


def test_docker_desktop_down_keeps_the_master(fake):
    err = b'error during connect: Get "http://docker.example/v1.47/version": EOF'
    fake.rules[(*D, "version")] = [(1, b"", err)]
    assert not ds.reachable()
    assert not fake.argvs("ssh", "-O", "exit") and len(fake.argvs(*D, "version")) == 2


def test_unreachable_desktop_is_not_retried(fake):
    fake.rules[CHECK] = [(255, b"", b"No such file or directory")]
    fake.rules[PROBE] = [(255, b"", b"ssh: connect to host: Operation timed out")]
    fake.rules[(*D, "version")] = [subprocess.TimeoutExpired("docker", 5)]
    assert not ds.reachable()
    assert len(fake.argvs(*D, "version")) == 1 and not fake.argvs("ssh", "-O", "exit")


def test_command_errors_do_not_close_the_master(fake):
    # Closing it would drop every other satellite's forward mid-test.
    fake.rules[(*D, "exec")] = [(1, b"", b"Error response from daemon: No such container: dsat1")]
    with pytest.raises(ds.DesktopError, match="No such container"):
        ds.docker("exec", "dsat1", "true")
    assert not fake.argvs("ssh", "-O", "exit") and not fake.argvs(*PROBE)


def test_stop_saves_logs_and_crash_reports_then_removes(fake, sat):
    sat.dir.mkdir(parents=True)
    fake.rules[(*D, "ps")] = [(0, b"dsat1\n", b"")]
    fake.rules[(*D, "logs")] = [(0, b"[Server thread/INFO]: Done\n", None)]
    assert sat.stop() == "dsat1: stopped"
    order = [c["argv"][3] if c["argv"][0] == "docker" else c["argv"][2] for c in fake.calls]
    assert order.index("stop") < order.index("logs") < order.index("cp") < order.index("rm") < order.index("cancel")
    [cp] = fake.argvs(*D, "cp")
    assert cp[4:] == ["dsat1:/srv/crash-reports", str(sat.dir)]
    assert next(c for c in fake.calls if c["argv"][3:4] == ["logs"])["merge"]
    assert (sat.dir / "harness.log").read_bytes() == b"[Server thread/INFO]: Done\n"


def test_push_datapack_replaces_the_pack(fake, sat, tmp_path, monkeypatch):
    root = write_datapack(tmp_path / "packs", "redstone_ai", {"build": "say hi\n"})
    sat.push_datapack(root, reload=False)
    [call] = [c for c in fake.calls if c["argv"][3:4] == ["exec"]]
    assert call["argv"][4:7] == ["-i", "dsat1", "sh"]
    assert "rm -rf '/srv/testworld/datapacks/redstone_ai'" in call["argv"][-1]
    names = tarfile.open(fileobj=io.BytesIO(call["input"])).getnames()
    assert "redstone_ai/pack.mcmeta" in names and "redstone_ai/data/redstone_ai/function/build.mcfunction" in names


def test_stop_idle_skips_busy_and_recent(fake, monkeypatch, tmp_path):
    sats = {n: ds.DockerSatellite(n, tmp_path / n, 0, 25675 + i, "1G") for i, n in enumerate(["dsat1", "dsat2", "dsat3"], 1)}
    monkeypatch.setattr(ds, "BY_NAME", sats)
    fake.rules[(*D, "ps")] = [(0, b"dsat1\ndsat2\ndsat3\n", b"")]
    for s in sats.values():
        s.dir.mkdir()
        s.lock.touch()
    old = time.time() - 3600
    os.utime(sats["dsat1"].lock, (old, old))
    os.utime(sats["dsat2"].lock, (old, old))
    with open(sats["dsat2"].lock, "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        stopped = ds.stop_idle(minutes=10)
    assert stopped == ["dsat1: stopped"]
    assert [a[-1] for a in fake.argvs(*D, "stop")] == ["dsat1"]
    assert sats["dsat1"].lock.stat().st_mtime < time.time() - 3000  # checking is not use
    assert sats["dsat2"].lock.stat().st_mtime > time.time() - 60  # held means in use now


def test_stop_idle_stops_a_container_that_never_had_a_lock(fake, monkeypatch, tmp_path):
    sats = {"dsat1": ds.DockerSatellite("dsat1", tmp_path / "dsat1", 0, 25676, "1G")}
    monkeypatch.setattr(ds, "BY_NAME", sats)
    fake.rules[(*D, "ps")] = [(0, b"dsat1\n", b"")]
    assert ds.stop_idle(minutes=10) == ["dsat1: stopped"]


def test_reaper_outlasts_an_unreachable_desktop(fake, monkeypatch, tmp_path):
    monkeypatch.setattr(ds, "REAPER_LOCK", tmp_path / "reaper.lock")
    sleeps = []
    monkeypatch.setattr(ds.time, "sleep", sleeps.append)
    outcomes = iter([True, True, True, False])

    def stop_idle(minutes):
        if next(outcomes):
            raise ds.DesktopError("unreachable")
        return []

    monkeypatch.setattr(ds, "stop_idle", stop_idle)
    monkeypatch.setattr(ds, "running", lambda timeout=30: set())
    ds.reap(every=60)
    assert sleeps == [60, 120, 240, 480]


def test_cli_accepts_only_its_actions(fake):
    assert ds.main(["forward"]) == 2 and ds.main(["stop", "sat1"]) == 2
    assert not fake.calls


# Live: only when the desktop answers. Uses dsat6, which scripts and tests pick last.
@pytest.fixture(scope="module")
def live():
    if not ds.reachable():
        pytest.skip(f"desktop {ds.HOST} not reachable")
    sat = ds.BY_NAME["dsat6"]
    if sat.name in ds.running():
        pytest.skip("dsat6 is already running")
    sat.dir.mkdir(parents=True, exist_ok=True)
    with open(sat.lock, "a") as lock:  # keep conftest from taking it meanwhile
        fcntl.flock(lock, fcntl.LOCK_EX)
        sat.start()
        yield sat
        sat.stop()


def test_live_rcon_pack_and_ticks(live, tmp_path):
    from redstone.rcon import Rcon
    r = Rcon(port=live.rcon_port)
    try:
        root = write_datapack(tmp_path, "dsat_live", {"hi": "scoreboard objectives add dl dummy\n"
                                                           "scoreboard players set x dl 42\n"})
        live.push_datapack(root)
        assert r.cmd("function dsat_live:hi").startswith("Running function")
        assert "42" in r.cmd("scoreboard players get x dl")
        r.cmd("tick freeze")
        t0 = int(r.cmd("time query gametime").split()[-2])
        r.cmd("tick step 5")
        deadline = time.time() + 5
        while int(r.cmd("time query gametime").split()[-2]) < t0 + 5:
            assert time.time() < deadline
        r.cmd("tick unfreeze")
    finally:
        r.close()


def test_live_stop_leaves_logs_and_nothing_running(live):
    live.stop()
    assert live.name not in ds.running()
    assert not live.is_up()
    assert "RCON running" in live.log.read_text()
    live.unforward()  # is_up above forwarded again


def test_image_build_streams_the_context_without_mac_metadata():
    from scripts.satellite_image import commands
    tar, build = commands()
    assert tar[:3] == ["tar", "--no-xattrs", "--no-mac-metadata"]
    assert tar[-3:] == ["-C", tar[-2], "server.jar"] and tar[-2].endswith("/server")
    assert {"Dockerfile", "start.sh", "pregen.sh", "server.properties"} <= set(tar)
    assert build == ["docker", "--context", ds.CONTEXT, "build", "-t", ds.IMAGE, "-"]
    assert "--no-cache" in commands(no_cache=True)[1]
