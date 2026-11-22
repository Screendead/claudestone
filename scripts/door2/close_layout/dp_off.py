"""DP's on and off, stage 2 of the close, from blocks (door coords): the last command of the door's close up to
stage 2 is gone. Seven blocks on top of trigger.py's build; its 36 blocks, design_c's opening, the close feeds
and the S feed are unchanged. Everything printed is COMPUTED on the simulator; nothing here ran on a server.

Source  RB_D, a redstone block resting at (-3,4,2), south of DP's source cell (-3,4,1); A_D, a sticky piston at
        (-3,4,3) facing north, behind it. A_D out: RB_D real at (-3,4,1), DP 15. A_D's retract pulls it home.
Power   A_D's only power is Q_D, a stone at (-3,6,3), two above it (a QC cell), strongly powered by repeater R_D
        (-2,6,3), 1 tick, facing east on glass (-2,5,3). R_D reads TAP, a dust at (-1,6,3) on glass (-1,5,3),
        which reads NP12's dust (0,5,3) down the step. The glass passes nothing back: NP12 reads as before.
Armed   NP12 lights at t6 g (G leaves the step); that storm updates A_D, which is not powered yet. R_D turns on at
        t8 d and updates Q_D's neighbours, not A_D: from then A_D waits powered and not updated, as K does.
On      c0: K's event (level 1) kills NP12. H (-3,3,3), the dust under A_D, dies in it and updates A_D, which R_D
        still powers: A_D extends at level 2. RB_D lands at c2 j and lights DP; DP's change updates P11, which
        extends at c3, level 0: three ticks after P12's retract, as a block event.
Off     R_D turns off at c2 d (TAP died with NP12), again without an update of A_D. A_D's head lands at c2 j,
        right behind RB_D (a push makes the head's block entity last), and the landing updates A_D: unpowered,
        its retract is queued behind P11's extension. c3, level 0: P11 extends; A_D pulls RB_D, which is a moving
        block at once, DP 0, and DP's change updates P11: spat at level 1, S real at (0,3,0). RB_D and A_D are home
        at c5 j: the feed leaves nothing to return.
P6      P11's extension queues P6 (QC through FP) behind A_D's retract: that event finds FP dark and is dropped,
        in every order. P6 extends once, at c4, on NA's repeater with P1 to P5, and stays out, which is where the
        closed door has it. It is not spat: for that DP would have to stay lit one event longer.
        dp_off_search.py screens one and two more blocks for it; what passes there is built at the end here,
        and none of it holds.
Later   P11's head is in (-1,3,0) during c3, so P10 (stage 3) comes at c4 or later: the probe's commands for
        stages 3 to 5 are one tick later than trigger.py's.

Not controls: the two glass blocks carry TAP and R_D (the simulator does not drop an unsupported dust or
repeater); TAP's must not conduct (a stone there cuts NP12's step: ctl 9).
Run from the repo root (sim; replay-only):
python -m scripts.door2.close_layout.dp_off > scripts/door2/close_layout/dp_off.txt"""
import copy
from scripts.door2.close_layout import feeds as f, s_feed as s, trigger as t, dp
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, DIRS

RB_D, A_D, LIT, HEAD = (-3, 4, 2), (-3, 4, 3), t.SRC_P, (-3, 4, 2)
TAP_S, TAP, R_S, R_D, Q_D = (-1, 5, 3), (-1, 6, 3), (-2, 5, 3), (-2, 6, 3), (-3, 6, 3)
P11, P6, ON_P11 = dp.P11, dp.P6, (-2, 4, 0)
MINE = {RB_D: B("rb", id="RB_D"), A_D: t.pis("sticky_piston", "north", "A_D"), TAP_S: t.GLASS, TAP: t.DUST,
        R_S: t.GLASS, R_D: B("repeater", facing="east", delay=1, powered=False), Q_D: t.STONE}
