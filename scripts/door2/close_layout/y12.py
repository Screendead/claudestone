"""Y12's re-arm, first pass (door coords): after the close, Y12 goes in and is armed as the load leaves it, G is in
its closed cell (-3,3,2), NP12 is dark, RB_D and ARM_Z11 are where they were and A_D never moves. Not done from
blocks: two sources are stood in for by commands after the one input, so this is a mechanism with its two open
drives named, not yet a design. Everything printed is COMPUTED on the simulator; nothing here ran on a server.

Sticky  Y12 is a sticky piston here. It is a measured block of design_c, a plain piston there. A plain Y12 leaves G
        at (-4,3,2): a block goes east out of that cell only by a piston in (-5,3,2), where P_W's head stands, or by
        Y12's pull. The opening, the close and the returns are the same at every tick with Y12 sticky (west_drives.txt).
Holds   Y12 is held by ARM_Z11, on it, and by RB_D beside ARM_Z11 (QC). Every cell one step from ARM_Z11 powers Y12
        too, so no one step takes it away; a redstone block powers nothing while it moves. Both blocks are lifted
        one cell and put back, and Y12 is updated while both move.
When    RB_D has two movers, A_D and a piston above it, and the DP tap powers both while NP12 is lit (A_D through
        its stone, the piston above RB_D by standing beside that stone). NP12 lights again when RB12 lands on K at
        c60 j and the tap's repeater turns on at c62 d: the lift is at c61 g, the one tick between G's landing in
        (-4,3,2) and the tap. A_D is not used: fired with the tap on it stays out, RB_D parks in DP's source cell
        and powers M_K by QC, and G's leaving updates M_K (the what-if near the end).
W_Y     A sticky piston at (-3,6,2) facing down, above RB_D, in at rest. S_W, a stone at (-3,7,3) on the tap's
        stone and beside the cell above W_Y, powers it without an update from c52 d to c60 d: R_F, a 1-tick
        repeater at (-4,7,3) on Y_G, reads S_F, a stone at (-5,7,3) on R_G, which D_X, a dust at (-6,7,3) on Y_X,
        powers while Y_X is (c50 to c58). P_G's extension beside W_Y at c58 g is its update: it goes out, its head
        lands on RB_D at c60 j and updates it, by then unpowered: at c61 g it retracts and pulls RB_D up. RB_D
        lands in front of it at c63 j with the tap on: W_Y pushes it down at c64 g. G's landing at c63 j has put
        NP12 out, the tap's repeater turns off at c65 d and updates W_Y, a neighbour of its stone, one tick into
        the push: W_Y leaves RB_D and retracts (a sticky piston released within 2 gt of its push). In the open
        state the tap holds W_Y out, its head on RB_D; it retracts at c2 g, with A_D's head under it, and pulls
        nothing.
U_Y     A sticky piston at (-2,6,2) facing down, above ARM_Z11, built out, its head on ARM_Z11. STAND-IN: it is
        held by a redstone block at (-2,8,2), two above it (QC, no update), which a command takes out before c60
        and another sets back before c63, both without updates. NP12's relight at c60 j is its update (the tap's
        dust and NP12's (0,6,2) are two cells from it): at c61 g it retracts and pulls ARM_Z11 up. ARM_Z11 lands
        in front of it at c63 j: it pushes it down at c64 g and stays out, as loaded.
Y12     W_Y's and U_Y's events at c61 g each update Y12; at the second both blocks are moving and Y12 retracts and
        pulls G, which landed at c60 j. G lands at (-3,3,2) at c63 j and cuts the step: NP12 is dark.
B_Y     A piston at (-4,3,3) facing north, south of the cell G leaves: the blocker the load has in (-4,3,2).
        STAND-IN: a redstone block set beside it at (-5,3,3) before c62 and taken out before c70, with updates. Its
        head is in (-4,3,2) from c62 g. G's landing at c63 j and ARM_Z11's at c66 j each update Y12, powered, and
        its push fails on the head; nothing updates Y12 after B_Y retracts, so it is left in, powered by ARM_Z11
        and RB_D and not updated. B_Y's head also keeps K, powered by L, from pushing RB12 up.
A_D     G's landing puts H out under A_D with the tap still on: A_D's push is queued at c63 j behind W_Y's, queued
        when RB_D landed, and at c64 g it fails on RB_D moving into the cell in front of it. With the two events
        in the other order A_D's head takes that cell, RB_D stays up and holds A_D out (the what-if under order):
        it rests on moving blocks ticking in the order their moves began, measured by close_rbt_drives_probe.
Left    U_Y's hold from blocks: a source that goes dark without updating U_Y between c58 g and c61 g and is back
        by c65 d. The cells that power U_Y without an update are (-1,7,2), (-2,7,3) and (-2,8,2); a redstone block
        there has no second powering cell one step away except (-2,7,2), whose leaving updates U_Y, and each cell
        from which a piston or a repeater would reach them is taken ((0,7,2) and (-2,9,2), glass under R_C and
        under the west line; (-2,6,3), the tap's repeater), outside the box (z 4), or powers a measured piston
        ((-4,8,2) is two above P_G; (-1,7,0) two above P10). (-2,6,1), (-2,7,1) and (-2,7,2) are kept free for the
        down-pusher Z11's return needs over RB11's open cell. B_Y's source from blocks: on at c62 d (2 ticks
        after R_G) and off no earlier than c67 d, with updates, from a cell that does not update A_D between c62
        and c64 (the cell above B_Y is beside A_D).

Run from the repo root (sim; about 4 minutes):
python -m scripts.door2.close_layout.y12 > scripts/door2/close_layout/y12.txt"""
import copy
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, p10_v as pv, returns as r, rbt_drives as rd, dp_off as o, west_drives as wd
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World

