"""S's H2 feed for the close: option (a) of docs/research/door_close_layout.md (door coords).

At close stage 5 V spits S into (1,3,0). S must fire there in the same phase (H2), push C from (1,2,0) to
(1,1,0), and be spat itself within 2 gt, so that (1,2,0) is free for TM. S's only power cell that is not a
wall, a door block or a moving piston is DS (1,4,1), the opening's dust on the wall block (1,3,1) beside S
(constraints.txt). Of DS's free neighbours only (1,5,1), above it, lights it without powering a piston that
still has to wait or fire (it is a QC cell of T, which has fired by then), and a redstone block can rest
beside (1,5,1) through the opening only to the south. Both are computed below.

The feed is two blocks; two more pull it out inside the phase. design_c's opening and the nine close-feed
blocks are unchanged:
  F_S    sticky piston (1,5,3) facing north, retracted
  RB_F   redstone block (1,5,2): pushed by F_S; real at (1,5,1) at once if F_S is depowered within 2 gt (spat)
  G_S    sticky piston (3,5,1) facing west, extended, head (2,5,1): pulls RB_F out to (2,5,1) when its hold goes
  HOLD_G redstone block (3,6,1): G_S's hold (stand-in for whatever the close chain removes, like P_R's HOLD)

Three drives:
  A  F_S spits RB_F; G_S pulls it out, at most 2 gt after S fires. Each acts inside its own block event, so S
     can fire and be spat in one phase. RB_F ends parked at (2,5,1), where it QC-powers P7 (and Z_S): P7 must
     have fired before RB_F lands there (2 gt after the pull) or get no update until its stage, and RB_F must
     go home before the next opening: HOLD_G back (G_S pushes it to (1,5,1)), then any pulse on F_S.
  B  F_S spits RB_F; F_S's second pulse pulls it home, at most 2 gt after S fires. F_S lands 2 gt after the
     spit, so with pulses set between ticks the pull comes 4 gt or more after the spit. No G_S.
  C  F_S pushes RB_F and stays out; RB_F lands 2 gt later; F_S's release, at most 2 gt after S fires, pulls it
     home. RB_F must land after T's retract event, so F_S starts 2 gt before it at the earliest. No G_S.
Wake: S spat onto the lit cell checks itself on landing; S already real is updated by DS's change (S is 2 from
DS). A pull updates RB_F's old cell, DS goes dark inside the puller's event, and that change updates S again,
so S's retract is queued there and spits C. DS's changes also update T, P7, Z_S, Z_T and G_S (through its
head).
T: RB_F at (1,5,1) is a QC cell of T and DS points into T. RB_F real there before T's retract event cancels
the retract (ctl 4). T lands 2 gt after that event; if DS is lit then, S must be in (1,3,0), moving in,
extended or retracting, or T fires again into the empty cell (ctl 5). An S that lands on the lit cell later
queues its own extension before T is updated, and T's push then fails on the extended S (windows, S late).
Only S at rest under a landed T when DS lights is open: dust's update order picks which fires first (ctl 6).

Probe stand-ins, set by command between ticks: SRC_F (1,6,3) above F_S; SRC_10 (-1,5,1) beside P10; SRC_V
(-1,3,1) beside V's firing cell; POKE (1,5,0), a glass block set and cleared above T (the update T's depower
must deliver, still-needed item 3); and feeds.py's SRC_T, SRC_P, RB_A, RB12 and puller.py's HOLD.
Run from the repo root (sim; replay-only):
python -m scripts.door2.close_layout.s_feed > scripts/door2/close_layout/s_feed.txt"""
import copy, functools
from scripts.door2.close_layout import feeds as f, puller as pr
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World

F_S, RB_F, LIT, G_S, G_HEAD, HOLD_G, PARK = (1, 5, 3), (1, 5, 2), (1, 5, 1), (3, 5, 1), (2, 5, 1), (3, 6, 1), (2, 5, 1)
DS, P7, Z_S = (1, 4, 1), (2, 4, 0), (2, 4, 2)
SRC_F, SRC_10, SRC_V, POKE = (1, 6, 3), (-1, 5, 1), (-1, 3, 1), (1, 5, 0)
F_BLOCK = B("sticky_piston", facing="north", extended=False, id="F_S")
ADDED = {F_S: F_BLOCK, RB_F: B("rb", id="RB_F"),
         G_S: B("sticky_piston", facing="west", extended=True, id="G_S"),
         G_HEAD: B("piston_head", facing="west", sticky=True), HOLD_G: B("rb")}
