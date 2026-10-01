"""CPU4 compact control decoder cpu_ctrl_compact.

The four op bits ride overhead as dust at y=3 on blocks at y=2, running south along z
(op3 at x=1, op1 at x=4, op2 at x=7, op0 at x=10). Logic lives at y=1 under them and
takes literals through taps from y=2: a wall torch on a bus block hangs over a y=1 cell
and lights it with NOT bit; a repeater reading a bus block drives a y=2 solid, which
powers the y=1 dust under it with the bit. So every literal is available, at 15, in the
tap columns x=2,3 (between buses 1 and 4), 5,6 and 8,9:

    x2: N3 | O1   x3: N1 | O3   x5: N1 | O2   x6: N2 | O1   x8: N2 | O0   x9: N0 | O2

Each product term is a row of subtract comparators facing east: the row starts on a
positive literal tap and each comparator subtracts the taps on its north and south side
cells. Rows sit two apart and share the side rows between them. Rows end in the feed
column x=11; outputs that OR several terms merge there through the side rows (through a
repeater where one term feeds two outputs), then a repeater at x=12 drives the east pin.
"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from redstone.build import Build
from redstone.fileformat import Spec, dump
from scripts.cpu_ctrl import control, gray

SOLID = "white_concrete"
WIRE = "redstone_wire"
BUS_X = {"op3": 1, "op1": 4, "op2": 7, "op0": 10}
LIT = {"op0": "0", "op1": "1", "op2": "2", "op3": "3"}
# tap column -> (bus x it hangs a torch from, (rep x, rear bus x) for the positive literal)
TAPS = {2: (1, (3, 4)), 3: (4, (2, 1)), 5: (4, (6, 7)), 6: (7, (5, 4)), 8: (7, (9, 10)), 9: (10, (8, 7))}
BIT_AT = {x: b for b, x in BUS_X.items()}
FEED, REP, PIN = 11, 12, 13
W = 14


def facing_from(src, dst):
    """Diode at dst whose input is on the src side."""
    dx, dz = src[0] - dst[0], src[2] - dst[2]
    return {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(dx, dz)]


class Dec:
    def __init__(self, length):
        self.L = length
        self.b = {}
        self.inputs, self.outputs, self.named = {}, {}, {}

    def put(self, p, s):
        old = self.b.get(p)
        if old is not None and old != s:
            raise ValueError(f"overlap at {p}: {old} vs {s}")
        self.b[p] = s

    def dust(self, x, z, y=1):
        self.put((x, y, z), WIRE)

    def rep(self, p, src):
        self.put(p, f"repeater[facing={facing_from(src, p)}]")

    def cmp(self, p, src):
        self.put(p, f"comparator[facing={facing_from(src, p)},mode=subtract]")

    # ---- taps ---------------------------------------------------------------
    def tap(self, x, z, lit):
        """Light (x,1,z) with lit: 'N<b>' by a torch, 'O<b>' by a repeater."""
        tbus, (rx, rbus) = TAPS[x]
        if lit == "N" + LIT[BIT_AT[tbus]]:
            side = "east" if tbus < x else "west"
            self.put((x, 2, z), f"redstone_wall_torch[facing={side}]")
        elif lit == "O" + LIT[BIT_AT[rbus]]:
            self.put((rx, 1, z), SOLID)
            self.rep((rx, 2, z), (rbus, 2, z))
            self.put((x, 2, z), SOLID)
        else:
            raise ValueError(f"{lit} not available at x={x}")
        self.dust(x, z)

    # ---- buses ----------------------------------------------------------------
    def buses(self, zlo, zhi):
        for x in BUS_X.values():
            for z in range(zlo, zhi + 1):
                self.put((x, 2, z), SOLID)
                self.put((x, 3, z), WIRE)

    def op_input(self, bit, z):
        """West pin for bit at row z; climbs onto its bus at the same row."""
        bx = BUS_X[bit]
        self.put((0, 0, z), SOLID)
        self.inputs[bit] = (0, 1, z)
        self.rep((1, 1, z), (0, 1, z))
        if bx == 1:
            self.put((2, 1, z), SOLID)
            self.dust(2, z, y=2)
        else:
            for x in range(2, bx - 1):
                self.dust(x, z)
            self.put((bx - 1, 1, z), SOLID)
            self.dust(bx - 1, z, y=2)

    # ---- product rows ----------------------------------------------------------
    def row(self, z, xs, comps, rear=None, step=1):
        """Cells xs (in signal order) of row z: comparators at comps {x: (north, south)},
        dust elsewhere; rear (x, lit) taps the first cell."""
        if rear:
            self.tap(rear[0], z, rear[1])
        for x in xs:
            if x in comps:
                self.cmp((x, 1, z), (x - step, 1, z))
                n, s = comps[x]
                if n:
                    self.tap(x, z - 1, n)
                if s:
                    self.tap(x, z + 1, s)
            else:
                self.dust(x, z)

    def east(self, z, comps, rear):
        self.row(z, range(rear[0] + 1, FEED + 1), comps, rear)

    def west(self, z, comps, start, rear=None):
        self.row(z, range(start, 0, -1), comps, rear, step=-1)

    def out_east(self, name, z):
        self.put((W - 1, 0, z), SOLID)
        self.dust(W - 1, z)
        self.rep((REP, 1, z), (FEED, 1, z))
        self.outputs[name] = (W - 1, 1, z)

    def build(self, name):
        b = Build()
        for p, s in self.b.items():
            b.place(p, s)
        for (x, y, z) in list(b.blocks):
            if y == 1 and (x, 0, z) not in b.blocks:
                b.blocks[(x, 0, z)] = "minecraft:" + SOLID
        return Spec(name, b, inputs=dict(self.inputs), outputs=dict(self.outputs),
                    named={**self.named, **self.outputs})


def north(d):
    """jt (x=1) and hlt (x=11) on the north face; jz/jc and m11 run west into jt's column."""
    # jt pin, repeater, and the merge column x=1 rows 2..8
    d.put((1, 0, 0), SOLID); d.dust(1, 0); d.rep((1, 1, 1), (1, 1, 2)); d.outputs["jt"] = (1, 1, 0)
    for z in range(2, 9):
        d.dust(1, z)
    # m11 = O0 - O2 - N1 - N3 (row 2, westward from an O0 tap at x8)
    d.row(2, range(7, 1, -1), {5: ("O2", None), 3: ("N1", None), 2: ("N3", None)}, rear=(8, "O0"), step=-1)
    # hlt = O3 - N1 - N2 - N0 (row 4, eastward), up x=11 to the north pin
    d.row(4, range(4, FEED + 1), {5: ("N1", None), 6: (None, "N2"), 9: ("N0", None)}, rear=(3, "O3"))
    d.dust(FEED, 3); d.dust(FEED, 2); d.rep((FEED, 1, 1), (FEED, 1, 2))
    d.put((FEED, 0, 0), SOLID); d.dust(FEED, 0); d.outputs["hlt"] = (FEED, 1, 0)
    # jz: z - O0 - N2 - O1 - N3 (row 8 westward from the z pin); jc: c - N0 - O1 - N2 joins at x4
    for name, z in (("z", 8), ("c", 10)):
        d.put((W - 1, 0, z), SOLID); d.inputs[name] = (W - 1, 1, z); d.rep((REP, 1, z), (W - 1, 1, z))
    d.row(8, range(FEED, 0, -1), {8: ("O0", None), 6: ("N2", "O1"), 2: (None, "N3")}, step=-1)
    d.row(10, range(FEED, 3, -1), {9: (None, "N0"), 6: ("O1", "N2")}, step=-1)
    d.dust(4, 9)


