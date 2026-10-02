"""cpu_fib4: the whole CPU4 computer in the main plot, running the Fibonacci program, built
from the compact parts (pass 2).

Layout (top view, north up, x east): the legend and the START/RESET panels along the north
edge; the ROM (levers on top) with the PC abutting its east face, so pc and pimm are one dust
cell each; the decoder turned a quarter clockwise under the ROM, op pins facing the ROM's op
taps; the ALU east of the PC, taking n from the PC's passthrough, and the register file
abutting the ALU's east face; the display at the north edge east of the register file; the
clock south of the ALU. Abutting pins get one dust cell; every other net is routed by
scripts.alu_route (FixedRouter), then dust runs that die out get repeaters. Every solid block
becomes concrete in the colour of the circuit that placed it: a part's own circuits() where it
has several, else the part; a routed net's colour for its dust supports (KEY, repeated on
signs beside the levers).
"""

from collections import deque

from redstone.build import Build
from redstone.fileformat import Spec, load
from redstone.harness import parse_state
from redstone.library import LIBRARY, SUFFIX
from redstone.rotate import rotate_pos, rotated
from scripts.alu_route import DIR, SOLID, WIRE, Grid, fix
from scripts.cpu_alu_compact import FixedRouter
from scripts.cpu_clock_compact import cpu_clock_compact
from scripts.rom_ctrl import rom_ctrl

FIB_PROGRAM = [0x10, 0x80, 0x11, 0xA0, 0x90, 0x20, 0xD8, 0xB3, 0xF0] + [0] * 7
PERIOD, CAP_AT = 122, 92           # measured: 122/92 passes, 120/90 fails; the clock needs CAP_AT <= PERIOD - 30
CLOCK_L = 12                 # start rise -> first COM at the clock pin (cpu_clock_compact, MEASURED)
YMAX = 4
SOLIDS = ("smooth_stone", "white_concrete", "black_concrete")
PAINTED = ("smooth_stone", "white_concrete")
FACING = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0)}
JOG = 6                      # columns between the PC and the ALU for the n jog

KEY = [
    ("red", "Clock", "and clock lines"),
    ("orange", "Program", "counter"),
    ("yellow", "ROM", "program words"),
    ("purple", "Control", "decoder"),
    ("blue", "Register A", "+ reg file"),
    ("cyan", "Register B", ""),
    ("brown", "Flags Z C", "+ flag lines"),
    ("green", "ALU", "sum and mux"),
    ("lime", "ALU", "carry chain"),
    ("light_gray", "OUT register", "+ display"),
    ("light_blue", "Data buses", "pc a b y n"),
    ("magenta", "Control lines", "op, writes, jt"),
    ("white", "START, RESET", "levers + lines"),
]
PART_COLOUR = {"clock": "red", "pc": "orange", "rom": "yellow", "dec": "purple", "disp": "light_gray",
               "pstart": "white", "prst": "white"}
CIRCUIT_COLOUR = {"a": "blue", "b": "cyan", "out": "light_gray", "flags": "brown", "ctl": "magenta",
                  "clock": "red", "carry": "lime", "alu": "green"}
CONTROL_NETS = {"xsel", "sub", "za", "wa", "wb", "wo", "wf", "hlt", "jt", *(f"op{i}" for i in range(4))}
FLAG_NETS = {"zo", "co", "z", "c"}


def sign(*lines):
    msgs = ",".join(f'"{t}"' for t in (list(lines) + [""] * 4)[:4])
    return f"oak_wall_sign[facing=north]{{front_text:{{messages:[{msgs}]}}}}"


def panel(name, *label):
    """A wall lever on the north face of a block that powers the source pin south of it;
    the input cell beside the pin is the harness's driver for the same net."""
    b = Build()
    for x in range(3):
        for z in range(3):
            b.place((x, 0, z), "white_concrete")
    b.place((1, 1, 1), "white_concrete")
    b.place((1, 1, 0), "lever[face=wall,facing=north,powered=false]")
    b.place((1, 2, 1), "white_concrete")
    b.place((1, 2, 0), sign(*label))
    b.place((1, 1, 2), "redstone_wire")
    spec = Spec(name, b, outputs={"src": (1, 1, 2)},
                named={"lever": (1, 1, 0), "src": (1, 1, 2), "driver": (0, 1, 2)})
    spec.fixtures = {(1, 2, 1), (1, 2, 0)}
    return spec


