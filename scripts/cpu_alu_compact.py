"""CPU4 ALU, compact: x = n if xsel else b; y = (a - za) + (x xor sub) + sub; co, zo.

Bit k owns z rows 1+8k .. 8+8k; inside the generator Z(d) = 4+8k+d, d = -3..4. The cells are
the old cpu_alu's (scripts/alu.py: comparator xor bridges, the carry-cancel chain at x=XC, y=2),
with a comparator mux in front: x = (n - NOT xsel) | (b - xsel). a, b and y meet the east face
(REGS abuts there); n and the controls enter the west face. Control lanes run along z at y=5;
nets between hand-placed cells are routed by scripts.alu_route.
"""
import heapq
import random

from scripts.alu_route import Grid as _Grid, Router, SOLID, WIRE, H4, fix as fix_strength
from scripts.alu import bridge, GRAY

BITS = 4
PITCH = 8
E = 43                      # east face x
SIZE = (E + 1, 8, 39)
HW = {"a": (-3, 27), "b": (3, 11)}   # highways at y=5: band row d, west end x
XC = 33                     # carry chain column
LANE = {"XS": 9, "SUB": 17, "ZA": 26}
LY = 7                      # control lanes run along z at this height
CTL_Z = {"XS": 34, "SUB": 36, "ZA": 38}
LANE_END = {"XS": 2, "SUB": 0, "ZA": 2}
S_X = 24
COLL = XC - 4               # zero collector column, y=7
COLL_REPS = (12, 28)
CY = 7
TAP_D = 4
ZO_Z, CO_Z = 33, 35
CARRY_NETS = ("c", "cc", "gen", "kill", "np", "pg", "cp", "co", "SUBC", "xpb")
PINS = {"XS": "xsel", "ZA": "za", "SUB": "sub"}


def zrow(k):
    return 4 + 8 * k


class Grid(_Grid):
    """alu_route.Grid that records the circuit of every cell it places."""
    def __init__(self, size):
        super().__init__(size)
        self.circuit = "alu"
        self.of = {}

    def put(self, p, state, net=None, support=True):
        had = set(self.b)
        r = super().put(p, state, net, support)
        for q in set(self.b) - had:
            self.of[q] = self.circuit
        return r


