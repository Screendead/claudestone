"""The test servers. Tick freeze, step and rate are global to a server, so each server
runs one test at a time; satellites let tests in different plots run at once.

`main` is the world players join. Satellites are headless copies of its settings with
their own worlds, generated from the same flat preset so plot coordinates mean the same
place; a satellite keeps only the plot under test loaded.
"""

import re
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