def legend():
    b = Build()
    for i, (colour, *text) in enumerate(KEY):
        b.place((2 * i, 0, 1), f"{colour}_concrete")
        b.place((2 * i, 1, 1), f"{colour}_concrete")
        b.place((2 * i, 1, 0), sign(*text))
    spec = Spec("legend", b)
    spec.fixtures = set(b.blocks)
    return spec


def turned(spec: Spec, k: int) -> Spec:
    """spec turned k quarters clockwise seen from above, shifted back to a (0, 0, 0) corner."""
    b = rotated(spec.build, k)
    lo, _ = b.bounds()
    shift = lambda p: (lambda q: (q[0] - lo[0], q[1], q[2] - lo[2]))(rotate_pos(p, k))
    out = Build()
    for p, s in b.blocks.items():
        out.place((p[0] - lo[0], p[1], p[2] - lo[2]), s)
    m = lambda d: {n: shift(p) for n, p in d.items()}
    t = Spec(spec.name, out, inputs=m(spec.inputs), outputs=m(spec.outputs), named=m(spec.named))
    t.fixtures = {shift(p) for p in spec.fixtures}
    return t


def at(off, p):
    return (p[0] + off[0], p[1] + off[1], p[2] + off[2])


def part(n):
    return load(LIBRARY / "cpu_parts" / f"{n}{SUFFIX}")


def circuit_maps():
    from scripts.cpu_alu_compact import circuits as alu_circuits
    from scripts.cpu_regs_compact import circuits as regs_circuits
    return {"alu": alu_circuits(), "regs": regs_circuits()}


def parts(words, period=PERIOD, cap_at=CAP_AT):
    rom = rom_ctrl("rom", words)
    pc = part("cpu_pc_compact")
    dec = turned(part("cpu_ctrl_compact"), 1)
    alu, regs = part("cpu_alu_compact"), part("cpu_regs_compact")
    disp = part("cpu_out_display_compact")
    clock = cpu_clock_compact("clock", period=period, cap_at=cap_at)
    roff = (4, 0, 3)
    rx = roff[0] + 47                                     # ROM east face
    poff = (rx + 1, 0, roff[2] + rom.inputs["pc0"][2] - pc.outputs["pc0"][2])
    pw = pc.build.bounds()[1][0] + 1
    ph = pc.build.bounds()[1][2] + 1
    doc_x = rx - dec.inputs["op0"][0]
    gap_x = doc_x + dec.build.bounds()[1][0] + 2          # PC lines climb here, east of the decoder
    ax = max(poff[0] + pw + JOG, gap_x + 10)              # then the ALU control columns
    aoff = (ax, 0, roff[2] + 5)                            # rows for the OUT lines north of the regs
    goff = (ax + alu.build.bounds()[1][0] + 1, 0, aoff[2])
    rw, rd = (v + 1 for v in regs.build.bounds()[1][::2])
    doff = (goff[0] + rw + 10, 0, 1)
    # decoder under the ROM: op0's pin lines up with the ROM's op taps' column
    dz = max(roff[2] + 37, poff[2] + ph) + 9
    doc = (doc_x, 0, dz)
    dsouth = dz + dec.build.bounds()[1][2]
    # clock inside the strip, west of the decoder's columns, under its own two rows (the
    # strip's first); the panels south of it, facing south
    r0 = max(dsouth, goff[2] + rd - 1) + 3
    coff = (doc_x - 14, 0, r0 + 5)
    ps = turned(panel("pstart", "START", "flip on once", "(runs the", "clock)"), 2)
    pr = turned(panel("prst", "RESET", "on two cycles,", "then off: runs", "the program again"), 2)
    st = at(coff, clock.inputs["start"])
    psoff = (st[0] - ps.outputs["src"][0], 0, st[2] + 1)
    proff = (psoff[0] - 5, 0, psoff[2])
    return {"rom": (rom, roff), "pc": (pc, poff), "dec": (dec, doc), "alu": (alu, aoff), "regs": (regs, goff),
            "disp": (disp, doff), "clock": (clock, coff),
            "legend": (legend(), (1, 0, 0)), "pstart": (ps, psoff), "prst": (pr, proff)}


