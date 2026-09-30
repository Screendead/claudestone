"""Compose tested parts into a circuit and route wires between them.

Wires are dust on a support block. A wire two layers up can pass over another one: the
lower wire's dust ignores the weak power in the block above it. Wires climb or descend
one block per step.

A wire cell is only placed where it cannot interact with anything that isn't its own:
  - nothing foreign orthogonally beside it on its own layer;
  - on the layer above, only plain solid blocks (a torch there would be a tap, and
    foreign dust there could join ours diagonally);
  - on the layer below, nothing but plain solid blocks beside or under it, since our
    dust weakly powers the support block and could feed whatever touches it;
  - no torch directly under the support block, which would power our dust through it.
Each net starts with a repeater in line with the source's output dust, which isolates
the part and restarts the signal at full strength.
"""

import heapq
import itertools
from dataclasses import dataclass, field

from .build import Build, Pos
from .fileformat import Spec
from .harness import parse_state

REFRESH_AT = 4
REPEATER_TICKS = 2
STEP_COST = 3
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
FACING_FROM = {(1, 0): "west", (-1, 0): "east", (0, 1): "north", (0, -1): "south"}  # repeater facing for flow
COMPONENT_WORDS = ("redstone", "repeater", "comparator", "torch", "lever", "button", "lamp", "observer", "piston")


def _is_component(state: str) -> bool:
    return any(w in state for w in COMPONENT_WORDS)


def _is_torch(state: str) -> bool:
    return "torch" in state


def _add(p: Pos, dx: int, dy: int, dz: int) -> Pos:
    return (p[0] + dx, p[1] + dy, p[2] + dz)


def part_delay(spec: Spec) -> int:
    for t in spec.tests:
        if "delay" in t:
            return t["delay"]
        if "max_delay" in t:
            return t["max_delay"]
    raise ValueError(f"{spec.name} declares no delay")


@dataclass
class Net:
    source: tuple[str, str]  # (part, output)
    sinks: list[tuple[str, str]]  # (part, input)
    cells: dict[Pos, str] = field(default_factory=dict)  # route cell -> block state
    repeaters_to: dict[tuple[str, str], int] = field(default_factory=dict)


class RoutingError(Exception):
    pass


