"""Create, start, stop and list the satellite test servers:

    python -m scripts.servers {start,stop,status,idle} [laptop|docker|all]

`laptop` is sat1..sat6, `docker` dsat1..dsat6 on the desktop (redstone/docker_sats.py);
start and stop default to laptop, status to all. `start` is idempotent: it creates
missing satellite directories from the main server's files and starts any satellite
whose RCON is down. The main server is never touched. `idle` stops the dsats unused for
docker_sats.IDLE_MINUTES.
"""

import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from redstone import docker_sats, watch
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


ACTIONS = {"start": start, "stop": stop, "status": status}
KINDS = ("laptop", "docker", "all")


def main(argv: list[str]) -> None:
    name = argv[0] if argv else "status"
    which = argv[1] if len(argv) > 1 else "all" if name == "status" else "laptop"
    if name not in (*ACTIONS, "idle") or which not in KINDS:
        raise SystemExit(f"usage: python -m scripts.servers {{{','.join(ACTIONS)},idle}} [{'|'.join(KINDS)}]")
    if name == "idle":
        print("\n".join(docker_sats.stop_idle()) or "no idle docker satellites")
        return
    jobs = []
    if which in ("laptop", "all"):
        jobs += [lambda sat=sat: ACTIONS[name](sat) for sat in SATELLITES]
    if which in ("docker", "all"):
        if docker_sats.HOST is None:
            print("docker: no host (REDSTONE_DOCKER_HOST or server/docker_host)")
        elif docker_sats.reachable():
            jobs += [getattr(sat, name) for sat in docker_sats.DOCKER_SATELLITES]
        else:
            print("docker: desktop unreachable")
    with ThreadPoolExecutor(max(1, len(jobs))) as pool:
        for line in pool.map(lambda job: job(), jobs):
            print(line)
    if name == "start" and which != "docker" and _rcon_up(MAIN.rcon_port) and watch.autostart():
        print("watch director started")


if __name__ == "__main__":
    main(sys.argv[1:])
