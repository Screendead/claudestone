"""Create, start, stop and list the satellite test servers:

    python -m scripts.servers {start,stop,status}

`start` is idempotent: it creates missing satellite directories from the main server's
files and starts any satellite whose RCON is down. The main server is never touched.
"""

import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from redstone import watch
from redstone.harness import _rcon_up, ensure_server
from redstone.rcon import Rcon
from redstone.servers import MAIN, SATELLITES, Server

# The minimum ChunkMap.setServerViewDistance allows.
DISTANCE = 2
GAMERULES = {"advance_time": "false", "advance_weather": "false", "spawn_mobs": "false"}


def properties(sat: Server) -> str:
    text = (MAIN.dir / "server.properties").read_text()
    for key, value in {"server-port": sat.port, "query.port": sat.port, "rcon.port": sat.rcon_port,
                       "view-distance": DISTANCE, "simulation-distance": DISTANCE, "max-players": 1}.items():
        text, n = re.subn(rf"^{re.escape(key)}=.*$", f"{key}={value}", text, flags=re.M)
        assert n == 1, key
    return text


def create(sat: Server) -> None:
    sat.dir.mkdir(parents=True, exist_ok=True)
    # The bundler jar unpacks libraries/ and versions/ next to itself; sharing main's
    # means it finds them already there.
    for name in ("server.jar", "libraries", "versions"):
        link = sat.dir / name
        if not link.exists():
            link.symlink_to(MAIN.dir / name)
    for name in ("eula.txt", "ops.json", "whitelist.json"):
        if not (sat.dir / name).exists() and (MAIN.dir / name).exists():
            shutil.copy(MAIN.dir / name, sat.dir / name)
    (sat.dir / "server.properties").write_text(properties(sat))


def start(sat: Server) -> str:
    create(sat)
    was_up = _rcon_up(sat.rcon_port)
    began = time.time()
    ensure_server(sat)
    r = Rcon(port=sat.rcon_port)
    try:
        for rule, value in GAMERULES.items():
            out = r.cmd(f"gamerule {rule} {value}")
            if "set to" not in out and "already" not in out.lower():
                raise RuntimeError(f"{sat.name} gamerule {rule}: {out}")
    finally:
        r.close()
    return f"{sat.name}: {'already up' if was_up else f'started in {time.time() - began:.0f}s'}"


def stop(sat: Server) -> str:
    if not _rcon_up(sat.rcon_port):
        return f"{sat.name}: down"
    r = Rcon(port=sat.rcon_port)
    try:
        r.cmd("stop")
    except Exception:
        pass  # the server may drop the connection as it shuts down
    deadline = time.time() + 60
    while _rcon_up(sat.rcon_port) and time.time() < deadline:
        time.sleep(0.5)
    return f"{sat.name}: {'stopped' if not _rcon_up(sat.rcon_port) else 'still up'}"


def status(sat: Server) -> str:
    return f"{sat.name}: {'up' if _rcon_up(sat.rcon_port) else 'down'}  rcon {sat.rcon_port}  {sat.dir}"


def main(argv: list[str]) -> None:
    action = {"start": start, "stop": stop, "status": status}[argv[0] if argv else "status"]
    with ThreadPoolExecutor(len(SATELLITES)) as pool:
        for line in pool.map(action, SATELLITES):
            print(line)
    if action is start and _rcon_up(MAIN.rcon_port) and watch.autostart():
        print("watch director started")


if __name__ == "__main__":
    main(sys.argv[1:])
