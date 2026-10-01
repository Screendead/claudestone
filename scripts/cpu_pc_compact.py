"""CPU4 program counter, compact variant (cpu_pc_compact).

Master/slave 4-bit register with an incrementer and a next-PC mux: next = 0 if rst, else imm if
jt, else pc+1 mod 16. The master captures while cap AND (rst OR NOT hlt); the slave copies the
master while com. The pc pin repeaters are themselves the slaves (com -> pc 8 gt); a second
slave per bit feeds the incrementer, so the next value never changes while cap is high.
Library cells: repeater-lock latches as d_latch/dl_lock_pair and register/shift_reg4_lock;
subtract comparators as xor/xor_comparator_bridge; two-torch climbs as
vertical_wire/vwire_torch_tower_up. Hand-placed cells, long nets wired by
scripts.alu_route's router in a fixed seeded order (SEED), then its strength pass.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from redstone.build import Build
from redstone.fileformat import Spec, dump
from scripts.alu_route import Grid, Router, SOLID, WIRE

W, H, D = 32, 6, 28
YMAX = 7
KEEP = set()  # cells the router must leave air (so a dust line keeps pointing into its block)
FRAG = set()   # pre-placed sink fragments, never used as route starts
Z0 = 1
B = [Z0 + 3 * i for i in range(4)]          # pc pin rows
IMM = [Z0 + 15 + 3 * i for i in range(4)]   # imm / n rows


def torch(g, p, net):
    g.put(p, "redstone_torch", net)
    g.strong.setdefault((p[0], p[1] + 1, p[2]), set()).add(net)


def west_and_bank(g, named):
    for i, b in enumerate(B):
        g.dust((0, 1, b), f"pc{i}")
        g.rep((1, 1, b), "w", f"pc{i}")             # S_i, the pin slave
        named[f"s{i}"] = (1, 1, b)
        g.rep((1, 1, b + 1), "n", "slk")             # its lock
        g.dust((1, 1, b + 2), "ncom")
        g.dust((2, 1, b + 2), "ncom")
        g.block((2, 1, b))                            # T': S_i's input, powered from the pad
        g.dust((2, 2, b), f"m{i}")
        g.block((3, 2, b))
        g.dust((3, 3, b), f"m{i}")
        if i < 3:
            g.block((2, 2, b + 2))
            g.block((3, 2, b + 2))
        # bank
        g.block((4, 3, b))                            # B: hard-powered by M
        g.rep((5, 3, b), "w", f"m{i}")                # M_i
        named[f"m{i}"] = (5, 3, b)
        g.dust((6, 3, b), f"d{i}")
        named[f"d{i}"] = (6, 3, b)
        g.rep((5, 3, b + 1), "n", "mlk")              # M lock
        g.put((5, 3, b + 2), SOLID, support=False)    # its source block
        g.dust((5, 4, b + 2), "L")
        for dz in (0, 1):
            g.block((5, 4, b + dz))
            g.dust((5, 5, b + dz), "L")
        g.rep((4, 3, b + 1), "s", f"P{i}")            # S'_i, copy of the slave for the incrementer
        named[f"q{i}"] = (4, 3, b + 1)
        g.rep((3, 3, b + 1), "e", "s2lk")
        g.put((2, 3, b + 1), SOLID, support=False)
        g.dust((2, 4, b + 1), "ncom")
        g.put((2, 3, b + 2), SOLID, support=False)
        g.dust((2, 4, b + 2), "ncom")
        g.put((2, 4, b), SOLID, support=False)
        g.dust((2, 5, b), "ncom")
        g.put((4, 3, b + 2), SOLID, support=False)    # P block, hard-powered by S'
        g.dust((4, 2, b + 2), f"P{i}")
        g.dust((5, 1, b + 2), f"P{i}")
    for z in range(B[0] + 2, B[3] + 2):
        g.dust((3, 1, z), "ncom")


def south(g, named, inputs, outputs):
    """imm rows with their n passthrough, control pins and their first climb."""
    for i, z in enumerate(IMM):
        inputs[f"imm{i}"] = (0, 1, z)
        g.put((0, 0, z), SOLID)
        g.rep((1, 1, z), "e", f"imm{i}")
        outputs[f"n{i}"] = (W - 1, 1, z)
        if i < 3:
            for x in range(2, W - 2):
                if x % 9 == 0:
                    g.rep((x, 1, z), "e", f"imm{i}")
                else:
                    g.dust((x, 1, z), f"imm{i}")
            g.rep((W - 2, 1, z), "e", f"n{i}")
            g.dust((W - 1, 1, z), f"n{i}")
        else:
            g.block((2, 1, z))
            g.dust((2, 2, z), f"imm{i}")
            for x in range(3, W - 3):
                if x % 9 == 0:
                    g.rep((x, 3, z), "e", f"imm{i}")
                else:
                    g.dust((x, 3, z), f"imm{i}")
            g.dust((W - 3, 2, z), f"imm{i}")
            g.rep((W - 2, 1, z), "e", f"n{i}")
            g.dust((W - 1, 1, z), f"n{i}")
    for name, x in CTRL.items():
        inputs[name] = (x, 1, D - 1)
        g.put((x, 0, D - 1), SOLID)
        g.rep((x, 1, D - 2), "n", name)
        g.block((x, 1, D - 3))
        net = "J" if name == "jt" else name
        g.dust((x, 1, D - 4), net)
        g.dust((x, 2, D - 5), net)
        g.dust((x, 3, D - 6), net)
    # face cells beside pins: solid floor
    for z in list(IMM) + list(B):
        for dz in (-1, 0, 1):
            g.b.setdefault((0, 0, z + dz), SOLID)
            g.b.setdefault((W - 1, 0, z + dz), SOLID)
    for x in CTRL.values():
        for dx in (-1, 0, 1):
            g.b.setdefault((x + dx, 0, D - 1), SOLID)


CTRL = {"com": 3, "cap": 5, "hlt": 7, "rst": 9, "jt": 11}


def cell(g, p, torch_side, out_net, ports=(), pad=None):
    """NOR cell: block at p, wall torch on torch_side ('w','e','n','s'), inputs as repeater
    ports [(side, net)] pointing into the block and an optional pad net on top.
    Returns {net: goal cell} for the router (port backs and the pad)."""
    D4 = {"w": (-1, 0), "e": (1, 0), "n": (0, -1), "s": (0, 1)}
    OPPS = {"w": "e", "e": "w", "n": "s", "s": "n"}
    g.block(p)
    dx, dz = D4[torch_side]
    g.wall_torch((p[0] + dx, p[1], p[2] + dz), OPPS[torch_side], out_net)
    goals = []
    for side, net in ports:
        dx, dz = D4[side]
        r = (p[0] + dx, p[1], p[2] + dz)
        g.rep(r, OPPS[side], net)          # output toward the block
        goals.append((net, (r[0] + dx, r[1], r[2] + dz)))
    if pad:
        goals.append((pad, (p[0], p[1] + 1, p[2])))
    return goals


XE, XO, CH = 9, 17, 25          # even tile column, odd tile column, carry chain column


def j_column(g, jx, rows):
    """J zigzag along z at x=jx from row 1 to 16: y=3 on blocks, except a pad at y=2 on the
    block (jx,1,b+2) for each tile row b in rows (that block feeds the tile's J repeater)."""
    pads = {b + 2 for b in rows}
    for z in range(1, 17):
        if z in pads:
            g.put((jx, 1, z), SOLID)
            g.dust((jx, 2, z), "J")
        else:
            g.put((jx, 2, z), SOLID)
            if z in ((6, 13) if jx == 11 else (9, 15)):
                g.rep((jx, 3, z), "n", "J")
            else:
                g.dust((jx, 3, z), "J")


def inc_and_mux(g, named):
    """Per bit: G_i = W_i - max(c_{i+1} or J) into O_i, which feeds d_i. W_i = P_i or c_i
    (bit 0: a redstone block, c_0 = 1). The side port reads dust cJ fed by a c repeater and
    a J repeater (J from a zigzag column per tile column). Carry chain at x=CH: Kc_{i+1} is
    hard-powered by Q_i (torch standing on Pb_i) and by NOT c_i through two repeaters from
    Kc_i; its wall torch is c_{i+1}."""
    goals = []
    j_column(g, XE - 2 + 4, [b for i, b in enumerate(B) if i % 2 == 0])   # x=11
    j_column(g, XO + 2, [b for i, b in enumerate(B) if i % 2 == 1])       # x=19
    for i, b in enumerate(B):
        even = i % 2 == 0
        xo = XE if even else XO
        n = f"d{i}"
        g.cmp((xo, 1, b), "n", n)                        # G_i
        g.put((xo, 1, b - 1), SOLID)                     # O_i
        g.strong.setdefault((xo, 1, b - 1), set()).add(n)
        g.net[(xo, 1, b - 1)] = n
        g.dust((7, 3, b), n)
        if even:
            g.dust((8, 1, b - 1), n)
            g.block((7, 1, b - 1))
            g.dust((7, 2, b - 1), n)
            jx = xo + 2                                  # cJ east of G
            g.rep((xo + 1, 1, b), "w", f"cJ{i}")
            g.rep((jx + 1, 1, b), "w", f"c{i+1}")
            goals.append((f"c{i+1}", (jx + 2, 1, b)))
        else:
            # O_i up a two-torch tower, west over both J columns at y=5, down to d_i
            torch(g, (xo, 2, b - 1), f"nd{i}")
            g.put((xo, 3, b - 1), SOLID)
            torch(g, (xo, 4, b - 1), n)
            g.put((xo, 5, b - 1), SOLID)
            for x in range(10, xo):
                g.put((x, 4, b - 1), SOLID); g.dust((x, 5, b - 1), n)
            g.put((10, 4, b), SOLID); g.dust((10, 5, b), n)
            g.put((9, 3, b), SOLID); g.dust((9, 4, b), n)
            g.dust((8, 3, b), n)
            jx = xo + 2                                  # cJ east of G
            g.rep((xo + 1, 1, b), "w", f"cJ{i}")
            g.rep((jx + 1, 1, b), "w", f"c{i+1}")
            if even:
                goals.append((f"c{i+1}", (jx + 2, 1, b)))
            else:                                        # short hand path from the carry torch above
                cn = f"c{i+1}"
                for p in [(CH - 2, 3, b + 1), (CH - 3, 2, b + 1), (CH - 3, 2, b), (jx + 2, 1, b)]:
                    g.dust(p, cn)
        g.dust((jx, 1, b), f"cJ{i}")
        g.rep((jx, 1, b + 1), "n", "J")
        if i == 0:
            g.put((xo, 1, b + 1), "redstone_block")
        else:
            g.block((xo, 1, b + 1))                      # W_i, weakly powered: P_i dust from the side, c_i pad
            side = -1
            frag = [(xo + side, 1, b + 1), (xo + 2 * side, 1, b + 1)]
            for p in frag:
                g.dust(p, f"P{i}")
            FRAG.update(frag)
            KEEP.update({(xo - 1, 1, b + 2), (xo - 1, 1, b)})
            goals.append((f"P{i}", (xo + 3 * side, 1, b + 1)))
            cn = f"c{i}" if i > 1 else "P0"
            g.dust((xo, 2, b + 1), cn)                   # pad on W_i
            FRAG.add((xo, 2, b + 1))
            KEEP.add((xo, 3, b + 1))                     # the pad's step up to its connector
            g.put((xo + side, 2, b + 1), SOLID)          # keeps the P dust below from climbing to it
            dz = 0 if even else 2
            g.put((xo, 2, b + dz), SOLID)
            goals.append((cn, (xo, 3, b + dz)) if i > 1 else ("P0", ((xo, 3, b + dz),), "c1"))
        # carry chain
        r = b + 2
        g.block((CH, 1, r))                              # Pb_i
        g.rep((CH - 1, 1, r), "e", f"P{i}")
        g.rep((CH, 1, r - 1), "s", f"P{i}")
        g.rep((CH + 1, 1, r), "w", f"P{i}")
        goals.append((f"P{i}", ((CH - 2, 1, r), (CH, 1, r - 2), (CH + 2, 1, r))))
        torch(g, (CH, 2, r), f"Q{i}")
        g.put((CH, 3, r), SOLID)                         # Kc_{i+1}
        g.wall_torch((CH - 1, 3, r), "e", f"c{i+1}")
        g.dust((CH - 2, 3, r), f"c{i+1}")
        if i < 3:
            g.rep((CH, 3, r + 1), "s", "nc")
            g.rep((CH, 3, r + 2), "s", "nc")
    return goals


FROZEN = []   # (goal item, {pos: (state, net)}) laid in before routing


def build_all():
    g = Grid((W, 8, D))
    named, inputs, outputs = {}, {}, {}
    west_and_bank(g, named)
    south(g, named, inputs, outputs)
    inc = inc_and_mux(g, named)
    ctl = controls(g, named)
    J = [x for x in inc if x[0] == "J"]
    inc = [x for x in inc if x[0] != "J"]
    inc.sort(key=lambda t: (0 if t[0].startswith("c") else 1 if t[0].startswith("P") else 2))
    late = [x for x in ctl if x[0].startswith("d")]
    ctl = [x for x in ctl if not x[0].startswith("d")]
    nj = [x for x in ctl if x[0] == 'NJ']
    ctl = [x for x in ctl if x[0] != 'NJ']
    goals = J + inc + nj + ctl + late
    for item, cells in FROZEN:
        for p, (st, n) in cells.items():
            g.b[p] = st
            if n is not None:
                g.net[p] = n
        goals = [x for x in goals if x != item]
    return g, named, inputs, outputs, goals


def build_core():
    g = Grid((W, 8, D))
    named, inputs, outputs = {}, {}, {}
    west_and_bank(g, named)
    goals = inc_and_mux(g, named)
    return g, named, inputs, outputs, goals


def route(g, goals, ymax=5):
    R = Router(g, ymax=ymax)
    R.keep.add((W - 3, 3, IMM[3]))
    R.keep |= KEEP
    for (x, y, z), st in list(g.b.items()):         # keep every existing dust step's corner air
        if st != WIRE:
            continue
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + 1, z + dz)
            if g.b.get(q) == WIRE and g.net.get(q) == g.net.get((x, y, z)) and g.b.get((x, y + 1, z)) is None:
                R.keep.add((x, y + 1, z))
    norm = []
    for item in goals:
        net, goal = item[0], item[1]
        alts = goal if isinstance(goal[0], tuple) else (goal,)
        nets = (net,) + tuple(item[2:])
        norm.append((nets, alts))
        for a in alts:
            R.mark_input(a, net)
    fails = []
    for nets, alts in norm:
        ok = False
        for net in nets:
            for goal in alts:
                starts = [c for c, n in g.net.items() if n == net and g.b.get(c) == WIRE and c not in FRAG]
                starts += [c for c, n in g.net.items() if n == net and g.b.get(c) != WIRE and g.b.get(c) == SOLID]
                R.inputs[goal] = net
                starts = [c for c in starts if c != goal]
                try:
                    R.route(net, starts, goal)
                    ok = True
                    break
                except RuntimeError:
                    pass
            if ok:
                break
        if not ok:
            fails.append((nets[0], alts[0]))
    return R, fails


