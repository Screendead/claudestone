"""Turn a box-lattice RAM cell from the T8 floor search into a 3x3x2 `.redstone.yaml` array.

    python tools/t8_cell_to_spec.py <found.jsonl> <name> [--line N] [--tests-from SPEC] [--out PATH]

The cell is one line of the search's output (`lat`, `S`/`K`/`O` offsets, `u`/`w` line
directions, raw `types` in index order x + a*(y + c*z) for a box basis (a,0,0),(0,c,0),(0,0,f)).
Types follow the search model: sol (conductor), gls (sturdy, non-conducting), dust, air, and
rN/rE/rS/rW repeaters whose letter is the input side (Minecraft's `facing`).

Cell (i, j, k) is the lattice point i*u + j*w + k*t, t the third basis vector: i runs along the
data lines, j along the control lines, k across planes. So hold/rd ik address a word, din/dout
jk a bit, as in t8_c_v51. Each cell's box is shifted so its S, K, O, their input and output
blocks and the line dust they touch lie inside it; the array is the union of the 18 boxes,
with dust kept only where it belongs to one of the array's lines, each line carried one cell
further upstream (out of the array) so its driver has room, plus the supports of kept dust and repeaters. each line is driven at its upstream end (din from the west; hold and rd from
the bottom, since their glass staircases carry signal upward only) by a redstone block in a free
cell beside the end dust, and dout is read at the west end dust.
The script prints each line's dust strength at the farthest cell it serves and fails if any is
below 1.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from redstone.build import Build  # noqa: E402
from redstone.fileformat import Spec, dump, load  # noqa: E402
from redstone.library import path_of  # noqa: E402

N, E, S, W = (0, 0, -1), (1, 0, 0), (0, 0, 1), (-1, 0, 0)
UP, DOWN = (0, 1, 0), (0, -1, 0)
HD = {"N": N, "E": E, "S": S, "W": W}
HNAME = {v: k for k, v in {"north": N, "east": E, "south": S, "west": W}.items()}
HDIRS = [N, E, S, W]
SOLID = "smooth_stone"
STATE = {"sol": SOLID, "gls": "glass"}
SHIFT = (-2, 0, -2)  # where a cell's box starts relative to its S, in cell units of the lattice


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def neg(a):
    return (-a[0], -a[1], -a[2])


def scale(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


class Cell:
    def __init__(self, found: dict):
        lat = found["lat"]
        assert lat[0][1:] == [0, 0] and lat[1][0] == lat[1][2] == 0 and lat[2][:2] == [0, 0], "box lattice only"
        self.a, self.c, self.f = lat[0][0], lat[1][1], lat[2][2]
        self.types = found["types"]
        self.u, self.w = tuple(found["u"]), tuple(found["w"])
        self.t = next(tuple(v) for v in lat if tuple(v) not in (self.u, self.w))
        self.S, self.K, self.O = (tuple(found[k]) for k in "SKO")

    def type(self, p):
        x, y, z = p
        return self.types[x % self.a + self.a * (y % self.c + self.c * (z % self.f))]

    def origin(self, i, j, k):
        return add(add(scale(self.u, i), scale(self.w, j)), scale(self.t, k))

    def box(self, i, j, k):
        o = add(self.origin(i, j, k), SHIFT)
        return [add(o, (x, y, z)) for z in range(self.f) for y in range(self.c) for x in range(self.a)]


def rep_in(t):
    return HD[t[1]]


class World:
    def __init__(self, blocks):
        self.b = blocks  # pos -> model type

    def t(self, p):
        return self.b.get(p, "air")

    def conn(self, p):
        """Minecraft's side/up/none for each side of dust at p."""
        above_open = self.t(add(p, UP)) != "sol"
        sides = {}
        for d in HDIRS:
            n = add(p, d)
            tn = self.t(n)
            c = None
            if above_open and tn in ("sol", "gls") and self.t(add(n, UP)) == "dust":
                c = "up"
            elif tn == "dust" or (tn[0] == "r" and rep_in(tn)[0] * d[0] + rep_in(tn)[2] * d[2] != 0):
                c = "side"
            elif tn != "sol" and self.t(add(n, DOWN)) == "dust":
                c = "side"
            sides[d] = c
        if not (sides[N] or sides[S]):
            sides[E], sides[W] = sides[E] or "side", sides[W] or "side"
        if not (sides[E] or sides[W]):
            sides[N], sides[S] = sides[N] or "side", sides[S] or "side"
        return sides

    def sources(self, p):
        """Dust whose power dust at p reads: up a step only past a conductor, down only past a
        non-conductor, so a glass staircase carries signal upward only."""
        out = []
        above_c = self.t(add(p, UP)) == "sol"
        for d in HDIRS:
            n = add(p, d)
            tn = self.t(n)
            if tn == "dust":
                out.append(n)
            elif tn == "sol":
                if not above_c and self.t(add(n, UP)) == "dust":
                    out.append(add(n, UP))
            elif self.t(add(n, DOWN)) == "dust":
                out.append(add(n, DOWN))
        return out

    def readers(self, p):
        near = [add(add(p, d), (0, dy, 0)) for d in HDIRS for dy in (-1, 0, 1)]
        return [q for q in near if self.t(q) == "dust" and p in self.sources(q)]

    def state(self, p):
        t = self.t(p)
        if t == "dust":
            sides = self.conn(p)
            return "redstone_wire[" + ",".join(f"{HNAME[d]}={sides[d] or 'none'}" for d in HDIRS) + "]"
        if t[0] == "r":
            return f"repeater[facing={HNAME[rep_in(t)]}]"
        return STATE[t]

    def net(self, seeds, inside):
        seen, todo = set(), [s for s in seeds if self.t(s) == "dust"]
        while todo:
            p = todo.pop()
            if p in seen or p not in inside:
                continue
            seen.add(p)
            todo += self.sources(p) + self.readers(p)
        return seen

    def strength(self, sources):
        """Dust strength from 15 at each source dust, -1 per dust step."""
        best = {}
        todo = [(15, s) for s in sources]
        while todo:
            todo.sort()
            lvl, p = todo.pop()
            if lvl <= best.get(p, 0):
                continue
            best[p] = lvl
            todo += [(lvl - 1, q) for q in self.readers(p)]
        return best