Y12, G_HOME, ARM, RB_D, A_D, H = wd.Y12, wd.G_HOME, wd.ARM_Z11, o.RB_D, o.A_D, (-3, 3, 3)
U_Y, U_HEAD, HOLD, ARM_UP = (-2, 6, 2), (-2, 5, 2), (-2, 8, 2), (-2, 5, 2)
W_Y, W_HEAD = (-3, 6, 2), (-3, 5, 2)                                # W_HEAD is also where RB_D stands when lifted
B_Y, B_HEAD, SRC_B = (-4, 3, 3), wd.UP, (-5, 3, 3)
D_X, S_F, R_F, S_W = (-6, 7, 3), (-5, 7, 3), (-4, 7, 3), (-3, 7, 3)
LAST = 74
STICKY = t.pis("sticky_piston", "west", "Y12")
HOLD_BLOCK = B("rb", id="HOLD_U")
PISTONS = {U_Y: t.pis("sticky_piston", "down", "U_Y", True), U_HEAD: B("piston_head", facing="down", sticky=True),
           W_Y: t.pis("sticky_piston", "down", "W_Y"), B_Y: t.pis("piston", "north", "B_Y")}
FEED = {D_X: t.DUST, S_F: t.STONE, R_F: rd.rep("west", 1), S_W: t.STONE}
MINE = {**PISTONS, **FEED}
NAMES = {U_Y: "U_Y", W_Y: "W_Y", B_Y: "B_Y", D_X: "D_X", S_F: "S_F", R_F: "R_F", S_W: "S_W", HOLD: "U_Y's stand-in hold", Y12: "Y12"}
ADDED = (*MINE, HOLD, SRC_B, W_HEAD, Y12, G_HOME)                    # cells left out when a run is set beside west_drives.py's
CORNER = (Y12, G_HOME, B_HEAD, ARM, ARM_UP, RB_D, W_HEAD, A_D, o.LIT, U_Y, W_Y, B_Y, HOLD, SRC_B, *FEED)
HOLD_AT, SRC_AT = (60, 63), (62, 70)                                 # the stand-in commands: before these ticks
NP12 = [c for c, ro in wd.build().role.items() if ro == "NP12" and c != wd.L]      # NP12's dust behind the gate
wd.SHOW = (*wd.SHOW, f"repeater {R_F} ", *(f"land {n}@{c}" for n, c in (("rb", ARM_UP), ("rb", ARM), ("rb", W_HEAD), ("stone", G_HOME))))


