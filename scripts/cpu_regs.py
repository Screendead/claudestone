"""CPU4 register file cpu_regs: A and B master/slave, OUT, Z and C latches.

Bit k of every register sits on its own deck at y = 3 + 2k, so a register is a vertical
stack of four repeater latches (dl_lock_stack). The latches of one register are locked
together from below: its hold line climbs a glass zigzag beside the stack from a head of
torches on the control deck at y = 1. Each deck holds one bit's data nets and needs no
crossings; the control deck holds the heads and their lines.
"""

from redstone.build import Build
from redstone.fileformat import Spec

SOLID = "white_concrete"
GLASS = "glass"
WIRE = "redstone_wire"

DECKS = 4
Z0 = 8                       # data row of the register stacks
X = {"o": 10, "a": 16, "b": 25}
XF, ZF = 4, 14               # flag latch (Z on deck 0, C on deck 1)
COL = {"y": 29, "a": 31, "b": 33}
ZB = 11                      # regs z of the ALU's z = 0
E = 49                       # east face
X_DESCENT = 35
X_JOG = {"a": 44, "b": 46}
WE_PIN_X = {"o": 12, "a": 18, "b": 27}
COM_X = 22
RUN = 12                     # dust cells between repeaters on long lines


def deck_y(k):
    return 3 + 2 * k


def band_row(net, k):
    return ZB + {"b": 6, "a": 8, "y": 10}[net] + 7 * k


def pin_row(net, k):
    return ZB + {"b": 7, "a": 9, "y": 10}[net] + 7 * k


FACING = {(1, 0): "west", (-1, 0): "east", (0, 1): "north", (0, -1): "south"}  # flow -> input side


class Regs:
    def __init__(self):
        self.b = {}
        self.net = {}

    def put(self, p, state, net=None):
        old = self.b.get(p)
        if old is not None and old != state:
            raise ValueError(f"overlap at {p}: {old} ({self.net.get(p)}) vs {state} ({net})")
        if old is not None and net is not None and self.net.get(p) not in (None, net):
            raise ValueError(f"net clash at {p}: {self.net.get(p)} vs {net}")
        self.b[p] = state
        if net is not None:
            self.net[p] = net

    def support(self, p):
        q = (p[0], p[1] - 1, p[2])
        if q[1] >= 0 and q not in self.b:
            self.b[q] = SOLID

    def dust(self, p, net):
        self.put(p, WIRE, net)
        self.support(p)

    def rep(self, p, flow, net):
        """Repeater whose output goes in direction flow (dx, dz)."""
        self.put(p, f"repeater[facing={FACING[flow]},delay=1]", net)
        self.support(p)

    def torch(self, p, attached_dir, net):
        """Wall torch on the block in direction attached_dir from p."""
        self.put(p, f"redstone_wall_torch[facing={FACING[attached_dir]}]", net)

    def path(self, cells, net, run=0, reps=()):
        """Dust along cells (in signal order); a repeater wherever the flat run since the
        last source reaches RUN cells and the cell is mid-way along a straight flat stretch,
        or at the indices in reps. Returns the run length left at the end."""
        for i, c in enumerate(cells):
            prv = cells[i - 1] if i else None
            nxt = cells[i + 1] if i + 1 < len(cells) else None
            straight = (prv and nxt and prv[1] == c[1] == nxt[1]
                        and (c[0] - prv[0], c[2] - prv[2]) == (nxt[0] - c[0], nxt[2] - c[2]))
            if i in reps or (straight and run >= RUN):
                self.rep(c, (nxt[0] - c[0], nxt[2] - c[2]), net)
                run = 0
            else:
                self.dust(c, net)
                run += 1
        return run

    def riser(self, x, zr, d, top, net):
        """Glass zigzag from y=1 to top: dust at odd y in z=zr, at even y in z=zr+d."""
        self.put((x, 0, zr), SOLID)
        for y in range(1, top + 1):
            z = zr if y % 2 else zr + d
            self.put((x, y, z), WIRE, net)
            if y > 1:
                self.put((x, y - 1, z), GLASS)


