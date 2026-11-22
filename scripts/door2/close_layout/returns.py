"""The returns, after the close (door coords): what the cells that still differ from the loaded closed state after
p9_p8.py's close need, and how far the trigger chain's blocks can go home. Nothing is added to p9_p8.py's build
except in the what-ifs. Everything printed is COMPUTED on the simulator; nothing here ran on a server.

Holds   Every fired piston outside the door plane is still powered after the close: each of the opening's seven
        relays by its arm, a redstone block design_c leaves beside it for good (X2's set strict after the load;
        Y12's is Z11's, and DP's RB_D holds Y12 too; RB_F holds Z_S too), and K by RB12; the up relays Z_Q, Y1,
        Z9, Z11 and K also by their own payload, which rests at R+2, a QC
        cell (MEASURED for a sticky up relay in door_relay_rearm, test 3). K_T is held by RB_T at (2,6,-1). A
        relay goes home only if its arm leaves first and something updates it then.
Routes  A moved block goes home one cell at a time. A step from u to v needs v empty (or v the block's closed
        cell), and a mover: a piston behind u facing v, or a sticky piston beyond v facing u. A mover stands in a
        free cell (in the box, empty in the closed state, in every tick of the opening and of the close to c30,
        off the door plane and out of the hallway) and is screened: built retracted into the closed state, nothing
        moves during the load and every other cell is the same at every tick of the opening and the close. A stop
        is screened too: a redstone block set into the world after the close at that cell (updates included) must
        fire no piston in 12 ticks. The screen is lenient: a stop may leave a piston powered and not updated (the
        trap below is one). Breadth first from the block's cell after the close; with no route, each step to a
        cell not reached is printed with why. The box is the opening's and the close's, 12x14x12 since the bus's
        west branch was re-laid over the input (trigger.py, 2026-11-22).
Verdict In the screen RB_T and RB12 have no route home; RB_ST has one now that the box reaches y 10 (up over
        (2,9,0), (3,9,0), (3,9,1), (3,8,1) and (3,7,1), movers up to y 10; the screen is static and does not keep
        movers off the path: (3,9,1) is on it), not designed. RB_T gets to (1,6,-1) (P_R's push), (2,7,-1) and
        (2,6,-2) and no further: (1,5,-1) is entered from (1,6,-1) only from (1,7,-1), where a piston fires in the
        opening (below), or by Z_T's own pull, and RB_T at (1,6,-1) holds Z_T by QC; the other ways pass a cell
        where a redstone block fires Z_T or the opening, or have no free mover. RB12 cannot move: K's head is
        under it, G above it, M_K and Y12's head beside it, the box edge west, and south no mover. G's closed
        cell is Y12's head. K_T made sticky would pull SPC home, but only once RB_T has left (2,6,-1).
Grown   The box grown by 2 on every side: RB12 has a route west round (-5,3,2) to (-5,2,2), movers out to x -6,
        RB_ST's is the one in the box, RB_T has none. Every way into (1,5,-1), for any block, needs a mover in
        R_8's cell, r_P10's, (1,7,-1), Z_T's (non-sticky, and held by a block at (1,6,-1)), W_T's or a wall's, or
        one of three free cells whose piston moves during the load ((0,5,-1): NA's stone beside it; (1,5,-3): NA's
        dust and RB_A) or fires at c3 ((2,5,-1): under RB_T).
Fix     The fix as chosen (2026-11-22: the bus's first west dust off (1,8,-1), a down-pusher at (1,7,-1)) fails
        on the piston, not on the bus: K_in (1,8,-2) is strongly powered while the input is on and stands beside
        (1,8,-1), the cell above the piston, so the piston is QC-powered from t0 d whatever is in (1,8,-1); I_A's
        extension beside it updates it at t0 g, it extends into the empty (1,6,-1) and Z_T cannot lift RB_T at t3.
        One cell higher it would be powered by K_in directly.
Others  The report's other ways. Z_T sticky: RB_T back at (1,6,-1) is Z_T's own payload at R+2 and holds it out
        by QC, so it never pulls RB_T down. W_T sticky would pull a block south out of (1,5,-2), RB_A's open cell:
        every way into that cell is NA's wiring, a wall, a piston that moves during the load, or I_A's own push
        (the opening). T held otherwise: T fires at t3 g on RB_T alone (DS is dark by then) and Z_T's lift takes
        RB_T away in that phase; another hold is another relay inside the opening's T stage, a change to
        design_c's opening, not tried.
Column  What does push RB_T down (what-if, sim only): H_T, a piston at (1,9,-1) facing down, two cells higher,
        where K_in does not reach it, over two glass spacers, GA (1,7,-1) and GB (1,6,-1) in the closed state. Z_T
        lifts RB_T, GB and GA together at t3, so in the open state and after the close GB is at (1,7,-1) and GA at
        (1,8,-1); H_T pushes GA, GB and RB_T down one cell and RB_T is home. GB stands in (1,6,-1), a cell of the
        opening: the opening and the close are the same at every tick outside the column's three cells. That is
        why the bus's west branch left (1,8,-1) and (1,7,-1). The bus dust beside H_T, (1,9,-2) and (0,9,-1),
        points past it.
Trap    P_R cannot push RB_T straight back under the column: K_T, held by RB_T at (2,6,-1), retracts in P_R's
        phase, its base lands in the same phase j as RB_T, behind it, and updates W_T, which RB_T at (1,6,-1)
        powers by QC: W_T's head takes (1,5,-1). So N_T, a sticky piston at (2,6,-3) facing south, kicks first:
        out and in, it pulls RB_T north to (2,6,-2), K_T retracts and lands with W_T unpowered; out again, it
        pushes RB_T back, and RB_T's landing in front of P_R is the update P_R needs. P_R's hold (RB_ST at
        (3,7,0)) must arrive while RB_T is parked: earlier, P_R extends into the empty cell when RB_T is pulled
        away.
What-if RB_T returned by command (sim only): N_T's and H_T's sources and the returns of RB_ST and SPC are stood in
        for by commands after the close. The trigger chain's east side (RB_T, GA, GB, P_R, K_T, SPC, RB_ST, Z_T,
        W_T, AP) and the S feed's thirteen end as the closed state has them, T powered by RB_T. What still
        differs is the opening's seven relays with their blocks and the west side (K, M_K, RB12, G). K_T made
        sticky (a measured block) would pull SPC home at the kick. Not designed: the two sources and their
        timing, RB_ST's route and SPC's mover; no command may follow the input, so this is not yet a design.
What-if Z9 in place, by command (sim only): the up relays need not be re-oriented. ARM_Z9 taken out before c22
        or earlier: RB9's departure (c16 g) or P9's spit (c22 g) updates Z9, unpowered, and it retracts. A_9 brings
        RB9 back over it at c22 j, where RB9 QC-powers Z9 without updating it. D9, a piston at (4,5,1) facing down,
        its source on before c24 at the latest and off before c24 at the earliest, is updated by RB9's landing or
        by its source and pushes RB9 down; RB9 is moving when P9's base lands (c24 j), which would otherwise fire Z9,
        and lands on Z9 at c25 j or later. ARM_Z9 set back from c23 on: its landing updates Z9's head cell, not Z9.
        Back before c25 j, it powers Z9 at P9's landing and RB9's, and Z9's push fails, on RB9 moving, then on D9's
        head: the blocker the load puts at (4,4,1). Z9, RB9, ARM_Z9 and D9 end as the closed state has them and Z9 fires on the next update.
        D9's and ARM_Z9's drives are not designed; no command may follow the input, so this is not yet a design.

Run from the repo root (sim; about 2 minutes):
python -m scripts.door2.close_layout.returns > scripts/door2/close_layout/returns.txt"""
import copy, functools
from collections import deque
from scripts.door2.close_layout import feeds as f, puller as pr, trigger as t, s_inputs as si, p9_p8 as pp, p10_v as pv
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, DIRS, add
from scripts.door2 import volume as v

