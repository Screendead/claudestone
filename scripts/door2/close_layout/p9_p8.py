"""P7, P9 and P8, the last stages of the close, from blocks (door coords): the close runs from the one falling
input to the closed door's plane with no command. Nine blocks on top of s_inputs.py's build, and one glass block
of design_c becomes a stone; design_c's opening is the same at every tick, and every earlier step's blocks are
unchanged. Everything printed is COMPUTED on the simulator; nothing here ran on a server.

Order   The plan closes the top row as 1 P9 (TM to (2,2,0)), 6 P8 (Q down), 7 Q H2 (TM on to (1,2,0)), 8 P7 (TR
        down), which needs P7 held in until Q has fired. P7 is not held: NA's relight fires it at c3 and TR lands
        at (2,2,0) at c5 j. And no block feeds P9: it has not fired in any run so far. So P9 fires after stage 5
        instead and pushes two, TM from (3,2,0) to (2,2,0) and TR on to (1,2,0), the cell S's 0-tick frees at
        c15. Then P8 pushes Q down to (3,2,0). Q never fires and P7 needs no block. TM and TR end in each other's
        cells; they are the same block, and the door plane is the closed door's.
Pulse   R_X, a 2-tick repeater at (2,5,1) facing west on glass G_X (2,4,1), reads (1,5,1), where RB_F stands from
        c12 j to c15 g. It turns on at c16 d and, its input gone, off at c20 d: a repeater's pulse is at least
        its delay long.
Shuttle A_9, a sticky piston at (3,4,1) facing east, QC-powered by R_X through (3,5,1), the cell above it. In
        front of it stands RB9, the opening's redstone block, which Z9 pushes up to (4,4,1) at t3. A_9 extends at
        c16 and RB9 lands at (5,4,1) at c18 j, beside LY's dusts (5,4,2) and (6,4,1); A_9 pulls it back at c20
        and both are home at c22 j.
Wire    LY, the opening's dust from RB_Y to Z_S, dark since t0, runs from there to P9. Its dust (6,4,1) stands on
        glass (6,3,1), which passes nothing down to LY's dust (6,3,0): S_L, a stone in that cell, does. LY reads
        15 at (6,4,1) and 14 at (6,3,0) from c18 j to c20 g.
P9      R_9, a 1-tick repeater at (5,3,0) facing east on glass G_9 (5,2,0), reads LY's dust (6,3,0) and points
        into (4,3,0), the cell above P9: on at c20 d, off at c22 d. P9 extends at c20 and pushes TM and TR; at c22
        it is spat: TM real at (2,2,0) at once, TR lands at (1,2,0) at c22 j.
P8      R_8, a 1-tick repeater at (3,5,-1) facing north on design_c's stone (3,4,-1), reads D_8, a dust at
        (3,5,-2) on glass G_8 (3,4,-2), which reads NA's dust (2,4,-2) up the step, and points into (3,5,0), the
        cell above P8. It is on from c4 d, and in the closed state, where it turns off at t2 d ahead of NV's cut,
        as R_V does. O_8, an obsidian block at (3,-1,0) under the static block (3,0,0), stops P8 until P9 has
        fired: at c4 d P8 could push Q, TM, R and the static block down if its event ran ahead of P5's.
Wake    A_9 stands south of P8. Its landing at c22 j updates P8, powered and by then free: P8 extends at c23 and
        Q lands at (3,2,0) at c25 j.
After   A_9, RB9, R_X and LY are as in the open state and R_9 is off. R_8 stays on while NA is lit and holds P8
        out whatever NV does. When LY relights (RB_Y's return) R_9 powers P9 behind Q, as RB9 does in the closed
        door.

Not controls: G_9 carries R_9 (the simulator does not drop an unsupported repeater) and may be any block. The
glass under R_X and the glass under D_8 must not conduct (ctl 8 and 9).
Run from the repo root (sim; replay-only):
python -m scripts.door2.close_layout.p9_p8 > scripts/door2/close_layout/p9_p8.txt"""
import copy, functools
from scripts.door2.close_layout import feeds as f, s_feed as s, trigger as t, dp_off as o, p10_v as pv, s_inputs as si
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, DIRS

