"""Z11's return, first pass (door coords): after the close Z11 goes in and is armed as the load leaves it, RB11 at
(-2,4,1) on its head cell, (-2,5,1) and (-1,5,1) empty, with Y12's re-arm (y12_holds.py) the same at every tick.
Not done from blocks: one drive, H11's pull, is stood in for by a redstone block set and taken out by command
(setblock strict) after the input, so this is a mechanism with its one open drive named, not yet a design.
3 blocks on y12_holds.py's build, no measured block changed, box 2940. Everything printed is COMPUTED on the
simulator; nothing here ran on a server.

Holds   After the close Z11 is held by ARM_Z11 (-2,4,2), beside the cell above it, and by its own payload RB11
        at (-2,5,1), two above it (QC). ARM_Z11 leaves only in Y12's window (U_Y lifts it at c61 g and puts it
        back, landing at c66 j); RB11 has to be away from (-2,5,1) then, and back in (-2,4,1) by the end.
H11     A sticky piston at (-3,5,1) facing east, beside RB11. DP's pulse is its first drive: RB_D lands in DP's
        source cell (-3,4,1), under H11, at c2 j and A_D pulls it back at c3 g, the pulse that spits P11. H11
        pushes RB11 east at c3 g and is spat in the same phase: RB11 is placed at (-1,5,1) at once, beside P10,
        which it powers until c60. P11's head is then moving through (-1,3,0), in P10's way, so P10's push fails
        and it goes out at c8 on r_P10 as before. That rests on order: H11's spit is queued ahead of P11's (A_D's
        pull updates H11, above RB_D's cell, before DP's dust, which reaches P11), and a plain H11 would land
        RB11 only at c5 j and P10 would go out at c6 (the order checks and the controls). Nothing else of the
        close changes. Z11, then held by ARM_Z11 alone, retracts at c61 g when U_Y's lift of ARM_Z11 updates its
        head, inside Y12's window: Y12 is retracting then and P11 is unpowered, so Z11's retract moves nothing
        else.
Return  H11 pulls RB11 back into (-2,5,1) and D11, a piston at (-2,6,1) facing down, pushes it into (-2,4,1).
        STAND-IN: H11's second drive is a redstone block at (-3,6,0), beside the cell above H11 (QC; it powers
        no other piston), set before c56 and taken out before c61, both without updates. W_Y's extension
        beside H11 at c58 g is H11's update: it goes out into the empty (-2,5,1), its head landing at c60 j
        beside U_Y's head (U_Y is updated then anyway, by NP12's relight). Z11's retract at c61 g takes its
        head out from under H11's: H11, unpowered, pulls RB11 back (after Z11's event, so RB11 lands at c63 j
        after Z11's base). D11 is powered from c60 d to c68 d by R11, a 4-tick repeater at (-2,7,2) on U_Y
        facing south: it reads S_U (-2,7,3) and points into (-2,7,1), the cell above D11 (QC; nothing else
        reads it there). RB11's landing at c63 j is D11's update: it pushes RB11 down at c64 g, while ARM_Z11
        is moving; ARM_Z11 lands at c66 j, RB11 right after it, and Z11, powered again, cannot push RB11 up
        into D11's head. R11 turns off at c68 d and D11 retracts. Z11 ends in, powered by ARM_Z11 and not
        updated, as loaded.
Why     R11 must not be on before H11's head is in (-2,5,1): D11 would push into the empty cell and its head's
        arrival beside U_Y's head would retract U_Y a tick early (the control without the stand-in). At 4 ticks
        R11 comes on at c60 d, as H11's head lands. And D11 must still be out when RB11 lands at c66 j. RB_U in
        its park (-1,7,1) powers D11 too (QC) from c14 to c44 and c54 to c60, while (-2,5,1) is empty until
        c58 (the lead's warning): nothing updates D11 then.
Left    H11's second drive from blocks. It needs power at W_Y's extension (c58 g) and none from Z11's retract
        (c61 g) on, with no update to W_Y (in and powered c52 to c58), U_Y (out and dark c60 d to c61 g) or
        D11 (dark beside the empty (-2,5,1) before c58). Every cell that powers H11 is boxed in by the bus's
        west branch, the west timer's line, W_Y's column, DP's source cell and D11's cell; no single block in
        reach does it (z11_search.txt). The S feed's own time would: a redstone block at (-3,7,1), beside the
        cells above H11, W_Y and D11, from c52 to c60 returns Z11 with no other command (W_Y is powered then
        by S_W anyway; the what-if). A stone there under a dust lit from D_S would carry it, but that dust's
        cells join the west timer's line, a measured block (the lead's call).

Not controls: the stand-in block (a command).
Run from the repo root (sim; about 20 s):
python -m scripts.door2.close_layout.z11 > scripts/door2/close_layout/z11.txt"""
import copy
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, p10_v as pv, returns as r, rbt_drives as rd, west_drives as wd, y12 as y, y12_holds as h
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World

