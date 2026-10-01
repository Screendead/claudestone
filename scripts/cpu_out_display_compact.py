"""CPU4 output display, compact: out0..out3 as two lamp digits facing north.

Units: a 3x5 lamp font (seg_lamp_3x5) at x=0..2, tens a single lamp column at x=4 (the
"1" is segments b and c, the right-hand column), black frame column at x=3. Each
segment's middle lamp is hard-powered by a repeater behind it, so it lights the lamps
touching it; the two holes stop the bleed between segments.

Decoder: a NOR-NOR PLA stacked in three storeys. Literal lines run north along z at
y=5 (dust on y=4 blocks); term rows run along x at y=3 under them; a tap is a wall torch
on a literal block over the row, lit while that literal is off, so a row is NOT(term).
Output lines run north at y=1 under the rows; an output tap is a wall torch hanging on a
row's support over the output dust, lit while the term is true, so an output line is the
OR of its terms. Each output then climbs a dust stair at its own column, turns west along
a repeater chain at its segment's height and runs north as a repeater lane into the feed.
A torch at the turn inverts the outputs the PLA builds as off-sets.
"""

import itertools

from redstone.build import Build, Pos
from redstone.devices import DIGITS
from redstone.fileformat import Spec, dump

SOLID = "white_concrete"
FRAME = "black_concrete"
LAMP = "redstone_lamp"
WIRE = "redstone_wire"

# Literal lines (true or complement) and their x at y=5.
LIT_X = {"b0": 0, "nb0": 2, "K": 4, "N": 6, "K2": 8, "b2": 10, "nb2": 12}
# Southmost dust of each literal line (its head lies south of that).
LIT_START = {"b0": 28, "nb0": 25, "K": 25, "N": 23, "K2": 25, "b2": 28, "nb2": 25}
# Terms over the literal lines (N = b1 xnor b3, K = b1 and not b3, K2 = b3 and not b1).
TERMS = {
    "T1": ["N", "nb0", "nb2"],   # 0, 10
    "T2": ["K", "b2", "nb0"],    # 6
    "T3": ["N", "b2", "nb0"],    # 4, 14
    "T4": ["N", "b0", "nb2"],    # 1, 11
    "T5": ["K", "b2", "b0"],     # 7
    "T6": ["N", "b0", "b2"],     # 5, 15
    "T8": ["K2", "nb2"],         # 8, 9
    "TB": ["b0"],                # odd
}
# Output -> (terms ORed on its line, line is the on-set?)
OUTS = {
    "a": (["T3", "T4"], False),
    "b": (["T2", "T6"], False),
    "c": (["TB", "T1", "T2", "T3", "T8"], True),
    "d": (["T3", "T4", "T5"], False),
    "e": (["TB", "T3"], False),
    "f": (["T1", "T2", "T3", "T6", "T8"], True),
    "g": (["T1", "T4", "T5"], False),
}
# Segment -> (lane x, lane height = driven lamp's y, turn slice, stair column).
# Lanes of segments turning further south pass the chains of those turning north, so a
# column further east turns further north.
ROUTE = {
    "b": (0, 4, 6, 1), "c": (0, 2, 6, 3),
    "d": (1, 1, 5, 5), "g": (1, 3, 5, 7), "a": (1, 5, 5, 9),
    "e": (2, 2, 4, 11), "f": (2, 4, 4, 13),
}
TENS_COL, TENS_SLICE, TENS_H = 15, 2, 3
TENS_TERMS = ("T8",)  # the tens line is the off-set: T8 OR NOT b3 (fed at the heads)
ROW0 = 11           # northmost term row
ROWS = list(TERMS)  # north to south
PINS_Z = 35
PIN_X = {"out0": 0, "out1": 2, "out2": 4, "out3": 6}
# Repeaters on output lines (under row supports) and literal lines (between rows).
OUT_REFRESH = (ROW0, ROW0 + 8)
LIT_REFRESH = (ROW0 + 7, 26)
T_REFRESH = (ROW0, ROW0 + 8, 28)