class Circuit:
    def __init__(self, name: str, size: Pos = (64, 32, 64)):
        self.name = name
        self.size = size
        self.parts: dict[str, tuple[Spec, Pos]] = {}
        self.nets: list[Net] = []

    def add(self, name: str, spec: Spec, at: Pos) -> "Circuit":
        self.parts[name] = (spec, at)
        return self

    def connect(self, source: str, *sinks: str) -> "Circuit":
        def split(s):
            part, pin = s.split(".")
            return part, pin
        self.nets.append(Net(split(source), [split(s) for s in sinks]))
        return self

    # --- geometry -------------------------------------------------------------------
    def _pin(self, part: str, pin: str, kind: str) -> Pos:
        spec, at = self.parts[part]
        table = spec.inputs if kind == "input" else spec.outputs
        return _add(table[pin], *at)

    def build(self, description: str = "", truth=None) -> Spec:
        world = Build()
        owner: dict[Pos, str] = {}
        for name, (spec, at) in self.parts.items():
            for pos, state in spec.build.shifted(at).blocks.items():
                if pos in world.blocks:
                    raise RoutingError(f"part {name} overlaps at {pos}")
                world.blocks[pos] = state
                owner[pos] = name
        routed_sinks = {s for n in self.nets for s in n.sinks}
        self.keepout: set[Pos] = set()
        for name, (spec, at) in self.parts.items():
            for pin, pos in spec.inputs.items():
                if (name, pin) not in routed_sinks:
                    p = _add(pos, *at)
                    self.keepout |= {p} | {_add(p, *d) for d in
                                           [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]}
        self.world, self.owner = world, owner
        # Each net's pins, and the free cells around them, belong to that net alone, so
        # an earlier wire can't wall off a later net's source or sink.
        self.reserved: dict[Pos, str] = {}
        for i, net in enumerate(self.nets):
            for pin in [self._pin(*net.source, "output")] + [self._pin(*s, "input") for s in net.sinks]:
                for p in [pin] + [_add(pin, dx, 0, dz) for dx, dz in DIRS]:
                    if p not in world.blocks:
                        self.reserved[p] = f"net{i}"
        for i, net in enumerate(self.nets):
            self._route(i, net)
        return self._spec(description, truth)

    def _state(self, pos: Pos) -> str | None:
        return self.world.blocks.get(pos)

    def _foreign(self, pos: Pos, me: str, allow: set[Pos]) -> str | None:
        if pos in allow:
            return None
        s = self._state(pos)
        if s is None or self.owner.get(pos) == me:
            return None
        return s

    def _cell_ok(self, c: Pos, me: str, allow: set[Pos]) -> bool:
        """Can net `me` put dust (or a repeater) at c, with its support block below?"""
        s = _add(c, 0, -1, 0)
        if any(v < 0 or v >= lim for v, lim in zip(c, self.size)) or s[1] < 0:
            return False
        if c in getattr(self, "banned", ()) or self.reserved.get(c, me) != me:
            return False
        for p in (c, s):
            if p in self.keepout and p not in allow:
                return False
            if p in self.world.blocks and not (p == s and self.owner.get(p) == me):
                return False
        for dx, dz in DIRS:  # same layer, orthogonal
            if self._foreign(_add(c, dx, 0, dz), me, allow) is not None:
                return False
        for dx, dz in itertools.product((-1, 0, 1), repeat=2):
            above = self._foreign(_add(c, dx, 1, dz), me, allow)
            if above is not None and _is_component(above):
                return False
            below = self._foreign(_add(s, dx, 0, dz), me, allow)
            if below is not None and _is_component(below):
                return False
        under = self._foreign(_add(s, 0, -1, 0), me, allow)
        return not (under is not None and _is_torch(under))

    # --- search -----------------------------------------------------------------------
    def _route(self, index: int, net: Net) -> None:
        me = f"net{index}"
        src = self._pin(*net.source, "output")
        src_part = net.source[0]
        start = None
        for dx, dz in DIRS:
            c = _add(src, dx, 0, dz)
            if self._cell_ok(c, me, allow={src}) and self._cell_ok(_add(c, dx, 0, dz), me, allow=set()):
                start = (c, (dx, dz))
                break
        if start is None:
            raise RoutingError(f"no room to leave {net.source}")
        (c0, d0) = start
        parent: dict[Pos, Pos | None] = {c0: None}
        via: set[Pos] = set()
        kind: dict[Pos, str] = {c0: "repeater[facing=%s]" % FACING_FROM[d0]}
        self._claim(c0, me, kind[c0])
        first = _add(c0, d0[0], 0, d0[1])
        parent[first] = c0
        kind[first] = "redstone_wire"
        self._claim(first, me, "redstone_wire")
        tree_dust = [first]

        for sink in net.sinks:
            goal = self._pin(*sink, "input")
            self.banned: set[Pos] = set()
            for _ in range(200):
                path = self._search(tree_dust, goal, me, sink)
                if path is None:
                    raise RoutingError(f"cannot route {net.source} -> {sink}")
                clash = _self_conflict(path)
                if clash is None:
                    break
                self.banned.add(clash)
            else:
                raise RoutingError(f"{net.source} -> {sink}: path keeps colliding with itself")
            prev = path[0]
            for step, is_via in path[1:]:
                parent[step] = prev
                kind[step] = "redstone_wire"
                if is_via:
                    via.add(step)
                    # Each staircase step needs air above its lower dust; a later
                    # wire's support block there would cut the connection.
                    lower = prev if step[1] > prev[1] else step
                    self.keepout.add(_add(lower, 0, 1, 0))
                self._claim(step, me, "redstone_wire")
                prev = step
                if not is_via and step != goal:
                    tree_dust.append(step)
            net.repeaters_to[sink] = 0
        # Repeaters: walk from the root, refreshing the signal where a slot allows.
        children: dict[Pos, list[Pos]] = {}
        for c, p in parent.items():
            if p is not None:
                children.setdefault(p, []).append(c)
        sinks = {self._pin(*s, "input"): s for s in net.sinks}
        strength = {c0: 16}
        reps_on_path = {c0: 1}
        stack = [c0]
        while stack:
            p = stack.pop()
            for c in children.get(p, []):
                nxt = children.get(c, [])
                straight = (len(nxt) == 1 and c[1] == p[1] == nxt[0][1]
                            and (c[0] - p[0], c[2] - p[2]) == (nxt[0][0] - c[0], nxt[0][2] - c[2]))
                ok = straight and c not in via and p not in via and c not in sinks and p != c0
                if ok and strength[p] - 1 <= REFRESH_AT:
                    d = (c[0] - p[0], c[2] - p[2])
                    kind[c] = f"repeater[facing={FACING_FROM[d]}]"
                    strength[c] = 16
                    reps_on_path[c] = reps_on_path[p] + 1
                else:
                    strength[c] = strength[p] - 1
                    reps_on_path[c] = reps_on_path[p]
                    if strength[c] <= 0:
                        raise RoutingError(f"signal dies at {c} on {net.source}")
                stack.append(c)
        for c, k in kind.items():
            self.world.blocks[c] = "minecraft:" + k
        for goal, sink in sinks.items():
            net.repeaters_to[sink] = reps_on_path[goal]
        net.cells = {c: kind[c] for c in kind}

    def _claim(self, c: Pos, me: str, state: str) -> None:
        s = _add(c, 0, -1, 0)
        self.world.blocks[c] = "minecraft:" + state
        self.owner[c] = me
        if s not in self.world.blocks:
            self.world.blocks[s] = "minecraft:white_concrete"
            self.owner[s] = me

    def _search(self, starts: list[Pos], goal: Pos, me: str, sink) -> list | None:
        dest_part, _ = sink
        spec, at = self.parts[dest_part]
        # The sink's own input repeater is the one foreign block the last cell may touch.
        allow = {p for d in DIRS for p in [_add(goal, d[0], 0, d[1])] if self.owner.get(p) == dest_part}
        def h(p):
            return abs(p[0] - goal[0]) + abs(p[2] - goal[2]) + abs(p[1] - goal[1]) * 2
        frontier = []
        best: dict[Pos, int] = {}
        came: dict[Pos, tuple[Pos, bool] | None] = {}
        counter = itertools.count()
        for s in starts:
            best[s] = 0
            came[s] = None
            heapq.heappush(frontier, (h(s), next(counter), s))
        while frontier:
            _, _, cur = heapq.heappop(frontier)
            if cur == goal:
                path = []
                node = cur
                while came[node] is not None:
                    prev, is_via = came[node]
                    path.append((node, is_via))
                    node = prev
                path.reverse()
                return [node] + path
            g = best[cur]
            for dx, dz in DIRS:
                nxt = _add(cur, dx, 0, dz)
                own = allow if nxt == goal else set()
                if nxt not in best and self._step_ok(cur, nxt, me, own):
                    best[nxt] = g + 1
                    came[nxt] = (cur, False)
                    heapq.heappush(frontier, (g + 1 + h(nxt), next(counter), nxt))
                for dy in (1, -1):
                    step = _add(cur, dx, dy, dz)
                    if step in best:
                        continue
                    own = allow if step == goal else set()
                    if self._climb_ok(cur, step, me, own):
                        best[step] = g + STEP_COST
                        came[step] = (cur, True)
                        heapq.heappush(frontier, (g + STEP_COST + h(step), next(counter), step))
        return None

    def _step_ok(self, cur: Pos, nxt: Pos, me: str, allow: set[Pos]) -> bool:
        return self._cell_ok(nxt, me, allow | {cur}) and not self._touches_own(nxt, cur, me)

    def _touches_own(self, c: Pos, came_from: Pos, me: str) -> bool:
        """Beside our own wire anywhere but where we came from, dust would join a
        different branch of the tree."""
        return any(self.owner.get(n) == me and n != came_from and _is_component(self.world.blocks[n])
                   for dx, dz in DIRS for n in [_add(c, dx, 0, dz)])

    def _climb_ok(self, cur: Pos, step: Pos, me: str, allow: set[Pos]) -> bool:
        # Dust climbs one block per step; the lower dust needs clear air above it or the
        # block there cuts the connection.
        lower = cur if step[1] > cur[1] else step
        gap = _add(lower, 0, 1, 0)
        if gap in self.world.blocks or gap in self.keepout or step[1] < 1:
            return False
        return self._cell_ok(step, me, allow | {cur}) and not self._touches_own(step, cur, me)

    # --- result -----------------------------------------------------------------------
    def _spec(self, description: str, truth) -> Spec:
        routed_sinks = {s for n in self.nets for s in n.sinks}
        routed_sources = {n.source for n in self.nets}
        inputs, outputs = {}, {}
        for name, (spec, at) in self.parts.items():
            for pin, pos in spec.inputs.items():
                if (name, pin) not in routed_sinks:
                    inputs[f"{name}.{pin}"] = _add(pos, *at)
            for pin, pos in spec.outputs.items():
                if (name, pin) not in routed_sources:
                    outputs[f"{name}.{pin}"] = _add(pos, *at)
        spec = Spec(self.name, self.world, inputs=inputs, outputs=outputs, named=dict(outputs),
                    description=description)
        if truth:
            spec.tests = [_truth_test(list(inputs), list(outputs), truth, self._delay_bound())]
        return spec

    def _delay_bound(self) -> int:
        """Longest input-to-output path: part delays plus route repeaters."""
        memo: dict[str, int] = {}
        feeding = {}
        for n in self.nets:
            for s in n.sinks:
                feeding.setdefault(s[0], []).append((n, s))
        def arrive(part: str) -> int:
            if part not in memo:
                memo[part] = part_delay(self.parts[part][0]) + max(
                    [arrive(n.source[0]) + REPEATER_TICKS * n.repeaters_to[s] for n, s in feeding.get(part, [])],
                    default=0)
            return memo[part]
        return max(arrive(p) for p in self.parts)


