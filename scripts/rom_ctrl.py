"""CPU4 program memory: 16 words x 8 bits on levers, addressed by pc.

Even words (A) sit low: word line dust at y=1, levers at y=2. Odd words (B) sit four
higher: word line at y=5, levers at y=6, in the columns between A's. Pair p takes x =
4+4p .. 9+4p: A word line, A repeater, A cell block (lever on top), B cell block (lever on
top), B repeater, B word line (= the next pair's A repeater column, one level up).

Word lines are active low: decoder taps (torches hanging off the pc literal rows) light a
word line whenever a literal it needs is false. A cell is a block with a lever on top,
strongly powered by the lever or by a repeater from its word line; a torch on its south
face lights the bit row (via the block above it) only when the word is selected and its
lever is off. A bit row therefore carries NOT bit; the A and B rows of a bit merge into
one block whose torch gives the bit.
"""

from redstone.build import Build, Pos
from redstone.fileformat import Spec

SOLID = "white_concrete"
WIRE = "redstone_wire"
BOX = (48, 16, 40)

PC_PINS = [4, 7, 10, 13]          # east face z
PIMM_PINS = [19, 22, 25, 28]      # east face z
LOW_CELLS = [18, 21, 24, 27]      # cell rows of bits 0-3 (bit row = cell + 1 = pimm pin z)
OP_CELLS = [29, 31, 33, 35]       # cell rows of bits 4-7
CELLS = LOW_CELLS + OP_CELLS
W_END = CELLS[-1]
W_REPEATERS = [17, 26]
LIVE_LEVERS = {(2, 0), (2, 1)}
FEED_JOG_X = [41, 39, 39, None]   # where each pc true line turns north to its row


def rep(facing: str) -> str:
    """Repeater whose input is on side `facing`."""
    return f"repeater[facing={facing},delay=1]"


def torch(facing: str) -> str:
    return f"redstone_wall_torch[facing={facing}]"


def rows():
    """(z, pc bit, polarity) of the decoder literal rows."""
    for i in range(4):
        yield 1 + 4 * i, i, True
        yield 3 + 4 * i, i, False


def rom_ctrl(name: str, words: list[int], description: str = "") -> Spec:
    assert len(words) == 16
    b = Build()
    named: dict[str, Pos] = {}
    outputs: dict[str, Pos] = {}
    inputs: dict[str, Pos] = {}

    def dust(pos, support=True):
        b.place(pos, WIRE)
        x, y, z = pos
        if support and y > 1 and (x, y - 1, z) not in b.blocks:
            b.place((x, y - 1, z), SOLID)

    # Word lines and cells.
    def word_x(w):
        p = w // 2
        xb = 4 + 4 * p
        if w % 2 == 0:
            return dict(level=0, wl=xb, r=xb + 1, cell=xb + 2, rface="west")
        return dict(level=4, wl=xb + 5, r=xb + 4, cell=xb + 3, rface="east")

    for w in range(16):
        g = word_x(w)
        y = 1 + g["level"]
        for z in range(2, W_END + 1):
            if z in W_REPEATERS:
                b.place((g["wl"], y, z), rep("north"))
                if y > 1:
                    b.place((g["wl"], y - 1, z), SOLID)
            else:
                dust((g["wl"], y, z))
        named[f"w{w}"] = (g["wl"], y, CELLS[0])
        for bit, zc in enumerate(CELLS):
            on = bool(words[w] >> bit & 1)
            b.place((g["r"], y, zc), rep(g["rface"]))
            if y > 1:
                b.place((g["r"], y - 1, zc), SOLID)
            b.place((g["cell"], y, zc), SOLID)
            b.place((g["cell"], y + 1, zc), f"lever[face=floor,facing=north,powered={'true' if on else 'false'}]")
            b.place((g["cell"], y, zc + 1), torch("south"))
            b.place((g["cell"], y + 1, zc + 1), SOLID)
            if (w, bit) in LIVE_LEVERS:
                named[f"lv{w}_{bit}"] = (g["cell"], y + 1, zc)

    # Bit rows: A at y=3 (x 4..39) into the merge block at x=40, B at y=7 (x 7..37) then a
    # stair down onto that block. Repeaters (flowing east) skip cell columns.
    for bit, zc in enumerate(CELLS):
        z = zc + 1
        for x in range(4, 40):
            if (x, 2, z) not in b.blocks:
                b.place((x, 2, z), SOLID)
            b.place((x, 3, z), rep("west") if x in (21, 37) else WIRE)
        for x in range(7, 38):
            if (x, 6, z) not in b.blocks:
                b.place((x, 6, z), SOLID)
            b.place((x, 7, z), rep("west") if x in (21, 36) else WIRE)
        dust((38, 6, z)), dust((39, 5, z)), dust((40, 4, z))
        b.place((40, 3, z), SOLID)
        b.place((41, 3, z), torch("east"))
        if bit < 4:
            dust((42, 3, z)), dust((43, 2, z)), dust((44, 1, z)), dust((45, 1, z))
            b.place((46, 1, z), rep("west"))
            b.place((47, 1, z), WIRE)
            outputs[f"pimm{bit}"] = (47, 1, z)
        else:
            named[f"op{bit - 4}"] = (41, 3, z)

    # Decoder literal rows: A rows at y=3, B rows at y=7. True rows come from the east,
    # complements and the B copies from a torch tower at x=2.
    for z, i, pol in rows():
        a_reps = (5, 21, 37) if pol else (17,)
        a_face = "east" if pol else "west"
        a_lo, a_hi = (3, 38) if pol else (2, 32)
        for x in range(a_lo, a_hi + 1):
            if x in a_reps:
                b.place((x, 2, z), SOLID).place((x, 3, z), rep(a_face))
            else:
                dust((x, 3, z))
        for x in range(3 if pol else 2, 38):
            if x in (15, 31):
                b.place((x, 6, z), SOLID).place((x, 7, z), rep("west"))
            else:
                dust((x, 7, z))
        if pol:
            b.place((2, 3, z), SOLID)
            b.place((2, 3, z + 1), torch("south"))
            b.place((2, 4, z), "redstone_torch")
            b.place((2, 5, z), SOLID)
            b.place((2, 6, z), "redstone_torch")
            b.place((2, 7, z), SOLID)
            b.place((2, 7, z + 1), torch("south"))
    for w in range(16):
        g = word_x(w)
        y = 2 + g["level"]
        for z, i, pol in rows():
            want = bool(w >> i & 1)
            if pol == want:
                b.place((g["wl"], y, z + 1), torch("south"))

    # pc inputs on the east face, climbing to y=3 and turning to their true rows.
    for i, zp in enumerate(PC_PINS):
        zt = 1 + 4 * i
        inputs[f"pc{i}"] = (47, 1, zp)
        b.place((46, 1, zp), rep("east"))
        dust((45, 1, zp)), dust((44, 2, zp)), dust((43, 3, zp))
        jog = FEED_JOG_X[i]
        if jog is None:
            for x in range(39, 43):
                dust((x, 3, zp))
            continue
        for x in range(jog, 43):
            dust((x, 3, zp))
        for z in range(zt, zp):
            dust((jog, 3, z))
        for x in range(39, jog):
            dust((x, 3, zt))

    b.with_base()
    lo, hi = b.bounds()
    assert lo[0] >= 0 and lo[2] >= 0 and hi[0] < BOX[0] and hi[1] < BOX[1] and hi[2] < BOX[2], (lo, hi)
    spec = Spec(name, b, inputs=inputs, outputs=outputs, named={**named, **outputs},
                description=description or default_description(words))
    spec.traits = ["torch_based", "pistonless", "entityless"]
    spec.tests = tests(name, words)
    return spec