def row_z(t: str) -> int:
    return ROW0 + 2 * ROWS.index(t)


class Grid:
    def __init__(self):
        self.b = Build()

    def put(self, p: Pos, state: str) -> None:
        state = "minecraft:" + state.removeprefix("minecraft:")
        old = self.b.blocks.get(p)
        if old is not None and old != state:
            raise ValueError(f"{p}: {old} vs {state}")
        if min(p) < 0:
            raise ValueError(f"{p} outside the box")
        self.b.blocks[p] = state

    def solid(self, p: Pos) -> None:
        if p not in self.b.blocks:
            self.put(p, SOLID)

    def dust(self, p: Pos) -> None:
        self.put(p, WIRE)
        self.solid((p[0], p[1] - 1, p[2]))

    def rep(self, p: Pos, facing: str) -> None:
        self.put(p, f"repeater[facing={facing}]")
        self.solid((p[0], p[1] - 1, p[2]))


def face(g: Grid) -> dict[str, Pos]:
    named = {}
    for y in range(1, 6):
        for x in range(3):
            g.put((x, y, 0), FRAME if (x, y) in ((1, 2), (1, 4)) else LAMP)
        g.put((3, y, 0), FRAME)
        g.put((4, y, 0), LAMP)
    for x in range(5):
        g.put((x, 0, 0), FRAME)
    for s, (x, y, _, _) in ROUTE.items():
        named[f"u_{s}"] = (x, y, 0)
    named["t_b"], named["t_c"] = (4, 4, 0), (4, 2, 0)
    return named


def lanes(g: Grid) -> None:
    for s, (fx, h, sl, col) in ROUTE.items():
        inverted = not OUTS[s][1]
        for z in range(1, sl):
            g.rep((fx, h, z), "south")
        if inverted and col == fx + 1:
            g.put((fx, h, sl), "redstone_wall_torch[facing=west]")
        else:
            g.solid((fx, h, sl))
            first = col - 1
            if inverted:
                g.put((first, h, sl), "redstone_wall_torch[facing=west]")
                first -= 1
            for x in range(fx + 1, first + 1):
                g.rep((x, h, sl), "east")
        g.solid((col, h, sl))
        # Stair down and south from the turn block to y=1.
        for j in range(h, 0, -1):
            g.dust((col, j, sl + 1 + h - j))
    # Tens: one chain at y=3 hard-powers (4,3,2); the dust above and below it feeds the
    # repeaters behind the two driven tens lamps.
    g.rep((4, 4, 1), "south")
    g.rep((4, 2, 1), "south")
    g.put((4, 3, 2), SOLID)
    g.put((4, 4, 2), WIRE)
    g.dust((4, 2, 2))
    g.put((TENS_COL - 1, TENS_H, TENS_SLICE), "redstone_wall_torch[facing=west]")
    for x in range(5, TENS_COL - 1):
        g.rep((x, TENS_H, TENS_SLICE), "east")
    g.solid((TENS_COL, TENS_H, TENS_SLICE))
    for j in range(TENS_H, 0, -1):
        g.dust((TENS_COL, j, TENS_SLICE + 1 + TENS_H - j))


def pla(g: Grid) -> None:
    last = row_z(ROWS[-1])
    out_cols = {s: ROUTE[s][3] for s in OUTS}
    for t, lits in TERMS.items():
        z = row_z(t)
        taps = [LIT_X[l] + 1 for l in lits]
        users = [out_cols[s] for s, (ts, _) in OUTS.items() if t in ts]
        if t in TENS_TERMS:
            users.append(TENS_COL)
        for x in range(min(taps + users), max(taps + users) + 1):
            g.dust((x, 3, z))
        for l in lits:
            g.put((LIT_X[l] + 1, 4, z), "redstone_wall_torch[facing=east]")
        for x in users:
            g.put((x, 2, z + 1), "redstone_wall_torch[facing=south]")
    for s, (fx, h, sl, col) in ROUTE.items():
        for z in range(sl + h + 1, last + 2):
            if z in OUT_REFRESH:
                g.rep((col, 1, z), "south")
            else:
                g.dust((col, 1, z))
    for z in range(TENS_SLICE + TENS_H + 1, 34):
        if z in T_REFRESH:
            g.rep((TENS_COL, 1, z), "south")
        else:
            g.dust((TENS_COL, 1, z))
    for l, x in LIT_X.items():
        for z in range(ROW0, LIT_START[l] + 1):
            if z in LIT_REFRESH:
                g.rep((x, 5, z), "south")
            else:
                g.dust((x, 5, z))


