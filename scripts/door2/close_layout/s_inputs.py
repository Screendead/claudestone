"""The S feed's inputs, stage 5 of the close, from blocks (door coords): the last commands are gone and the close
runs from the one falling input with no command after it. Thirteen blocks on top of p10_v.py's build, and three
of the S feed's come out; design_c's opening, the close feeds, the trigger chain, DP's seven and p10_v's two are
unchanged. Everything printed is COMPUTED on the simulator; nothing here ran on a server.

Drive   C of s_feed.py, not A: F_S pushes RB_F and stays out, RB_F lands at (1,5,1), F_S's release pulls it home.
        Nothing is spat and nothing pulls RB_F aside, so G_S (3,5,1), its head (2,5,1) and its hold HOLD_G (3,6,1)
        are taken out: RB_F is never parked at (2,5,1), where it QC-powered P7, and needs no return.
Source  RB_ST, trigger.py's redstone block. K_T's push in c0 leaves it at (2,8,0), where it lands at c2 j and
        rests until its return; in the closed state it is at (3,7,0) and in the open state at (2,7,0).
Feed    R_F, a 4-tick repeater at (2,8,1) facing north on glass, reads RB_ST and turns on at c10 d. Dust D_1
        (2,8,2) on glass and D_2 (1,8,2) on a stone carry it to D_F (1,7,3), one step down from D_2 on stone Q_F
        (1,6,3), which is above F_S: the T feed's pattern (DT on FT). D_F's change updates F_S, two below it.
        Eight of the 13 work (R_F, D_1, D_2, D_F, R_C, Q_C, A_C, C_F); five carry them.
On      c10 g: F_S extends. RB_F lands at c12 j and lights DS; S is moving in (c11 g to c13 j), so T's push
        fails. S lands on the lit cell at c13 j and extends at c14.
Cut     R_C, a 1-tick repeater at (0,8,2) facing east on glass, reads D_2 and powers stone Q_C (-1,8,2) at
        c12 d. A_C, a sticky piston at (-1,8,3) facing east beside Q_C, pushes stone C_F from (0,8,3) to (1,8,3),
        the cell above D_F and beside D_2. C_F lands at c14 j and cuts the step, as C_cut cuts NV in the opening:
        D_F is dark in that phase and its change updates F_S.
Off     c15 g: F_S retracts and pulls RB_F, a moving block at once: DS 0, S is updated and spat one tick after
        its extension, C real at (1,1,0), (1,2,0) free. RB_F and F_S are home at c17 j.
After   R_F and R_C stay on and A_C out while RB_ST is at (2,8,0): the feed is cut, not off. When RB_ST leaves
        (its return, not designed; taken out by command below), R_F turns off 8 gt later, R_C 2 gt after it, and
        A_C pulls C_F back beside a dark D_2: the 13 blocks are as in the open state, nothing of them to return.
Ticks   F_S may extend at c9 or c10 and must be released at c14 (behind S's event), c15 or c16 (drive C by
        command, below). R_F at 4 ticks is the only delay that gives c10 from RB_ST's landing; R_C at 1 tick puts
        the release at c15, at 2 ticks at c17, where S pulls C back.

Not controls: the glass under R_F, D_1 and R_C and the stone Q_F under D_F (the simulator does not drop an
unsupported dust or repeater). Q_F may be glass: D_F, two above F_S, is a QC source of F_S by itself. The stone
under D_2 must conduct: on glass D_F does not read D_2 down the step (ctl 5).
Run from the repo root (sim; replay-only):
python -m scripts.door2.close_layout.s_inputs > scripts/door2/close_layout/s_inputs.txt"""
import copy
from scripts.door2.close_layout import feeds as f, s_feed as s, trigger as t, dp, dp_off as o, p10_v as pv
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, DIRS

