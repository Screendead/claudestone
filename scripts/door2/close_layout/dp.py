"""DP, stage 2 of the close (door coords): what its on and off need and what the free cells allow. Built on
trigger.py; the chain of stages 0 and 1 is unchanged. No design is added here: this pass found none (see
docs/research/door_close_layout.md, "DP, stage 2"); the one found after it is dp_off.py. Everything printed is
computed on the simulator.

What-ifs set or clear SRC_P (-3,4,1) between two block events of one phase, which no command can do in the
game: they show which orders work, not how to get them.

On    DP lit before T's extension event is queued: P11 shoves the top row. Lit after that and before P12's
      retract event: T's head in (1,3,0) stops the push and P11 waits powered; NA's relight (RB_A landing,
      c2 j) updates P11 and P6 and they extend at c3. Lit after P12's retract event: they extend in c0.
      T's event is queued at level 1 and runs at level 2, so an on inside an event of level 2 or more is
      safe in every order; inside K's event (level 1) it depends on whether Z_T's ran before it.
Off   Before P11's extension event: P11 never fires. Between P11's and P6's: P11 is spat, P6's event finds
      no power and is dropped (NA extends P6 at c4). After P6's, up to two ticks later: both are spat.
Who   P12's retract event updates one free cell, (0,5,-1). A piston there can face up or down only and
      updates nothing at x < 0 but r_P10, its glass and the bus's glass. At x <= -2 the block events of c0
      are M_K's (level 0) and K's (level 1); the next is M_K's at c3 (RB12 landing beside it).
Source  A redstone block lights DP from (-3,4,1) or (-2,4,0); at (-2,4,0) it powers V and S. At (-3,4,1) it
      QC-powers M_K, so it cannot be there before c0. It can rest beside that cell only to the south
      (-3,4,2): above, it holds the bus lit; below, it holds M_K; either way the NP12 kill never comes.
Out   A piston under the block, (-3,3,1) facing up, is powered by FP and updated by DP's change: it fires
      with P11, ahead of P6, and its block lands beside the bus's last dust, which relights the bus. The
      others are the pusher south of the block (pulls it back) and a pusher at (-3,6,1) above a spacer.
      Of the free cells P11's and P6's extension events update, one, (-2,2,1) facing west, updates one of
      those three, the piston under the block, and nothing powers it there.
NA    A sticky piston at (-4,4,-1) facing east has the bus's stone above it and NA's dust north of it: it is
      powered except from c0 to c2 j. It pulls CP into the cut at c0 and pushes it out at c3, where DP reads
      NA: an on as a block event, three ticks after P12's retract, opening unchanged. DP then stays lit.
      CP's cell takes a block at once only from two cells away, and those are r_P10's glass, the bus's
      stone, NA's stone and a cell outside the box.

Run from the repo root (sim; replay-only):
python -m scripts.door2.close_layout.dp > scripts/door2/close_layout/dp.txt
The search over one and two added blocks is dp_search.py (about an hour on four cores); the two candidates it
passes are built and opened at the end here: both fail."""
import copy
from scripts.door2.close_layout import feeds as f, s_feed as s, trigger as t
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, add, DIRS, UPDATE_ORDER

P11, P6, P12 = (-2, 3, 0), (-2, 2, 0), (0, 5, 0)
LISTEN, P_W, A, RB_S, D_TOP = (0, 5, -1), (-4, 4, -1), (-3, 4, 3), (-3, 4, 2), (-3, 6, 1)
BUS_END, STAGE2 = (-4, 5, 1), ("P11", "P6")
# what dp_search.txt passes, with the piston at (-4,4,-1) plain or sticky: the same events
SEARCHED = {A: t.pis("sticky_piston", "north", "A_S"), RB_S: B("rb", id="RB_D"), P_W: t.pis("piston", "south", "X_S"),
            (-4, 4, 3): B("rb", id="RB_P")}
IDLE = [[(f.DRIVER, AIR)]] + [[] for _ in range(7)]            # c-1 .. c6, no DP command


