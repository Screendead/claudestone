"""Render a library spec's blocks as a 3D voxel picture (matplotlib, no server).

    python tools/render_spec_voxels.py <spec> <out.png> [--elev 25 --azim -60] [--box x0,y0,z0,x1,y1,z1]

Repeaters named s*/k*/o* (the RAM cell's memory, lock and read repeaters) get their own colours;
--box keeps only the blocks inside an inclusive range, to show one cell.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from redstone.fileformat import load  # noqa: E402
from redstone.library import path_of  # noqa: E402

COLOURS = {"smooth_stone": (0.62, 0.62, 0.62, 0.55), "glass": (0.75, 0.9, 1.0, 0.18),
           "redstone_wire": (0.85, 0.05, 0.05, 0.95), "repeater": (0.95, 0.6, 0.2, 1.0),
           "s": (0.15, 0.35, 0.95, 1.0), "k": (0.6, 0.2, 0.8, 1.0), "o": (0.1, 0.75, 0.3, 1.0),
           "input": (1.0, 0.85, 0.0, 1.0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--elev", type=float, default=25)
    ap.add_argument("--azim", type=float, default=-60)
    ap.add_argument("--box")
    ap.add_argument("--title", default="")
    args = ap.parse_args()
    spec = load(path_of(args.spec))
    kind = {p: s.removeprefix("minecraft:").split("[")[0] for p, s in spec.build.blocks.items()}
    for name, p in spec.named.items():
        if name[0] in "sko" and kind.get(p) == "repeater":
            kind[p] = name[0]
    for name in spec.inputs:
        for p in spec.input_cells(name):
            kind[p] = "input"
    if args.box:
        x0, y0, z0, x1, y1, z1 = map(int, args.box.split(","))
        kind = {p: k for p, k in kind.items() if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and z0 <= p[2] <= z1}
    lo = [min(p[a] for p in kind) for a in range(3)]
    hi = [max(p[a] for p in kind) for a in range(3)]
    # matplotlib axes: X = x east, Y = z south (flipped so north is at the back), Z = y up
    shape = (hi[0] - lo[0] + 1, hi[2] - lo[2] + 1, hi[1] - lo[1] + 1)
    filled = np.zeros(shape, bool)
    colours = np.zeros(shape + (4,))
    for (x, y, z), k in kind.items():
        i = (x - lo[0], hi[2] - z, y - lo[1])
        filled[i] = k in COLOURS
        colours[i] = COLOURS.get(k, (0, 0, 0, 0))
    fig = plt.figure(figsize=(9, 8), dpi=130)
    ax = fig.add_subplot(projection="3d")
    ax.voxels(filled, facecolors=colours, edgecolor=(0, 0, 0, 0.12), linewidth=0.3)
    ax.set_box_aspect(shape)
    ax.view_init(elev=args.elev, azim=args.azim)
    ax.set_xlabel("x (east)")
    ax.set_ylabel("north ← z → south")
    ax.set_zlabel("y (up)")
    ax.set_yticks([])
    if args.title:
        ax.set_title(args.title)
    fig.tight_layout()
    fig.savefig(args.out)


if __name__ == "__main__":
    main()
