"""The CPU's output display: a 4-bit value (0-15) on two seven-segment digits.

A sum-of-products decoder folded into three storeys so it fits a 30 x 16 x 40 box. Term
rows run north along z at y=5 under the literal lines, which run along x at y=7 (the
same NOR plane as pla.py, turned). The output plane is stacked under the term rows: output
wires run along x at y=3, and each tap is a torch hanging off a row's support block at
y=4, lit while the term is true. Each input climbs from its pin to a feeder lane at y=9
(y=7 for the top line) and drops onto its true line; the true line's west end lights a
torch that feeds the complement line beside it. Each output leaves through a torch hanging
off its wire's support into y=1, is inverted back by a second torch, and runs north under
the decoder; route.py wires it to the digits.
"""

import itertools

from .build import Build, Pos
from .devices import DIGITS, seven_segment
from .fileformat import Spec
from .route import Circuit

SOLID = "white_concrete"
WIRE = "redstone_wire"
CROSS = "redstone_wire[north=side,south=side,east=side,west=side]"
REFRESH_AT = 4
FACING_FROM = {(1, 0): "west", (-1, 0): "east", (0, 1): "north", (0, -1): "south"}

SIZE = (30, 16, 40)
BITS = ["out0", "out1", "out2", "out3"]
PIN_X = [4, 6, 8, 10]
PIN_Z = 39
OUTS = ["a", "b", "c", "d", "e", "f", "g", "tens"]
# A minimum shared cover of all eight outputs, each output the OR of every term inside its
# on-set: 14 terms, and an exhaustive search finds none of 13 (positive outputs only).
TERMS = [[3, 7], [2, 3], [6], [12], [5], [8, 9], [15], [10, 14], [0, 4], [13],
         [0, 2, 8, 10], [10, 11, 14, 15], [4, 6, 12, 14], [1, 3, 9, 11]]
TRUE_Z = [28, 24, 20, 16]  # input i's true line; its complement is 2 north
OUT_Z = {o: 15 + 2 * k for k, o in enumerate(OUTS)}
ESCAPE_X = {"a": 3, "b": 6, "c": 9, "d": 12, "e": 15, "f": 18, "g": 21, "tens": 24}
SOURCE_Z = 11
UNITS_AT, TENS_AT = (9, 0, 0), (15, 0, 0)


def on_set(o: str) -> set[int]:
    return {n for n in range(16) if (n >= 10 if o == "tens" else o in DIGITS[n % 10])}


def literals(term: list[int]) -> dict[int, bool]:
    return {i: bool(term[0] >> i & 1) for i in range(4) if len({n >> i & 1 for n in term}) == 1}


class _Grid:
    def __init__(self):
        self.b = Build()

    def put(self, pos: Pos, state: str) -> None:
        state = "minecraft:" + state.removeprefix("minecraft:")
        old = self.b.blocks.get(pos)
        if old is not None and old != state:
            raise ValueError(f"{pos}: {old} vs {state}")
        if not all(0 <= v < lim for v, lim in zip(pos, SIZE)):
            raise ValueError(f"{pos} outside the box")
        self.b.blocks[pos] = state

    def wire(self, parent: dict[Pos, Pos | None], strength: int, slots: set[Pos]) -> None:
        """Dust on supports along a tree (each cell -> the cell feeding it), the root
        receiving `strength`; repeaters go in `slots` wherever the signal would run out."""
        children: dict[Pos, list[Pos]] = {}
        root = next(c for c, p in parent.items() if p is None)
        for c, p in parent.items():
            if p is not None:
                children.setdefault(p, []).append(c)
        order, stack = [], [root]
        while stack:
            c = stack.pop()
            order.append(c)
            stack.extend(children.get(c, []))
        gap: dict[Pos, int] = {}
        for c in reversed(order):
            gap[c] = max([1 if ch in slots else 1 + gap[ch] for ch in children.get(c, [])], default=0)
        level = {root: strength}
        for c in order:
            p = parent[c]
            state = WIRE
            if p is not None:
                here = level[p] - 1
                if c in slots and (here <= REFRESH_AT or here - gap[c] < 2):
                    state = f"repeater[facing={FACING_FROM[(c[0] - p[0], c[2] - p[2])]}]"
                    here = 16
                if here <= 0:
                    raise ValueError(f"signal dies at {c}")
                level[c] = here
            self.put(c, state)
            below = (c[0], c[1] - 1, c[2])
            if below not in self.b.blocks:
                self.put(below, SOLID)


