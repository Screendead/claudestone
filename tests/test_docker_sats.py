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


_real_spawn_reaper = ds._spawn_reaper


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


HOST = "user@desktop.invalid"
D = ("docker", "-H", f"ssh://{HOST}")
EXIT = ["ssh", "-O", "exit", HOST]
CHECK = ("ssh", "-O", "check", HOST)
PROBE = ("ssh", "-o", "ConnectTimeout=5", HOST, "exit")
MASTER = (0, b"", b"Master running (pid=4242)\r\n")


@pytest.fixture
def fake(monkeypatch):
    f = Fake({CHECK: [MASTER]})
    monkeypatch.setattr(ds, "HOST", HOST)
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


def test_host_comes_from_the_environment_then_the_file(monkeypatch, tmp_path):
    path = tmp_path / "docker_host"
    monkeypatch.delenv("REDSTONE_DOCKER_HOST", raising=False)
    assert ds.configured_host(path) is None
    path.write_text("a@file\n")
    assert ds.configured_host(path) == "a@file"
    monkeypatch.setenv("REDSTONE_DOCKER_HOST", "b@env")
    assert ds.configured_host(path) == "b@env"


def test_no_host_means_unavailable_without_running_anything(fake, sat, monkeypatch):
    monkeypatch.setattr(ds, "HOST", None)
    assert not ds.reachable()
    assert not sat.is_up()
    with pytest.raises(ds.DesktopError, match="REDSTONE_DOCKER_HOST"):
        ds.running()
    assert ds.main(["status"]) == 1
    assert not fake.calls


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
    assert ["ssh", "-O", "forward", "-L", "25676:127.0.0.1:25676", HOST] in fake.argvs("ssh")
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


def test_a_start_racing_the_reaper_s_exit_still_gets_a_reaper(fake, monkeypatch, tmp_path):
    monkeypatch.setattr(ds, "REAPER_LOCK", tmp_path / "reaper.lock")
    monkeypatch.setattr(ds, "_spawn_reaper", _real_spawn_reaper)
    spawned = []
    monkeypatch.setattr(ds.subprocess, "Popen", lambda *a, **k: spawned.append(a))
    monkeypatch.setattr(ds.time, "sleep", lambda s: None)
    monkeypatch.setattr(ds, "stop_idle", lambda minutes: [])
    # The reaper's last look finds nothing; a start then runs dsat1 and, finding the
    # reaper's lock still held, spawns none.
    looks = iter([set(), {"dsat1"}])

    def running(timeout=30):
        names = next(looks)
        if not names:
            ds._spawn_reaper()
        return names

    monkeypatch.setattr(ds, "running", running)
    ds.reap(every=0)
    assert len(spawned) == 1


def test_cli_accepts_only_its_actions(fake):
    assert ds.main(["forward"]) == 2 and ds.main(["stop", "sat1"]) == 2
    assert not fake.calls


# Choosing a server: redstone.servers.take_idle/take, and the dsat side of it.

class Laptop(Server):
    pass


class Docker(Server):
    up = True

    def is_up(self):
        return self.up


