"""Y12's re-arm from blocks (door coords): y12.py's re-arm with its two stand-in sources made of blocks. From the
one falling input, with no command after it, Y12 goes in and is armed again, G lands in its closed cell (-3,3,2),
NP12 and the DP tap go dark, A_D never moves, and the opening, the close and the returns are y12.py's at every tick
outside the added cells and B_Y's head cell. 14 blocks on y12.py's 8; Y12 sticky (the lead's call, 2026-11-22), no
other measured block changed. Everything printed is COMPUTED on the simulator; nothing here ran on a server.

Hold    RB_U, a redstone block at (-1,7,2) beside the cell above U_Y, powers U_Y by QC; its moves do not update U_Y.
        It replaces y12.py's stand-in at (-2,8,2). H_U, a sticky piston at (-1,7,3) facing north under A_C, pushes it
        to (-1,7,1) and pulls it back. U_Y has to be lit at W_Y's extension (c58 g) and dark at NP12's relight (c60
        j): a block that a sticky piston moves out and back is gone for 5 gt at least, and no update reaches a cell
        from which a piston would move a block out of U_Y's three silent cells late in c58 g or in c59
        (y12_holds_search.txt). So the hold goes early and U_Y is lit at c58 by S_U.
S_U     A stone at (-2,7,3), the third cell that powers U_Y without an update, under dust D_U (-2,8,3), which D_S, a
        dust on S_W (-3,8,3), lights while S_W is (c52 d to c60 d). D_U is beside A_C: D_Z, a dust at (-2,8,4) on
        glass G_Z (-2,7,4), turns it north-south so that it does not point east into A_C (without D_Z A_C pushes C_F
        out at c52 and back at c60). D_U is three cells from U_Y, D_S three from W_Y: neither is updated by them. S_U
        also powers H_U, beside it, and D_U's changes update H_U.
Run     c12: A_C goes out, its cell is powered by Q_C (-1,8,2) until c44 and H_U, under it, by QC: H_U pushes RB_U
        out and pulls it back at c44 (home at c46 j); no update reaches U_Y from c5 to c58. c52 d: S_W lights D_S, D_U
        and S_U, H_U pushes RB_U out again and U_Y is lit by S_U. c58 g: W_Y's extension finds U_Y lit. c60 d: S_W,
        D_U and S_U go dark, H_U pulls RB_U at c60 g, and U_Y is dark until RB_U lands at c62 j. c60 j: NP12's
        relight finds U_Y dark and it pulls ARM_Z11 at c61 g, as y12.py's stand-in had it (out before c60, back
        before c62). ARM_Z11's landing at c63 j finds U_Y lit again: it pushes at c64 g and stays out on RB_U.
B_Y     R_B, a 3-tick repeater at (-4,6,4) facing north on glass G_B, reads Y_G (c58 d to c66 d) and powers stone S_B
        (-4,6,5) from c64 d to c72 d. D_B, a dust under S_B at (-4,5,5) on stone S_B2 (-4,4,5), steps down north to
        D_Y (-4,4,4) on glass G_Y (-4,3,4); D_Y points north into (-4,4,3), the cell above B_Y, so B_Y is powered by
        QC and updated by D_Y's changes. It goes out at c64 g into (-4,3,2), empty since G left at c61 g, its head is
        there when ARM_Z11 lands on Y12 at c66 j, and it goes in at c72 g. D_Y is two cells from A_D: it updates A_D
        at c64 d, when A_D's push is already queued (at G's landing, c63 j, behind W_Y's), and at c72 d, when the tap
        is off.
Why     Y_G alone is one tick short: ARM_Z11 lands at c66 j, after B_Y's retract at c66 g (the what-if). A repeater
        reads Y_G only from (-4,6,4), facing north, so its output is at z 5. R_B at 1 tick powers B_Y at G's landing
        in (-4,3,2) at c60 j, whose push then stops only because M_K's base lands after G; at 2 ticks D_Y updates A_D
        in c62 d beside the tap's turning on; at 3 ticks neither (the margins).
Room    The hold takes z 4 (D_Z, G_Z), B_Y's source z 4 (R_B, G_B, D_Y, G_Y) and z 5 (S_B, D_B, S_B2): the box grows
        from 14 x 15 x 12 = 2520 to 14 x 15 x 14 = 2940.
Cost    RB_U at (-1,7,1) is one step from (-2,7,1): from c14 j to c44 g and c54 j to c60 g it would power a piston at
        (-2,6,1), kept free for Z11's down-pusher, by QC.

Not controls: the glass under the dust and the repeater (G_Z, G_B, G_Y; the simulator has no rule for support).
Run from the repo root (sim; about a minute):
python -m scripts.door2.close_layout.y12_holds > scripts/door2/close_layout/y12_holds.txt"""
import copy, random
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, p10_v as pv, returns as r, rbt_drives as rd, dp_off as o, west_drives as wd, y12 as y
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World

