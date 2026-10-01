"""cpu_alu generator: Y = (A - za) + (((B - xsel) | imm) xor sub) + sub over 4 bit slices.

Each slice is placed by hand (comparator bridges, the carry cell, lane taps) and the nets
between them are routed by scripts.alu_route; build_routed() is deterministic."""
from scripts.alu_route import Grid, Router, SOLID, WIRE, fix as fix_strength

SIZE = (48, 16, 32)
XC = 44
LANE = {"XS": 7, "ZA": 10, "I0": 13, "I1": 16, "I2": 19, "I3": 22, "SUB": 28}
Y5 = 5


def zrow(i):
    return 7 + 7 * i


def bridge(g, R, xb, d0, z, nets, a_from="east"):
    """Library xor_comparator_bridge, rows d0..d0+3 of band z. a enters row d0+1 (east rep at xb+3
    or north rep at (xb+2, d0)); b enters row d0+2 from the west (rep at xb). Returns cells."""
    a, b, o = nets
    Z = lambda d: z + d0 + d
    g.block((xb + 1, 1, Z(0)), o); g.strong.setdefault((xb + 1, 1, Z(0)), set()).add(o)
    g.cmp((xb + 1, 1, Z(1)), "n", o)
    g.dust((xb + 2, 1, Z(1)), a)
    if a_from == "east":
        g.rep((xb + 3, 1, Z(1)), "w", a)
        a_in = (xb + 4, 1, Z(1))
    else:
        g.rep((xb + 2, 1, Z(0)), "s", a)
        a_in = (xb + 2, 1, Z(-1))
    g.rep((xb, 1, Z(2)), "e", b)
    b_in = (xb - 1, 1, Z(2))
    g.dust((xb + 1, 1, Z(2)), b)
    g.cmp((xb + 2, 1, Z(2)), "s", o)
    g.block((xb + 1, 1, Z(3)))
    g.block((xb + 2, 1, Z(3)), o)
    g.dust((xb + 1, 2, Z(0)), o)
    g.block((xb + 1, 2, Z(1)))
    g.block((xb + 1, 2, Z(2)))
    g.dust((xb + 1, 2, Z(3)), o)
    g.dust((xb + 2, 2, Z(3)), o)
    g.dust((xb + 1, 3, Z(1)), o)
    g.dust((xb + 1, 3, Z(2)), o)
    for k in [(xb + 1, 3, Z(0)), (xb + 1, 3, Z(3)), (xb, 1, Z(1)), (xb + 3, 1, Z(2)),
              (xb + 2, 2, Z(2)), (xb + 2, 2, Z(1)), (xb, 2, Z(2)), (xb + 2, 3, Z(2)), (xb + 2, 3, Z(3)),
              (xb, 3, Z(1)), (xb + 2, 3, Z(1)), (xb, 2, Z(0)), (xb + 2, 2, Z(0)), (xb + 1, 2, Z(-1)),
              (xb + 1, 1, Z(-1)), (xb + 2, 1, Z(4)), (xb + 1, 1, Z(4))]:
        if k not in g.b:
            R.keep.add(k)
    R.mark_input(a_in, a)
    R.mark_input(b_in, b)
    return a_in, b_in, (xb + 2, 2, Z(3))


def tap(g, R, lane_x, d, z, net, to_x):
    """Stair from lane (lane_x, 5) down to dust at (to_x, 2, z+d) on a block; to_x = lane_x -/+ 3."""
    s = -1 if to_x < lane_x else 1
    zz = z + d
    g.dust((lane_x + s, 4, zz), net)
    g.dust((lane_x + 2 * s, 3, zz), net)
    g.dust((lane_x + 3 * s, 2, zz), net)
    R.keep.add((lane_x + s, 5, zz)); R.keep.add((lane_x + 2 * s, 4, zz)); R.keep.add((lane_x + 3 * s, 3, zz))
    return (lane_x + 3 * s, 1, zz)


