"""P10 and V, stages 3 and 4 of the close, from blocks (door coords): the P10 and V commands are gone. Two blocks
on top of dp_off.py's build; its seven blocks, the trigger chain, design_c's opening, the close feeds and the S
feed are unchanged. Everything printed is COMPUTED on the simulator; nothing here ran on a server.

P10     No block. r_P10 (-1,5,-1), design_c's 3-tick repeater on NA, turns on at c8 d, three ticks after NA's
        relight (RB_A's landing, c2 j). P10 extends at c8, level 0, five ticks after P11's spit, pushes V into
        (-1,3,0) and stays out, which is where the closed door has it. V and P10's head land at c10 j.
Feed    D_V, a dust at (1,4,-4) on the hallway's roof, between NA's dusts (2,4,-4) and (1,4,-3); R_V, a 1-tick
        repeater at (0,4,-4) facing east on the roof beside it. R_V reads D_V and powers NV's dust (-1,4,-4),
        four dusts up the line from (-1,3,-1), the dust that points south into V's cell (-1,3,0). NV is the
        opening's own V feed, cut at t2 j by C_cut and dark from then on; R_V feeds it west of the cut.
On      NA relights at c2 j, R_V turns on at c4 d: NV's west branch is lit, 12 at (-1,3,-1). S left (-1,3,0)
        at c3 and P11's head is gone, so the dust points into air. V lands on the lit cell at c10 j, checks
        itself and extends at c11, level 0: S moves into (1,3,0) and lands at c13 j.
Not spat  The feed stays on while NA is lit, so V extends once and stays out, head in (0,3,0): the closed door
        has V out, on NV. S is real at (1,3,0) two ticks after V's extension instead of at once.
Opening NA dies at t0 g, R_V turns off at t2 d, C_cut cuts NV at t2 j as before: V retracts at t3.
P8      NV's east branch reads the feed too: 1 at (5,5,0) and 0 at (4,5,0), the dust that points into P8's
        QC cell. One dust further up NV the feed would light it.
Stage 5 Still commands, now from c12: F_S on, c13 off (RB_F spat while S moves in), c15 G_S's hold.
Fewer   p10_v_search.py builds every single block in 175 free cells around V, P10 and NV's west branch: 3 of
        5600 pass its rule and none can be built; they are opened at the end here.

Not controls: the roof under D_V and R_V is the hallway's wall ring.
Run from the repo root (sim; replay-only):
python -m scripts.door2.close_layout.p10_v > scripts/door2/close_layout/p10_v.txt"""
import copy, re
from scripts.door2.close_layout import feeds as f, s_feed as s, trigger as t, dp, dp_off as o
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, DIRS

D_V, R_V = (1, 4, -4), (0, 4, -4)
NV_IN, NV_V, NV_P8, NV_E = (-1, 4, -4), (-1, 3, -1), (4, 5, 0), (5, 5, 0)       # R_V's dust, V's dust, P8's dust, the one before it
NV_WEST = [(-1, 3, -1), (-1, 3, -2), (-1, 3, -3), (-1, 4, -4), (-1, 5, -5), (-1, 6, -6), (0, 6, -6)]
P10, R_P10, V_WAIT, V_CELL, V_HEAD, S_WAIT, S_CELL = (-1, 5, 0), (-1, 5, -1), (-1, 4, 0), (-1, 3, 0), (0, 3, 0), (0, 3, 0), (1, 3, 0)
MINE = {D_V: t.DUST, R_V: B("repeater", facing="east", delay=1, powered=True)}
SHOW = ("EXTEND", "RETRACT", "cancel", "failed", "dropped", f"wire {NV_V}", f"wire {D_V}", f"repeater {R_V}", f"repeater {R_P10}", f"event sticky_piston@{V_CELL}",
        f"land sticky_piston@{V_CELL}", f"land sticky_piston@{S_CELL}", f"land piston_head@{V_WAIT}")
LAST = 18                                                           # the runs end after c18
FEED = (12, 13, 15)                                                 # F_S on, F_S off, G_S's hold off: the ticks they act in


def build(drop=(), swap=None, **kw):
    """dp_off.py's build with the two blocks; `drop` leaves cells out, `swap` replaces or adds some."""
    return o.build(drop=drop, swap={**MINE, **(swap or {})}, **kw)