D_S, D_U, S_U, D_Z, G_Z = (-3, 8, 3), (-2, 8, 3), (-2, 7, 3), (-2, 8, 4), (-2, 7, 4)
H_U, RB_U, PARK_U = (-1, 7, 3), (-1, 7, 2), (-1, 7, 1)            # PARK_U: where H_U puts RB_U
R_B, G_B, S_B, D_B, S_B2, D_Y, G_Y = (-4, 6, 4), (-4, 5, 4), (-4, 6, 5), (-4, 5, 5), (-4, 4, 5), (-4, 4, 4), (-4, 3, 4)
LAST = y.LAST
DOT = B("redstone_wire", power=0, dot=True)
HOLD_U = {D_S: t.DUST, D_U: t.DUST, S_U: t.STONE, D_Z: t.DUST, G_Z: t.GLASS, H_U: t.pis("sticky_piston", "north", "H_U"),
          RB_U: B("rb", id="RB_U")}
SOURCE_B = {R_B: rd.rep("north", 3), G_B: t.GLASS, S_B: t.STONE, D_B: t.DUST, S_B2: t.STONE, D_Y: t.DUST, G_Y: t.GLASS}
MINE = {**HOLD_U, **SOURCE_B}
GLASSES = (G_Z, G_B, G_Y)
NAMES = {D_S: "D_S", D_U: "D_U", S_U: "S_U", D_Z: "D_Z", G_Z: "G_Z", H_U: "H_U", RB_U: "RB_U", R_B: "R_B", G_B: "G_B", S_B: "S_B",
         D_B: "D_B", S_B2: "S_B2", D_Y: "D_Y", G_Y: "G_Y", PARK_U: "RB_U's park"}
MOVED = (PARK_U,)
ADDED = (*y.ADDED, *MINE, *MOVED)                                    # left out when a run is set beside y12.py's
STAND_INS = (y.HOLD, y.SRC_B)
wd.SHOW = (*wd.SHOW, f"repeater {R_B} ", f"land rb@{PARK_U}", f"land rb@{RB_U}")


def build(drop=(), swap=None, y12=y.STICKY):
    """y12.py's build without its stand-in hold, with the 14 blocks; `drop` leaves cells out (y12.py's too: U_Y
    with its head), `swap` replaces some."""
    theirs = (*y.MINE, y.U_HEAD)
    b = y.build(drop=(y.HOLD, *(c for c in drop if c in theirs)), swap={c: st for c, st in (swap or {}).items() if c in theirs} or None, y12=y12)
    for c, st in {**MINE, **{c: st for c, st in (swap or {}).items() if c not in theirs}}.items():
        if c not in drop:
            assert c in (swap or {}) or c not in b.b, c
            b.b[c] = st
            b.role[c] = "y12_holds"
    return b