def build(mutant=None):
    g = Grid(SIZE)
    R = Router(g, ymax=6)
    inputs, outputs, named = {}, {}, {}
    last_tap = {"XS": 3, "ZA": 3, "SUB": 3, "I0": 0, "I1": 1, "I2": 2, "I3": 3}
    # lanes: pin at (L,5,0), rep at (L,5,1), dust to the last tap row
    for name, L in LANE.items():
        i = last_tap[name]
        dlast = {"XS": -2, "ZA": 1, "SUB": -1}.get(name, -2)
        zend = zrow(i) + dlast
        inputs[name] = (L, 5, 0)
        g.block((L, 4, 0))
        g.rep((L, 5, 1), "s", name)
        for z in range(2, zend + 1):
            g.dust((L, 5, z), name)
    terms = {}  # net -> list of goal cells to route later
    for i in range(4):
        z = zrow(i)
        Z = lambda d: z + d
        n = lambda s: f"{s}{i}"
        # ---- chain column (y=2) and interface
        for d in range(-3, 4):
            if d != 2:
                g.block((XC, 1, Z(d)))
            g.block((XC, 3, Z(d)))
        if i == 0:
            g.dust((XC, 2, Z(-3)), "SUB"); g.dust((XC, 2, Z(-2)), "SUB"); g.rep((XC, 2, Z(-1)), "s", n("c"))
        else:
            for d in (-3, -2, -1):
                g.dust((XC, 2, Z(d)), n("c"))
        g.dust((XC, 2, Z(0)), n("c"))
        named[f"c{i}"] = (XC, 2, Z(0))
        g.cmp((XC, 2, Z(1)), "s", n("cc"))
        g.block((XC, 2, Z(2)), n("cc"))
        g.strong.setdefault((XC, 2, Z(2)), set()).update({n("cc"), n("gen")})
        nxt = f"c{i + 1}" if i < 3 else "c4"
        if i < 3:
            g.dust((XC, 2, Z(3)), nxt)
        else:
            g.dust((XC, 2, Z(3)), nxt)  # link dust u3 of the last cell, read by the co repeater
        g.block((XC, 1, Z(2)))
        # Gen = X' - P into B from the east
        g.cmp((XC + 1, 2, Z(2)), "w", n("gen"))
        g.block((XC + 2, 2, Z(2)), n("xpb"))
        g.rep((XC + 2, 2, Z(1)), "s", n("xpb"))
        g.dust((XC + 2, 2, Z(0)), n("xpb"))
        g.block((XC + 1, 2, Z(0)), n("p")); R.mark_input((XC + 1, 2, Z(0)), n("p"))
        g.rep((XC + 1, 2, Z(1)), "s", n("pg"))
        g.block((XC + 2, 3, Z(0)))
        R.keep.add((XC + 1, 2, Z(3)))
        g.block((XC - 1, 1, Z(1)))
        g.rep((XC - 1, 2, Z(1)), "e", n("kill"))
        R.mark_input((XC - 2, 2, Z(1)), n("np"))
        g.block((XC - 1, 1, Z(-2)))
        g.rep((XC - 1, 2, Z(-2)), "w", n("cp"))
        g.dust((XC - 2, 2, Z(-2)), n("cp"))
        R.keep.add((XC - 1, 2, Z(2)))
        # nP: torch (42,2,d0) on block (41,2,d0) powered by P lights (42,2,d1), read by the kill repeater
        g.block((41, 2, Z(0)), n("p")); R.mark_input((41, 2, Z(0)), n("p"))
        g.wall_torch((42, 2, Z(0)), "w", n("np"))
        g.dust((42, 2, Z(1)), n("np"))
        g.block((42, 2, Z(2)))
        for k in [(42, 3, Z(0)), (42, 1, Z(0)), (42, 2, Z(-1)), (41, 1, Z(0))]:
            R.keep.add(k)
        # P bridge at 29, rows d-2..d1: a = Ae (east), b = X' (west)
        a_in, b_in, p_out = bridge(g, R, 31, -2, z, (n("xpr"), n("aer"), n("p")))
        # sum bridge at 34, rows d-1..d2: a = cp (north), b = P (west)
        a2, b2, s_out = bridge(g, R, 36, -1, z, (n("cpr"), n("pr"), n("y")), a_from="north")
        named[f"s{i}"] = s_out
        R.keep.add((38, 3, Z(4))); R.keep.add((38, 2, Z(4)))
        for net, cell in [("p", b2), ("cp", a2), ("xp", a_in), ("ae", b_in),
                          ("p", (41, 3, Z(0))), ("xpb", (46, 2, Z(-1))), ("p", (45, 3, Z(0)))]:
            g.dust(cell, n(net))
            R.inputs[cell] = n(net)
            terms.setdefault(i, []).append((n(net), cell))
        # ---- front zone
        inputs[f"b{i}"] = (0, 1, Z(0))
        g.block((0, 0, Z(0)))
        g.rep((1, 1, Z(0)), "e", n("b"))
        g.dust((2, 1, Z(0)), n("b")); g.dust((3, 1, Z(0)), n("b"))
        g.cmp((4, 1, Z(0)), "e", n("x0"))
        g.rep((4, 1, Z(-1)), "s", n("xsr"))
        g.block((4, 1, Z(-2)))
        tap(g, R, LANE["XS"], -2, z, "XS", 4)
        for x in range(5, 9):
            g.dust((x, 1, Z(0)), n("x0"))
        g.rep((9, 1, Z(0)), "e", n("x"))
        for x in range(10, 21):
            g.dust((x, 1, Z(0)), n("x"))
        Li = LANE[f"I{i}"]
        g.rep((Li - 3, 1, Z(-1)), "s", n("x"))
        g.block((Li - 3, 1, Z(-2)))
        tap(g, R, Li, -2, z, f"I{i}", Li - 3)
        a_x, b_x, xp_out = bridge(g, R, 21, -2, z, (n("subr"), n("x"), n("xp")))
        g.block(a_x)
        tap(g, R, LANE["SUB"], -1, z, "SUB", 25)
        for x in (24, 25, 26):
            g.dust((x, 2, Z(1)), n("xp"))
        g.rep((27, 2, Z(1)), "e", n("xpb")); g.dust((28, 2, Z(1)), n("xpb"))
        g.block((28, 2, Z(0)))
        for x in range(2, 30):
            if x in (8, 20):
                g.rep((x, 3, Z(3)), "w", n("y"))
            else:
                g.dust((x, 3, Z(3)), n("y"))
        for x in range(30, 38):
            if x == 33:
                g.rep((x, 4, Z(3)), "w", n("y"))
            else:
                g.dust((x, 4, Z(3)), n("y"))
        g.dust((38, 3, Z(3)), n("y"))

        R.keep.add((29, 4, Z(3))); R.keep.add((38, 4, Z(3)))
        # A stream and ZA
        inputs[f"a{i}"] = (0, 1, Z(2))
        g.block((0, 0, Z(2)))
        g.rep((1, 1, Z(2)), "e", n("a"))
        g.dust((2, 1, Z(2)), n("a"))
        for x in range(2, 7):
            g.dust((x, 1, Z(3)), n("a"))
        g.cmp((7, 1, Z(3)), "e", n("ae0"))
        g.dust((8, 1, Z(3)), n("ae0"))
        g.rep((9, 1, Z(3)), "e", n("ae1"))
        for x in range(10, 21):
            g.dust((x, 1, Z(3)), n("ae1"))
        g.rep((21, 1, Z(3)), "e", n("ae2"))
        for x in range(22, 27):
            g.dust((x, 1, Z(3)), n("ae2"))
        g.rep((27, 1, Z(3)), "e", n("ae"))
        g.dust((28, 1, Z(3)), n("ae"))
        g.rep((7, 1, Z(2)), "s", n("zar"))
        g.block((7, 1, Z(1)))
        tap(g, R, LANE["ZA"], 1, z, "ZA", 7)
        g.block((7, 2, Z(0))); g.block((8, 2, Z(0))); g.block((6, 2, Z(0)))
        # Y pin at (0,3,d3)
        g.dust((0, 3, Z(3)), n("y")); g.block((0, 2, Z(3)))
        outputs[f"y{i}"] = (0, 3, Z(3))
        g.rep((1, 3, Z(3)), "w", n("y"))

    # SUB to the chain's carry-in (tile 0, rows z 4..5)
    for x in range(29, 41):
        if x == 34:
            g.rep((x, 5, 2), "e", "SUB")
        else:
            g.dust((x, 5, 2), "SUB")
    for c in [(40, 5, 3), (41, 4, 3), (42, 3, 3), (43, 2, 3), (44, 2, 3)]:
        g.dust(c, "SUB")
    # co is the carry out of bit 3: the link dust on the south face, lit by B3
    outputs["co"] = (XC, 2, zrow(3) + 3)
    R.keep.add((XC + 1, 2, zrow(3) + 3)); R.keep.add((XC - 1, 2, zrow(3) + 3))
    return g, R, inputs, outputs, named, terms