LO, HI = (-4, -3, -8), (7, 10, 3)                # the box of the opening and the close: the bus's west branch tops it at y 10
NEG = {"west": "east", "east": "west", "up": "down", "down": "up", "north": "south", "south": "north"}
CLOSE = 32                                       # c-1 to c30
RB_T_HOME, RB_ST_HOME, RB12_HOME = (1, 5, -1), t.RB_ST, (-4, 2, 2)
ARM, D9, SRC, Z9, POKE = (5, 3, 1), (4, 5, 1), (4, 6, 1), (4, 2, 1), (4, 1, 1)   # ARM_Z9, the down-pusher, its stand-in source, Z9, a cell under Z9
Z9_CELLS = (Z9, pp.RB9_CLOSED, pp.RB9_OPEN, ARM, D9)
GROUPS = (("the opening's relays and their blocks", ("X2", "Z_Q", "Y1", "Z_S", "Z9", "Z11", "Y12", "RB_X", "C_cut", "RB_Q", "RB_Y", "RB_S",
                                                    "RB9", "RB11", "G")),
          ("the trigger chain's", ("K", "M_K", "RB12", "P_R", "RB_T", "K_T", "SPC", "RB_ST")),
          ("the S feed's", ("A_C", "C_F", "R_F", "R_C")), ("p9_p8's", ("R_9",)))
D9_BLOCK = t.pis("piston", "down", "D9")
# RB_T's return: the down-pusher, its two glass spacers where the closed state has them, the kicker and where it parks RB_T
H_T, GA, GB, N_T, PARK = (1, 9, -1), (1, 7, -1), (1, 6, -1), (2, 6, -3), (2, 6, -2)
COLUMN = (GB, GA, (1, 8, -1))
SRC_H, SRC_N, POKE_R = (1, 10, -1), (3, 6, -3), (3, 6, -2)     # stand-in sources of H_T and N_T; a cell beside P_R
Z_T, T_CELL, K_IN, RB_A_OPEN = (1, 4, -1), (1, 4, 0), (1, 8, -2), f.RB_A
RBT_BLOCKS = {H_T: t.pis("piston", "down", "H_T"), GA: B("glass", id="GA"), GB: B("glass", id="GB"),
              N_T: t.pis("sticky_piston", "south", "N_T")}
# the cells RB_T's return must leave as the closed state has them: the column, the two pistons, P_R, K_T, SPC's and RB_ST's
# cells, Z_T, W_T, T, AP, the stand-in cells and the S feed's thirteen with its cut cell
EAST = [RB_T_HOME, *COLUMN, H_T, N_T, PARK, pr.P_R, pr.HEAD, t.K_T, t.SPC, t.SRC, t.UP, t.RB_ST, Z_T, t.W_T, T_CELL, t.AP,
        SRC_H, SRC_N, POKE_R, *si.MINE, si.CUT]


BOX = [LO, HI]                                   # the box routes keep to; main grows it for the second pass


def in_box(c):
    return all(lo <= x <= hi for x, lo, hi in zip(c, *BOX))


def plane_or_hall(c):
    x, y, z = c
    return (z == 0 and -1 <= x <= 3 and -1 <= y <= 3) or (z != 0 and 0 <= x <= 2 and 0 <= y <= 2)


@functools.lru_cache(None)
def worlds():
    """p9_p8.py's build; the loaded closed state; the world after c30 of the close (noted); the frames of the
    opening and the close from the load, for the mover screen; the free cells."""
    b = pp.build()
    cl = d.make_world(b)[0]
    mine, _ = t.opened(b)
    w = pp.noted(mine)
    ref = list(frames(b))[1:]
    taken = set(d.full_blocks(b)) | set(cl.b) | set(v.cumulative_cells(b)[0])
    for blocks, be in w.frames:
        taken |= set(blocks) | set(be)
    used.cells = frozenset(taken)
    return b, cl, w, ref, free_in(LO, HI)


