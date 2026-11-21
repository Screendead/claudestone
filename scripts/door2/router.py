"""BFS router for a redstone-dust path in a door build (legacy wire rules).

A dust cell needs a sturdy block below (existing quartz/stone/glass, or a free cell where glass is placed).
Moves: horizontal to a neighbour at the same y; up a step (neighbour + up) when the block above the current
cell is not a conductor and the neighbour cell is (or will be) a solid support; down a step (neighbour + down)
when the neighbour cell at the current y is not a conductor.
Constraints: no cell inside `forbid`; every dust cell at Manhattan distance >= `keep` from each cell in `sensitive`
(a dust change updates everything within 2); no dust adjacent (or step-adjacent) to foreign dust."""
from collections import deque

H4 = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)]


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def route(b, start_cells, goal_cells, sensitive=(), keep=3, forbid=(), bounds=((-7, 9), (-5, 9), (-8, 5)),
          own=(), extra_sens=None, stone_bad=()):
    """b: Build (dict b.b); start_cells: dust cells allowed as path start (must be free/placeable);
    goal_cells: target dust cells. Returns list of dust cells (start..goal) or None."""
    blocks = b.b
    forbid = set(forbid)
    own = set(own)
    stone_bad = set(stone_bad)

    def solid(c):
        n = blocks.get(c)
        return n is not None and n.n in ("quartz", "stone", "glass", "obsidian")

    def conductor(c):
        n = blocks.get(c)
        return n is not None and n.n in ("quartz", "stone", "obsidian")

    def free(c):
        return c not in blocks and c not in forbid

    foreign = {c for c, s in blocks.items() if s.n == "redstone_wire" and c not in own}
    rbs = {c for c, s in blocks.items() if s.n == "rb" and c not in own}

    def near_foreign(c):
        for d in H4:
            q = add(c, d)
            if q in foreign:
                return True
            if add(q, (0, 1, 0)) in foreign or add(q, (0, -1, 0)) in foreign:
                return True
        if add(c, (0, 1, 0)) in foreign or add(c, (0, -1, 0)) in foreign:
            return True
        return False

    def ok(c):
        x, y, z = c
        for d in H4 + [(0, 1, 0), (0, -1, 0)]:
            if add(c, d) in rbs:
                return False
        if not (bounds[0][0] <= x <= bounds[0][1] and bounds[1][0] <= y <= bounds[1][1] and bounds[2][0] <= z <= bounds[2][1]):
            return False
        if not free(c):
            return False
        sup = add(c, (0, -1, 0))
        if not (solid(sup) or sup not in blocks):
            return False
        if 0 <= x <= 2 and 0 <= y <= 2:
            return False
        for s in sensitive:
            if abs(s[0] - x) + abs(s[1] - y) + abs(s[2] - z) < keep:
                return False
        if near_foreign(c):
            return False
        return True

    prev = {}
    dq = deque()
    for s in start_cells:
        if ok(s) or (s in own and blocks.get(s) is not None and blocks[s].n == "redstone_wire"):
            prev[s] = None
            dq.append(s)
    goals = set(goal_cells)
    while dq:
        c = dq.popleft()
        if c in goals:
            path = []
            while c is not None:
                path.append(c)
                c = prev[c]
            return path[::-1]
        for d in H4:
            n = add(c, d)
            cands = [n]
            if not conductor(add(c, (0, 1, 0))):
                cands.append(add(n, (0, 1, 0)))
            if not conductor(n):
                # power descends only if c's support is a conductor (existing, or a free cell we make stone)
                sc = add(c, (0, -1, 0))
                if conductor(sc) or (sc not in blocks and sc not in stone_bad):
                    cands.append(add(n, (0, -1, 0)))
            for m in cands:
                if m in prev or not ok(m):
                    continue
                # a step path must not pass through a support cell used by the path itself
                prev[m] = c
                dq.append(m)
    return None


def stone_supports(path):
    """cells whose support must be a conductor: upper ends of down-steps, in path order."""
    need = set()
    for a, bb in zip(path, path[1:]):
        if bb[1] == a[1] - 1:
            need.add((a[0], a[1] - 1, a[2]))
    return need