G_X, R_X, A_9 = (2, 4, 1), (2, 5, 1), (3, 4, 1)
S_L, G_9, R_9 = (6, 3, 1), (5, 2, 0), (5, 3, 0)
O_8, G_8, D_8, R_8 = (3, -1, 0), (3, 4, -2), (3, 5, -2), (3, 5, -1)
RB9_OPEN, RB9_OUT, RB9_CLOSED = (4, 4, 1), (5, 4, 1), (4, 3, 1)       # RB9 in the open state, pushed by A_9, in the closed state
LY = ((7, 4, -2), (7, 4, -1), (6, 3, -1), (6, 3, 0), (6, 4, 1), (6, 4, 2), (5, 4, 2), (4, 5, 2), (3, 4, 2), (3, 4, 3))   # from RB_Y to Z_S
LY_9, LY_UP = (6, 3, 0), (6, 4, 1)                                     # the dust R_9 reads, and the one on S_L
P7, P8, P9, Q_WAIT, Q_CELL = s.P7, (3, 4, 0), (4, 2, 0), (3, 3, 0), (3, 2, 0)
P5 = (4, 1, 0)
PISTONS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11", "P12", "Q", "S", "T", "V")
PLANE = [(x, y, 0) for x in range(-1, 4) for y in range(-1, 4)]


def rep(facing, delay, on=False):
    return B("repeater", facing=facing, delay=delay, powered=on)


MINE = {G_X: t.GLASS, R_X: rep("west", 2), A_9: t.pis("sticky_piston", "east", "A_9"), S_L: t.STONE, G_9: t.GLASS,
        R_9: rep("east", 1, True), O_8: B("obsidian"), G_8: t.GLASS, D_8: t.DUST, R_8: rep("north", 1, True)}
PARTS = {R_X: "R_X", A_9: "A_9", S_L: "S_L", R_9: "R_9", O_8: "O_8", D_8: "D_8", R_8: "R_8"}       # the seven that work
SHOW = ("EXTEND", "RETRACT", "cancel", "failed", "dropped", f"repeater {R_X}", f"repeater {R_9}", f"repeater {R_8}",
        f"wire {LY_9}", f"wire {D_8}", f"land rb@{RB9_OUT}", f"land rb@{RB9_OPEN}", f"land sticky_piston@{A_9}",
        f"land sticky_piston@{Q_CELL}", f"land sticky_piston@{P9}", "land quartz@(1, 2, 0)", "land quartz@(2, 2, 0)")
LAST = 30                                                           # the runs end after c30


@functools.lru_cache(None)
def fixed():
    """s_inputs.py's build and every cell its opening occupies."""
    from scripts.door2 import volume as v
    b = si.build()
    return b, frozenset(v.cumulative_cells(b)[0])


def build(drop=(), swap=None):
    """s_inputs.py's build with the nine blocks and S_L in place of design_c's glass; `drop` leaves cells out (S_L:
    the glass stays), `swap` replaces or adds some."""
    b0, occ = fixed()
    b = copy.deepcopy(b0)
    assert b.b[S_L] == t.GLASS
    for p, st in {**MINE, **(swap or {})}.items():
        if p in drop:
            continue
        assert p == S_L or (p not in b0.b and p not in occ), p
        b.b[p] = st
        b.role[p] = "p9_p8"
    return b


def idle(last=LAST):
    return pv.idle(last)