def line(*pts):
    """Cells along axis-aligned waypoints (x, y, z), all at one y per leg."""
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        dx, dy, dz = ((b[i] > a[i]) - (b[i] < a[i]) for i in range(3))
        while out[-1] != b:
            c = out[-1]
            out.append((c[0] + dx, c[1] + dy, c[2] + dz))
    return out


def stair(start, flow, steps, dh):
    """Staircase from start moving flow (dx, dz) one cell per step, dh (+1/-1) a step."""
    x, y, z = start
    return [(x + flow[0] * t, y + dh * t, z + flow[1] * t) for t in range(steps + 1)]


def build(mutant=None):
    g = Regs()
    named, inputs, outputs, extra = {}, {}, {}, {}
    top = deck_y(DECKS - 1)

    # Stacks. Every master's lock and riser are north of it; slaves' are south.
    for k in range(DECKS):
        y = deck_y(k)
        for r in ("a", "b"):
            x = X[r]
            g.rep((x, y, Z0), (1, 0), f"m{r}{k}")
            g.rep((x, y, Z0 - 1), (0, 1), f"h{r}")
            g.rep((x + 1, y, Z0), (1, 0), f"s{r}{k}")
            if not (mutant == "slave_unlocked" and r == "a" and k == 0):
                g.rep((x + 1, y, Z0 + 1), (0, -1), f"n{r}")
            named[f"m{r}{k}"] = (x, y, Z0)
            named[f"s{r}{k}"] = (x + 1, y, Z0)
        g.rep((X["o"], y, Z0), (-1, 0), f"mo{k}")
        g.rep((X["o"], y, Z0 - 1), (0, 1), "ho")
        named[f"mo{k}"] = (X["o"], y, Z0)
    for k, (fin, fout) in enumerate((("zo", "z"), ("co", "c"))):
        y = deck_y(k)
        g.rep((XF, y, ZF), (1, 0), f"m{fout}")
        g.rep((XF, y, ZF - 1), (0, 1), "hf")
        named[f"m{fout}"] = (XF, y, ZF)
    for r in ("a", "b", "o"):
        g.riser(X[r], Z0 - 2, -1, top, f"h{r}")
    for r in ("a", "b"):
        g.riser(X[r] + 1, Z0 + 2, 1, top, f"n{r}")
    g.riser(XF, ZF - 2, -1, deck_y(1), "hf")

    # Data, one deck per bit.
    for k in range(DECKS):
        y = deck_y(k)
        ka, kb, ko, ky = f"a{k}", f"b{k}", f"o{k}", f"y{k}"
        xo, xa, xb = X["o"], X["a"], X["b"]
        # o: west to the out pin.
        g.path(line((xo - 1, y, Z0), (2, y, Z0)), ko)
        g.rep((1, y, Z0), (-1, 0), ko)
        g.dust((0, y, Z0), ko)
        outputs[f"out{k}"] = (0, y, Z0)
        # a: junction east of the A slave; to B, round the north to O, south to the port.
        g.path(line((xa + 2, y, Z0), (xa + 3, y, Z0)), ka)
        g.path(line((xa + 4, y, Z0), (xb - 1, y, Z0)), ka)
        g.path(line((xa + 3, y, Z0 - 1), (xa + 3, y, Z0 - 6), (xo + 2, y, Z0 - 6), (xo + 2, y, Z0),
                    (xo + 1, y, Z0)), ka, run=2)
        a_rows = line((xa + 3, y, Z0 + 1), (xa + 3, y, Z0 + 5), (COL["a"], y, Z0 + 5),
                      (COL["a"], y, band_row("a", k)), (X_DESCENT - 1, y, band_row("a", k)))
        # b: east to its column.
        b_rows = line((xb + 2, y, Z0), (COL["b"], y, Z0), (COL["b"], y, band_row("b", k)),
                      (X_DESCENT - 1, y, band_row("b", k)))
        # y: from its column west along the port row and north into A.
        y_rows = line((COL["y"], y, band_row("y", k)), (COL["y"], y, Z0 + 8), (xa - 2, y, Z0 + 8),
                      (xa - 2, y, Z0), (xa - 1, y, Z0))
        y_band = line((X_DESCENT - 1, y, band_row("y", k)), (COL["y"] + 1, y, band_row("y", k)))
        # descents of a and b, climb of y, at the east face
        for net, r, rows, run0, kn in (("a", band_row("a", k), a_rows, 2, ka),
                                       ("b", band_row("b", k), b_rows, 0, kb)):
            st = stair((X_DESCENT, y, r), (1, 0), y - 1, -1)
            run0 = g.path(rows + st, kn, run=run0, reps=(len(rows) - 1,))
            jog = X_JOG[net]
            g.path(line((st[-1][0] + 1, 1, r), (jog, 1, r), (jog, 1, r + 1), (E - 2, 1, r + 1)),
                   kn, run=run0)
            g.rep((E - 1, 1, r + 1), (1, 0), kn)
            g.dust((E, 1, r + 1), kn)
            outputs[f"{net}{k}"] = (E, 1, r + 1)
        ry = band_row("y", k)
        inputs[ky] = (E, 3, ry)
        g.put((E, 2, ry), SOLID)
        g.rep((E - 1, 3, ry), (-1, 0), ky)
        climb = stair((X_DESCENT + 2 * k, 3, ry), (-1, 0), 2 * k, 1)
        flat = line((E - 2, 3, ry), (X_DESCENT + 2 * k + 1, 3, ry)) if E - 2 > X_DESCENT + 2 * k else []
        g.path(flat + climb + y_band + y_rows, ky)
    # flags: in from the west face, out back to it below
    for k, (fin, fout) in enumerate((("zo", "z"), ("co", "c"))):
        y = deck_y(k)
        inputs[fin] = (0, y, ZF)
        g.put((0, y - 1, ZF), SOLID)
        g.rep((1, y, ZF), (1, 0), fin)
        g.path(line((2, y, ZF), (XF - 1, y, ZF)), fin)
        g.path(line((XF + 1, y, ZF), (XF + 2, y, ZF), (XF + 2, y, ZF + 3), (2, y, ZF + 3)), fout)
        g.rep((1, y, ZF + 3), (-1, 0), fout)
        g.dust((0, y, ZF + 3), fout)
        outputs[fout] = (0, y, ZF + 3)

    # Control deck. Master heads: hold = NOT cap OR NOT we, two torches beside the riser
    # base; cap from the west through a bus under the data row, we from the north face.
    def head(x, zb, net):
        g.torch((x - 1, 1, zb), (-1, 0), net)
        g.torch((x + 1, 1, zb), (1, 0), net)
        g.put((x - 1 - 1, 1, zb), SOLID)
        g.put((x + 1 + 1, 1, zb), SOLID)
        return (x - 2, 1, zb)

    inputs["cap"] = (0, 1, Z0)
    g.rep((1, 1, Z0), (1, 0), "cap")
    caps = []
    for r in ("o", "a", "b"):
        x = X[r]
        cb = head(x, Z0 - 2, f"h{r}")
        g.dust((cb[0], 1, Z0 - 1), "cap")
        caps.append(cb[0])
        wx = WE_PIN_X[r]
        inputs[f"w{r}"] = (wx, 1, 0)
        g.put((wx, 0, 0), SOLID)
        g.rep((wx, 1, 1), (0, 1), f"w{r}")
        g.path(line((wx, 1, 2), (wx, 1, Z0 - 3)), f"w{r}")
    g.path(line((2, 1, Z0), (max(caps), 1, Z0)), "cap", reps=(8,))
    # flags head: wf from the west face, cap north to the bus
    head(XF, ZF - 2, "hf")
    inputs["wf"] = (0, 1, ZF - 2)
    g.put((0, 0, ZF - 2), SOLID)
    g.rep((1, 1, ZF - 2), (1, 0), "wf")
    g.path(line((XF + 2, 1, ZF - 3), (XF + 2, 1, Z0 + 1)), "cap")
    # slave heads: NOT com torch beside each slave riser base, com from the south face
    for r in ("a", "b"):
        x = X[r] + 1
        g.torch((x + 1, 1, Z0 + 2), (1, 0), f"n{r}")
        g.put((x + 2, 1, Z0 + 2), SOLID)
        g.path(line((x + 2, 1, Z0 + 3), (x + 2, 1, Z0 + 4)), "com")
    zs = band_row("y", DECKS - 1) + 1
    inputs["com"] = (COM_X, 1, zs)
    g.put((COM_X, 0, zs), SOLID)
    g.rep((COM_X, 1, zs - 1), (0, -1), "com")
    g.path(line((COM_X, 1, zs - 2), (COM_X, 1, Z0 + 6)), "com")
    g.path(line((X["a"] + 3, 1, Z0 + 5), (X["b"] + 3, 1, Z0 + 5)), "com")

    for p in inputs.values():
        g.put((p[0], p[1] - 1, p[2]), SOLID)
    for p in list(g.b):
        if p[1] == 1 and (p[0], 0, p[2]) not in g.b:
            g.b[(p[0], 0, p[2])] = SOLID
    return g, inputs, outputs, named