ABUT = [*[("pc", f"pc{i}", "rom", f"pc{i}") for i in range(4)],
        *[("rom", f"pimm{i}", "pc", f"imm{i}") for i in range(4)],
        *[("alu", f"y{i}", "regs", f"y{i}") for i in range(4)],
        *[("regs", f"a{i}", "alu", f"a{i}") for i in range(4)],
        *[("regs", f"b{i}", "alu", f"b{i}") for i in range(4)],
        ("alu", "zo", "regs", "zo"), ("alu", "co", "regs", "co")]

# (net, source part, pin, sink part, pin), routed in this order
NETS = [
    *[(f"op{i}", "rom", f"op{i}", "dec", f"op{i}") for i in (3, 2, 1, 0)],
    *[(f"n{i}", "pc", f"n{i}", "alu", f"n{i}") for i in range(4)],
    ("jt", "dec", "jt", "pc", "jt"), ("hlt", "dec", "hlt", "pc", "hlt"),
    ("com", "clock", "com", "pc", "com"), ("cap", "clock", "cap", "pc", "cap"),
]
# The control strip south of the decoder, rows north to south: each line leaves its source
# pin straight (dust at y=1, along z), climbs sideways onto its own row (y=3 on supports,
# crossing over every column), and comes down sideways onto the sink's column. Columns never
# cross each other, rows never cross each other; the clock lines are the southmost rows so
# their columns (from the clock, south of the strip) pass under every other row.
STRIP = [("cap", "clock", "cap", "regs", "cap"), ("com", "clock", "com", "regs", "com"),
         ("z", "regs", "z", "dec", "z"), ("c", "regs", "c", "dec", "c"),
         ("xsel", "dec", "xsel", "alu", "xsel"), ("sub", "dec", "sub", "alu", "sub"), ("za", "dec", "za", "alu", "za"),
         ("wa", "dec", "wa", "regs", "wa"), ("wf", "dec", "wf", "regs", "wf"),
         ("wo", "dec", "wo", "regs", "wo"), ("wb", "dec", "wb", "regs", "wb")]
OUT_NETS = [(f"out{i}", "regs", f"out{i}", "disp", f"out{i}") for i in range(4)]
PANEL_NETS = [("start", "pstart", "src", "clock", "start"), ("rst", "prst", "src", "pc", "rst")]


def strip(g, P, pins):
    """Lay STRIP (see there). Returns the rows' z."""
    zs = lambda name: at(P[name][1], P[name][0].build.bounds()[1])[2]
    r0 = max(zs("dec"), zs("regs")) + 3
    alu_cols = {"xsel": 4, "sub": 6, "za": 8}
    gap_x = at(P["dec"][1], P["dec"][0].build.bounds()[1])[0] + 2
    rows = {}
    for k, (net, sp, spin, kp, kpin) in enumerate(STRIP):
        r = r0 + 2 * k
        rows[net] = r
        a, b = pins[f"{sp}.{spin}"], pins[f"{kp}.{kpin}"]
        cells = []
        if sp == "clock":
            cells += [(a[0], 1, z) for z in range(a[2] - 1, r - 1, -1)]
        else:
            cells += [(a[0], 1, z) for z in range(a[2] + 1, r + 1)]
        xd = gap_x + alu_cols[net] if kp == "alu" else b[0]
        d = 1 if xd > a[0] else -1
        cells += [(a[0] + d, 2, r)] + [(x, 3, r) for x in range(a[0] + 2 * d, xd - d, d)] + [(xd - d, 2, r)]
        if kp == "alu":
            cells += [(xd, 1, z) for z in range(r, b[2] - 1, -1)] + [(x, 1, b[2]) for x in range(xd + 1, b[0] + 1)]
        else:
            cells += [(xd, 1, z) for z in range(r, b[2] - 1, -1)]
        for c in cells:
            if g.b.get(c) == WIRE and g.net.get(c) == net:
                continue
            g.dust(c, net)
        g.net[a] = g.net[b] = net
    return rows