# the same blocks as drive A leaves them: RB_F parked in front of the retracted G_S, hold gone
PARKED = {F_S: F_BLOCK, PARK: B("rb", id="RB_F"), G_S: B("sticky_piston", facing="west", extended=False, id="G_S")}
RB, GLASS = B("rb"), B("glass")
CELL = {f.RB_A: "RB_A", f.RB12: "RB12", f.SRC_P: "SRC_P", f.SRC_T: "SRC_T", pr.HOLD: "HOLD", SRC_F: "SRC_F",
        SRC_10: "SRC_10", SRC_V: "SRC_V", POKE: "POKE", HOLD_G: "HOLD_G"}
SHOW = ("EXTEND", "RETRACT", "cancel", "failed", "dropped", f"wire {DS}")
SHOW_AT = {"queue": ((1, 3, 0), (1, 4, 0)), "land": ((1, 4, 0), (1, 3, 0), (1, 2, 0), (1, 1, 0), LIT, PARK, RB_F)}
ON, OFF, PULL = (SRC_F, RB), (SRC_F, AIR), (HOLD_G, AIR)


def staged(*drive, late=0, v_off=None):
    """The close through stage 4, one stage's event per tick (each tick: its commands, then the tick), plus the
    feed's commands: (tick, command), or (tick, command, "first") to put it ahead of that tick's stage commands.
    T's retract event is k3 g and T lands at k5 j. `late` delays stages 3 and 4; V's block goes at v_off (default
    k5 + late), which spits S into (1,3,0) if S has not landed there by itself."""
    v_off = v_off or 5 + late
    out = [[] for _ in range(max(9, max([v_off] + [k for k, *_ in drive]) + 3))]
    out[0] = [(f.RB_A, AIR), (f.RB12, AIR), (f.SRC_P, RB)]       # k1: 0 P12 retracts; 2 P11 (and P6) extend
    out[1] = [(f.SRC_P, AIR), (f.SRC_T, RB), (pr.HOLD, AIR)]     # k2: P11, P6 spat, S real at (0,3); 1 T extends
    out[2] = [(f.SRC_T, AIR), (POKE, GLASS), (POKE, AIR)]        # k3: T spat, C real at (1,2)
    out[2 + late].append((SRC_10, RB))                           # k3: 3 P10 extends
    out[3 + late] += [(SRC_V, RB), (SRC_10, AIR)]                # k4: P10 spat; 4 V lands lit and fires
    out[v_off - 1].append((SRC_V, AIR))                          # k5: V spat, S real at (1,3,0)
    for k, cmd, *first in drive:
        if first:
            out[k - 1].insert(0, cmd)
        else:
            out[k - 1].append(cmd)
    return out


def drive_a(spit=5, pull=6, first=False, **kw):
    """F_S on for the tick before `spit`; G_S's hold removed at `pull` (0: never)."""
    return staged((spit - 1, ON), (spit, OFF, "first") if first else (spit, OFF), *([(pull, PULL)] if pull else []), **kw)


def drive_b(spit=3, release=7, **kw):
    return staged((spit - 1, ON), (spit, OFF), (release - 1, ON), (release, OFF), **kw)


def drive_c(start=2, release=6, **kw):
    return staged((start, ON), (release, OFF), **kw)


# name: (title, schedule, where RB_F and G_S must end)
CASES = {
    "A": ("drive A: RB_F spat before S lands (S fires on landing), pulled by G_S 1 gt later", drive_a(first=True), "parked"),
    "A2": ("drive A, S spat first, then RB_F (S is woken by DS's change)", drive_a(), "parked"),
    "B": ("drive B: RB_F spat right after T's retract event (k3), S lands lit at k5, F_S's second pulse pulls RB_F home",
          drive_b(), "home"),
    "C": ("drive C: F_S out from k2, RB_F lands at k4 j, S lands lit at k5, F_S's release pulls RB_F home", drive_c(), "home"),
}
CONTROLS = {
    "ctl 1": ("no feed (SRC_F never set)", staged(), "home"),
    "ctl 2": ("drive A, RB_F not pulled (HOLD_G stays)", drive_a(first=True, pull=0), "parked"),
    "ctl 3": ("drive A, pull 3 gt after S fires: a landed C is pulled back", drive_a(first=True, pull=8), "parked"),
    "ctl 4": ("wrong order: RB_F spat before T's retract event", staged((2, ON), (3, OFF, "first"), (6, PULL)), "parked"),
    "ctl 5": ("drive C with stages 3 and 4 two ticks late: T lands at k5 j, lit, over an empty (1,3,0)",
              drive_c(release=8, late=2), "home"),
    "ctl 6": ("drive C started in the tick of T's retract: RB_F lands at k5 j, after T, with S at rest", drive_c(start=3), "home"),
}