def _pick(cells: list, i: int, j: int) -> Pos:
    # Ban the earlier of the two clashing cells: the later one is nearer the sink,
    # where there may be no other way in.
    return cells[min(i, j)] if min(i, j) > 0 else cells[max(i, j)]


def _self_conflict(path: list) -> Pos | None:
    """The search checks cells against what is already built, not against the rest of
    its own path. Find a cell that collides with another part of the path: sitting where
    another needs its support or clear air, a support where another needs clear air, or
    running beside a non-adjacent step."""
    cells = [path[0]] + [c for c, _ in path[1:]]
    support = {_add(c, 0, -1, 0): i for i, c in enumerate(cells)}
    air: dict[Pos, int] = {}
    for i in range(1, len(cells)):
        prev, c = cells[i - 1], cells[i]
        if c[1] != prev[1]:
            air[_add(prev if c[1] > prev[1] else c, 0, 1, 0)] = i
    for i, c in enumerate(cells):
        for need in (support, air):
            j = need.get(c)
            if j is not None and j != i:
                return _pick(cells, i, j)
        for k, other in enumerate(cells):
            if abs(k - i) > 1 and other[1] == c[1] and abs(other[0] - c[0]) + abs(other[2] - c[2]) == 1:
                return _pick(cells, i, k)
    for pos, i in air.items():
        if pos in support:
            return _pick(cells, i, support[pos])
    return None


def _truth_test(inputs: list[str], outputs: list[str], fn, bound: int) -> dict:
    lines = [" ".join(inputs) + " | " + " ".join(outputs)]
    for row in itertools.product([0, 1], repeat=len(inputs)):
        got = fn(dict(zip(inputs, map(bool, row))))
        lines.append(" ".join(map(str, row)) + " | " + " ".join(str(int(got[o])) for o in outputs))
    return {"name": "logic", "truth_table": "\n".join(lines) + "\n", "max_delay": bound}
