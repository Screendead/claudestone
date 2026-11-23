"""Z9's re-arm in place, D9's source from blocks (door coords): after the close Z9 goes in and is armed as the load
leaves it, RB9 at (4,3,1) on its head cell, ARM_Z9 at (5,3,1), (4,4,1) empty, with Z11's return and Y12's re-arm
(z11.py) the same at every tick. returns.py's what-if, with D9's stand-in source made of blocks: the S feed's line
carried round x 3 and the timer to the cell above D9. ARM_Z9's mover is not done from blocks: it has none in the free
cells (z9_search.txt), so ARM_Z9 is still taken out and set back by command after the input. 25 blocks on z11.py's
build (D9 and its source), no measured block changed, box 2940. Everything printed is COMPUTED on the simulator;
nothing here ran on a server.

Holds   After the close Z9 (4,2,1) is out, held by ARM_Z9 (5,3,1), beside the cell above it (QC), and by RB9 at (4,4,1),
        its payload at R+2, which A_9 takes east at c16 g and brings back at c22 j (p9_p8.py). ARM_Z9 gone, RB9's
        departure (c16 g) updates Z9 through its head and it retracts; RB9's return powers it by QC without an update.
        P9's base lands beside Z9 at c24 j: by then RB9 has to be moving down into (4,3,1), or Z9 fires into the empty
        cell. So D9, a piston at (4,5,1) facing down, has to be powered at RB9's landing (c22 j), which updates it, or
        updated with power by c23: it pushes RB9 down at c23 g and RB9 lands on Z9's head cell at c25 j.
Source  The signals dark in the closed state and the opening and lit at c23 are the S feed's line ((2,8,1) to Q_C, c10
        to c42, which reads RB_ST at (2,8,0)), R_0 (c18 to c26), RB_ST and RB_T, and RB11, RB_U and RB12 on the west
        side; they lie at x 2 and below, behind RB_1, RB_2, G_N, ARM_ZS and LY at x 3 (z9_search.txt). LY, the lead's,
        is lit in the closed state, and its death at t0 g updates D9 (its dust (4,5,2) is beside D9) while (4,4,1) is
        empty. The line: R9_1, a 1-tick repeater at (2,8,3)
        facing north, reads the line's dust (2,8,2); dust W9_1 to W9_3 along z 4 at y 8; R9_2 and R9_3, 1-tick repeaters
        facing west at (5,8,4) and (6,8,4), past the timer's dust (5,8,3) and its step at (6,7,3), which dust would join;
        dust W9_4 at (7,8,4); R9_4, a 1-tick repeater facing south at (7,8,3), past (6,7,3) again; dust W9_5 (7,8,2), W9_6
        (7,7,1) and W9_7 (6,6,1) stepping down, W9_5 and W9_6 on stone, since a dust passes power down a step only over
        a conductor; R9_5, a 1-tick repeater at (5,6,1) facing east, points into (4,6,1), the cell above D9: D9 is powered
        by QC and updated by R9_5's changes. Ten glass blocks carry the rest. On from c20 d to c52 d.
Run     D9 is powered from c20 d: its push then fails on A_9's head in (4,4,1) (c20 d) and on RB9 moving (c20 g). RB9's
        landing at c22 j updates it: D9 pushes RB9 down at c23 g, RB9 lands at (4,3,1) at c25 j, after P9's base (c24 j).
        STAND-IN: ARM_Z9 taken out before c13 and set back before c27, both with updates (returns.py's what-if). Its
        landing updates the cell above Z9, where RB9 is: not Z9. Z9, powered by ARM_Z9 again, is updated at RB9's
        landing (c25 j) and later only with D9's head in (4,4,1), so its push fails (the blocker). R9_5 turns off at c52
        d and D9 retracts. End: Z9 in, powered by ARM_Z9 and not updated, RB9 at (4,3,1), D9 in, the line dark: Z9 fires
        on the next update. 14 cells outside the door plane still differ from the closed state (17 after z11.py).
Left    ARM_Z9's mover. Its neighbours are Z9's head cell, RB9's stroke (5,4,1) beside LY, S_L, R_9, LY's glass (5,3,2)
        and (5,2,1); in (5,2,1) it powers Z9 directly, and a sticky piston at (5,1,1) that would pull it there is held
        out by ARM_Z9 itself (QC). No free cell takes it (z9_search.txt). With ARM_Z9 one cell over, at (4,3,2) (a
        design_c block moved: the lead's call), a sticky piston at (4,3,4) facing north pulls it to (4,3,3) and back
        (the what-if).

Not controls: the glass under the dust and the repeaters (the simulator has no rule for support); ARM_Z9's two
commands.
Run from the repo root (sim; about a minute):
python -m scripts.door2.close_layout.z9 > scripts/door2/close_layout/z9.txt"""
import copy
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, p10_v as pv, returns as r, rbt_drives as rd, west_drives as wd, y12 as y, y12_holds as h, z11 as z
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World