class Probe(World):
    """World that records the pistons a change of DS updates, and can run dust's neighbour updates in reverse
    order (the game walks a HashSet there; sim.py a fixed order)."""
    reverse = False
    storm = 0
    woken = None

    def wire_update(self, p):
        self.storm += p == DS
        if not self.reverse:
            World.wire_update(self, p)
        else:
            calls = []
            self.update_neighbors = lambda q, skip=None: calls.append(q)
            try:
                World.wire_update(self, p)
            finally:
                del self.update_neighbors
            for q in reversed(calls):
                self.update_neighbors(q)
        self.storm -= p == DS

    def check_extend(self, p):
        if self.storm and self.woken is not None:
            st = self.get(p)
            self.woken.append(st.p.get("id", st.n))
        World.check_extend(self, p)


@functools.lru_cache(None)
def fixed():
    """design_c + the nine close-feed blocks (puller.build), and every cell its opening occupies."""
    from scripts.door2 import volume as v
    b = pr.build()
    return b, frozenset(v.cumulative_cells(b)[0])


def build(mine=ADDED):
    """a copy of fixed() with this feed's blocks added."""
    b0, occ = fixed()
    b = copy.deepcopy(b0)
    for p, st in mine.items():
        assert p not in b.b and p not in occ, p
        b.b[p] = st
        b.role[p] = "s_feed"
    return b


def say(cmds):
    return ", ".join("POKE " + ("set" if st.n == "glass" else "clear") if p == POKE else
                     CELL[p] + (" off" if st.n == "air" else " on") for p, st in cmds)


def shown(m):
    return any(k in m for k in SHOW) or any(k in m and any(str(c) in m for c in cs) for k, cs in SHOW_AT.items())


def run(w, ticks, reverse=False):
    """a copy of w taken through ticks: (world, lines per tick, pistons each tick's DS changes updated,
    (blocks, moving cells) after each tick)."""
    w = copy.deepcopy(w)
    w.__class__ = Probe
    w.reverse = reverse
    lines, woken, frames = [], [], []
    for k, cmds in enumerate(ticks, 1):
        w.log.clear()
        w.woken = []
        for p, st in cmds:
            w.cmd_set(p, st)
        w.tick()
        lines.append([f"k{k} [{say(cmds)}]"] + [f"   k{k}{ph} {m}" for (t, ph, m) in w.log if shown(m)])
        woken.append(sorted(set(w.woken)))
        frames.append((dict(w.b), set(w.be)))
    return w, lines, woken, frames


def at(w, ident):
    p, kind = w.find(ident)
    return p, kind, (w.get(p).p.get("extended") if kind == "real" else None)


NEED = {"S": ((1, 3, 0), "real", False), "C": ((1, 1, 0), "real", None), "T": ((1, 4, 0), "real", False),
        "V": ((-1, 3, 0), "real", False), "P12": ((0, 5, 0), "real", False), "SP": ((0, 4, 0), "real", None),
        "P7": (P7, "real", False), "TR": ((2, 3, 0), "real", None), "P8": ((3, 4, 0), "real", False),
        "Q": ((3, 3, 0), "real", False), "TM": ((3, 2, 0), "real", None), "F_S": (F_S, "real", False)}
END = {"parked": {"RB_F": (PARK, "real", None), "G_S": (G_S, "real", False)},
       "home": {"RB_F": (RB_F, "real", None), "G_S": (G_S, "real", True)}}


def verdict(w, end):
    """what keeps the world from the state the close needs after stage 5; empty when S's H2 is done."""
    bad = [f"{n} {at(w, n)}" for n, want in {**NEED, **END[end]}.items() if at(w, n) != want]
    if w.get((1, 2, 0)).n != "air":
        bad.append(f"(1,2,0) {w.get((1, 2, 0))}")
    return bad


def events(lines):
    return [x for tick in lines for x in tick if "EXTEND" in x or "RETRACT" in x]


