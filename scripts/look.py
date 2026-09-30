"""Compact views of a test or the world.

    python -m scripts.look trace <spec> "<test>" [--cells a,b,out] [--from T --to T] [--levels]

--levels shows a comparator's output strength (0-15) instead of 0/1; only dense traces
(try --trace) record it.
    python -m scripts.look world <plot> [--y N] [--server NAME] [--spec NAME]
"""

import argparse
import json
import re
import sys
from pathlib import Path

from redstone import fileformat, library
from redstone.build import namespaced
from redstone.servers import PLOT_RECORDS, SERVERS
from redstone.plots import PLOTS
from redstone.rcon import Rcon
from redstone.spec import TRACE_DIR

MAX_ROWS = 60


def trace_table(spec_name: str, test: str, cells=None, lo=0, hi=10**9, levels=False) -> str:
    path = TRACE_DIR / spec_name / f"{test}.json"
    if not path.exists():
        return f"no trace for {spec_name} / {test!r}: run python -m scripts.try {spec_name} first"
    data = json.loads(path.read_text())
    names = {}  # "x,y,z" -> cell name
    inputs = []
    if data["spec"]:
        s = fileformat.load(data["spec"])
        names = {",".join(map(str, p)): n for n, p in s.named.items()}
        inputs = list(s.inputs)
    cols = list(cells) if cells else inputs + list(names.values())
    keys = {n: k for k, n in names.items()}
    drive = dict.fromkeys(inputs, 0)
    prev, rows = None, []
    for f in data["frames"]:
        for n, v in re.findall(r"(\w+)=([01])", f["event"] if f["event"].startswith("drive") else ""):
            drive[n] = int(v)
        shown = f["signals"] | f.get("levels", {}) if levels else f["signals"]
        vals = [drive[c] if c in drive else shown.get(keys.get(c, c), 0) for c in cols]
        if vals != prev and lo <= f["tick"] <= hi:
            rows.append([str(f["tick"]), *map(str, vals), f["event"]])
        prev = vals
    note = ("\n(sparse trace: rerun with --trace for every tick" + (" and comparator levels)" if levels else ")")
            if data.get("sparse") else "")
    if not rows:
        return "no changes in range" + note
    table = [["tick", *cols, "event"]] + rows[:MAX_ROWS]
    w = [max(len(r[i]) for r in table) for i in range(len(cols) + 1)]
    out = ["  ".join(c.rjust(w[i]) for i, c in enumerate(r[:-1])) + "  " + r[-1] for r in table]
    if len(rows) > MAX_ROWS:
        out.append(f"... {len(rows) - MAX_ROWS} more rows")
    return "\n".join(out).rstrip() + note


# Ids probed in this order; the first hit names a cell. Unlisted blocks show as ?.
COMMON = ("smooth_stone white_concrete stone redstone_wire repeater redstone_torch redstone_wall_torch "
          "redstone_block redstone_lamp comparator lever stone_button polished_blackstone_button observer "
          "piston sticky_piston hopper dropper dispenser target slime_block honey_block glass "
          "stone_bricks cobblestone white_wool obsidian iron_block note_block rail powered_rail detector_rail "
          "activator_rail tripwire_hook tripwire ladder oak_planks oak_button oak_pressure_plate "
          "stone_pressure_plate light_weighted_pressure_plate heavy_weighted_pressure_plate daylight_detector "
          "trapped_chest chest barrel copper_bulb sculk_sensor lightning_rod oak_door iron_door oak_trapdoor "
          "white_carpet grass_block dirt").split()
FACING = ("repeater comparator redstone_wall_torch observer piston sticky_piston hopper dropper dispenser "
          "lever stone_button polished_blackstone_button").split()
FACES = ("wall", "floor", "ceiling")
DIRS = ("north", "south", "east", "west")
SPARE = iter("ABCDEFGHIJKMNOPQSTUVWXYZbcdefghijklmpqrstwxyz0123456789")


def connect(server: str | None, plot: str) -> Rcon:
    if server is None:
        pinned = PLOT_RECORDS / f"{plot}.json"
        server = json.loads(pinned.read_text())["server"] if pinned.exists() else "main"
    if server not in SERVERS:
        raise SystemExit(f"unknown server {server!r}; one of {', '.join(SERVERS)}")
    return Rcon(port=SERVERS[server].rcon_port)


def yes(r: Rcon, cmd: str) -> bool:
    return "passed" in r.cmd(cmd)