def verdict(w, cl):
    """y12.py's verdict (Y12's corner, NP12 and the tap dark, A_D unpowered, west_drives' verdict without G's line),
    the 14 blocks and RB_U's park cell as loaded, and U_Y, H_U and B_Y powered as in the closed state. Empty when
    Y12 is re-armed."""
    bad = y.verdict(w, cl)
    bad += [f"{NAMES[c]} {'moving' if c in w.be else w.get(c)}" for c in (*MINE, *MOVED) if c in w.be or pp.bare(w.get(c)) != pp.bare(cl.get(c))]
    bad += [f"{n} powered by {[x for _, x in power_sources(w, c)]}" for n, c in (("U_Y", y.U_Y), ("H_U", H_U), ("B_Y", y.B_Y))
            if w.get(c).n == cl.get(c).n in ("piston", "sticky_piston") and power_sources(w, c) != power_sources(cl, c)]
    return bad


def run(b, opened=None, extra=None, last=LAST, **kw):
    """b opened from the input and taken through the close and the returns, no command: (closed state, noted
    world, verdict); `extra` {tick: function of the world} acts before that tick (sim only)."""
    cl = d.make_world(b)[0]
    w = wd.noted(t.opened(b)[0] if opened is None else opened, pp.idle(last), before=extra, **kw)
    return cl, w, verdict(w, cl)


def mine_line(x):
    return y.mine_line(x) or any(f" {n}@" in x for n in ("H_U",)) or f"repeater {R_B} " in x or \
        any(f"land rb@{c}" in x for c in (PARK_U, RB_U))


def said(w, first=50, last=LAST):
    return [x for x in pv.told(w) if first <= pv.tick_of(x) <= last and mine_line(x)]


def where(w):
    return y.where(w) + f", RB_U {t.at(w, 'RB_U')[0]}, H_U " + ("out" if t.at(w, "H_U")[2] else "in")


def runs(ks):
    """tick numbers of the close as first..last runs."""
    return rd.spans([f"c{k}" for k in ks])


def spans(w, cells):
    """after which ticks of the close each cell is lit (dust) or on (repeater) or strongly powered (stone)."""
    out = {}
    for k, (bl, _) in enumerate(w.frames):
        x = World()
        x.b = bl
        for c in cells:
            st = bl.get(c, AIR)
            on = st.p.get("power", 0) > 0 if st.n == "redstone_wire" else st.p.get("powered") if st.n == "repeater" else x.direct_signal_to(c) > 0
            if on:
                out.setdefault(c, []).append(k - 1)
    return {c: runs(ks) for c, ks in out.items()}


def second(b, w, cl):
    """the world after the run with every other cell set back as loaded, without updates (a stand-in for the
    returns not designed), opened again: the cells set back, the ticks at which the second opening differs from
    the first, labels apart, and the second close and returns."""
    x = copy.deepcopy(w)
    x.__class__ = World
    back = [c for c in set(cl.b) | set(x.b) if pp.bare(cl.get(c)) != pp.bare(x.get(c))]
    for c in back:
        x.cmd_set_silent(c, cl.get(c))
    a, _ = d.make_world(b)
    for z in (a, x):
        z.run(4)
        z.cmd_set(f.DRIVER, t.RB)
    differ = []
    for k in range(t.OPEN_TICKS):
        a.tick()
        x.tick()
        differ += [f"t{k - 1}"] * (set(a.be) != set(x.be) or {c: pp.bare(st) for c, st in a.b.items()} != {c: pp.bare(st) for c, st in x.b.items()})
    return back, differ, run(b, opened=x)


def frame_diff(fa, fb, skip):
    """for two lists of (blocks, moving cells) from c-1: each cell outside `skip` that differs, with the ticks
    after which it does."""
    out = {}
    for k, ((ba, ma), (bb, mb)) in enumerate(zip(fa, fb)):
        for c in (set(ba) | set(bb) | ma | mb) - set(skip):
            if ba.get(c) != bb.get(c) or (c in ma) != (c in mb):
                out.setdefault(c, []).append(k - 1)
    return out


def drift(x, w):
    """the cells outside y12.py's and these added ones that differ between two noted runs at any tick, with the ticks
    after which they do."""
    return frame_diff(x.frames, w.frames, ADDED)