def used():
    """every cell the closed state, the opening or the close to c30 occupies (set by worlds())."""
    return used.cells


def free_in(lo, hi):
    """the free cells of a box: in it, not used, off the door plane and out of the hallway."""
    taken = used()
    return frozenset(c for c in ((x, y, z) for x in range(lo[0], hi[0] + 1) for y in range(lo[1], hi[1] + 1)
                                 for z in range(lo[2], hi[2] + 1)) if c not in taken and not plane_or_hall(c))


def frames(b):
    """what moved during the load, then (blocks, moving cells) after each tick of the opening and of the close."""
    w, moved = d.make_world(b)
    yield moved
    w.run(4)
    w.cmd_set(f.DRIVER, t.RB)
    for k in range(t.OPEN_TICKS + CLOSE):
        if k == t.OPEN_TICKS:
            w.cmd_set(f.DRIVER, AIR)
        w.tick()
        yield dict(w.b), set(w.be)


def tick_name(k):
    return f"t{k - 1}" if k < t.OPEN_TICKS else f"c{k - t.OPEN_TICKS - 1}"


@functools.lru_cache(None)
def mover(cell, kind, facing):
    """None if a retracted piston of that kind and facing at cell changes nothing, else where it first does."""
    b, _, _, ref, _ = worlds()
    bx = copy.deepcopy(b)
    bx.b[cell] = t.pis(kind, facing, "M")
    g = frames(bx)
    if next(g):
        return "moves during the load"
    for k, ((blocks, be), (rb, rbe)) in enumerate(zip(g, ref)):
        if be != rbe or {p: s for p, s in blocks.items() if p != cell} != rb:
            return "changes the " + ("opening at " if k < t.OPEN_TICKS else "close at ") + tick_name(k)
    return None


def after():
    """a plain world after the close's c30, nothing moving."""
    x = copy.deepcopy(worlds()[2])
    x.__class__ = World
    assert not x.be
    return x


@functools.lru_cache(None)
def stop(cell, gone=None):
    """the pistons a redstone block set at cell fires in 12 ticks after the close (gone: the moving block's own
    cell emptied first, silently), but a piston that moves to its state in the closed state (K_T in, P_R out: their
    returns), and the pistons it leaves powered that were not."""
    cl = worlds()[1]
    w = after()
    if gone:
        w.cmd_set_silent(gone, AIR)
    before = {p for p, s in w.b.items() if s.n in ("piston", "sticky_piston") and power_sources(w, p)}
    w.log.clear()
    w.cmd_set(cell, t.RB)
    w.run(12)
    fired = list(dict.fromkeys(m.split("@")[0].split()[-1] for _, _, m in w.log if ("EXTEND" in m or "RETRACT" in m) and
                               t.at(cl, m.split("@")[0].split()[-1])[2] != ("EXTEND" in m)))
    armed = sorted(s.p.get("id", str(p)) for p, s in w.b.items() if s.n in ("piston", "sticky_piston") and power_sources(w, p) and p not in before)
    return tuple(fired), tuple(armed)


def label(w, c):
    s = w.get(c)
    return s.p.get("id") or s.n


def held(m, u, start):
    """the piston at m, with a redstone block at u (its own cell after the close emptied): what powers it."""
    x = after()
    x.cmd_set_silent(start, AIR)
    x.cmd_set_silent(u, t.RB)
    return [c for _, c in power_sources(x, m)]


def step(u, name, goal, w, free, start):
    """(v, how, None) for the step from u in direction name, else (v, None, why not). A mover is a screened
    piston in a free cell, or a piston already there facing the right way (a puller only if nothing it would
    need gone holds it with the block at u)."""
    dv = DIRS[name]
    v_ = add(u, dv)
    if not in_box(v_):
        return v_, None, "outside the box"
    if v_ != goal and v_ != start and (v_ in w.b or plane_or_hall(v_)):
        return v_, None, f"{label(w, v_)} there" if v_ in w.b else "door plane or hallway"
    if v_ != goal:
        fired, _ = stop(v_, start)
        if fired:
            return v_, None, "a redstone block there fires " + ", ".join(fired)
    why = []
    for m, kinds, facing in ((add(u, dv, -1), ("piston", "sticky_piston"), name), (add(v_, dv), ("sticky_piston",), NEG[name])):
        pull = m != add(u, dv, -1)
        st = w.get(m)
        if m != start and st.n in ("piston", "sticky_piston") and st.p["facing"] == facing:
            hold = held(m, u, start) if pull else []
            if not hold:
                return v_, f"{'pulled' if pull else 'pushed'} by {st.p.get('id')} at {m}" + (", made sticky" if pull and st.n == "piston" else ""), None
            why.append(f"{st.p.get('id')} at {m}, facing {facing}, held by " + ", ".join(f"{label(w, c) if c != u else 'the block'} {c}" for c in hold))
            continue
        if m not in free:
            why.append(f"{m}: " + ("the block's own cell" if m == start else label(w, m) if m in w.b else "outside the box" if not in_box(m) else "not free"))
            continue
        res = {k: mover(m, k, facing) for k in kinds}
        if any(r is None for r in res.values()):
            return v_, f"{'pulled by a sticky piston' if pull else 'pushed by a piston'} at {m} facing {facing}", None
        why.append(f"{m} facing {facing}: {res[kinds[-1]]}")
    return v_, None, "no mover (" + "; ".join(why) + ")"