class Noted(si.Noted):
    """s_inputs' Noted with this step's lines, each update of P8, P9 and A_9 while it is in with whether it is
    powered and whether it can push then, each update of P8 while it is out, and the pistons that a change of LY
    updates. `first` (tick, cell) puts that cell's block events queued in phase d of that tick ahead of the
    others (sim only)."""
    ly, first = 0, None

    def L(self, msg):
        World.L(self, msg)
        if any(x in msg for x in SHOW):
            self.lines.append((self.tick_no, self.phase, self.cur if self.phase == "g" and self.seen is not None else None, msg))

    def check_extend(self, p):
        st = self.get(p)
        if st.p.get("id") in self.woke and not st.p["extended"]:
            fdir = DIRS[st.p["facing"]]
            self.woke[st.p["id"]].append((self.tick_no, self.phase, bool(self.neighbor_signal(p, fdir)), self.resolve(p, fdir, True)[0]))
        elif st.p.get("id") == "P8":
            self.held.append((self.tick_no, self.phase, bool(self.neighbor_signal(p, DIRS["down"]))))
        if self.ly and self.tick_no >= 1:
            self.reached.setdefault(("LY", self.tick_no), set()).add(st.p.get("id", str(p)))
        si.Noted.check_extend(self, p)

    def wire_update(self, p):
        self.ly += p in LY
        si.Noted.wire_update(self, p)
        self.ly -= p in LY

    def repeater_tick(self, p):
        si.Noted.repeater_tick(self, p)
        if self.first and self.tick_no == self.first[0]:
            for key in [k for k in self.events if k[0] == self.first[1]]:
                self.events.move_to_end(key, last=False)


def noted(w, ticks=None, first=-1, before=None, ahead=None, **kw):
    """s_inputs.noted with this module's Noted: a copy of w taken through ticks (each: its commands, then the
    tick), with the shown lines, the updates of P8, P9 and A_9 and (blocks, moving cells) after each tick. `before`
    {tick number: function of the world} acts ahead of that tick, `ahead` is Noted.first (both sim only)."""
    w = copy.deepcopy(w)
    w.__class__ = Noted
    w.reverse, w.ia_last, w.first = kw.get("reverse", False), kw.get("ia_last", False), ahead
    w.lvl, w.order, w.seen, w.after, w.said, w.lines, w.noted, w.fed, w.power, w.frames = {}, [], None, None, [], [], [], [], [], []
    w.reached, w.woke, w.held = {}, {"P8": [], "P9": [], "A_9": []}, []
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


def bare(st):
    """a block without its label."""
    return st.n, tuple(sorted((k, x) for k, x in st.p.items() if k != "id"))


def verdict_end(w, cl, skip=()):
    """the door closed: what keeps the world from the loaded closed state `cl` in the door's pistons and the door
    plane (labels apart; `skip`: cells left out), and this step's blocks from their rest; empty when stages 6 and
    7 are done."""
    bad = [f"{n} {t.at(w, n)}" for n in PISTONS if t.at(w, n) != t.at(cl, n)]
    bad += [f"{c} {'moving' if c in w.be else w.get(c)}" for c in PLANE if c not in skip and (c in w.be or bare(w.get(c)) != bare(cl.get(c)))]
    bad += [f"{n} {t.at(w, n)}" for n, want in (("A_9", (A_9, "real", False)), ("RB9", (RB9_OPEN, "real", None))) if t.at(w, n) != want]
    bad += [f"{n} on" for n, c in (("R_X", R_X), ("R_9", R_9)) if w.get(c).p.get("powered")]
    bad += ["R_8 off"] * (w.get(R_8).p.get("powered") is False) + [f"LY {w.get(LY_9).p['power']}"] * bool(w.get(LY_9).p.get("power"))
    return bad + [f"moving at {sorted(w.be)}"] * bool(w.be)


def verdicts(mine, dusts, cl, **kw):
    """every stage of the close from the input in the open state `mine`, no command: (stages 0 to 2, stages 3 and
    4 after c13, stage 5 after c19 as s_inputs.py has it, stages 6 and 7 after c`LAST`), each a list of what is
    wrong."""
    early = t.verdict_c0(noted(mine, idle(0), **kw)) + o.verdict(noted(mine, idle(6), **kw), dusts)
    return early, pv.verdict34(noted(mine, idle(13), **kw), dusts), si.verdict_end(noted(mine, idle(19), **kw)), verdict_end(noted(mine, **kw), cl)


def per_tick(w, first=-1, last=LAST):
    return pv.per_tick(w, first, last)