R_F, D_1, D_2, D_F, Q_F = (2, 8, 1), (2, 8, 2), (1, 8, 2), (1, 7, 3), (1, 6, 3)
R_C, Q_C, A_C, C_F, CUT = (0, 8, 2), (-1, 8, 2), (-1, 8, 3), (0, 8, 3), (1, 8, 3)       # C_F rests at C_F and cuts at CUT
G_R, G_1, S_2, G_C = (2, 7, 1), (2, 7, 2), (1, 7, 2), (0, 7, 2)                         # under R_F, D_1, D_2 and R_C
RB_UP = t.UP                                                                            # RB_ST's cell from c2 j
GONE = (s.G_S, s.G_HEAD, s.HOLD_G)


def rep(facing, delay):
    return B("repeater", facing=facing, delay=delay, powered=False)


MINE = {G_R: t.GLASS, R_F: rep("north", 4), G_1: t.GLASS, D_1: t.DUST, S_2: t.STONE, D_2: t.DUST, Q_F: t.STONE, D_F: t.DUST,
        G_C: t.GLASS, R_C: rep("east", 1), Q_C: t.STONE, A_C: t.pis("sticky_piston", "east", "A_C"), C_F: B("stone", id="C_F")}
PARTS = {R_F: "R_F", D_1: "D_1", D_2: "D_2", D_F: "D_F", R_C: "R_C", Q_C: "Q_C", A_C: "A_C", C_F: "C_F"}     # the eight that work
SHOW = ("EXTEND", "RETRACT", "cancel", "failed", "dropped", f"wire {D_1}", f"wire {D_F}", f"wire {s.DS}", f"repeater {R_F}",
        f"repeater {R_C}", f"land rb@{RB_UP}", f"land rb@{s.LIT}", f"land rb@{s.RB_F}", f"land stone@{CUT}", f"land stone@{C_F}",
        f"land sticky_piston@{pv.S_CELL}", f"land quartz@(1, 1, 0)")
LAST = 20                                                           # the runs end after c20


def build(drop=(), swap=None, hold=False, **kw):
    """p10_v.py's build with the 13 blocks and without G_S, its head and its hold (`hold`: with them); `drop`
    leaves cells out, `swap` replaces or adds some."""
    b = pv.build(drop=drop, swap={**MINE, **(swap or {})}, **kw)
    for c in () if hold else GONE:
        del b.b[c]
    return b


def idle(last=LAST):
    return pv.idle(last)


def by_command(on, off, last=LAST):
    """idle() with drive C of s_feed.py by command: F_S on before tick `on`, off before tick `off`."""
    out = idle(last)
    out[on + 1].append(s.ON)
    out[off + 1].append(s.OFF)
    return out


class Noted(pv.Noted):
    """p10_v's Noted with this step's lines, each update of F_S with whether F_S is powered then, and the pistons
    that a change of DS or of the feed's dust updates."""
    feed = 0

    def L(self, msg):
        World.L(self, msg)
        if any(x in msg for x in SHOW):
            self.lines.append((self.tick_no, self.phase, self.cur if self.phase == "g" and self.seen is not None else None, msg))

    def check_extend(self, p):
        if p == s.F_S and self.get(p).n == "sticky_piston":
            self.fed.append((self.tick_no, self.phase, bool(self.neighbor_signal(p, DIRS["north"]))))
        for n, on in (("DS", self.storm), ("feed", self.feed)):
            if on and self.tick_no >= 1:
                self.reached.setdefault((n, self.tick_no), set()).add(self.get(p).p.get("id", str(p)))
        pv.Noted.check_extend(self, p)

    def wire_update(self, p):
        self.feed += p in (D_1, D_2, D_F)
        pv.Noted.wire_update(self, p)
        self.feed -= p in (D_1, D_2, D_F)