def convert(found, name, tests, description):
    cell = Cell(found)
    I, J, K = 3, 3, 2
    cells = [(i, j, k) for k in range(K) for j in range(J) for i in range(I)]
    inside = set()
    for ijk in cells:
        inside |= set(cell.box(*ijk))
    near = set(inside)
    for i, j, k in cells:
        near |= set(cell.box(i - 1, j, k)) | set(cell.box(i, j - 1, k))
    lattice = World({p: cell.type(p) for p in {add(q, d) for q in near for d in [(0, 0, 0), UP, DOWN, N, E, S, W]}})

    roles = {}
    for ijk in cells:
        o = cell.origin(*ijk)
        s, k_, o_ = add(o, cell.S), add(o, cell.K), add(o, cell.O)
        for p in (s, k_, o_):
            assert p in inside and lattice.t(p)[0] == "r", (ijk, p, lattice.t(p))
        s_in = add(s, rep_in(lattice.t(s)))
        roles[ijk] = {"s": s, "k": k_, "o": o_, "s_in": s_in,
                      "k_in": add(k_, rep_in(lattice.t(k_))), "o_in": add(o_, rep_in(lattice.t(o_))),
                      "o_out": add(o_, neg(rep_in(lattice.t(o_))))}

    def touching(block):
        return [q for q in [add(block, d) for d in HDIRS + [UP]] if lattice.t(q) == "dust"]

    nets = {}
    for ijk, r in roles.items():
        i, j, k = ijk
        nets.setdefault(("din", j, k), set()).update(lattice.net(touching(r["s_in"]), inside))
        nets.setdefault(("dout", j, k), set()).update(lattice.net(touching(r["o_out"]), inside))
        nets.setdefault(("hold", i, k), set()).update(lattice.net([r["k_in"]], inside))
        nets.setdefault(("rd", i, k), set()).update(lattice.net([r["o_in"]], inside))
    def line_end(ps, axis):
        return min(ps, key=lambda p: (p[0] * axis[0] + p[1] * axis[1] + p[2] * axis[2], p[1]))

    def assemble():
        owner = {}
        for key, ps in nets.items():
            for p in ps:
                assert owner.setdefault(p, key) == key, f"nets {owner[p]} and {key} touch at {p}"
        blocks = {p: lattice.t(p) for p in inside if lattice.t(p) != "air" and (lattice.t(p) != "dust" or p in owner)}
        for p in owner:
            blocks[p] = "dust"
        for p in [p for p, t in blocks.items() if t == "dust" or t[0] == "r"]:
            blocks.setdefault(add(p, DOWN), lattice.t(add(p, DOWN)))
        world = World(blocks)
        drivers = {}
        for (kind, m, k), ps in nets.items():
            if kind == "dout":
                continue
            end = line_end(ps, cell.u if kind == "din" else cell.w)
            free = [q for q in [add(end, d) for d in HDIRS + [UP]] if world.t(q) == "air"
                    and all(n == end or world.t(n) == "air" for n in [add(q, d) for d in HDIRS + [UP, DOWN]])]
            drivers[(kind, m, k)] = free[0] if free else None
        return blocks, world, drivers

    blocks, world, drivers = assemble()
    for (kind, m, k), drv in drivers.items():
        if drv is None:
            before = (-1, m, k) if kind == "din" else (m, -1, k)
            nets[(kind, m, k)] |= lattice.net(list(nets[(kind, m, k)]), nets[(kind, m, k)] | set(cell.box(*before)))
    blocks, world, drivers = assemble()

    outputs, report, bad = {}, [], False
    for (kind, m, k), ps in sorted(nets.items()):
        if kind == "dout":
            outputs[f"dout{m}{k}"] = line_end(ps, cell.u)
    for key, drv in drivers.items():
        assert drv, f"{key}: no free cell beside its upstream end for a driver"
    drivers = {f"{kind}{m}{k}": drv for (kind, m, k), drv in sorted(drivers.items())}

    def powering(block):
        """Dust that powers a block: dust on top, or beside it and pointing into it."""
        return [q for q in [add(block, d) for d in HDIRS + [UP]] if world.t(q) == "dust"
                and (q[1] > block[1] or world.conn(q)[(block[0] - q[0], 0, block[2] - q[2])])]
    for label, drv in drivers.items():
        kind, m, k = label[:-2], int(label[-2]), int(label[-1])
        lvl = world.strength([q for q in [add(drv, d) for d in HDIRS + [UP, DOWN]] if world.t(q) == "dust"])
        if kind == "din":
            reads = [max(lvl.get(q, 0) for q in powering(r["s_in"])) for ijk, r in roles.items() if (ijk[1], ijk[2]) == (m, k)]
        else:
            key = "k_in" if kind == "hold" else "o_in"
            reads = [lvl.get(r[key], 0) for ijk, r in roles.items() if (ijk[0], ijk[2]) == (m, k)]
        report.append(f"{label}: weakest cell reads {min(reads)}")
        bad |= min(reads) < 1
    for label, out in outputs.items():
        m, k = int(label[-2]), int(label[-1])
        worst = 15
        for ijk, r in roles.items():
            if (ijk[1], ijk[2]) == (m, k):
                lvl = world.strength([q for q in [add(r["o_out"], d) for d in HDIRS + [UP, DOWN]] if world.t(q) == "dust"])
                worst = min(worst, lvl.get(out, 0))
        report.append(f"{label}: farthest cell gives {worst} at the output")
        bad |= worst < 1

    every = list(blocks) + list(drivers.values())
    lo = tuple(min(p[a] for p in every) for a in range(3))

    def at(p):
        return (p[0] - lo[0], p[1] - lo[1], p[2] - lo[2])

    spec = Spec(name, Build(), description=description, traits=["pistonless", "entityless", "silent", "lightless"])
    for p in blocks:
        spec.build.place(at(p), world.state(p))
    spec.inputs = {label: at(p) for label, p in sorted(drivers.items())}
    for label, p in sorted(outputs.items()):
        spec.named[label] = spec.outputs[label] = at(p)
    for (i, j, k), r in sorted(roles.items()):
        for part in "sko":
            spec.named[f"{part}{i}{j}{k}"] = at(r[part])
    spec.tests = tests
    return spec, report, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("found")
    ap.add_argument("name")
    ap.add_argument("--line", type=int, default=0)
    ap.add_argument("--tests-from", default="t8_c_v51")
    ap.add_argument("--description", default="")
    ap.add_argument("--out")
    args = ap.parse_args()
    found = json.loads(Path(args.found).read_text().splitlines()[args.line])
    if "types" not in found and "raw" in found:
        found["types"] = found["raw"]
    tests = load(path_of(args.tests_from)).tests
    spec, report, bad = convert(found, args.name, tests, args.description)
    print("\n".join(report))
    if bad:
        sys.exit("a line is too weak to reach its farthest cell")
    text = dump(spec)
    if args.out:
        Path(args.out).write_text(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