def route(start, goal, w, free):
    """breadth first; (path or None, reached cells, rejected steps from each reached cell)."""
    prev, q, rejected = {start: None}, deque([start]), {}
    while q:
        u = q.popleft()
        if u == goal:
            break
        for name in DIRS:
            v_, how, why = step(u, name, goal, w, free, start)
            if how and v_ not in prev:
                prev[v_] = (u, how)
                q.append(v_)
            elif why:
                rejected.setdefault(u, []).append((v_, f"{name} to {v_}: {why}"))
    if goal not in prev:
        return None, list(prev), rejected
    path, x = [], goal
    while prev[x]:
        path.append(f"{prev[x][0]} -> {x}, {prev[x][1]}")
        x = prev[x][0]
    return path[::-1], list(prev), rejected


def z9_ticks(arm_off=13, src_on=21, arm_on=27, src_off=29, last=40, poke=False):
    """idle ticks with the what-if's commands, each set before tick c<n> with updates: ARM_Z9 out and back, a
    redstone block at SRC (D9's stand-in source) on and off; `poke`: a glass block set and cleared under Z9 after
    the last tick."""
    ticks = pp.idle(last)
    for k, c, st in ((arm_off, ARM, AIR), (src_on, SRC, t.RB), (arm_on, ARM, t.RB), (src_off, SRC, AIR)):
        if k is not None:
            ticks[k + 1] = ticks[k + 1] + [(c, st)]
    return ticks


def z9_build():
    b = pp.build()
    assert D9 in worlds()[4]
    b.b[D9] = D9_BLOCK
    b.role[D9] = "returns"
    return b


def poke(w):
    """an update of Z9 after the run: a glass block set under it and taken out, then 4 ticks; Z9's extension and
    RB9's cell."""
    x = copy.deepcopy(w)
    x.log.clear()
    x.cmd_set(POKE, t.GLASS)
    x.cmd_set(POKE, AIR)
    x.run(4)
    return [m.split(":")[0] for _, _, m in x.log if "EXTEND" in m or "RETRACT" in m], t.at(x, "RB9")[0]


def z9_verdict(w, cl):
    """what keeps Z9, RB9, ARM_Z9 and D9 from the closed state, the door plane from the closed door's, and Z9 from
    firing on the next update."""
    bad = [f"{c} {w.get(c)}" for c in Z9_CELLS if w.get(c) != cl.get(c)] + [f"moving at {sorted(w.be)}"] * bool(w.be)
    bad += [x for x in pp.verdict_end(w, cl) if not x.startswith("RB9 ")]
    fired, rb9 = poke(w)
    return bad + ([] if rb9 == pp.RB9_OPEN else [f"Z9 does not fire on an update ({fired or 'nothing'})"])


def against(b, skip):
    """b beside p9_p8.py's build: what moved during the load, and the ticks of the opening and the close at which a
    cell outside `skip` differs."""
    g = frames(b)
    moved = next(g)
    return moved, [tick_name(k) for k, ((bl, be), (rb, rbe)) in enumerate(zip(g, worlds()[3]))
                   if be - skip != rbe - skip or {p: s for p, s in bl.items() if p not in skip} != {p: s for p, s in rb.items() if p not in skip}]


def ways_into(cell, w, fr):
    """one line a direction: the mover a block needs to enter `cell` that way, a pusher behind it or a sticky puller
    beyond the cell, and what stands in each mover's cell or what the screen says of a piston there."""
    out = []
    for name, dv in DIRS.items():
        u, push, pull = add(cell, dv, -1), add(cell, dv, -2), add(cell, dv)

        def what(m, kinds, facing):
            if m in fr:
                return ", ".join(f"a {k.replace('_', ' ')} there {mover(m, k, facing) or 'passes the screen'}" for k in kinds)
            return f"{label(w, m)} there" if m in w.b else "not free"
        out.append(f"moving {name} from {u} ({label(w, u) if u in w.b else 'air'}): pushed from {push}: {what(push, ('piston', 'sticky_piston'), name)}; "
                   f"pulled from {pull}: {what(pull, ('sticky_piston',), NEG[name])}")
    return out


def rbt_build(drop=(), swap=None):
    """p9_p8.py's build with RB_T's four: H_T, the spacers GA and GB, N_T; `drop` leaves cells out, `swap` replaces
    or adds some. GB stands in (1,6,-1), a cell of the opening: Z_T lifts it with RB_T."""
    b = pp.build()
    for c, st in {**RBT_BLOCKS, **(swap or {})}.items():
        if c not in drop:
            b.b[c] = st
            b.role[c] = "returns"
    return b


def probe_build(drop=()):
    """rbt_build with D9 as well: close_returns_probe's build (export_returns.py)."""
    b = rbt_build(drop=drop)
    if D9 not in drop:
        b.b[D9] = D9_BLOCK
        b.role[D9] = "returns"
    return b


def rbt_ticks(kick=(32, 34), home=37, back=(38, 43), src=(45, 48), spc=51, last=58, poke=None):
    """idle ticks with the what-if's commands, each set before tick c<n> with updates. kick: a redstone block at
    SRC_N, N_T's stand-in source, on and off (N_T out and in: RB_T pulled north to PARK). home: RB_ST taken out of
    (2,8,0) and set at (3,7,0), its closed cell (stand-in for its return). back: SRC_N on and off again (N_T pushes
    RB_T back in front of P_R and stays out until P_R has taken it). src: a redstone block at SRC_H, H_T's stand-in
    source, on and off. spc: SPC taken out of (2,7,0) and set at (2,6,0) (stand-in for its return). poke: a glass
    block set and cleared beside P_R. None leaves a command out."""
    ticks = pp.idle(last)
    for k, cmds in ((kick and kick[0], [(SRC_N, t.RB)]), (kick and kick[1], [(SRC_N, AIR)]),
                    (home, [(t.UP, AIR), (t.RB_ST, B("rb", id="RB_ST"))]), (poke, [(POKE_R, t.GLASS), (POKE_R, AIR)]),
                    (back and back[0], [(SRC_N, t.RB)]), (back and back[1], [(SRC_N, AIR)]),
                    (src and src[0], [(SRC_H, t.RB)]), (src and src[1], [(SRC_H, AIR)]),
                    (spc, [(t.SRC, AIR), (t.SPC, B("glass", id="SPC"))])):
        if k is not None:
            ticks[k + 1] = ticks[k + 1] + cmds
    return ticks