def noted(w, ticks=None, first=-1, before=None, **kw):
    """p10_v.noted with this module's Noted: a copy of w taken through ticks (each: its commands, then the tick),
    with the shown lines, F_S's updates, the power on the waiting V and S and (blocks, moving cells) after each
    tick. `before` {tick number: function of the world} acts ahead of that tick (sim only)."""
    w = copy.deepcopy(w)
    w.__class__ = Noted
    w.reverse, w.ia_last = kw.get("reverse", False), kw.get("ia_last", False)
    w.lvl, w.order, w.seen, w.after, w.said, w.lines, w.noted, w.fed, w.power, w.frames = {}, [], None, None, [], [], [], [], [], []
    w.reached = {}
    for k, cmds in enumerate(idle() if ticks is None else ticks):
        w.log.clear()
        w.tick_no = k + first
        for c, blk in cmds:
            w.cmd_set(c, blk)
        if before and w.tick_no in before:
            before[w.tick_no](w)
        w.tick()
        w.power.append((w.tick_no, pv.waiting(w)))
        w.frames.append((dict(w.b), set(w.be)))
    return w


NEED_END = {**{n: x for n, x in pv.NEED_END.items() if n != "G_S"}, "RB_F": (s.RB_F, "real", None)}


def verdict_end(w, cut=True):
    """stage 5 done from blocks: p10_v.verdict_end with RB_F home, DS and D_F dark and, with `cut`, C_F on the step."""
    need = {**NEED_END, **({"A_C": (A_C, "real", True), "C_F": (CUT, "real", None)} if cut else {})}
    bad = [f"{n} {t.at(w, n)}" for n, want in need.items() if t.at(w, n) != want]
    bad += [f"(1,2,0) {w.get((1, 2, 0))}"] * (w.get((1, 2, 0)).n != "air")
    return bad + [f"{n} {w.get(c).p['power']}" for n, c in (("DS", s.DS), ("D_F", D_F)) if w.get(c).p.get("power")]


def verdicts(mine, dusts, **kw):
    """every stage of the close from the input in the open state `mine`, no command: (stages 0 to 2, stages 3 and
    4 after c13, stage 5 after c`LAST`), each a list of what is wrong."""
    early = t.verdict_c0(noted(mine, idle(0), **kw)) + o.verdict(noted(mine, idle(6), **kw), dusts)
    return early, pv.verdict34(noted(mine, idle(13), **kw), dusts), verdict_end(noted(mine, **kw))


def per_tick(w, first=-1, last=LAST):
    return pv.per_tick(w, first, last)


def levels(w, cells=(D_1, D_2, D_F, s.DS)):
    return ", ".join(f"{PARTS.get(c, 'DS')} {w.get(c).p['power']}" for c in cells)


def state(w):
    """the 13 blocks' cells and the cut cell, as the world has them."""
    return {c: w.get(c) for c in list(MINE) + [CUT]}


