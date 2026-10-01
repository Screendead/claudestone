"""Offline redstone simulator for dust, repeaters, comparators, torches and solid blocks.

Agreed with 126 of 136 library truth tables built only from those blocks; it does not
model repeater locking, item frames or quasi-connectivity, and its delays read 1 tick high.
"""

from redstone.harness import parse_state

V = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0)}
H = list(V.values())
OPPV = {v: (-v[0], -v[1], -v[2]) for v in H}
NONSOLID = {"air", "redstone_wire", "repeater", "comparator", "redstone_torch", "redstone_wall_torch",
            "redstone_block", "glass", "lever"}
D6 = H + [(0, 1, 0), (0, -1, 0)]


def add(p, d):
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


class FSim:
    def __init__(self, blocks, inputs):
        self.kind, self.props = {}, {}
        for p, s in blocks.items():
            b, pr = parse_state(s)
            self.kind[p] = b.removeprefix("minecraft:")
            self.props[p] = pr
        self.inputs = inputs
        self.input_cells = {c for cs in inputs.values() for c in cs}
        self.issues = set()
        self.t = 0
        self.pending = {}
        self.out = {}
        self.build()

    def k(self, p):
        return self.kind.get(p, "air")

    def solid(self, p):
        return self.k(p) not in NONSOLID

    def build(self):
        kind = self.kind
        self.diodes = [p for p, b in kind.items() if b in ("repeater", "comparator")]
        self.torches = [p for p, b in kind.items() if b in ("redstone_torch", "redstone_wall_torch")]
        for p in self.diodes:
            self.out.setdefault(p, 0)
        for p in self.torches:
            self.out.setdefault(p, 15)
        self.fvec = {p: V[self.props[p]["facing"]] for p in self.diodes}
        self.target_of = {p: add(p, OPPV[self.fvec[p]]) for p in self.diodes}  # output cell
        # torch attached / outputs
        self.attached = {}
        for p in self.torches:
            if kind[p] == "redstone_torch":
                self.attached[p] = add(p, (0, -1, 0))
            else:
                f = V[self.props[p]["facing"]]
                self.attached[p] = add(p, OPPV[f])
        # dust topology
        self.dust = [p for p, b in kind.items() if b == "redstone_wire"]
        self.conn = {}
        self.point = {}
        for p in self.dust:
            dirs, nbrs = set(), []
            above_solid = self.solid(add(p, (0, 1, 0)))
            for v in H:
                n = add(p, v)
                kn = self.k(n)
                if kn == "redstone_wire":
                    dirs.add(v); nbrs.append(n); continue
                if kn in ("redstone_block", "redstone_torch", "redstone_wall_torch", "comparator", "lever"):
                    dirs.add(v); continue
                if kn == "repeater":
                    if self.fvec[n] in (v, OPPV[v]):
                        dirs.add(v)
                    continue
                up = add(n, (0, 1, 0))
                if self.k(up) == "redstone_wire" and not above_solid:
                    dirs.add(v); nbrs.append(up)
                down = add(n, (0, -1, 0))
                if self.k(down) == "redstone_wire" and not self.solid(n):
                    dirs.add(v); nbrs.append(down)
            pt = set(dirs)
            if len(dirs) == 1:
                pt.add(OPPV[next(iter(dirs))])
            self.conn[p] = nbrs
            self.point[p] = pt
        # blocks weakly powered by dust: block -> list of dust
        self.dust_powers = {}
        for p in self.dust:
            below = add(p, (0, -1, 0))
            if self.solid(below):
                self.dust_powers.setdefault(below, []).append(p)
            for v in self.point[p]:
                n = add(p, v)
                if self.solid(n):
                    self.dust_powers.setdefault(n, []).append(p)
        # strong power into blocks: block -> list of (diode) and torches below
        self.strong_src = {}
        for p in self.diodes:
            t = self.target_of[p]
            if self.solid(t):
                self.strong_src.setdefault(t, []).append(p)
        for p in self.torches:
            a = add(p, (0, 1, 0))
            if self.solid(a):
                self.strong_src.setdefault(a, []).append(p)
        # dust base sources: list of callables -> precompute lists
        self.dust_base = {}
        for p in self.dust:
            srcs = []
            for d in D6:
                n = add(p, d)
                b = self.k(n)
                if b == "redstone_block":
                    srcs.append(("rb", n))
                elif b in ("repeater", "comparator"):
                    if self.target_of[n] == p:
                        srcs.append(("d", n))
                elif b in ("redstone_torch", "redstone_wall_torch"):
                    if self.attached[n] != p:
                        srcs.append(("d", n))
                elif self.solid(n):
                    srcs.append(("s", n))
            self.dust_base[p] = srcs
        # component inputs
        self.back = {}
        self.sides = {}
        for p in self.diodes:
            f = self.fvec[p]
            self.back[p] = add(p, f)
            self.sides[p] = [add(p, v) for v in H if v != f and v != OPPV[f]]
        self.level = {p: 0 for p in self.dust}

    def strong(self, b):
        m = 0
        for s in self.strong_src.get(b, ()):
            m = max(m, self.out[s])
        return m

    def weak(self, b):
        m = self.strong(b)
        for d in self.dust_powers.get(b, ()):
            m = max(m, self.level[d])
        return m

    def solve_dust(self):
        lv = {}
        for p in self.dust:
            m = 0
            for kind, n in self.dust_base[p]:
                if kind == "rb":
                    m = 15
                elif kind == "d":
                    m = max(m, self.out[n])
                else:
                    m = max(m, self.strong(n))
            lv[p] = m
        # propagate: process in descending order
        order = sorted(self.dust, key=lambda p: -lv[p])
        import heapq
        heap = [(-lv[p], p) for p in self.dust if lv[p] > 0]
        heapq.heapify(heap)
        while heap:
            negl, p = heapq.heappop(heap)
            l = -negl
            if l < lv[p]:
                continue
            for n in self.conn[p]:
                if l - 1 > lv[n]:
                    lv[n] = l - 1
                    heapq.heappush(heap, (-(l - 1), n))
        self.level = lv

    def src_into(self, n, p):
        b = self.k(n)
        if b == "redstone_block":
            return 15
        if b == "redstone_wire":
            return self.level.get(n, 0)
        if b in ("repeater", "comparator"):
            return self.out[n] if self.target_of[n] == p else 0
        if b in ("redstone_torch", "redstone_wall_torch"):
            return self.out[n] if self.attached[n] != p else 0
        if b not in NONSOLID:
            return self.weak(n)
        return 0

    def side_into(self, n, p):
        b = self.k(n)
        if b == "redstone_block":
            return 15
        if b == "redstone_wire":
            return self.level.get(n, 0)
        if b in ("repeater", "comparator"):
            return self.out[n] if self.target_of[n] == p else 0
        return 0

    def target(self, p):
        b = self.kind[p]
        if b == "repeater":
            for n in self.sides[p]:
                if self.k(n) in ("repeater", "comparator") and self.target_of[n] == p and self.out[n] > 0:
                    self.issues.add(f"repeater {p} locked by {n}")
            return 15 if self.src_into(self.back[p], p) > 0 else 0
        if b == "comparator":
            back = self.src_into(self.back[p], p)
            side = max(self.side_into(n, p) for n in self.sides[p])
            if self.props[p].get("mode") == "subtract":
                return max(0, back - side)
            return back if back >= side else 0
        return 0 if self.weak(self.attached[p]) > 0 else 15

    def delay(self, p):
        if self.kind[p] == "repeater":
            return 2 * int(self.props[p].get("delay", 1))
        return 2

    def drive(self, name, v):
        changed = False
        for c in self.inputs[name]:
            if v and self.kind.get(c) != "redstone_block":
                self.kind[c] = "redstone_block"; self.props[c] = {}; changed = True
            elif not v and c in self.kind:
                del self.kind[c]; del self.props[c]; changed = True
        if changed:
            self.build()
            self.dirty = True

    dirty = True

    def step(self):
        fire = [p for p, t in self.pending.items() if t <= self.t]
        if fire or self.dirty:
            if self.dirty:
                self.solve_dust()
            new = {}
            for p in fire:
                new[p] = self.target(p)
                del self.pending[p]
            for p, v in new.items():
                self.out[p] = v
            self.solve_dust()
            for p in self.diodes + self.torches:
                if p in self.pending:
                    continue
                if self.target(p) != self.out[p]:
                    self.pending[p] = self.t + self.delay(p)
            self.dirty = False
        self.t += 1

    def settle(self, n=300):
        for _ in range(n):
            self.step()
            if not self.pending:
                return True
        return False

    def read(self, p):
        b = self.k(p)
        if b == "redstone_wire":
            return self.level.get(p, 0)
        return self.out.get(p, 0)


def from_spec(spec):
    return FSim(dict(spec.build.blocks), {n: spec.input_cells(n) for n in spec.inputs})


def run_rows(sim, cells, rows, maxwait=60):
    """rows: list of (inputs dict, expected dict name->0/1/None). Returns worst delay and failures.
    Delay = last tick at which any expected output was still wrong (conservative)."""
    worst, fails, per = 0, [], []
    for i, (vin, vout) in enumerate(rows):
        for n, v in vin.items():
            sim.drive(n, v)
        last_bad = 0
        for t in range(maxwait):
            ok = all(v is None or (sim.read(cells[o]) > 0) == bool(v) for o, v in vout.items())
            if not ok:
                last_bad = t + 1
            sim.step()
        ok = all(v is None or (sim.read(cells[o]) > 0) == bool(v) for o, v in vout.items())
        if not ok:
            fails.append((i, vin, vout, {o: sim.read(cells[o]) for o in vout}))
            last_bad = maxwait
        worst = max(worst, last_bad)
        per.append(last_bad)
    return worst, fails, per