def cpu_regs(name="cpu_regs", mutant=None) -> Spec:
    g, inputs, outputs, named = build(mutant)
    b = Build()
    for p, s in sorted(g.b.items()):
        b.place(p, s)
    spec = Spec(name, b, inputs=inputs, outputs=outputs, named={**named, **outputs},
                traits=["pistonless", "entityless", "torch_based"])
    spec.description = DESCRIPTION
    spec.tests = regs_tests()
    return spec


DESCRIPTION = (
    "CPU4 register file: A and B master/slave, OUT, Z and C single latches, all repeater latches. "
    "Bit k of A, B and OUT sits on deck y=3+2k (Z on deck 0, C on deck 1), so each register is a vertical "
    "stack of four latches like dl_lock_stack: masters at z=8 (OUT x=10, A x=16, B x=25), A and B slaves "
    "one block east. Every master is locked from the north by a repeater fed by its register's hold line, "
    "which climbs a glass zigzag (z=5/6) from a head of two wall torches on the control deck (y=1): "
    "hold = NOT cap OR NOT we. Every slave is locked from the south by a NOT com line climbing the same "
    "way (z=10/11). A takes y, B and OUT take a (A's slave), so SWAP is race-free; Z takes zo and C co. "
    "Each deck's a, b and y lines fan out east to that bit's band, then step down (a, b) or up (y) to "
    "the east-face pins, which match cpu_alu's west face (regs z = alu z + 11). Pins: east face b_k "
    "(49,1,18+7k), a_k (49,1,20+7k), y_k in (49,3,21+7k); west face cap (0,1,8), wf (0,1,12), "
    "out_k (0,3+2k,8), zo (0,3,14), co (0,5,14), z (0,3,17), c (0,5,17); north face wo (12,1,0), "
    "wa (18,1,0), wb (27,1,0); south face com (22,1,43). OUT, Z and C change during cap when enabled; "
    "A and B change after com.")


