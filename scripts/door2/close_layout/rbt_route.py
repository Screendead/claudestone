"""RB_ST's own route home (door coords): why rbt_drives.py moves three redstone blocks one place each instead of one
block all the way. A screen on p9_p8.py's build after its close; nothing is built here. Everything printed is
COMPUTED on the simulator; nothing here ran on a server.

RB_ST rests at (2,8,0) after the close and stands at (3,7,0), beside it and one lower, in the closed state.
returns.py's screen found a route of six steps and did not design it. This one lists every route of up to eight
steps, with returns.py's two screens (a redstone block set at each cell of the way fires no piston; each mover, a
piston behind the block or a sticky piston beyond its next cell, stands in a free cell and, built retracted,
changes nothing in the load, the opening or the close to c30) and the two rules they leave out:
Path    A mover stands in no cell of the route: the block has to pass there.
Up      A sticky piston facing up cannot pull a redstone block down onto its head's cell: the block, two above the
        piston, is beside the cell above it and powers it by QC, so it stays out (shown below; returns.py found the
        same of Z_T and of the opening's up relays).

Cells   Every cell c with |c - (2,8,0)| + |c - (3,7,0)| <= 8 in city-block distance: no route of eight steps or
        fewer leaves them. Movers may stand outside them, in a box three wider than the build's on every side.
Verdict Two steps: the block would stand at (2,7,0), where it lights DT (W_T fires, then K_T), or at (3,8,0),
        where it lights DH and the bus (I_A fires: the opening). Six steps: two routes, both with the step (3,8,1)
        to (3,7,1), down, which only a sticky piston at (3,6,1) facing up can drive off the path: neither can be
        built. Eight steps: the shortest that can, eight pistons, each with a source and a time of its own.

Run from the repo root (sim; about a minute):
python -m scripts.door2.close_layout.rbt_route > scripts/door2/close_layout/rbt_route.txt"""
from scripts.door2.close_layout import trigger as t, returns as r
from scripts.door2.close_layout.feeds import power_sources
from scripts.door2.sim import DIRS, add

START, GOAL, LIMIT, GROW = t.UP, t.RB_ST, 8, 3
UP_PULLER, HEAD, ABOVE = (3, 6, 1), (3, 7, 1), (3, 8, 1)           # the six-step routes' puller, its head's cell, the block's


def dist(a, c):
    return sum(abs(x - y) for x, y in zip(a, c))


def options(u, name, w, free):
    """the movers that can take a redstone block from u one cell in direction name, off no path yet: (v, [(how, cell,
    kind, facing)]) or (v, why not)."""
    dv = DIRS[name]
    v_ = add(u, dv)
    if v_ != GOAL and v_ != START and (v_ in w.b or r.plane_or_hall(v_)):
        return v_, f"{r.label(w, v_)} there" if v_ in w.b else "door plane or hallway"
    if v_ != GOAL and r.stop(v_, START)[0]:
        return v_, "a redstone block there fires " + ", ".join(r.stop(v_, START)[0])
    out = []
    behind, beyond = add(u, dv, -1), add(v_, dv)
    if behind in free:
        kind = next((k for k in ("piston", "sticky_piston") if r.mover(behind, k, name) is None), None)
        if kind:
            out.append(("pushed", behind, kind, name))
    if beyond in free and r.mover(beyond, "sticky_piston", r.NEG[name]) is None:
        out.append(("pulled", beyond, "sticky_piston", r.NEG[name]))
    return v_, out or "no mover"


def text(m):
    how, cell, kind, facing = m
    return f"{how} by a {kind.replace('_', ' ')} at {cell} facing {facing}"