Z9, D9, ARM, HEAD, OPEN = r.Z9, r.D9, r.ARM, pp.RB9_CLOSED, pp.RB9_OPEN          # HEAD: Z9's head cell, RB9's closed cell; OPEN: RB9's open cell
ABOVE = (4, 6, 1)                                                                   # the cell above D9, where R9_5 points
ARM_BLOCK = d.ARM[ARM]
R9_1, R9_2, R9_3, R9_4, R9_5 = (2, 8, 3), (5, 8, 4), (6, 8, 4), (7, 8, 3), (5, 6, 1)
W9 = ((2, 8, 4), (3, 8, 4), (4, 8, 4), (7, 8, 4), (7, 8, 2), (7, 7, 1), (6, 6, 1))   # W9_1 to W9_7
S9_1, S9_2 = (7, 7, 2), (7, 6, 1)                                                   # the stones under W9_5 and W9_6
GLASSES = ((2, 7, 3), (2, 7, 4), (3, 7, 4), (4, 7, 4), (5, 7, 4), (6, 7, 4), (7, 7, 4), (7, 7, 3), (6, 5, 1), (5, 5, 1))
FACING = {R9_1: "north", R9_2: "west", R9_3: "west", R9_4: "south", R9_5: "east"}
REPEATERS = {c: rd.rep(fc, 1) for c, fc in FACING.items()}
LINE = {**REPEATERS, **{c: t.DUST for c in W9}, S9_1: t.STONE, S9_2: t.STONE, **{c: t.GLASS for c in GLASSES}}
MINE = {D9: r.D9_BLOCK, **LINE}
NAMES = {D9: "D9", **{c: f"R9_{k}" for k, c in enumerate(FACING, 1)}, **{c: f"W9_{k}" for k, c in enumerate(W9, 1)}, S9_1: "S9_1", S9_2: "S9_2",
         **{c: f"the glass {c}" for c in GLASSES}, Z9: "Z9", HEAD: "(4,3,1)", OPEN: "(4,4,1)", ARM: "ARM_Z9", ABOVE: "(4,6,1)"}
ARM_AT = (13, 27)                                     # the stand-in: ARM_Z9 taken out before c13 and set back before c27, with updates
COLUMN = (Z9, HEAD, OPEN, ARM)                        # the cells of z11.py's run that this re-arm changes
CELLS = (*COLUMN, *MINE)
LAST = z.LAST
SEEN = ("Z9", "D9", "A_9", "P9")
wd.SHOW = (*wd.SHOW, *(f"repeater {c} " for c in REPEATERS), f"land rb@{HEAD}")


def build(drop=(), swap=None):
    """z11.py's build with the 25 blocks; `drop` leaves cells out, `swap` replaces or adds some."""
    b = z.build()
    for c, st in {**MINE, **(swap or {})}.items():
        if c not in drop:
            assert c in (swap or {}) or c not in b.b, c
            b.b[c] = st
            b.role[c] = "z9"
    return b