def out_bus(g, P, pins):
    """OUT lines, flat at y=1: north out of the register file, east, south past its east face,
    east under the display and north into its pins. out3 takes the innermost loop at the top
    and the outermost at the bottom, so no two lines cross."""
    gx = at(P["regs"][1], P["regs"][0].build.bounds()[1])[0] + 3
    for i in range(4):
        a, b = pins[f"regs.out{i}"], pins[f"disp.out{i}"]
        zt, xc, zb = a[2] - 1 - 2 * (3 - i), gx + 2 * (3 - i), b[2] + 2 + 2 * i
        cells = ([(a[0], 1, z) for z in range(a[2] - 1, zt, -1)] + [(x, 1, zt) for x in range(a[0], xc)]
                 + [(xc, 1, z) for z in range(zt, zb)] + [(x, 1, zb) for x in range(xc, b[0])]
                 + [(b[0], 1, z) for z in range(zb, b[2] - 1, -1)])
        for c in cells:
            if not (g.b.get(c) == WIRE and g.net.get(c) == f"out{i}"):
                g.dust(c, f"out{i}")
        g.net[a] = g.net[b] = f"out{i}"


def size(P):
    hi = [0, 0, 0]
    for spec, off in P.values():
        b = spec.build.bounds()[1]
        hi = [max(h, v + o) for h, v, o in zip(hi, b, off)]
    return (hi[0] + 3, YMAX + 1, hi[2] + 4)


def outward(P, name, q):
    spec, off = P[name]
    lo, hi = (at(off, p) for p in spec.build.bounds())
    return ((-1, 0) if q[0] == lo[0] else (1, 0) if q[0] == hi[0] else
            (0, -1) if q[2] == lo[2] else (0, 1))


def setup(P, S):
    g = Grid(S)
    R = FixedRouter(g, ymax=YMAX)
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
                for y in range(0, min(hi[1] + 2, S[1])):
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
        g.net[p] = f"op{i}"
        g.b[at(roff, (42, 2, 30 + 2 * i))] = SOLID
        pins[f"rom.op{i}"] = p
    for x in range(42, 48):
        for z in range(29, 38):
            for y in range(0, YMAX + 1):
                c = at(roff, (x, y, z))
                if c not in g.b:
                    R.keep.discard(c)
    for q in pins.values():
        R.keep.discard(q)
    return g, R, pins


def abut(g, pins):
    for sp, spin, kp, kpin in ABUT:
        net = spin
        q = pins[f"{kp}.{kpin}"]
        s = pins[f"{sp}.{spin}"]
        assert abs(q[0] - s[0]) + abs(q[2] - s[2]) == 1 and q[1] == s[1], (spin, s, q)
        g.b[q] = WIRE
        g.net[q] = net
        g.net[s] = net


def reserve(g, R, P, pins, nets):
    """Three cells straight out of every routed pin belong to its net; the cells beside them stay air."""
    netpins = {}
    for net, sp, spin, kp, kpin in nets:
        netpins[f"{sp}.{spin}"] = net
        netpins[f"{kp}.{kpin}"] = net
    sides = set()
    for key, net in netpins.items():
        name = key.split(".")[0]
        if key.startswith("rom.op"):
            continue
        q = pins[key]
        d = outward(P, name, q)
        for k in (1, 2, 3):
            c = (q[0] + d[0] * k, q[1], q[2] + d[1] * k)
            if c in g.b:
                break
            R.inputs[c] = net
            R.keep.discard(c)
            sides |= {(c[0] + d[1], c[1], c[2] + d[0]), (c[0] - d[1], c[1], c[2] - d[0])}
    for c in sides:
        if c not in R.inputs and c not in g.b:
            R.keep.add(c)