def default_description(words):
    prog = " ".join(f"{w:02X}" for w in words)
    return ("CPU4 program memory (stage 1 of ROM_CTRL: no control decoder yet). 16 words x 8 bits on "
            f"levers, lever on = 1, words {prog}. Lever of word w, bit b: x = 6+2w at y=2 for even w, "
            "x = 5+2w at y=6 for odd w (word 0 at the smallest x, the viewer's right); z = 18, 21, 24, 27, 29, "
            "31, 33, 35 for b = 0..7 (bit 0 nearest the viewer). pc0..3 in and pimm0..3 out on the east face; "
            "op0..3 are the bit 4-7 torches.")


GRAY = [0, 1, 3, 2, 6, 7, 5, 4, 12, 13, 15, 14, 10, 11, 9, 8]


def tests(name, words):
    head = "pc0 pc1 pc2 pc3 | pimm0 pimm1 pimm2 pimm3 op0 op1 op2 op3"
    lines = [head]
    for pc in GRAY:
        w = words[pc]
        lines.append(" ".join(str(pc >> i & 1) for i in range(4)) + " | "
                     + " ".join(str(w >> i & 1) for i in range(8)))
    out = [{"name": "program", "truth_table": "\n".join(lines) + "\n", "max_delay": 40, "settle": 40}]
    if name == "cpu_rom_ctrl":
        # Word 2 is 1A: flip bit 0 (0 -> 1) and bit 1 (1 -> 0).
        out.append({"name": "levers live", "settle": 60, "steps": [
            {"drive": {"pc1": 1}}, {"wait": 40},
            {"expect": {"pimm0": 0, "pimm1": 1, "pimm2": 0, "pimm3": 1}},
            {"use": "lv2_0"}, {"use": "lv2_1"}, {"wait": 20},
            {"expect": {"pimm0": 1, "pimm1": 0, "pimm2": 0, "pimm3": 1}},
            {"use": "lv2_0"}, {"use": "lv2_1"}, {"wait": 20},
            {"expect": {"pimm0": 0, "pimm1": 1, "pimm2": 0, "pimm3": 1}},
        ]})
    return out
