"""Where U_Y's hold and B_Y's source can come from (door coords): the screens behind y12_holds.py. Everything is
computed on y12.py's build without its stand-in hold (1 to 3) or on y12_holds.py's build (4 and 5), in the
simulator; nothing here ran on a server.

U_Y   1. Every free cell within two steps of U_Y: whether a redstone block there powers U_Y, and whether setting or
         taking it updates U_Y (it is beside U_Y or beside U_Y's head, which passes an update on). Silent: it
         powers U_Y without an update.
      2. For each silent cell, each one-step move of a redstone block out of it by a sticky piston, pushed from the
         cell behind it or pulled by a piston two cells away: what stands in the piston's cell and in the cell the
         block goes to at any tick of y12.py's run, and what a redstone block in that cell powers.
      3. The cells that a neighbour update reaches from W_Y's extension at c58 g (where U_Y must still be powered)
         to the end of c59, and the scheduled ticks due in c59, in y12.py's run with its hold and no command: a hold
         that a sticky piston moves out and back is gone for 5 gt at least, so without another source for c58 it
         has to leave in that window and be home by c64 j.
B_Y   4. Every cell from which a repeater reads Y_G, S_W, S_F, Y_X or the tap's stone (its back is one of them), its
         support and where its output goes.
      5. Every single block (dust, dot, stone, redstone block, repeater of each facing and delay, piston and sticky
         piston of each facing) in every free cell up to two steps from B_Y, from the cell above it or from Y_G, z 5
         at most, on y12_holds.py's build without B_Y's 7 blocks, run from the input with no command.
Run from the repo root (sim; about 5 minutes):
python -m scripts.door2.close_layout.y12_holds_search > scripts/door2/close_layout/y12_holds_search.txt"""
import copy
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, returns as r, rbt_drives as rd, west_drives as wd, y12 as y, y12_holds as h
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, DIRS, add

RESERVED = ((-2, 6, 1), (-2, 7, 1), (-2, 7, 2))                     # kept free for Z11's down-pusher (y12.py)
HORIZONTAL = ("north", "south", "east", "west")


def near(c, k=2):
    return [(c[0] + dx, c[1] + dy, c[2] + dz) for dx in range(-k, k + 1) for dy in range(-k, k + 1) for dz in range(-k, k + 1)
            if 0 < abs(dx) + abs(dy) + abs(dz) <= k]


def adjacent(a, b_):
    return sum(abs(p - q) for p, q in zip(a, b_)) == 1


def taken_by(b, w):
    """every cell the closed state, the opening or the run `w` fills at any tick."""
    from scripts.door2 import volume as v
    cells = set(d.full_blocks(b)) | set(d.make_world(b)[0].b) | set(v.cumulative_cells(b)[0])
    for blocks, be in w.frames:
        cells |= set(blocks) | be
    return cells


def status(c, taken):
    if c in RESERVED:
        return "kept free"
    if c in taken:
        return "taken"
    if r.plane_or_hall(c):
        return "door plane or hallway"
    return "free" + " (z 4)" * (c[2] == 4) + " (z 5)" * (c[2] == 5)


def rb_powers(w, c):
    """what a redstone block at c powers: pistons (labels) and dust beside it."""
    x = copy.deepcopy(w)
    x.cmd_set_silent(c, B("rb", id="X"))
    out = [st.p.get("id", st.n) + f"@{p}" for p, st in x.b.items() if st.n in ("piston", "sticky_piston") and c in [q for _, q in power_sources(x, p)]]
    out += [f"dust@{p}" for p in (add(c, dv) for dv in DIRS.values()) if x.get(p).n == "redstone_wire"]
    return out