def guard(g, R, P, pins):
    """Keep the panel lines a cell clear of every part's box; the pin stubs stay open."""
    S = g.size
    for name, (spec, off) in P.items():
        lo, hi = (at(off, p) for p in spec.build.bounds())
        for x in range(lo[0] - 1, hi[0] + 2):
            for z in range(lo[2] - 1, hi[2] + 2):
                if lo[0] <= x <= hi[0] and lo[2] <= z <= hi[2]:
                    continue
                for y in range(2, min(hi[1] + 2, S[1])):
                    c = (x, y, z)
                    if c not in g.b and c not in R.inputs and all(0 <= v < m for v, m in zip(c, S)):
                        R.keep.add(c)


def route_some(g, R, pins, nets, tries=12):
    """Route nets in order; when one fails, start again with it moved to the front. Returns
    the grid and router of the first order that routes everything, and that order."""
    import copy
    order = list(nets)
    err = None
    for _ in range(tries):
        g2, R2 = copy.deepcopy((g, R))
        try:
            route_all(g2, R2, pins, order)
            return g2, R2, order
        except RuntimeError as e:
            err = e
            bad = next(n for n in order if f"for {n[0]} to {pins[f'{n[3]}.{n[4]}']}" in str(e))
            order.remove(bad)
            order.insert(0, bad)
    raise RuntimeError(f"no order routes every net; last: {err}")


def route_all(g, R, pins, nets, max_nodes=600000):
    for net, sp, spin, kp, kpin in nets:
        s = pins[f"{sp}.{spin}"]
        g.net[s] = net
        q = pins[f"{kp}.{kpin}"]
        starts = [c for c, n in g.net.items() if n == net and (g.b.get(c) == WIRE or c == s)]
        R.inputs[q] = net
        R.route(net, starts, q, max_nodes=max_nodes)


def isolate(g, P, pins, nets):
    """A repeater on the first cell out of every routed source pin."""
    done = set()
    for net, sp, spin, kp, kpin in nets:
        q = pins[f"{sp}.{spin}"]
        if q in done or sp == "rom":
            continue
        done.add(q)
        d = outward(P, sp, q)
        c = (q[0] + d[0], q[1], q[2] + d[1])
        if g.b.get(c) == WIRE and g.net.get(c) == net and g.b.get((c[0] + d[0], c[1], c[2] + d[1])) == WIRE:
            del g.b[c]
            g.rep(c, DIR[d], net)


def lag(g, net, src, dst):
    """2 gt per repeater on the shortest path of net from cell src to cell dst."""
    dist = {src: 0}
    todo = deque([src])
    while todo:
        c = todo.popleft()
        if c == dst:
            return 2 * dist[c]
        for e in DIR:
            for dy in (0, 1, -1):
                n = (c[0] + e[0], c[1] + dy, c[2] + e[1])
                s = g.b.get(n, "")
                if n not in dist and g.net.get(n) == net and (s == WIRE or "repeater" in s):
                    dist[n] = dist[c] + ("repeater" in s)
                    todo.append(n)
    raise ValueError(f"{net}: no path {src} -> {dst}")


def net_colour(net):
    base = net.rstrip("0123456789")
    if net in ("cap", "com"):
        return "red"
    if net in ("start", "rst"):
        return "white"
    if net in CONTROL_NETS:
        return "magenta"
    if net in FLAG_NETS:
        return "brown"
    if base == "out":
        return "light_gray"
    if base in ("pc", "pimm", "n", "a", "b", "y"):
        return "light_blue"
    raise ValueError(f"no colour for net {net}")


def part_colour(name, p, maps):
    if name in maps:
        return CIRCUIT_COLOUR[maps[name][p]]
    return PART_COLOUR[name]


def paint(g, P, part_cells):
    """Concrete for every routed solid, coloured by the net it carries or supports."""
    out, loose = {}, []
    for p, s in g.b.items():
        if p in part_cells or s != SOLID:
            continue
        x, y, z = p
        near = [(x, y + 1, z), (x, y - 1, z), (x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1)]
        net = g.net.get(p)
        if net is None or net.startswith("part:"):
            net = next((g.net[q] for q in near if q in g.net and not g.net[q].startswith("part:")), net)
        if net is None:
            loose.append(p)
        elif net.startswith("part:"):
            out[p] = f"{PART_COLOUR.get(net[5:], 'white')}_concrete"
        else:
            out[p] = f"{net_colour(net)}_concrete"
    return out, loose


