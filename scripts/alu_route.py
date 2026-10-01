"""Net-tagged placement grid, a one-net-at-a-time A* dust router, and a strength pass
that swaps dust for repeaters where a routed run would die out (used by scripts.alu)."""

import heapq
import sys
from collections import deque

from scripts.redsim import FSim

SOLID = "white_concrete"
WIRE = "redstone_wire"
OUT = {"e": (1, 0), "w": (-1, 0), "s": (0, 1), "n": (0, -1)}
FACE_OF_OUT = {"e": "west", "w": "east", "s": "north", "n": "south"}  # facing = input side


class Grid:
    def __init__(self, size):
        self.size = size
        self.b = {}      # pos -> state
        self.net = {}    # pos -> net tag (dust/diode output/strong block)
        self.strong = {}  # block pos -> net it is strongly powered with

    def put(self, p, state, net=None, support=True):
        if not all(0 <= v < s for v, s in zip(p, self.size)):
            raise ValueError(f"{p} outside box for {state} {net}")
        old = self.b.get(p)
        if old is not None and old != state:
            raise ValueError(f"overlap at {p}: {old} ({self.net.get(p)}) vs {state} ({net})")
        if old is not None and state != SOLID and self.net.get(p) not in (None, net):
            raise ValueError(f"net clash at {p}: {self.net.get(p)} vs {net}")
        self.b[p] = state
        if net is not None:
            self.net[p] = net
        if support and state != SOLID and "redstone_block" not in state and p[1] >= 1:
            q = (p[0], p[1] - 1, p[2])
            if q not in self.b:
                self.b[q] = SOLID
        return p

    def block(self, p, net=None):
        return self.put(p, SOLID, net)

    def dust(self, p, net):
        return self.put(p, WIRE, net)

    def rep(self, p, out, net, delay=1):
        s = f"repeater[facing={FACE_OF_OUT[out]},delay={delay}]"
        self.put(p, s, net)
        self._strong_target(p, out, net)
        return p

    def cmp(self, p, out, net, mode="subtract"):
        self.put(p, f"comparator[facing={FACE_OF_OUT[out]},mode={mode}]", net)
        self._strong_target(p, out, net)
        return p

    def _strong_target(self, p, out, net):
        dx, dz = OUT[out]
        self.strong.setdefault((p[0] + dx, p[1], p[2] + dz), set()).add(net)

    def wall_torch(self, p, attached_dir, net):
        # attached_dir: side of p holding the block; facing is the opposite
        opp = {"n": "south", "s": "north", "e": "west", "w": "east"}[attached_dir]
        self.put(p, f"redstone_wall_torch[facing={opp}]", net, support=False)
        self.strong.setdefault((p[0], p[1] + 1, p[2]), set()).add(net)
        return p

    def path(self, cells, net):
        """Dust along cells (x,y,z); supports added under each."""
        for c in cells:
            self.dust(c, net)

    def check(self):
        errs = []
        solid = lambda q: self.b.get(q, "air") == SOLID or (self.b.get(q, "").startswith("minecraft:") is False and self.b.get(q) == SOLID)
        for p, s in self.b.items():
            if s != WIRE:
                continue
            n = self.net.get(p)
            x, y, z = p
            above_solid = self.b.get((x, y + 1, z)) == SOLID
            for dx, dz in OUT.values():
                q = (x + dx, y, z + dz)
                if self.b.get(q) == WIRE and self.net.get(q) != n:
                    errs.append(f"dust {p} {n} touches dust {q} {self.net.get(q)}")
                up = (x + dx, y + 1, z + dz)
                if self.b.get(up) == WIRE and self.net.get(up) != n and not above_solid:
                    errs.append(f"dust {p} {n} climbs to {up} {self.net.get(up)}")
                dn = (x + dx, y - 1, z + dz)
                if self.b.get(dn) == WIRE and self.net.get(dn) != n and self.b.get(q) != SOLID:
                    errs.append(f"dust {p} {n} drops to {dn} {self.net.get(dn)}")
            for d in [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0)]:
                q = (x + d[0], y + d[1], z + d[2])
                for sn in self.strong.get(q, ()):
                    if sn != n and self.b.get(q) == SOLID:
                        errs.append(f"dust {p} {n} next to block {q} strong with {sn}")
                if "redstone_block" in self.b.get(q, ""):
                    errs.append(f"dust {p} {n} next to redstone block {q}")
                if "torch" in self.b.get(q, "") and self.net.get(q) != n:
                    errs.append(f"dust {p} {n} next to torch {q} {self.net.get(q)}")
        return errs

    def show(self, y, z0, z1, x0=0, x1=None):
        x1 = self.size[0] if x1 is None else x1
        sym = {}
        lines = []
        for z in range(z0, z1):
            row = []
            for x in range(x0, x1):
                s = self.b.get((x, y, z))
                if s is None:
                    c = "."
                elif s == SOLID:
                    c = "#"
                elif s == WIRE:
                    c = "-"
                elif "repeater" in s:
                    c = {"west": ">", "east": "<", "north": "v", "south": "^"}[s.split("facing=")[1].split(",")[0].rstrip("]")]
                elif "comparator" in s:
                    c = {"west": "E", "east": "W", "north": "S", "south": "N"}[s.split("facing=")[1].split(",")[0]]
                elif "torch" in s:
                    c = "t"
                elif "redstone_block" in s:
                    c = "R"
                else:
                    c = "?"
                row.append(c)
            lines.append(f"{z:3d} " + "".join(row))
        return "\n".join(lines)