class FixedRouter(Router):
    """alu_route.Router whose A* also refuses a step onto the column of an earlier path cell two
    levels away: the cell between must be air for the diagonal step and solid as a support."""

    def route(self, net, starts, goal, maxlen=14, max_nodes=200000):
        """starts: existing cells of the net (dust or anything powered); goal: cell to become dust."""
        g = self.g
        reserved = g.b.get(goal) == WIRE and g.net.get(goal) == net
        if reserved:
            del g.b[goal]; del g.net[goal]
        def h(c):
            return abs(c[0] - goal[0]) + abs(c[1] - goal[1]) * 2 + abs(c[2] - goal[2])
        self.cov = {}
        openl = []
        prev = {}
        cost = {}
        for s in starts:
            cost[s] = 0
            heapq.heappush(openl, (h(s), 0, s))
        found = None
        n = 0
        while openl and n < max_nodes:
            n += 1
            f, gc, c = heapq.heappop(openl)
            if c == goal:
                found = c
                break
            if gc > cost.get(c, 1e9):
                continue
            x, y, z = c
            for dx, dz in H4:
                for dy in (0, 1, -1):
                    q = (x + dx, y + dy, z + dz)
                    if dy == 1 and g.b.get((x, y + 1, z)) == SOLID:
                        continue
                    if dy == 1 and (x, y + 1, z) in self.keep_solid_cells():
                        continue
                    if dy == -1 and g.b.get((x + dx, y, z + dz)) == SOLID:
                        continue
                    r = self.ok(q, net, None)
                    if not r:
                        continue
                    must_air = set()
                    chain = [q, c]
                    cc = c
                    for _ in range(60):
                        if cc not in prev:
                            break
                        chain.append(prev[cc]); cc = prev[cc]
                    for a, b in zip(chain, chain[1:]):
                        if a[1] != b[1]:
                            lo = a if a[1] < b[1] else b
                            must_air.add((lo[0], lo[1] + 1, lo[2]))
                    sup = (q[0], q[1] - 1, q[2])
                    if q in must_air or (sup in must_air and g.b.get(sup) is None):
                        continue
                    if r is not True and any(cv in must_air for cv in r):
                        continue
                    if any((cv[0], cv[1] - 1, cv[2]) == q for cv in ()):
                        continue
                    bad = False
                    for p in chain[2:]:
                        if p[1] - 1 == q[1] and p[0] == q[0] and p[2] == q[2]:
                            bad = True
                    for p in chain[1:]:
                        if p[0] == q[0] and p[2] == q[2] and abs(p[1] - q[1]) == 2:
                            bad = True
                    if bad:
                        continue
                    if dy == 1 and c in self.cov and (c[0], c[1] + 1, c[2]) in self.cov[c]:
                        continue
                    # path cells must not be consecutive-adjacent to older path cells (self loops fine)
                    nc = gc + 1 + (2 if dy else 0)
                    if r is not True:
                        nc += 3 * len(r)
                    if nc < cost.get(q, 1e9):
                        if r is not True:
                            self.cov[q] = r
                        else:
                            self.cov.pop(q, None)
                        cost[q] = nc
                        prev[q] = c
                        heapq.heappush(openl, (nc + h(q), nc, q))
        if not found:
            if reserved:
                g.b[goal] = WIRE; g.net[goal] = net
            raise RuntimeError(f"no route for {net} to {goal}")
        path = []
        c = found
        while c in prev:
            path.append(c)
            c = prev[c]
        attach = c
        path.reverse()
        full = [attach] + path
        level = self.start_level
        reps = set()
        for k in range(1, len(full)):
            level -= 1
            a, b = full[k - 1], full[k]
            nx = full[k + 1] if k + 1 < len(full) else None
            if level <= 3 and nx is not None and a[1] == b[1] == nx[1] and (b[0] - a[0], b[2] - a[2]) == (nx[0] - b[0], nx[2] - b[2]):
                reps.add((b, (nx[0] - b[0], nx[2] - b[2])))
                level = 15
        rep_at = dict(reps)
        for i, c in enumerate(path):
            nxt = path[i + 1] if i + 1 < len(path) else None
            prv = path[i - 1] if i else attach
            if c in rep_at:
                d = {(1, 0): "e", (-1, 0): "w", (0, 1): "s", (0, -1): "n"}[rep_at[c]]
                g.rep(c, d, net)
            else:
                g.dust(c, net)
            for cv in self.cov.get(c, ()):
                if cv not in g.b:
                    g.b[cv] = SOLID
            for o in (prv, nxt):
                if o is not None and o[1] != c[1]:
                    lo = c if c[1] < o[1] else o
                    self.keep.add((lo[0], lo[1] + 1, lo[2]))
        return path


def carry_net(net):
    base = net.rstrip("0123456789")
    return base in CARRY_NETS


def tap(g, R, lane_x, d, z, net, to_x, steps=LY - 2):
    """Stair from lane (lane_x, LY) down `steps` cells to dust on a block; to_x = lane_x -/+ steps."""
    s = -1 if to_x < lane_x else 1
    zz = z + d
    for k in range(1, steps + 1):
        g.dust((lane_x + k * s, LY - k, zz), net)
        R.keep.add((lane_x + k * s, LY - k + 1, zz))
    return (lane_x + (LY - 2) * s, 1, zz)


