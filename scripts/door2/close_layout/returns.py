"""The returns, after the close (door coords): what the 41 cells that still differ from the loaded closed state
after p9_p8.py's close need, and whether the trigger chain's blocks can go home inside the box. Nothing is added
to p9_p8.py's build except in the what-ifs. Everything printed is COMPUTED on the simulator; nothing here ran on a
server.

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
        fire no piston in 12 ticks. The screen is lenient: a stop may leave a piston powered and not updated.
        Breadth first from the block's cell after the close; each step to a cell not reached is printed with why.
Verdict RB_T, RB_ST and RB12 have no route home: the trigger chain cannot be returned inside the box by blocks
        added to it, whatever drives them. RB_ST is shut in at (2,8,0) on the box's top layer: a redstone block at
        (3,8,0) or (2,8,-1) lights the bus (I_A or AP fires, and W_T), R_F stands south, the stone over DT west and
        SPC below, and at (2,7,0) it lights DT and W_T fires into (1,5,-1); the way out is up, out of the box. RB_T
        gets to (1,6,-1) (P_R's push), (2,7,-1) and (2,6,-2) and no further: (1,5,-1) is entered from (1,6,-1)
        only past the bus's glass (1,7,-1) or by Z_T's own pull, and RB_T at (1,6,-1) holds Z_T by QC; the other
        ways pass a cell where a redstone block fires Z_T or AP, or have no free mover. RB12 cannot move: K's head
        is under it, G above it, M_K and Y12's head beside it, the box edge west, and south no mover. G's closed
        cell is Y12's head. K_T made sticky would pull SPC home, but only once RB_T has left (2,6,-1).
Grown   The box grown by 2 on every side, measured blocks unchanged (the lead's relaxation of 2026-11-22): RB12 and
        RB_ST have routes in the screen (west round (-5,3,2) to (-5,2,2), movers out to x -6; up over (2,9,0), (3,9,0),
        (3,9,1), (3,8,1), (3,7,1), movers up to y 10; the screen is static and does not keep movers off the path:
        (3,9,1) is on it). RB_T has none, as in the box: every way into (1,5,-1), for any block, needs a mover in
        R_8's cell, r_P10's, the bus's glass (1,7,-1), Z_T's (non-sticky, and held by a block at (1,6,-1)), W_T's or a
        wall's, or one of three free cells whose piston moves during the load ((0,5,-1): NA's stone beside it;
        (1,5,-3): NA's dust and RB_A) or fires at c3 ((2,5,-1): under RB_T); all of them inside the box. So the
        trigger chain cannot be returned without changing a measured block, whatever the box.
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
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, p10_v as pv
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, DIRS, add
from scripts.door2 import volume as v

LO, HI = (-4, -3, -8), (7, 8, 3)
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
        for u in reached:
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
    for name, dv in DIRS.items():
        u, push, pull = add(RB_T_HOME, dv, -1), add(RB_T_HOME, dv, -2), add(RB_T_HOME, dv)

        def what(m, kinds, facing):
            if m in fr:
                return ", ".join(f"a {k.replace('_', ' ')} there {mover(m, k, facing)}" for k in kinds)
            return f"{label(w, m)} there" if m in w.b else "not free"
        print(f"      moving {name} from {u} ({label(w, u) if u in w.b else 'air'}): pushed from {push}: {what(push, ('piston', 'sticky_piston'), name)}; "
              f"pulled from {pull}: {what(pull, ('sticky_piston',), NEG[name])}")
    BOX[:] = [LO, HI]