def idle(last=LAST):
    """c-1 .. c`last`, no command after the input."""
    return [[(f.DRIVER, AIR)]] + [[] for _ in range(last + 1)]


def staged(feed=FEED, last=LAST):
    """idle() with stage 5 by command (drive A of s_feed.py): F_S on before tick feed[0], off before feed[1]
    (RB_F spat), G_S's hold off before feed[2] (0: never)."""
    out = idle(last)
    for tick, cmd in zip(feed, (s.ON, s.OFF, s.PULL)):
        if tick:
            out[tick + 1].append(cmd)
    return out


class Noted(o.Noted):
    """dp_off's Noted with this step's lines, and each update of V in its firing cell with whether V is powered then."""

    def L(self, msg):
        World.L(self, msg)
        if any(x in msg for x in SHOW):
            self.lines.append((self.tick_no, self.phase, self.cur if self.phase == "g" and self.seen is not None else None, msg))

    def check_extend(self, p):
        if p == V_CELL and self.get(p).p.get("id") == "V":
            self.noted.append((self.tick_no, self.phase, bool(self.neighbor_signal(p, DIRS["east"]))))
        dp.Levels.check_extend(self, p)


def waiting(w):
    """power on V and S where they wait, after a tick: {name: (cell, sources)} for each that is real, retracted and
    not yet in its firing cell."""
    out = {}
    for n, fire in (("V", V_CELL), ("S", S_CELL)):
        p, kind, ext = t.at(w, n)
        if kind == "real" and not ext and p != fire:
            out[n] = (p, [c for _, c in power_sources(w, p)])
    return out


def noted(w, ticks=None, first=-1, before=None, **kw):
    """a copy of w taken through ticks (each: its commands, then the tick), the first numbered `first`; keeps the
    shown lines, the power on the waiting V and S and (blocks, moving cells) after each tick. `before` {tick
    number: function of the world} acts ahead of that tick (sim only)."""
    w = copy.deepcopy(w)
    w.__class__ = Noted
    w.reverse, w.ia_last = kw.get("reverse", False), kw.get("ia_last", False)
    w.lvl, w.order, w.seen, w.after, w.said, w.lines, w.noted, w.power, w.frames = {}, [], None, None, [], [], [], [], []
    for k, cmds in enumerate(idle() if ticks is None else ticks):
        w.log.clear()
        w.tick_no = k + first
        for c, blk in cmds:
            w.cmd_set(c, blk)
        if before and w.tick_no in before:
            before[w.tick_no](w)
        w.tick()
        w.power.append((w.tick_no, waiting(w)))
        w.frames.append((dict(w.b), set(w.be)))
    return w


def moves(w, name=None, upto=None):
    """the piston events that ran, as (tick, text); of one piston, through one tick."""
    return [(k, m) for k, m in o.moves(w) if (name is None or f" {name}@" in m) and (upto is None or k <= upto)]


def fired(w, name):
    return ", ".join(f"c{k} " + ("out" if "EXTEND" in m else "spat" if "SPIT" in m else "in") for k, m in moves(w, name)) or "never fires"


def verdict34(w, dusts):
    """stages 3 and 4 as the world has them with no command after the input: a list of what is wrong."""
    bad = []
    spit = next((i for i, (_, m) in enumerate(moves(w)) if "RETRACT P11" in m and "SPIT" in m), None)
    out10 = [i for i, (_, m) in enumerate(moves(w)) if "EXTEND P10@" in m]
    if spit is None or len(out10) != 1 or out10[0] < spit or moves(w, "P10")[1:]:
        bad.append("P10 does not extend once, after P11's spit, and stay out: " + fired(w, "P10"))
    if [m.split()[0] for _, m in moves(w, "V")] != ["EXTEND"]:
        bad.append("V does not extend once and stay out: " + fired(w, "V"))
    if any(n in m for _, m in moves(w) for n in (" S@", " T@", " P12@", " P11@") if _ > 3):
        bad.append("S, T, P12 or P11 moves after c3")
    want = {"V": (V_CELL, "real", True), "P10": (P10, "real", True), "S": (S_CELL, "real", False), "C": ((1, 2, 0), "real", None),
            "T": ((1, 4, 0), "real", False), "P12": ((0, 5, 0), "real", False), "SP": ((0, 4, 0), "real", None),
            "P11": (o.P11, "real", False), "TL": ((0, 2, 0), "real", None), "P8": ((3, 4, 0), "real", False),
            "Q": ((3, 3, 0), "real", False), "TM": ((3, 2, 0), "real", None)}
    bad += [f"{n} {t.at(w, n)}" for n, x in want.items() if t.at(w, n) != x]
    bad += [f"dust lost at {c}" for c in dusts if w.get(c).n != "redstone_wire"]
    bad += [f"waiting {n} powered at c{k} from {src}" for k, got in w.power for n, (_, src) in got.items() if src]
    return bad + [f"P8's dust {w.get(NV_P8).p['power']}"] * bool(w.get(NV_P8).p["power"])