def painted(name, spec, maps):
    b = Build()
    for p, s in spec.build.blocks.items():
        blk = parse_state(s)[0].removeprefix("minecraft:")
        b.place(p, f"{part_colour(name, p, maps)}_concrete" if blk in PAINTED and p not in spec.fixtures else s)
    return b


def cpu_fib4(words=FIB_PROGRAM, name="cpu_fib4", period=PERIOD, cap_at=CAP_AT) -> Spec:
    P = parts(words, period, cap_at)
    S = size(P)
    g, R, pins = setup(P, S)
    part_cells = {at(off, p) for spec, off in P.values() for p in spec.build.blocks}
    abut(g, pins)
    strip(g, P, pins)
    out_bus(g, P, pins)
    reserve(g, R, P, pins, NETS + PANEL_NETS)
    g, R, order = route_some(g, R, pins, PANEL_NETS + NETS)
    isolate(g, P, pins, STRIP + OUT_NETS + NETS + PANEL_NETS)
    fix(g, rounds=1000, fixed={n for n in set(g.net.values()) if n.startswith("part:")})
    colours, loose = paint(g, P, part_cells)
    assert not loose, f"routed solids with no net: {loose}"
    maps = circuit_maps()
    build = Build()
    for pname, (spec, off) in P.items():
        build.merge(painted(pname, spec, maps), off)
    for p, s in g.b.items():
        if p not in part_cells:
            build.place(p, colours.get(p, s))
    spec = Spec(name, build, description=description(period, cap_at))
    pick = {"pc": [f"s{i}" for i in range(4)],
            "regs": [f"sa{i}" for i in range(4)] + [f"sb{i}" for i in range(4)] + ["mz", "mc"] + [f"out{i}" for i in range(4)],
            "disp": [f"u_{s}" for s in "abcdefg"] + ["t_b", "t_c"]}
    for pname, cells in pick.items():
        pspec, off = P[pname]
        for c in cells:
            spec.named[f"{pname}.{c}"] = at(off, pspec.named[c])
    for pname, (pspec, off) in P.items():
        spec.fixtures |= {at(off, p) for p in pspec.fixtures}
    for pname, net in (("pstart", "start"), ("prst", "rst")):
        off = P[pname][1]
        spec.inputs[net] = at(off, P[pname][0].named["driver"])
        spec.named[f"{net}_lever"] = at(off, P[pname][0].named["lever"])
    lags = {"start": lag(g, "start", pins["pstart.src"], pins["clock.start"]),
            "rst": lag(g, "rst", pins["prst.src"], pins["pc.rst"]),
            "com": lag(g, "com", pins["clock.com"], pins["pc.com"])}
    spec.traits = ["torch_based", "pistonless", "entityless"]
    T = Timing(period, cap_at, lags)
    spec.tests = [fib_test(words, T), reset_test(words, T), rerun_test(words, T)]
    return spec


class Timing:
    """Test timing: samples fall at COM + period/2 - 2 at the PC; rst edges at COM + rst_at."""

    def __init__(self, period, cap_at, lags):
        self.P = period
        self.lags = lags
        self.sample = CLOCK_L + lags["com"] + 2 + period // 2 - 2
        self.rst_at = cap_at // 3
        assert lags["rst"] < cap_at, lags


DIGIT = {0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg", 5: "acdfg", 6: "acdefg", 7: "abc",
         8: "abcdefg", 9: "abcdfg"}


def isa(words, cycles, rst=()):
    """State during each cycle (slaves, flags and OUT before the cycle's write); rst holds
    the cycles whose CAP sees rst, which load PC 0 instead of the next address."""
    pc = a = b = z = c = out = 0
    rows = []
    for k in range(cycles):
        op, n = words[pc] >> 4, words[pc] & 15
        rows.append(dict(pc=pc, a=a, b=b, z=z, c=c, out=out))
        npc = n if op == 11 or (op == 12 and z) or (op == 13 and c) else pc if op == 15 else (pc + 1) & 15
        if k in rst:
            npc = 0
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