def _free(path) -> bool:
    with open(path, "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False


@pytest.fixture
def pool(tmp_path):
    d = [Docker(f"dsat{i}", tmp_path / f"dsat{i}", 0, 25675 + i, "1G") for i in (1, 2)]
    lap = [Laptop(f"sat{i}", tmp_path / f"sat{i}", 25565 + i, 25575 + i, "1G") for i in (1, 2)]
    return d, lap


def _hold(server):
    server.dir.mkdir(parents=True, exist_ok=True)
    f = open(server.lock, "w")
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return f


def test_an_idle_dsat_comes_before_an_idle_laptop_satellite(pool):
    from redstone.servers import take_idle
    d, lap = pool
    lock, got = take_idle([*d, *lap])
    assert got is d[0] and not _free(d[0].lock)
    lock.close()


def test_a_busy_dsat_is_passed_over(pool):
    from redstone.servers import take_idle
    d, lap = pool
    held = [_hold(s) for s in d]
    lock, got = take_idle([*d, *lap])
    assert got is lap[0]
    lock.close()
    for h in held:
        h.close()


def test_a_dsat_found_down_after_its_lock_is_won_is_dropped_and_freed(pool):
    from redstone.servers import take_idle
    d, lap = pool
    d[0].up = False
    lock, got = take_idle([*d, *lap])
    assert got is d[1] and _free(d[0].lock)
    lock.close()
    d[1].up = False
    lock, got = take_idle(d, spare=lambda: None)
    assert (lock, got) == (None, None) and _free(d[0].lock) and _free(d[1].lock)


def test_all_busy_asks_for_a_spare_once(pool, tmp_path):
    from redstone.servers import take_idle
    d, lap = pool
    held = [_hold(s) for s in [*d, *lap]]
    spare = Docker("dsat3", tmp_path / "dsat3", 0, 25678, "1G")
    asked = []

    def start_spare():
        asked.append(1)
        return _hold(spare), spare

    lock, got = take_idle([*d, *lap], start_spare)
    assert got is spare and asked == [1]
    lock.close()
    # No spare: waits for the first busy one to come free, without asking again.
    asked.clear()
    import threading
    threading.Timer(0.3, held[2].close).start()
    lock, got = take_idle([*d, *lap], lambda: asked.append(1))
    assert got is lap[0] and asked == [1]
    lock.close()
    for h in held:
        h.close()


def test_nothing_up_and_no_spare_means_main(pool):
    from redstone.servers import take_idle
    assert take_idle([], lambda: None) == (None, None)


def test_a_down_dsat_s_idle_time_survives_being_tried(pool):
    from redstone.servers import take, take_idle
    d, lap = pool
    d[0].up = False
    d[0].dir.mkdir(parents=True)
    d[0].lock.touch()
    os.utime(d[0].lock, (1, 1))
    assert take_idle([d[0]], lambda: None) == (None, None)
    with pytest.raises(RuntimeError):
        take(d[0])
    assert d[0].lock.stat().st_mtime == 1
    d[0].up = True
    lock, got = take_idle([d[0]])
    assert got is d[0] and d[0].lock.stat().st_mtime > time.time() - 60
    lock.close()


def test_a_pinned_server_waits_for_its_lock_then_must_be_up(pool):
    from redstone.servers import take
    d, lap = pool
    lock = take(lap[0])  # a laptop satellite is not asked
    assert not _free(lap[0].lock)
    lock.close()
    d[0].up = False
    with pytest.raises(RuntimeError, match="dsat1 is not up"):
        take(d[0])
    assert _free(d[0].lock)


def test_pinning_accepts_the_dsat_names():
    code = ("import os; os.environ['REDSTONE_SERVER'] = 'dsat2'; import sys; sys.path.insert(0, 'tests'); "
            "import conftest; from redstone.servers import SERVERS; "
            "assert conftest.SERVER == 'dsat2' and SERVERS[conftest.SERVER].rcon_port == 25677")
    subprocess.run([sys.executable, "-c", code], cwd=ds.ROOT.parent, check=True)


@pytest.fixture
def down_file(fake, monkeypatch, tmp_path):
    monkeypatch.setattr(ds, "DOWN_FILE", tmp_path / "dsat_unreachable")
    return ds.DOWN_FILE


def test_available_lists_the_running_dsats(fake, down_file):
    fake.rules[(*D, "ps")] = [(0, b"dsat3\ndsat1\n", b"")]
    assert [s.name for s in ds.available()] == ["dsat1", "dsat3"]
    assert not down_file.exists()


def test_an_unreachable_desktop_is_remembered_across_processes(fake, down_file, monkeypatch):
    fail = (255, b"", b"ssh: Could not resolve hostname desktop.invalid")
    fake.rules.update({(*D, "ps"): [fail], CHECK: [fail], PROBE: [fail]})
    assert ds.available() == [] and down_file.read_text() == HOST
    fake.calls.clear()
    assert ds.available() == [] and ds.start_spare() is None
    assert not fake.calls
    # Another host's failure does not count against this one.
    down_file.write_text("other@host")
    fake.rules[(*D, "ps")] = [(0, b"dsat1\n", b"")]
    assert [s.name for s in ds.available()] == ["dsat1"]
    # An old mark is probed again in the background, not on the test's time.
    down_file.write_text(HOST)
    old = time.time() - ds.DOWN_SECONDS - 1
    os.utime(down_file, (old, old))
    assert ds.available() == []
    ds._rechecking.join(5)
    assert not down_file.exists()
    assert [s.name for s in ds.available()] == ["dsat1"]


def test_a_desktop_still_down_is_marked_again_by_the_background_probe(fake, down_file, monkeypatch):
    fail = (255, b"", b"ssh: connect to host desktop.invalid port 22: Operation timed out")
    fake.rules.update({(*D, "ps"): [fail], CHECK: [fail], PROBE: [fail]})
    down_file.write_text(HOST)
    old = time.time() - ds.DOWN_SECONDS - 1
    os.utime(down_file, (old, old))
    assert ds.available() == [] and ds.start_spare() is None
    ds._rechecking.join(5)
    assert down_file.read_text() == HOST and time.time() - down_file.stat().st_mtime < 5
    fake.calls.clear()
    assert ds.available() == [] and not fake.calls


def test_one_process_probes_an_old_mark_at_a_time(fake, down_file):
    down_file.write_text(HOST)
    old = time.time() - ds.DOWN_SECONDS - 1
    os.utime(down_file, (old, old))
    with open(down_file.parent / f"{down_file.name}.lock", "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        ds._recheck()
    assert not fake.calls and down_file.exists()


def test_no_docker_cli_means_unavailable_not_an_error(fake, down_file, monkeypatch):
    def missing(argv, **kw):
        raise FileNotFoundError(2, "No such file or directory", argv[0])

    monkeypatch.setattr(ds, "run", missing)
    assert ds.available() == [] and ds.start_spare() is None and not ds.reachable()
    assert down_file.read_text() == HOST


def test_no_host_offers_no_dsats_without_running_anything(fake, down_file, monkeypatch):
    monkeypatch.setattr(ds, "HOST", None)
    assert ds.available() == [] and ds.start_spare() is None
    assert not fake.calls


def test_start_spare_starts_the_first_stopped_dsat_whose_lock_is_free(fake, down_file, monkeypatch, tmp_path):
    sats = [ds.DockerSatellite(f"dsat{i}", tmp_path / f"dsat{i}", 0, 25675 + i, "1G") for i in (1, 2, 3)]
    monkeypatch.setattr(ds, "DOCKER_SATELLITES", sats)
    fake.rules[(*D, "ps")] = [(0, b"dsat1\n", b"")]
    started = []
    monkeypatch.setattr(ds.DockerSatellite, "start", lambda self: started.append(self.name))
    held = _hold(sats[1])  # another process is starting dsat2
    lock, got = ds.start_spare()
    assert got is sats[2] and started == ["dsat3"] and not _free(sats[2].lock)
    lock.close()
    held.close()


def test_a_failed_spare_start_releases_its_lock(fake, down_file, monkeypatch, tmp_path):
    sats = [ds.DockerSatellite("dsat1", tmp_path / "dsat1", 0, 25676, "1G")]
    monkeypatch.setattr(ds, "DOCKER_SATELLITES", sats)
    fake.rules[(*D, "ps")] = [(0, b"", b"")]

    def start(self):
        raise TimeoutError("slow")

    monkeypatch.setattr(ds.DockerSatellite, "start", start)
    assert ds.start_spare() is None and _free(sats[0].lock)


def _conftest(monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("conftest_copy", ds.ROOT.parent / "tests" / "conftest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_conftest_offers_dsats_then_laptop_satellites_that_are_up(monkeypatch, pool):
    c = _conftest(monkeypatch)
    d, lap = pool
    monkeypatch.setattr(c.docker_sats, "available", lambda: list(d))
    monkeypatch.setattr(c, "SATELLITES", lap)
    monkeypatch.setattr(c, "_rcon_up", lambda port: port == lap[1].rcon_port)
    seen = {}

    def take_idle(candidates, spare):
        seen["candidates"], seen["spare"] = candidates, spare
        return None, None

    monkeypatch.setattr(c, "take_idle", take_idle)
    assert c._take_satellite() == (None, None)
    assert seen["candidates"] == [*d, lap[1]] and seen["spare"] is c.docker_sats.start_spare


# Live: only when the desktop answers. Uses dsat6, which scripts and tests pick last.
@pytest.fixture(scope="module")
def live():
    if not ds.reachable():
        pytest.skip(f"desktop {ds.HOST or '(no host configured)'} not reachable")
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
    assert build == [*ds.docker_argv("build"), "-t", ds.IMAGE, "-"]
    assert "--no-cache" in commands(no_cache=True)[1]