ORDER = ["ae", "xp", "xpb", "p", "cp", "y"]


def route_all(g, R, terms, rows=None):
    fails = []
    goals = {c for i in terms for _, c in terms[i]}
    order = sorted(((k, i) for i in range(4) for k in range(len(terms[i]))), key=lambda t: (t[0], -t[1]))
    for k, i in order:
        net, goal = terms[i][k]
        R.zlim = rows(i, net) if rows else (zrow(i) - 4 if i else 1, min(zrow(i) + 4, 31))
        conn = [c for c, nn in g.net.items() if nn == net and c not in goals and g.b.get(c) == WIRE
                and not (net.startswith("y") and c[0] < 34) and not (net.startswith("xpb") and c[0] >= 45)]
        try:
            R.route(net, conn, goal)
            goals.discard(goal)
        except RuntimeError as e:
            fails.append(str(e))
    R.zlim = None
    return fails


if __name__ == "__main__":
    g, R, ins, outs, named, terms = build()
    errs = g.check()
    print("pre-route check:", len(errs)); print("\n".join(errs[:30]))
    fails = route_all(g, R, terms)
    print("route fails:", fails)
    errs = g.check()
    print("post-route check:", len(errs)); print("\n".join(errs[:30]))
    for y in range(1, 6):
        print("y", y)
        print(g.show(y, 0, 14))