def products(d, o=0):
    """Eastward product rows from row o. xsel, sub and wf OR their terms in the feed column;
    m14a feeds both xsel and sub through repeaters; wa takes wf and za through repeaters."""
    def e(z, comps, rear):
        d.east(z + o, comps, rear)

    def f(z, kind="dust", src=None):
        if kind == "dust":
            d.dust(FEED, z + o)
        else:
            d.rep((FEED, 1, z + o), (FEED, 1, src + o))
    top = (None, None) if o == 12 else ("N2", None), (None, None) if o == 12 else ("N0", None)
    e(0, {3: ("N1", None), 6: top[0], 9: top[1]}, (2, "N3"))             # m7 (N2, N0 from jc's row when o=12)
    e(2, {6: (None, "O1"), 9: ("N0", "O2")}, (2, "N3"))                   # m1
    e(5, {5: (None, "N1"), 8: ("N2", "O0")}, (3, "O3"))                   # m14a
    for z in (1, 3):
        f(z)
    f(4, "rep", 5); f(6, "rep", 5); f(7)
    e(8, {3: (None, "N1"), 9: ("N0", "O2")}, (2, "N3"))                   # m3
    e(10, {9: (None, "N0")}, (3, "N1"))                                   # za (O2 from the row above)
    f(11, "rep", 10); f(12); f(13, "rep", 14)
    e(14, {3: ("N1", None)}, (2, "N3"))                                   # W1
    e(16, {8: (None, "N2")}, (2, "N3"))                                   # W2
    e(18, {5: (None, "N1"), 8: (None, "O0")}, (3, "O3"))                  # m14b (N2 from the row above)
    f(15); f(17)
    e(20, {5: (None, "O2"), 8: (None, None)}, (3, "O3"))                  # wo (N1, O0 from the row above)
    e(22, {5: (None, None), 6: (None, "O1")}, (3, "O3"))                  # wb (O2 from the row above)
    for name, z in (("xsel", 2), ("sub", 8), ("za", 10), ("wa", 12), ("wf", 14), ("wo", 20), ("wb", 22)):
        d.out_east(name, z + o)