def occupied(r: Rcon, origin, size, y_only=None):
    """Non-air cells of a plot by narrowing: y layers (in bands under the 32768-block
    compare limit), then rows, then cells, each against an air region high above."""
    ox, oy, oz = origin
    sx, sy, sz = size
    r.cmd(f"forceload add {ox} {oz} {ox + sx - 1} {oz + sz - 1}")
    sky = oy + 128
    band = max(1, 32768 // sx)
    cells = []
    for y in ([y_only] if y_only is not None else range(sy)):
        for z0 in range(0, sz, band):
            z1 = min(z0 + band, sz) - 1
            if yes(r, f"execute if blocks {ox} {oy + y} {oz + z0} {ox + sx - 1} {oy + y} {oz + z1} {ox} {sky} {oz + z0} all"):
                continue
            for z in range(z0, z1 + 1):
                if yes(r, f"execute if blocks {ox} {oy + y} {oz + z} {ox + sx - 1} {oy + y} {oz + z} {ox} {sky} {oz + z} all"):
                    continue
                for x in range(sx):
                    if not yes(r, f"execute if block {ox + x} {oy + y} {oz + z} air"):
                        cells.append((x, y, z))
    return cells


def block_at(r: Rcon, pos, hint: list[str]) -> str:
    ids = hint + [b for b in COMMON if b not in hint]
    for b in ids:
        if yes(r, f"execute if block {pos} {b}"):
            if b in FACING:
                for d in DIRS:
                    if yes(r, f"execute if block {pos} {b}[facing={d}]"):
                        return f"{b}[facing={d}]"
            return b
    return "?"


def world(plot: str, y=None, server=None, spec_name=None) -> str:
    p = PLOTS[plot]
    r = connect(server, plot)
    glyphs = {"air": "."} | {k.removeprefix("minecraft:"): g for k, g in fileformat.GLYPHS.items()}
    hint = []
    if spec_name:
        path = library.path_of(spec_name)
        import yaml
        for g, e in yaml.safe_load(path.read_text())["palette"].items():
            block = e if isinstance(e, str) else e.get("block")
            if block:
                glyphs.setdefault(namespaced(block).removeprefix("minecraft:"), str(g))
                hint.append(namespaced(block).removeprefix("minecraft:").split("[")[0])
    cells = occupied(r, p.origin, p.size, y)
    if not cells:
        return f"{plot}: empty" + ("" if y is None else f" at y={y}")
    ox, oy, oz = p.origin
    found = {c: block_at(r, f"{ox + c[0]} {oy + c[1]} {oz + c[2]}", list(dict.fromkeys(hint))) for c in cells}
    r.close()
    for state in dict.fromkeys(found.values()):
        if state not in glyphs and state.split("[")[0] in glyphs:
            glyphs[state] = glyphs[state.split("[")[0]]  # spec glyph for the bare id
        elif state not in glyphs:
            glyphs[state] = "?" if state == "?" else next(g for g in SPARE if g not in glyphs.values())
    xs, zs = [c[0] for c in cells], [c[2] for c in cells]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    out = ["  ".join(f"{glyphs[s]}={s}" for s in dict.fromkeys(found.values())) + f"   origin {ox},{oy},{oz} x{x0}..{x1} z{z0}..{z1}"]
    for yy in sorted({c[1] for c in cells}):
        out.append(f"y={yy}")
        out += ["".join(glyphs[found[(x, yy, z)]] if (x, yy, z) in found else "." for x in range(x0, x1 + 1))
                for z in range(z0, z1 + 1)]
    return "\n".join(out)


def main(argv):
    ap = argparse.ArgumentParser(prog="look")
    sub = ap.add_subparsers(dest="mode", required=True)
    t = sub.add_parser("trace")
    t.add_argument("spec")
    t.add_argument("test")
    t.add_argument("--cells")
    t.add_argument("--from", dest="lo", type=int, default=0)
    t.add_argument("--to", dest="hi", type=int, default=10**9)
    t.add_argument("--levels", action="store_true", help="comparator output strength instead of 0/1")
    w = sub.add_parser("world")
    w.add_argument("plot")
    w.add_argument("--y", type=int)
    w.add_argument("--server")
    w.add_argument("--spec")
    a = ap.parse_args(argv)
    if a.mode == "trace":
        print(trace_table(a.spec, a.test, a.cells.split(",") if a.cells else None, a.lo, a.hi, a.levels))
    else:
        print(world(a.plot, a.y, a.server, a.spec))


if __name__ == "__main__":
    main(sys.argv[1:])