NEED_END = {**t.NEED_END, "V": (V_CELL, "real", True), "P10": (P10, "real", True)}


def verdict_end(w):
    """stage 5 done, V out: trigger.verdict_end with V where this feed leaves it."""
    bad = [f"{n} {t.at(w, n)}" for n, want in NEED_END.items() if t.at(w, n) != want]
    return bad + ([f"(1,2,0) {w.get((1, 2, 0))}"] if w.get((1, 2, 0)).n != "air" else [])


def per_tick(w, first=-1, last=LAST):
    return [sorted(m for k, m in moves(w) if k == n) for n in range(first, last + 1)]


def told(w, tick="c", keep=lambda m: True):
    """dp_off.told with a dust's successive steps inside one phase as one line."""
    out = []
    for x in o.told(w, tick, keep):
        head, _, step = x.partition(" power ")
        if step and out and out[-1].startswith(head + " power ") and out[-1].endswith("->" + step.split("->")[0]):
            out[-1] = out[-1].rsplit("->", 1)[0] + "->" + step.split("->")[1]
        else:
            out.append(x)
    return out


def tick_of(line):
    return int(re.match(r"\w(-?\d+)", line).group(1))


def levels(w, cells):
    return ", ".join(f"{c} {w.get(c).p['power']}" for c in cells)


def opening_notes(b):
    """the opening of b from the closed state, noted; ticks are numbered as trigger.py numbers them (t-1 first)."""
    w, _ = d.make_world(b)
    w.run(4)
    w.cmd_set(f.DRIVER, t.RB)
    return noted(w, [[] for _ in range(t.OPEN_TICKS)])


def differing(a, b_, skip=()):
    """cells that differ between two worlds, as text, dust levels apart."""
    cells = [p for p in sorted(set(a.b) | set(b_.b)) if p not in skip and a.b.get(p) != b_.b.get(p)]
    dust = [p for p in cells if a.get(p).n == b_.get(p).n == "redstone_wire"]
    rest = [f"{p}: {a.get(p)} there, {b_.get(p)} here" for p in cells if p not in dust]
    return rest, dust


# p10_v_search.txt's three passes
ONE = {"a 1-tick repeater at (-2,2,-2) facing west, from NA's dust (-3,2,-2) into the wall block under NV's dust (-1,3,-2)":
           ((-2, 2, -2), B("repeater", facing="west", delay=1, powered=True)),
       "a 1-tick repeater at (-2,2,-1) facing west, from the stone under NA's dust (-3,3,-1) into the wall block under NV's dust (-1,3,-1)":
           ((-2, 2, -1), B("repeater", facing="west", delay=1, powered=True)),
       "a 4-tick repeater at (-2,4,0) facing west, from DP toward (-1,4,0), the cell above V (QC): DP's one tick at c2 j comes out as four, c10 d to c18 d":
           ((-2, 4, 0), B("repeater", facing="west", delay=4, powered=False))}