def box(cells):
    lo = [min(c[i] for c in cells) for i in range(3)]
    hi = [max(c[i] for c in cells) for i in range(3)]
    dims = [h - l + 1 for l, h in zip(lo, hi)]
    return f"x {lo[0]}..{hi[0]} y {lo[1]}..{hi[1]} z {lo[2]}..{hi[2]} -> {dims[0]} x {dims[1]} x {dims[2]} = {dims[0] * dims[1] * dims[2]}"


def cell_diff(a, b_, skip=()):
    return sorted(p for p in set(a.b) | set(b_.b) if p not in skip and a.b.get(p) != b_.b.get(p)) or "none"


def poke(w, p=(2, 5, 0)):
    """one neighbour update beside P7 (a glass block set and cleared above it); True if P7 then extends."""
    w = copy.deepcopy(w)
    w.cmd_set(p, GLASS)
    w.cmd_set(p, AIR)
    w.run(3)
    return at(w, "P7")[2]


def reset(w):
    """drive A's return: HOLD_G back (G_S pushes RB_F to (1,5,1)), 3 ticks, a 1-tick pulse on F_S, 3 ticks."""
    w.log.clear()
    for cmd, n in (((HOLD_G, RB), 3), (ON, 1), (OFF, 3)):
        w.cmd_set(*cmd)
        w.run(n)
    return [f"   {ph} {m}" for (t, ph, m) in w.log if "EXTEND" in m or "RETRACT" in m]


def opened(w, ticks=14):
    w.run(4)
    w.cmd_set(f.DRIVER, RB)
    w.run(ticks)
    return w


