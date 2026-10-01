"""CPU4 register file, compact: A and B master/slave, OUT, Z and C, all repeater-lock latches.

Bit k owns z rows 1+8k .. 8+8k (v0..v7). A row v0 flows east: y pin -> A master -> A slave -> a.
a returns west on row v3 to its pin, runs east on v0 to OUT, and down column x=10 to row v5,
where the B row flows west: B master -> B slave -> b pin. Every latch is a repeater locked from
the south by a repeater reading a block; dust on that block's top climbs to a hold line at y=3
running along z (x = 2 A, 6 slaves, 10 B, 14 OUT, 18 flags). A tap must sit beside exactly one
line, so lines are 4 apart. Each line comes down to a head at y=1 (row 38): hold = NOT cap OR
NOT we, one wall torch on the cap row (cap dust at y=2 on blocks, row 40) and one on the
enable's block, whose net crosses the cap row at y=4. The slave line's head has only NOT com.
"""

from redstone.build import Build
from redstone.fileformat import Spec

SOLID = "white_concrete"
FACING = {"N": "south", "S": "north", "E": "west", "W": "east"}   # output side -> facing
WALL = {"N": "north", "S": "south", "E": "east", "W": "west"}

BITS = 4
PITCH = 8
LINE = {"a": 2, "s": 6, "b": 10, "o": 14, "f": 18}
HEAD_Z = 38
CAP_Z = 40
PIN_Z = 45
LINE_REPS = (26, 12)
EN_X = {"a": 4, "s": 8, "b": 12, "o": 16, "f": 20}     # enable (com for s) block / net column
CAP_X = 10
Z_X, C_X = 24, 22
ZO_Z, CO_Z = 33, 35
OUT_X = [16 + 2 * k for k in range(BITS)]
RUN = 14


class Grid:
    def __init__(self):
        self.b = {}

    def put(self, p, s):
        if p in self.b and self.b[p] != s:
            raise ValueError(f"clash at {p}: {self.b[p]} vs {s}")
        self.b[p] = s

    def floor(self, p):
        q = (p[0], p[1] - 1, p[2])
        if q not in self.b:
            self.put(q, SOLID)

    def blk(self, p):
        self.put(p, SOLID)

    def dust(self, p):
        self.put(p, "redstone_wire")
        self.floor(p)

    def rep(self, p, out):
        self.put(p, f"repeater[facing={FACING[out]},delay=1]")
        self.floor(p)

    def torch(self, p, out):
        self.put(p, f"redstone_wall_torch[facing={WALL[out]}]")


def zrow(k, v):
    return 1 + PITCH * k + v


def latch(g, q, out):
    """Repeater q outputting `out` (E or W), lock repeater south of it, tap block and tap dust."""
    x, _, z = q
    g.rep(q, out)
    g.rep((x, 1, z + 1), "N")
    g.blk((x, 1, z + 2))
    g.dust((x, 2, z + 2))