H4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def _is_diode(s):
    return s is not None and ("repeater" in s or "comparator" in s)


class Router:
    """A* for one net at a time on a Grid. Dust cells only; supports are added as needed."""

    def __init__(self, g, ymax=4, keep=()):
        self.g = g
        self.ymax = ymax
        self.keep = set(keep)  # cells that must stay air
        self.zlim = None
        self.start_level = 99
        self.pending_path = ()
        self.cov = {}
        self.inputs = {}  # cells read by diodes/torches -> net they belong to

    def mark_input(self, cell, net):
        self.inputs[cell] = net

    def foreign_dust(self, q, net):
        return self.g.b.get(q) == WIRE and self.g.net.get(q) != net

    def ok(self, c, net, newsup):
        g = self.g
        x, y, z = c
        if not (0 < x < g.size[0] and 1 <= y <= self.ymax and 0 <= z < g.size[2]):
            self.why = sys._getframe().f_lineno; return False
        if self.zlim and not (self.zlim[0] <= z <= self.zlim[1]):
            self.why = sys._getframe().f_lineno; return False
        if c in g.b or c in self.keep:
            self.why = sys._getframe().f_lineno; return False
        if c in self.inputs and self.inputs[c] != net:
            self.why = sys._getframe().f_lineno; return False
        below = (x, y - 1, z)
        bs = g.b.get(below)
        if bs is None:
            if below in self.keep or (below in self.inputs and self.inputs[below] != net):
                self.why = sys._getframe().f_lineno; return False
            for sn in g.strong.get(below, ()):
                if sn != net:
                    self.why = sys._getframe().f_lineno; return False
        elif bs != SOLID:
            self.why = sys._getframe().f_lineno; return False
        else:
            if below in self.inputs and self.inputs[below] != net:
                self.why = sys._getframe().f_lineno; return False
            for sn in g.strong.get(below, ()):
                if sn != net:
                    self.why = sys._getframe().f_lineno; return False
        above_solid = g.b.get((x, y + 1, z)) == SOLID
        covers = set()
        for dx, dz in H4:
            q = (x + dx, y, z + dz)
            s = g.b.get(q)
            if s == WIRE and g.net.get(q) != net:
                self.why = sys._getframe().f_lineno; return False
            if s is not None and s != SOLID and s != WIRE and g.net.get(q) != net:
                # foreign component next to new dust: only allowed if it is a diode whose axis is perpendicular
                if _is_diode(s) and self.inputs.get(c) == net:
                    pass
                elif _is_diode(s):
                    f = s.split("facing=")[1].split(",")[0].rstrip("]")
                    axis_x = f in ("east", "west")
                    if (dx != 0) == axis_x:
                        self.why = sys._getframe().f_lineno; return False
                    if "comparator" in s:
                        return False  # would feed a comparator side
                else:
                    self.why = sys._getframe().f_lineno; return False
            if s == SOLID:
                if q in self.inputs and self.inputs[q] != net:
                    self.why = sys._getframe().f_lineno; return False
                for sn in g.strong.get(q, ()):
                    if sn != net:
                        self.why = sys._getframe().f_lineno; return False
            up = (x + dx, y + 1, z + dz)
            if g.b.get(up) == WIRE and g.net.get(up) != net and not above_solid:
                covers.add((x, y + 1, z))
            dn = (x + dx, y - 1, z + dz)
            if g.b.get(dn) == WIRE and g.net.get(dn) != net and s != SOLID:
                covers.add(q)
        for q in [(x, y + 1, z), (x, y - 1, z)]:
            s = g.b.get(q)
            if s is not None and "redstone_block" in s:
                self.why = sys._getframe().f_lineno; return False
            for sn in g.strong.get(q, ()):
                if sn != net and g.b.get(q) == SOLID:
                    self.why = sys._getframe().f_lineno; return False
        for cv in covers:
            if cv in g.b and g.b[cv] != SOLID:
                self.why = sys._getframe().f_lineno; return False
            if cv in self.keep or cv in self.inputs or g.strong.get(cv) or not (0 <= cv[1] < g.size[1]):
                self.why = sys._getframe().f_lineno; return False
            if any(cc == cv for cc in self.pending_path):
                self.why = sys._getframe().f_lineno; return False
        self.last_covers = covers
        return covers or True

    def route(self, net, starts, goal, maxlen=14):
        """starts: existing cells of the net (dust or anything powered); goal: cell to become dust."""
        g = self.g
        reserved = g.b.get(goal) == WIRE and g.net.get(goal) == net
        if reserved:
            del g.b[goal]; del g.net[goal]
        def h(c):
            return abs(c[0] - goal[0]) + abs(c[1] - goal[1]) * 2 + abs(c[2] - goal[2])
        self.cov = {}
        openl = []
        prev = {}
        cost = {}
        for s in starts:
            cost[s] = 0
            heapq.heappush(openl, (h(s), 0, s))
        found = None
        n = 0
        while openl and n < 200000:
            n += 1
            f, gc, c = heapq.heappop(openl)
            if c == goal:
                found = c
                break
            if gc > cost.get(c, 1e9):
                continue
            x, y, z = c
            for dx, dz in H4:
                for dy in (0, 1, -1):
                    q = (x + dx, y + dy, z + dz)
                    if dy == 1 and g.b.get((x, y + 1, z)) == SOLID:
                        continue
                    if dy == 1 and (x, y + 1, z) in self.keep_solid_cells():
                        continue
                    if dy == -1 and g.b.get((x + dx, y, z + dz)) == SOLID:
                        continue
                    r = self.ok(q, net, None)
                    if not r:
                        continue
                    must_air = set()
                    chain = [q, c]
                    cc = c
                    for _ in range(60):
                        if cc not in prev:
                            break
                        chain.append(prev[cc]); cc = prev[cc]
                    for a, b in zip(chain, chain[1:]):
                        if a[1] != b[1]:
                            lo = a if a[1] < b[1] else b
                            must_air.add((lo[0], lo[1] + 1, lo[2]))
                    sup = (q[0], q[1] - 1, q[2])
                    if q in must_air or (sup in must_air and g.b.get(sup) is None):
                        continue
                    if r is not True and any(cv in must_air for cv in r):
                        continue
                    if any((cv[0], cv[1] - 1, cv[2]) == q for cv in ()):
                        continue
                    bad = False
                    for p in chain[2:]:
                        if p[1] - 1 == q[1] and p[0] == q[0] and p[2] == q[2]:
                            bad = True
                    if bad:
                        continue
                    if dy == 1 and c in self.cov and (c[0], c[1] + 1, c[2]) in self.cov[c]:
                        continue
                    # path cells must not be consecutive-adjacent to older path cells (self loops fine)
                    nc = gc + 1 + (2 if dy else 0)
                    if r is not True:
                        nc += 3 * len(r)
                    if nc < cost.get(q, 1e9):
                        if r is not True:
                            self.cov[q] = r
                        else:
                            self.cov.pop(q, None)
                        cost[q] = nc
                        prev[q] = c
                        heapq.heappush(openl, (nc + h(q), nc, q))
        if not found:
            if reserved:
                g.b[goal] = WIRE; g.net[goal] = net
            raise RuntimeError(f"no route for {net} to {goal}")
        path = []
        c = found
        while c in prev:
            path.append(c)
            c = prev[c]
        attach = c
        path.reverse()
        full = [attach] + path
        level = self.start_level
        reps = set()
        for k in range(1, len(full)):
            level -= 1
            a, b = full[k - 1], full[k]
            nx = full[k + 1] if k + 1 < len(full) else None
            if level <= 3 and nx is not None and a[1] == b[1] == nx[1] and (b[0] - a[0], b[2] - a[2]) == (nx[0] - b[0], nx[2] - b[2]):
                reps.add((b, (nx[0] - b[0], nx[2] - b[2])))
                level = 15
        rep_at = dict(reps)
        for i, c in enumerate(path):
            nxt = path[i + 1] if i + 1 < len(path) else None
            prv = path[i - 1] if i else attach
            if c in rep_at:
                d = {(1, 0): "e", (-1, 0): "w", (0, 1): "s", (0, -1): "n"}[rep_at[c]]
                g.rep(c, d, net)
            else:
                g.dust(c, net)
            for cv in self.cov.get(c, ()):
                if cv not in g.b:
                    g.b[cv] = SOLID
            for o in (prv, nxt):
                if o is not None and o[1] != c[1]:
                    lo = c if c[1] < o[1] else o
                    self.keep.add((lo[0], lo[1] + 1, lo[2]))
        return path

    def keep_solid_cells(self):
        return ()