class Levels(t.Probe):
    """Probe that numbers the block events of one tick, records each event's level and the cells it updates,
    and can run commands right after the n-th event (sim only)."""
    cur, n, counting, after = -1, 0, False, None

    def block_event(self, p, name, b0, fdir):
        key = (p, name, b0, fdir)
        if key not in self.events:
            self.lvl[key] = self.cur + 1 if self.phase == "g" else 0
        World.block_event(self, p, name, b0, fdir)

    def trigger(self, p, st, b0, fdir):
        self.cur = self.lvl.get((p, st.n, b0, fdir), 0)
        self.seen = []
        World.trigger(self, p, st, b0, fdir)
        self.order.append((self.tick_no, self.cur, f"{st.p.get('id', st.n)} ev{b0}", p, self.seen))
        self.seen = None
        if self.counting:
            self.n += 1
            for c, blk in (self.after or {}).get(self.n, ()):
                self.set(c, blk, 3)

    def neighbor_changed(self, p):
        if self.seen is not None and p not in self.seen:
            self.seen.append(p)
        World.neighbor_changed(self, p)


def levels(w, ticks=IDLE, after=None, count=1, **kw):
    """a copy of w through ticks; `after` {n: [(cell, block)]} acts after the n-th event of tick `count` (1 = c0)."""
    w = copy.deepcopy(w)
    w.__class__ = Levels
    w.reverse, w.ia_last = kw.get("reverse", False), kw.get("ia_last", False)
    w.lvl, w.order, w.seen, w.after, w.said = {}, [], None, after, []
    for k, cmds in enumerate(ticks):
        w.log.clear()
        for c, blk in cmds:
            w.cmd_set(c, blk)
        w.tick_no, w.counting = k - 1, k == count
        w.tick()
        w.said += [f"c{k - 1} {m}" for (_, ph, m) in w.log if any(x in m for x in ("EXTEND", "RETRACT")) and any(n + "@" in m for n in STAGE2)]
    return w


def names(w, tick=0):
    return [n for k, _, n, _, _ in w.order if k == tick]


def outcome(w):
    """stage 2 as the world has it 5 ticks after c0."""
    if t.at(w, "Q")[0] != (3, 3, 0):
        return "FAILS: top row shoved, Q at " + str(t.at(w, "Q")[0])
    got = {n: [x.split()[0] + {"EXTEND": " out", "RETRACT": " spat" if "SPIT" in x else " pulls back"}[x.split()[1]]
               for x in w.said if n + "@" in x] for n in STAGE2}
    out = "; ".join(f"{n} " + (", ".join(seq) + ("" if "c" in seq[-1] and "out" not in seq[-1] else ", stays out") if seq else "never fires")
                    for n, seq in got.items())
    return out + ("" if t.at(w, "S")[0] == (0, 3, 0) else "; S " + str(t.at(w, "S")[0]))


def free(w, occ, c):
    """an empty cell outside the opening's cells and the door plane."""
    return c not in w.b and c not in w.be and c not in occ and not (c[2] == 0 and -1 <= c[0] <= 3 and -1 <= c[1] <= 3)


def reach(u, facing):
    """cells a piston at u updates when it extends into an empty cell: its neighbours and its head's."""
    arm = add(u, DIRS[facing])
    return {add(u, x) for x in UPDATE_ORDER} | {add(arm, x) for x in UPDATE_ORDER}


def same_opening(b):
    wa, wb = d.make_world(t.build())[0], d.make_world(b)[0]
    for w in (wa, wb):
        w.run(4)
        w.cmd_set(f.DRIVER, t.RB)
    differ = []
    for k in range(t.OPEN_TICKS):
        wa.tick()
        wb.tick()
        differ += [k - 2] * bool(f.diff(f.snapshot(wa), f.snapshot(wb)))
    return f"differ at t{differ}" if differ else "the same at every tick"