def _path(cells: list[Pos]) -> dict[Pos, Pos | None]:
    return {c: (cells[i - 1] if i else None) for i, c in enumerate(cells)}


def _straight(cells: list[Pos]) -> set[Pos]:
    return {c for p, c, n in zip(cells, cells[1:], cells[2:])
            if p[1] == c[1] == n[1] and (c[0] - p[0], c[2] - p[2]) == (n[0] - c[0], n[2] - c[2])}


def decoder(drop: int | None = None) -> Spec:
    """`drop` leaves one term's output taps off: a broken copy for a control test."""
    terms = TERMS
    covers = {o: [k for k, t in enumerate(terms) if set(t) <= on_set(o) and k != drop] for o in OUTS}
    if drop is None:
        for o in OUTS:
            assert set().union(*(terms[k] for k in covers[o])) == on_set(o), o
    g = _Grid()
    row_x = [1 + 2 * k for k in range(len(terms))]
    east = row_x[-1] + 1

    def line_z(i: int, value: bool) -> int:
        return TRUE_Z[i] if value else TRUE_Z[i] - 2

    for i, x in enumerate(PIN_X):
        g.put((x, 0, PIN_Z), SOLID)
        g.put((x + 1, 0, PIN_Z), SOLID)
        g.put((x - 1, 0, PIN_Z), SOLID)
        g.put((x, 1, PIN_Z - 1), "repeater[facing=south]")
        g.put((x, 0, PIN_Z - 1), SOLID)
        zt = TRUE_Z[i]
        feed = [(x, 1 + k, PIN_Z - 2 - k) for k in range(7)]  # up to (x, 7, 31)
        if zt == 28:
            feed += [(x, 7, 30), (x, 7, 29), (x, 7, 28)]
        else:
            feed += [(x, 8, 30)] + [(x, 9, z) for z in range(29, zt + 1, -1)] + [(x, 8, zt + 1), (x, 7, zt)]
        west = [(xx, 7, zt) for xx in range(x - 1, 0, -1)]
        eastward = [(xx, 7, zt) for xx in range(x + 1, east + 1)]
        tree = _path(feed) | _path([feed[-1]] + west) | _path([feed[-1]] + eastward)
        tree[feed[-1]] = feed[-2]
        slots = _straight(feed) | {c for c in west + eastward if c[0] % 2 == 0} - {west[-1], eastward[-1]}
        g.wire(tree, 15, slots)
        g.put((0, 7, zt), SOLID)
        g.put((0, 7, zt - 1), "redstone_wall_torch[facing=north]")
        comp = [(xx, 7, zt - 2) for xx in range(0, east + 1)]
        g.wire(_path(comp), 15, {c for c in comp[1:-1] if c[0] % 2 == 0})

    for k, (term, x) in enumerate(zip(terms, row_x)):
        taps = [line_z(i, v) + 1 for i, v in literals(term).items()]
        outs = [OUT_Z[o] for o in OUTS if k in covers[o]]
        lo, hi = min(taps + outs), max(taps + outs)
        assert hi - lo < 15, f"row {k} spans {lo}..{hi}"
        for z in range(lo, hi + 1):
            g.put((x, 5, z), WIRE)
            g.put((x, 4, z), SOLID)
        for z in taps:
            g.put((x, 6, z), "redstone_wall_torch[facing=south]")
        for z in outs:
            g.put((x + 1, 4, z), "redstone_wall_torch[facing=east]")

    outputs = {}
    for o in OUTS:
        z, xe = OUT_Z[o], ESCAPE_X[o]
        taps = {row_x[k] + 1 for k in covers[o]}
        lo, hi = min(taps | {xe}), max(taps | {xe})
        left = [(xx, 3, z) for xx in range(lo, xe + 1)]
        right = [(xx, 3, z) for xx in range(hi, xe, -1)]
        for side in (left, right):
            if side:
                g.wire(_path(side), 15, {c for c in side[1:-1] if c[0] not in taps and c[0] != xe})
        g.put((xe, 2, z - 1), "redstone_wall_torch[facing=north]")
        g.put((xe, 1, z - 1), CROSS)
        g.put((xe, 0, z - 1), SOLID)
        g.put((xe, 1, z - 2), SOLID)
        g.put((xe, 1, z - 3), "redstone_wall_torch[facing=north]")
        for zz in range(z - 4, SOURCE_Z - 1, -1):
            g.put((xe, 1, zz), WIRE)
            g.put((xe, 0, zz), SOLID)
        outputs[o] = (xe, 1, SOURCE_Z)

    inputs = {bit: (x, 1, PIN_Z) for bit, x in zip(BITS, PIN_X)}
    return Spec("decoder", g.b, inputs=inputs, outputs=outputs, named=dict(outputs))