DIR = {(1, 0): "e", (-1, 0): "w", (0, 1): "s", (0, -1): "n"}


def levels(g):
    sim = FSim(dict(g.b), {})
    lv = {}
    from collections import deque
    q = deque()
    for p in sim.dust:
        best = 0
        for kind, n in sim.dust_base[p]:
            s = g.b.get(n, "")
            if kind == "rb":
                best = 15
            elif kind == "d":
                best = max(best, 11 if "comparator" in s else 15)
            elif kind == "s" and n in sim.strong_src:
                srcs = sim.strong_src[n]
                best = max(best, max(11 if "comparator" in g.b[x] else 15 for x in srcs))
        if best:
            lv[p] = best
            q.append(p)
    parent = {}
    import heapq
    h = [(-l, p) for p, l in lv.items()]
    heapq.heapify(h)
    while h:
        l, p = heapq.heappop(h); l = -l
        if l < lv.get(p, 0):
            continue
        for n in sim.conn[p]:
            if l - 1 > lv.get(n, 0):
                lv[n] = l - 1; parent[n] = p
                heapq.heappush(h, (-(l - 1), n))
    return sim, lv, parent


def fix(g, rounds=40, fixed=()):
    added = []
    for _ in range(rounds):
        sim, lv, parent = levels(g)
        front = [p for p in sim.dust if p in lv and g.net.get(p) not in fixed
                 and any(n not in lv for n in sim.conn[p])]
        if not front:
            return added
        p = min(front, key=lambda c: lv[c])
        chain = []
        c = p
        while c in parent:
            chain.append(c)
            c = parent[c]
        chain.append(c)
        # chain: from weak end back toward the source; choose a cell k with chain[k-1] (child), chain[k+1] (parent)
        done = False
        for k in range(1, len(chain) - 1):
            ch, cell, par = chain[k - 1], chain[k], chain[k + 1]
            if lv.get(cell, 0) > 12:
                break
            if ch[1] == cell[1] == par[1]:
                d1 = (cell[0] - par[0], cell[2] - par[2]); d2 = (ch[0] - cell[0], ch[2] - cell[2])
                ok_nb = set(sim.conn[cell]) <= {ch, par}
                for dx, dz in DIR:
                    q = (cell[0] + dx, cell[1], cell[2] + dz)
                    if q not in (ch, par) and g.b.get(q, "").startswith(("repeater", "comparator")):
                        ok_nb = False
                if d1 == d2 and g.b.get(cell) == WIRE and ok_nb:
                    net = g.net[cell]
                    del g.b[cell]
                    g.rep(cell, DIR[d1], net)
                    added.append(cell)
                    done = True
                    break
        if not done:
            raise RuntimeError(f"no straight run to boost {p} {g.net.get(p)} chain {chain[:8]}")
    return added
