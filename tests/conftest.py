import fcntl
import json
import os

import pytest

from redstone import docker_sats, fileformat, showroom, watch
from redstone.harness import Rig, _rcon_up, ensure_server, mirror
from redstone.plots import MAIN as MAIN_PLOT, PLOTS, plot_for
from redstone.rcon import Rcon
from redstone.servers import MAIN, PLOT_RECORDS, SATELLITES, SERVERS, take, take_idle

# "auto": a plot other than main runs on the first idle Docker satellite, else laptop
# satellite, else one more Docker satellite started for it, else waits for a busy
# satellite; main only if no satellite is up or startable. "main" or a satellite's name
# (sat1, dsat1, ...) pins every test to that server.
SERVER = os.environ.get("REDSTONE_SERVER", "auto")


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


def _take_satellite():
    """The held lock file of a satellite for this test, and that satellite."""
    return take_idle(docker_sats.available() + [s for s in SATELLITES if _rcon_up(s.rcon_port)],
                     docker_sats.start_spare)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # The rig fixture's teardown reads the call phase's outcome from the item.
    rep = yield
    setattr(item, f"rep_{rep.when}", rep)
    return rep


def _plot(request):
    """$REDSTONE_PLOT, else main, unless the library build under test does not fit main."""
    if "REDSTONE_PLOT" in os.environ:
        return PLOTS[os.environ["REDSTONE_PLOT"]]
    path = getattr(request.node, "callspec", None) and request.node.callspec.params.get("path")
    build = fileformat.load(path).build if path else None
    if build and build.blocks:
        lo, hi = build.bounds()
        if any(a < 0 or b >= s for a, b, s in zip(lo, hi, MAIN_PLOT.size)):
            return plot_for(path) or MAIN_PLOT
    return MAIN_PLOT


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
        (PLOT_RECORDS / f"{plot.name}.json").write_text(json.dumps({"server": server.name}))
        try:
            r = connect(server)
        except Exception:
            lock.close()
            raise
        rig = None
        try:
            rig = Rig(r, plot.origin, plot.size, plot.name, server=server, display=connect(MAIN))
            yield rig
        finally:
            # Tests freeze the world; let it run again for anyone watching.
            try:
                if rig is not None:
                    rig.release()
                else:
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
                          {"test": tested["test"], "passed": rep.passed, "delay": tested["delay"]},
                          full=server == MAIN)
