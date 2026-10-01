"""cpu_fib4: the whole CPU4 computer in the main plot, running the Fibonacci program.

The seven parts sit at fixed origins; the decoder is mirrored in x so that its op inputs
and imm outputs line up with the ROM and the ALU without crossings. The op lines, the
imm/n comb between decoder and ALU and the stubs at the register file's west face are laid
by hand; every other net is routed by scripts.alu_route, then dust runs that die out get
repeaters and the four clock lines are padded to the same number of repeaters.
"""

from collections import deque

from redstone.build import Build
from redstone.fileformat import Spec, load
from redstone.harness import format_state, parse_state
from redstone.library import LIBRARY, SUFFIX
from scripts.alu_route import DIR, SOLID, WIRE, Grid, Router, fix
from scripts.cpu_regs import line
from scripts.rom_ctrl import rom_ctrl

SIZE = (192, 24, 192)
FIB_PROGRAM = [0x10, 0x80, 0x11, 0xA0, 0x90, 0x20, 0xD8, 0xB3, 0xF0] + [0] * 7
OX, OZ = 110, 4                       # ROM origin; the rest follow from it
FACING = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0)}
CLOCK = ("cape", "come", "capw", "comw")
# Start rise to the first COM at the clock pins (cpu_clock, MEASURED 18), the 11 repeaters
# every clock line carries, the part pin repeater, then half a 200 gt cycle.
SAMPLE = 18 + 2 * 11 + 2 + 100 - 2
SOLIDS = ("smooth_stone", "white_concrete", "black_concrete")


def mirror_x(spec: Spec, w: int) -> Spec:
    """The spec mirrored in x (x -> w - x)."""
    b = Build()
    for (x, y, z), s in spec.build.blocks.items():
        blk, props = parse_state(s)
        if props.get("facing") in ("east", "west"):
            props["facing"] = {"east": "west", "west": "east"}[props["facing"]]
        if "east" in props and "west" in props:
            props["east"], props["west"] = props["west"], props["east"]
        b.place((w - x, y, z), format_state(blk, props))
    m = lambda d: {k: (w - p[0], p[1], p[2]) for k, p in d.items()}
    return Spec(spec.name, b, inputs=m(spec.inputs), outputs=m(spec.outputs), named=m(spec.named))


def parts(words):
    part = lambda n: load(LIBRARY / "cpu_parts" / f"{n}{SUFFIX}")
    mx, mz = OX - 12, OZ + 40
    ax, az = mx - 14, 128
    return {"rom": (rom_ctrl("rom", words), (OX, 0, OZ)),
            "pc": (part("cpu_pc"), (OX + 60, 0, OZ)),
            "ctrl": (mirror_x(part("cpu_ctrl"), 69), (mx, 0, mz)),
            "alu": (part("cpu_alu"), (ax, 0, az)),
            "regs": (part("cpu_regs"), (ax - 52, 0, az - 11)),
            "disp": (part("cpu_out_display"), (0, 0, 80)),
            "clock": (part("cpu_clock"), (140, 0, 166))}


def at(off, p):
    return (p[0] + off[0], p[1] + off[1], p[2] + off[2])


# Routing order matters: each face's buses go in the order they turn.
NETS = [
    *[(f"pc{i}", "pc", f"pc{i}", "rom", f"pc{i}") for i in range(4)],
    *[(f"pimm{i}", "rom", f"pimm{i}", "pc", f"imm{i}") for i in range(4)],
    ("xsel", "ctrl", "xsel", "alu", "xsel"), ("sub", "ctrl", "sub", "alu", "sub"), ("za", "ctrl", "za", "alu", "za"),
    ("wb", "ctrl", "wb", "regs", "wb"), ("wa", "ctrl", "wa", "regs", "wa"), ("wo", "ctrl", "wo", "regs", "wo"),
    ("wf", "ctrl", "wf", "regs", "wf"), ("hlt", "ctrl", "hlt", "pc", "hlt"), ("jt", "ctrl", "jt", "pc", "jt"),
    *[(f"pimm{i}", "rom", f"pimm{i}", None, "entry") for i in (3, 2, 1, 0)],
    ("cape", "clock", "cape", "pc", "cap"), ("come", "clock", "come", "pc", "com"),
    ("capw", "clock", "capw", "regs", "cap"), ("comw", "clock", "comw", "regs", "com"),
    ("zo", "alu", "zo", "regs", "zo"), ("co", "alu", "co", "regs", "co"),
    *[(f"out{i}", "regs", f"out{i}", "disp", f"out{i}") for i in range(4)],
    ("c", "regs", "c", "ctrl", "c"), ("z", "regs", "z", "ctrl", "z"),
]
REGS_WEST_SINKS = ("cap", "wf", "zo", "co")