def controls(g, named):
    """Hand-placed control logic; returns route goals."""
    goals = []
    # com -> two NOT-com torches on block (3,1,13)
    for z in range(16, D - 6):
        g.dust((3, 3, z), "com")
    g.block((3, 2, 16))
    g.block((3, 1, 15)); g.dust((3, 2, 15), "com")
    g.dust((3, 1, 14), "com")
    g.block((3, 1, 13))
    g.wall_torch((3, 1, 12), "s", "ncom")
    torch(g, (3, 2, 13), "ncom")
    g.put((3, 3, 13), SOLID)
    g.dust((3, 4, 13), "ncom")
    g.put((2, 3, 13), SOLID)
    g.dust((2, 4, 13), "ncom")
    # cap -> NOT-cap torch; hlt - rst comparator; both hard-power (5,5,14) -> L
    for z in range(15, D - 6):
        g.dust((5, 3, z), "cap")
    g.put((5, 3, 14), SOLID)
    torch(g, (5, 4, 14), "L")
    g.put((5, 5, 14), SOLID)
    g.strong.setdefault((5, 5, 14), set()).add("L")
    g.put((5, 4, 13), SOLID)
    g.dust((5, 5, 13), "L")
    g.cmp((5, 5, 15), "n", "L")                         # H = hlt - rst
    g.dust((5, 5, 16), "hlt")
    FRAG.add((5, 5, 16))
    g.rep((6, 5, 15), "w", "rst")
    g.rep((5, 5, 17), "n", "hlt")                       # full strength at H's rear
    goals += [("hlt", (5, 5, 18)), ("rst", (7, 5, 15))]
    for x in range(12, 20):                              # J over to the odd tiles' column
        g.put((x, 2, 17), SOLID)
        g.dust((x, 3, 17), "J")
    # J = jt or rst ; NJ = NOT(J - rst)
    for z in range(17, D - 6):
        if z == 18:
            g.rep((11, 3, z), "n", "J")
        else:
            g.dust((11, 3, z), "J")
    for z in range(21, D - 6):
        g.dust((9, 3, z), "rst")
    g.rep((10, 3, 21), "e", "rst")                      # rst into J
    g.cmp((12, 3, 20), "e", "nj")                        # J - rst
    g.put((12, 3, 18), SOLID)
    g.rep((12, 3, 19), "s", "rst")
    goals += [("rst", (12, 4, 18))]
    g.put((13, 3, 20), SOLID)                           # Kj
    g.wall_torch((13, 3, 21), "n", "NJ")
    g.dust((13, 3, 22), "NJ")
    # imm gates C_i = imm_i - NJ in one row; each output block climbs to a hand-laid bus on the
    # top deck (y=7) that runs north, then west to d_i, then steps down onto d_i's (7,3,b)
    for i, colx in enumerate([29, 25, 21, 17]):
        b = B[i]
        n = f"d{i}"
        g.cmp((colx, 3, 21), "s", n)
        g.put((colx, 3, 22), SOLID)
        g.strong.setdefault((colx, 3, 22), set()).add(n)
        g.net[(colx, 3, 22)] = n
        g.rep((colx, 3, 20), "s", f"imm{i}")
        goals.append((f"imm{i}", (colx, 3, 19)))
        sd = -1 if i % 2 == 0 else 1                     # pairs of gates share one NJ cell between them
        g.rep((colx + sd, 3, 21), "e" if sd < 0 else "w", "NJ")
        if i % 2 == 0:
            goals.append(("NJ", (colx - 2, 3, 21)))
        g.dust((colx, 4, 22), n)
        g.put((colx, 4, 21), SOLID); g.dust((colx, 5, 21), n)
        g.put((colx, 5, 20), SOLID); g.dust((colx, 6, 20), n)
        xend = 11 if i % 2 == 0 else 12
        cells = [(colx, 7, z) for z in range(19, b - 1, -1)] + [(x, 7, b) for x in range(colx - 1, xend - 1, -1)]
        for k, p in enumerate(cells):
            g.put((p[0], 6, p[2]), SOLID)
            nxt = cells[k + 1] if k + 1 < len(cells) else (p[0] - 1, 7, p[2])
            prv = cells[k - 1] if k else (colx, 7, 20)
            straight = (nxt[0] - p[0], nxt[2] - p[2]) == (p[0] - prv[0], p[2] - prv[2])
            if k % 11 == 10 and straight:
                d = {(1, 0): "e", (-1, 0): "w", (0, 1): "s", (0, -1): "n"}[(nxt[0] - p[0], nxt[2] - p[2])]
                g.rep(p, d, n)
            else:
                g.dust(p, n)
        down = [((10, 6, b), (10, 5, b)), ((9, 5, b), (9, 4, b)), ((8, 4, b), (8, 3, b))] if i % 2 == 0 \
            else [((11, 6, b), (11, 5, b))]
        for p, sup in down:
            g.put(sup, SOLID)
            g.dust(p, n)
    return goals