Z11, HEAD, UP, PARK = (-2, 3, 1), (-2, 4, 1), (-2, 5, 1), (-1, 5, 1)    # HEAD: Z11's head cell, RB11's closed cell; UP: RB11's open cell
H11, D11, R11, HOLD = (-3, 5, 1), (-2, 6, 1), (-2, 7, 2), (-3, 6, 0)     # HOLD: the stand-in for H11's second drive
P10, P11 = (-1, 5, 0), (-2, 3, 0)
LAST = h.LAST
MINE = {H11: t.pis("sticky_piston", "east", "H11"), D11: t.pis("piston", "down", "D11"), R11: rd.rep("south", 4)}
HOLD_BLOCK = B("rb", id="HOLD_H")
HOLD_AT = (56, 61)                                                       # the stand-in commands: before these ticks, both strict
NAMES = {H11: "H11", D11: "D11", R11: "R11", HOLD: "H11's stand-in", PARK: "(-1,5,1)", UP: "(-2,5,1)", HEAD: "(-2,4,1)", Z11: "Z11"}
CELLS = (Z11, HEAD, UP, PARK, *MINE, HOLD)                               # what the verdict reads, and what a run beside y12_holds.py's leaves out
wd.SHOW = (*wd.SHOW, f"repeater {R11} ", *(f"land rb@{c}" for c in (PARK, UP, HEAD)))


def build(drop=(), swap=None):
    """y12_holds.py's build with the 3 blocks; `drop` leaves cells out, `swap` replaces some."""
    b = h.build()
    for c, st in {**MINE, **(swap or {})}.items():
        if c not in drop:
            assert c in (swap or {}) or c not in b.b, c
            b.b[c] = st
            b.role[c] = "z11"
    return b


def verdict(w, cl):
    """y12_holds.py's verdict, the cells of Z11's column, RB11's park, the 3 blocks and the stand-in's cell as
    loaded, and Z11, H11 and D11 powered as in the closed state, R11 off. Empty when Z11 is home."""
    bad = h.verdict(w, cl)
    bad += [f"{NAMES[c]} {'moving' if c in w.be else w.get(c)}" for c in CELLS if c in w.be or pp.bare(w.get(c)) != pp.bare(cl.get(c))]
    bad += [f"{n} powered by {[x for _, x in power_sources(w, c)]}" for n, c in (("Z11", Z11), ("H11", H11), ("D11", D11))
            if w.get(c).n == cl.get(c).n in ("piston", "sticky_piston") and power_sources(w, c) != power_sources(cl, c)]
    return bad + ["R11 on"] * bool(w.get(R11).p.get("powered"))


def commands(hold=HOLD_AT):
    """`before` for wd.noted: the stand-in block set before c`hold[0]` and taken out before c`hold[1]`, both
    without updates (setblock strict); None leaves them out."""
    if not hold:
        return {}
    return {hold[0]: lambda w: w.cmd_set_silent(HOLD, HOLD_BLOCK), hold[1]: lambda w: w.cmd_set_silent(HOLD, AIR)}


def run(b, hold=HOLD_AT, opened=None, extra=None, last=LAST, **kw):
    """b opened from the input and taken through the close and the returns with the stand-in commands: (closed
    state, noted world, verdict); `extra` {tick: function of the world} acts before that tick as well."""
    cl = d.make_world(b)[0]
    before = commands(hold)
    for k, fn in (extra or {}).items():
        before[k] = (lambda g, e: lambda w: (g(w), e(w)))(before[k], fn) if k in before else fn
    w = wd.noted(t.opened(b)[0] if opened is None else opened, pp.idle(last), before=before, **kw)
    return cl, w, verdict(w, cl)


def mine_line(x):
    return any(f" {n}@" in x for n in ("H11", "D11", "Z11")) or f"repeater {R11} " in x or any(f"land rb@{c}" in x for c in (PARK, UP, HEAD))


def said(w, first=-1, last=LAST):
    return [x for x in pv.told(w) if first <= pv.tick_of(x) <= last and (mine_line(x) or (pv.tick_of(x) >= 58 and h.mine_line(x)))]