if __name__ == "__main__":
    b, cl, w, ref, _ = r.worlds()
    lo, hi = tuple(x - GROW for x in r.LO), tuple(x + GROW for x in r.HI)
    r.BOX[:] = [lo, hi]
    free = r.free_in(lo, hi)
    region = [c for c in ((x, y, z) for x in range(lo[0], hi[0] + 1) for y in range(lo[1], hi[1] + 1) for z in range(lo[2], hi[2] + 1))
              if dist(c, START) + dist(c, GOAL) <= LIMIT]
    print(f"RB_ST {START} to {GOAL} after p9_p8.py's close: every route of up to {LIMIT} steps; {len(region)} cells, movers in {len(free)} free cells")
    edges, closed = {}, {}
    for u in region:
        if u != START and (u in w.b or r.plane_or_hall(u) or r.stop(u, START)[0]):
            continue
        for name in DIRS:
            v_, got = options(u, name, w, free)
            if v_ in region or v_ == GOAL:
                if isinstance(got, list):
                    edges[(u, v_)] = got
                elif u == START or v_ == GOAL:
                    closed[(u, v_)] = got
    print("the steps out of its rest cell and into its closed cell that the screens reject:")
    for (u, v_), why in sorted(closed.items()):
        print(f"   {u} -> {v_}: {why}")
    nxt = {}
    for u, v_ in edges:
        nxt.setdefault(u, []).append(v_)
    paths = []

    def walk(path):
        if path[-1] == GOAL:
            paths.append(list(path))
        elif len(path) <= LIMIT:
            for v_ in nxt.get(path[-1], ()):
                if v_ not in path:
                    path.append(v_)
                    walk(path)
                    path.pop()
    walk([START])
    print(f"routes by the two screens alone (a mover may stand on the path): {len(paths)}, of",
          ", ".join(f"{n} steps: {sum(len(p) - 1 == n for p in paths)}" for n in sorted({len(p) - 1 for p in paths})))
    kept = []
    for p in paths:
        steps = [[m for m in edges[(a, c)] if m[1] not in p] for a, c in zip(p, p[1:])]
        if all(steps):
            kept.append((p, steps))
    print(f"with every mover off the path: {len(kept)}, of",
          ", ".join(f"{n} steps: {sum(len(p) - 1 == n for p, _ in kept)}" for n in sorted({len(p) - 1 for p, _ in kept})))
    built = []
    for p, steps in sorted(kept, key=lambda x: (len(x[0]), x[0])):
        rest = [[m for m in ms if not (m[0] == "pulled" and m[3] == "up")] for ms in steps]
        ok = all(rest)
        built += [(p, rest)] * ok
        if len(p) - 1 < 8 or ok and len(built) <= 3:
            print(f"   {len(p) - 1} steps" + ("" if ok else ", NOT BUILDABLE (a step has only a sticky piston facing up)") + ":")
            for (a, c), ms in zip(zip(p, p[1:]), steps):
                print(f"      {a} -> {c}: " + " or ".join(text(m) for m in ms))
    print(f"without the pullers that face up: {len(built)}, of",
          ", ".join(f"{n} steps: {sum(len(p) - 1 == n for p, _ in built)}" for n in sorted({len(p) - 1 for p, _ in built})) or "none",
          f"(the first {min(3, len(built))} are listed above); pistons in the shortest: {min(len(p) - 1 for p, _ in built)}" if built else "")

    print(f"\n== the puller facing up (what-if): after the close a sticky piston set out at {UP_PULLER}, its head in {HEAD}, a redstone block at {ABOVE}")
    x = r.after()
    for c, st in ((UP_PULLER, t.pis("sticky_piston", "up", "X", True)), (HEAD, t.B("piston_head", facing="up", sticky=True)), (ABOVE, t.RB)):
        x.cmd_set_silent(c, st)
    held = [c for _, c in power_sources(x, UP_PULLER)]
    x.cmd_set(add(UP_PULLER, DIRS["east"]), t.GLASS)
    x.cmd_set(add(UP_PULLER, DIRS["east"]), t.B("air"))
    x.run(6)
    print("   powered by", held, "(QC: the block is beside the cell above the piston) | after an update and six ticks: the piston",
          "out" if x.get(UP_PULLER).p.get("extended") else "in", "| the block at", [c for c in (ABOVE, HEAD) if x.get(c).n == "rb"])
