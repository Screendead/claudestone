"""Rebuild Pepich1851's 4x4x4 RAM cell (CELL.md) as a 2x2x2 array: `ref_pepich1851_cube444`.

    python tools/t8_ref64/cell_to_spec.py [--out PATH]

The cell is CELL.md's four layers, typed in below as written. Cell (i, j, k) sits at
(4i, 4k, 4j) in cell-local axes: i along x (words sideways), j along z (bits of one word),
k up. So word ik is the enable pair hold ik (write enable, dark blue) / nrd ik (read enable,
cyan), and bit jk is the data pair din jk (red) / dout jk (orange).

Drivers: each enable line enters at its +z end the way the next cell along the word would
feed it, through a fixture repeater (delay 1, input +z) on a fixture support, fed by the
line's input block behind it. din jk is a redstone block beside the west end of its line;
dout jk is read at the west end dust.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from redstone.build import Build  # noqa: E402
from redstone.fileformat import Spec, dump, load  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "ref_pepich1851_cube444"
OUT = HERE.parents[1] / "library" / "register" / f"{NAME}.redstone.yaml"

N, E, S, W = (0, 0, -1), (1, 0, 0), (0, 0, 1), (-1, 0, 0)
UP, DOWN = (0, 1, 0), (0, -1, 0)
HDIRS = [N, E, S, W]
HNAME = {N: "north", E: "east", S: "south", W: "west"}

# CELL.md's layers: rows z = 0..3, columns x = 0..3. Repeaters and the comparator are named by
# the side their input is on (Minecraft's `facing`).
KEY = {
    ".": "air", "b": "blue_wool", "c": "cyan_wool", "y": "yellow_wool", "o": "orange_wool",
    "r": "red_wool", "-": "dust",
    "R": "repeater[facing=south,delay=1]",   # enable repeaters, storage: input +z
    "L": "repeater[facing=west,delay=1]",    # lock: input -x
    "C": "comparator[facing=south,mode=subtract]",
}
LAYERS = [
    ["bo.c", "b.yc", "byyc", "...."],   # y=0
    ["R-oR", "-oC-", "-LR-", "b.rc"],   # y=1
    ["....", "o-oo", "....", "rr-r"],   # y=2
    ["....", "-.--", "....", "--.-"],   # y=3
]
CELL = {(x, y, z): KEY[LAYERS[y][z][x]] for y in range(4) for z in range(4) for x in range(4)
        if LAYERS[y][z][x] != "."}
STORE, LOCK, COMP = (2, 1, 2), (1, 1, 2), (2, 1, 1)
DIN_END, DOUT_END = (0, 3, 3), (0, 3, 1)
I = J = K = 2


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def solid(t):
    return t.endswith("_wool") or t == "stone"


def conn(world, p):
    """Minecraft's side/up/none for each side of dust at p."""
    t = lambda q: world.get(q, "air")  # noqa: E731
    above_open = not solid(t(add(p, UP)))
    sides = {}
    for d in HDIRS:
        n = add(p, d)
        tn = t(n)
        c = None
        if above_open and solid(tn) and t(add(n, UP)) == "dust":
            c = "up"
        elif tn == "dust" or tn.startswith("comparator") or (
                tn.startswith("repeater") and (f"facing={HNAME[d]}" in tn or f"facing={HNAME[(-d[0], 0, -d[2])]}" in tn)):
            c = "side"
        elif not solid(tn) and t(add(n, DOWN)) == "dust":
            c = "side"
        sides[d] = c
    if not (sides[N] or sides[S]):
        sides[E], sides[W] = sides[E] or "side", sides[W] or "side"
    if not (sides[E] or sides[W]):
        sides[N], sides[S] = sides[N] or "side", sides[S] or "side"
    return sides


def build(tests):
    world, named = {}, {}
    for i in range(I):
        for j in range(J):
            for k in range(K):
                o = (4 * i + 1, 4 * k, 4 * j)  # x + 1 leaves room for the din drivers
                for p, b in CELL.items():
                    world[add(o, p)] = b
                for part, p in (("s", STORE), ("l", LOCK), ("c", COMP)):
                    named[f"{part}{i}{j}{k}"] = add(o, p)
    inputs, fixtures, outputs = {}, set(), {}
    for i in range(I):
        for k in range(K):
            for line, x in (("hold", 0), ("nrd", 3)):
                rep = (4 * i + 1 + x, 4 * k + 1, 4 * J)
                world[rep] = KEY["R"]
                world[add(rep, DOWN)] = "stone"
                fixtures |= {rep, add(rep, DOWN)}
                inputs[f"{line}{i}{k}"] = add(rep, S)
    for j in range(J):
        for k in range(K):
            end = add((1, 4 * k, 4 * j), DIN_END)
            inputs[f"din{j}{k}"] = add(end, W)
            outputs[f"dout{j}{k}"] = add((1, 4 * k, 4 * j), DOUT_END)
    spec = Spec(NAME, Build(), description=DESCRIPTION, traits=["pistonless", "entityless", "silent", "lightless"])
    for p, b in world.items():
        if b == "dust":
            s = conn(world, p)
            b = "redstone_wire[" + ",".join(f"{HNAME[d]}={s[d] or 'none'}" for d in HDIRS) + "]"
        spec.build.place(p, b)
    spec.fixtures = fixtures
    spec.inputs = dict(sorted(inputs.items()))
    spec.named = dict(sorted(named.items())) | dict(sorted(outputs.items()))
    spec.outputs = dict(sorted(outputs.items()))
    spec.tests = tests
    return spec


DESCRIPTION = (
    "Rebuilt reference: Pepich1851's \"4^3 tileable memory cell\" (YouTube, 2018-05-21; source and timestamps in "
    "tools/t8_ref64/SOURCE.md), the community 64-blocks-per-bit RAM cell, read block by block from the video into "
    "tools/t8_ref64/CELL.md and tiled here by tools/t8_ref64/cell_to_spec.py into a 2x2x2 array (8 cells). In each "
    "cell s is the storage repeater, locked from its side by l, and c a subtract comparator that reads s from behind "
    "and the read-enable line from its side. Words run along z (bits j), words sideways along x (i), layers up y (k): "
    "word ik is hold ik (write enable, dark blue wool) and nrd ik (read enable, cyan); bit jk is din jk (red, along x) "
    "and dout jk (orange, along x, read at its west end). Both enables are inverted: hold 1 keeps and 0 writes; nrd 1 "
    "keeps the word off dout (15 - 14 = 1, which dies before the line) and 0 reads it. Each enable line enters at its "
    "south end through a fixture repeater standing where the next cell's repeater would be. Not built: the repeaters "
    "a long data line needs, which the video leaves to the user.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out)
    tests = load(out).tests if out.exists() else []
    Path(args.out).write_text(dump(build(tests)))


if __name__ == "__main__":
    main()