# name: (title, build keywords)
CONTROLS = {
    "ctl 1": ("no R_F: nothing reads RB_ST", dict(drop=(R_F,))),
    "ctl 2": ("R_F at 3 ticks: every tick of the feed two early, and F_S pulls RB_F home at c13 g, before S lands (c13 j)",
              dict(swap={R_F: rep("north", 3)})),
    "ctl 3": ("no C_F: A_C pushes nothing, the step is never cut", dict(drop=(C_F,))),
    "ctl 4": ("R_C at 2 ticks: C_F lands at c16 j and F_S is released at c17, three ticks after S's extension",
              dict(swap={R_C: rep("east", 2)})),
    "ctl 5": ("glass under D_2: D_F does not read D_2 down the step", dict(swap={S_2: t.GLASS})),
    "ctl 6": ("a dust in R_F's place (no delay): the feed is lit when RB_ST lands, c2 j, and T fires into the empty (1,3,0)",
              dict(swap={R_F: t.DUST})),
    "ctl 7": ("R_C turned round (facing west): it reads Q_C and drives D_2", dict(swap={R_C: rep("west", 1)})),
}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    b, b0 = build(), pv.build()
    base, _ = t.opened(b0)
    mine, moved = t.opened(b)
    cl, cl0 = d.make_world(b)[0], d.make_world(b0)[0]
    dusts = [c for c, st in mine.b.items() if st.n == "redstone_wire"]
    kinds = [st.n for st in MINE.values()]
    print(f"added: {len(MINE)} blocks ({kinds.count('repeater')} repeaters, {kinds.count('redstone_wire')} dust, 1 sticky piston, "
          f"{kinds.count('stone')} stone, {kinds.count('glass')} glass); taken out: G_S, its head and HOLD_G; no stand-in, no command "
          "after the input")
    print("opening, p10_v's build vs this one, open-state differences:", f.diff(f.snapshot(base), f.snapshot(mine)) or "none")
    print("cell differences outside the added blocks and G_S's three cells:", s.cell_diff(base, mine, set(MINE) | set(GONE)),
          "| tick by tick, the door's pistons and the door plane:", dp.same_opening(b))
    rest, dust = pv.differing(cl0, cl, set(MINE) | set(GONE))
    print("moved during load:", moved or "none", "| closed state: R_F", "on" if cl.get(R_F).p["powered"] else "off", "| R_C",
          "on" if cl.get(R_C).p["powered"] else "off", "|", levels(cl), "| RB_ST", t.at(cl, "RB_ST")[0], "| F_S powered by",
          [c for _, c in power_sources(cl, s.F_S)] or "nothing", "| cells that differ from p10_v's closed state:", rest + dust or "none")
    wo = pv.opening_notes(b)
    wo.__class__ = Noted
    seen = set()
    wx, _ = d.make_world(b)
    wx.run(4)
    wx.cmd_set(f.DRIVER, t.RB)
    for _ in range(t.OPEN_TICKS):
        wx.tick()
        seen |= {c for c in MINE if wx.get(c) != cl.get(c)} | {c for c in list(MINE) + [CUT] if c in wx.be}
        seen |= {c for _, c in power_sources(wx, s.F_S)} | {c for _, c in power_sources(wx, A_C)}
    print("the opening: added cells that change or move, and power on F_S or A_C, at any tick:", sorted(seen) or "none",
          "| RB_ST after it:", t.at(mine, "RB_ST")[0])
    print("open state: R_F", "on" if mine.get(R_F).p["powered"] else "off", "| R_C", "on" if mine.get(R_C).p["powered"] else "off",
          "|", levels(mine), "| F_S", t.at(mine, "F_S"), "RB_F", t.at(mine, "RB_F")[:2], "A_C", t.at(mine, "A_C")[1:], "C_F", t.at(mine, "C_F")[0])
    print("pistons with an added cell among their power sources, closed and open state:",
          {st.p["id"]: sorted(c for _, c in power_sources(w, p) if c in MINE) for w in (cl, mine) for p, st in sorted(w.b.items())
           if st.n in ("piston", "sticky_piston") and any(c in MINE for _, c in power_sources(w, p))} or "none")
    cells = set(v.cumulative_cells(b)[0])
    print("box, opening:", s.box(cells))

    w, ref = noted(mine), pv.noted(base, idle())
    for blocks, _ in w.frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print(f"\n== the close from the input, no command: c-1 to c{LAST}")
    same = next((n for n in range(-1, LAST + 1) if per_tick(w)[n + 1] != per_tick(ref)[n + 1]), None)
    print(f"   c-1 to c{same - 1}: the piston events of p10_v's run with no command, tick by tick" if same else "   NO DIFFERENCE from p10_v's run")
    print("\n".join("   " + x for x in pv.told(w) if pv.tick_of(x) >= 2 and (pv.tick_of(x) >= 8 or "(2, 8, 0)" in x)))
    bad02, bad34, bad5 = verdicts(mine, dusts)
    print("   stages 0 to 2 ->", "FAILS: " + "; ".join(bad02) if bad02 else
          "done as in p10_v's run: stages 0 and 1 in c0, P11 out and spat in c3, S real at (0,3,0), RB_D and A_D home")
    print("   stages 3 and 4, after c13 ->", "FAILS: " + "; ".join(bad34) if bad34 else
          "done as in p10_v's run: P10 out at c8, V out at c11, S real at (1,3,0), retracted; no dust lost; nothing powers V or S "
          "where they wait; P8's dust 0")
    print(f"   stage 5, after c{LAST} ->", "FAILS: " + "; ".join(bad5) if bad5 else
          "done: S real at (1,3,0), retracted; C real at (1,1,0); (1,2,0) air; T, P12, P11 in; V and P10 out; SP, TL, Q, TM, P8 "
          "where the close needs them; RB_F home at (1,5,2), F_S in; DS and D_F 0; A_C out, C_F on the step; P7 out over TR at (2,2,0)")
    print("   F_S:", pv.fired(w, "F_S") + ";", "S:", pv.fired(w, "S") + ";", "A_C:", pv.fired(w, "A_C") + ";", "W_T:", pv.fired(w, "W_T"))
    print("   F_S's updates:", ", ".join(dict.fromkeys(f"c{k}{ph} " + ("powered" if on else "not powered") for k, ph, on in w.fed if k >= 1)))
    at = {k: noted(mine, idle(k)) for k in (9, 10, 12, 13, 14)}
    print("   levels after c9:", levels(at[9]), "| c10:", levels(at[10]), "| c12:", levels(at[12]), "| c13:", levels(at[13]), "| c14:",
          levels(at[14]), f"| c{LAST}:", levels(w))
    print("   block events from c1 on whose updates reach F_S:", [f"c{k} {n}" for k, _, n, _, sn in w.order if s.F_S in sn and k >= 1],
          "| T while DS is lit:", "; ".join(x for x in pv.told(w, "c", lambda m: " T@" in m or str((1, 4, 0)) in m) if pv.tick_of(x) >= 10) or
          "no event")
    print("   pistons updated by a change of DS:", "; ".join(f"c{k} {sorted(ids)}" for (n, k), ids in sorted(w.reached.items()) if n == "DS"),
          "| of D_1, D_2 or D_F:", "; ".join(f"c{k} {sorted(ids)}" for (n, k), ids in sorted(w.reached.items()) if n == "feed"))
    r0 = pv.noted(base, pv.staged(last=LAST))
    rest, dust = pv.differing(r0, w, set(MINE) | {CUT})
    print("   end state against p10_v.py's run, where commands drive stage 5 (drive A): cells that differ outside the 13 blocks and the cut cell:")
    print("     ", "; ".join(rest) or "none")
    print("      dust levels that differ:", ", ".join(f"{c} {r0.get(c).p['power']}->{w.get(c).p['power']}" for c in dust) or "none")
    print("   box, opening + close through stage 5:", s.box(cells))

    print("\n== order (must pass): against the run above")
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)),
                     ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("both", dict(reverse=True, ia_last=True))):
        x = noted(mine, **kw)
        print(f"   {name}:", "FAILS" if any(verdicts(mine, dusts, **kw)) else "stages 0 to 4 done, stage 5 done;", "piston events of each tick",
              "the same set;" if per_tick(x) == per_tick(w) else "DIFFER;", "end-state cells", "the same" if s.cell_diff(w, x) == "none" else "DIFFER")

    for name, (title, bkw) in CONTROLS.items():
        bc = build(**bkw)
        cc, mv = d.make_world(bc)
        co, _ = t.opened(bc)
        c = noted(co)
        badc = verdict_end(c)
        print(f"\n== {name}: {title}")
        print("   moved during load:", [m.split("@")[0] for m in mv] or "none", "| opening:", dp.same_opening(bc), "| open state: F_S",
              "out" if t.at(co, "F_S")[2] else "in", "RB_F", t.at(co, "RB_F")[0], "D_F", co.get(D_F).p.get("power"))
        print("   close:", "; ".join(x for x in pv.told(c, "c", lambda m: any(n in m for n in (" F_S@", " A_C@", " S@", " T@", str(R_F), str(R_C),
                                                                                               f"land rb@{s.LIT}", f"land stone@{CUT}")))
                                     if pv.tick_of(x) >= 1) or "nothing moves at F_S")
        print("   ->", "FAILS: " + "; ".join(badc[:5]) if badc else "done")

    print("\n== each of the eight working blocks left out: stage 5")
    print("  ", ", ".join(f"{n} " + ("FAILS" if verdict_end(noted(t.opened(build(drop=(c,)))[0])) else "done") for c, n in PARTS.items()),
          "| Q_F as glass (D_F a QC source of F_S by itself):",
          "FAILS" if verdict_end(noted(t.opened(build(swap={Q_F: t.GLASS}))[0])) else "done")
    print("\n== the two delays, R_F 1 to 4 ticks with R_C at 1, and R_C 1 to 4 ticks with R_F at 4: stage 5")
    print("   R_F:", ", ".join(f"{n} " + ("FAILS" if verdict_end(noted(t.opened(build(swap={R_F: rep('north', n)}))[0])) else "done") for n in (1, 2, 3, 4)),
          "| R_C:", ", ".join(f"{n} " + ("FAILS" if verdict_end(noted(t.opened(build(swap={R_C: rep('east', n)}))[0])) else "done") for n in (1, 2, 3, 4)))
    print("\n== why c10 and c15: drive C by command in p10_v's build with G_S and its hold out (SRC_F (1,6,3) set before the first tick, "
          "cleared before the second)")
    plain, _ = t.opened(build(drop=tuple(MINE)))
    for on in (8, 9, 10, 11):
        print(f"   F_S out from c{on}, released at c13 / c14 / c15 / c16 / c17:",
              " / ".join("FAILS" if verdict_end(noted(plain, by_command(on, off)), cut=False) else "done" for off in (13, 14, 15, 16, 17)))

    hb = build(hold=True)
    ho, _ = t.opened(hb)
    h = noted(ho)
    print("\n== with G_S, its head and HOLD_G left in (HOLD_G never removed): opening", dp.same_opening(hb) + ";", "piston events of each tick",
          "the same set;" if per_tick(h) == per_tick(w) else "DIFFER;", "end-state cells outside G_S's three:", s.cell_diff(w, h, set(GONE)))

    gone = noted(mine, idle(44), before={24: lambda x: x.cmd_set(RB_UP, AIR)})
    print("\n== after the close (what-if; RB_ST's return is not designed): RB_ST taken out of (2,8,0) by command before c24, to c44")
    print("\n".join("   " + x for x in pv.told(gone) if pv.tick_of(x) >= 24))
    print(f"   RB_ST's neighbours after c{LAST}:", ", ".join(f"{c} " + (PARTS.get(c) or w.get(c).p.get("id") or w.get(c).n) for c in
                                                             [tuple(a + b_ for a, b_ in zip(RB_UP, x)) for x in DIRS.values()]),
          "((2,9,0) is outside the box)")
    print("   the 13 blocks and the cut cell against the open state:", "the same" if state(gone) == state(mine) else
          {c: (mine.get(c), gone.get(c)) for c in state(mine) if mine.get(c) != gone.get(c)}, "|", levels(gone), "| F_S", pv.fired(gone, "F_S"),
          "| A_C", pv.fired(gone, "A_C"))
    plain_a, _ = t.opened(build(swap={A_C: t.pis("piston", "east", "A_C")}))
    pa = noted(plain_a, idle(44), before={24: lambda x: x.cmd_set(RB_UP, AIR)})
    print("   ctl 8: A_C not sticky: stage 5", "FAILS" if verdict_end(noted(plain_a)) else "done;", "after RB_ST is taken out: A_C",
          pv.fired(pa, "A_C") + ",", "C_F at", t.at(pa, "C_F")[0], "-> the step stays cut for the next close")

    print("\n== ctl 9: the input off n ticks after it went on (trigger.py's feed is armed at t10 j, R_D on at t8 d)")
    res = {}
    for n in (8, 9, 10, 11, 12, 16):
        on, _ = t.opened(b, ticks=n)
        res[n] = "FAILS" if any(verdicts(on, dusts)) else "done"
    print("   stages 0 to 5:", res)