def build_routed(seeds=300, ymax=7):
    import random
    best = None
    for seed in range(seeds):
        g, named, inputs, outputs, goals = build_all()
        if seed:
            rnd = random.Random(seed)
            goals = goals[:]
            rnd.shuffle(goals)
        crit = []
        def rank(t):
            for k, c in enumerate(crit):
                if t[0] == c[0] and (len(c) == 1 or t[1] == c[1]):
                    return k
            return 10 + (0 if t[0][0] in "Pc" else 1)
        goals.sort(key=rank)
        R, fails = route(g, goals, ymax=ymax)
        if best is None or len(fails) < len(best):
            best = fails
        if not fails:
            from scripts.alu_route import fix
            try:
                added = fix(g)
            except RuntimeError as e:
                print("fix failed", seed, e)
                continue
            g._seed = seed
            return g, named, inputs, outputs, seed
    raise RuntimeError(f"no routing: {best}")


def step_violations(g):
    """Same-net dust pairs one step apart diagonally whose step is blocked: the cell above the
    lower one is a conductor (the router can leave these behind when it adds a support later)."""
    bad = []
    for (x, y, z), st in g.b.items():
        if st != WIRE:
            continue
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            up = (x + dx, y + 1, z + dz)
            if g.b.get(up) == WIRE and g.net.get(up) == g.net.get((x, y, z)):
                a = g.b.get((x, y + 1, z))
                if a not in (None, WIRE) and "glass" not in a and "repeater" not in a and "comparator" not in a and "torch" not in a:
                    bad.append(((x, y, z), up))
    return bad