def lay(g, cells, net, reps=()):
    for i, c in enumerate(cells):
        if c in g.b and g.b[c] != SOLID:
            if g.net.get(c) == net:
                continue
            raise ValueError(f"{net} hits {c} {g.b[c]} {g.net.get(c)}")
        if i in reps:
            n = cells[i + 1]
            g.rep(c, DIR[(n[0] - c[0], n[2] - c[2])], net)
        else:
            g.dust(c, net)


def setup(P):
    g = Grid(SIZE)
    R = Router(g, ymax=12)
    pins = {}
    for name, (spec, off) in P.items():
        lo, hi = spec.build.bounds()
        for p, s in spec.build.blocks.items():
            q = at(off, p)
            blk, pr = parse_state(s)
            blk = blk.removeprefix("minecraft:")
            g.b[q] = SOLID if blk in SOLIDS else s.removeprefix("minecraft:")
            g.net[q] = f"part:{name}"
            if blk in ("repeater", "comparator"):
                f = FACING[pr["facing"]]
                g.strong.setdefault(at(q, (-f[0], 0, -f[2])), set()).add(f"part:{name}")
                R.inputs.setdefault(at(q, f), f"part:{name}")
            elif "torch" in blk:
                g.strong.setdefault(at(q, (0, 1, 0)), set()).add(f"part:{name}")
        a, b = at(off, lo), at(off, hi)
        for x in range(a[0], b[0] + 1):
            for z in range(a[2], b[2] + 1):
                for y in range(0, min(hi[1] + 2, SIZE[1])):
                    R.keep.add((x, y, z))
        for pin, p in list(spec.inputs.items()) + list(spec.outputs.items()):
            pins[f"{name}.{pin}"] = at(off, p)
        for pin, p in spec.inputs.items():
            below = at(off, (p[0], p[1] - 1, p[2]))
            if below not in g.b:
                g.b[below] = SOLID
                g.net[below] = f"part:{name}"
    # op taps: dust beside the ROM's bit 4-7 torches; the ROM is empty east of them there
    roff = P["rom"][1]
    for i in range(4):
        p = at(roff, (42, 3, 30 + 2 * i))
        g.b[p] = WIRE
        g.b[at(roff, (42, 2, 30 + 2 * i))] = SOLID
        pins[f"rom.op{i}"] = p
    for x in range(42, 48):
        for z in range(29, 38):
            for y in range(0, 10):
                c = at(roff, (x, y, z))
                if c not in g.b:
                    R.keep.discard(c)
    for q in pins.values():
        R.keep.discard(q)
    return g, R, pins


def hand(g, pins):
    """Op lines, the imm/n comb and the register file's west stubs. Returns the n entries."""
    oz, mz = OZ, OZ + 40
    for i in range(4):
        z = oz + 30 + 2 * i
        col = pins[f"ctrl.op{i}"][0]
        cells = line((OX + 43, 3, z), (col, 3, z), (col, 3, mz))
        lay(g, cells, f"op{i}", (3,) if len(cells) > 13 else ())
    s = mz + 63                       # decoder south face
    for j in range(4):
        x, ax = pins[f"ctrl.imm{j}"][0], pins[f"alu.imm{j}"][0]
        jr = s + 13 + 2 * j
        az = pins[f"alu.imm{j}"][2]
        cells = [(x, 1, s + 1), (x, 2, s + 2), (x, 3, s + 3), (x, 4, s + 4)]
        cells += line((x, 5, s + 5), (x, 5, jr), (ax, 5, jr), (ax, 5, az))
        lay(g, cells, f"imm{j}", reps=(8,))
    entries = {}
    for j in range(4):
        x = pins[f"ctrl.n{j}"][0]
        row = s + 7 + 2 * (3 - j)
        down = [(x, 7 - t, s + 7 - t) for t in range(7)] + [(x, 1, s)]
        lay(g, line((OX + 4, 7, row), (x, 7, row), (x, 7, s + 7))[:-1] + down, f"pimm{j}")
        entries[j] = (OX + 5, 7, row)
    for i in range(4):
        for net in ("a", "b"):
            x, y, z = pins[f"regs.{net}{i}"]
            lay(g, line((x + 1, y, z), pins[f"alu.{net}{i}"]), f"{net}{i}")
        x, y, z = pins[f"alu.y{i}"]
        lay(g, line((x - 1, y, z), pins[f"regs.y{i}"]), f"y{i}")
    stubs = {"cap": "capw", "wf": "wf", "zo": "zo", "co": "co", "z": "z", "c": "c",
             **{f"out{i}": f"out{i}" for i in range(4)}}
    for pin, net in stubs.items():
        x, y, z = pins[f"regs.{pin}"]
        lay(g, [(x - k, y, z) for k in range(0 if pin in REGS_WEST_SINKS else 1, 5)], net)
    return entries


