"""Design B (mirrored), full opening wiring, v2. Door coords: x right, y up, z hallway axis, door plane z=0.

Push relays: retracted, armed (powered) in the closed state, fired by one designated neighbour update.
ARM blocks are placed after the harness update pass without updates (setblock ... strict)."""
import sys
sys.setrecursionlimit(50000)
from scripts.door2.compactB import pis, dust, rb, rep, door_plane, DOOR, TRACK
from scripts.door2.doorkit import Build, B, add
from scripts.door2.router import route, stone_supports
from scripts.door2.sim import World, AIR, DIRS

ARM = {}
N6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

# where pushed redstone blocks land (dust must never touch these)
FUTURE_RB = {(1, 5, -2),   # RB_A (I_A) -> arms Z_T by QC at t2 j
             (7, 5, -3),   # RB_Y (Y1, pushes up)
             (1, 7, -5),   # RB_X (X2)
             (1, 6, -1),   # RB_T (Z_T, t3)
             (0, 4, 2),    # RB_S (Z_S)
             (4, 4, 1),    # RB9 (Z9, t3)
             (-2, 5, 1)}   # RB11 (Z11, t6)


def arm(b, p, st, name):
    ARM[p] = st
    b.role[p] = name


def _fb(exclude=()):
    rbs = (set(FUTURE_RB) | {p for p, st in ARM.items() if st.n == "rb"}) - set(exclude)
    return {add(r, d) for r in rbs for d in N6} | rbs


def stone_bad_cells(b):
    bad = set()
    for p, st in b.b.items():
        if st.n in ("piston", "sticky_piston"):
            for d in N6:
                bad.add(add(p, d))
                bad.add(add(add(p, (0, 1, 0)), d))
        if st.n in ("repeater", "comparator"):
            bad.add(add(p, DIRS[st.p["facing"]]))
    return bad


def place_path(b, name, path):
    need = stone_supports(path)
    for c in path:
        if c in b.b:
            continue
        sup = (c[0], c[1] - 1, c[2])
        if sup not in b.b:
            b.put(sup, B("stone" if sup in need else "glass"), name + "_s")
        elif sup in need and b.b[sup].n not in ("quartz", "stone", "obsidian"):
            raise RuntimeError(f"{name}: support {sup} must be a conductor")
        b.put(c, B("redstone_wire", power=0), name)


RESERVED = set()


def net(b, name, src_cells, goals, sensitive, keep=3, own=(), bounds=((-7, 10), (-5, 10), (-9, 6))):
    placed = []
    for i, g in enumerate(goals):
        gl = g if isinstance(g, list) else [g]
        later = set()
        for g2 in goals[i + 1:]:
            for c in (g2 if isinstance(g2, list) else [g2]):
                later |= {c, (c[0], c[1] - 1, c[2])}
        p = route(b, list(src_cells) + placed, gl, sensitive=sensitive, keep=keep, own=set(placed) | set(own),
                  bounds=bounds, forbid=_fb(own) | later | (RESERVED - set(gl)), stone_bad=stone_bad_cells(b))
        if p is None:
            raise RuntimeError(f"{name}: no route to {g}")
        place_path(b, name, p)
        placed += [c for c in p if c not in placed]
    return placed


# relay positions (armed; must stay out of every storm except their own wake)
X2, Z_Q, Y1, Z_S, Z9, Z11, Z_T = (1, 7, -3), (6, 3, -3), (7, 3, -3), (2, 4, 2), (4, 2, 1), (-2, 3, 1), (1, 4, -1)