def pc(v): return {f"pc{i}": (v >> i) & 1 for i in range(4)}
def ms(v): return {f"m{i}": (v >> i) & 1 for i in range(4)}
def imm(v, **kw):
    d = {f"imm{i}": (v >> i) & 1 for i in range(4)}; d.update(kw); return d


class T:
    def __init__(self, name, settle=60):
        self.name, self.settle, self.steps = name, settle, []
    def s(self, **kw): self.steps.append(kw)
    def cycle(self, after, before_cap=None, after_cap=None, next_check=None):
        self.s(drive={"com": 1}); self.s(wait=10); self.s(drive={"com": 0}); self.s(wait=2)
        self.s(expect=pc(after))
        if next_check is not None:
            self.s(wait=58); self.s(expect={f"d{i}": (next_check >> i) & 1 for i in range(4)}); self.s(wait=50)
        else:
            self.s(wait=108)
        if before_cap: self.s(drive=before_cap)
        self.s(wait=30); self.s(drive={"cap": 1}); self.s(wait=10); self.s(drive={"cap": 0}); self.s(wait=10)
        if after_cap: self.s(drive=after_cap)
        self.s(wait=28); self.s(expect=pc(after)); self.s(wait=2)
    def lead(self, inputs=None):
        self.s(wait=10)
        if inputs: self.s(drive=inputs)
        self.s(wait=30); self.s(drive={"cap": 1}); self.s(wait=10); self.s(drive={"cap": 0}); self.s(wait=10)
        self.s(wait=28); self.s(wait=2)
    def dump(self): return {"name": self.name, "settle": self.settle, "steps": self.steps}