def lane(g, R, name):
    """West pin at (0,1,CTL_Z) -> repeater -> stair to y=5 -> east along the row -> north at x=LANE."""
    zp, L = CTL_Z[name], LANE[name]
    for dz in (-1, 0, 1):
        if zp + dz < SIZE[2]:
            g.block((0, 0, zp + dz))
    g.rep((1, 1, zp), "e", name)
    g.dust((2, 1, zp), name)
    for k in range(1, LY):
        g.dust((2 + k, 1 + k, zp), name)
        R.keep.add((1 + k, 1 + k, zp))
    for x in range(LY + 2, L + 1):
        g.dust((x, LY, zp), name)
    for z in range(LANE_END[name], zp):
        g.dust((L, LY, z), name)
    R.keep.add((0, 1, zp))
    return (0, 1, zp)


def build(mutant=None):
    g = Grid(SIZE)
    R = FixedRouter(g, ymax=7)
    R.keep_solid_cells = lambda: ()
    inputs, outputs, named = {}, {}, {}
    for name in LANE:
        inputs[PINS[name]] = lane(g, R, name)
    g.circuit = "alu"
    terms = []   # (band, net, starts, goal)
    for i in range(BITS):
        z = zrow(i)
        Z = lambda d: z + d
        n = lambda s: f"{s}{i}"
        # ---- n pin and mux: x = (n - NXS) | (b - XS)
        inputs[f"n{i}"] = (0, 1, Z(0))
        for dz in (-1, 0, 1):
            g.block((0, 0, Z(dz)))
        R.keep.add((0, 1, Z(0)))
        g.rep((1, 1, Z(0)), "e", n("n"))
        for x in (2, 3, 4):
            g.dust((x, 1, Z(0)), n("n"))
        # n - NXS: NXS is dust under a wall torch hung on T, a block xsel's tap dust sits on
        g.block((5, 2, Z(-2))); R.mark_input((5, 2, Z(-2)), "XS")
        tap(g, R, LANE["XS"], -2, z, "XS", 5, steps=4)
        g.wall_torch((5, 2, Z(-1)), "n", n("nxs"))
        g.dust((5, 1, Z(-1)), n("nxs"))
        g.cmp((5, 1, Z(0)), "e", n("x"))
        g.dust((6, 1, Z(0)), n("x")); g.dust((7, 1, Z(0)), n("x"))
        # b - XS: T2 tapped by xsel, a repeater into the gate's west side, output north into x
        g.block((4, 1, Z(1))); R.mark_input((4, 1, Z(1)), "XS")
        tap(g, R, LANE["XS"], 1, z, "XS", 4)
        g.rep((5, 1, Z(1)), "e", n("xsr"))
        g.cmp((6, 1, Z(1)), "n", n("x"))
        g.block((4, 2, Z(0)))
        for c in [(10, 4, Z(3)), (9, 3, Z(3)), (8, 2, Z(3)), (7, 1, Z(3)), (6, 1, Z(3)), (6, 1, Z(2))]:
            g.dust(c, n("b"))
        R.keep.update({(10, 5, Z(3)), (9, 4, Z(3)), (8, 3, Z(3)), (7, 2, Z(3))})
        for k in [(4, 1, Z(-1)), (6, 1, Z(-1)), (7, 1, Z(1)), (5, 3, Z(-1)), (5, 1, Z(2)), (7, 1, Z(2)),
                  (4, 2, Z(-1)), (6, 2, Z(-1)), (5, 2, Z(0)), (6, 2, Z(1))]:
            if k not in g.b:
                R.keep.add(k)
        # ---- X' = x xor sub (xor_comparator_bridge)
        a_x, _, xp_out = bridge(g, R, 8, -2, z, (n("subr"), n("x"), n("xp")))
        g.block(a_x); R.mark_input(a_x, "SUB")
        tap(g, R, LANE["SUB"], -1, z, "SUB", 12)
        for x in (11, 12, 13):
            g.dust((x, 2, Z(1)), n("xp"))
        g.rep((14, 2, Z(1)), "e", n("xpb")); g.dust((15, 2, Z(1)), n("xpb"))
        # ---- P = A' xor X': X' from the west, A' from the north
        p_ae, p_xp, p_out = bridge(g, R, 18, -2, z, (n("ae"), n("xpr"), n("p")), a_from="north")
        # A' = a - za: comparator at (21,1,Z-3) facing west into the bridge's north input
        g.dust(p_ae, n("ae"))
        g.cmp((21, 1, Z(-3)), "w", n("ae"))
        g.rep((21, 1, Z(-2)), "n", n("zar"))
        g.block((21, 1, Z(-1))); R.mark_input((21, 1, Z(-1)), "ZA")
        g.block((20, 2, Z(-1)))
        tap(g, R, LANE["ZA"], -1, z, "ZA", 21)
        R.keep.add((21, 1, Z(-4)))
        for c in [(22, 1, Z(-3)), (23, 1, Z(-3)), (24, 2, Z(-3)), (25, 3, Z(-3)), (26, 4, Z(-3))]:
            g.dust(c, n("a"))
        R.keep.update({(23, 2, Z(-3)), (24, 3, Z(-3)), (25, 4, Z(-3)), (26, 5, Z(-3))})
        # ---- sum bridge y = cp xor P
        s_cp, s_p, s_out = bridge(g, R, S_X, -1, z, (n("cpr"), n("pr"), n("y")), a_from="north")
        R.keep.add((S_X + 2, 3, Z(4))); R.keep.add((S_X + 2, 2, Z(4)))
        # ---- carry chain (y=2) at XC
        g.circuit = "carry"
        for d in range(-3, 5):
            if d != 2:
                g.block((XC, 1, Z(d)))
            g.block((XC, 3, Z(d)))
        if i == 0:
            g.dust((XC, 2, Z(-3)), "SUB"); g.dust((XC, 2, Z(-2)), "SUB")
            g.rep((XC, 2, Z(-1)), "s", n("c"))
        else:
            for d in (-3, -2, -1):
                g.dust((XC, 2, Z(d)), n("c"))
        g.dust((XC, 2, Z(0)), n("c"))
        named[f"c{i}"] = (XC, 2, Z(0))
        g.cmp((XC, 2, Z(1)), "s", n("cc"))
        g.block((XC, 2, Z(2)), n("cc"))
        g.strong.setdefault((XC, 2, Z(2)), set()).update({n("cc"), n("gen")})
        nxt = f"c{i + 1}" if i < 3 else "co"
        g.dust((XC, 2, Z(3)), nxt)
        g.rep((XC, 2, Z(4)), "s", nxt)       # restores the carry: B is only as strong as cc's output
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
        g.block((XC - 1, 1, Z(-2)))
        g.rep((XC - 1, 2, Z(-2)), "w", n("cp"))
        g.dust((XC - 2, 2, Z(-2)), n("cp"))
        R.keep.add((XC - 1, 2, Z(2)))
        g.block((XC - 3, 2, Z(0)), n("p")); R.mark_input((XC - 3, 2, Z(0)), n("p"))
        g.wall_torch((XC - 2, 2, Z(0)), "w", n("np"))
        g.dust((XC - 2, 2, Z(1)), n("np"))
        g.block((XC - 2, 2, Z(2)))
        for k in [(XC - 2, 3, Z(0)), (XC - 2, 1, Z(0)), (XC - 2, 2, Z(-1)), (XC - 3, 1, Z(0))]:
            R.keep.add(k)
        g.circuit = "alu"
        # ---- east pins: y out (Z-3), a in (Z0), b in (Z2)
        for d, nm, io in [(-3, "y", "out"), (0, "a", "in"), (2, "b", "in")]:
            for dz in (-1, 0, 1):
                g.block((E, 0, Z(d) + dz))
            for dz in (-1, 1):
                for yy in (1, 2):
                    R.keep.add((E, yy, Z(d) + dz))
            if io == "in":
                inputs[n(nm)] = (E, 1, Z(d))
                R.keep.add((E, 1, Z(d)))
                g.rep((E - 1, 1, Z(d)), "w", n(nm))
                x0 = E - 2
                g.dust((x0, 1, Z(d)), n(nm))
                hd, hx = HW[nm]
                for k in range(1, 5):
                    g.dust((x0 - k, 1 + k, Z(d)), n(nm))
                    R.keep.add((x0 + 1 - k, 1 + k, Z(d)))
                xz = x0 - 4
                step = 1 if hd > d else -1
                for zz in range(Z(d) + step, Z(hd) + step, step):
                    g.dust((xz, 5, zz), n(nm))
                for x in range(hx, xz):
                    g.dust((x, 5, Z(hd)), n(nm))
            else:
                g.dust((E, 1, Z(d)), n("yo"))
                outputs[n(nm)] = (E, 1, Z(d))
                g.rep((E - 1, 1, Z(d)), "e", n("yo"))
        # zero tap: y -> repeater into the collector
        g.rep((COLL + 1, CY, Z(TAP_D)), "w", "yany")
        terms.append((i, n("xpb"), [(15, 2, Z(1))], p_xp))
        terms.append((i, n("xpb"), None, (XC + 2, 2, Z(-1))))
        terms.append((i, n("p"), [p_out], s_p))
        terms.append((i, n("p"), None, (XC - 3, 3, Z(0))))
        terms.append((i, n("p"), None, (XC + 1, 3, Z(0))))
        terms.append((i, n("cp"), [(XC - 2, 2, Z(-2))], s_cp))
        terms.append((i, n("y"), [s_out], (E - 2, 1, Z(-3))))
        terms.append((i, n("y"), None, (COLL + 2, CY, Z(TAP_D))))
        named[f"s{i}"] = s_out
    # zero collector: OR of the y taps flowing south into a block; zo = torch on it
    for zz in range(zrow(0) + TAP_D, ZO_Z + 2):
        if zz in COLL_REPS:
            g.rep((COLL, CY, zz), "s", "yany")
        else:
            g.dust((COLL, CY, zz), "yany")
    g.block((COLL, CY, ZO_Z + 2))
    g.wall_torch((COLL + 1, CY, ZO_Z + 2), "w", "zo")
    g.dust((COLL + 2, CY, ZO_Z + 2), "zo")
    for k in [(COLL + 1, CY, ZO_Z + 1), (COLL + 1, CY, ZO_Z + 3), (COLL + 1, CY - 1, ZO_Z + 2)]:
        R.keep.add(k)
    for nm, zz in [("zo", ZO_Z), ("co", CO_Z)]:
        for dz in (-1, 0, 1):
            g.block((E, 0, zz + dz))
        g.dust((E, 1, zz), nm + "o")
        g.rep((E - 1, 1, zz), "e", nm + "o")
        outputs[nm] = (E, 1, zz)
        for dz in (-1, 1):
            for yy in (1, 2):
                R.keep.add((E, yy, zz + dz))
    terms.append((None, "SUB", [(LANE["SUB"], LY, z) for z in range(0, 6)], (XC, 2, 0)))
    terms.append((None, "co", [(XC, 2, zrow(3) + 4)], (E - 2, 1, CO_Z)))
    terms.append((None, "zo", [(COLL + 2, CY, ZO_Z + 2)], (E - 2, 1, ZO_Z)))
    g.block((E - 2, 2, ZO_Z))
    if mutant == "carry":
        g.b[(XC, 2, zrow(1) + 4)] = SOLID   # cut the carry link from bit 1 to bit 2
    return g, R, inputs, outputs, named, terms