def judged(bad, dr):
    """a run's verdict and its drift from the run as built, as text."""
    if bad:
        return y.ok(bad)
    return "done at the end, but cells outside the added ones differ from the run as built: " + "; ".join(
        f"{c} after {runs(ks)}" for c, ks in sorted(dr.items())) if dr else "done"


def landing_reversed(w):
    """before a tick: the moving blocks that land in its phase j in reverse order among themselves (sim only)."""
    idx = [i for i, be in enumerate(w.tickers) if not be.removed and be.progress >= 1.0]
    for i, be in zip(idx, [w.tickers[i] for i in reversed(idx)]):
        w.tickers[i] = be


def shuffled(seed, first=30):
    """{tick: function}: before each tick from c`first` on, the scheduled ticks due in it in a random order,
    priorities ignored (sim only)."""
    rng = random.Random(seed)

    def fn(w):
        due = sorted((x for x in w.sched if x[0] <= w.time + 1), key=lambda x: (x[1], x[2]))
        mixed = rng.sample(due, len(due))
        w.sched = [x for x in w.sched if x[0] > w.time + 1] + [(x[0], 0, sub, x[3], x[4]) for x, sub in zip(mixed, sorted(q[2] for q in due))]
    return {k: fn for k in range(first, LAST + 1)}