def expect_row(rows, k):
    r = rows[k]
    e = {}
    for i in range(4):
        e.update({f"pc.s{i}": r["pc"] >> i & 1, f"regs.sa{i}": r["a"] >> i & 1,
                  f"regs.sb{i}": r["b"] >> i & 1, f"regs.out{i}": r["out"] >> i & 1})
    e["regs.mz"], e["regs.mc"] = r["z"], r["c"]
    if k == 0 or rows[k - 1]["out"] != r["out"]:
        on = {f"u_{s}" for s in DIGIT[r["out"] % 10]} | ({"t_b", "t_c"} if r["out"] >= 10 else set())
        e.update({f"disp.{n}": int(n in on) for n in [f"u_{s}" for s in "abcdefg"] + ["t_b", "t_c"]})
    return {"expect": e}


def cycle_test(name, words, T, cycles, start, toggles=()):
    """Sample every cycle mid-cycle. toggles: (cycle, step) pairs, each step landing at
    COM + rst_at of that cycle at the PC; a rise there holds rst through that cycle's CAP."""
    on, rst = None, set()
    for k, _ in toggles:
        if on is None:
            on = k
        else:
            rst |= set(range(on, k))
            on = None
    assert on is None
    rows = isa(words, cycles, rst)
    w = (T.rst_at - (T.P // 2 - 2) - T.lags["rst"]) % T.P
    at_cycle = dict(toggles)
    steps = [*start, {"wait": T.sample + T.lags["start"]}]
    for k in range(cycles):
        steps.append(expect_row(rows, k))
        if k + 1 in at_cycle:
            steps += [{"wait": w}, at_cycle[k + 1], {"wait": T.P - w}]
        else:
            steps.append({"wait": T.P})
    return {"name": name, "settle": 40, "steps": steps}


def fib_test(words, T, cycles=41):
    pulse = [{"drive": {"start": 1}}, {"wait": 2}, {"drive": {"start": 0}}]
    return cycle_test("fibonacci", words, T, cycles, pulse)


def reset_test(words, T):
    """DESIGN 9: rst through one CAP after 10 cycles replays the program from PC 0."""
    pulse = [{"drive": {"start": 1}}, {"wait": 2}, {"drive": {"start": 0}}]
    return cycle_test("reset", words, T, 20, pulse,
                      [(10, {"drive": {"rst": 1}}), (11, {"drive": {"rst": 0}})])


def rerun_test(words, T):
    """Through the levers: START, run to the halt, RESET on for two cycles and off, run again."""
    return cycle_test("rerun", words, T, 86, [{"use": "start_lever"}],
                      [(41, {"use": "rst_lever"}), (43, {"use": "rst_lever"})])


def description(period, cap_at):
    return (
        "The whole CPU4 computer running the Fibonacci program (words 10 80 11 A0 90 20 D8 B3 F0), built from "
        "the compact parts: cpu_clock_compact, the 16x8 lever ROM (rom_ctrl), cpu_pc_compact abutting its east face, "
        "cpu_ctrl_compact turned under the ROM, cpu_alu_compact (n muxed inside) abutting cpu_regs_compact, and "
        "cpu_out_display_compact at the north edge. OUT shows 1, 1, 2, 3, 5, 8, 13, then JC 8 halts it at PC 8. "
        f"Clock period {period} gt, CAP {cap_at} gt after COM. "
        "Player controls on the south edge at the west end, facing south (stand south of the build): START "
        "(the east one of the two wall levers) starts the clock, flip it on once; RESET (5 blocks west of it) on "
        "for two cycles then off sends PC to 0 and the program runs again. The display faces north at the "
        "north-east corner; the ROM's 128 levers lie on its top, nothing above them. "
        "Colour key (every solid block is concrete in the colour of the circuit that placed it; the legend "
        "signs along the north edge repeat it): "
        + "; ".join(f"{c.replace('_', ' ')} = {' '.join(t for t in text if t)}" for c, *text in KEY)
        + "; black = display frame. Tests sample every register mid-cycle: fibonacci (41 cycles), "
        "reset (rst through one CAP at cycle 10, the program replays) and rerun (through the levers: run to "
        "the halt, RESET for two cycles, the same OUT sequence and halt again).")