def build_routed(seed_max=300):
    import random
    for seed in range(seed_max):
        g, R, ins, outs, named, terms = build()
        if seed:
            rnd = random.Random(seed)
            for i in terms:
                head, tail = terms[i][:2], terms[i][2:]
                rnd.shuffle(tail)
                terms[i] = head + tail
        f = route_all(g, R, terms)
        if not f:
            try:
                fix_strength(g)
            except RuntimeError as e:
                f = [str(e)]
                continue
            return g, ins, outs, named, seed
    raise RuntimeError(f"no routing found: {f}")


PINS = {"XS": "xsel", "ZA": "za", "SUB": "sub", **{f"I{i}": f"imm{i}" for i in range(4)}}
GRAY = [i ^ (i >> 1) for i in range(16)]


def _row(a, b, xsel=0, za=0, sub=0, imm=0):
    x = imm if xsel else b
    t = (0 if za else a) + ((15 - x) if sub else x) + sub
    ins = [a >> i & 1 for i in range(4)] + [b >> i & 1 for i in range(4)] + [xsel, za, sub] + [imm >> i & 1 for i in range(4)]
    outs = [t >> i & 1 for i in range(4)] + [t >> 4 & 1]
    return " ".join(map(str, ins)) + " | " + " ".join(map(str, outs))


HEAD = " ".join([f"a{i}" for i in range(4)] + [f"b{i}" for i in range(4)] + ["xsel", "za", "sub"]
                + [f"imm{i}" for i in range(4)]) + " | y0 y1 y2 y3 co"


def _table(rows):
    return HEAD + "\n" + "\n".join(rows) + "\n"


def alu_tests():
    pairs = [(a, b) for k, a in enumerate(GRAY) for b in (GRAY if k % 2 == 0 else GRAY[::-1])]
    add = [_row(a, b) for a, b in pairs]
    sub = [_row(a, b, sub=1) for a, b in pairs]
    imm = [_row(b ^ 10, b, za=1) for b in GRAY]                       # pass b (SWAP)
    imm += [_row(n ^ 6, n ^ 9, xsel=1, za=1, imm=n) for n in GRAY]      # pass imm (LDI)
    imm += [_row(a, a ^ 5, xsel=1, imm=n) for a in GRAY[:8] for n in (GRAY if a % 2 else GRAY[::-1])[:8]]
    imm += [_row(a, a ^ 3, xsel=1, sub=1, imm=n) for a in GRAY[8:] for n in GRAY[8:]]
    t = {"settle": 60, "max_delay": 48}
    return [{"name": "add", "truth_table": _table(add), **t},
            {"name": "sub", "truth_table": _table(sub), **t},
            {"name": "pass and imm", "truth_table": _table(imm), **t}]


def cpu_alu(name="cpu_alu", mutant=False):
    from redstone.build import Build
    from redstone.fileformat import Spec
    g, ins, outs, named, seed = build_routed()
    if mutant:
        # cut the carry link from bit 1 to bit 2
        del g.b[(XC, 2, zrow(1) + 3)]
    b = Build()
    for p, s in sorted(g.b.items()):
        b.place(p, s)
    inputs = {PINS.get(k, k): v for k, v in ins.items()}
    spec = Spec(name, b, inputs=inputs, outputs=dict(outs),
                named={f"c{i}": named[f"c{i}"] for i in range(1, 4)} | dict(outs),
                traits=["pistonless", "entityless", "comparator_based"])
    spec.description = (
        "CPU4 ALU, arithmetic: y = (a - za) + (((b - xsel) | imm) xor sub) + sub, co = carry out "
        "(for sub, 1 = no borrow). Covers ADD, SUB, ADDI, SUBI (imm already gated by xsel in the "
        "decoder) and the pass ops LDI and SWAP (za zeroes a). Four bit slices 7 rows apart along z; "
        "in each, a comparator mux and xor bridge form X' = ((b - xsel) | imm) xor sub, a second bridge "
        "forms P = a xor X', and a carry-cancel chain at x=44, y=2 takes NOT P (a torch) on the cancel "
        "comparator's side and Gen = X' - P from the east; the sum bridge reads the carry tapped off the "
        "chain. Pins: b_i (0,1,7+7i), a_i (0,1,9+7i), y_i out (0,3,10+7i); control lanes enter the north "
        "face at y=5: xsel x=7, za 10, imm0-3 13/16/19/22, sub 28; co is the chain's last link at (44,2,31). "
        "Hand-placed cells, nets routed by scripts/alu_route.py.")
    spec.tests = alu_tests()
    return spec