# name: (title, build keywords)
CONTROLS = {
    "ctl 1": ("no D_V: R_V reads nothing", dict(drop=(D_V,))),
    "ctl 2": ("no R_V: NA's dust stops at D_V", dict(drop=(R_V,))),
    "ctl 3": ("R_V at 2 ticks: in the opening it turns off at t4 d, after the cut at t2 j, and V retracts late",
              dict(swap={R_V: B("repeater", facing="east", delay=2, powered=True)})),
    "ctl 4": ("a dust in R_V's place (no delay, both ways): NA and NV are one net", dict(swap={R_V: t.DUST})),
    "ctl 5": ("a stone in D_V's place: NA's dusts beside it do not point into it", dict(swap={D_V: t.STONE})),
    "ctl 6": ("R_V turned round (facing west): it reads NV and drives D_V", dict(swap={R_V: B("repeater", facing="west", delay=1, powered=True)})),
}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    b, b0 = build(), o.build()
    base, _ = t.opened(b0)
    mine, moved = t.opened(b)
    cl, cl0 = d.make_world(b)[0], d.make_world(b0)[0]
    dusts = [c for c, st in mine.b.items() if st.n == "redstone_wire"]
    print(f"added: {len(MINE)} blocks (1 dust, 1 repeater); no stand-in for P10 or V")
    print("opening, dp_off's build vs + the two, open-state differences:", f.diff(f.snapshot(base), f.snapshot(mine)) or "none")
    print("cell differences outside the added blocks:", s.cell_diff(base, mine, set(MINE)),
          "| tick by tick, the door's pistons and the door plane:", dp.same_opening(b))
    rest, dust = differing(cl0, cl, set(MINE))
    print("moved during load:", moved or "none", "| closed state: D_V", cl.get(D_V).p["power"], "R_V", "on" if cl.get(R_V).p["powered"] else "off",
          "| V powered by", [c for _, c in power_sources(cl, V_CELL)], "| cells that differ from dp_off's closed state:", rest or "none",
          "but NV's levels:", ", ".join(f"{c} {cl0.get(c).p['power']}->{cl.get(c).p['power']}" for c in dust))
    wo, wo0 = opening_notes(b), opening_notes(b0)
    print("the opening at V:", "; ".join(told(wo, "t", lambda m: any(x in m for x in ("repeater", str(NV_V), " V@", " P10@")))))
    print("   in dp_off's build:", "; ".join(told(wo0, "t", lambda m: any(x in m for x in (str(NV_V), " V@", " P10@")))))
    print("open state: D_V", mine.get(D_V).p["power"], "| R_V", "on" if mine.get(R_V).p["powered"] else "off", "| NV's west branch:",
          levels(mine, NV_WEST), "| V", t.at(mine, "V"), "S", t.at(mine, "S"), "P10", t.at(mine, "P10"))
    print("pistons with an added cell among their power sources, closed and open state:",
          {st.p["id"]: sorted(c for _, c in power_sources(w, p) if c in MINE) for w in (cl, mine) for p, st in sorted(w.b.items())
           if st.n in ("piston", "sticky_piston") and any(c in MINE for _, c in power_sources(w, p))} or "none")
    cells = set(v.cumulative_cells(b)[0])
    print("box, opening:", s.box(cells))

    w, ref = noted(mine), noted(base)
    print(f"\n== the close from the input, no command: c-1 to c{LAST}")
    same = next((n for n in range(-1, LAST + 1) if per_tick(w)[n + 1] != per_tick(ref)[n + 1]), None)
    print(f"   c-1 to c{same - 1}: the piston events of dp_off's run with no command, tick by tick" if same else "   NO DIFFERENCE from dp_off's run")
    print("\n".join("   " + x for x in told(w) if tick_of(x) >= 2))
    w6 = noted(mine, idle(6))
    bad0, bad2, bad = t.verdict_c0(noted(mine, idle(0))), o.verdict(w6, dusts), verdict34(w, dusts)
    print("   stages 0 to 2 ->", "FAILS: " + "; ".join(bad0 + bad2) if bad0 or bad2 else
          "done as in dp_off's run: stages 0 and 1 in c0, P11 out and spat in c3, S real at (0,3,0), RB_D and A_D home")
    print("   stages 3 and 4 ->", "FAILS: " + "; ".join(bad) if bad else
          "done: P10 extends once, at c8, after P11's spit, and stays out; V lands lit at (-1,3,0), extends once, at c11, and stays out; "
          "S real at (1,3,0), retracted; C (1,2,0), SP (0,4,0), TL (0,2,0), Q (3,3,0), TM (3,2,0); T, P12, P11, P8 in; no dust lost")
    print("   P10:", fired(w, "P10") + ";", "V:", fired(w, "V") + ";", "after each tick, power on V and S while they wait:",
          {f"{n} at {p}": f"c{min(k for k, got in w.power if got.get(n, (0,))[0] == p)} to c{max(k for k, got in w.power if got.get(n, (0,))[0] == p)}: "
           + ("none" if not any(got[n][1] for k, got in w.power if got.get(n, (0,))[0] == p) else "POWERED")
           for n, p in (("V", V_WAIT), ("S", V_CELL), ("S", S_WAIT))})
    lit = noted(mine, idle(4))
    print("   NV after c4, R_V on:", levels(lit, NV_WEST[::-1]), "| east of the cut's dust (1,6,-6)", lit.get((1, 6, -6)).p["power"], "to",
          levels(lit, [(5, 6, -2), (5, 5, -1), NV_E, NV_P8]), "| P8 powered by", [c for _, c in power_sources(lit, (3, 4, 0))] or "nothing")
    print("   block events from c4 on whose updates reach V's cell (-1,3,0):", [f"c{k} {n}" for k, _, n, _, sn in w.order if V_CELL in sn and k >= 4],
          "| V's updates there:", ", ".join(f"c{k}{ph} " + ("powered" if on else "not powered") for k, ph, on in w.noted),
          "(at c10 j: placed, its own landing check, then P10's head landing above it)")

    r = noted(mine, staged())
    for blocks, _ in r.frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print(f"\n== through stage 5: stage 5 by command (c{FEED[0]} F_S on; c{FEED[1]} off; c{FEED[2]} G_S's hold), to c{LAST}")
    print("\n".join("   " + x for x in told(r) if tick_of(x) >= 8))
    bad1 = verdict_end(r)
    print(f"   after c{LAST} ->", "FAILS: " + "; ".join(bad1) if bad1 else
          "stage 5 done: S real at (1,3,0), retracted; C real at (1,1,0); (1,2,0) air; T, P12, P11 in; V and P10 out; SP, TL, Q, TM, "
          "P8 where the close needs them; RB_F parked; P7 out over TR at (2,2,0)")
    _, wt, _, _ = t.close(b0, o.staged())
    rest, dust = differing(wt, r, set(MINE))
    print("   end state against dp_off.py's run, where commands drive P10 and V: cells that differ outside the two blocks:")
    print("     ", "; ".join(rest) or "none")
    print("      and the levels of NV's dust that R_V lights:", ", ".join(f"{c} {r.get(c).p['power']}" for c in dust),
          "| every other dust the same:", all(b0.role.get(c) == "NV" for c in dust))
    print("   box, opening + close through stage 5 (stand-in sources included):", s.box(cells))

    print("\n== order (must pass): against the runs above")
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)),
                     ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("both", dict(reverse=True, ia_last=True))):
        x, x6, x5 = noted(mine, **kw), noted(mine, idle(6), **kw), noted(mine, staged(), **kw)
        print(f"   {name}:", "FAILS" if t.verdict_c0(noted(mine, idle(0), **kw)) or o.verdict(x6, dusts) or verdict34(x, dusts) or verdict_end(x5)
              else "stages 0 to 4 done, stage 5 done;", "piston events of each tick", "the same set;" if per_tick(x) == per_tick(w) and
              per_tick(x5) == per_tick(r) else "DIFFER;", "end-state cells", "the same" if s.cell_diff(r, x5) == "none" else "DIFFER")

    for name, (title, bkw) in CONTROLS.items():
        bc = build(**bkw)
        cc, mv = d.make_world(bc)
        co, _ = t.opened(bc)
        c = noted(co)
        badc = verdict34(c, [x for x in dusts if x not in bkw.get("drop", ()) and x not in bkw.get("swap", {})])
        print(f"\n== {name}: {title}")
        print("   moved during load:", [m.split("@")[0] for m in mv] or "none", "| opening:", dp.same_opening(bc), "| open state: V", t.at(co, "V")[0],
              "NV at V", co.get(NV_V).p["power"], "NA at (2,4,-4)", co.get((2, 4, -4)).p["power"])
        print("   close:", "; ".join(told(c, "c", lambda m: any(x in m for x in (" V@", " P10@", str(R_V), str(NV_V), " S@")))) or "nothing moves at V")
        print("   ->", "FAILS: " + "; ".join(badc[:5]) if badc else "done")

    gone = copy.deepcopy(mine)
    gone.cmd_set_silent(R_P10, AIR)
    g = noted(gone)
    print("\n== what stage 3 rests on (design_c's block, not an added one): r_P10 taken out of the open state without an update")
    print("   close:", "; ".join(told(g, "c", lambda m: any(x in m for x in (" V@", " P10@", " S@")))) or "nothing moves at P10 or V",
          "->", "FAILS: " + "; ".join(verdict34(g, dusts)[:3]) if verdict34(g, dusts) else "done")
    print("\n== what-if (no block does this): NV's west branch lit early, a redstone block set beside (-1,3,-2) before that tick. S is in "
          "(-1,3,0), the cell the dust points into, until P11's extension event (c3, queued at c2 j)")
    for tick in (3, 2):
        early = noted(mine, before={tick: lambda x: x.cmd_set((-2, 3, -2), t.RB)})
        print(f"   before c{tick}:", "; ".join(told(early, "c", lambda m: any(x in m for x in (" V@", " P10@", " S@", " P11@", "skipped")))[:5]),
              "->", "FAILS: " + "; ".join(verdict34(early, dusts)[:3]) if verdict34(early, dusts) else
              "done: S's own event is queued behind P11's and finds S moving")
    print("\n== why (-1,4,-4): a redstone block set without updates beside each dust of NV's west branch in the open state, then one "
          "update of that dust: the level at P8's dust (4,5,0)")
    out = {}
    for c, src in zip(NV_WEST, ((-2, 3, -1), (-2, 3, -2), (-2, 3, -3), (-2, 4, -4), (-2, 5, -5), (-2, 6, -6), (0, 7, -6))):
        x = copy.deepcopy(mine)
        x.cmd_set_silent(src, t.RB)
        x.neighbor_changed(c)
        out[c] = x.get(NV_P8).p["power"]
    print("  ", out)

    print("\n== ctl 7: the input off n ticks after it went on (trigger.py's feed is armed at t10 j, R_D on at t8 d)")
    res = {}
    for n in (8, 9, 10, 11, 12, 16):
        on, _ = t.opened(b, ticks=n)
        res[n] = "FAILS" if t.verdict_c0(noted(on, idle(0))) or verdict34(noted(on), dusts) else "done"
    print("   stages 0 to 4:", res)

    print("\n== stage 5's commands (drive A of s_feed.py): S moves in from c11 g to c13 j and fires at c14")
    print("   RB_F spat at c10 / c11 / c12 / c13, G_S's hold off at c15:",
          " / ".join("FAILS" if verdict_end(noted(mine, staged((k - 1, k, 15)))) else "done" for k in (10, 11, 12, 13)),
          "| spat at c13, hold off at c14 / c15 / c16 / c17:",
          " / ".join("FAILS" if verdict_end(noted(mine, staged((12, 13, k)))) else "done" for k in (14, 15, 16, 17)))
    x = noted(mine, staged((9, 10, 15)))
    print("   spat at c10, before V's extension:", "; ".join(told(x, "c", lambda m: any(n in m for n in (" T@", " S@", " V@")) and "c0g" not in m)),
          "->", "; ".join(verdict_end(x)[:3]))
    print("   s_feed.py's ticks (F_S on c5, off c6, hold c7), as in dp_off's run:", "FAILS: " + "; ".join(verdict_end(noted(mine, staged((5, 6, 7))))[:3]))

    print("\n== one block instead of two? p10_v_search.txt: every single block built into 175 free cells, 3 of 5600 pass its rule (c14); "
          "none can be built")
    for title, (c, blk) in ONE.items():
        bo = o.build(swap={c: blk})
        wo_, mv = t.opened(bo)
        x = noted(wo_, staged(last=22))
        under = b0.b.get((c[0], c[1] - 1, c[2]), AIR)
        print(f"   {title}: stands on", under.p.get("id") or f"{under.n} ({b0.role.get((c[0], c[1] - 1, c[2]))})", "at", str((c[0], c[1] - 1, c[2])) + ";",
              "opening:", dp.same_opening(bo) + ";", "V:", fired(x, "V") + ";", "NV at V after c4:", noted(wo_, idle(4)).get(NV_V).p["power"],
              "P8's dust", x.get(NV_P8).p["power"], f"| stage 5 by command, after c22 ->", "FAILS: " + "; ".join(verdict_end(x)[:3]) if verdict_end(x) else "done")
