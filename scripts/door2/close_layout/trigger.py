"""The close's trigger chain from one input, stages 0 and 1 (door coords): still-needed items 2 and 3 of
docs/research/door_close_layout.md. design_c's opening, the nine close-feed blocks' cells and the S feed are
kept; the stand-ins RB_A, RB12, SRC_T, HOLD and POKE are replaced by blocks that the falling input drives.
DP (stage 2) is still lit and cut by command: its on and off are not designed (see the report).

Block events run first in, first out, so an event queued inside an event of level n runs after every event of
level n: order that rests on levels does not depend on the order of dust's neighbour updates.

Bus   Dust fed by K_in (1,8,-2), lit while the input is on. East branch (2,8,-2), (3,8,-2), DH (3,8,-1) on
      stone (3,7,-1) above P_R: P_R's hold, in place of HOLD. (4,8,-2) on stone (4,7,-2) feeds a 4-tick
      repeater (4,7,-1) into AP. West branch from K_in's top, over the input repeater: (1,9,-2) on K_in,
      (0,10,-2) on stone (0,9,-2) above R_in, (0,9,-1), (-1,9,-1), (-2,8,-1), (-3,7,-1), (-4,6,-1), (-4,5,0),
      (-4,5,1) on stone (-4,4,1) above M_K. Cut: stone (-3,5,0) over DP. Until 2026-11-22 the west branch left
      K_in's south side, (1,8,-1) on glass (1,7,-1), (0,8,-1), (-1,7,-1), (-2,7,-1), under a stone cut (1,8,0)
      over DT: moved off the column above RB_T's cells so that the returns can push RB_T down it (returns.py);
      K_in's other sides are R_in, X2's top and I_A. (1,9,-2) reads the east branch's (2,8,-2) down the step
      as well: one net, fed by K_in alone.
E0    I_A sticky (part 1): pulls RB_A home. Level 0.
P_R   Held by DH, and in the closed state by RB_ST at (3,7,0), a QC cell. The bus dies in phase d of c0, so
      P_R's retract is level 0 too. It pulls RB_T; Z_T retracts
      when the second of RB_A and RB_T has left (RB_A's old cell updates Z_T's head), level 1.
T     The feed is armed in the open state, not in c0: AP (4,7,0), a piston facing west behind the repeater,
      pushes RB_ST from (3,7,0) to (2,7,0), beside DT. It lands at t10 j, after T's last update of the
      opening (t8 j, P12's head landing), so T waits powered and not updated; Z_T's retract event wakes it
      (level 2). FT also QC-powers P12 through the open state.
DT off  W_T (1,5,0), a piston facing north above T: powered by FT, blocked by Z_T's head until Z_T's
      retract event, which queues T first and W_T after it (level 2). W_T's extension updates K_T (2,5,0), a
      sticky piston facing up under glass SPC (2,6,0) and RB_ST: QC-powered by RB_ST and FT, three from DT, so
      no update since RB_ST landed (level 3). K_T pushes SPC and RB_ST up: DT dies inside K_T's event and its
      change updates W_T, two below FT (level 4). W_T's retract event updates T, which is spat (level 5):
      the update the S probe's POKE stood in for.
P12   K (-4,1,2), a piston facing up under RB12, QC-powered by L (-3,2,2), armed from the load: design_c's
      obsidian blocker at (-4,3,2) stops it there. M_K (-4,3,1), a sticky piston facing down held by the
      bus, pulls glass WK (-4,1,1) from beside K (level 0); K pushes RB12 and gate stone G up (level 1) and
      NP12 dies. P12 stays out while FT and CT are lit; W_T's retract event updates it too, so it retracts
      at level 5, after DT is dark: the order is T's 0-tick first, then P12, in one phase.
Rest  After the close RB_ST is at (2,8,0) and SPC at (2,7,0), RB12 at (-4,3,2) and G at (-4,4,2); RB12 there
      powers M_K (out again from c3, WK back beside K) and K; RB_T at (2,6,-1) QC-powers K_T, which NA's
      relight updates (out from c3, its head under SPC). The east side's return is rbt_drives.py's.
Sticky K_T is sticky since 2026-11-22 (it was a plain piston when the six probes were first measured): DT's death
      unpowers it inside its own extension, so it is released at once and spits SPC, which is real at (2,7,0)
      from c0 g instead of landing at c2 j; RB_ST, the second block of the push, lands at (2,8,0) at c2 j as
      before, and every other cell of the opening and of the close is the same at every tick (rbt_drives.py).
      The return needs it: when RB_T is lifted off (2,6,-1) K_T retracts and pulls SPC home to (2,6,0).

Probe stand-ins, set by command between ticks: SRC_P (-3,4,1) south of DP ((-4,4,0) is now the bus's
support) and s_feed.py's SRC_10, SRC_V, SRC_F and HOLD_G.
Run from the repo root (sim; replay-only):
python -m scripts.door2.close_layout.trigger > scripts/door2/close_layout/trigger.txt"""
import copy, functools
from scripts.door2.close_layout import feeds as f, puller as pr, s_feed as s
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources

I_A, RB_A_HOME, RB12_UP, G_UP = (1, 7, -2), (1, 6, -2), (-4, 3, 2), (-4, 4, 2)
AP, REP, RB_ST, SRC, UP = (4, 7, 0), (4, 7, -1), (3, 7, 0), (2, 7, 0), (2, 8, 0)
W_T, K_T, SPC, DH = (1, 5, 0), (2, 5, 0), (2, 6, 0), (3, 8, -1)
M_K, WK, K, CUT_DP = (-4, 3, 1), (-4, 1, 1), (-4, 1, 2), (-3, 5, 0)
SRC_P = (-3, 4, 1)
RB, GLASS, STONE, DUST = s.RB, s.GLASS, B("stone"), B("redstone_wire", power=0)


def pis(n, facing, ident, ext=False):
    return B(n, facing=facing, extended=ext, id=ident)


BUS_EAST = {(2, 7, -2): GLASS, (2, 8, -2): DUST, (3, 7, -2): GLASS, (3, 8, -2): DUST, (3, 7, -1): STONE, DH: DUST,
            (4, 7, -2): STONE, (4, 8, -2): DUST}
ARMING = {(4, 6, -1): GLASS, REP: B("repeater", facing="north", delay=4, powered=False),
          AP: pis("piston", "west", "AP"), RB_ST: B("rb", id="RB_ST")}
RELAY = {W_T: pis("piston", "north", "W_T"), K_T: pis("sticky_piston", "up", "K_T"), SPC: B("glass", id="SPC")}
BUS_WEST = {(1, 9, -2): DUST, (0, 9, -2): STONE, (0, 10, -2): DUST, (0, 8, -1): GLASS, (0, 9, -1): DUST,
            (-1, 8, -1): STONE, (-1, 9, -1): DUST, (-2, 7, -1): STONE, (-2, 8, -1): DUST, (-3, 6, -1): STONE,
            (-3, 7, -1): DUST, (-4, 5, -1): STONE, (-4, 6, -1): DUST, (-4, 4, 0): GLASS, (-4, 5, 0): DUST,
            CUT_DP: STONE, (-4, 4, 1): STONE, (-4, 5, 1): DUST}
NP12_KILL = {M_K: pis("sticky_piston", "down", "M_K"), WK: B("glass", id="WK"), K: pis("piston", "up", "K")}
MINE = {**BUS_EAST, **ARMING, **RELAY, **BUS_WEST, **NP12_KILL}
P_R = {pr.P_R: pis("sticky_piston", "west", "P_R", True), pr.HEAD: B("piston_head", facing="west", sticky=True)}
STICKY_IA = pis("sticky_piston", "down", "I_A")
CELL = {f.DRIVER: "input", SRC_P: "SRC_P", s.SRC_10: "SRC_10", s.SRC_V: "SRC_V", s.SRC_F: "SRC_F", s.HOLD_G: "HOLD_G"}
SHOW = ("EXTEND", "RETRACT", "cancel", "failed", "dropped", f"wire {f.DT}")
OPEN_TICKS = 16