# name: (title, build keywords)
CONTROLS = {
    "no RB_U": ("nothing holds U_Y: built out, it retracts in the load and pulls ARM_Z11 up", dict(drop=(RB_U,))),
    "no H_U": ("RB_U stays home: NP12's relight finds U_Y powered, U_Y and Y12 stay out, W_Y lifts RB_D alone and A_D goes out at c67",
               dict(drop=(H_U,))),
    "H_U not sticky": ("it leaves RB_U at (-1,7,1) at c44: U_Y goes in at c61 as built but stays in, ARM_Z11 stays up and powers Y12, which "
                       "goes out again at c64", dict(swap={H_U: t.pis("piston", "north", "H_U")})),
    "no S_U": ("nothing powers H_U at c52 (nor U_Y at c58): RB_U stays home and it is as without H_U", dict(drop=(S_U,))),
    "no D_U": ("the same: nothing powers S_U", dict(drop=(D_U,))),
    "no D_S": ("the same: nothing lights D_U", dict(drop=(D_S,))),
    "no D_Z": ("D_U points east and west, into A_C: A_C pushes C_F out at c52 and pulls it back at c60", dict(drop=(D_Z,))),
    "no R_B": ("nothing powers B_Y: ARM_Z11's landing at c66 j fires Y12 again", dict(drop=(R_B,))),
    "no S_B": ("the same: R_B points into air", dict(drop=(S_B,))),
    "no D_B": ("the same", dict(drop=(D_B,))),
    "no S_B2": ("the same: D_Y does not read D_B down the step without a conductor under D_B", dict(drop=(S_B2,))),
    "no D_Y": ("the same", dict(drop=(D_Y,))),
}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    r.worlds()
    yb = y.build()
    ycl, yw, ybad = y.run(yb)
    assert not ybad
    rb = wd.build()
    ref = list(wd.frames(rb))[1:]
    rcl, rw, rbad = wd.run(rb, ticks=pp.idle(LAST))
    assert not rbad
    b = build()
    kinds = [st.n for st in MINE.values()]
    print(f"added: {len(MINE)} blocks on y12.py's 8 ({kinds.count('sticky_piston')} sticky piston, {kinds.count('rb')} redstone block, "
          f"{kinds.count('repeater')} repeater, {kinds.count('redstone_wire')} dust, {kinds.count('stone')} stone, {kinds.count('glass')} glass under dust and "
          "a repeater); y12.py's stand-in hold at (-2,8,2) taken out; Y12 a sticky piston (the lead's call), no other measured block changed; "
          "no stand-in, no command after the input")
    taken = set(d.full_blocks(yb)) | set(ycl.b) | set(v.cumulative_cells(yb)[0])
    for blocks, be in (*ref, *yw.frames):
        taken |= set(blocks) | be
    print("added cells, and RB_U's park, that y12.py's build fills at any tick (its stand-ins included) or on the door plane or in the hallway:",
          ", ".join(f"{NAMES[c]} {c}" for c in (*MINE, *MOVED) if c in taken or r.plane_or_hall(c)) or "none")
    moved, first = wd.against(b, ref, set(ADDED))
    print("moved during load:", moved or "none", "| the opening and the close to c30 against west_drives.py's build, outside y12.py's and these added cells:",
          f"differ at {wd.differs(first, 30)}" if wd.differs(first, 30) else "the same at every tick")
    op, _ = t.opened(b)
    print("open state:", ", ".join(f"{n} " + ("out" if t.at(op, n)[2] else "in") + f" powered by {[x for _, x in power_sources(op, c)] or 'nothing'}"
                                   for n, c in (("U_Y", y.U_Y), ("W_Y", y.W_Y), ("B_Y", y.B_Y), ("H_U", H_U))), "| RB_U", t.at(op, "RB_U")[0])
    cl, w, bad = run(b)
    late = frame_diff(w.frames, rw.frames, ADDED)
    names = {**wd.NAMES, y.ARM: "ARM_Z11's cell", y.RB_D: "RB_D's cell", y.B_HEAD: "(-4,3,2)", wd.L: "L", o.TAP: "the tap's dust", o.R_D: "the tap's repeater",
             **{c: f"NP12's dust {c}" for c in y.NP12}}
    by_tick = {}
    for c, ks in sorted(late.items(), key=lambda x: (x[1][0], x[0])):
        by_tick.setdefault(ks[0], []).append(names.get(c, str(c)))
    print(f"the close and the returns, c-1 to c{LAST}, against west_drives.py's run, cells outside y12.py's and these added ones that differ:",
          "; ".join(f"from c{k}: " + ", ".join(ns) for k, ns in by_tick.items()) or "none", "| every other cell is the same at every tick")
    against_y = frame_diff(w.frames, yw.frames, ADDED + STAND_INS)
    print(f"   against y12.py's run with its four stand-in commands, c-1 to c{LAST}, cells outside the added and the stand-in cells that differ:",
          "; ".join(f"{names.get(c, c)} after {runs(ks)}" for c, ks in sorted(against_y.items())) or "none",
          "(B_Y's head: out at c64 and in at c72, two ticks after the stand-in source's c62 and c70) | every other cell is the same at every tick")
    cells = set(v.cumulative_cells(b)[0])
    for blocks, _ in w.frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print("box, opening + close + returns:", t.s.box(cells))

    print(f"\n== the close and the returns from the input, no command: c50 to c{LAST}")
    mine_ev, y_ev = pv.per_tick(w, -1, LAST), pv.per_tick(yw, -1, LAST)
    early = [f"c{n}: " + ", ".join(m.split(" ", 1)[1].split(":")[0] for m in set(mine_ev[n + 1]) - set(y_ev[n + 1])) for n in range(-1, 50) if mine_ev[n + 1] != y_ev[n + 1]]
    assert all(set(c) <= set(a_) for a_, c in zip(mine_ev[:51], y_ev[:51]))
    print("   c-1 to c49: the piston events of y12.py's run, tick by tick, and", "; ".join(early) or "no other", "| from c50:")
    print("\n".join("   " + x for x in said(w)))
    print("   ->", "FAILS: " + "; ".join(bad) if bad else "done: Y12 in, powered by ARM_Z11 and RB_D and not updated since; G at (-3,3,2); NP12 dark, the tap off; "
          "RB_D and ARM_Z11 where they were; A_D in and unpowered, it never moved; U_Y out on RB_U, W_Y, B_Y and H_U in; RB12 on K, K in, powered by L "
          "and not updated; the 14 blocks as loaded, the dust dark, R_B off; the rest as west_drives.py leaves it; nothing moving")
    print("   ", where(w))
    print("   H_U's events from c-1 to c49:", "; ".join(x.split(":")[0] for x in pv.told(w) if pv.tick_of(x) < 50 and "H_U@" in x) or "none",
          "(A_C's cell is powered by Q_C from c12 to c44; no update reaches U_Y between c4 and c58)")
    lit = spans(w, (D_S, D_U, S_U, R_B, D_Y))
    print("   lit or powered:", "; ".join(f"{NAMES[c]} after {s}" for c, s in lit.items()),
          "| RB_U away from its cell after", runs([k - 1 for k, (bl, be) in enumerate(w.frames) if RB_U in be or bl.get(RB_U, AIR).n != "rb"]))
    pw = {}
    for k, (bl, _) in enumerate(w.frames):
        x = World()
        x.b = bl
        for n, c in (("U_Y", y.U_Y), ("B_Y", y.B_Y), ("H_U", H_U)):
            if k > 6 and power_sources(x, c):
                pw.setdefault(n, []).append(k - 1)
    print("   powered, after c5:", "; ".join(f"{n} after {runs(ks)}" for n, ks in pw.items()),
          "| A_D's push at c64:", "; ".join(x.split(" ", 1)[1] for x in pv.told(w) if pv.tick_of(x) == 64 and "piston@" + str(y.A_D) in x) or "not queued")
    rest, dust = pv.differing(cl, w)
    off = [x for x in rest if not any(x.startswith(str(c) + ":") for c in (*pp.PLANE, t.RB_ST, rd.RB_1, rd.RB_2))]
    left = [n for n in r.GROUPS[0][1] if t.at(cl, n) != t.at(w, n)]
    print(f"   cells outside the door plane that still differ from the closed state: {len(off)} (20 after y12.py):", ", ".join(left),
          "(the opening's other six relays and their blocks) and p9_p8's repeater R_9, off while RB_Y is up | NP12's dust and the tap's that are lit:",
          [c for c in (*y.NP12, o.TAP) if w.get(c).p["power"]] or "none")

    print("\n== order: against the run above")
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)), ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("from c30 on, the scheduled ticks of each tick in reverse order, priorities ignored", dict(backwards=True)),
                     ("at c64, A_D's push ahead of W_Y's (sim only; the game queues W_Y's first, at RB_D's landing)", dict(extra={64: y.a_d_first})),
                     ("the blocks that land at c60 j in reverse order (sim only)", dict(extra={60: y.all_reversed})),
                     ("the blocks that land at c63 j in reverse order: G ahead of RB_D, so A_D's push is queued ahead of W_Y's (sim only)", dict(extra={63: y.all_reversed})),
                     ("the blocks that land at c66 j in reverse order (sim only)", dict(extra={66: y.all_reversed})),
                     *((f"only the blocks that land at c{k} j in reverse order among themselves (sim only)", dict(extra={k: landing_reversed}))
                       for k in (14, 46, 54, 60, 62, 64, 66, 72))):
        _, x, badx = run(b, **kw)
        print(f"   {name}:", y.ok(badx) + ";", "piston events of each tick", "the same set" if pv.per_tick(x, -1, LAST) == mine_ev else "DIFFER", "|", where(x))
    mixed = [run(b, extra=shuffled(n), reverse=bool(n & 1), ia_last=bool(n & 2)) for n in range(60)]
    print("   60 runs, in each from c30 on the scheduled ticks of every tick in a random order, priorities ignored; dust's updates reversed in every "
          "second run, I_A's event last in two of every four (the moving blocks in the order their moves began, as measured):",
          "done in all 60;" if not any(x[2] for x in mixed) else f"FAILS in {sum(bool(x[2]) for x in mixed)};", "piston events of each tick",
          "the same set in all" if all(pv.per_tick(x[1], -1, LAST) == mine_ev for x in mixed) else "DIFFER in some")

    print(f"\n== R_B's delay, 1 to 4 ticks with the rest as built (the only delay added; run to c{LAST + 6}, R_B on from c58 d + 2k to c66 d + 2k)")
    for k in (1, 2, 3, 4):
        bk = build(swap={R_B: rd.rep("north", k)})
        _, x, badk = run(bk, last=LAST + 6)
        ev = [m.split(" ", 1)[1].split(":")[0] for m in said(x, 58, LAST + 6) if "B_Y@" in m]
        ad = [m for m in pv.told(x) if pv.tick_of(m) >= 50 and (f"piston@{y.A_D}" in m or "A_D@" in m)]
        var = {n: y.ok(run(bk, last=LAST + 6, **kw)[2]) for n, kw in (("the blocks landing at c60 j reversed", dict(extra={60: landing_reversed})),
                                                                       ("the scheduled ticks reversed from c30", dict(backwards=True)))}
        print(f"   {k}:", y.ok(badk), "| B_Y:", "; ".join(f"c{pv.tick_of(m)}" + m.split(" ", 1)[1].split(":")[0].replace("level ", " level ") for m in said(x, 58, LAST + 6) if "B_Y@" in m),
              "| A_D's events from c50:", "; ".join(m.split(" ", 1)[1] for m in ad) or "none", "|", "; ".join(f"{n}: {v_}" for n, v_ in var.items()))

    print("\n== controls: one thing changed, the same run, no command")
    for name, (title, bkw) in CONTROLS.items():
        bc = build(**bkw)
        mv = d.make_world(bc)[1]
        _, x, badc = run(bc)
        print(f"   {name}: {title}:", judged(badc, drift(x, w)), "|", where(x), "| moved during load: " + ", ".join(m.split("@")[0] for m in mv) if mv else "")
    work = [c for c in MINE if c not in GLASSES]
    left = {}
    for c in work:
        _, x, badc = run(build(drop=(c,)))
        left[c] = bool(badc) or bool(drift(x, w))
    print(f"   each of the {len(work)} added blocks that are not glass left out, one at a time:",
          "the re-arm FAILS or the close differs outside the added cells, every time" if all(left.values()) else
          "done, the same, without " + ", ".join(NAMES[c] for c, bad_ in left.items() if not bad_))
    old = {c: bool(run(build(drop=(c,)))[2]) for c in y.MINE if c != y.U_HEAD}
    print(f"   each of y12.py's {len(old)} blocks left out, one at a time (U_Y with its head):",
          "the re-arm FAILS every time" if all(old.values()) else "done without " + ", ".join(y.NAMES[c] for c, bad_ in old.items() if not bad_))
    print("   Y12 as built, a plain piston:", y.ok(run(build(y12=t.pis("piston", "west", "Y12")))[2]))

    back, differ2, (_, z, bad2) = second(b, w, cl)
    print(f"\n== a second cycle (sim only): after the run the {len(back)} cells that still differ, labels apart, are set back as loaded without updates, "
          "and the input goes on again")
    print("   pending after the first run: scheduled ticks", w.sched or "none", "| block events", list(w.events) or "none")
    print("   the second opening against the first, every cell, labels apart:", f"differs at {differ2}" if differ2 else "the same at every tick")
    print("   the second close and returns:", y.ok(bad2) + ";", "piston events of each tick, labels apart,",
          "the same" if wd.bare_events(z) == wd.bare_events(w) else "DIFFER")

    print("\n== what-ifs (sim only)")
    yd = build(drop=tuple(SOURCE_B), swap={(-4, 5, 3): DOT, (-4, 4, 3): t.GLASS})
    _, x, badd = run(yd)
    print("   B_Y powered by Y_G alone, through a dot at (-4,5,3) under it (on glass at (-4,4,3)) in place of the 7 blocks:", y.ok(badd), "|",
          "; ".join(m.split(":")[0] for m in said(x, 61, LAST) if "B_Y@" in m or "Y12@" in m or "land rb@(-2, 4, 2)" in m))