def poked(w):
    """an update of Z9 after the run (returns.py's poke: a glass block set under Z9 and taken out, then 4 ticks):
    whether Z9 fires and RB9 goes up to (4,4,1)."""
    fired, rb9 = r.poke(w)
    return any("Z9@" in m and "EXTEND" in m for m in fired) and rb9 == OPEN


def verdict(w, cl):
    """z11.py's verdict (RB9's line apart: it ends on Z9's head cell now), the cells of Z9's column, ARM_Z9's and the 25
    blocks as loaded, Z9 and D9 powered as in the closed state, the repeaters off, and Z9 firing on the next update.
    Empty when Z9 is re-armed."""
    bad = [x for x in z.verdict(w, cl) if not x.startswith("RB9 ")]
    bad += [f"{NAMES[c]} {'moving' if c in w.be else w.get(c)}" for c in CELLS if c in w.be or pp.bare(w.get(c)) != pp.bare(cl.get(c))]
    bad += [f"{n} powered by {[x for _, x in power_sources(w, c)]}" for n, c in (("Z9", Z9), ("D9", D9))
            if w.get(c).n == cl.get(c).n == "piston" and power_sources(w, c) != power_sources(cl, c)]
    bad += [f"{NAMES[c]} on" for c in REPEATERS if w.get(c).p.get("powered")]
    return bad + ([] if bad or poked(w) else ["Z9 does not fire on an update"])


def commands(arm=ARM_AT):
    """{tick: function}: ARM_Z9 taken out before c`arm[0]` and set back before c`arm[1]`, both with updates; None
    leaves the commands out (a part may be None)."""
    out = {}
    for k, st in zip(arm or (), (AIR, ARM_BLOCK)):
        if k is not None:
            out[k] = (lambda s: lambda w: w.cmd_set(ARM, s))(st)
    return out


def run(b, arm=ARM_AT, hold=z.HOLD_AT, opened=None, extra=None, last=LAST, **kw):
    """b opened from the input and taken through the close and the returns with ARM_Z9's two commands and z11.py's
    stand-in: (closed state, noted world, verdict); `extra` {tick: function of the world} acts before that tick as
    well."""
    before = commands(arm)
    for k, fn in (extra or {}).items():
        before[k] = (lambda g, e: lambda w: (g(w), e(w)))(before[k], fn) if k in before else fn
    cl, w, _ = z.run(b, hold=hold, opened=opened, extra=before, last=last, **kw)
    return cl, w, verdict(w, cl)


def mine_line(x):
    return any(f" {n}@" in x for n in SEEN) or any(f"repeater {c} " in x for c in REPEATERS) or f"land rb@{HEAD}" in x or f"land rb@{OPEN}" in x


def said(w, first=10, last=60):
    return [x for x in pv.told(w) if first <= pv.tick_of(x) <= last and mine_line(x)]


def where(w):
    return ", ".join(f"{n} {t.at(w, n)[0]}" + {True: " out", False: " in", None: ""}[t.at(w, n)[2]] for n in ("Z9", "RB9", "D9")) + \
        f", ARM_Z9's cell {w.get(ARM).n}, (4,4,1) {'moving' if OPEN in w.be else w.get(OPEN).n}"


def events(w, first=10, last=60):
    return "; ".join(f"c{pv.tick_of(m)}" + m.split(" ", 1)[1].split(":")[0].replace("level ", " level ") for m in pv.told(w)
                     if first <= pv.tick_of(m) <= last and any(f" {n}@" in m for n in ("Z9", "D9"))) or "none"


def spans(w, test):
    """after which ticks of the close `test(blocks world)` holds."""
    ks = []
    for k, (bl, _) in enumerate(w.frames):
        x = World()
        x.b = bl
        ks += [k - 1] * bool(test(x))
    return h.runs(ks) if ks else "never"