def tests():
    out = []
    t = T("count"); t.lead()
    for k in range(1, 18): t.cycle(k % 16, next_check=(k + 1) % 16)
    out.append(t)
    t = T("jump"); t.lead()
    t.cycle(1, imm(5, jt=1), imm(0, jt=0)); t.cycle(5, imm(10, jt=1), imm(0, jt=0))
    t.cycle(10, imm(15, jt=1), imm(0, jt=0)); t.cycle(15, imm(0, jt=1), imm(0, jt=0))
    t.cycle(0); t.cycle(1); t.cycle(2); out.append(t)
    t = T("halt"); t.lead(); t.cycle(1); t.cycle(2, {"hlt": 1}); t.cycle(2); t.cycle(2, after_cap={"hlt": 0})
    t.cycle(2); t.cycle(3); t.cycle(4); out.append(t)
    t = T("reset"); t.lead(imm(9, jt=1))
    t.cycle(9, {"rst": 1, "jt": 0, "imm0": 0, "imm3": 0}, {"rst": 0}); t.cycle(0)
    t.cycle(1, {"hlt": 1, "rst": 1}, {"rst": 0}); t.cycle(0, after_cap={"hlt": 0}); t.cycle(0); t.cycle(1); out.append(t)
    t = T("no capture without cap"); t.lead(imm(6, jt=1)); t.s(drive=imm(0, jt=0))
    for v, extra in ((9, {"jt": 1}), (6, {"jt": 1, "hlt": 1}), (15, {"jt": 0, "rst": 1}), (0, {"jt": 1, "hlt": 0, "rst": 0})):
        t.s(wait=40); t.s(drive=imm(v, **extra)); t.s(wait=60)
        t.s(drive={"com": 1}); t.s(wait=10); t.s(drive={"com": 0}); t.s(wait=2)
        t.s(expect=pc(6)); t.s(expect=ms(6)); t.s(wait=88)
    t.s(drive=imm(0, jt=0, hlt=0, rst=0)); out.append(t)
    t = T("two phase"); t.lead()
    t.cycle(1, imm(12, jt=1), imm(3, jt=0)); t.cycle(12, imm(3, jt=0), imm(7, jt=1))
    t.cycle(13, imm(7, jt=1), imm(0, jt=0)); t.cycle(7); t.cycle(8); out.append(t)
    t = T("com to pc delay"); t.lead()
    t.s(drive={"com": 1}); t.s(wave={"pc0": "0" * WAVE_COM + "1" * 6, "s0": "0" * WAVE_COM + "1" * 6}); t.s(drive={"com": 0})
    out.append(t)
    res = [x.dump() for x in out]
    res.append({"name": "passthrough", "truth_table": "imm0 imm1 imm2 imm3 | n0 n1 n2 n3\n" + "\n".join(
        " ".join(str((v >> i) & 1) for i in range(4)) + " | " + " ".join(str((v >> i) & 1) for i in range(4))
        for v in (0, 1, 3, 7, 15, 14, 12, 8, 5, 10, 0)), "delay": PASS_DELAY})
    return res