@functools.lru_cache(None)
def fixed():
    """design_c, the six feed blocks, P_R (no HOLD) and the S feed; every cell its opening occupies."""
    from scripts.door2 import volume as v
    b = f.build(extra=True)
    b.b.update({**P_R, **s.ADDED})
    return b, frozenset(v.cumulative_cells(b)[0])


def build(drop=(), swap=None, ia=STICKY_IA):
    """fixed() with I_A sticky and this step's blocks; `drop` leaves cells out, `swap` replaces or adds some."""
    b0, occ = fixed()
    b = copy.deepcopy(b0)
    b.b[I_A] = ia
    for p, st in {**MINE, **(swap or {})}.items():
        if p in drop:
            continue
        assert p not in b0.b and p not in occ, p
        b.b[p] = st
        b.role[p] = "trigger"
    return b


def opened(b, ticks=OPEN_TICKS):
    w, moved = d.make_world(b)
    w.run(4)
    w.cmd_set(f.DRIVER, RB)
    w.run(ticks)
    return w, moved


class Probe(s.Probe):
    """s_feed's Probe, and optionally I_A's retract event moved behind the others queued in phase d."""
    ia_last = False

    def repeater_tick(self, p):
        s.Probe.repeater_tick(self, p)
        if self.ia_last:
            for key in [k for k in self.events if k[0] == I_A]:
                self.events.move_to_end(key)


def staged(through=5, early_dp=False):
    """Commands per tick, each tick: its commands, then the tick. The input goes off before tick 1; R_in turns
    off in phase d of tick 2 = c0, where stages 0 and 1 run. Stage 2 and on by command, one event a tick."""
    out = [[] for _ in range(14)]
    out[0] = [(f.DRIVER, AIR)]                                   # c-1
    out[1 if early_dp else 2].append((SRC_P, RB))                # c1: 2 P11 (and P6) extend
    if through >= 5:
        out[3] = [(SRC_P, AIR)]                                  # c2: P11, P6 spat, S real at (0,3); T, P12 land in j
        out[4] = [(s.SRC_10, RB)]                                # c3: 3 P10 extends
        out[5] = [(s.SRC_10, AIR), (s.SRC_V, RB), (s.SRC_F, RB)]  # c4: P10 spat; 4 V lands lit and fires; F_S out
        out[6] = [(s.SRC_F, AIR), (s.SRC_V, AIR)]                # c5: RB_F spat, then V spat: 5 S fires
        out[7] = [(s.HOLD_G, AIR)]                               # c6: RB_F pulled: S spat
    return out


def run(w, ticks, reverse=False, ia_last=False):
    """a copy of w taken through ticks: (world, lines per tick, (blocks, moving cells) after each tick)."""
    w = copy.deepcopy(w)
    w.__class__ = Probe
    w.reverse, w.ia_last = reverse, ia_last
    lines, frames = [], []
    for k, cmds in enumerate(ticks):
        w.log.clear()
        for p, st in cmds:
            w.cmd_set(p, st)
        w.tick()
        said = ", ".join(CELL[p] + (" off" if st.n == "air" else " on") for p, st in cmds)
        lines.append([f"c{k - 1} [{said}]"] + [f"   c{k - 1}{ph} {m}" for (t, ph, m) in w.log if any(x in m for x in SHOW)])
        frames.append((dict(w.b), set(w.be)))
    return w, lines, frames


def at(w, ident):
    return s.at(w, ident)


# after the tick c0: stages 0 and 1 done inside one phase
NEED_C0 = {"RB_A": (RB_A_HOME, "moving"), "RB_T": (pr.HEAD, "moving"), "Z_T": ((1, 4, -1), "moving"),
           "T": ((1, 4, 0), "moving"), "C": ((1, 2, 0), "real"), "W_T": (W_T, "moving"), "K_T": (K_T, "moving"),
           "SPC": (SRC, "real"), "RB_ST": (UP, "moving"), "RB12": (RB12_UP, "moving"), "G": (G_UP, "moving"),
           "P12": ((0, 5, 0), "moving"), "SP": ((0, 4, 0), "moving"), "S": ((-1, 3, 0), "real"), "P11": ((-2, 3, 0), "real")}