def rbt_verdict(w, cl):
    """what keeps the trigger chain's east side and the S feed's cut from the closed state `cl`, cell for cell, the
    pistons there from the closed state's power, and the door plane from the closed door's."""
    bad = [f"{c} {'moving' if c in w.be else w.get(c)}" for c in EAST if c in w.be or w.get(c) != cl.get(c)]
    bad += [f"{n} powered by {[c for _, c in power_sources(w, p)]}" for n, p in (("Z_T", Z_T), ("W_T", t.W_T), ("K_T", t.K_T), ("P_R", pr.P_R),
                                                                               ("H_T", H_T), ("N_T", N_T), ("AP", t.AP))
            if w.get(p) == cl.get(p) and power_sources(w, p) != power_sources(cl, p)]
    bad += ["T not powered by RB_T"] * (("qc", RB_T_HOME) not in power_sources(w, T_CELL))
    return bad + pp.verdict_end(w, cl)


def shown(w, first, names):
    return [x for x in pv.told(w) if pv.tick_of(x) >= first and any(f" {n}@" in x for n in names)]


if __name__ == "__main__":
    b, cl, w, ref, free = worlds()
    print("p9_p8.py's build; the world after c30 of its close against the loaded closed state")
    rest, dust = pv.differing(cl, w)
    off = [x for x in rest if not any(x.startswith(str(c) + ":") for c in pp.PLANE)]
    print(f"cells outside the door plane that differ: {len(off)}, dust levels apart")
    ids = {}
    for c in set(cl.b) | set(w.b):
        if c not in pp.PLANE and cl.get(c) != w.get(c) and not cl.get(c).n == w.get(c).n == "redstone_wire":
            for s in (cl.get(c), w.get(c)):
                ids.setdefault(s.p.get("id") or {pp.R_9: "R_9", (2, 8, 1): "R_F", (0, 8, 2): "R_C"}.get(c), set()).add(c)
    def where(x, n):
        p, _, ext = t.at(x, n)
        return str(p) + {True: " out", False: " in", None: ""}[ext]

    for title, names in GROUPS:
        print(f"   {title}:", "; ".join(f"{n} " + (f"{where(cl, n)}, now {where(w, n)}" if t.at(cl, n)[0] else
                                                 ", ".join(f"{c} {cl.get(c)}, now " + ("on" if w.get(c).p.get("powered") else "off")
                                                           for c in sorted(ids[n])))
                                     for n in names))

    print("\n== what holds each fired piston after the close (power sources; R+2: its own payload, a QC cell)")
    for n in ("X2", "Z_Q", "Y1", "Z_S", "Z9", "Z11", "Y12", "K", "M_K", "K_T", "A_C"):
        p, _, _ = t.at(w, n)
        f_ = DIRS[w.get(p).p["facing"]]
        print(f"   {n} {p} facing {w.get(p).p['facing']}:", ", ".join(
            f"{label(w, c)} {c}" + (" (R+2)" if c == add(p, f_, 2) else "") + ("" if k == "direct" else " QC")
            for k, c in power_sources(w, p)))
    p = t.at(w, "P_R")[0]
    print(f"   P_R {p}, in: powered in the closed state by", ", ".join(f"{label(cl, c)} {c}" for _, c in power_sources(cl, p)), "only")

    print(f"\n== the trigger chain's blocks: routes home inside the box ({len(free)} free cells)")
    for n, home in (("RB_T", RB_T_HOME), ("RB_ST", RB_ST_HOME), ("RB12", RB12_HOME)):
        start = t.at(w, n)[0]
        path, reached, rejected = route(start, home, w, free)
        print(f"   {n} {start} to {home}:", "; ".join(path) if path else f"NO ROUTE; reached {', '.join(map(str, reached))}")
        for u in () if path else reached:
            for v_, x in rejected.get(u, []):
                if v_ not in reached:
                    print(f"      from {u}, {x}")
    st, _ = stop((2, 7, 0), (2, 8, 0))
    print("   RB_ST down to (2,7,0), SPC taken out first (what-if): a redstone block there fires", ", ".join(st), "(DT lit, FT powers W_T, "
          "whose head takes (1,5,-1), RB_T's closed cell)")
    print("   SPC (2,7,0) to (2,6,0): K_T's head is in (2,6,0) and RB_T holds K_T. K_T sticky (what-if): opening and close the same but",
          end=" ")
    bk = copy.deepcopy(b)
    bk.b[t.K_T] = t.pis("sticky_piston", "up", "K_T")
    g, g2 = frames(bk), frames(bk)
    next(g), next(g2)
    own = (t.K_T, t.SPC, t.SRC)
    diffs = [tick_name(k) for k, ((bl, be), (rb, rbe)) in enumerate(zip(g, ref))
             if be - {t.SRC} != rbe - {t.SRC} or {p_: s for p_, s in bl.items() if p_ not in own} != {p_: s for p_, s in rb.items() if p_ not in own}]
    spc = [tick_name(k) for k, ((bl, be), (rb, rbe)) in enumerate(zip(g2, ref)) if bl.get(t.SRC) != rb.get(t.SRC) or (t.SRC in be) != (t.SRC in rbe)]
    print("K_T's head is sticky and SPC is real at (2,7,0) instead of moving after", ", ".join(spc) + "; any other cell:", diffs or "none",
          "| K_T would pull SPC home when it retracts, which needs RB_T gone from (2,6,-1)")
    print("   G (-4,4,2) to (-3,3,2): its closed cell is Y12's head, and Y12 is held by its arm (above)")

    print("\n== what-if (sim only): Z9 returned in place, by command. D9, a piston at (4,5,1) facing down, added; ARM_Z9 out before c13 "
          "and back before c27; a redstone block at (4,6,1), D9's stand-in source, before c21 and out before c29")
    print("   D9 alone (no command after the input): mover screen", mover(D9, "piston", "down") or "passes", "| D9 in the closed state",
          "powered" if power_sources(d.make_world(z9_build())[0], D9) else "not powered")
    zb = z9_build()
    zo, _ = t.opened(zb)
    zw = pp.noted(zo, z9_ticks())
    print("\n".join("   " + x for x in pv.told(zw) if pv.tick_of(x) >= 12 and any(k in x for k in (" Z9@", " D9@", " P9@", " A_9@", "land rb@(4,"))))
    zcl = d.make_world(zb)[0]
    bad = z9_verdict(zw, zcl)
    print("   ->", "FAILS: " + "; ".join(bad) if bad else "done: Z9 in, RB9 at (4,3,1), ARM_Z9 at (5,3,1), D9 in, as the closed state has them; "
          "the door plane closed at c25 j as in p9_p8's run; nothing moving")
    print("   Z9 powered by", [f"{label(zw, c)} {c}" for _, c in power_sources(zw, Z9)], "| an update under Z9:", ", ".join(poke(zw)[0]),
          "| RB9 then at", poke(zw)[1])
    ref_ev = pv.per_tick(pp.noted(t.opened(pp.build())[0], pp.idle(40)), -1, 40)
    new = [x for k, (a, c) in enumerate(zip(pv.per_tick(zw, -1, 40), ref_ev)) for x in sorted(set(a) - set(c))]
    print("   piston events against p9_p8's run: added", "; ".join(new), "| none taken away" if all(set(c) <= set(a) for a, c in
                                                                                                  zip(pv.per_tick(zw, -1, 40), ref_ev)) else "| SOME TAKEN AWAY")
    print("   windows, one command moved at a time (the others as above), done or not:")
    for title, kw, ks in (("ARM_Z9 out before", "arm_off", range(10, 24)), ("ARM_Z9 back before", "arm_on", range(21, 32)),
                          ("D9's source on before", "src_on", range(14, 27)), ("D9's source off before", "src_off", range(22, 32))):
        res = {k: not z9_verdict(pp.noted(zo, z9_ticks(**{kw: k})), zcl) for k in ks}
        print(f"      {title}:", " ".join(f"c{k} {'done' if ok else 'FAILS'}" for k, ok in res.items()))
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)), ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True))):
        x = pp.noted(zo, z9_ticks(), **kw)
        print(f"   {name}:", "FAILS" if z9_verdict(x, zcl) else "done;", "piston events of each tick",
              "the same set" if pv.per_tick(x, -1, 40) == pv.per_tick(zw, -1, 40) else "DIFFER")
    print("   ARM_Z9 back before c23 to c24 exercises the blocker: Z9 is updated by P9's landing (c24 j) with RB9 moving below D9's head, "
          "and by RB9's landing (c25 j):")
    x = pp.noted(zo, z9_ticks(arm_on=23), before={0: lambda y: y.woke.setdefault("Z9", [])})
    print("      Z9's updates while it is in, c22 to c26:", pp.woke(x, "Z9", 22, 26), "| ->", "FAILS" if z9_verdict(x, zcl) else "done")
    print("   controls:")
    for title, kw in (("ARM_Z9 left in place: Z9 stays out and D9 cannot push RB9 into its head", dict(arm_off=None, arm_on=None)),
                      ("no source for D9: RB9 stays over Z9, and P9's landing at c24 j fires Z9 again (c25 g)", dict(src_on=None, src_off=None)),
                      ("ARM_Z9 back before c22: P9's spit (c22 g) fires Z9 into the empty cell", dict(arm_on=21))):
        x = pp.noted(zo, z9_ticks(**kw))
        bad = z9_verdict(x, zcl)
        print(f"      {title}:", "FAILS: " + "; ".join(bad[:3]) if bad else "done", "| Z9", "out" if t.at(x, "Z9")[2] else "in", "RB9", t.at(x, "RB9")[0])

    grow = 2
    lo, hi = tuple(x - grow for x in LO), tuple(x + grow for x in HI)
    BOX[:] = [lo, hi]
    fr = free_in(lo, hi)
    print(f"\n== the box grown by {grow} on every side, x {lo[0]}..{hi[0]} y {lo[1]}..{hi[1]} z {lo[2]}..{hi[2]} ({len(fr)} free cells), measured blocks "
          "unchanged: routes home")
    for n, home in (("RB_T", RB_T_HOME), ("RB12", RB12_HOME), ("RB_ST", RB_ST_HOME)):
        start = t.at(w, n)[0]
        path, reached, rejected = route(start, home, w, fr)
        print(f"   {n} {start} to {home}:", "; ".join(path) if path else f"NO ROUTE; reached {', '.join(map(str, reached))}, as in the box")
    print("   every way into (1,5,-1), RB_T's closed cell, for any block (box-independent: every cell named is inside the box):")
    for x in ways_into(RB_T_HOME, w, fr):
        print("      " + x)
    print("   every way into (1,5,-2), from where W_T made sticky would pull a block into (1,5,-1) (what-if):")
    for x in ways_into(RB_A_OPEN, w, fr):
        print("      " + x)
    BOX[:] = [LO, HI]

    def names(src, x):
        return [f"{label(x, c)} {c}" + ("" if k == "direct" else " QC") for k, c in src] or "nothing"

    print("\n== RB_T's last step, (1,6,-1) down to (1,5,-1), now that the bus's west branch is off (1,8,-1) and (1,7,-1)")
    for kind in ("piston", "sticky_piston"):
        bx = copy.deepcopy(b)
        bx.b[GA] = t.pis(kind, "down", "X")
        wx, moved = d.make_world(bx)
        closed = names(power_sources(wx, GA), wx)
        wx.run(4)
        wx.cmd_set(f.DRIVER, t.RB)
        ev, t0 = [], None
        for k in range(t.OPEN_TICKS):
            wx.log.clear()
            wx.tick()
            ev += [f"{tick_name(k)}{ph} {m.split(':')[0]}" for _, ph, m in wx.log if any(n in m for n in (" X@", " Z_T@", " T@")) and ("EXTEND" in m or "RETRACT" in m)]
            t0 = names(power_sources(wx, GA), wx) if k == 1 else t0
        print(f"   the fix as chosen, a {kind.replace('_', ' ')} at (1,7,-1) facing down: screen: {mover(GA, kind, 'down') or 'passes'} | moved during the load:",
              moved or "none", f"| powered in the closed state by {closed}, after t0 by {t0} | X, Z_T and T in the opening: {'; '.join(ev)} "
              f"(p9_p8's build: t3g EXTEND T, t3g EXTEND Z_T, t3g RETRACT T) | after t13: X", "out" if t.at(wx, "X")[2] else "in", "powered by",
              names(power_sources(wx, GA), wx))
    print("      K_in is strongly powered while the input is on and stands beside (1,8,-1), the cell above the piston: QC, whatever is in "
          "(1,8,-1). I_A's extension beside the piston updates it at t0 g, it extends into the empty (1,6,-1), and Z_T cannot lift RB_T at t3")
    x = after()
    x.cmd_set_silent(Z_T, t.pis("sticky_piston", "up", "Z_T"))
    x.cmd_set_silent(t.at(x, "RB_T")[0], AIR)
    x.cmd_set(GB, B("rb", id="RB_T"))
    held_by = names(power_sources(x, Z_T), x)
    x.cmd_set((0, 4, -1), t.GLASS)
    x.cmd_set((0, 4, -1), AIR)
    x.run(6)
    print("   Z_T made sticky (what-if; set into the world after the close, RB_T set at (1,6,-1) as P_R's push leaves it): Z_T powered by", held_by,
          "(its own payload at R+2) | after an update:", {n: t.at(x, n) for n in ("Z_T", "RB_T")}, "| still powered by", names(power_sources(x, Z_T), x),
          "| a sticky Z_T is held out by the block it would pull")
    wt = d.make_world(b)[0]
    held0 = names(power_sources(wt, T_CELL), wt)
    wt.run(4)
    wt.cmd_set(f.DRIVER, t.RB)
    wt.run(4)
    print("   T held otherwise: T's power in the closed state:", held0, "| after t2, the tick before it fires:", names(power_sources(wt, T_CELL), wt),
          "| T fires on RB_T at t3 g and Z_T's lift takes RB_T away in that phase: another hold is another relay for the opening's T stage")

    print("\n== the column (what-if): H_T, a piston at (1,9,-1) facing down, clear of K_in; glass spacers GA (1,7,-1) and GB (1,6,-1) in the "
          "closed state, lifted with RB_T by Z_T at t3 to (1,8,-1) and (1,7,-1); N_T, a sticky piston at (2,6,-3) facing south")
    rb_ = rbt_build()
    moved, differ = against(rb_, set(COLUMN) | {H_T, N_T})
    print("   moved during the load:", moved or "none", "| the opening and the close to c30 outside the column's three cells:",
          f"differ at {differ}" if differ else "the same at every tick")
    rcl = d.make_world(rb_)[0]
    ro, _ = t.opened(rb_)
    seen, last_ = [], None
    for k, (bl, be) in enumerate(list(frames(rb_))[1:t.OPEN_TICKS + 3]):
        cur = [("~" if c in be else "") + (bl[c].p.get("id") or bl[c].n if c in bl else "air") for c in (RB_T_HOME, *COLUMN)]
        if cur != last_:
            seen.append(f"{tick_name(k)} " + ", ".join(cur))
            last_ = cur
    print("   (1,5,-1), (1,6,-1), (1,7,-1), (1,8,-1) after each tick they change (~ moving):", "; ".join(seen))
    ra = pp.noted(ro)
    wq, _ = d.make_world(rb_)
    lit = [f"{n} closed" for n, c in (("H_T", H_T), ("N_T", N_T)) if power_sources(wq, c)]
    wq.run(4)
    wq.cmd_set(f.DRIVER, t.RB)
    for k in range(t.OPEN_TICKS + CLOSE):
        if k == t.OPEN_TICKS:
            wq.cmd_set(f.DRIVER, AIR)
        wq.tick()
        lit += [f"{n} {tick_name(k)}" for n, c in (("H_T", H_T), ("N_T", N_T)) if power_sources(wq, c)]
    print("   H_T and N_T powered:", ", ".join(lit) or "never: not in the closed state, nor after any tick of the opening or of the close to c30")
    print("   the bus dust beside H_T in the open state:", {c: ro.get(c).p["power"] for c in ((1, 9, -2), (0, 9, -1))},
          "| neither points at it: (1,9,-2) runs west up the step and east down it, (0,9,-1) north up the step and west")

    print("\n== the trap: P_R woken straight after the close (RB_ST set home before c31, a glass block set and cleared beside P_R before c32, "
          "H_T's source before c40)")
    tr = pp.noted(ro, rbt_ticks(kick=None, home=31, poke=32, back=None, src=(40, 43), spc=None, last=46))
    print("\n".join("   " + x for x in shown(tr, 31, ("P_R", "K_T", "W_T", "H_T"))))
    print("   ->", {n: t.at(tr, n) for n in ("RB_T", "W_T", "K_T", "H_T")}, "| W_T powered by", names(power_sources(tr, t.W_T), tr))
    print("      K_T, held by RB_T at (2,6,-1), retracts in P_R's phase; its base lands in the same phase j as RB_T, behind it, and updates "
          "W_T, which RB_T at (1,6,-1) powers by QC: W_T's head takes (1,5,-1) and H_T's push stops on it")

    print("\n== what-if (sim only): RB_T returned by command. N_T's stand-in source (3,6,-3) before c32 and out before c34 (the kick); RB_ST out "
          "of (2,8,0) and at (3,7,0) before c37; the source again before c38 and out before c43; H_T's stand-in source (1,10,-1) before c45 and out "
          "before c48; SPC out of (2,7,0) and at (2,6,0) before c51")
    rw = pp.noted(ro, rbt_ticks())
    print("\n".join("   " + x for x in shown(rw, 31, ("N_T", "P_R", "K_T", "W_T", "H_T", "Z_T", "A_C", "T"))))
    bad = rbt_verdict(rw, rcl)
    print("   ->", "FAILS: " + "; ".join(bad) if bad else "done: RB_T at (1,5,-1), GB and GA under H_T, P_R out, K_T in, N_T and H_T in, Z_T not powered, T powered by "
          "RB_T, W_T, AP and the S feed's thirteen as the closed state has them; the door plane closed; nothing moving")
    rest, _ = pv.differing(rcl, rw)
    off = [x for x in rest if not any(x.startswith(str(c) + ":") for c in pp.PLANE)]
    off0 = [x for x in pv.differing(rcl, ra)[0] if not any(x.startswith(str(c) + ":") for c in pp.PLANE)]
    print(f"   cells outside the door plane that still differ from the closed state: {len(off)} ({len(off0)} after the close in this build, the column's three "
          "among them):",
          "; ".join(f"{n} {where(rcl, n)}, now {where(rw, n)}" for n in GROUPS[0][1] + ("K", "M_K", "RB12") if t.at(rcl, n) != t.at(rw, n)))
    ref_ev = pv.per_tick(pp.noted(t.opened(pp.build())[0], pp.idle(58)), -1, 58)
    mine_ev = pv.per_tick(rw, -1, 58)
    print("   piston events against p9_p8's run: added", "; ".join(x.split(":")[0] for a, c in zip(mine_ev, ref_ev) for x in sorted(set(a) - set(c))),
          "| none taken away" if all(set(c) <= set(a) for a, c in zip(mine_ev, ref_ev)) else "| SOME TAKEN AWAY")
    print("   windows, one command moved at a time (the others as above), done or not:")
    base = dict(kick=(32, 34), home=37, back=(38, 43), src=(45, 48))
    for title, key, i, ks in (("the kick's source on before", "kick", 0, range(27, 34)), ("the kick's source off before", "kick", 1, range(33, 38)),
                              ("RB_ST home before", "home", None, range(31, 44)), ("the source again before", "back", 0, range(35, 43)),
                              ("and off before", "back", 1, range(39, 46)), ("H_T's source on before", "src", 0, range(40, 48)),
                              ("H_T's source off before", "src", 1, range(46, 51))):
        res = {}
        for k in ks:
            kw = dict(base)
            kw[key] = k if i is None else tuple(k if j == i else v for j, v in enumerate(base[key]))
            res[k] = not rbt_verdict(pp.noted(ro, rbt_ticks(**kw)), rcl)
        print(f"      {title}:", " ".join(f"c{k} {'done' if ok else 'FAILS'}" for k, ok in res.items()))
    early = {k: not rbt_verdict(pp.noted(ro, rbt_ticks(kick=(k, k + 2), home=k + 5, back=(k + 6, k + 11), src=(k + 13, k + 16), spc=k + 19, last=58)), rcl)
             for k in range(3, 33)}
    print("   the whole schedule moved earlier, the kick's source on before:", " ".join(f"c{k} {'done' if ok else 'FAILS'}" for k, ok in early.items()))
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)), ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True))):
        x = pp.noted(ro, rbt_ticks(), **kw)
        print(f"   {name}:", "FAILS" if rbt_verdict(x, rcl) else "done;", "piston events of each tick",
              "the same set" if pv.per_tick(x, -1, 58) == mine_ev else "DIFFER")
    print("   controls:")
    for title, bkw, kw in (("RB_ST home before the kick (c31): P_R, powered, is updated when RB_T is pulled away and extends into the empty cell", {}, dict(home=31)),
                           ("no GB: Z_T lifts RB_T alone and H_T's push ends a cell short", dict(drop=(GB,)), {}),
                           ("no source for H_T: RB_T stays at (1,6,-1)", {}, dict(src=None)),
                           ("N_T not sticky: no kick, RB_T is never in front of N_T's head", dict(swap={N_T: t.pis("piston", "south", "N_T")}), {})):
        cb = rbt_build(**bkw)
        x = pp.noted(t.opened(cb)[0], rbt_ticks(**kw))
        bad = rbt_verdict(x, d.make_world(cb)[0])
        print(f"      {title}:", "FAILS: " + "; ".join(bad[:4]) if bad else "done", "| RB_T", t.at(x, "RB_T")[0], "P_R", "out" if t.at(x, "P_R")[2] else "in",
              "W_T", "out" if t.at(x, "W_T")[2] else "in")
    kb = rbt_build(swap={t.K_T: t.pis("sticky_piston", "up", "K_T")})
    x = pp.noted(t.opened(kb)[0], rbt_ticks(spc=None))
    print("   K_T made sticky (what-if; a measured block changed), no command for SPC:", "FAILS: " + "; ".join(rbt_verdict(x, d.make_world(kb)[0])[:4])
          if rbt_verdict(x, d.make_world(kb)[0]) else "done: K_T pulls SPC home when the kick releases it", "| SPC", t.at(x, "SPC")[0])