def bus_taps(d, bx):
    zs = set()
    for (x, y, z), s in d.b.items():
        if y == 2 and abs(x - bx) == 1 and ("torch" in s and ((x < bx) == ("west" in s)) or
                                            ("repeater" in s and (("facing=west" in s and x > bx) or ("facing=east" in s and x < bx)))):
            zs.add(z)
    return zs


def bus_repeaters(d, zlo, zhi, rows):
    """Refresh each bus before it runs out, both ways from its feed, never at a tap row."""
    for bit, bx in BUS_X.items():
        zf = rows[bit]
        taps = bus_taps(d, bx)
        for step, facing in ((-1, "south"), (1, "north")):
            level = 15 - (bx - 1)
            z = zf + step
            while zlo <= z <= zhi:
                level -= 1
                if level <= 3 and z not in taps:
                    d.b[(bx, 3, z)] = f"repeater[facing={facing}]"
                    level = 16
                z += step


OUTS = ["xsel", "za", "sub", "wa", "wb", "wo", "wf", "hlt", "jt"]
INS = ["op0", "op1", "op2", "op3", "z", "c"]
ROWS = {"op0": 13, "op1": 15, "op2": 17, "op3": 19}
PRODUCTS_AT = 21
LENGTH = 45
CONTROL_MAX = 14     # MEASURED worst over the table on dsat (PASS line gives each edge)
FLAG_MAX = 10


def pin_floors(d):
    """Pins stand on solid with solid y=0 one cell either way along their face."""
    for p in list(d.inputs.values()) + list(d.outputs.values()):
        x, _, z = p
        along = [(x, z - 1), (x, z + 1)] if x in (0, W - 1) else [(x - 1, z), (x + 1, z)]
        for ax, az in [(x, z)] + along:
            d.b.setdefault((ax, 0, az), SOLID)
            for y in (1, 2):
                if (ax, az) != (x, z):
                    assert (ax, y, az) not in d.b or d.b[(ax, y, az)] == SOLID, (p, (ax, y, az))