def where(w):
    return ", ".join(f"{n} {t.at(w, n)[0]}" + {True: " out", False: " in", None: ""}[t.at(w, n)[2]] for n in ("Z11", "RB11", "H11", "D11", "Y12", "U_Y")) + \
        f", ARM_Z11's cell {w.get(y.ARM).n}, (-2,5,1) {'moving' if UP in w.be else w.get(UP).n}"


def events(w, first=-1, last=LAST):
    return "; ".join(f"c{pv.tick_of(m)}" + m.split(" ", 1)[1].split(":")[0].replace("level ", " level ") for m in pv.told(w)
                     if first <= pv.tick_of(m) <= last and any(f" {n}@" in m for n in ("H11", "D11", "Z11"))) or "none"


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
    the first, labels apart, and the second close and returns with the same stand-in."""
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


def rb11_first(w):
    """before c63: RB11's move back, begun after Z11's retract, put ahead of Z11's base among the moving blocks, so that it lands
    first at c63 j (sim only)."""
    idx = {be.pos: i for i, be in enumerate(w.tickers) if not be.removed}
    if UP in idx and Z11 in idx and idx[UP] > idx[Z11]:
        w.tickers.insert(idx[Z11], w.tickers.pop(idx[UP]))


def p11_first(w):
    """before c3: in its phase g, H11's spit is put behind P11's, both queued by A_D's pull of RB_D (sim only)."""
    orig = w.trigger

    def trig(p, st, b0, fc):
        if p == H11 and b0 != 0 and any(k[0] == P11 for k in w.events):
            w.events[(p, st.n, b0, fc)] = True
            return
        return orig(p, st, b0, fc)
    w.trigger = trig