def build(drop=(), swap=None, y12=STICKY):
    """west_drives.py's build with Y12 sticky, the eight blocks and U_Y's stand-in hold; `drop` leaves cells out
    (U_Y's head with U_Y), `swap` replaces some."""
    b = wd.build()
    drop = (*drop, U_HEAD) if U_Y in drop else drop
    for c, st in {**MINE, HOLD: HOLD_BLOCK, **(swap or {})}.items():
        if c not in drop:
            assert c in (swap or {}) or c not in b.b, c
            b.b[c] = st
            b.role[c] = "y12"
    b.b[Y12] = y12
    return b


def commands(hold=HOLD_AT, src=SRC_AT, last=LAST):
    """(ticks, before) for wd.noted: the input off, then the stand-in commands: U_Y's hold out before c`hold[0]`
    and back before c`hold[1]` without updates, B_Y's source in before c`src[0]` and out before c`src[1]` with
    updates; None leaves a pair out."""
    ticks, before = pp.idle(last), {}
    if hold:
        before[hold[0]] = lambda w: w.cmd_set_silent(HOLD, AIR)
        before[hold[1]] = lambda w: w.cmd_set_silent(HOLD, HOLD_BLOCK)
    if src:
        ticks[src[0] + 1] = ticks[src[0] + 1] + [(SRC_B, t.RB)]
        ticks[src[1] + 1] = ticks[src[1] + 1] + [(SRC_B, AIR)]
    return ticks, before


def verdict(w, cl):
    """what keeps Y12's corner from the loaded closed state `cl`: its cells, cell for cell and labels apart; Y12's
    power from the closed state's, RB11 apart (Z11's block, still up); NP12's dust and the tap from dark; and
    west_drives' verdict without its line on G. Empty when Y12 is re-armed."""
    bad = [f"{c} {'moving' if c in w.be else w.get(c)}" for c in CORNER if c in w.be or pp.bare(w.get(c)) != pp.bare(cl.get(c))]
    if pp.bare(w.get(Y12)) == pp.bare(cl.get(Y12)):
        src = [{x for _, x in power_sources(x_, Y12)} - {(-2, 4, 1)} for x_ in (w, cl)]
        bad += [f"Y12 powered by {sorted(src[0])}"] * (src[0] != src[1])
    bad += [f"A_D powered by {[x for _, x in power_sources(w, A_D)]}"] * bool(power_sources(w, A_D))
    lit = [c for c in (*NP12, o.TAP) if w.get(c).p["power"]]
    bad += [f"lit: {lit}"] * bool(lit) + ["the tap's repeater on"] * w.get(o.R_D).p["powered"]
    return bad + [x for x in wd.verdict(w, cl) if not x.startswith("G (")]


def run(b, hold=HOLD_AT, src=SRC_AT, opened=None, extra=None, **kw):
    """b opened from the input and taken through the close and the returns with the stand-in commands: (closed
    state, noted world, verdict); `extra` {tick: function of the world} acts before that tick as well."""
    cl = d.make_world(b)[0]
    ticks, before = commands(hold, src)
    for k, fn in (extra or {}).items():
        before[k] = (lambda g, h: lambda w: (g(w), h(w)))(before[k], fn) if k in before else fn
    w = wd.noted(t.opened(b)[0] if opened is None else opened, ticks, before=before, **kw)
    return cl, w, verdict(w, cl)


def mine_line(x):
    return any(f" {n}@" in x for n in ("U_Y", "W_Y", "B_Y", "Y12", "A_D", "P_G", "M_K", "K")) or f"repeater {R_F} " in x or \
        any(f"@{c}" in x and " land " in x for c in (ARM_UP, ARM, W_HEAD, G_HOME, wd.K_UP, B_HEAD))


def said(w, first=50, last=LAST):
    return [x for x in pv.told(w) if first <= pv.tick_of(x) <= last and mine_line(x)]