def second(b, w, cl):
    """the world after the run with every other cell set back as loaded, without updates (a stand-in for the
    returns not designed), opened again: the cells set back, the ticks at which the second opening differs from
    the first, labels apart, and the second close and returns with the same stand-ins."""
    x = copy.deepcopy(w)
    x.__class__ = World
    back = [c for c in set(cl.b) | set(x.b) if pp.bare(cl.get(c)) != pp.bare(x.get(c))]
    for c in back:
        x.cmd_set_silent(c, cl.get(c))
    a, _ = d.make_world(b)
    for q in (a, x):
        q.run(4)
        q.cmd_set(f.DRIVER, t.RB)
    differ = []
    for k in range(t.OPEN_TICKS):
        a.tick()
        x.tick()
        differ += [f"t{k - 1}"] * (set(a.be) != set(x.be) or {c: pp.bare(st) for c, st in a.b.items()} != {c: pp.bare(st) for c, st in x.b.items()})
    return back, differ, run(b, opened=x)


def reversed_from(first, last):
    """{tick: function}: before each tick from c`first` to c`last`, the scheduled ticks due in it in reverse order,
    priorities ignored (sim only)."""
    def fn(w):
        due = sorted((x for x in w.sched if x[0] <= w.time + 1), key=lambda x: (x[1], x[2]))
        w.sched = [x for x in w.sched if x[0] > w.time + 1] + [(x[0], 0, sub, x[3], x[4]) for x, sub in zip(reversed(due), sorted(q[2] for q in due))]
    return {k: fn for k in range(first, last + 1)}


class Moved:
    """ARM_Z9 moved in design_c's ARM table (sim only, a what-if): `with Moved(new):` the load puts it at `new`."""
    def __init__(self, new):
        self.new = new

    def __enter__(self):
        self.saved = dict(d.ARM)
        d.ARM.pop(ARM)
        d.ARM[self.new] = ARM_BLOCK

    def __exit__(self, *a):
        d.ARM.clear()
        d.ARM.update(self.saved)