ORDER = ["SUB", "xpb", "p", "cp", "y", "co", "zo"]


def route_all(g, R, terms, shuffle=None):
    fails = []
    goals = {t[3] for t in terms}
    order = sorted(range(len(terms)), key=lambda k: (ORDER.index(terms[k][1].rstrip("0123456789")), k))
    if shuffle is not None:
        rnd = random.Random(shuffle)
        order = sorted(order, key=lambda k: (ORDER.index(terms[k][1].rstrip("0123456789")) + rnd.random() * 2.5))
    for k in order:
        i, net, starts, goal = terms[k]
        R.zlim = (zrow(i) - 3, zrow(i) + 4) if i is not None else (((0, 2)) if net == "SUB" else (zrow(3), SIZE[2] - 1))
        if starts is None:
            starts = [c for c, nn in g.net.items() if nn == net and g.b.get(c) == WIRE and c not in goals
                      and c in routed.get(net, ())]
        R.inputs[goal] = net
        g.circuit = "carry" if carry_net(net) else "alu"
        try:
            path = R.route(net, list(starts), goal)
            paths.append(path)
            routed.setdefault(net, set()).update(path)
            routed[net].update(starts)
            goals.discard(goal)
        except RuntimeError as e:
            fails.append(str(e))
    g.circuit = "alu"
    R.zlim = None
    for path in paths:
        for a, b in zip(path, path[1:]):
            if a[1] != b[1]:
                lo, hi = (a, b) if a[1] < b[1] else (b, a)
                if g.b.get((lo[0], hi[1], lo[2])) == SOLID:
                    fails.append(f"step {hi}->{lo} capped by a support")
    return fails