def where(w):
    return ", ".join(f"{n} {t.at(w, n)[0]}" + {True: " out", False: " in", None: ""}[t.at(w, n)[2]]
                     for n in ("Y12", "G", "RB_D", "A_D", "U_Y", "W_Y", "B_Y", "RB12", "K")) + f", ARM_Z11's cell {w.get(ARM).n}, H {w.get(H).p['power']}"


def ok(bad):
    return "FAILS: " + "; ".join(bad[:3]) + (" ..." if len(bad) > 3 else "") if bad else "done"


def a_d_first(w):
    """before c64: A_D's queued push is put ahead of W_Y's (sim only)."""
    for key in [k for k in w.events if k[0] == A_D]:
        w.events.move_to_end(key, last=False)


def all_reversed(w):
    """before a tick: every moving block in reverse order; set once before the tick they land in (sim only)."""
    w.tickers.reverse()


def second(b, w, cl):
    """the world after the run with every other cell set back as loaded, without updates (a stand-in for the
    returns not designed), opened again: the cells set back, the ticks at which the second opening differs from
    the first, labels apart, and the second close and returns with the same stand-in commands."""
    x = copy.deepcopy(w)
    x.__class__ = World
    back = [c for c in set(cl.b) | set(x.b) if pp.bare(cl.get(c)) != pp.bare(x.get(c))]
    for c in back:
        x.cmd_set_silent(c, cl.get(c))
    a, _ = d.make_world(b)
    for y in (a, x):
        y.run(4)
        y.cmd_set(f.DRIVER, t.RB)
    differ = []
    for k in range(t.OPEN_TICKS):
        a.tick()
        x.tick()
        differ += [f"t{k - 1}"] * (set(a.be) != set(x.be) or {c: pp.bare(st) for c, st in a.b.items()} != {c: pp.bare(st) for c, st in x.b.items()})
    return back, differ, run(b, opened=x)