SHOW = ("EXTEND", "RETRACT", "cancel", "failed", "dropped", f"wire {f.DP}", f"wire {TAP}", f"repeater {R_D}",
        f"land rb@{LIT}", f"land rb@{RB_D}", f"land piston_head@{HEAD}")
IDLE = [[(f.DRIVER, AIR)]] + [[] for _ in range(7)]            # c-1 .. c6, no command after the input
# dp_off_search.txt's six two-block passes that do not hold the dust on P11: four ideas
RELAY = "N_X, a piston at (-3,5,3) facing north above A_D, and D_X, a piston (plain or sticky) at (-3,5,2) facing down in front of it"
PAIRS = {
    "a dust at (-4,3,0), on NA's dust and beside NA's (-4,3,-1), and a stone at (-4,4,-1) above that one":
        {(-4, 3, 0): t.DUST, (-4, 4, -1): t.STONE},
    "dp_search's row pusher, a piston (plain or sticky) at (-4,4,-1) facing south, and a redstone block at (-4,4,3)":
        {(-4, 4, -1): t.pis("piston", "south", "X"), (-4, 4, 3): B("rb", id="XR")},
    "a redstone block at (-2,3,-1), beside NA's and NV's dust, under a piston at (-2,4,-1) facing down":
        {(-2, 3, -1): B("rb", id="XR"), (-2, 4, -1): t.pis("piston", "down", "X")},
    RELAY: {(-3, 5, 3): t.pis("piston", "north", "N_X"), (-3, 5, 2): t.pis("piston", "down", "D_X")},
}


def build(drop=(), swap=None, **kw):
    """trigger.py's build with the seven blocks; `drop` leaves cells out, `swap` replaces or adds some."""
    return t.build(drop=drop, swap={**MINE, **(swap or {})}, **kw)


def staged(through=5):
    """trigger.staged without the DP stand-in and with stages 3 to 5 one tick later: P11's head is in (-1,3,0)
    during c3, so P10 extends at c4."""
    out = [[] for _ in range(15)]
    out[0] = [(f.DRIVER, AIR)]                                       # c-1; c0: stages 0 and 1; c3: stage 2
    if through >= 5:
        out[5] = [(s.SRC_10, t.RB)]                                  # c4: 3 P10 extends
        out[6] = [(s.SRC_10, AIR), (s.SRC_V, t.RB), (s.SRC_F, t.RB)]  # c5: P10 spat; 4 V lands lit and fires; F_S out
        out[7] = [(s.SRC_F, AIR), (s.SRC_V, AIR)]                    # c6: RB_F spat, then V spat: 5 S fires
        out[8] = [(s.HOLD_G, AIR)]                                   # c7: RB_F pulled: S spat
    return out


class Noted(dp.Levels):
    """Levels that keeps each shown log line with its tick, phase and block-event level, and each update of A_D
    with whether A_D is powered then."""

    def L(self, msg):
        World.L(self, msg)
        if any(x in msg for x in SHOW):
            self.lines.append((self.tick_no, self.phase, self.cur if self.phase == "g" and self.seen is not None else None, msg))

    def check_extend(self, p):
        if p == A_D and self.get(p).n == "sticky_piston":
            self.noted.append((self.tick_no, self.phase, bool(self.neighbor_signal(p, DIRS["north"]))))
        super().check_extend(p)


def noted(w, ticks=IDLE, first=-1, before=None, **kw):
    """a copy of w taken through ticks (each: its commands, then the tick), the first numbered `first`;
    `before` {tick number: function of the world} acts ahead of that tick (sim only)."""
    w = copy.deepcopy(w)
    w.__class__ = Noted
    w.reverse, w.ia_last = kw.get("reverse", False), kw.get("ia_last", False)
    w.lvl, w.order, w.seen, w.after, w.said, w.lines, w.noted = {}, [], None, None, [], [], []
    for k, cmds in enumerate(ticks):
        w.log.clear()
        w.tick_no = k + first
        for c, blk in cmds:
            w.cmd_set(c, blk)
        if before and w.tick_no in before:
            before[w.tick_no](w)
        w.tick()
    w.said = [f"c{k} {m}" for k, _, _, m in w.lines if any(x in m for x in ("EXTEND", "RETRACT")) and any(n + "@" in m for n in dp.STAGE2)]
    return w