def build(mutant=None):
    g = Grid()
    named, outputs, inputs = {}, {}, {}
    for k in range(BITS):
        v = [zrow(k, i) for i in range(8)]
        # A row
        inputs[f"y{k}"] = (0, 1, v[0])
        g.rep((1, 1, v[0]), "E")
        g.dust((2, 1, v[0]))
        latch(g, (3, 1, v[0]), "E")
        g.dust((4, 1, v[0]))
        latch(g, (5, 1, v[0]), "E")
        named[f"ma{k}"], named[f"sa{k}"] = (3, 1, v[0]), (5, 1, v[0])
        # a: junction (6,v0); west on v3 to its pin, east on v0, down x=10 to v5
        for z in (v[0], v[1], v[2], v[3]):
            g.dust((6, 1, z))
        for x in range(2, 6):
            g.dust((x, 1, v[3]))
            if x != 2:
                g.blk((x, 2, v[3]))
        g.rep((1, 1, v[3]), "W")
        outputs[f"a{k}"] = (0, 1, v[3])
        for x in range(7, 13):
            g.dust((x, 1, v[0]))
            if x != LINE["b"]:
                g.blk((x, 2, v[0]))
        for z in v[1:6]:
            g.dust((10, 1, z))
        # B row flows west
        latch(g, (9, 1, v[5]), "W")
        g.dust((8, 1, v[5]))
        latch(g, (7, 1, v[5]), "W")
        named[f"mb{k}"], named[f"sb{k}"] = (9, 1, v[5]), (7, 1, v[5])
        for x in range(2, 7):
            g.dust((x, 1, v[5]))
        g.rep((1, 1, v[5]), "W")
        outputs[f"b{k}"] = (0, 1, v[5])
        # OUT latch and its lane to the north face
        latch(g, (13, 1, v[0]), "E")
        named[f"mo{k}"] = (13, 1, v[0])
        X = OUT_X[k]
        path = [(14, v[0])]
        if k == 0:
            path += [(15, v[0]), (15, v[0] + 1), (16, v[0] + 1)]
        else:
            path += [(x, v[0]) for x in range(15, X + 1)] + [(X, z) for z in range(v[0] - 1, 1, -1)]
        run = 0
        for x, z in path:
            if run == RUN and z < v[0]:
                g.rep((x, 1, z), "N")
                run = 0
            else:
                g.dust((x, 1, z))
                run += 1
        g.rep((X, 1, 1), "N")
        outputs[f"out{k}"] = (X, 1, 0)
    # cover the B taps of the band above against the next band's v0 dust (and the zo row)
    for k in range(BITS):
        for x in (7, 9):
            g.blk((x, 2, zrow(k, 0) + PITCH)) if (x, 2, zrow(k, 0) + PITCH) not in g.b else None
    # flags: Z (lock from the north), C (lock from the south), line x=18
    inputs["zo"], inputs["co"] = (0, 1, ZO_Z), (0, 1, CO_Z)
    for z, out_x, name, lock in ((ZO_Z, Z_X, "z", -1), (CO_Z, C_X, "c", 1)):
        g.rep((1, 1, z), "E")
        for x in range(2, 17):
            g.dust((x, 1, z))
        g.rep((17, 1, z), "E")
        g.rep((17, 1, z + lock), "N" if lock == 1 else "S")
        g.blk((17, 1, z + 2 * lock))
        g.dust((17, 2, z + 2 * lock))
        for x in range(18, out_x + 1):
            g.dust((x, 1, z))
        for zz in range(z + 1, PIN_Z - 1):
            if zz == z + 5:
                g.rep((out_x, 1, zz), "S")
            else:
                g.dust((out_x, 1, zz))
        g.rep((out_x, 1, PIN_Z - 1), "S")
        outputs[name] = (out_x, 1, PIN_Z)
        named["m" + name] = (17, 1, z)
    for x in (7, 9):
        g.put((x, 2, ZO_Z), SOLID) if (x, 2, ZO_Z) not in g.b else None
    # hold lines
    for key, L in LINE.items():
        top = 31 if key == "f" else 3
        for z in range(top, HEAD_Z - 1):
            if z in LINE_REPS and key != "f":
                g.put((L, 2, z), SOLID)
                g.rep((L, 3, z), "N")
            else:
                if (L, 2, z) not in g.b:
                    g.blk((L, 2, z))
                g.dust((L, 3, z))
        g.blk((L, 1, HEAD_Z - 1))
        g.dust((L, 2, HEAD_Z - 1))
        g.dust((L, 1, HEAD_Z))
        en = EN_X[key]
        g.torch((L + 1, 1, HEAD_Z), "W")
        g.blk((en, 1, HEAD_Z))
        if key != "s":
            g.torch((L, 1, HEAD_Z + 1), "N")
        # enable / com net from the south face, over the cap row at y=4
        pin = {"a": "wa", "s": "com", "b": "wb", "o": "wo", "f": "wf"}[key]
        inputs[pin] = (en, 1, PIN_Z)
        g.rep((en, 1, PIN_Z - 1), "N")
        g.dust((en, 1, PIN_Z - 2))
        g.blk((en, 1, PIN_Z - 3)); g.dust((en, 2, PIN_Z - 3))
        g.blk((en, 2, PIN_Z - 4)); g.dust((en, 3, PIN_Z - 4))
        g.blk((en, 3, CAP_Z)); g.dust((en, 4, CAP_Z))
        g.blk((en, 2, CAP_Z - 1)); g.dust((en, 3, CAP_Z - 1))
        g.dust((en, 2, HEAD_Z))
    # cap row
    for x in range(1, 20):
        g.blk((x, 1, CAP_Z))
        g.dust((x, 2, CAP_Z))
    inputs["cap"] = (CAP_X, 1, PIN_Z)
    g.rep((CAP_X, 1, PIN_Z - 1), "N")
    for z in range(CAP_Z + 1, PIN_Z - 1):
        g.dust((CAP_X, 1, z))
    for p in outputs.values():
        g.dust(p)
    for p in inputs.values():
        g.floor(p)
    if mutant:
        del g.b[(5, 1, zrow(0, 1))]    # A's bit-0 slave loses its lock: A slave transparent
    return g, inputs, outputs, named