def bits(prefix, v, n=4):
    return {f"{prefix}{i}": (v >> i) & 1 for i in range(n)}


def cyc(drive=None, expect=None):
    """One 200 gt cycle: COM pulse, expect at +70, drive inputs, CAP pulse at +150."""
    s = [{"drive": {"com": 1}}, {"wait": 10}, {"drive": {"com": 0}}, {"wait": 60}]
    if expect:
        s.append({"expect": expect})
    if drive:
        s.append({"drive": drive})
    return s + [{"wait": 80}, {"drive": {"cap": 1}}, {"wait": 10}, {"drive": {"cap": 0}}, {"wait": 40}]


def regs_tests():
    zero = {**bits("b", 0), **bits("out", 0), "z": 0, "c": 0}
    load = []
    prev = None
    for v in (5, 10, 15, 0, 9, 6):
        load += cyc({"wa": 1, **bits("y", v)}, None if prev is None else {**bits("a", prev), **zero})
        prev = v
    load += cyc({"wa": 0}, {**bits("a", prev), **zero})
    swap = (cyc({"wa": 1, **bits("y", 5)}) + cyc({"wa": 0, "wb": 1}, bits("a", 5))
            + cyc({"wb": 0, "wa": 1, **bits("y", 10)}, bits("b", 5))
            + cyc({"wb": 1, **bits("y", 5)}, {**bits("a", 10), **bits("b", 5)})
            + cyc({**bits("y", 10)}, {**bits("a", 5), **bits("b", 10)})
            + cyc({"wa": 0, "wb": 0}, {**bits("a", 10), **bits("b", 5)})
            + cyc(None, {**bits("a", 10), **bits("b", 5)}))
    out = (cyc({"wa": 1, **bits("y", 9)}) + cyc({"wa": 0, "wo": 1}, bits("a", 9))
           + cyc({"wo": 0, "wa": 1, **bits("y", 6)}, {**bits("out", 9)})
           + cyc({"wa": 0}, {**bits("a", 6), **bits("out", 9)})
           + cyc({"wo": 1}, {**bits("out", 9)})
           + cyc({"wo": 0}, {**bits("out", 6), **bits("a", 6)}))
    flags = []
    prev = None
    for zo, co in ((1, 0), (0, 1), (1, 1), (0, 0)):
        flags += cyc({"wf": 1, "zo": zo, "co": co}, prev)
        prev = {"z": zo, "c": co}
    flags += cyc({"wf": 0, "zo": 1, "co": 1}, prev) + cyc(None, {"z": 0, "c": 0}) + cyc(None, {"z": 0, "c": 0})
    still = {**bits("a", 5), **bits("b", 5), **bits("out", 5), "z": 1, "c": 1}
    hold = (cyc({"wa": 1, "wb": 1, "wo": 1, "wf": 1, "zo": 1, "co": 1, **bits("y", 5)})
            + cyc({"wa": 0, "wb": 0, "wo": 0, "wf": 0, **bits("y", 10), "zo": 0, "co": 0},
                  {**bits("a", 5), **bits("b", 0), **bits("out", 0), "z": 1, "c": 1}))
    hold += cyc({"wb": 1, "wo": 1}) + cyc({"wb": 0, "wo": 0}, still)
    hold += [{"drive": {"com": 1}}, {"wait": 10}, {"drive": {"com": 0}}, {"wait": 30},
             {"drive": {"wa": 1, "wb": 1, "wo": 1, "wf": 1}}, {"wait": 30},
             {"drive": {"wa": 0, "wb": 0, "wo": 0, "wf": 0}}, {"wait": 30},
             {"drive": {"cap": 1}}, {"wait": 10}, {"drive": {"cap": 0}}, {"wait": 20},
             {"drive": {"wa": 1, "wb": 1, "wo": 1, "wf": 1}}, {"wait": 30}]
    hold += cyc({"wa": 0, "wb": 0, "wo": 0, "wf": 0}, still) + cyc(None, still)
    hold += [{"drive": {"com": 1}}, {"wait": 10}, {"drive": {"com": 0}}, {"wait": 40}, {"expect": still}]
    ys = {f"y{k}": 1 for k in range(DECKS)}
    ma, mo, sa = ([f"{c}{k}" for k in range(DECKS)] for c in ("ma", "mo", "sa"))
    outs, a = bits("out", 0), bits("a", 0)
    timing = [{"drive": {"wa": 1, **ys}}, {"wait": 20},
              {"drive": {"cap": 1}}, {"wave": {c: "0" * 10 for c in ma}},
              {"drive": {"cap": 0}}, {"wave": {c: "1" * 20 for c in ma}},
              {"drive": {"wa": 0, "wo": 1}}, {"wait": 20},
              {"drive": {"com": 1}}, {"wave": {c: "0" * 10 for c in sa + list(a)}},
              {"drive": {"com": 0}},
              {"wave": {**{c: "00" + "1" * 16 for c in sa}, **{f"a{k}": "0" * (12 + 2 * (k // 2)) + "1" * (6 - 2 * (k // 2))
                                                               for k in range(DECKS)}}},
              {"wait": 20}, {"drive": {"cap": 1}},
              {"wave": {**{c: "0" * 10 for c in outs}, **{c: "0" * 8 + "11" for c in mo}}},
              {"drive": {"cap": 0}}, {"wave": {c: "1" * 10 for c in list(outs) + mo}}]
    return [{"name": "load a", "steps": load}, {"name": "mov and swap", "steps": swap},
            {"name": "out", "steps": out}, {"name": "flags", "steps": flags},
            {"name": "holds without cap or enable", "steps": hold},
            {"name": "timing", "steps": timing}]