# "13" as the viewer sees it, rows top down, columns left to right: tens, a gap, units.
THIRTEEN = """\
.......###.
....#.....#
....#.....#
....#.....#
.......###.
....#.....#
....#.....#
....#.....#
.......###."""


GRAY = [k ^ (k >> 1) for k in range(16)]


def out_display(name: str = "cpu_out_display", drop: int | None = None) -> Spec:
    c = Circuit(name, size=SIZE)
    c.add("pla", decoder(drop), (0, 0, 0))
    c.add("units", seven_segment("digit"), UNITS_AT)
    c.add("tens", seven_segment("digit_one", "bc"), TENS_AT)
    for s in "abcdefg":
        c.connect(f"pla.{s}", f"units.{s}")
    c.connect("pla.tens", "tens.b", "tens.c")
    spec = c.build()
    spec.inputs = {k.removeprefix("pla."): v for k, v in spec.inputs.items()}
    spec.outputs = {}
    named = {k: v for k, v in spec.named.items() if not k.startswith("pla.")}
    for s in "abcdefg":
        named[f"u_{s}"] = named.pop(f"units.{s}0")
    named["t_b"], named["t_c"] = named.pop("tens.b0"), named.pop("tens.c0")
    spec.named = named
    seg_cells = [f"u_{s}" for s in "abcdefg"] + ["t_b", "t_c"]
    lines = [" ".join(BITS) + " | " + " ".join(seg_cells)]
    for n in GRAY:
        want = [int(s in DIGITS[n % 10]) for s in "abcdefg"] + [int(n >= 10)] * 2
        lines.append(" ".join(str(n >> i & 1) for i in range(4)) + " | " + " ".join(map(str, want)))
    spec.tests = [{"name": "digits", "truth_table": "\n".join(lines) + "\n", "max_delay": 40},
                  front_view_test(spec)]
    spec.traits = ["torch_based", "pistonless", "entityless"]
    spec.description = (
        "CPU output display: out0-out3 (out0 least significant, pins on the south face at x=4,6,8,10, y=1) "
        "shown as two seven-segment digits facing north on the z=0 face, tens on the viewer's left (blank for "
        "0-9, 1 for 10-15). A 14-term sum-of-products decoder in three storeys, routed to the digits; "
        "u_a-u_g, t_b, t_c are each segment's middle lamp.")
    return spec


def front_view_test(spec: Spec) -> dict:
    """Drive 13 and check every lamp against the picture the viewer should see. The viewer
    stands north looking south, so their left is +x: picture column 0 is the largest x."""
    n = 13
    right_x = UNITS_AT[0]
    left_x = TENS_AT[0] + 4
    width = left_x - right_x + 1
    checks = []
    for r, row in enumerate(THIRTEEN.splitlines()):
        assert len(row) == width
        y = 9 - r
        for col, ch in enumerate(row):
            x = left_x - col
            is_lamp = spec.build.blocks.get((x, y, 0)) == "minecraft:redstone_lamp"
            assert is_lamp or ch == ".", f"no lamp where the viewer should see one: {(x, y, 0)}"
            if is_lamp:
                checks.append(f"if block ~{x} ~{y} ~0 minecraft:redstone_lamp[lit={'true' if ch == '#' else 'false'}]")
    steps = [{"drive": {bit: n >> i & 1 for i, bit in enumerate(BITS)}}, {"wait": 60}]
    for chunk in itertools.batched(checks, 12):
        steps.append({"check": " ".join(chunk)})
    return {"name": "front view", "steps": steps}
