"""The camera director on main (redstone/watch.py):

    python -m scripts.watch run [options]     # in the foreground
    python -m scripts.watch start [options]   # in the background, saving the options
        --orbit|--no-orbit    move during a shot, or hold still
        --motion dolly|orbit  slide sideways, or swing round the build
        --camera entity|tp    spectate a gliding entity, or teleport the players
        --glide TICKS         the camera's teleport_duration: longer is smoother and lags more
        --dwell S  --rate HZ
    python -m scripts.watch stop       # stays off until `start`, even when tests run
    python -m scripts.watch status
    python -m scripts.watch off [player...]   # opt out; restores the previous gamemode
    python -m scripts.watch on [player...]    # opt back in

The harness starts the director by itself whenever it uses main (`REDSTONE_WATCH=0` stops
that for one process). `start` options are saved to server/watch/config.json. Players
default to everyone online.
"""

import argparse
import os
import signal
import sys
import time

from redstone import watch
from redstone.harness import _rcon_up
from redstone.rcon import Rcon
from redstone.servers import MAIN


def _options(ap):
    ap.add_argument("--orbit", action=argparse.BooleanOptionalAction, default=None)
    ap.add_argument("--motion", choices=["dolly", "orbit"])
    ap.add_argument("--camera", choices=["entity", "tp"])
    ap.add_argument("--glide", type=int)
    ap.add_argument("--dwell", type=float)
    ap.add_argument("--rate", type=float)


def _changes(a) -> dict:
    return {k: getattr(a, k) for k in ("orbit", "motion", "camera", "glide", "dwell", "rate") if getattr(a, k) is not None}


def _players(r: Rcon, names: list[str]) -> tuple[list[str], list[str]]:
    """The named players (default: everyone online), and which of them are online."""
    on = watch.online(r)
    names = names or on
    return names, [n for n in names if n in on]


def opt(names: list[str], out: bool) -> None:
    if not _rcon_up(MAIN.rcon_port):
        if not names:
            sys.exit("main is down: name the players")
        with watch.State() as state:
            for n in names:
                if out and n not in state["optout"]:
                    state["optout"].append(n)
                if not out and n in state["optout"]:
                    state["optout"].remove(n)
        print(f"{'opted out' if out else 'opted in'} {', '.join(names)}; applied when they join")
        return
    r = Rcon(port=MAIN.rcon_port)
    try:
        names, present = _players(r, names)
        with watch.State() as state:
            for n in names:
                if out and n not in state["optout"]:
                    state["optout"].append(n)
                if not out and n in state["optout"]:
                    state["optout"].remove(n)
            watch.reconcile(r, present, state, watch.default_gamemode())
    finally:
        r.close()
    later = sorted(set(names) - set(present))
    print(f"{'opted out' if out else 'watching'}: {', '.join(names) or 'nobody online'}"
          + (f" ({', '.join(later)} when they join)" if later else ""))
    if not out and not watch.running():
        print("the director is not running: python -m scripts.watch start")


def stop() -> None:
    watch.save_config({"enabled": False})
    try:
        os.kill(int(watch.PID.read_text()), signal.SIGTERM)
    except (OSError, ValueError):
        pass
    deadline = time.time() + 10
    while watch.running() and time.time() < deadline:
        time.sleep(0.2)
    print("stopped" if not watch.running() else "still running")


def status() -> None:
    cfg = watch.load_config()
    pid = watch.PID.read_text().strip() if watch.PID.exists() else "?"
    print(f"director: {'running (pid ' + pid + ')' if watch.running() else 'not running'}"
          f"{'' if cfg['enabled'] else ', off until `start`'}")
    print("config: " + ", ".join(f"{k}={v}" for k, v in cfg.items() if k != "enabled"))
    with watch.State() as state:
        print(f"opted out: {', '.join(state['optout']) or 'nobody'}")
        print(f"put in spectator (gamemode to restore): "
              f"{', '.join(f'{p} ({m})' for p, m in state['gamemode'].items()) or 'nobody'}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="watch")
    sub = ap.add_subparsers(dest="action", required=True)
    _options(sub.add_parser("run"))
    _options(sub.add_parser("start"))
    sub.add_parser("stop")
    sub.add_parser("status")
    for name in ("on", "off"):
        sub.add_parser(name).add_argument("players", nargs="*")
    a = ap.parse_args(argv)
    if a.action == "run":
        return watch.run(_changes(a))
    if a.action == "start":
        watch.save_config({"enabled": True, **_changes(a)})
        started = watch.autostart(force=True)
        print("started" if started else "already running" if watch.running() else "did not start; see "
              + str(watch.LOG))
    elif a.action == "stop":
        stop()
    elif a.action == "status":
        status()
    else:
        opt(a.players, a.action == "off")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