# name: (title, build keywords, run keywords)
CONTROLS = {
    "no H11": ("RB11 stays at (-2,5,1) and holds Z11 out: D11 never moves", dict(drop=(H11,)), {}),
    "H11 not sticky": ("its push at c3 is not spat: RB11 lands at (-1,5,1) at c5 j, after P11's head has left (-1,3,0), and P10 goes out at "
                       "c6 instead of c8: the door plane fails (P8, Q, S)",
                       dict(swap={H11: t.pis("piston", "east", "H11")}), {}),
    "no D11": ("RB11 comes back to (-2,5,1) and stays there: Z11 is in, powered by it and ARM_Z11, (-2,4,1) empty", dict(drop=(D11,)), {}),
    "no R11": ("the same: nothing powers D11", dict(drop=(R11,)), {}),
    "no stand-in": ("H11 never goes out again: RB11 stays at (-1,5,1); R11 comes on at c60 with (-2,5,1) empty, D11 pushes into it and its "
                    "head beside U_Y's retracts U_Y a tick early: Y12's re-arm fails", {}, dict(hold=None)),
    "stand-in out before c62": ("H11 is still powered at Z11's retract and pulls only at c64, when RB_D leaves (-3,5,2); D11 pushes at c67, "
                                "R11 lets it go at c68 with RB11 still moving, and Z11 pushes RB11 up again at c70", {}, dict(hold=(HOLD_AT[0], 62))),
}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    r.worlds()
    hb = h.build()
    hcl, hw, hbad = h.run(hb)
    assert not hbad
    href = list(wd.frames(hb))[1:]
    b = build()
    kinds = [st.n for st in MINE.values()]
    print(f"added: {len(MINE)} blocks on y12_holds.py's build ({kinds.count('sticky_piston')} sticky piston, {kinds.count('piston')} piston, "
          f"{kinds.count('repeater')} repeater); no measured block changed; one stand-in: a redstone block at {HOLD} set and taken out with "
          f"setblock strict after the input (before c{HOLD_AT[0]} and before c{HOLD_AT[1]})")
    taken = set(d.full_blocks(hb)) | set(hcl.b) | set(v.cumulative_cells(hb)[0])
    for blocks, be in (*href, *hw.frames):
        taken |= set(blocks) | be
    print("added cells, the stand-in's and RB11's park, that y12_holds.py's build fills at any tick or on the door plane or in the hallway:",
          ", ".join(f"{NAMES[c]} {c}" for c in (*MINE, HOLD, PARK) if c in taken or r.plane_or_hall(c)) or "none")
    moved, first = wd.against(b, href, set(MINE))
    early = {c: k for c, k in first.items() if wd.tick_key(k) <= 1000 + 30}
    print("moved during load:", moved or "none", "| the opening and the close to c30 against y12_holds.py's build, outside the 3 cells:",
          "; ".join(f"{NAMES.get(c, c)} from {k}" for c, k in sorted(early.items(), key=lambda x: (wd.tick_key(x[1]), x[0]))) or "the same at every tick",
          "(RB11 spat by H11 at c3), every other cell the same at every tick")
    op, _ = t.opened(b)
    print("open state:", ", ".join(f"{n} " + ("out" if t.at(op, n)[2] else "in") + f" powered by {[x for _, x in power_sources(op, c)] or 'nothing'}"
                                   for n, c in (("H11", H11), ("D11", D11), ("Z11", Z11))), "| RB11", t.at(op, "RB11")[0], "| R11",
          "on" if op.get(R11).p["powered"] else "off")
    cl, w, bad = run(b)
    print("closed state:", ", ".join(f"{n} powered by {[x for _, x in power_sources(cl, c)] or 'nothing'}" for n, c in (("Z11", Z11), ("H11", H11), ("D11", D11))))
    late = h.frame_diff(w.frames, hw.frames, CELLS)
    print(f"the close and the returns, c-1 to c{LAST}, against y12_holds.py's run, cells outside the 3 blocks, the stand-in's, Z11's column and RB11's park "
          "that differ:", "; ".join(f"{c} after {h.runs(ks)}" for c, ks in sorted(late.items())) or "none", "| every other cell is the same at every tick")
    mine = h.frame_diff(w.frames, hw.frames, (*MINE, HOLD))
    print("   Z11's column and RB11's park against y12_holds.py's run:", "; ".join(f"{NAMES[c]} after {h.runs(ks)}" for c, ks in sorted(mine.items())))
    cells = set(v.cumulative_cells(b)[0])
    for blocks, _ in w.frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print("box, opening + close + returns:", t.s.box(cells))

    print(f"\n== the close and the returns from the input, with the stand-in: c-1 to c{LAST} (Z11's, H11's and D11's events, R11, RB11's landings; "
          "from c58 y12_holds.py's lines as well)")
    print("\n".join("   " + x for x in said(w)))
    print("   ->", y.ok(bad) if bad else "done: Z11 in, powered by ARM_Z11 and not updated since; RB11 at (-2,4,1), (-2,5,1) and (-1,5,1) empty; H11 "
          "and D11 in, R11 off, the stand-in's cell empty; Y12's re-arm as y12_holds.py leaves it; nothing moving")
    print("   ", where(w))
    print("   powered: H11 after", spans(w, lambda x: x.get(H11).n == "sticky_piston" and power_sources(x, H11)), "| D11 after",
          spans(w, lambda x: x.get(D11).n == "piston" and power_sources(x, D11)), "| R11 on after", spans(w, lambda x: x.get(R11).p.get("powered")),
          "| P10 powered by RB11 after", spans(w, lambda x: x.get(PARK).n == "rb"))
    rest, _ = pv.differing(cl, w)
    off = [x for x in rest if not any(x.startswith(str(c) + ":") for c in (*pp.PLANE, t.RB_ST, rd.RB_1, rd.RB_2))]
    left = [n for n in r.GROUPS[0][1] if t.at(cl, n) != t.at(w, n)]
    print(f"   cells outside the door plane that still differ from the closed state: {len(off)} (20 after y12_holds.py):", ", ".join(left),
          "(the opening's other five relays and their blocks) and p9_p8's repeater R_9, off while RB_Y is up")
    p10 = [m for m in pv.told(w) if pv.tick_of(m) <= 10 and ("P10@" in m or "P11@" in m or "H11@" in m)]
    print("   c3 to c10, H11, P11 and P10:", "; ".join(f"c{pv.tick_of(m)}" + m.split(" ", 1)[1].split(":")[0].replace("level ", " level ") for m in p10))

    print("\n== the stand-in commands, each moved alone (before the tick named)")
    for at in (0, 1):
        vals = (4, 30, 50, 56, 57, 58, 59) if at == 0 else (58, 59, 60, 61, 62)
        res = {}
        for k in vals:
            pair = list(HOLD_AT)
            pair[at] = k
            if pair[0] < pair[1]:
                res[f"c{k}"] = "done" if not run(b, hold=tuple(pair))[2] else "FAILS"
        print(f"   {'set' if at == 0 else 'taken out'} (here c{HOLD_AT[at]}):", res)
    print("   set before c58 or earlier: H11 is powered when W_Y's extension updates it (no other update reaches H11 from c4 to c57); set before "
          "c59 it misses that update. Taken out before c59 or c60, W_Y's head landing at c60 j updates H11 and it pulls at c61 g ahead of Z11's "
          "retract; before c61 Z11's retract itself updates H11 and it pulls after it; before c62 or later it is still powered then")

    print("\n== order: against the run above")
    mine_ev = pv.per_tick(w, -1, LAST)
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)), ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("from c30 on, the scheduled ticks of each tick in reverse order, priorities ignored", dict(backwards=True)),
                     ("at c3, P11's spit ahead of H11's (sim only; A_D's pull updates H11, above RB_D's cell, before the dust that reaches P11)",
                      dict(extra={3: p11_first})),
                     ("at c63 j, RB11 landing in (-2,5,1) ahead of Z11's base (sim only; its move began after Z11's)", dict(extra={63: rb11_first})),
                     *((f"only the blocks that land at c{k} j in reverse order among themselves (sim only)", dict(extra={k: h.landing_reversed}))
                       for k in (60, 66))):
        _, x, badx = run(b, **kw)
        print(f"   {name}:", y.ok(badx) + ";", "piston events of each tick", "the same set" if pv.per_tick(x, -1, LAST) == mine_ev else "DIFFER", "|", where(x))
    mixed = [run(b, extra=h.shuffled(n), reverse=bool(n & 1), ia_last=bool(n & 2)) for n in range(60)]
    print("   60 runs, in each from c30 on the scheduled ticks of every tick in a random order, priorities ignored; dust's updates reversed in every "
          "second run, I_A's event last in two of every four (the moving blocks in the order their moves began, as measured):",
          "done in all 60;" if not any(x[2] for x in mixed) else f"FAILS in {sum(bool(x[2]) for x in mixed)};", "piston events of each tick",
          "the same set in all" if all(pv.per_tick(x[1], -1, LAST) == mine_ev for x in mixed) else "DIFFER in some")

    print(f"\n== R11's delay, 1 to 4 ticks with the rest as built (on from c52 d + 2k to c60 d + 2k)")
    for k in (1, 2, 3, 4):
        _, x, badk = run(build(swap={R11: rd.rep("south", k)}))
        print(f"   {k}:", y.ok(badk), "|", events(x, 50))

    print("\n== controls: one thing changed, the same run")
    for name, (title, bkw, rkw) in CONTROLS.items():
        bc = build(**bkw)
        mv = d.make_world(bc)[1]
        _, x, badc = run(bc, **rkw)
        print(f"   {name}: {title}:", y.ok(badc), "|", where(x), "|", events(x, 3), "| moved during load: " + ", ".join(m.split("@")[0] for m in mv) if mv else "")

    back, differ2, (_, z, bad2) = second(b, w, cl)
    print(f"\n== a second cycle (sim only): after the run the {len(back)} cells that still differ, labels apart, are set back as loaded without updates, "
          "and the input goes on again")
    print("   pending after the first run: scheduled ticks", w.sched or "none", "| block events", list(w.events) or "none")
    print("   the second opening against the first, every cell, labels apart:", f"differs at {differ2}" if differ2 else "the same at every tick")
    print("   the second close and returns, the same stand-in:", y.ok(bad2) + ";", "piston events of each tick, labels apart,",
          "the same" if wd.bare_events(z) == wd.bare_events(w) else "DIFFER")

    print("\n== what-ifs (sim only)")
    ha = h.build()
    ha.b[H11] = MINE[H11]
    hacl, haw, habad = h.run(ha)
    print("   H11 alone, on y12_holds.py's build, from the input, no command: y12_holds.py's verdict", y.ok(habad), "|", events(haw), "|", where(haw))
    print("   against y12_holds.py's run, every cell that differs:", "; ".join(f"{NAMES.get(c, c)} after {h.runs(ks)}"
                                                                         for c, ks in sorted(h.frame_diff(haw.frames, hw.frames, ()).items())))
    s_at = (-3, 7, 1)
    ex = {52: lambda w: w.cmd_set_silent(s_at, t.RB), 60: lambda w: w.cmd_set_silent(s_at, AIR)}
    _, x, badx = run(b, hold=None, extra=ex)
    print(f"   H11's drive in the S feed's time at {s_at}, beside the cells above H11, W_Y and D11 (QC for all three): a redstone block set before c52 and "
          "taken out before c60 without updates, in place of the stand-in; W_Y is powered then by S_W anyway:", y.ok(badx), "|", events(x, 50))
    print("   (a stone there under a dust at (-3,8,1), lit from D_S through a dust at (-3,9,2) on glass at (-3,8,2), would carry it, but both dusts would join "
          "the west timer's line: (-3,8,1) beside its step stone (-3,8,0) under (-3,9,0), (-3,9,2) up the glass (-2,9,2) to (-2,10,2))")