def build_open():
    ARM.clear()
    b = Build(hall=(-4, 7))
    b.walls()
    door_plane(b)

    # ---- input: R_in (fixture, timing repeater) -> K_in -> I_A pushes RB_A down (NA dies; RB_A arms Z_T at t2 j)
    rep(b, (0, 8, -2), "west", "R_in")
    b.put((1, 8, -2), B("stone"), "K_in")
    pis(b, (1, 7, -2), "down", "I_A", sticky=False)
    rb(b, (1, 6, -2), "RB_A")
    # P7 feed (NA end): D7a on the ceiling, line N-S pointing S into P7
    dust(b, (2, 4, -1), "NA", support="quartz")
    dust(b, (2, 4, -2), "NA", support="quartz")
    b.put((3, 4, -1), B("stone"), "cut_DQ")          # separates D7a from DQ (both directions)
    # ring repeaters: off at t2 d (NA dies at t0 g)
    for x in range(3):
        rep(b, (x, -2, -1), "north", f"r_P{x+1}")
    rep(b, (-2, 1, -1), "north", "r_P4")
    rep(b, (-3, 2, 0), "west", "r_P6")
    rep(b, (5, 0, 0), "east", "r_P5")
    b.put((4, 0, 0), B("stone"), "c_P5")
    rep(b, (-1, 5, -1), "north", "r_P10", delay=3)   # off at t6 d

    # ---- Q: DQ on wall (3,2,-1); chain from RB_Q; Z_Q pushes RB_Q (after Q0)
    dust(b, (3, 3, -1), "DQ", support="quartz")
    arm(b, (6, 4, -3), B("rb", id="RB_Q"), "RB_Q")
    pis(b, Z_Q, "up", "Z_Q", sticky=False)
    arm(b, (6, 4, -4), B("rb"), "ARM_ZQ")
    # ---- X2: woken by I_A's base update; kills NB (-> Z_Q after Q0); carries C_cut (cuts NV at t2 j)
    pis(b, X2, "north", "X2", sticky=False)
    rb(b, (1, 7, -4), "RB_X")
    b.put((1, 7, -5), B("stone", id="C_cut"), "C_cut")
    arm(b, (1, 8, -4), B("rb"), "ARM_X2")
    # ---- Y1: woken by Z_Q's base update (after Q1); kills LY (-> Z_S after S0)
    pis(b, Y1, "up", "Y1", sticky=False)
    rb(b, (7, 4, -3), "RB_Y")                         # -> (7,5,-3)
    arm(b, (7, 4, -4), B("rb"), "ARM_Y1")             # QC cell of Y1 (neighbour of RB_Y's cell)
    # ---- S: DS on ceiling (1,3,1) fed by RB_S; Z_S pushes RB_S west
    dust(b, (1, 4, 1), "DS", support="quartz")
    rb(b, (1, 4, 2), "RB_S")
    pis(b, Z_S, "west", "Z_S", sticky=False)
    arm(b, (2, 6, 2), B("rb"), "ARM_ZS")
    # ---- T: permanent QC power RB_T; Z_T (armed at t2 j by RB_A) pushes it up after T0
    rb(b, (1, 5, -1), "RB_T")
    pis(b, Z_T, "up", "Z_T", sticky=False)
    # ---- P9: permanent QC power RB9; Z9 pushes it up after P9 0
    rb(b, (4, 3, 1), "RB9")
    pis(b, Z9, "up", "Z9", sticky=False)
    arm(b, (5, 3, 1), B("rb"), "ARM_Z9")
    # ---- P11: permanent QC power RB11; Z11 pushes it up after P11 0
    arm(b, (-2, 4, 1), B("rb", id="RB11"), "RB11")   # placed after load: it also QC-arms Y12
    pis(b, Z11, "up", "Z11", sticky=False)
    arm(b, (-2, 4, 2), B("rb"), "ARM_Z11")
    # ---- P12 (t6): Y12 (woken by Z11's base update, after P11 1) pushes gate stone G off the L->H step,
    #      so NP12 powers G12 (dust on top of P12) and P12 extends, pushing the spare into slot (0,3)
    pis(b, (-2, 3, 2), "west", "Y12", sticky=False)     # armed by ARM_Z11 above it
    b.put((-3, 3, 2), B("stone", id="G"), "G")           # gate: above L; lands (-4,3,2)
    rb(b, (-4, 2, 2), "RB12")
    dust(b, (-3, 2, 2), "NP12")                          # L, fed by RB12
    b.put((-3, 2, 3), B("glass"), "NP12_s")
    dust(b, (-3, 3, 3), "NP12")                          # H: takes L's power once G is gone
    dust(b, (0, 6, 0), "NP12", support="quartz")         # G12 on top of P12 (support placeholder replaced below)
    dust(b, (0, 6, 1), "NP12")                           # G12b: makes G12 a N-S line (never points W at P10)
    # ---- NV: V and P8 feed; cut at t2 j by C_cut landing at (1,7,-6) above A
    b.put((1, 6, -7), B("stone"), "NV_s")           # B's support: conductor so power steps down B -> A
    dust(b, (1, 7, -7), "NV")            # B, fed by RB_V
    rb(b, (1, 7, -8), "RB_V")
    dust(b, (1, 6, -6), "NV")            # A: cut when C_cut lands above it at (1,7,-6)
    dust(b, (-1, 3, -1), "NV", support="quartz")   # on wall: points S into V
    dust(b, (-1, 3, -2), "NV", support="quartz")
    dust(b, (4, 5, 0), "NV")             # P8 QC: points W into (3,5,0)
    dust(b, (5, 5, 0), "NV")
    return b