def reserve(g, R, P, pins):
    """Three cells straight out of every pin belong to its net; the cells beside them stay air."""
    netpins = {}
    for net, sp, spin, kp, kpin in NETS:
        netpins[f"{sp}.{spin}"] = net
        if kp:
            netpins[f"{kp}.{kpin}"] = net
    for i in range(4):
        netpins[f"ctrl.op{i}"] = netpins[f"rom.op{i}"] = f"op{i}"
        netpins[f"ctrl.imm{i}"] = netpins[f"alu.imm{i}"] = f"imm{i}"
        netpins[f"ctrl.n{i}"] = f"pimm{i}"
    sides = set()
    for name, (spec, off) in P.items():
        lo, hi = (at(off, p) for p in spec.build.bounds())
        for pin in list(spec.inputs) + list(spec.outputs):
            q = pins[f"{name}.{pin}"]
            d = ((-1, 0) if q[0] == lo[0] else (1, 0) if q[0] == hi[0] else
                 (0, -1) if q[2] == lo[2] else (0, 1))
            for k in (1, 2, 3):
                c = (q[0] + d[0] * k, q[1], q[2] + d[1] * k)
                R.inputs[c] = netpins.get(f"{name}.{pin}", f"pin:{name}.{pin}")
                R.keep.discard(c)
                sides |= {(c[0] + d[1], c[1], c[2] + d[0]), (c[0] - d[1], c[1], c[2] - d[0])}
    for c in sides:
        if c not in R.inputs and c not in g.b:
            R.keep.add(c)


def outward(P, part, q):
    spec, off = P[part]
    lo, hi = (at(off, p) for p in spec.build.bounds())
    return ((-1, 0) if q[0] == lo[0] else (1, 0) if q[0] == hi[0] else
            (0, -1) if q[2] == lo[2] else (0, 1))


def isolate(g, P, pins):
    """A repeater on the first cell out of every routed source pin: some parts' output dust
    is part of a longer net inside them and arrives weak."""
    for net, sp, spin, kp, kpin in NETS:
        q = pins[f"{sp}.{spin}"]
        d = outward(P, sp, q)
        c = (q[0] + d[0], q[1], q[2] + d[1])
        if g.b.get(c) == WIRE and g.net.get(c) == net and g.b.get((c[0] + d[0], c[1], c[2] + d[1])) == WIRE:
            del g.b[c]
            g.rep(c, DIR[d], net)


def route_all(g, R, pins, entries):
    for net, sp, spin, kp, kpin in NETS:
        s = pins[f"{sp}.{spin}"]
        g.net[s] = net
        q = entries[int(net[-1])] if kpin == "entry" else pins[f"{kp}.{kpin}"]
        starts = [c for c, n in g.net.items() if n == net and (g.b.get(c) == WIRE or c == s)]
        if kp == "regs" and kpin in REGS_WEST_SINKS:
            stub = {(q[0] - k, q[1], q[2]) for k in range(5)}
            starts = [c for c in starts if c not in stub]
            q = (q[0] - 4, q[1], q[2])
        if kpin == "entry":
            starts = [c for c in starts if c[2] < OZ + 40]
        R.inputs[q] = net
        R.route(net, starts, q, max_nodes=1500000)


def _reps(g, net):
    return [p for p, n in g.net.items() if n == net and "repeater" in g.b.get(p, "")]