if __name__ == "__main__":
    from scripts.door2 import volume as v
    b = t.build()
    _, occ = t.fixed()
    op, _ = t.opened(b)
    base = levels(op)
    c0 = [(lv, n) for k, lv, n, _, _ in base.order if k == 0]
    print("== c0 by level, the trigger chain with no DP command")
    print("  ", " | ".join(f"{lv} " + ", ".join(n for l2, n in c0 if l2 == lv) for lv in sorted({lv for lv, _ in c0})))
    west = [(k, lv, n) for k, lv, n, p, _ in base.order if p[0] <= -2]
    print("   block events at x <= -2 through c6:", "; ".join(f"c{k} level {lv} {n}" for k, lv, n in west))
    print("   updates of P11 and P6 from c-1 through c1:",
          [f"c{k} {n}" for k, _, n, _, seen in base.order if k <= 1 and (P11 in seen or P6 in seen)] or "none",
          "| at c2 j, NA's relight: P11 and P6 extend at c3 if DP is lit (below)")

    print("\n== on: SRC_P set right after the n-th block event of c0, never cleared")
    for n, name in enumerate(names(base), 1):
        w = levels(op, after={n: [(t.SRC_P, t.RB)]})
        print(f"   after {n:2} {name:8} ->", outcome(w))
    for label, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)), ("I_A's event last", dict(ia_last=True))):
        order = names(levels(op, **kw))
        print(f"   {label}: c0 runs {', '.join(order[:5])}, ...;",
              {f"after {order[n - 1]}": outcome(levels(op, after={n: [(t.SRC_P, t.RB)]}, **kw)).split(";")[0] for n in (4, 5)})

    on = names(base).index("P12 ev1") + 1
    lit = levels(op, after={on: [(t.SRC_P, t.RB)]})
    rest = names(lit)[on:]
    print(f"\n== off: SRC_P set after P12's retract event (c0 goes on: {', '.join(rest)}), cleared after the n-th")
    for n in range(on + 1, len(names(lit)) + 1):
        w = levels(op, after={on: [(t.SRC_P, t.RB)], n: [(t.SRC_P, AIR)]})
        print(f"   after {names(lit)[n - 1]:8} ->", outcome(w))
    for tick in (2, 3, 4):
        w = levels(op, ticks=[c + ([(t.SRC_P, AIR)] if k == tick else []) for k, c in enumerate(IDLE)], after={on: [(t.SRC_P, t.RB)]})
        print(f"   by command before c{tick - 1} ->", outcome(w))

    print("\n== who hears P12's retract event")
    heard = next(seen for k, _, n, _, seen in base.order if k == 0 and n == "P12 ev1")
    print("   cells it updates:", {c: op.get(c).p.get("id", op.get(c).n) for c in sorted(heard)})
    print("   free and outside the opening:", [c for c in sorted(heard) if free(op, occ, c)])
    print(f"   a piston at {LISTEN}, by facing:", "; ".join(
        f"{facing}: " + (f"updates at x < 0 {({c: op.get(c).n for c in sorted(reach(LISTEN, facing)) if c[0] < 0})}"
                         if op.get(add(LISTEN, DIRS[facing])).n == "air" else "front is " + op.get(add(LISTEN, DIRS[facing])).n)
        for facing in DIRS))

    print("\n== source: a redstone block beside DP, pistons it powers in the open state")
    for c in sorted(add(f.DP, x) for x in UPDATE_ORDER):
        if not free(op, occ, c):
            print(f"   {c}: {op.get(c).n}, {b.role.get(c, '')}")
            continue
        w = copy.deepcopy(op)
        w.cmd_set_silent(c, t.RB)
        print(f"   {c}: free; powers", sorted({f"{st.p['id']} {kind}" for p, st in w.b.items() if st.n in ("piston", "sticky_piston")
                                               for kind, q in power_sources(w, p) if q == c}) or "nothing",
              "| DP", "lit" if World.best_neighbor_signal(w, f.DP) else "dark")
    print("   resting beside (-3,4,1) from the opening on, then the close: after c0")
    for c in (RB_S, (-3, 5, 1), (-3, 3, 1)):
        w = copy.deepcopy(op)
        w.cmd_set(c, t.RB)
        w.run(2)
        w0 = levels(w, IDLE[:2])
        bad = t.verdict_c0(w0)
        print(f"   {c}:", "FAILS: " + "; ".join(bad[:4]) if bad else "stages 0 and 1 done;", "bus", w0.get(BUS_END).p["power"],
              "| M_K", t.at(w0, "M_K")[1:], "| DP", w0.get(f.DP).p["power"])

    w = copy.deepcopy(op)
    w.cmd_set_silent(A, t.pis("sticky_piston", "north", "A"))
    print(f"   the pusher's cell {A}: powered in the open state by", [c for _, c in power_sources(w, A)] or "nothing",
          "| updated in c0 by", [n for k, _, n, _, seen in base.order if k == 0 and A in seen],
          "| its power cells:", {c: op.get(c).n for c in sorted(add(A, x) for x in UPDATE_ORDER) if c != RB_S and c[2] <= 3})
    w = copy.deepcopy(op)
    w.cmd_set((-2, 4, 3), t.STONE)
    print("   a stone at (-2,4,3), east of it: NP12's dust (-1,4,3) reads", w.get((-1, 4, 3)).p["power"], "(open state", str(op.get((-1, 4, 3)).p["power"]) + ")")

    print("\n== out: the block real at (-3,4,1) after P12's retract event, then")
    y = levels(op, ticks=IDLE, after={on: [(t.SRC_P, t.RB), ((-3, 3, 1), t.pis("piston", "up", "Y"))]})
    print("   a piston under it, (-3,3,1) facing up (FP powers it, DP's change updates it):", outcome(y),
          "| the block lands at", y.find("Y")[0] and [c for c, st in y.b.items() if st.n == "rb" and c[0] == -3 and c[2] == 1],
          "| bus", y.get(BUS_END).p["power"], "| P_R", t.at(y, "P_R")[1:], "M_K", t.at(y, "M_K")[1:])
    woken = {}
    for who, name in ((P11, "P11 ev0"), (P6, "P6 ev0")):
        seen = next(sn for k, _, n, _, sn in lit.order if k == 0 and n == name)
        seen = seen[seen.index(P6) + 1:] if who == P11 else seen
        woken[name] = [c for c in seen if free(lit, occ, c) and c != t.SRC_P]
    print("   free cells updated by P11's extension event after P6 is queued, and by P6's:", woken)
    actors = {A: "the pusher south of the block", D_TOP: "a pusher above the spacer", (-3, 3, 1): "a pusher under it"}
    hits = [(u, facing, a) for cells in woken.values() for u in cells for facing in DIRS for a in actors
            if lit.get(add(u, DIRS[facing])).n == "air" and a in reach(u, facing)]
    print("   pistons there whose extension updates", ", ".join(f"{a} ({why})" for a, why in actors.items()) + ":", hits or "none")
    print("   power in the open state on those cells:", {u: sorted({c for _, c in power_sources(w, u)})
                                                         for cells in woken.values() for u in cells
                                                         for w in [copy.deepcopy(op)] if not w.cmd_set_silent(u, t.pis("piston", "up", "X"))})

    print("\n== NA: a sticky piston at (-4,4,-1) facing east, CP in front of it")
    bw = t.build(swap={P_W: t.pis("sticky_piston", "east", "P_W")})
    cl, moved = d.make_world(bw)
    wo, _ = t.opened(bw)
    print("   moved during load:", moved or "none", "| closed state: CP at", [c for c in ((-3, 4, -1), (-2, 4, -1)) if cl.get(c).n == "stone"],
          "DP", cl.get(f.DP).p["power"], "P11", t.at(cl, "P11")[1:], "powered by", [c for _, c in power_sources(cl, P_W)])
    print("   opening:", f.diff(f.snapshot(op), f.snapshot(wo)) or "open-state diff none;", same_opening(bw) + ";",
          "DP", wo.get(f.DP).p["power"], "| powered by", [c for _, c in power_sources(wo, P_W)],
          "| box", s.box(set(v.cumulative_cells(bw)[0])))
    wn = levels(wo)
    print("   close:", "; ".join(f"c{k} level {lv} {n}" for k, lv, n, p, _ in wn.order if n.split()[0] in ("P_W", "P12") + STAGE2), "->",
          outcome(wn), "| after c0", "FAILS" if t.verdict_c0(levels(wo, IDLE[:2])) else "stages 0 and 1 done", "| DP", wn.get(f.DP).p["power"])
    print("   close, other orders:", {label: outcome(levels(wo, **kw)) for label, kw in (
        ("dust reversed", dict(reverse=True)), ("I_A last", dict(ia_last=True)), ("both", dict(reverse=True, ia_last=True)))})
    print("   in line with CP's cell, two away:", {c: (op.get(c).n if c[0] >= -4 else "outside the box") + " " + b.role.get(c, "")
                                                     for c in ((-5, 4, -1), (-1, 4, -1), (-3, 6, -1), (-3, 2, -1))},
          "| under it:", op.get((-3, 3, -1)).n)

    print("\n== the search's two passes (sticky pusher (-3,4,3) north, redstone blocks (-3,4,2) and (-4,4,3), piston (-4,4,-1) south), built")
    bs = t.build(swap=SEARCHED)
    cl, moved = d.make_world(bs)
    print("   moved during load:", moved or "none", "| closed state: DP", cl.get(f.DP).p["power"], "| opening:", same_opening(bs))
    row = [(-4, 4, z) for z in range(0, 5)]
    print("   the row that piston pushes at c3 in the search:", {c: (op.get(c).n if c[2] <= 3 else "outside the box") +
                                                               (" under " + op.get(add(c, (0, 1, 0))).n if add(c, (0, 1, 0)) in op.b else "")
                                                               for c in row}, "| (-4,4,2) is G's rest cell, (-4,4,3) the pusher's power")