def heads(g: Grid) -> dict[str, Pos]:
    """Pins on the south face, the climbs to the literal plane, complements, K/K2/N."""
    inputs = {}
    for x in range(max(PIN_X.values()) + 2):
        g.solid((x, 0, PINS_Z))
    for name, x in PIN_X.items():
        inputs[name] = (x, 1, PINS_Z)
        g.solid((x, 0, PINS_Z))
        g.rep((x, 1, PINS_Z - 1), "south")

    def stair_north(x, z_low, h_from, h_to):
        # dust at (x, h_from, z_low) climbing one block per step northward
        for k, y in enumerate(range(h_from, h_to + 1)):
            g.dust((x, y, z_low - k))

    def complement(x, zh):
        # true line dust at (x,5,zh) -> branch east -> block -> torch north -> line x+2
        g.dust((x + 1, 5, zh))
        g.put((x + 2, 5, zh), SOLID)
        g.put((x + 2, 5, zh - 1), "redstone_wall_torch[facing=north]")

    # b0: climb at x=0, complement to x=2.
    stair_north(0, 33, 1, 5)
    complement(0, 27)
    # b2: climb at x=4, jog east at y=5 to x=10, complement to x=12.
    stair_north(4, 33, 1, 5)
    for x in range(5, 11):
        g.dust((x, 5, 29))
    complement(10, 27)
    # b1 (west) and b3 (east) into a comparator pair under b2's climb: S = b1-b3 = K
    # into the block north of it, N = b3-b1 = K2 into the block south of it.
    for z in range(30, 34):
        g.dust((2, 1, z))
    g.rep((3, 1, 30), "west")
    g.dust((4, 1, 30))
    g.put((4, 1, 29), "comparator[facing=south,mode=subtract]")
    g.solid((4, 0, 29))
    g.put((5, 1, 30), "comparator[facing=north,mode=subtract]")
    g.solid((5, 0, 30))
    g.dust((5, 1, 29))
    g.rep((6, 1, 29), "east")
    g.dust((6, 1, 33))
    g.dust((7, 1, 33))
    for z in (32, 31, 30):
        g.rep((7, 1, z), "south")
    g.dust((7, 1, 29))
    g.put((4, 1, 28), SOLID)   # K
    g.put((5, 1, 31), SOLID)   # K2
    # K: dust on its block, climb north to the K line at x=4.
    g.put((4, 2, 28), WIRE)
    stair_north(4, 27, 3, 5)
    # K2: east of its block, up over b3 at y=3, north under b2's jog, up to x=8. (The
    # block under (6,2,30) sits beside the K2 comparator; a block feeds no side input.)
    g.dust((6, 1, 31))
    g.dust((6, 2, 30))
    g.dust((6, 3, 29))
    g.dust((7, 3, 29))
    for z in (29, 28, 27):
        g.dust((8, 3, z))
    stair_north(8, 26, 4, 5)
    # N = NOR(K, K2): both lines branch into a block whose torch starts the N line.
    g.dust((5, 5, 25))
    g.dust((7, 5, 25))
    g.put((6, 5, 25), SOLID)
    g.put((6, 5, 24), "redstone_wall_torch[facing=north]")
    # NOT b3 onto the tens line: b3 branches east into a block, a torch beside it.
    g.dust((8, 1, 33))
    g.put((9, 1, 33), SOLID)
    g.put((10, 1, 33), "redstone_wall_torch[facing=east]")
    for x in range(11, TENS_COL + 1):
        g.dust((x, 1, 33))
    return inputs