def _pad(g, net, src, need):
    """Turn need straight dust cells of net into repeaters pointing away from src."""
    dist = {src: 0}
    todo = deque([src])
    while todo:
        c = todo.popleft()
        for e in DIR:
            for dy in (0, 1, -1):
                n = (c[0] + e[0], c[1] + dy, c[2] + e[1])
                if n not in dist and g.net.get(n) == net and (g.b.get(n) == WIRE or "repeater" in g.b.get(n, "")):
                    dist[n] = dist[c] + 1
                    todo.append(n)
    cand = []
    for p in sorted(dist, key=dist.get):
        if g.b.get(p) != WIRE:
            continue
        x, y, z = p
        for d in ((1, 0), (0, 1)):
            a, b = (x - d[0], y, z - d[1]), (x + d[0], y, z + d[1])
            side = [(x + d[1], y, z + d[0]), (x - d[1], y, z - d[0])]
            if (g.b.get(a) == WIRE == g.b.get(b) and g.net.get(a) == net == g.net.get(b)
                    and all(g.b.get(o) != WIRE and "repeater" not in g.b.get(o, "") for o in side)):
                cand.append((p, d if dist[a] < dist[p] else (-d[0], -d[1])))
    step = max(1, len(cand) // (need + 1))
    for p, d in cand[step::step][:need]:
        del g.b[p]
        g.rep(p, DIR[d], net)


def cpu_fib4(words=FIB_PROGRAM, name="cpu_fib4") -> Spec:
    P = parts(words)
    g, R, pins = setup(P)
    part_cells = {at(off, p) for spec, off in P.values() for p in spec.build.blocks}
    entries = hand(g, pins)
    reserve(g, R, P, pins)
    route_all(g, R, pins, entries)
    isolate(g, P, pins)
    fix(g, rounds=400, fixed={n for n in set(g.net.values()) if n.startswith("part:")})
    most = max(len(_reps(g, n)) for n in CLOCK)
    for n in CLOCK:
        _pad(g, n, pins[f"clock.{n}"], most - len(_reps(g, n)))
    assert len({len(_reps(g, n)) for n in CLOCK}) == 1
    build = Build()
    for spec, off in P.values():
        build.merge(spec.build, off)
    for p, s in g.b.items():
        if p not in part_cells:
            build.place(p, s)
    spec = Spec(name, build, description=DESCRIPTION)
    pick = {"pc": [f"s{i}" for i in range(4)],
            "regs": [f"sa{i}" for i in range(4)] + [f"sb{i}" for i in range(4)] + ["mz", "mc"] + [f"out{i}" for i in range(4)],
            "disp": [f"u_{s}" for s in "abcdefg"] + ["t_b", "t_c"]}
    for part, cells in pick.items():
        pspec, off = P[part]
        for c in cells:
            spec.named[f"{part}.{c}"] = at(off, pspec.named[c])
    spec.inputs["start"] = at(P["clock"][1], P["clock"][0].inputs["start"])
    spec.inputs["rst"] = at(P["pc"][1], P["pc"][0].inputs["rst"])
    spec.traits = ["torch_based", "pistonless", "entityless"]
    spec.tests = [fib_test(words)]
    return spec


DIGIT = {0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg", 5: "acdfg", 6: "acdefg", 7: "abc",
         8: "abcdefg", 9: "abcdfg"}


def isa(words, cycles):
    """State during each cycle (slaves, flags and OUT before the cycle's write)."""
    pc = a = b = z = c = out = 0
    rows = []
    for _ in range(cycles):
        op, n = words[pc] >> 4, words[pc] & 15
        rows.append(dict(pc=pc, a=a, b=b, z=z, c=c, out=out))
        npc = n if op == 11 or (op == 12 and z) or (op == 13 and c) else pc if op == 15 else (pc + 1) & 15
        y, x = None, (n if op in (1, 7, 14) else b)
        if op in (2, 7):
            y, c = (a + x) & 15, (a + x) >> 4
            z = int(y == 0)
        elif op in (3, 14):
            y, c = (a + (~x & 15) + 1) & 15, (a + (~x & 15) + 1) >> 4
            z = int(y == 0)
        elif op == 1:
            y = x
        if op == 9:
            y, b = b, a
        elif op == 8:
            b = a
        elif op == 10:
            out = a
        if y is not None:
            a = y
        pc = npc
    return rows


def fib_test(words, cycles=41):
    rows = isa(words, cycles)
    steps = [{"drive": {"start": 1}}, {"wait": 2}, {"drive": {"start": 0}}, {"wait": SAMPLE}]
    for k, r in enumerate(rows):
        e = {}
        for i in range(4):
            e.update({f"pc.s{i}": r["pc"] >> i & 1, f"regs.sa{i}": r["a"] >> i & 1,
                      f"regs.sb{i}": r["b"] >> i & 1, f"regs.out{i}": r["out"] >> i & 1})
        e["regs.mz"], e["regs.mc"] = r["z"], r["c"]
        if k == 0 or rows[k - 1]["out"] != r["out"]:
            on = {f"u_{s}" for s in DIGIT[r["out"] % 10]} | ({"t_b", "t_c"} if r["out"] >= 10 else set())
            e.update({f"disp.{n}": int(n in on) for n in [f"u_{s}" for s in "abcdefg"] + ["t_b", "t_c"]})
        steps += [{"expect": e}, {"wait": 200}]
    return {"name": "fibonacci", "settle": 40, "steps": steps}


DESCRIPTION = (
    "The whole CPU4 computer running the Fibonacci program (words 10 80 11 A0 90 20 D8 B3 F0): "
    "clock, program counter, 16x8 lever ROM, control decoder (mirrored in x), ALU, register file and "
    "two-digit display. OUT shows 1, 1, 2, 3, 5, 8, 13, then JC 8 halts it at PC 8. The test samples "
    "every register mid-cycle for 41 cycles of 200 gt.")