def power_cells(p):
    """cells whose signal can power a piston at p (direct neighbours and QC cells)."""
    out = {add(p, d) for d in N6}
    a = add(p, (0, 1, 0))
    out |= {add(a, d) for d in N6}
    return out


def wake_goals(target, avoid, radius=2):
    """dust cells within `radius` of target (so its storm updates it), not able to power it, >=3 from avoid."""
    out = []
    x0, y0, z0 = target
    pc = power_cells(target)
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            for dz in range(-2, 3):
                c = (x0 + dx, y0 + dy, z0 + dz)
                if 0 < abs(dx) + abs(dy) + abs(dz) <= radius and c not in pc:
                    if all(sum(abs(a - b) for a, b in zip(c, s)) >= 3 for s in avoid):
                        out.append(c)
    return out


def route_nets(b):
    placed = []
    placed += net(b, "NV", [(1, 6, -6)], [(-1, 3, -3), [(6, 5, 0), (5, 5, -1), (5, 6, 0)]],
                  sensitive=[Z_T, Z9, Z11], own={(1, 7, -7), (1, 6, -6), (-1, 3, -1), (-1, 3, -2), (4, 5, 0), (5, 5, 0)})
    # DQ chain, routed from its source (RB_Q) toward DQ so descents get stone supports
    placed += net(b, "DQ", [(5, 4, -3), (7, 4, -3), (6, 4, -2)], [(4, 3, -1)], sensitive=[Y1, Z9, Z_S, Z11],
                  own={(3, 3, -1), (6, 4, -3)})
    relays = [X2, Z_Q, Y1, Z_S, Z9, Z11]
    own = {(2, 4, -2), (2, 4, -1), (1, 6, -2)}
    placed += net(b, "NA", [(0, 6, -2), (2, 6, -2), (1, 6, -3)],
                  [(2, 4, -3), (6, 0, 0), (-1, 5, -2), (-4, 2, 0), (-2, 1, -2), (0, -2, -2), (1, -2, -2), (2, -2, -2)],
                  sensitive=relays + [(4, 2, 0)], own=own)
    placed += net(b, "NB", [(0, 7, -4), (2, 7, -4), (1, 6, -4)],
                  [wake_goals(Z_Q, [(4, 2, 0), Y1, Z9, Z_S, Z11])], sensitive=[(4, 2, 0), Y1, Z9, Z_S, Z11],
                  own={(1, 7, -4)})
    placed += net(b, "NP12", [(-3, 3, 3)], [(0, 6, 2)], sensitive=[], own={(-3, 3, 3), (0, 6, 1), (0, 6, 0), (-3, 2, 2), (-4, 2, 2)},
                  bounds=((-7, 10), (-5, 10), (-9, 3)))
    placed += net(b, "LY", [(7, 4, -2), (8, 4, -3)],
                  [wake_goals(Z_S, [(1, 4, 0), Z9, Z11, Z_T])], sensitive=[(1, 4, 0), Z9, Z11, Z_T],
                  own={(7, 4, -3)}, bounds=((-7, 7), (-5, 10), (-9, 3)))
    return placed