# name: (title, build keywords, run keywords)
CONTROLS = {
    "Y12 as built, a plain piston": ("it retracts at c61 and pulls nothing: G stays in (-4,3,2), NP12 lit, and Y12 goes out again at c67", dict(y12=t.pis("piston", "west", "Y12")), {}),
    "no U_Y": ("ARM_Z11 stays on Y12: W_Y lifts RB_D alone and Y12 stays out", dict(drop=(U_Y,)), {}),
    "U_Y not sticky": ("the same: it pulls nothing", dict(swap={U_Y: t.pis("piston", "down", "U_Y", True), U_HEAD: B("piston_head", facing="down", sticky=False)}), {}),
    "U_Y's hold never taken out": ("the same: NP12's relight finds U_Y powered", {}, dict(hold=None)),
    "no W_Y": ("RB_D stays beside ARM_Z11's cell: U_Y lifts ARM_Z11 alone and Y12 stays out", dict(drop=(W_Y,)), {}),
    "W_Y not sticky": ("the same: its head lands on RB_D and it pulls nothing", dict(swap={W_Y: t.pis("piston", "down", "W_Y")}), {}),
    "no S_W": ("nothing powers W_Y at c58: P_G's update finds it unpowered and it stays in", dict(drop=(S_W,)), {}),
    "no R_F": ("the same", dict(drop=(R_F,)), {}),
    "no S_F": ("the same: R_F reads air", dict(drop=(S_F,)), {}),
    "no D_X": ("the same: nothing powers S_F", dict(drop=(D_X,)), {}),
    "no B_Y": ("nothing stands in (-4,3,2): ARM_Z11's landing at c66 j fires Y12 again", dict(drop=(B_Y,)), {}),
    "B_Y's source never set": ("the same", {}, dict(src=None)),
}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    r.worlds()
    rb = wd.build()
    ref = list(wd.frames(rb))[1:]
    rcl, rw, rbad = wd.run(rb, ticks=pp.idle(LAST))
    assert not rbad
    b = build()
    kinds = [st.n for st in MINE.values()]
    print(f"added: {len(MINE)} blocks ({kinds.count('sticky_piston')} sticky pistons, one of them built out with its head, {kinds.count('piston')} piston, "
          f"{kinds.count('repeater')} repeater, {kinds.count('redstone_wire')} dust, {kinds.count('stone')} stone); Y12 a sticky piston, a measured block of "
          "design_c changed; stand-ins: one redstone block built at (-2,8,2) and four commands after the input (that block out and back without updates, "
          "a redstone block at (-5,3,3) in and out with updates)")
    taken = set(d.full_blocks(rb)) | set(rcl.b) | set(v.cumulative_cells(rb)[0])
    for blocks, be in (*ref, *rw.frames):
        taken |= set(blocks) | be
    print("added or stand-in cells that west_drives.py's build fills at any tick, or on the door plane or in the hallway:",
          ", ".join(f"{NAMES.get(c, c)} {c}" for c in (*MINE, HOLD, SRC_B, W_HEAD) if c in taken or r.plane_or_hall(c)) or "none")
    moved, first = wd.against(b, ref, set(ADDED))
    print("moved during load:", moved or "none", "| the opening and the close to c30 outside the added cells, Y12 and its head's cell:",
          f"differ at {wd.differs(first, 30)}" if wd.differs(first, 30) else "the same at every tick")
    op, _ = t.opened(b)
    print("open state:", ", ".join(f"{n} " + ("out" if t.at(op, n)[2] else "in") + f" powered by {[x for _, x in power_sources(op, c)] or 'nothing'}"
                                   for n, c in (("U_Y", U_Y), ("W_Y", W_Y), ("B_Y", B_Y))), "| G", t.at(op, "G")[0],
          "(the tap's stone holds W_Y out, its head on RB_D; B_Y's push would move G north)")
    cl, w, bad = run(b)
    late = {}
    for k, ((bl, be), (rbl, rbe)) in enumerate(zip(w.frames, rw.frames)):
        for c in (set(bl) | set(rbl) | be | rbe) - set(ADDED):
            if (bl.get(c) != rbl.get(c) or (c in be) != (c in rbe)) and c not in late:
                late[c] = k - 1
    names = {**wd.NAMES, ARM: "ARM_Z11's cell", RB_D: "RB_D's cell", B_HEAD: "(-4,3,2)", wd.L: "L", o.TAP: "the tap's dust", o.R_D: "the tap's repeater",
             **{c: f"NP12's dust {c}" for c in NP12}}
    by_tick = {}
    for c, k in sorted(late.items(), key=lambda x: (x[1], x[0])):
        by_tick.setdefault(k, []).append(names.get(c, str(c)))
    print(f"the close and the returns, c-1 to c{LAST}, against west_drives.py's run, cells outside the added ones that differ:",
          "; ".join(f"from c{k}: " + ", ".join(ns) for k, ns in by_tick.items()) or "none", "| every other cell is the same at every tick")
    cells = set(v.cumulative_cells(b)[0])
    for blocks, _ in w.frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print("box, opening + close + returns, stand-in cells included:", t.s.box(cells))

    print(f"\n== the close and the returns from the input, with the four stand-in commands: c50 to c{LAST}")
    mine_ev, ref_ev = pv.per_tick(w, -1, LAST), pv.per_tick(rw, -1, LAST)
    early = [f"c{n}: " + ", ".join(m.split(" ", 1)[1].split(":")[0] for m in set(mine_ev[n + 1]) - set(ref_ev[n + 1])) for n in range(-1, 50) if mine_ev[n + 1] != ref_ev[n + 1]]
    assert all(set(c) <= set(a_) for a_, c in zip(mine_ev[:51], ref_ev[:51]))
    print("   c-1 to c49: the piston events of west_drives' run, tick by tick, and", "; ".join(early) or "no other", "| from c50:")
    print("\n".join("   " + x for x in said(w)))
    print("   ->", ok(bad) if bad else "done: Y12 in, powered by ARM_Z11 and RB_D and not updated since; G at (-3,3,2); NP12 dark, the tap off; RB_D and "
          "ARM_Z11 where they were; A_D in and unpowered, it never moved; U_Y out on its hold, W_Y and B_Y in; RB12 on K, K in, powered by L and not "
          "updated; the rest as west_drives.py leaves it; nothing moving")
    print("   ", where(w))
    print("   U_Y's and W_Y's events from c-1 to c49:", "; ".join(x for x in pv.told(w) if pv.tick_of(x) < 50 and ("U_Y@" in x or "W_Y@" in x)) or "none",
          "(the tap's repeater turns off beside W_Y at c2 d; A_D's head is under W_Y's then)")
    rest, dust = pv.differing(cl, w)
    off = [x for x in rest if not any(x.startswith(str(c) + ":") for c in (*pp.PLANE, t.RB_ST, rd.RB_1, rd.RB_2))]
    left = [n for n in r.GROUPS[0][1] if t.at(cl, n) != t.at(w, n)]
    print(f"   cells outside the door plane that still differ from the closed state: {len(off)} (24 after west_drives.py):", ", ".join(left),
          "(the opening's other six relays and their blocks) and p9_p8's repeater R_9, off while RB_Y is up | NP12's dust and the tap's that are lit:",
          [c for c in (*NP12, o.TAP) if w.get(c).p["power"]] or "none")
    lit = [k - 1 for k, (bl, _) in enumerate(w.frames) if k > 6 and bl[H].p["power"]]
    tap = [k - 1 for k, (bl, _) in enumerate(w.frames) if k > 6 and bl[o.R_D].p["powered"]]
    dp = [k - 1 for k, (bl, _) in enumerate(w.frames) if k > 6 and bl[f.DP].p["power"]]
    print(f"   after c5: H lit after c{lit[0]} to c{lit[-1]}; the tap's repeater on after c{tap[0]} to c{tap[-1]}; DP lit:", dp or "never",
          "| A_D's push at c64:", "; ".join(x.split(" ", 1)[1] for x in pv.told(w) if pv.tick_of(x) == 64 and "piston@" + str(A_D) in x) or "not queued")

    print("\n== order: against the run above")
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)), ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("from c30 on, the scheduled ticks of each tick in reverse order, priorities ignored", dict(backwards=True)),
                     ("at c64, A_D's push ahead of W_Y's (sim only; the game queues W_Y's first, at RB_D's landing)", dict(extra={64: a_d_first})),
                     ("the blocks that land at c60 j in reverse order (sim only)", dict(extra={60: all_reversed})),
                     ("the blocks that land at c63 j in reverse order: G ahead of RB_D, so A_D's push is queued ahead of W_Y's (sim only)", dict(extra={63: all_reversed})),
                     ("the blocks that land at c66 j in reverse order (sim only)", dict(extra={66: all_reversed}))):
        _, x, badx = run(b, **kw)
        print(f"   {name}:", ok(badx) + ";", "piston events of each tick", "the same set" if pv.per_tick(x, -1, LAST) == mine_ev else "DIFFER", "|", where(x))

    print("\n== the stand-in commands, each moved alone (before the tick named), and R_F's delay")
    for name, key, at, vals in (("U_Y's hold out", "hold", 0, (56, 58, 59, 60, 61, 62)), ("U_Y's hold back", "hold", 1, (61, 62, 63, 64, 65, 66, 68)),
                                ("B_Y's source in", "src", 0, (60, 61, 62, 63, 64, 65, 66)), ("B_Y's source out", "src", 1, (64, 66, 67, 68, 70, 72))):
        base = dict(hold=HOLD_AT, src=SRC_AT)
        res = {}
        for k in vals:
            pair = list(base[key])
            pair[at] = k
            res[f"c{k}"] = "done" if not run(b, **{key: tuple(pair)})[2] else "FAILS"
        print(f"   {name} (here c{base[key][at]}):", res)
    print("   R_F (built 1 tick):", {k: "done" if not run(build(swap={R_F: rd.rep("west", k)}))[2] else "FAILS" for k in (1, 2, 3, 4)},
          "(at 2 ticks or more W_Y is still powered when its head lands and stays out on RB_D)")
    print("   B_Y's source in before c62 or c63 puts the head in (-4,3,2) ahead of G's landing at c63 j; in before c60 it is powered and not updated until G leaves "
          "(G's landing at c60 j finds M_K's base still moving behind G); from c64 on Y12's push, queued at c63 j, is dropped at c64 g behind U_Y's and W_Y's")

    print("\n== controls: one thing changed, the same run (where G is still in (-4,3,2) at c62, B_Y's stand-in source, set blind, pushes it north into M_K)")
    for name, (title, bkw, rkw) in CONTROLS.items():
        bc = build(**bkw)
        mv = d.make_world(bc)[1]
        _, x, badc = run(bc, **rkw)
        print(f"   {name}: {title}:", ok(badc), "|", where(x), "| moved during load: " + ", ".join(m.split("@")[0] for m in mv) if mv else "")
    work = [c for c in MINE if c != U_HEAD]
    left = {c: bool(run(build(drop=(c,)))[2]) for c in work}
    print(f"   each of the {len(work)} added blocks (U_Y with its head) left out, one at a time:",
          "the re-arm FAILS every time" if all(left.values()) else "done without " + ", ".join(NAMES[c] for c, bad_ in left.items() if not bad_))

    back, differ2, (_, y, bad2) = second(b, w, cl)
    print(f"\n== a second cycle (sim only): after the run the {len(back)} cells that still differ, labels apart, are set back as loaded without updates, "
          "and the input goes on again")
    print("   pending after the first run: scheduled ticks", w.sched or "none", "| block events", list(w.events) or "none")
    print("   the second opening against the first, every cell, labels apart:", f"differs at {differ2}" if differ2 else "the same at every tick")
    print("   the second close and returns, the same commands:", ok(bad2) + ";", "piston events of each tick, labels apart,",
          "the same" if wd.bare_events(y) == wd.bare_events(w) else "DIFFER")

    print("\n== what-ifs (sim only)")
    ws = wd.run(wd.build(swap={Y12: STICKY}))[1]
    x = copy.deepcopy(ws)
    x.__class__ = World
    for c, st in ((U_Y, PISTONS[U_Y]), (U_HEAD, PISTONS[U_HEAD]), (HOLD, HOLD_BLOCK), (B_Y, PISTONS[B_Y])):
        x.cmd_set_silent(c, st)
    x.log.clear()
    t0 = x.time
    x.cmd_set((-2, 4, 3), t.GLASS)
    x.run(4)
    parked = t.at(x, "RB_D")[0], [c for _, c in power_sources(x, wd.M_K)]
    x.cmd_set_silent(HOLD, AIR)
    x.cmd_set((-2, 7, 2), t.GLASS)
    x.run(4)
    ev = [f"+{tm - t0}{ph} {m.split(':')[0]}" for tm, ph, m in x.log if "EXTEND" in m or "RETRACT" in m]
    print("   RB_D moved by A_D instead of W_Y, after west_drives.py's returns with Y12 sticky (NP12 lit, the tap on): A_D updated by command goes "
          f"out and stays out; RB_D parks at {parked[0]}, M_K powered by {parked[1]} (QC through the stone on it); then U_Y's hold out and U_Y "
          "updated by command:", "; ".join(ev), "| M_K", "out" if t.at(x, "M_K")[2] else "in",
          "(G's leaving updates M_K; its retract would pull WK up beside K, and K, powered by L, fires on that)")
    hyp = copy.deepcopy(cl)
    hyp.cmd_set_silent(ARM, AIR)
    hyp.cmd_set_silent(RB_D, AIR)
    cellsy = {}
    for c in ((-2, 5, 2), (-1, 4, 2), (-2, 4, 3), (-2, 4, 1), (-3, 4, 2)):
        z = copy.deepcopy(hyp)
        z.cmd_set_silent(c, t.RB)
        cellsy[c] = bool(power_sources(z, Y12))
    print("   a redstone block one step from ARM_Z11's cell, RB_D taken out: Y12 powered from", [c for c, on in cellsy.items() if on],
          "| not powered from", [c for c, on in cellsy.items() if not on] or "none")