# 12 ticks after c0, stages 2 to 5 driven by command; P7, P6 and P10 are out again on NA's relight (c2 j)
NEED_END = {"S": ((1, 3, 0), "real", False), "C": ((1, 1, 0), "real", None), "T": ((1, 4, 0), "real", False),
            "V": ((-1, 3, 0), "real", False), "P12": ((0, 5, 0), "real", False), "SP": ((0, 4, 0), "real", None),
            "P11": ((-2, 3, 0), "real", False), "TL": ((0, 2, 0), "real", None), "P8": ((3, 4, 0), "real", False),
            "Q": ((3, 3, 0), "real", False), "TM": ((3, 2, 0), "real", None), "F_S": (s.F_S, "real", False),
            "RB_F": (s.PARK, "real", None), "G_S": (s.G_S, "real", False), "P_R": (pr.P_R, "real", False),
            "RB_T": (pr.HEAD, "real", None), "RB_A": (RB_A_HOME, "real", None), "W_T": (W_T, "real", False),
            "RB_ST": (UP, "real", None), "RB12": (RB12_UP, "real", None), "P7": (s.P7, "real", True),
            "TR": ((2, 2, 0), "real", None)}


def verdict_c0(w):
    bad = [f"{n} {at(w, n)[:2]}" for n, want in NEED_C0.items() if at(w, n)[:2] != want]
    bad += [f"{c} {w.get(c)}" for c in ((1, 3, 0), (0, 3, 0)) if w.get(c).n != "air"]
    return bad + ([f"DT {w.get(f.DT).p['power']}"] if w.get(f.DT).p["power"] else [])


def verdict_end(w):
    bad = [f"{n} {at(w, n)}" for n, want in NEED_END.items() if at(w, n) != want]
    return bad + ([f"(1,2,0) {w.get((1, 2, 0))}"] if w.get((1, 2, 0)).n != "air" else [])


def events(lines):
    return [x for tick in lines for x in tick if "EXTEND" in x or "RETRACT" in x]


def close(b, ticks=None, **kw):
    """the opened build taken through `ticks` (default: every stage to 5): (world after c0, final world, lines, frames)."""
    w, _ = opened(b)
    ticks = ticks or staged()
    w0, _, _ = run(w, ticks[:2], **kw)
    w1, lines, frames = run(w, ticks, **kw)
    return w0, w1, lines, frames