EXPECT_CLOSED = {"P1": 1, "P2": 1, "P3": 1, "P4": 1, "P5": 1, "P6": 1, "P7": 1, "P8": 1, "V": 1, "P10": 1,
                 "Q": 1, "S": 1, "T": 1, "P9": 1, "P11": 1, "P12": 0, "I_A": 0,
                 "X2": 1, "Z_Q": 1, "Y1": 1, "Z_S": 1, "Z_T": 0, "Z9": 1, "Z11": 1, "Y12": 1}


def settle_dust(w):
    """give every wire its evaluated power without neighbour updates (the builder's order)."""
    from scripts.door2.sim import HORIZ, U, D
    cells = [c for c, s in w.b.items() if s.n == "redstone_wire"]
    for _ in range(40):
        changed = False
        for c in cells:
            st = w.get(c)
            w.should_signal = False
            bs = w.best_neighbor_signal(c)
            w.should_signal = True
            ws = 0
            above_cond = w.is_conductor(add(c, U))
            for d in HORIZ:
                q = add(c, d)
                ws = max(ws, w.wire_power(q))
                if w.is_conductor(q) and not above_cond:
                    ws = max(ws, w.wire_power(add(q, U)))
                elif not w.is_conductor(q):
                    ws = max(ws, w.wire_power(add(q, D)))
            t = bs if bs >= 15 else max(bs, ws - 1)
            if st.p.get("power", 0) != t:
                w.b[c] = st.w(power=t)
                changed = True
        if not changed:
            break


STRICT_ARM = {(1, 8, -4)}          # ARM_X2: a QC cell of X2, placed with setblock ... strict after load
BLOCKERS = [(6, 5, -3), (7, 5, -3), (0, 4, 2), (4, 4, 1), (-2, 5, 1), (-4, 3, 2)]


def full_blocks(b):
    """the build as loaded on the server: ARM blocks included, obsidian blockers in relay lines."""
    blocks = dict(b.b)
    blocks.update({p: st for p, st in ARM.items() if p not in STRICT_ARM})
    for p in BLOCKERS:
        assert p not in blocks, p
        blocks[p] = B("obsidian")
    return blocks


def make_world(b, settle=20):
    w = World()
    w.load(full_blocks(b))
    w.run(settle)
    moved = [m for t, ph, m in w.log if any(k in m for k in ("EXTEND", "RETRACT"))]
    for p in BLOCKERS:
        w.cmd_set_silent(p, AIR)            # setblock ... air strict
    for p in STRICT_ARM:
        w.cmd_set_silent(p, ARM[p])         # setblock ... redstone_block strict
    return w, moved


def closed_check(b):
    w, moved = make_world(b)
    from scripts.door2.sim import piston_report
    return w, moved, piston_report(w, EXPECT_CLOSED)


def run_open(b, ticks=12):
    w, moved = make_world(b)
    w.run(4)
    w.log.clear()
    t_in = w.time
    w.cmd_set((-1, 8, -2), B("rb"))
    hist = []
    for i in range(ticks):
        w.tick()
        hist.append((w.time - t_in - 2, {n: w.find(n) for n in TRACK}))
    return w, t_in, hist


def report(w, t_in, hist, verbose=True):
    for t, snap in hist:
        frame = [n for n in DOOR.values() if snap[n][0] and 0 <= snap[n][0][0] <= 2 and 0 <= snap[n][0][1] <= 2 and snap[n][0][2] == 0]
        print(f"t{t:+d} frame={frame}")
    if verbose:
        for (t, ph, m) in w.log:
            if any(k in m for k in ("EXTEND", "RETRACT", "queue", "skipped", "dropped", "cancel", "failed")):
                print(f"  t{t - t_in - 2:+d}{ph} {m}")


if __name__ == "__main__":
    b = build_open()
    route_nets(b)
    w, moved, bad = closed_check(b)
    print("moved during load:", moved)
    print("\n".join(bad) or "closed state: all pistons powered as intended")