# name: (title, build keywords, run keywords)
CONTROLS = {
    "no D9": ("RB9 stays over Z9: P9's landing at c24 j fires Z9 again at c25", dict(drop=(D9,)), {}),
    "no R9_1": ("the line stays dark and D9 never moves: the same", dict(drop=(R9_1,)), {}),
    "no R9_5": ("the same: nothing powers D9", dict(drop=(R9_5,)), {}),
    "no command for ARM_Z9": ("ARM_Z9 holds Z9 out; D9 cannot push RB9 into Z9's head", {}, dict(arm=None)),
    "ARM_Z9 back before c22": ("Z9 retracted at c16 is powered again when P9's spit (c22 g) updates it, and fires into the empty cell", {},
                               dict(arm=(ARM_AT[0], 22))),
}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    r.worlds()
    zb = z.build()
    zcl, zw, zbad = z.run(zb)
    assert not zbad
    zref = list(wd.frames(zb))[1:]
    b = build()
    kinds = [st.n for st in MINE.values()]
    print(f"added: {len(MINE)} blocks on z11.py's build (D9, a piston; its source: {kinds.count('repeater')} repeaters, {kinds.count('redstone_wire')} "
          f"dust, {kinds.count('stone')} stone, {kinds.count('glass')} glass under dust and repeaters); no measured block changed; one stand-in, "
          f"ARM_Z9's mover: ARM_Z9 taken out and set back by command after the input, with updates (before c{ARM_AT[0]} and before c{ARM_AT[1]}); "
          "z11.py's stand-in for H11's pull as it was")
    taken = set(d.full_blocks(zb)) | set(zcl.b) | set(v.cumulative_cells(zb)[0])
    for blocks, be in (*zref, *zw.frames):
        taken |= set(blocks) | be
    print("added cells that z11.py's build fills at any tick or on the door plane or in the hallway:",
          ", ".join(f"{NAMES[c]} {c}" for c in MINE if c in taken or r.plane_or_hall(c)) or "none")
    moved, first = wd.against(b, zref, set(MINE))
    print("moved during load:", moved or "none", "| the opening, and the close and the returns to c70 without ARM_Z9's commands, against z11.py's "
          "build, outside the 25 cells:", "; ".join(f"{NAMES.get(c, c)} from {k}" for c, k in sorted(first.items(), key=lambda x: (wd.tick_key(x[1]), x[0])))
          or "the same at every tick")
    cl, w, bad = run(b)
    op, _ = t.opened(b)
    print("open state:", ", ".join(f"{n} " + ("out" if t.at(op, n)[2] else "in") + f" powered by {[x for _, x in power_sources(op, c)] or 'nothing'}"
                                   for n, c in (("D9", D9), ("Z9", Z9))), "| RB9", t.at(op, "RB9")[0], "| the line",
          "dark" if not any(op.get(c).p.get("power") or op.get(c).p.get("powered") for c in LINE) else "LIT")
    print("closed state:", ", ".join(f"{n} powered by {[x for _, x in power_sources(cl, c)] or 'nothing'}" for n, c in (("Z9", Z9), ("D9", D9))))
    late = h.frame_diff(w.frames, zw.frames, CELLS)
    print(f"the close and the returns, c-1 to c{LAST}, against z11.py's run, cells outside the 25 blocks, Z9's column and ARM_Z9's that differ:",
          "; ".join(f"{c} after {h.runs(ks)}" for c, ks in sorted(late.items())) or "none", "| every other cell is the same at every tick")
    mine = h.frame_diff(w.frames, zw.frames, MINE)
    print("   Z9's column and ARM_Z9's cell against z11.py's run:", "; ".join(f"{NAMES[c]} after {h.runs(ks)}" for c, ks in sorted(mine.items())))
    cells = set(v.cumulative_cells(b)[0])
    for blocks, _ in w.frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print("box, opening + close + returns:", t.s.box(cells))

    print(f"\n== the close and the returns from the input, with ARM_Z9's two commands: c10 to c60 (Z9's, D9's, A_9's and P9's events, the five "
          "repeaters, RB9's landings)")
    print("\n".join("   " + x for x in said(w)))
    print("   ->", y.ok(bad) if bad else "done: Z9 in, powered by ARM_Z9 and not updated since; RB9 at (4,3,1), (4,4,1) empty, ARM_Z9 at (5,3,1); D9 in; "
          "the line dark; Z11's return and Y12's re-arm as z11.py leaves them; nothing moving; an update under Z9 fires it")
    print("   ", where(w))
    print("   on:", "; ".join(f"{NAMES[c]} after {spans(w, lambda x, c=c: x.get(c).p.get('powered'))}" for c in REPEATERS),
          "| D9 powered after", spans(w, lambda x: x.get(D9).n == "piston" and power_sources(x, D9)),
          "| Z9 powered after", spans(w, lambda x: x.get(Z9).n == "piston" and power_sources(x, Z9)))
    print("   the S feed's dust (2,8,2) lit after", spans(w, lambda x: x.get((2, 8, 2)).p["power"]), "| W9_7 lit after", spans(w, lambda x: x.get(W9[-1]).p["power"]))
    ref_ev = pv.per_tick(zw, -1, LAST)
    mine_ev = pv.per_tick(w, -1, LAST)
    new = [f"c{k - 1} " + m for k, (a, c) in enumerate(zip(mine_ev, ref_ev)) for m in sorted(set(a) - set(c))]
    gone = [f"c{k - 1} " + m for k, (a, c) in enumerate(zip(mine_ev, ref_ev)) for m in sorted(set(c) - set(a))]
    print("   piston events against z11.py's run: added", "; ".join(new) or "none", "| taken away", "; ".join(gone) or "none")
    rest, _ = pv.differing(cl, w)
    off = [x for x in rest if not any(x.startswith(str(c) + ":") for c in (*pp.PLANE, t.RB_ST, rd.RB_1, rd.RB_2))]
    left = [n for n in r.GROUPS[0][1] if t.at(cl, n) != t.at(w, n)]
    print(f"   cells outside the door plane that still differ from the closed state: {len(off)} (17 after z11.py):", ", ".join(left),
          "(the opening's other four relays and their blocks) and p9_p8's repeater R_9, off while RB_Y is up")

    print("\n== ARM_Z9's two commands, each moved alone (before the tick named)")
    for at, vals in ((0, range(10, 24)), (1, (21, 22, 23, 24, 25, 26, 30, 40, 50, 53, 60))):
        res = {}
        for k in vals:
            pair = list(ARM_AT)
            pair[at] = k
            if pair[0] < pair[1]:
                res[f"c{k}"] = "done" if not run(b, arm=tuple(pair))[2] else "FAILS"
        print(f"   {'taken out' if at == 0 else 'set back'} (here c{ARM_AT[at]}):", res)
    print("   taken out before c22 or earlier: RB9's departure at c16 g or P9's spit at c22 g finds Z9 unpowered (c23: RB9 is home over it); set back "
          "before c23 or later: Z9 is powered at P9's landing (c24 j) and RB9's (c25 j), with RB9 moving or D9's head in (4,4,1), and its push "
          "fails; set back after D9's retract (c52 g), with RB9 at rest on Z9's head cell, its landing does not update Z9 either")

    print("\n== order: against the run above")
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)), ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("from c30 on, the scheduled ticks of each tick in reverse order, priorities ignored", dict(backwards=True)),
                     ("from c10 to c29, the scheduled ticks of each tick in reverse order, priorities ignored (sim only)", dict(extra=reversed_from(10, 29))),
                     *((f"only the blocks that land at c{k} j in reverse order among themselves (sim only)", dict(extra={k: h.landing_reversed}))
                       for k in (22, 24, 25))):
        _, x, badx = run(b, **kw)
        print(f"   {name}:", y.ok(badx) + ";", "piston events of each tick", "the same set" if pv.per_tick(x, -1, LAST) == mine_ev else "DIFFER", "|", where(x))
    mixed = [run(b, extra=h.shuffled(n, first=10), reverse=bool(n & 1), ia_last=bool(n & 2)) for n in range(60)]
    print("   60 runs, in each from c10 on the scheduled ticks of every tick in a random order, priorities ignored; dust's updates reversed in every "
          "second run, I_A's event last in two of every four (the moving blocks in the order their moves began, as measured):",
          "done in all 60;" if not any(x[2] for x in mixed) else f"FAILS in {sum(bool(x[2]) for x in mixed)};", "piston events of each tick",
          "the same set in all" if all(pv.per_tick(x[1], -1, LAST) == mine_ev for x in mixed) else "DIFFER in some")

    print("\n== the five repeaters' delays, each 1 to 4 ticks with the rest as built")
    for c in REPEATERS:
        res = {}
        for k in (1, 2, 3, 4):
            _, x, badk = run(build(swap={c: rd.rep(FACING[c], k)}))
            res[k] = y.ok(badk) + " | " + events(x, 20, 70)
        print(f"   {NAMES[c]}:", "; ".join(f"{k}: {s}" for k, s in res.items()))

    print("\n== controls: one thing changed, the same run")
    for name, (title, bkw, rkw) in CONTROLS.items():
        bc = build(**bkw)
        mv = d.make_world(bc)[1]
        _, x, badc = run(bc, **rkw)
        print(f"   {name}: {title}:", y.ok(badc), "|", where(x), "|", events(x), "| moved during load: " + ", ".join(m.split("@")[0] for m in mv) if mv else "")
    work = [c for c in MINE if c not in GLASSES]
    out = {c: bool(run(build(drop=(c,)))[2]) for c in work}
    print(f"   each of the {len(work)} added blocks that are not glass left out, one at a time:",
          "the re-arm FAILS every time" if all(out.values()) else "done without " + ", ".join(NAMES[c] for c, bad_ in out.items() if not bad_))

    back, differ2, (_, q, bad2) = second(b, w, cl)
    print(f"\n== a second cycle (sim only): after the run the {len(back)} cells that still differ, labels apart, are set back as loaded without updates, "
          "and the input goes on again")
    print("   pending after the first run: scheduled ticks", w.sched or "none", "| block events", list(w.events) or "none")
    print("   the second opening against the first, every cell, labels apart:", f"differs at {differ2}" if differ2 else "the same at every tick")
    print("   the second close and returns, the same stand-ins:", y.ok(bad2) + ";", "piston events of each tick, labels apart,",
          "the same" if wd.bare_events(q) == wd.bare_events(w) else "DIFFER")

    print("\n== what-ifs (sim only)")
    for k in (1, 2, 3, 4):
        bk = build(drop=tuple(LINE), swap={(3, 5, 1): rd.rep("west", k)})
        _, x, badk = run(bk)
        print(f"   in place of the line, one {k}-tick repeater at (3,5,1) on A_9, facing west: it reads R_X (c16 d to c20 d) and points into D9:",
              y.ok(badk), "|", events(x, 10, 40))
    print("   (in the game A_9's extension at c16 pops it: an extended piston's top is not a full face, and a repeater needs one under it)")
    new, ph, pa, src = (4, 3, 2), (4, 3, 3), (4, 3, 4), (4, 3, 5)
    pull = {pa: t.pis("sticky_piston", "north", "P_A", ext=True), ph: B("piston_head", facing="north", sticky=True), src: B("rb", id="SRC_A")}
    with Moved(new):
        ba = build(swap=pull)
        mv = d.make_world(ba)[1]
        acl = d.make_world(ba)[0]
        _, firsta = wd.against(ba, list(wd.frames(b))[1:], {*pull, ARM, new})
        print(f"   ARM_Z9 at {new} in design_c, beside the cell above Z9 as at (5,3,1) (a measured block moved: the lead's call); P_A, a sticky piston at {pa} "
              f"facing north built out, its head at {ph}; P_A's power a redstone block at {src}: moved during load:", mv or "none",
              "| Z9 powered in the closed state by", [x for _, x in power_sources(acl, Z9)],
              "| the opening, the close and the returns without commands, against this build, outside the four cells and (5,3,1):",
              "; ".join(f"{c} from {k}" for c, k in sorted(firsta.items(), key=lambda x: wd.tick_key(x[1]))) or "the same at every tick")
        res = {}
        for off_, on_ in ((10, 21), (13, 21), (16, 21), (20, 21), (21, 22), (13, 23), (13, 30), (13, 47), (20, 60)):
            ex = {off_: lambda w: w.cmd_set(src, AIR), on_: lambda w: w.cmd_set(src, B("rb", id="SRC_A"))}
            _, x, badx = run(ba, arm=None, extra=ex)
            badx = [m for m in badx if not m.startswith("ARM_Z9")]
            ok = not badx and x.get(new).n == "rb" and x.get(ph).n == "piston_head"
            res[f"out before c{off_}, back before c{on_}"] = "done" if ok else "FAILS"
        print("   in place of ARM_Z9's two commands, P_A's power taken out and set back by command, with updates:", res)
    print("   (P_A pulls ARM_Z9 to (4,3,3) and pushes it back; its landing beside (4,3,1) does not update Z9. P_A's drive would be off from before c21 "
          "to after c21, on in the closed and the open state: an inverted pulse, the S feed's line through a sticky piston that moves P_A's redstone "
          "block aside while the line is lit, c12 to c44, for one [INFERRED])")