def digits_table() -> str:
    gray = [i ^ (i >> 1) for i in range(16)]
    cells = ["u_a", "u_b", "u_c", "u_d", "u_e", "u_f", "u_g", "t_b", "t_c"]
    lines = ["out0 out1 out2 out3 | " + " ".join(cells)]
    for v in gray:
        segs = DIGITS[v % 10]
        outs = [int(s in segs) for s in "abcdefg"] + [int(v >= 10)] * 2
        lines.append(" ".join(str(v >> i & 1) for i in range(4)) + " | " + " ".join(map(str, outs)))
    return "\n".join(lines) + "\n"


def build(mutant: str | None = None) -> tuple[Build, dict, dict]:
    g = Grid()
    named = face(g)
    lanes(g)
    pla(g)
    inputs = heads(g)
    if mutant:
        del g.b.blocks[MUTANTS[mutant]]
    return g.b, inputs, named


# One block removed: the T4 row's tap on output d (d stays off for 1 and 11).
MUTANTS = {"drop_d_T4": (ROUTE["d"][3], 2, row_z("T4") + 1)}


def cpu_out_display_compact(name: str = "cpu_out_display_compact", mutant: str | None = None) -> Spec:
    b, inputs, named = build(mutant)
    tests = [{"name": "digits", "truth_table": digits_table(), "max_delay": 60},
             front_view_test(13)]
    return Spec(name, b, inputs=inputs, named=named, tests=tests,
                traits=["torch_based", "comparator_based", "pistonless", "entityless"],
                description=(
                    "CPU output display, compact: out0-out3 (out0 least significant) enter on the south "
                    "face at y=1, z=35, x=0,2,4,6 (out0 west), each through a repeater facing south at z=34. "
                    "Units digit: a 3x5 lamp font at x=0..2, y=1..5 on the z=0 face (holes at (1,2) and (1,4)); "
                    "tens: one lamp column at x=4 (the 1, segments b and c), frame column x=3, both read from "
                    "the north. Each segment's middle lamp (u_a..u_g, t_b, t_c) is hard-powered by a repeater "
                    "behind it at z=1 and lights the lamps touching it. Decoder: a three-storey NOR-NOR PLA of "
                    "8 terms over b0, b2, N=(b1 xnor b3), K=b1-b3, K2=b3-b1 (a subtract-comparator pair), "
                    "outputs climbing dust stairs to repeater lanes at their segment's height."))


def lit_lamps(v: int) -> set[Pos]:
    """Lamps a reader should see lit for value v: each driven lamp and the lamps beside it."""
    lamps = {p for p, st in FACE_LAMPS.items()}
    lit = set()
    for s in DIGITS[v % 10]:
        x, y, _, _ = ROUTE[s]
        lit |= {(x + dx, y + dy, 0) for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))} & lamps
    if v >= 10:
        lit |= {(4, y, 0) for y in range(1, 6)}
    return lit


FACE_LAMPS = {(x, y, 0): LAMP for y in range(1, 6) for x in (0, 1, 2, 4)
              if (x, y) not in ((1, 2), (1, 4))}


def front_view_test(v: int) -> dict:
    lit = lit_lamps(v)
    conds = [f"if block ~{x} ~{y} ~{z} minecraft:redstone_lamp[lit={str(p in lit).lower()}]"
             for p in sorted(FACE_LAMPS) for x, y, z in [p]]
    steps = [{"drive": {f"out{i}": v >> i & 1 for i in range(4)}}, {"wait": 80}]
    steps += [{"check": " ".join(conds[i:i + 6])} for i in range(0, len(conds), 6)]
    return {"name": "front view", "steps": steps}


if __name__ == "__main__":
    import sys
    from pathlib import Path
    mutant = sys.argv[1] if len(sys.argv) > 1 else None
    name = "cpu_out_display_compact" + ("_mutant" if mutant else "")
    spec = cpu_out_display_compact(name, mutant)
    lo, hi = spec.build.bounds()
    print("bounds", lo, hi, "blocks", len(spec.build.blocks))
    Path(f"library/cpu_parts/{name}.redstone.yaml").write_text(dump(spec))