def region(p):
    x, _, z = p
    if z >= ZO_Z or x in LINE.values():
        return "flags" if (x >= 17 and z < HEAD_Z - 1) else "ctl"
    if x >= 13:
        return "out"
    if (z - 1) % PITCH >= 4 and x <= 10:
        return "b"
    return "a"


def regs_tests():
    from scripts.cpu_regs import regs_tests as old
    ys = {f"y{k}": 1 for k in range(BITS)}
    timing = [{"drive": {"wa": 1, "wf": 1, "zo": 1, "co": 1, **ys}}, {"wait": 20},
              {"drive": {"cap": 1}}, {"wait": 10}, {"drive": {"cap": 0}}, {"wait": 30},
              {"drive": {"wa": 0, "wf": 0, "wo": 1, "wb": 1}}, {"wait": 20},
              {"drive": {"com": 1}}, {"wait": 10}, {"drive": {"com": 0}}, {"wait": 40},
              {"drive": {"cap": 1}}, {"wait": 10}, {"drive": {"cap": 0}}, {"wait": 30},
              {"drive": {"com": 1}}, {"wait": 10}, {"drive": {"com": 0}}, {"wait": 40},
              {"expect": {**{f"a{k}": 1 for k in range(BITS)}, **{f"b{k}": 1 for k in range(BITS)},
                          **{f"out{k}": 1 for k in range(BITS)}, "z": 1, "c": 1}}]
    return [t for t in old() if t["name"] != "timing"] + [{"name": "timing", "steps": timing}]


def cpu_regs_compact(name="cpu_regs_compact", mutant=None) -> Spec:
    g, inputs, outputs, named = build(mutant)
    b = Build()
    for p, s in sorted(g.b.items()):
        b.place(p, s)
    spec = Spec(name, b, inputs=inputs, outputs=outputs, named={**named, **outputs},
                traits=["pistonless", "entityless", "torch_based"])
    spec.description = DESCRIPTION
    spec.tests = regs_tests()
    return spec


DESCRIPTION = (
    "CPU4 register file, compact: A and B master/slave, OUT, Z and C latches, every latch a repeater "
    "locked from the south by a repeater that reads a block; dust on that block climbs to a hold line at "
    "y=3 running along z (x=2 A masters, 6 both slaves, 10 B masters, 14 OUT, 18 flags). Lines come down "
    "to heads at row 38: hold = NOT cap OR NOT we (a wall torch on the cap row, cap dust on blocks at row 40, "
    "and one on the enable's block); the slave line holds while NOT com. Bit k owns rows 1+8k..8+8k: "
    "y_k in at (0,1,1+8k) -> A master (3) -> A slave (5) -> a; a_k out at (0,1,4+8k), b_k out at (0,1,6+8k) "
    "after B master (9) and B slave (7) on row 6+8k; OUT latch (13,1,1+8k), out_k pins on the north face "
    "at x=16+2k. zo in (0,1,33), co in (0,1,35); south face (z=45): wa 4, com 8, cap 10, wb 12, wo 16, wf 20 "
    "in, c 22, z 24 out. B and OUT take a (A's slave), so SWAP is race-free.")


if __name__ == "__main__":
    from pathlib import Path
    from redstone.fileformat import dump
    Path("library/cpu_parts/cpu_regs_compact.redstone.yaml").write_text(dump(cpu_regs_compact()))