def opening_against(b, skip, ref=None):
    """the opening of b beside that of s_inputs' build (or `ref`), tick by tick: the ticks at which the door's
    pistons or the door plane differ (O_8's own cell apart), and those at which any cell outside `skip` does,
    dust levels included."""
    wa, wb = d.make_world(ref or fixed()[0])[0], d.make_world(b)[0]
    for w in (wa, wb):
        w.run(4)
        w.cmd_set(f.DRIVER, t.RB)
    door, cells = [], []
    for k in range(t.OPEN_TICKS):
        wa.tick()
        wb.tick()
        door += [k - 1] * bool(set(f.diff(f.snapshot(wa), f.snapshot(wb))) - {O_8})
        cells += [k - 1] * any(p not in skip and wa.b.get(p) != wb.b.get(p) for p in set(wa.b) | set(wb.b))
    return door, cells


def same(ticks):
    return f"differ at t{ticks}" if ticks else "the same at every tick"


def levels(w, cells=(LY_UP, LY_9, D_8)):
    return ", ".join(f"{'D_8' if c == D_8 else 'LY ' + str(c)} {w.get(c).p['power']}" for c in cells)


def woke(w, name, since=1, until=LAST, tick="c"):
    """the updates of P8, P9 or A_9 while it is in: tick and phase, powered or not, free to push or blocked."""
    out = dict.fromkeys(f"{tick}{k}{ph} " + ("powered" if on else "not powered") + (", free" if ok else ", blocked")
                        for k, ph, on, ok in w.woke[name] if since <= k <= until)
    return "; ".join(out) or "none"


def opening_notes(b):
    """the opening of b from the closed state, noted; ticks are numbered as trigger.py numbers them (t-1 first)."""
    w, _ = d.make_world(b)
    w.run(4)
    w.cmd_set(f.DRIVER, t.RB)
    return noted(w, [[] for _ in range(t.OPEN_TICKS)])


def pulse(k, n):
    """before: P9 QC-powered from before tick k to before tick k + n, as R_9 powers it: a lit repeater set into
    R_9's cell without updates and taken out again, P9 updated each time (sim only; in the builds without R_9)."""
    def put(st):
        def act(x):
            x.cmd_set_silent(R_9, st)
            x.neighbor_changed(P9)
        return act
    return {k: put(rep("east", 1, True)), k + n: put(AIR)}


def top_row(w):
    return ", ".join(f"{n} {t.at(w, n)[0]}" + ("" if t.at(w, n)[1] == "real" else " moving") for n in ("TM", "TR", "C", "R")) + \
        f", P9 {'out' if t.at(w, 'P9')[2] else 'in'}, Q {t.at(w, 'Q')[0]}, P8 {'out' if t.at(w, 'P8')[2] else 'in'}"