routed = {}
paths = []


def _clean(g):
    return [e for e in g.check() if "strong with cc" not in e and "strong with gen" not in e]


def build_routed(mutant=None, tries=300):
    """Route sub's carry-in, each band and then co and zo, each group by its own seed search."""
    import copy
    routed.clear()
    g, R, ins, outs, named, terms = build()
    groups = [[t for t in terms if t[1] == "SUB"]] + [[t for t in terms if t[0] == i] for i in range(BITS)] \
        + [[t for t in terms if t[1] in ("co", "zo")]]
    seeds = []
    for grp in groups:
        for seed in range(tries):
            snap = copy.deepcopy((g, R, routed))
            paths.clear()
            f = route_all(g, R, grp, None if seed == 0 else seed)
            if not f:
                seeds.append(seed)
                break
            g, R, r = snap
            routed.clear(); routed.update(r)
        else:
            raise RuntimeError(f"no routing for {grp[0][:2]}: {f}")
    if fix_strength(g, rounds=1000, fixed={"yany"}) is None:
        raise RuntimeError("strength pass did not converge")
    if mutant == "carry":
        g.b[(XC, 2, zrow(1) + 4)] = SOLID
    return g, ins, outs, named, seeds


_CACHE = {}


def _routed(mutant=None):
    if mutant not in _CACHE:
        _CACHE[mutant] = build_routed(mutant)
    return _CACHE[mutant]