def row_text(op, z, c):
    exp = control(op, z, c)
    bits = [op >> i & 1 for i in range(4)] + [z, c]
    return " ".join(map(str, bits)) + " | " + " ".join(str(exp[o]) for o in OUTS)


def tests():
    head = " ".join(INS) + " | " + " ".join(OUTS)
    zc = [(0, 0), (0, 1), (1, 1), (1, 0)]
    lines = [head]
    for k, op in enumerate(gray(4)):
        for z, c in (zc if k % 2 == 0 else zc[::-1]):
            lines.append(row_text(op, z, c))
    flags = [head] + [row_text(op, z, c) for op in (12, 13) for z, c in zc + [(0, 0)]]
    return [
        {"name": "control", "truth_table": "\n".join(lines) + "\n", "max_delay": CONTROL_MAX},
        {"name": "flags", "truth_table": "\n".join(flags) + "\n", "max_delays": {"jt": FLAG_MAX}},
    ]


def build(name="cpu_ctrl_compact", mutant=None, rows=None, o=PRODUCTS_AT, L=LENGTH):
    rows = rows or ROWS
    d = Dec(L)
    d.buses(1, L - 1)
    for bit, z in rows.items():
        d.op_input(bit, z)
    north(d)
    products(d, o)
    bus_repeaters(d, 1, L - 1, rows)
    pin_floors(d)
    if mutant == "drop_m7_n1":
        # m7's N1 tap goes: xsel also fires for op 5
        del d.b[(3, 2, o - 1)]
    return d


DESCRIPTION = (
    "CPU4 compact control decoder: op0..3, z, c to xsel, za, sub, wa, wb, wo, wf, hlt and "
    "jt = B or (C and z) or (D and c), the function of scripts/cpu_ctrl.py without the imm gates. "
    "The four op bits run overhead as dust at y=3 on blocks at y=2 along z (op3 x=1, op1 x=4, "
    "op2 x=7, op0 x=10), as the input lines of redstone/pla.py do; the logic sits at y=1 under them. "
    "A wall torch on a bus block hangs over a y=1 cell and lights it with NOT bit (pla.py's tap; "
    "mechanics weak_powered_block_skips_dust keeps the cells under the buses dark), and a repeater "
    "reading a bus block drives a solid that powers the dust below it with the bit (not_gate's "
    "repeater-into-block, mechanics dust_powers_block_below and comparator_through_block_keeps_dust_level "
    "for the reads). Every product term is a row of subtract comparators, each an AND NOT of "
    "and/and_comparator_lightless and and/and_comparator_3input: the row starts on a positive "
    "literal tap and each comparator subtracts the taps on its side cells (mechanics "
    "comparator_side_input_sources); rows two apart share the side row between them. Outputs that "
    "OR several terms merge as dust in the feed column x=11; a term feeding two outputs (m14 into "
    "xsel and sub), and wa = wf or za, go through repeaters. jz and jc run west from the z and c pins "
    "and m11 west from an op0 tap into the jt column x=1; hlt runs east to x=11 and up to the north "
    "pin. Buses are refreshed by repeaters at y=3 where they would run out. "
    "Pins: west op0..op3 at z=13,15,17,19 (y=1); north jt x=1, hlt x=11; east (x=13, north to south) "
    "z 8, c 10, xsel 23, sub 29, za 31, wa 33, wf 35, wo 41, wb 43."
)


def cpu_ctrl_compact(name="cpu_ctrl_compact", mutant=None):
    d = build(name, mutant)
    spec = d.build(name)
    spec.tests = tests()
    spec.description = DESCRIPTION
    return spec


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "library" / "cpu_parts"
    for mutant, suffix in ((None, ""), ("drop_m7_n1", "_mutant")) if "--mutant" in sys.argv else ((None, ""),):
        spec = cpu_ctrl_compact("cpu_ctrl_compact" + suffix, mutant)
        (out / f"{spec.name}.redstone.yaml").write_text(dump(spec))
        print("wrote", spec.name, spec.build.bounds())
