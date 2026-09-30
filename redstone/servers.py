"""The test servers. Tick freeze, step and rate are global to a server, so each server
runs one test at a time; satellites let tests in different plots run at once.

`main` is the world players join. Satellites are headless copies of its settings with
their own worlds, generated from the same flat preset so plot coordinates mean the same
place; a satellite keeps only the plot under test loaded.

dsat1..dsat6 are satellites in Docker on the desktop, reached over SSH;
redstone/docker_sats.py adds them to SERVERS when imported.
"""

import fcntl
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "server"


@dataclass(frozen=True)
class Server:
    name: str
    dir: Path
    port: int
    rcon_port: int
    memory: str  # -Xmx value

    @property
    def lock(self) -> Path:
        return self.dir / "rig.lock"

    def level_name(self) -> str:
        props = (self.dir / "server.properties").read_text()
        return re.search(r"^level-name=(.*)$", props, re.M).group(1)


MAIN = Server("main", ROOT, 25565, 25575, "2G")
SATELLITES = [Server(f"sat{i}", ROOT / "satellites" / f"sat{i}", 25565 + i, 25575 + i, "1G")
              for i in range(1, 7)]
SERVERS = {s.name: s for s in [MAIN, *SATELLITES]}

# Where the last run of each plot happened: server/plots/<plot>.json = {"server": name}.
PLOT_RECORDS = ROOT / "plots"


def take_idle(candidates: list[Server], spare=lambda: None):
    """The held rig.lock and the server of the first idle candidate, else of spare()
    (asked once), else of the first candidate to come free: (None, None) when there are
    none. A candidate with is_up() was listed without asking it (a busy server can't
    answer in time), so it is asked once its lock is won, and dropped if down."""
    up = list(candidates)
    asked_spare = False
    while True:
        for server in list(up):
            server.dir.mkdir(parents=True, exist_ok=True)
            lock = open(server.lock, "a")  # "w" would refresh the mtime the dsat reaper reads as use
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                lock.close()
                continue
            if hasattr(server, "is_up") and not server.is_up():
                lock.close()
                up.remove(server)
                continue
            os.utime(server.lock)
            return lock, server
        if not asked_spare:
            asked_spare = True
            got = spare()
            if got:
                return got
        if not up:
            return None, None
        time.sleep(0.1)


def take(server: Server):
    """Wait for server's rig.lock and return it held. Raises RuntimeError, lock released,
    if the server has is_up() and is down: checked after the lock, which the dsat reaper
    holds while it stops one."""
    server.dir.mkdir(parents=True, exist_ok=True)
    lock = open(server.lock, "a")
    fcntl.flock(lock, fcntl.LOCK_EX)
    if hasattr(server, "is_up") and not server.is_up():
        lock.close()
        raise RuntimeError(f"{server.name} is not up; python -m redstone.docker_sats start {server.name}")
    os.utime(server.lock)
    return lock