def circuits(mutant=None):
    """pos -> 'carry' (sub's carry-in, the carry-cancel chain and its kill/gen/tap cells and the nets
    feeding them) or 'alu' (everything else), recorded when each block was placed."""
    g = _routed(mutant)[0]
    tag = {}
    for p in g.b:
        net = g.net.get(p)
        carry = g.of.get(p) == "carry" or (net is not None and carry_net(net)) \
            or (net == "SUB" and p[2] <= 2 and p[0] > LANE["SUB"])
        if p in g.of or net is not None:
            tag[p] = "carry" if carry else "alu"
    for p in g.b:
        if p not in tag:
            near = [(p[0], p[1] + 1, p[2])] + [(p[0] + dx, p[1], p[2] + dz) for dx, dz in H4]
            tag[p] = next((tag[q] for q in near if q in tag), "alu")
    return tag


def region(p):
    return circuits().get(p, "alu")


HEAD = " ".join([f"a{i}" for i in range(4)] + [f"b{i}" for i in range(4)] + ["xsel", "za", "sub"]
                + [f"n{i}" for i in range(4)]) + " | y0 y1 y2 y3 co zo"


def alu_tests(max_delay=70, settle=80):
    """scripts.alu's add, sub and pass/imm tables with n ungated: rows with xsel=0 carry n != 0."""
    from scripts.alu import _row
    pairs = [(a, b) for k, a in enumerate(GRAY) for b in (GRAY if k % 2 == 0 else GRAY[::-1])]
    add = [_row(a, b, imm=(a * 5 + b * 3) & 15) for a, b in pairs]
    sub = [_row(a, b, sub=1, imm=(a + b * 7) & 15) for a, b in pairs]
    imm = [_row(b ^ 10, b, za=1, imm=b ^ 5) for b in GRAY]
    imm += [_row(n ^ 6, n ^ 9, xsel=1, za=1, imm=n) for n in GRAY]
    imm += [_row(a, a ^ 5, xsel=1, imm=n) for a in GRAY[:8] for n in (GRAY if a % 2 else GRAY[::-1])[:8]]
    imm += [_row(a, a ^ 3, xsel=1, sub=1, imm=n) for a in GRAY[8:] for n in GRAY[8:]]
    t = {"settle": settle, "max_delay": max_delay}
    table = lambda rows: HEAD + "\n" + "\n".join(rows) + "\n"
    return [{"name": "add", "truth_table": table(add), **t},
            {"name": "sub", "truth_table": table(sub), **t},
            {"name": "pass and imm", "truth_table": table(imm), **t}]