WAVE_COM = 8
PASS_DELAY = 10




SEED = 48


def build_routed_fixed():
    g, named, ins, outs, goals = build_all()
    random.Random(SEED).shuffle(goals)
    goals.sort(key=lambda t: -2 if t[0].startswith("imm") else -1 if t[0] == "NJ" else 0 if t[0].startswith("P")
               else 1 if t[0].startswith("c") else 2)
    R, f = route(g, goals, ymax=7)
    if f or step_violations(g):
        raise RuntimeError(f"routing failed: {f} {step_violations(g)[:3]}")
    from scripts.alu_route import fix
    fix(g)
    return g, named, ins, outs


DESCRIPTION = (
    "CPU4 program counter, compact: master/slave 4-bit register, next = 0 if rst, else imm if jt, else pc+1. "
    "The pc pin repeaters at (1,1,1+3i) are the slaves (locked from NOT com), so COM to pc is 8 gt; a second "
    "slave per bit feeds a torch/comparator incrementer (carry chain of NOR cells at x=25), and per bit a "
    "subtract comparator G_i = (P_i or c_i) - (c_i+1 or J) feeds the master input d_i, OR'ed with imm_i - NJ "
    "from gates at y=3 whose outputs reach d_i over a bus on the top deck (y=7). L = NOT cap OR (hlt - rst) "
    "locks the masters, J = jt OR rst, NJ = NOT(J - rst). imm/jt/hlt/rst must settle 30 gt before cap "
    "(imm reaches d in up to ~20 gt). Pins: west pc0..3 out at z=1,4,7,10 and imm0..3 in at z=16,19,22,25; "
    "east n0..3 out at x=31, same z; south (z=27) com x=3, cap x=5, hlt x=7, rst x=9, jt x=11. "
    "Built from scripts/cpu_pc_compact.py.")


def cpu_pc_compact(name="cpu_pc_compact", mutant=None):
    g, named, ins, outs = build_routed_fixed()
    outs = dict(outs)
    for i, z in enumerate(B):
        outs[f"pc{i}"] = (0, 1, z)
    if mutant == "carry":
        # drop the carry into bit 2: its port repeater becomes air
        g.b.pop((12, 1, B[1] + 0) if False else (20, 1, B[1]), None)
    b = Build()
    for p, s in sorted(g.b.items()):
        if s and p not in ins.values():
            b.place(p, s)
    spec = Spec(name, b, inputs=ins, outputs=outs, named={**named, **outs},
                traits=["torch_based", "comparator_based", "pistonless", "entityless"])
    spec.description = DESCRIPTION
    spec.tests = tests()
    return spec


if __name__ == "__main__":
    lib = Path(__file__).resolve().parents[1] / "library" / "cpu_parts"
    (lib / "cpu_pc_compact.redstone.yaml").write_text(dump(cpu_pc_compact()))
    if "--mutant" in sys.argv:
        (lib / "cpu_pc_compact_mutant.redstone.yaml").write_text(dump(cpu_pc_compact("cpu_pc_compact_mutant", mutant="carry")))