# name: (title, build keywords, schedule keywords)
CONTROLS = {
    "ctl 1": ("no W_T: T is not updated when DT dies and stays out; P12 is not updated either", dict(drop=(W_T,)), {}),
    "ctl 2": ("no spacer: K_T's push moves nothing, DT stays lit", dict(drop=(SPC,)), {}),
    "ctl 3": ("no K_T", dict(drop=(K_T,)), {}),
    "ctl 4": ("no glass beside K: K is not woken, NP12 lives, P12 stays out and P11 shoves the top row", dict(drop=(WK,)), {}),
    "ctl 5": ("I_A not sticky (no E0): RB_A keeps Z_T out, T is not woken", dict(ia=pis("piston", "down", "I_A")), {}),
    "ctl 6": ("wrong order: DP lit before c0, P11 fires ahead of P12's retract", {}, dict(early_dp=True)),
    "ctl 7": ("the bus ending as a down-step onto M_K (stone (-4,4,0), dust (-4,4,1)): the stone QC-holds M_K until its "
              "own dust is dark, and only the end dust, three from M_K's stone, updates M_K. Not a failure at this length: "
              "the end dust's last step (1 to 0) follows the stone's (2 to 0) and M_K is released; one dust longer or "
              "shorter (levels 9 and 8, as before the west branch was re-laid) it is held for good. The end dust is also "
              "beside SRC_P, whose stand-in block relights the bus at c1",
              dict(drop=((-4, 5, 1),), swap={(-4, 4, 0): STONE, (-4, 4, 1): DUST}), {}),
}
SLOW3 = {REP: B("repeater", facing="north", delay=3, powered=False)}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    b = build()
    base, _ = opened(s.build())
    mine, moved = opened(b)
    print(f"added: {len(MINE)} blocks ({sum(st.n == 'redstone_wire' for st in MINE.values())} dust, "
          f"{sum(st.n in ('glass', 'stone') for st in MINE.values())} glass or stone, 5 pistons, 1 repeater, 1 redstone block); "
          "I_A sticky; P_R's HOLD (4,6,-1) gone")
    print("opening, design_c + close feeds + S feed vs + trigger, open-state differences:",
          f.diff(f.snapshot(base), f.snapshot(mine)) or "none")
    print("cell differences outside the added blocks, I_A and its head, HOLD, M_K's head and RB_ST's cell beside DT:",
          s.cell_diff(base, mine, set(MINE) | {I_A, RB_A_HOME, pr.HOLD, SRC, (-4, 2, 1), f.DT}), "| DT", mine.get(f.DT).p["power"])
    wa, wb = d.make_world(s.build())[0], d.make_world(b)[0]
    differ = []
    for w in (wa, wb):
        w.run(4)
        w.cmd_set(f.DRIVER, RB)
    for k in range(OPEN_TICKS):
        wa.tick()
        wb.tick()
        differ += [k - 2] * bool(f.diff(f.snapshot(wa), f.snapshot(wb)))
    print("opening tick by tick, the door's pistons and the door plane:", f"differ at t{differ}" if differ else "the same at every tick")
    w, _ = d.make_world(b)
    print("moved during load:", moved or "none", "| powered in the closed state:",
          {n: [c for _, c in power_sources(w, at(w, n)[0])] for n in ("P_R", "K", "W_T", "K_T", "M_K", "AP")})
    seen = []
    w.run(4)
    w.cmd_set(f.DRIVER, RB)
    t_in = w.time
    for _ in range(OPEN_TICKS):
        w.log.clear()
        w.tick()
        seen += [f"t{t - t_in - 2}{ph} {m}" for (t, ph, m) in w.log if ("EXTEND" in m or "RETRACT" in m or "land rb@" + str(SRC) in m)
                 and any(n in m for n in ("AP", "M_K", "P_R", "W_T", "K_T", "K@", str(SRC)))]
    print("added pistons moving during the opening:", "; ".join(seen))
    print("open state:", {n: at(mine, n) for n in ("P_R", "M_K", "AP", "RB_ST", "W_T", "K_T", "K")})
    print("powered in the open state:", {n: [c for _, c in power_sources(mine, at(mine, n)[0])]
                                         for n in ("T", "P12", "W_T", "K_T", "K", "P_R", "M_K", "AP")})
    added = set(MINE) | {SRC}
    print("other pistons with an added cell among their power sources, open state:",
          {st.p["id"]: sorted(c for _, c in power_sources(mine, p) if c in added) for p, st in sorted(mine.b.items())
           if st.n in ("piston", "sticky_piston") and st.p["id"] not in ("T", "P12", "W_T", "K_T", "K", "P_R", "M_K", "AP")
           and any(c in added for _, c in power_sources(mine, p))} or "none")
    hyp = copy.deepcopy(mine)
    for c, st in (((-4, 0, 2), pis("sticky_piston", "up", "X", True)), ((-4, 1, 2), B("piston_head", facing="up", sticky=True))):
        hyp.cmd_set_silent(c, st)
    print("why RB12 is pushed, not pulled: (-4,2,0) north of it is NA's dust, (-4,2,4) is outside the box, (-4,3,2) above it "
          "is where G lands, and a sticky piston facing up at (-4,0,2) with its head under RB12 is powered by",
          [c for _, c in power_sources(hyp, (-4, 0, 2))], "(RB12 itself, by QC)")
    cells = set(v.cumulative_cells(b)[0])
    print("box, opening:", s.box(cells))

    w0, w1, lines, frames = close(b)
    for blocks, _ in frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print("box, opening + close through stage 5 (stand-in sources included):", s.box(cells))
    print("\n== the close from the input: stages 0 and 1 in c0, stages 2 to 5 by command")
    for tick in lines:
        if len(tick) > 1 or not tick[0].endswith("[]"):
            print("\n".join(tick))
    bad0, bad1 = verdict_c0(w0), verdict_end(w1)
    print("   after c0 ->", "FAILS: " + "; ".join(bad0) if bad0 else
          "stages 0 and 1 done in one phase: C real at (1,2,0), T spat and retracting, (1,3,0) air; P12 retracting, SP "
          "moving into (0,4,0), (0,3,0) air; DT dark; RB_A, RB_T, RB_ST, RB12 and G moving to their rest cells")
    print("   after c12 ->", "FAILS: " + "; ".join(bad1) if bad1 else
          "stage 5 done: S real at (1,3,0), retracted; C real at (1,1,0); (1,2,0) air; T, P12, P11, V in; SP, TL, Q, TM, "
          "P8 where the close needs them; RB_F parked; P7 out over TR at (2,2,0) on NA's relight")
    print("   rest state:", {n: at(w1, n) for n in ("K", "M_K", "WK", "G", "K_T", "SPC", "AP", "I_A", "Z_T")})

    def per_tick(ls):
        return [sorted(x for x in tick if "EXTEND" in x or "RETRACT" in x) for tick in ls]

    def chain(ls):
        return [x.split("@")[0].split()[-1] for x in events(ls[:2]) if any(n in x for n in ("Z_T", " T@", "W_T", "K_T", "P12"))]

    print("\n== order (must pass): against the run above")
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)),
                     ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("both", dict(reverse=True, ia_last=True))):
        r0, r1, rl, _ = close(b, **kw)
        print(f"   {name}:", "FAILS" if verdict_c0(r0) or verdict_end(r1) else "done;",
              "end-state cells", "same;" if s.cell_diff(w1, r1) == "none" else "DIFFER;",
              "piston events of each tick", "the same set;" if per_tick(rl) == per_tick(lines) else "DIFFER;",
              "c0's first five:", ", ".join(x.split("@")[0].split()[-1] for x in events(rl)[:5]) + ";",
              "Z_T to T's spit in the same order" if chain(rl) == chain(lines) else "chain DIFFERS")

    for name, (title, bkw, skw) in CONTROLS.items():
        c0, c1, cl, _ = close(build(**bkw), staged(through=2, **skw))
        first = next((i for i, (x, y) in enumerate(zip(cl, lines)) if x != y), len(cl))
        print(f"\n== {name}: {title}" + (f" (as the run above through c{first - 2})" if first > 1 else ""))
        for tick in cl[first:6]:
            if len(tick) > 1 or not tick[0].endswith("[]"):
                print("\n".join(tick))
        print("   after c0 ->", "FAILS: " + "; ".join(verdict_c0(c0)) if verdict_c0(c0) else "done")
        print("   after c12:", {n: at(c1, n) for n in ("T", "C", "P12", "SP", "Q", "RB12", "RB_ST")}, "DT", c1.get(f.DT).p["power"])
    wo, _ = opened(build(swap=SLOW3))
    dif = f.diff(f.snapshot(base), f.snapshot(wo))
    print("\n== ctl 8: AP behind a 3-tick repeater: RB_ST lands at t8 j ahead of P12's head, whose landing updates the lit T")
    print("   open-state differences:", {k: dif[k] for k in sorted(dif, key=str)} or "none")
    print("\n== ctl 9: the input off n ticks after it went on (RB_ST lands at t10 j, 12 ticks after the input)")
    print("   after c0:", {n: "FAILS" if verdict_c0(run(opened(b, ticks=n)[0], staged(through=2)[:2])[0]) else "done"
                           for n in (8, 9, 10, 11, 12, 16)})