# name: (title, build keywords)
CONTROLS = {
    "ctl 1": ("no R_X: nothing reads RB_F's cell", dict(drop=(R_X,))),
    "ctl 2": ("R_X at 1 tick: A_9 is home at c19 j, a tick ahead of P9's spit, and its landing finds P8 behind P9's head",
              dict(swap={R_X: rep("west", 1)})),
    "ctl 3": ("R_X at 3 ticks: RB9 stands beside LY for 4 gt, R_9's pulse is 4 gt and P9 pulls TM back", dict(swap={R_X: rep("west", 3)})),
    "ctl 4": ("A_9 not sticky: RB9 stays beside LY, R_9 stays on and P9 stays out", dict(swap={A_9: t.pis("piston", "east", "A_9")})),
    "ctl 5": ("design_c's glass left under LY's dust (6,4,1): LY's dust (6,3,0) stays dark", dict(drop=(S_L,))),
    "ctl 6": ("R_9 at 2 ticks: its pulse is 4 gt, and in the opening it is still on at t3, when P9 fires",
              dict(swap={R_9: rep("east", 2, True)})),
    "ctl 7": ("R_8 at 2 ticks: in the opening it is still on when NV is cut, and P8 retracts late", dict(swap={R_8: rep("north", 2, True)})),
    "ctl 8": ("a stone under R_X: DS, lit from c12 j, points into it and it powers A_9, which fires at c13", dict(swap={G_X: t.STONE})),
    "ctl 9": ("a stone under D_8: NA's dust (2,4,-2) and DQ's (4,4,-2) read D_8 down the step and are one net", dict(swap={G_8: t.STONE})),
}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    b, b0 = build(), fixed()[0]
    base, _ = t.opened(b0)
    mine, moved = t.opened(b)
    cl, cl0 = d.make_world(b)[0], d.make_world(b0)[0]
    dusts = [c for c, st in mine.b.items() if st.n == "redstone_wire"]
    assert sorted(LY) == sorted(c for c, r in b0.role.items() if r == "LY"), "LY"
    kinds = [st.n for c, st in MINE.items() if c != S_L]
    print(f"added: {len(kinds)} blocks ({kinds.count('repeater')} repeaters, {kinds.count('redstone_wire')} dust, 1 sticky piston, "
          f"{kinds.count('obsidian')} obsidian, {kinds.count('glass')} glass) and S_L, a stone in place of design_c's glass {S_L}; "
          "no stand-in, no command after the input")
    dif = f.diff(f.snapshot(base), f.snapshot(mine))
    door, cells_ = opening_against(b, set(MINE))
    print("opening, s_inputs' build vs this one, open-state differences:", str({k: x for k, x in dif.items() if k != O_8} or "none") +
          " but O_8's own cell" * (O_8 in dif))
    print("cell differences outside the added blocks:", s.cell_diff(base, mine, set(MINE)), "| tick by tick, the door's pistons and the door "
          "plane (O_8's cell apart):", same(door), "| every cell outside the added blocks, dust levels included:", same(cells_))
    rest, dust = pv.differing(cl0, cl, set(MINE))
    print("moved during load:", moved or "none", "| closed state: R_X", "on" if cl.get(R_X).p["powered"] else "off", "| R_9",
          "on" if cl.get(R_9).p["powered"] else "off", "| R_8", "on" if cl.get(R_8).p["powered"] else "off", "|", levels(cl), "| RB9",
          t.at(cl, "RB9")[0], "| P9 powered by", [c for _, c in power_sources(cl, P9)], "| P8 by", [c for _, c in power_sources(cl, P8)],
          "| A_9 by", [c for _, c in power_sources(cl, A_9)] or "nothing", "| cells that differ from s_inputs' closed state:", rest + dust or "none")
    wo, wo0 = opening_notes(b), pv.opening_notes(b0)
    print("the opening at the added blocks:", "; ".join(pv.told(wo, "t", lambda m: any(str(c) in m for c in (R_X, R_9, R_8, LY_9, D_8, A_9, P8, P9)))))
    print("   in s_inputs' build:", "; ".join(pv.told(wo0, "t", lambda m: any(str(c) in m for c in (P8, P9)))) or
          "P8 " + pv.fired(wo0, "P8").replace("c", "t") + "; P9 " + pv.fired(wo0, "P9").replace("c", "t"))
    print("   P8's updates while it is out, t2 and t3:", ", ".join(dict.fromkeys(f"t{k}{ph} " + ("powered" if on else "not powered") for k, ph, on in wo.held if 2 <= k <= 3)),
          "| A_9's updates:", woke(wo, "A_9", -1, tick="t"))
    seen = set()
    wx, _ = d.make_world(b)
    wx.run(4)
    wx.cmd_set(f.DRIVER, t.RB)
    for _ in range(t.OPEN_TICKS):
        wx.tick()
        seen |= {c for _, c in power_sources(wx, A_9)} | {c for c in (A_9, RB9_OUT) if c in wx.be}
    print("   power on A_9, and A_9 or the cell east of RB9 moving, at any tick of the opening:", sorted(seen) or "none", "| RB9 after it:",
          t.at(mine, "RB9")[:2], "(pushed by Z9; its landing updates A_9)")
    print("open state: R_X", "on" if mine.get(R_X).p["powered"] else "off", "| R_9", "on" if mine.get(R_9).p["powered"] else "off", "| R_8",
          "on" if mine.get(R_8).p["powered"] else "off", "|", levels(mine), "| A_9", t.at(mine, "A_9")[1:], "| P8", t.at(mine, "P8"), "Q",
          t.at(mine, "Q")[0], "P9", t.at(mine, "P9")[1:], "TM", t.at(mine, "TM")[0], "TR", t.at(mine, "TR")[0])
    print("pistons with an added cell among their power sources: closed state",
          {st.p["id"]: sorted(c for _, c in power_sources(cl, p) if c in MINE) for p, st in sorted(cl.b.items())
           if st.n in ("piston", "sticky_piston") and any(c in MINE for _, c in power_sources(cl, p))} or "none", "| open state",
          {st.p["id"]: sorted(c for _, c in power_sources(mine, p) if c in MINE) for p, st in sorted(mine.b.items())
           if st.n in ("piston", "sticky_piston") and any(c in MINE for _, c in power_sources(mine, p))} or "none")
    cells = set(v.cumulative_cells(b)[0])
    print("box, opening:", s.box(cells))

    w, ref = noted(mine), si.noted(base, idle())
    for blocks, _ in w.frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print(f"\n== the close from the input, no command: c-1 to c{LAST}")
    differ = next((n for n in range(-1, LAST + 1) if per_tick(w)[n + 1] != per_tick(ref)[n + 1]), None)
    print(f"   c-1 to c{differ - 1}: the piston events of s_inputs' run, tick by tick" if differ else "   NO DIFFERENCE from s_inputs' run")
    print("\n".join("   " + x for x in pv.told(w) if pv.tick_of(x) >= 12 or any(str(c) in x for c in (D_8, R_8, P7))))
    bad02, bad34, bad5, bad67 = verdicts(mine, dusts, cl)
    print("   stages 0 to 2 ->", "FAILS: " + "; ".join(bad02) if bad02 else
          "done as in s_inputs' run: stages 0 and 1 in c0, P11 out and spat in c3, S real at (0,3,0), RB_D and A_D home")
    print("   stages 3 and 4, after c13 ->", "FAILS: " + "; ".join(bad34) if bad34 else
          "done as in s_inputs' run: P10 out at c8, V out at c11, S real at (1,3,0), retracted; no dust lost; nothing powers V or S "
          "where they wait; P8's dust 0")
    print("   stage 5, after c19 ->", "FAILS: " + "; ".join(bad5) if bad5 else
          "done as in s_inputs' run: S real at (1,3,0), retracted; C real at (1,1,0); (1,2,0) air; RB_F home, F_S in; TM at (3,2,0), Q at "
          "(3,3,0), P8 in; P7 out over TR at (2,2,0)")
    print(f"   stages 6 and 7, after c{LAST} ->", "FAILS: " + "; ".join(bad67) if bad67 else
          "done: the door's sixteen pistons where the closed door has them and in its state; the door plane the closed door's, cell for "
          "cell, labels apart; A_9 in, RB9 at (4,4,1); R_X and R_9 off, R_8 on, LY 0; nothing moving")
    print("   P7:", pv.fired(w, "P7") + ";", "A_9:", pv.fired(w, "A_9") + ";", "P9:", pv.fired(w, "P9") + ";", "P8:", pv.fired(w, "P8") + ";",
          "Q:", pv.fired(w, "Q") + ";", "after c" + str(LAST) + ":", top_row(w))
    print("   P9's updates while it is in:", woke(w, "P9", 12))
    print("   P8's updates while it is in:", woke(w, "P8", 2))
    at = {k: noted(mine, idle(k)) for k in (17, 18, 19, 20, 22)}
    print("   levels after c17:", levels(at[17]), "| c18:", levels(at[18]), "| c19:", levels(at[19]), "| c20:", levels(at[20]), f"| c{LAST}:",
          levels(w), "| LY after c18, from RB_Y's end to Z_S's:", ", ".join(str(at[18].get(c).p["power"]) for c in LY))
    print("   pistons updated by a change of LY:", "; ".join(f"c{k} {sorted(ids)}" for (n, k), ids in sorted(w.reached.items()) if n == "LY"),
          "| by a change of DS (s_inputs' count):", "; ".join(f"c{k} {sorted(ids)}" for (n, k), ids in sorted(w.reached.items()) if n == "DS"))
    labels = sorted(f"{c}: {cl.get(c).p['id']} there, {w.get(c).p['id']} here" for c in PLANE if bare(w.get(c)) == bare(cl.get(c)) and w.get(c) != cl.get(c))
    print("   door plane against the loaded closed state: labels that differ:", "; ".join(labels) or "none", "(the same block)")
    rest, dust = pv.differing(cl, w)
    off_plane = [x for x in rest if not any(x.startswith(str(c) + ":") for c in PLANE)]
    ids = sorted({st.p["id"] for c in set(cl.b) | set(w.b) if c not in PLANE and cl.get(c) != w.get(c) for st in (cl.get(c), w.get(c)) if st.p.get("id")})
    reps = [n for c, n in {**si.PARTS, **PARTS}.items() if cl.get(c).n == "repeater" and cl.get(c) != w.get(c)]
    nets = {}
    for c in dust:
        n = {D_8: "D_8", si.D_1: "D_1", si.D_2: "D_2"}.get(c, b.role.get(c))
        nets[n] = nets.get(n, 0) + 1
    print(f"   the rest of the world against it (the returns): {len(off_plane)} cells, the blocks", ", ".join(ids), "and the repeaters",
          ", ".join(reps), "| dust levels:", ", ".join(f"{n} {k}" for n, k in sorted(nets.items(), key=str)))
    r0 = si.noted(base, idle())
    rest, dust = pv.differing(r0, w, set(MINE))
    print("   end state against s_inputs.py's run: cells that differ outside the added blocks:")
    print("     ", "; ".join(rest) or "none")
    print("      dust levels that differ:", ", ".join(f"{c} {r0.get(c).p['power']}->{w.get(c).p['power']}" for c in dust) or "none")
    print("   box, opening + close:", s.box(cells))

    print("\n== order (must pass): against the run above")
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)),
                     ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("both", dict(reverse=True, ia_last=True))):
        x = noted(mine, **kw)
        print(f"   {name}:", "FAILS" if any(verdicts(mine, dusts, cl, **kw)) else "stages 0 to 5 done, stages 6 and 7 done;", "piston events of each tick",
              "the same set;" if per_tick(x) == per_tick(w) else "DIFFER;", "end-state cells", "the same" if s.cell_diff(w, x) == "none" else "DIFFER")

    for name, (title, bkw) in CONTROLS.items():
        bc = build(**bkw)
        cc, mv = d.make_world(bc)
        co, _ = t.opened(bc)
        c = noted(co)
        badc = verdict_end(c, cl)
        door, _ = opening_against(bc, set(MINE))
        print(f"\n== {name}: {title}")
        print("   moved during load:", [m.split("@")[0] for m in mv] or "none", "| opening:", same(door), "| open state:", top_row(co))
        print("   close:", "; ".join(x for x in pv.told(c, "c", lambda m: any(n in m for n in (" A_9@", " P9@", " P8@", " Q@", " P5@", str(R_X), str(R_9))))
                                     if pv.tick_of(x) >= 5) or "nothing moves at A_9, P9 or P8")
        print("   ->", "FAILS: " + "; ".join(badc[:6]) if badc else "done", "| after c" + str(LAST) + ":", top_row(c))

    print("\n== each of the seven working blocks left out (S_L: the glass stays): stages 6 and 7")
    print("  ", ", ".join(f"{n} " + ("FAILS" if verdict_end(noted(t.opened(build(drop=(c,)))[0]), cl, (O_8,)) else "done") for c, n in PARTS.items()),
          "(O_8: in the simulator's order of c4's events; the what-if below) | G_9 as stone:",
          "FAILS" if verdict_end(noted(t.opened(build(swap={G_9: t.STONE}))[0]), cl) else "done")
    print("\n== the three delays, each 1 to 4 ticks with the others as built: stages 6 and 7, and the opening")
    for n_, c, facing, on in (("R_X", R_X, "west", False), ("R_9", R_9, "east", True), ("R_8", R_8, "north", True)):
        out = []
        for k in (1, 2, 3, 4):
            bk = build(swap={c: rep(facing, k, on)})
            out.append(f"{k} " + ("FAILS" if verdict_end(noted(t.opened(bk)[0]), cl) else "done") + ", opening " + same(opening_against(bk, set(MINE))[0]))
        print(f"   {n_}:", "; ".join(out))

    print("\n== what-if (sim only): O_8 left out and P8's event put ahead of the others queued in phase d of c4 (R_8 and r_P5 both turn on "
          "there; the scheduled ticks' order decides in the game)")
    for title, bkw, ahead in (("O_8 left out, the simulator's order", dict(drop=(O_8,)), None), ("O_8 left out, P8's event first", dict(drop=(O_8,)), (4, P8)),
                              ("as built, P8's event first", {}, (4, P8))):
        x = noted(t.opened(build(**bkw))[0], ahead=ahead)
        print(f"   {title}: P8's updates c2 to c4:", ", ".join(dict.fromkeys(f"c{k}{ph} " + ("powered" if on else "not powered") + (", free" if ok else ", blocked")
                                                                                for k, ph, on, ok in x.woke["P8"] if 2 <= k <= 4)) + ";",
              "c4:", ", ".join(o.brief(m) if "failed" not in m else ("P8" if str(P8) in m else "P5") + "'s push fails" for k, _, _, m in x.lines
                               if k == 4 and any(n in m for n in (" P8@", " P5@", str(P8), str(P5)))) + ";",
              "->", "FAILS: " + "; ".join(verdict_end(x, cl, (O_8,))[:4]) + " | " + top_row(x) + f", the static block {t.at(x, 's2')[0]}"
              if verdict_end(x, cl, (O_8,)) else "done")

    plain, _ = t.opened(b0)
    print("\n== what-if (sim only): P9 by command in s_inputs' build, QC-powered as R_9 powers it (a lit repeater set into R_9's cell without "
          "updates, then taken out, P9 updated each time)")
    x = noted(plain, before=pulse(1, 1))
    print("   the plan's order, P9 in stage 1 (out at c1, spat at c2) with P7 on NA at c3:",
          "; ".join(pv.told(x, "c", lambda m: any(n in m for n in (" P9@", " P7@", " P5@", str(P5))))[:5]), "->", top_row(x))
    print("   this order, P9 after stage 5 (S's head is in (1,2,0) from c14 g to its spit in c15 g); done: TM real at (2,2,0), TR at (1,2,0), P9 in")
    for on in (14, 15, 16, 17):
        print(f"   P9 powered before c{on}, released 1 / 2 / 3 gt later:", " / ".join(
            "done" if t.at(y, "TM")[:2] == ((2, 2, 0), "real") and t.at(y, "TR")[:2] == ((1, 2, 0), "real") and not t.at(y, "P9")[2]
            else "FAILS (" + top_row(y).split(", C")[0] + ")" for y in (noted(plain, before=pulse(on, n)) for n in (1, 2, 3))))

    sw = build()
    sw.b[(1, 2, 0)], sw.b[(2, 2, 0)] = sw.b[(2, 2, 0)], sw.b[(1, 2, 0)]
    sdoor, scells = opening_against(sw, {(1, 2, 0), (2, 2, 0), (2, 3, 0), (3, 2, 0)}, ref=b)
    so, _ = t.opened(sw)
    print("\n== the closed door loaded with the labels as this close leaves them (TM and TR exchanged), opened: every cell outside the four the "
          "two blocks pass through, against the opening above:", same(scells) + ";", "open state:", ", ".join(f"{n} {t.at(so, n)[0]}" for n in ("TM", "TR")))

    gone = noted(mine, idle(54), before={34: lambda x: x.cmd_set(si.RB_UP, AIR)})
    print("\n== after the close (what-if; RB_ST's return is not designed): RB_ST taken out of (2,8,0) by command before c34, to c54")
    print("   the S feed's 13 blocks and its cut cell against the open state:", "the same" if si.state(gone) == si.state(mine) else "DIFFER",
          "| P8", "out" if t.at(gone, "P8")[2] else "IN", "powered by", [c for _, c in power_sources(gone, P8)], "| Q", t.at(gone, "Q")[0],
          "| stages 6 and 7 ->", "FAILS: " + "; ".join(verdict_end(gone, cl)[:4]) if verdict_end(gone, cl) else "still done")

    print("\n== ctl 10: the input off n ticks after it went on (trigger.py's feed is armed at t10 j, R_D on at t8 d)")
    res = {}
    for n in (8, 9, 10, 11, 12, 16):
        on, _ = t.opened(b, ticks=n)
        res[n] = "FAILS" if any(verdicts(on, dusts, cl)) else "done"
    print("   stages 0 to 7:", res)