def told(w, tick="c", keep=lambda m: True):
    return [f"{tick}{k}{ph}" + ("" if lv is None else f" level {lv}") + f" {m}" for k, ph, lv, m in w.lines if keep(m)]


def moves(w):
    """the piston events that ran, as (tick, text)."""
    return [(k, m) for k, _, _, m in w.lines if "EXTEND" in m or "RETRACT" in m]


def verdict(w, dusts):
    """stage 2 as the world has it after c6, with no DP command: a list of what is wrong."""
    ev = moves(w)
    bad = []
    i12 = next((i for i, (_, m) in enumerate(ev) if "RETRACT P12" in m), None)
    i11 = [i for i, (_, m) in enumerate(ev) if "EXTEND P11" in m]
    if i12 is None or len(i11) != 1 or i11[0] < i12:
        bad.append("P11 does not extend once after P12's retract")
    if not any("RETRACT P11" in m and "SPIT (0, 3, 0)" in m for _, m in ev):
        bad.append("P11 not spat")
    want = {"S": ((0, 3, 0), "real", False), "P11": (P11, "real", False), "SP": ((0, 4, 0), "real", None),
            "C": ((1, 2, 0), "real", None), "Q": ((3, 3, 0), "real", False), "P6": (P6, "real", True),
            "TL": ((0, 2, 0), "real", None), "RB_D": (RB_D, "real", None), "A_D": (A_D, "real", False)}
    bad += [f"{n} {t.at(w, n)}" for n, x in want.items() if t.at(w, n) != x]
    bad += [f"dust lost at {c}" for c in dusts if w.get(c).n != "redstone_wire"]
    bad += ["FP lost"] * (w.get(f.FP).n != "stone") + [f"DP {w.get(f.DP).p.get('power')}"] * bool(w.get(f.DP).p.get("power"))
    return bad


def brief(m):
    """one shown line in a few words."""
    if "dropped" in m:
        return "P6's event dropped"
    who = m.split("@")[0].split()[-1]
    return who + (" out" if "EXTEND" in m else " spat" if "SPIT" in m else " pulls " + m.split("PULL ")[1].split("@")[0] if "PULL" in m else " in")


def p6(w):
    ev = [f"c{k} " + ("out" if "EXTEND" in m else "spat" if "SPIT" in m else "pulls back") for k, m in moves(w) if "P6@" in m]
    return ", ".join(ev) or "never fires"


def opening_notes(b):
    """the opening of b from the closed state, noted; ticks are numbered as trigger.py numbers them (t-1 first)."""
    w, _ = d.make_world(b)
    w.run(4)
    w.cmd_set(f.DRIVER, t.RB)
    return noted(w, [[] for _ in range(t.OPEN_TICKS)])


def updates(w, tick="c"):
    """A_D's updates, one entry per tick, phase and power."""
    seen = {}
    for k, ph, on in w.noted:
        seen[(f"{tick}{k}{ph}", "powered" if on else "not powered")] = seen.get((f"{tick}{k}{ph}", "powered" if on else "not powered"), 0) + 1
    return [f"{when} {how}" for (when, how) in seen] or "none"


