import fcntl
import json
import os

import pytest

from redstone import docker_sats, remote, showroom, watch
from redstone.harness import Rig, _rcon_up, ensure_server, mirror
from redstone.plots import MAIN as MAIN_PLOT, PLOTS, plot_for
from redstone.rcon import Rcon
from redstone.servers import MAIN, PLOT_RECORDS, SATELLITES, SERVERS, answers, take, take_idle

# "auto": a plot other than main runs on the first idle Docker satellite, else laptop
# satellite, else one more Docker satellite started for it, else waits for a busy
# satellite; main only if no satellite is up or startable. "main" or a satellite's name
# (sat1, dsat1, ...) pins every test to that server.
SERVER = os.environ.get("REDSTONE_SERVER", "auto")
# Who is testing (a workflow id, say): kept in the plot record and the showroom entry, and
# shown on the plot's status sign.
OWNER = os.environ.get("REDSTONE_OWNER") or None


@pytest.fixture(scope="session")
def connect():
    opened: dict[str, Rcon] = {}

    def get(server):
        if server.name in opened and hasattr(server, "is_up"):
            # A dsat may have been stopped by the reaper and restarted since.
            try:
                opened[server.name].cmd("time query gametime")
            except Exception:
                opened.pop(server.name).close()
        if server.name not in opened:
            # Laptop satellites are started by scripts.servers only.
            if server == MAIN:
                ensure_server(server)
            elif hasattr(server, "is_up") and not server.is_up():  # also restores its forward
                raise RuntimeError(f"{server.name} is not up")
            opened[server.name] = Rcon(port=server.rcon_port)
        return opened[server.name]

    yield get
    for r in opened.values():
        r.close()


@pytest.fixture(scope="session")
def rcon(connect):
    return connect(MAIN)


def _in_container(server) -> bool:
    """Whether the test runs in the server's container (redstone.remote): over the SSH
    forward every command is a round trip to the desktop."""
    return remote.ENABLED and isinstance(server, docker_sats.DockerSatellite)


def _take_satellite():
    """The held lock file of a satellite for this test, and that satellite. A dsat listed
    as running needs no RCON check (~0.15 s) when the test runs in its container: it
    waits there for a server still starting."""
    return take_idle(docker_sats.available() + [s for s in SATELLITES if _rcon_up(s.rcon_port)],
                     docker_sats.start_spare, ready=lambda s: _in_container(s) or answers(s))


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # The rig fixture's teardown reads the call phase's outcome from the item.
    rep = yield
    setattr(item, f"rep_{rep.when}", rep)
    return rep


def _plot(request):
    """$REDSTONE_PLOT, else the plot of the library file under test, else main."""
    if "REDSTONE_PLOT" in os.environ:
        return PLOTS[os.environ["REDSTONE_PLOT"]]
    path = getattr(request.node, "callspec", None) and request.node.callspec.params.get("path")
    return (plot_for(path) if path else None) or MAIN_PLOT


@pytest.fixture
def rig(connect, request):
    plot = _plot(request)
    PLOT_RECORDS.mkdir(exist_ok=True)
    # Two runs of one plot would both mirror into, and sign on, the same place in main.
    with open(PLOT_RECORDS / f"{plot.name}.lock", "w") as plot_lock:
        fcntl.flock(plot_lock, fcntl.LOCK_EX)
        lock, server = None, None
        if SERVER == "auto" and plot.name != MAIN_PLOT.name:
            lock, server = _take_satellite()
        if lock is None:
            # The tick clock, tick rate and test data pack are global to a server, so one
            # test at a time runs on it, whatever its plot; other runs wait here.
            server = MAIN if SERVER == "auto" else SERVERS[SERVER]
            try:
                lock = take(server)
            except RuntimeError as e:
                pytest.fail(str(e))
        record = {"server": server.name} | ({"owner": OWNER} if OWNER else {})
        (PLOT_RECORDS / f"{plot.name}.json").write_text(json.dumps(record))
        in_container = _in_container(server)
        try:
            r = None if in_container else connect(server)
        except Exception:
            lock.close()
            raise
        rig = None
        try:
            if in_container:
                rig = remote.RemoteRig(server, plot, connect(MAIN), lambda: connect(server))
            else:
                rig = Rig(r, plot.origin, plot.size, plot.name, server=server, display=connect(MAIN))
            rig.owner = OWNER
            yield rig
        finally:
            # Tests freeze the world; let it run again for anyone watching.
            try:
                if rig is not None:
                    rig.release()
                elif r is not None:
                    r.cmd("tick unfreeze")
            finally:
                os.utime(lock.name)  # a dsat's idle time counts from the end of use
                lock.close()
        # Players watch main, so a satellite's build is placed there too, where it runs
        # live. Plain commands only, so this needs no lock on main. In any other plot the
        # build joins the plot's showroom beside the family's other variants; a test run on
        # main itself cleared that plot, so the whole showroom is redrawn.
        if not rig.loaded.blocks:
            return
        if plot.name == MAIN_PLOT.name:
            if server != MAIN:
                mirror(connect(MAIN), plot.origin, plot.size, rig.loaded)
                watch.emit("mirror", plot=plot.name, server=server.name,
                           spec=getattr(rig, "tested", {}).get("spec", None) and rig.tested["spec"].name,
                           box=watch.world_box(plot.origin, rig.loaded))
            return
        tested = getattr(rig, "tested", None)
        rep = getattr(request.node, "rep_call", None)
        if tested and rep:
            # The spec's own build, not rig.loaded: a tile test loads two copies.
            showroom.show(connect(MAIN), plot.name, tested["spec"], tested["spec"].build,
                          {"test": tested["test"], "passed": rep.passed, "delay": tested["delay"], "owner": OWNER},
                          full=server == MAIN)
