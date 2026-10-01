"""CPU4 control decoder: op0..3, z, c to the control lines, and imm0..3 = n AND xsel."""

import redstone.pla as pla_mod
from redstone.fileformat import Spec
from redstone.pla import minimise, pla

OPS = ["op0", "op1", "op2", "op3"]
OP_SETS = {"za": {1, 9}, "sub": {3, 14}, "wa": {1, 2, 3, 4, 5, 6, 7, 9, 14}, "wb": {8, 9},
           "wf": {2, 3, 4, 5, 6, 7, 14}, "wo": {10}, "hlt": {15}, "xsel": {1, 7, 14}}
CONTROL = list(OP_SETS) + ["jt"]
# Output rows north to south. cpu_fib4 mirrors the decoder, so these leave its west face in
# the order its buses turn south (jt and hlt north); xsel last, for the imm gates south of it.
ROW_ORDER = ["jt", "hlt", "wf", "wo", "wa", "wb", "za", "sub", "xsel"]
IMM_PITCH = 4
TORCH, REPEATER = 2, 2
# Measured on sat3: z -> jt 18 gt, c -> jt 22 gt (the jt output row is ~40 cells with refresh repeaters).
FLAG_WAIT = 24


def jt(op: int, z: int, c: int) -> int:
    return int(op == 11 or (op == 12 and z) or (op == 13 and c))


def control(op: int, z: int, c: int) -> dict[str, int]:
    out = {o: int(op in s) for o, s in OP_SETS.items()}
    out["jt"] = jt(op, z, c)
    return out


def gray(n: int) -> list[int]:
    return [i ^ (i >> 1) for i in range(1 << n)]


def _imm_gates(b, row_z: int, row_x: list[int]):
    """NOT xsel from a branch of the xsel row, then per bit a block powered by NOT n (torch)
    and by NOT xsel (repeater); the torch on it is imm. Pins on the south face."""
    xb = max(row_x) + 1
    zx = row_z
    b.place((xb, 1, zx + 1), "redstone_wire").place((xb, 1, zx + 2), "white_concrete")
    b.place((xb, 1, zx + 3), "redstone_wall_torch[facing=south]")
    zb = zx + 6
    xs = [xb - 2 - IMM_PITCH * i for i in range(4)]
    for x in range(xs[-1], xb + 1):
        b.place((x, 1, zx + 4), "redstone_wire")
    inputs, outputs = {}, {}
    for i, x in enumerate(xs):
        b.place((x, 1, zb - 1), "repeater[facing=north]").place((x, 1, zb), "white_concrete")
        b.place((x, 1, zb + 1), "redstone_wall_torch[facing=south]")
        for z in range(zb + 2, zb + 5):
            b.place((x, 1, z), "redstone_wire")
        b.place((x, 1, zb + 5), "repeater[facing=north]").place((x, 1, zb + 6), "redstone_wire")
        outputs[f"imm{i}"] = (x, 1, zb + 6)
        n = x + 2
        b.place((n, 1, zb + 5), "repeater[facing=south]").place((n, 1, zb + 4), "white_concrete")
        b.place((n, 1, zb + 3), "redstone_wall_torch[facing=north]")
        for z in range(zb, zb + 3):
            b.place((n, 1, z), "redstone_wire")
        b.place((x + 1, 1, zb), "redstone_wire")
        inputs[f"n{i}"] = (n, 1, zb + 6)
    return inputs, outputs


def cpu_ctrl(name: str = "cpu_ctrl", drop_jt_term: bool = False) -> Spec:
    outs = {o: minimise(OPS, s, set()) for o, s in OP_SETS.items()}
    jt_on = {v for v in range(64) if jt(v & 15, v >> 4 & 1, v >> 5 & 1)}
    outs["jt"] = minimise(OPS + ["z", "c"], jt_on, set())
    if drop_jt_term:
        outs["jt"] = [t for t in outs["jt"] if "c" not in t]
    outs = {o: outs[o] for o in ROW_ORDER}
    # xsel is the southmost output row, so the imm gates can sit just south of it.
    spacing = pla_mod.OUT_SPACING
    pla_mod.OUT_SPACING = 2
    try:
        spec = pla(name, OPS + ["z", "c"], outs)
    finally:
        pla_mod.OUT_SPACING = spacing
    b = spec.build
    pla_bound = spec.tests[0]["max_delay"]
    xz = spec.outputs["xsel"][2]
    row_x = [x for (x, y, z), s in b.blocks.items() if y == 1 and z == xz and "repeater" in s]
    taps = [x for (x, y, z), s in b.blocks.items() if y == 2 and z == xz and "torch" in s]
    n_in, imm_out = _imm_gates(b, xz, row_x + taps)
    b.with_base()
    spec.inputs.update(n_in)
    spec.outputs.update(imm_out)
    spec.named = dict(spec.outputs)
    imm_bound = pla_bound + TORCH + REPEATER + TORCH + REPEATER
    outs_all = CONTROL + [f"imm{i}" for i in range(4)]
    ins = OPS + ["z", "c"] + [f"n{i}" for i in range(4)]
    head = " ".join(ins) + " | " + " ".join(outs_all)

    def row(op, z, c, n):
        exp = control(op, z, c)
        exp.update({f"imm{i}": exp["xsel"] & (n >> i & 1) for i in range(4)})
        bits = [op >> i & 1 for i in range(4)] + [z, c] + [n >> i & 1 for i in range(4)]
        return " ".join(map(str, bits)) + " | " + " ".join(str(exp[o]) for o in outs_all)

    zc = [(0, 0), (0, 1), (1, 1), (1, 0)]
    lines = [head]
    for k, op in enumerate(gray(4)):
        for z, c in (zc if k % 2 == 0 else zc[::-1]):
            lines.append(row(op, z, c, 15))
    imm_lines = [head] + [row(op, 0, 0, n) for op in (1, 2) for n in gray(4)]
    spec.tests = [
        {"name": "control", "truth_table": "\n".join(lines) + "\n", "max_delay": imm_bound},
        {"name": "imm", "truth_table": "\n".join(imm_lines) + "\n", "max_delay": imm_bound},
        {"name": "flags", "settle": 60, "steps": [
            {"drive": {"op2": 1, "op3": 1}}, {"wait": 60}, {"expect": {"jt": 0}},
            {"drive": {"z": 1}}, {"wait": FLAG_WAIT}, {"expect": {"jt": 1}},
            {"drive": {"z": 0}}, {"wait": FLAG_WAIT}, {"expect": {"jt": 0}},
            {"drive": {"op0": 1, "c": 1}}, {"wait": 60}, {"expect": {"jt": 1}},
            {"drive": {"c": 0}}, {"wait": FLAG_WAIT}, {"expect": {"jt": 0}},
            {"drive": {"c": 1}}, {"wait": FLAG_WAIT}, {"expect": {"jt": 1}},
            {"drive": {"z": 1}}, {"wait": FLAG_WAIT}, {"expect": {"jt": 1}}]},
    ]
    spec.description = (
        "CPU4 control decoder. A two-plane torch PLA from op0..3, z and c to za, sub, wa, wb, wf, wo, hlt, "
        "xsel and jt = B or (C and z) or (D and c); then imm0..3 = n0..3 AND xsel, each a torch on a block "
        "fed NOT n (torch) and NOT xsel (inverter on a branch of the xsel row, through a repeater). "
        f"Op, z and c pins on the north face at y=3; control outputs on the east face; n pins and imm "
        f"outputs on the south face. Computed bounds: {pla_bound} gt to the PLA outputs, {imm_bound} gt to imm.")
    return spec