# name: (title, build keywords)
CONTROLS = {
    "ctl 1": ("no RB_D: A_D pushes nothing, DP stays dark", dict(drop=(RB_D,))),
    "ctl 2": ("no A_D", dict(drop=(A_D,))),
    "ctl 3": ("A_D not sticky: RB_D is pushed in and never pulled, DP stays lit and P11 stays out",
              dict(swap={A_D: t.pis("piston", "north", "A_D")})),
    "ctl 4": ("no R_D: Q_D is never powered", dict(drop=(R_D,))),
    "ctl 5": ("no TAP: R_D never turns on", dict(drop=(TAP,))),
    "ctl 6": ("no Q_D: R_D powers nothing", dict(drop=(Q_D,))),
    "ctl 7": ("R_D at 2 ticks: it is still on when A_D's head lands, so A_D is not released; it turns off at c4 d "
              "without an update", dict(swap={R_D: B("repeater", facing="east", delay=2, powered=False)})),
    "ctl 8": ("a dust in R_D's place (no delay): Q_D is lit by the storm that updates A_D at t6 g, and A_D fires in the opening",
              dict(swap={R_D: t.DUST})),
    "ctl 9": ("a stone under TAP: NP12's dust (0,5,3) no longer reads (-1,4,3) down the step", dict(swap={TAP_S: t.STONE})),
}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    b, b0 = build(), t.build()
    base, _ = t.opened(b0)
    mine, moved = t.opened(b)
    cl, _ = d.make_world(b)
    dusts = [c for c, st in mine.b.items() if st.n == "redstone_wire"]
    print(f"added: {len(MINE)} blocks (1 redstone block, 1 sticky piston, 1 repeater, 1 dust, 1 stone, 2 glass); no stand-in for DP")
    print("opening, trigger build vs + DP's seven, open-state differences:", f.diff(f.snapshot(base), f.snapshot(mine)) or "none")
    print("cell differences outside the added blocks:", s.cell_diff(base, mine, set(MINE)),
          "| tick by tick, the door's pistons and the door plane:", dp.same_opening(b))
    print("moved during load:", moved or "none", "| closed state: DP", cl.get(f.DP).p["power"], "TAP", cl.get(TAP).p["power"],
          "R_D", "on" if cl.get(R_D).p["powered"] else "off", "| A_D powered by", [c for _, c in power_sources(cl, A_D)] or "nothing")
    wo = opening_notes(b)
    print("arming in the opening:", "; ".join(told(wo, "t", lambda m: "wire" in m and str(TAP) in m or "repeater" in m)))
    print("   A_D's updates in the opening:", updates(wo, "t"),
          "| NP12's dust (0,5,3):", base.get((0, 5, 3)).p["power"], "in the trigger build,", mine.get((0, 5, 3)).p["power"], "here")
    print("open state:", {n: t.at(mine, n) for n in ("A_D", "RB_D")}, "| DP", mine.get(f.DP).p["power"], "| TAP", mine.get(TAP).p["power"],
          "| A_D powered by", [(kind, c) for kind, c in power_sources(mine, A_D)])
    added = set(MINE) | {LIT}
    print("other pistons with an added cell among their power sources, open state:",
          {st.p["id"]: sorted(c for _, c in power_sources(mine, p) if c in added) for p, st in sorted(mine.b.items())
           if st.n in ("piston", "sticky_piston") and st.p["id"] != "A_D" and any(c in added for _, c in power_sources(mine, p))} or "none",
          "| Y12's other sources:", sorted(c for _, c in power_sources(mine, (-2, 3, 2)) if c not in added))
    cells = set(v.cumulative_cells(b)[0])
    print("box, opening:", s.box(cells))

    w = noted(mine)
    w0 = noted(mine, IDLE[:2])
    print("\n== the close from the input, no DP command: c-1 to c6")
    print("\n".join("   " + x for x in told(w)))
    bad0, bad = t.verdict_c0(w0), verdict(w, dusts)
    trig = [m for _, m in moves(noted(base, IDLE[:2]))]
    here = [m for _, m in moves(w0)]
    print("   stages 0 and 1 ->", "FAILS: " + "; ".join(bad0) if bad0 else "done in c0 as in the trigger build;",
          "c0's piston events without A_D's:", "the same, in the same order" if [m for m in here if "A_D" not in m] == trig else "DIFFER")
    print("   stage 2 ->", "FAILS: " + "; ".join(bad) if bad else
          "done: P11 extends once, after P12's retract, and is spat in that phase; S real at (0,3,0), retracted; SP (0,4,0), "
          "C (1,2,0), Q (3,3,0); no dust lost, FP there; RB_D and A_D home, DP 0")
    print("   P6:", p6(w) + ", stays out; TL real at (0,2,0). Its event queued by P11's extension is dropped (FP dark)")
    print("   A_D's updates, c-1 to c6:", updates(w))
    seen_p11 = [(k, n) for k, _, n, _, sn in w.order if P11 in sn and k >= 0]
    print("   block events from c0 on whose updates reach P11:", [f"c{k} {n}" for k, n in seen_p11], "| and in phase j of c2 RB_D's landing (DP's change)")

    w0, w1, lines, frames = t.close(b, staged())
    for blocks, _ in frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print("\n== through stage 5: stages 3 to 5 by command, one tick later than in trigger.py (c4 P10; c5 V and F_S; c6 both off; c7 G_S's hold)")
    for tick in lines[4:]:
        if len(tick) > 1 or not tick[0].endswith("[]"):
            print("\n".join(tick))
    bad1 = t.verdict_end(w1)
    print("   after c13 ->", "FAILS: " + "; ".join(bad1) if bad1 else
          "stage 5 done: S real at (1,3,0), retracted; C real at (1,1,0); (1,2,0) air; T, P12, P11, V in; SP, TL, Q, TM, "
          "P8 where the close needs them; RB_F parked; P7 out over TR at (2,2,0)", "| RB_D", t.at(w1, "RB_D")[:2], "A_D", t.at(w1, "A_D")[1:],
          "DP", w1.get(f.DP).p["power"])
    _, wt, _, _ = t.close(b0)
    print("   end state against trigger.py's run, where a command lights and cuts DP: cell differences outside the seven blocks:",
          s.cell_diff(wt, w1, set(MINE)))
    print("   box, opening + close through stage 5 (stand-in sources included):", s.box(cells))

    def per_tick(x):
        return [sorted(m for k, m in moves(x) if k == n) for n in range(-1, 7)]

    print("\n== order (must pass): against the run above")
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)),
                     ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("both", dict(reverse=True, ia_last=True))):
        r, r0 = noted(mine, **kw), noted(mine, IDLE[:2], **kw)
        _, r1, _, _ = t.close(b, staged(), **kw)
        print(f"   {name}:", "FAILS" if t.verdict_c0(r0) or verdict(r, dusts) or t.verdict_end(r1) else "stages 0 to 2 done, stage 5 done;",
              "piston events of each tick", "the same set;" if per_tick(r) == per_tick(w) else "DIFFER;",
              "c3:", ", ".join(brief(m) for k, _, _, m in r.lines if k == 3 and any(x in m for x in ("P11", "A_D", str(P6)))) + ";",
              "P6:", p6(r))

    for name, (title, bkw) in CONTROLS.items():
        bc = build(**bkw)
        co, _ = t.opened(bc)
        c = noted(co)
        badc = verdict(c, dusts)
        print(f"\n== {name}: {title}")
        print("   opening:", dp.same_opening(bc), "| open state: A_D", t.at(co, "A_D")[1:], "powered by",
              [x for _, x in power_sources(co, A_D)] if co.get(A_D).n != "air" else "-", "| DP", co.get(f.DP).p["power"])
        print("   close:", "; ".join(told(c, "c", lambda m: any(x in m for x in ("A_D", "P11", "RB_D", str(LIT), str(R_D))))) or "nothing moves at DP")
        print("   ->", "FAILS: " + "; ".join(badc[:5]) if badc else "done")
    hf = noted(mine, before={2: lambda x: x.tickers.sort(key=lambda be: be.pos != HEAD)})
    print("\n== what-if (no block does this): A_D's head ticked ahead of RB_D in phase j of c2. A push adds the pushed block's "
          "block entity first and the head's last (sim.py move_blocks), and phase j runs them in that order")
    print("   close:", "; ".join(told(hf, "c", lambda m: any(x in m for x in ("A_D", "P11", str(LIT))))))
    print("   ->", "FAILS: " + "; ".join(verdict(hf, dusts)[:3]) if verdict(hf, dusts) else "done")
    print("\n== ctl 10: the input off n ticks after it went on (R_D turns on at t8 d; trigger.py's feed is armed at t10 j)")
    out = {}
    for n in (8, 9, 10, 11, 12, 16):
        on, _ = t.opened(b, ticks=n)
        out[n] = "FAILS" if t.verdict_c0(noted(on, IDLE[:2])) or verdict(noted(on), dusts) else "done"
    print("   stages 0 to 2:", out)

    stray = copy.deepcopy(mine)
    for blk in (t.GLASS, AIR):
        stray.cmd_set((-3, 5, 3), blk)
    stray = noted(stray, [[] for _ in range(6)], first=0)
    print("\n== cost: A_D is armed in the open state. A glass block set and cleared above it there (one stray update), then 6 ticks:")
    print("   ", "; ".join(told(stray, "s")), "->", {n: t.at(stray, n)[0] for n in ("RB_D", "S", "Q")}, "DP", stray.get(f.DP).p["power"])

    print("\n== P6 spat as well? dp_off_search.txt: one more block in the 36 free cells, 1 of 576 passes; two more, 455 of 161280, "
          "449 of them with that one block and 6 without. Set into the open state they pass; built, none does")
    silent = copy.deepcopy(mine)
    silent.cmd_set_silent(ON_P11, t.DUST)
    sw = noted(silent)
    print(f"   the one, a dust at {ON_P11}, on P11 and beside DP: set into the open state, P6:", p6(sw) + ";", "->",
          "FAILS: " + "; ".join(verdict(sw, dusts)) if [x for x in verdict(sw, dusts) if "P6" not in x and "TL" not in x] else
          "the rest of stage 2 as above: DP's change reaches the dust and the dust's reaches P6, so P6 is queued at c2 j with P11")
    bd = build(swap={ON_P11: t.DUST})
    cd_, _ = d.make_world(bd)
    lit = noted(silent, IDLE[:4])
    print("   built:", "opening:", dp.same_opening(bd) + ";", "closed state: DP", cd_.get(f.DP).p["power"], "(RB11 at (-2,4,1) is beside it);",
          "lit, it powers", sorted(st.p["id"] for c, st in lit.b.items() if st.n in ("piston", "sticky_piston")
                                   and any(q == ON_P11 for _, q in power_sources(lit, c))))
    print("   and it stands on P11, whose top is a full face only while it is retracted: the game drops such a dust when the "
          "piston extends [INFERRED]; the simulator has no rule for support")
    for title, sw_ in PAIRS.items():
        bp = build(swap=sw_)
        cp, mv = d.make_world(bp)
        po, _ = t.opened(bp)
        badp = verdict(noted(po), dusts)
        print(f"   {title}: built, moved during load:", [m.split("@")[0] for m in mv] or "none", "| opening:", dp.same_opening(bp),
              "| open state: A_D", "out" if t.at(po, "A_D")[2] else "in", "RB_D", t.at(po, "RB_D")[0], "DP", po.get(f.DP).p["power"],
              "| close ->", "FAILS: " + "; ".join(badp[:2]) if badp else "done")
    relay = copy.deepcopy(mine)
    for c, blk in PAIRS[RELAY].items():
        relay.cmd_set_silent(c, blk)
    rw = noted(relay)
    print("   the last of them set into the open state, where N_X is powered by Q_D and not updated (built, R_D's turning on at t8 d "
          "updates and fires it):")
    print("     ", "; ".join(told(rw, "c", lambda m: any(x in m for x in ("A_D", "N_X", "D_X", "P11", "P6@", str(R_D))))))
    print("      what it shows: an update of A_D at c2 g, after R_D is off, spits RB_D a tick early, so P11 and P6 are out in c2; and a "
          "piston pushed over the source cell at c0 lands at c2 j beside RB11, which powers it, and pushes RB_D down at c3: both spat. "
          "RB_D ends at", t.at(rw, "RB_D")[0], "and D_X out at", t.at(rw, "D_X")[0])