def screen_u():
    yb = y.build(drop=(y.HOLD,))
    cl = d.make_world(yb)[0]
    _, yw, _ = y.run(y.build())
    taken = taken_by(yb, yw) - {y.HOLD, y.SRC_B}
    head = y.U_HEAD
    print("== 1. cells within two steps of U_Y (-2,6,2): a redstone block there powers U_Y? silently?")
    silent = []
    for c in sorted(near(y.U_Y)):
        if cl.get(c).n != "air" or c == head:
            continue
        x = copy.deepcopy(cl)
        x.cmd_set_silent(c, B("rb", id="X"))
        if not power_sources(x, y.U_Y):
            continue
        loud = adjacent(c, y.U_Y) or adjacent(c, head)
        print(f"   {c}: powers U_Y, " + ("updates it (beside U_Y or its head)" if loud else "without an update") + f"; {status(c, taken)}"
              + f"; also powers {[p for p in rb_powers(cl, c) if not p.startswith('U_Y')] or 'nothing else'}")
        if not loud:
            silent.append(c)
    print("   silent cells:", silent)
    print("\n== 2. one-step moves of a redstone block out of each silent cell by a sticky piston")
    movers = {}
    for q in silent:
        for name, dv in DIRS.items():
            away = add(q, dv)
            for kind, pc, facing in (("push", add(q, dv, -1), name), ("pull", add(q, dv, 2), [n for n, e in DIRS.items() if e == tuple(-a for a in dv)][0])):
                movers[(q, kind, pc)] = away
                pw = [p for p in rb_powers(cl, away) if not p.startswith("U_Y")] if cl.get(away).n == "air" and away not in RESERVED else None
                print(f"   {q} {kind} {facing}: piston at {pc} ({status(pc, taken) if cl.get(pc).n == 'air' else cl.get(pc).n}), block to {away} "
                      f"({status(away, taken) if cl.get(away).n == 'air' else cl.get(away).n}" + (f"; a redstone block there powers {pw or 'nothing'}" if pw is not None else "")
                      + ")" + (" | piston beside U_Y or its head" if adjacent(pc, y.U_Y) or adjacent(pc, head) else ""))
    usable = {(q, k, pc): a for (q, k, pc), a in movers.items() if q not in RESERVED and not rb_powers(cl, a) and all(
        cl.get(c).n == "air" and c not in taken and c not in RESERVED and not r.plane_or_hall(c) for c in (pc, a))}
    print("   usable (the hold's cell, the piston's and the away cell not kept free, the last two free at every tick, the block there powering "
          "nothing that stands):", "; ".join(f"{q} {k} from {pc} to {a}" for (q, k, pc), a in usable.items()) or "none",
          "| the away cells (-2,8,1) and (-1,7,1) are one step from (-2,7,1): a block there would power a piston at (-2,6,1) by QC")

    print("\n== 3. updates from W_Y's extension at c58 g to the end of c59, y12.py's build with its hold and no command")
    reached, state = [], {"on": False}
    orig_nc, orig_tr = World.neighbor_changed, World.trigger

    def nc(self, p):
        if state["on"]:
            reached.append((self.tick_no, self.phase, p))
        return orig_nc(self, p)

    def tr(self, p, st, b0, fc):
        if getattr(self, "tick_no", None) == 58 and st.p.get("id") == "W_Y" and b0 == 0:
            state["on"] = True
        return orig_tr(self, p, st, b0, fc)

    def due(w):
        print("   scheduled ticks due in c59:", [(x[3], x[4]) for x in w.sched if x[0] <= w.time + 1] or "none")

    World.neighbor_changed, World.trigger = nc, tr
    try:
        wd.noted(t.opened(y.build())[0], pp.idle(59), before={59: due})
    finally:
        World.neighbor_changed, World.trigger = orig_nc, orig_tr
    cells = sorted({p for _, _, p in reached})
    print(f"   {len(cells)} cells reached:", cells)
    print("   the usable pistons' cells among them:", [pc for (q, k, pc) in usable if pc in cells] or "none",
          "| so a hold moved by one of them leaves before c58 g, when U_Y needs another source, or after c59, when it is home at c65 j at the "
          "earliest, after W_Y's retract at c65 g, U_Y's last update before it would push ARM_Z11 back")


def screen_b():
    hb = h.build()
    cl = d.make_world(hb)[0]
    _, hw, _ = h.run(hb)
    taken = taken_by(hb, hw) - set(h.SOURCE_B)
    print("\n== 4. cells from which a repeater reads a lit block of the west line's timer or the tap")
    for name, c in (("Y_G", wd.Y_G), ("S_W", y.S_W), ("S_F", y.S_F), ("Y_X", wd.Y_X), ("the tap's stone", (-3, 6, 3))):
        for facing in HORIZONTAL:
            p = add(c, DIRS[facing], -1)                       # the repeater's back (input) is c
            out = add(p, DIRS[facing], -1)
            if cl.get(p).n != "air" and p not in h.SOURCE_B:
                continue
            sup = add(p, DIRS["down"])
            print(f"   {name}: repeater at {p} facing {facing} ({status(p, taken)}), on {cl.get(sup).n if sup not in h.SOURCE_B else 'glass G_B'} at {sup}, "
                  f"output into {out} ({status(out, taken) if cl.get(out).n == 'air' else cl.get(out).n})")
    print("   (a repeater on a repeater or on dust has no support in the game)")

    print("\n== 5. one block near B_Y, on y12_holds.py's build without B_Y's 7 blocks, no command")
    base = h.build(drop=tuple(h.SOURCE_B))
    ccl = d.make_world(base)[0]
    cells = sorted({c for a in (y.B_Y, (-4, 4, 3), wd.Y_G) for c in near(a) if c[2] <= 5 and ccl.get(c).n == "air" and c not in taken
                    and not r.plane_or_hall(c) and c not in RESERVED})
    palette = [("dust", t.DUST), ("dot", B("redstone_wire", power=0, dot=True)), ("stone", t.STONE), ("redstone block", t.RB)]
    palette += [(f"repeater {fc} {k}", rd.rep(fc, k)) for fc in HORIZONTAL for k in (1, 2, 3, 4)]
    palette += [(f"{n} {fc}", t.pis(n, fc, "X")) for n in ("piston", "sticky_piston") for fc in DIRS]
    done, runs_ = [], 0
    for c in cells:
        for name, st in palette:
            try:
                bad = h.run(h.build(drop=tuple(h.SOURCE_B), swap={c: st}))[2]
            except (KeyError, AssertionError):                   # the block breaks a dust or a check of the build
                bad = ["broken"]
            runs_ += 1
            if not bad:
                done.append(f"{name} at {c}")
    print(f"   {len(cells)} cells x {len(palette)} blocks = {runs_} runs; Y12 re-armed in:", done or "none")
    print("   cells:", cells)


if __name__ == "__main__":
    r.worlds()
    screen_u()
    screen_b()