if __name__ == "__main__":
    from scripts.door2 import volume as v
    base = f.open_world(build({}))
    b = build()
    mine = f.open_world(b)
    print("opening, design_c + close feeds vs + S feed, open-state differences:", f.diff(f.snapshot(base), f.snapshot(mine)) or "none")
    print("cell differences outside the added blocks:", cell_diff(base, mine, ADDED))
    print("added blocks in the open state:", {p: (mine.get(p), power_sources(mine, p) if mine.get(p).n == "sticky_piston" else "")
                                              for p in ADDED})
    w, moved = d.make_world(b)
    seen = {F_S: set(), G_S: set()}
    print("Z_S in the closed state is QC-powered by", [c for _, c in power_sources(w, Z_S)], "(ARM_ZS (2,6,2); RB_F (1,5,2))")
    w.run(4)
    w.cmd_set(f.DRIVER, RB)
    for _ in range(15):
        for p in seen:
            seen[p] |= {c for _, c in power_sources(w, p)}
        w.tick()
    print("moved during load:", moved or "none", "| power on F_S at every tick, closed state to open state:",
          sorted(seen[F_S]) or "none", "| on G_S:", sorted(seen[G_S]))
    cells = set(v.cumulative_cells(b)[0])
    print("box, opening:", box(cells))
    w, _, _, _ = run(mine, staged()[:2])
    hits = {}
    for c in ((0, 4, 1), (2, 4, 1), LIT):
        w2 = copy.deepcopy(w)
        w2.cmd_set_silent(c, RB)
        hits[c] = [f"{st.p['id']}@{p} {kind}" for p, st in sorted(w2.b.items()) if st.n in ("piston", "sticky_piston")
                   for kind, q in power_sources(w2, p) if q == c]
    print("why (1,5,1): a redstone block at each free neighbour of DS, after k2 (S waiting at (0,3,0), T out), powers:", hits)
    rests = {}
    for c in (RB_F, (2, 5, 1), (1, 6, 1), (1, 5, 0)):
        dif = f.diff(f.snapshot(base), f.snapshot(f.open_world(build({c: RB}))))
        rests[c] = sorted(k for k in dif if isinstance(k, str)) or "none"
    print("why from the south: a redstone block resting at each free neighbour of (1,5,1) through the opening, pistons "
          "whose open state changes:", rests, "((0,5,1) is NP12's glass)")

    done = {}
    for name, (title, ticks, end) in CASES.items():
        done[name] = run(mine, ticks)
        for blocks, _ in done[name][3]:
            cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print("box, opening + drives A, B and C (stand-in sources included):", box(cells))
    ref_lines = done["A"][1]

    def report(name, title, ticks, end, reverse=False):
        w2, lines, woken, _ = done[name] if name in done and not reverse else run(mine, ticks, reverse)
        first = 0 if name == "A" else next((i for i, (x, y) in enumerate(zip(lines, ref_lines)) if x != y), len(ref_lines))
        print(f"\n== {name}: {title}" + (f" (as A through k{first})" if first else ""))
        for tick in lines[first:]:
            if len(tick) > 1 or not tick[0].endswith("[]"):
                print("\n".join(tick))
        lit = [f"k{k} {names}" for k, names in enumerate(woken, 1) if names]
        print("   pistons updated by DS's changes:", "; ".join(lit) or "none")
        bad = verdict(w2, end)
        print("   ->", "FAILS: " + "; ".join(bad) if bad else
              f"S H2 done: S real at (1,3,0), retracted; C real at (1,1,0); (1,2,0) air; T in; RB_F {end}; "
              "V, P12, SP, P7, TR, P8, Q, TM where the close needs them")

    def res(ticks, end):
        return "FAILS" if verdict(run(mine, ticks)[0], end) else "done"

    for name, case in CASES.items():
        report(name, *case)
    print("\n== after each drive: one neighbour update beside P7 (glass set and cleared at (2,5,0)); P7 extends:",
          {name: poke(done[name][0]) for name in CASES})
    print("\n== windows (done: the end state above; T's retract event is k3 g, T lands at k5 j)")
    print("   A, S fires at k5, G_S's pull 1/2/3 gt after:", "; ".join(
        f"RB_F spat at k{k} " + "/".join(res(drive_a(k, p), "parked") for p in (6, 7, 8)) for k in (3, 4, 5)))
    print("   B, S fires at k5, F_S's second release 2/3 gt after:", "; ".join(
        f"RB_F spat at k{k} " + "/".join(res(drive_b(k, r), "home") for r in (7, 8)) for k in (3, 4)))
    print("   C, S fires at k5, F_S's release 1/2/3 gt after:", "; ".join(
        f"F_S out from k{k} " + "/".join(res(drive_c(k, r), "home") for r in (6, 7, 8)) for k in (1, 2, 3)),
        "(out from k3 is ctl 6: dust's update order decides)")
    print("   S late under a DS lit before T lands, pull or release 1 gt after S fires; S spat at k6 / landing by itself "
          "at k6 j and firing at k7:",
          "A, RB_F spat at k3", "/".join(res(drive_a(3, v_ + 1, v_off=v_), "parked") for v_ in (6, 7)) + ";",
          "B, RB_F spat at k3", "/".join(res(drive_b(3, v_ + 1, v_off=v_), "home") for v_ in (6, 7)) + ";",
          "C, F_S out from k2", "/".join(res(drive_c(2, v_ + 1, v_off=v_), "home") for v_ in (6, 7)))
    for name, case in CONTROLS.items():
        report(name, *case)
    report("ctl 6", CONTROLS["ctl 6"][0] + "; dust's neighbour updates in reverse order", *CONTROLS["ctl 6"][1:], reverse=True)
    print("\n== dust's neighbour updates in reverse order, every other schedule: events and end-state cells",
          {name: "same" if events(lr) == events(lf) and cell_diff(wf, wr) == "none" else "DIFFER"
           for name, (title, ticks, end) in {**CASES, **CONTROLS}.items() if name != "ctl 6"
           for (wf, lf, _, _), (wr, lr, _, _) in [(run(mine, ticks), run(mine, ticks, reverse=True))]})

    print("\n== drive A's return: the closed state loaded as A leaves the feed (RB_F at (2,5,1), G_S in, no hold), then the reset")
    ref, _ = d.make_world(b)
    ref.run(7)
    parked = build(PARKED)
    wp, moved_p = d.make_world(parked)
    print("   moved during load:", moved_p or "none", "| P7 powered by", [c for _, c in power_sources(wp, P7)],
          "| Z_S by", [c for _, c in power_sources(wp, Z_S)])
    for line in reset(wp):
        print(line)
    print("   cells differing from the loaded closed state of the standard build:", cell_diff(ref, wp))
    print("   opening after the reset, open-state differences:", f.diff(f.snapshot(mine), f.snapshot(opened(wp))) or "none")
    wn, _ = d.make_world(parked)
    dif = f.diff(f.snapshot(mine), f.snapshot(opened(wn)))
    print("   ctl: opening from the parked state without the reset, open-state differences:",
          {k: dif[k] for k in sorted(dif, key=str)} or "none")
