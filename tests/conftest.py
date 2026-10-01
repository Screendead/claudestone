import contextlib
import fcntl
import json
import os

import pytest

from redstone import docker_sats, remote, showroom, watch
from redstone.harness import Rig, _rcon_up, ensure_server, mirror
from redstone.plots import MAIN as MAIN_PLOT, PLOTS, plot_for
from redstone.rcon import Rcon
from redstone.servers import (MAIN, PLOT_RECORDS, SATELLITES, answers, holds_plot_lock, pinned, plot_lock, take,
                              take_idle)

# "auto": a plot other than main runs on the first idle Docker satellite, else laptop
# satellite, else one more Docker satellite started for it, else waits for a busy
# satellite; main only if no satellite is up or startable. "main" or a satellite's name
# (sat1, dsat1, ...) pins every test to that server; a list (sat1,sat6) to the first idle
# one of those.
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


def _locked(path):
    f = open(path, "w")
    fcntl.flock(f, fcntl.LOCK_EX)
    return f


def _record(plot, server) -> None:
    record = {"server": server.name} | ({"owner": OWNER} if OWNER else {})
    tmp = PLOT_RECORDS / f".{plot.name}.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(record))
    tmp.replace(PLOT_RECORDS / f"{plot.name}.json")


@pytest.fixture
def rig(connect, request):
    plot = _plot(request)
    PLOT_RECORDS.mkdir(exist_ok=True)
    allowed = pinned(SERVER)
    # Each satellite is its own world, so runs of one plot on different satellites go at
    # once. A run that builds in main's copy of the plot (one on main, or of the main plot)
    # holds the plot lock throughout, taken before the rig.lock; no one waits for a plot
    # lock while holding a rig.lock.
    whole, lock, server = None, None, None
    if allowed is None and plot.name != MAIN_PLOT.name:
        lock, server = _take_satellite()
    if lock is None:
        candidates = allowed or [MAIN]
        if holds_plot_lock(plot.name, candidates):
            whole = _locked(plot_lock(plot.name))
        try:
            if len(candidates) == 1:
                server = candidates[0]
                lock = take(server)
            else:
                lock, server = take_idle(candidates, ready=lambda s: _in_container(s) or answers(s))
                if lock is None:
                    raise RuntimeError(f"none of {SERVER} is up")
        except RuntimeError as e:
            if whole:
                whole.close()
            pytest.fail(str(e))
    running = whole or _locked(plot_lock(plot.name, server))  # for scripts.status
    try:
        yield from _run(connect, request, plot, server, lock, whole, running)
    finally:
        running.close()


def _run(connect, request, plot, server, lock, whole, running):
    """The rig fixture's body once a server is held: test, then showroom or mirror."""
    _record(plot, server)
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
            if running is not whole:
                running.close()
    if not rig.loaded.blocks:
        return
    # A run on main (holding the plot lock) clears the plot's showroom there, so a
    # satellite's run takes the lock to place its slot; so do two satellites at once.
    with (contextlib.nullcontext() if whole else _locked(plot_lock(plot.name))):
        _show(connect, request, plot, server, rig)


def _show(connect, request, plot, server, rig):
    # Players watch main, so a satellite's build is placed there too, where it runs
    # live. Plain commands only, so this needs no lock on main. In any other plot the
    # build joins the plot's showroom beside the family's other variants; a test run on
    # main itself cleared that plot, so the whole showroom is redrawn.
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
