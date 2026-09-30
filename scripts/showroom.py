"""Redraw plot showrooms on main from server/showroom/<plot>.json and the library files.

    python -m scripts.showroom rebuild [<plot>]
"""

import argparse
import fcntl
import sys

from redstone import showroom
from redstone.harness import ensure_server
from redstone.plots import PLOTS
from redstone.rcon import Rcon
from redstone.servers import PLOT_RECORDS


def rebuild(r: Rcon, plot: str) -> None:
    PLOT_RECORDS.mkdir(exist_ok=True)
    with open(PLOT_RECORDS / f"{plot}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = showroom.load_state(plot)
        showroom.redraw(r, plot, state)
        showroom.save_state(plot, state)
    print(f"{plot}: {', '.join(sorted(state['specs'])) or 'empty'}")


def main(argv) -> int:
    ap = argparse.ArgumentParser(prog="showroom")
    ap.add_argument("command", choices=["rebuild"])
    ap.add_argument("plot", nargs="?")
    a = ap.parse_args(argv)
    plots = [a.plot] if a.plot else sorted(p.stem for p in showroom.STATE.glob("*.json"))
    for p in plots:
        if p not in PLOTS or p == "main":
            print(f"{p}: not a showroom plot")
            return 1
    ensure_server()
    r = Rcon()
    for p in plots:
        rebuild(r, p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