DESCRIPTION = (
    "CPU4 ALU, compact pass 2: x = n if xsel else b; y = (a - za) + (x xor sub) + sub, co = carry out "
    "(for sub, 1 = no borrow), zo = (y == 0). Bit k owns rows z 1+8k..8+8k. Per bit, west to east: n pin "
    "(0,1,4+8k) -> mux (two subtract comparators as in mux_comparator_2to1: n - NOT xsel, NOT xsel being dust "
    "lit by a wall torch above it, hung on a block that xsel's tap dust sits on, and b - xsel), X' = x xor sub "
    "(xor_comparator_bridge), P = A' xor X' (xor_comparator_bridge; A' = a - za by a comparator at (21,1,1+8k)), "
    "sum = P xor carry (xor_comparator_bridge), and a carry-cancel chain along z at x=33, y=2 "
    "(add_carry_cancel_cell's subtract comparator into a hard-powered block, kill = NOT P from a torch, "
    "gen = X' - P; one repeater per bit restores the carry). a and b enter the east face and ride y=5 "
    "highways west; controls enter the west face at z 34 (xsel), 36 (sub), 38 (za) and run along z at y=7. "
    "zo is a torch on the south end of a y=7 collector at x=29. East face (abuts cpu_regs_compact): y_k out "
    "(43,1,1+8k), a_k in (43,1,4+8k), b_k in (43,1,6+8k), zo out (43,1,33), co out (43,1,35). Cells adapted "
    "from scripts/alu.py; nets routed by scripts.alu_route with a fixed A* step check.")


def cpu_alu_compact(name="cpu_alu_compact", mutant=None, max_delay=50):
    from redstone.build import Build
    from redstone.fileformat import Spec
    g, ins, outs, named, seeds = _routed(mutant)
    b = Build()
    for p, st in sorted(g.b.items()):
        b.place(p, st)
    spec = Spec(name, b, inputs=dict(ins), outputs=dict(outs),
                named={**{f"c{i}": named[f"c{i}"] for i in range(1, BITS)}, **outs},
                traits=["pistonless", "entityless", "comparator_based"])
    spec.description = DESCRIPTION
    spec.tests = alu_tests(max_delay)
    return spec


if __name__ == "__main__":
    import sys
    from pathlib import Path
    from redstone.fileformat import dump
    if len(sys.argv) > 1 and sys.argv[1] == "mutant":
        Path("library/cpu_parts/cpu_alu_compact_mutant.redstone.yaml").write_text(
            dump(cpu_alu_compact("cpu_alu_compact_mutant", mutant="carry")))
    else:
        Path("library/cpu_parts/cpu_alu_compact.redstone.yaml").write_text(dump(cpu_alu_compact()))
