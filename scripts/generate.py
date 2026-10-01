"""Regenerate library/**/*.redstone.yaml files that come from generators."""

from redstone.build import Build
from redstone.fileformat import Spec, dump, load
from redstone.library import LIBRARY, SUFFIX, path_of
from redstone.devices import DIGITS, seven_segment, switch
from redstone.out_display import out_display
from redstone.pla import or_plane, pla
from redstone.route import Circuit

# Building-block folder for each generated spec; the rest are whole builds.
# ripple_adder_2bit spans 49 cells in z, more than a family plot's 48, so it is a build.
FOLDER = {"pla_xor": "xor", "full_adder": "full_adder",
          "encoder": "encoder", "half_adder": "half_adder", "digit": "seven_segment",
          "digit_one": "seven_segment", "lever_switch": "input", "button_switch": "input",
          "cpu_out_display": "cpu_parts", "cpu_rom_ctrl": "cpu_parts", "cpu_rom_ctrl_jumps": "cpu_parts", "cpu_alu": "cpu_parts",
          "cpu_ctrl": "cpu_parts", "cpu_regs": "cpu_parts", "cpu_fetch": "cpu"}


def destination(name: str):
    return LIBRARY / FOLDER.get(name, "builds") / f"{name}{SUFFIX}"


def generated():
    yield from generated_plas()
    yield from generated_stages()
    yield from generated_devices()
    yield from generated_circuits()
    yield from generated_cpu()
    yield out_display()


def generated_plas():
    yield pla("pla_xor", ["a", "b"], {"out": [{"a": True, "b": False}, {"a": False, "b": True}]},
              "XOR from the generic sum-of-products generator; must agree with xor_gate.")
    odd = [dict(zip("abc", bits)) for bits in
           [(True, False, False), (False, True, False), (False, False, True), (True, True, True)]]
    yield pla("full_adder", ["a", "b", "c"], {
        "sum": odd,
        "carry": [{"a": True, "b": True}, {"a": True, "c": True}, {"b": True, "c": True}],
    }, "One-bit full adder (c = carry in) from the sum-of-products generator.")


SUM_BITS = ["s0", "s1", "s2", "s3", "s4"]


def minterm(value: int) -> dict[str, bool]:
    return {v: bool(value >> i & 1) for i, v in enumerate(SUM_BITS)}


def generated_stages():
    """The stages of the two-digit adder."""
    # Inputs listed 9..0: the viewer faces south, so lever 0 (on their left) has the largest x.
    yield or_plane("encoder", [f"d{i}" for i in range(9, -1, -1)],
                   {f"bit{k}": [f"d{i}" for i in range(10) if i >> k & 1] for k in range(4)},
                   "One lever per digit 0-9 to a 4-bit number. Tested with one lever on at a time.",
                   one_hot=True)
    yield pla("half_adder", ["a", "b"], {"sum": [{"a": True, "b": False}, {"a": False, "b": True}],
                                         "carry": [{"a": True, "b": True}]}, "One-bit half adder.")
    outputs = {seg: [minterm(v) for v in range(19) if seg in DIGITS[v % 10]] for seg in "abcdefg"}
    outputs["tens"] = [minterm(v) for v in range(10, 19)]
    yield pla("decoder", SUM_BITS, outputs,
              "A sum 0-18 (s0 = least significant bit) to units-digit segments a-g and a tens flag.")


def generated_devices():
    yield seven_segment("digit")
    yield seven_segment("digit_one", "bc")
    yield switch("lever_switch", "lever")
    yield switch("button_switch", "stone_button")


def generated_circuits():

    not_gate = load(path_of("not_gate"))
    yield (Circuit("route_chain").add("A", not_gate, (0, 0, 2)).add("B", not_gate, (12, 0, 8))
           .connect("A.out", "B.a")
           .build("Two NOT gates joined by a routed wire.", lambda v: {"B.out": v["A.a"]}))
    yield (Circuit("route_cross")
           .add("A", not_gate, (0, 0, 2)).add("B", not_gate, (0, 0, 8))
           .add("C", not_gate, (16, 0, 8)).add("D", not_gate, (16, 0, 2)).add("E", not_gate, (16, 0, 14))
           .connect("A.out", "C.a", "E.a").connect("B.out", "D.a")
           .build("Two routed wires that must swap sides, one of them fanning out to two sinks.",
                  lambda v: {"C.out": v["A.a"], "D.out": v["B.a"], "E.out": v["A.a"]}))
    fa = next(s for s in generated_plas() if s.name == "full_adder")

    def ripple(v):
        a0, b0, c0, a1, b1 = (v[k] for k in ("F0.a", "F0.b", "F0.c", "F1.a", "F1.b"))
        c1 = (a0 + b0 + c0) >= 2
        return {"F0.sum": a0 ^ b0 ^ c0, "F1.sum": a1 ^ b1 ^ c1, "F1.carry": (a1 + b1 + c1) >= 2}
    yield two_digit_adder()
    yield (Circuit("ripple_adder_2bit").add("F0", fa, (0, 0, 1)).add("F1", fa, (0, 0, 26))
           .connect("F0.carry", "F1.c")
           .build("Two generated full adders with the carry routed from the first to the second.", ripple))


def two_digit_adder():
    part = {n: load(path_of(n)) for n in ("lever_switch", "button_switch", "encoder", "half_adder",
                                      "full_adder", "latch", "decoder", "digit", "digit_one")}
    c = Circuit("two_digit_adder", size=(192, 24, 192))
    # The player stands at the north edge facing south, so their left is +x.
    for g, x0 in (("A", 62), ("B", 40)):
        for i in range(10):
            c.add(f"{g}{i}", part["lever_switch"], (x0 + 2 * (9 - i), 0, 0))
        c.add(f"enc{g}", part["encoder"], (x0 - 1, 0, 10))
        for i in range(10):
            c.connect(f"{g}{i}.out", f"enc{g}.d{i}")
    c.add("button", part["button_switch"], (34, 0, 0))
    c.add("tens", part["digit_one"], (26, 0, 2)).add("units", part["digit"], (18, 0, 2))
    c.add("add0", part["half_adder"], (0, 0, 34))
    for k in (1, 2, 3):
        c.add(f"add{k}", part["full_adder"], (30 + 42 * (k - 1), 0, 34))
    for k in range(5):
        c.add(f"latch{k}", part["latch"], (10 + 14 * k, 0, 66))
    c.add("decoder", part["decoder"], (0, 0, 84))

    c.connect("encA.bit0", "add0.a").connect("encB.bit0", "add0.b")
    for k in (1, 2, 3):
        c.connect(f"encA.bit{k}", f"add{k}.a").connect(f"encB.bit{k}", f"add{k}.b")
        c.connect(f"add{k - 1}.carry", f"add{k}.c")
    sums = ["add0.sum", "add1.sum", "add2.sum", "add3.sum", "add3.carry"]
    for k, src in enumerate(sums):
        c.connect(src, f"latch{k}.d").connect(f"latch{k}.q", f"decoder.s{k}")
    c.connect("button.out", *[f"latch{k}.e" for k in range(5)])
    for seg in "abcdefg":
        c.connect(f"decoder.{seg}", f"units.{seg}")
    c.connect("decoder.tens", "tens.b", "tens.c")
    spec = c.build("Flick one lever 0-9 in each row, press the button, and the two-digit sum shows on the "
                   "seven-segment display.")
    # One pair per sum 0-18, which between them flick every lever.
    spec.tests = [adder_test(spec, [((t + 1) // 2, t // 2) for t in range(19)])]
    spec.tests[0]["name"] = "every sum"
    return spec


def display_expect(total: int, spec) -> dict:
    units = DIGITS[total % 10]
    want = {}
    for name in spec.named:
        digit, _, cell = name.partition(".")
        if digit == "units":
            want[name] = int(cell[0] in units)
        elif digit == "tens":
            want[name] = int(total >= 10)
    return want


LEVER_SETTLE, DISPLAY_SETTLE = 160, 120


def adder_test(spec, pairs) -> dict:
    steps = [{"expect": display_expect(0, spec)}]
    for i, j in pairs:
        steps += [{"use": f"A{i}.switch"}, {"use": f"B{j}.switch"}, {"wait": LEVER_SETTLE},
                  {"use": "button.switch"}, {"wait": DISPLAY_SETTLE},
                  {"expect": display_expect(i + j, spec)},
                  {"use": f"A{i}.switch"}, {"use": f"B{j}.switch"}]
    return {"name": "", "settle": 300, "steps": steps}


ALU_PROGRAM = [0x1C, 0x80, 0x1A, 0x40, 0xA0, 0x1A, 0x50, 0xA0, 0x1A, 0x60, 0xA0, 0xE6, 0xCE, 0xF0, 0xA0, 0xF0]
JUMP_PROGRAM = [0xB5, 0xC6, 0xD7, 0xF0] + [0] * 12


def generated_cpu():
    from scripts.rom_ctrl import rom_ctrl
    yield rom_ctrl("cpu_rom_ctrl", ALU_PROGRAM)
    yield rom_ctrl("cpu_rom_ctrl_jumps", JUMP_PROGRAM)
    from scripts.alu import cpu_alu
    yield cpu_alu()
    from scripts.cpu_ctrl import cpu_ctrl
    yield cpu_ctrl()
    from scripts.cpu_regs import cpu_regs
    yield cpu_regs()
    yield cpu_fetch()


FIB_PROGRAM = [0x10, 0x80, 0x11, 0xA0, 0x90, 0x20, 0xD8, 0xB3, 0xF0] + [0] * 7
WIRE_SUPPORT = "white_concrete"
# Clock pin rise to sample: 18 gt to the first COM, ~14 on the bus, 10 in the PC, 32 in the
# ROM leave pimm settled ~75 gt after start; sampling 140 gt in keeps >= 60 gt either side.
FETCH_SAMPLE = 140
# A spec's palette has about 55 free glyphs, so only these cells are named.
FETCH_NAMED = ({f"pc.{c}{i}" for c in "sm" for i in range(4)} | {f"rom.{c}{i}" for c in ("pimm", "op") for i in range(4)}
               | {"clock.com_node", "clock.cap_node"})


def _wire(build, points, refresh=12):
    """Dust at y=1 along axis-aligned waypoints (x, z), starting with a repeater.

    The last point is the sink's pin cell and stays dust."""
    from redstone.route import FACING_FROM
    cells = [points[0]]
    for (x0, z0), (x1, z1) in zip(points, points[1:]):
        dx, dz = (x1 > x0) - (x1 < x0), (z1 > z0) - (z1 < z0)
        while cells[-1] != (x1, z1):
            cells.append((cells[-1][0] + dx, cells[-1][1] + dz))
    run = 0
    repeaters = 0
    for i, (x, z) in enumerate(cells):
        nxt = cells[i + 1] if i + 1 < len(cells) else None
        prv = cells[i - 1] if i else None
        assert build.blocks.get((x, 1, z), "minecraft:air") == "minecraft:air", (x, z)
        flow = (nxt[0] - x, nxt[1] - z) if nxt else None
        straight = prv and nxt and (x - prv[0], z - prv[1]) == flow
        if i == 0 or (straight and run >= refresh and i < len(cells) - 2):
            build.place((x, 1, z), f"repeater[facing={FACING_FROM[flow]},delay=1]")
            run, repeaters = 0, repeaters + 1
        else:
            build.place((x, 1, z), "redstone_wire")
            run += 1
        if (x, 0, z) not in build.blocks:
            build.place((x, 0, z), WIRE_SUPPORT)
    return repeaters


def cpu_fetch(words=FIB_PROGRAM, name="cpu_fetch") -> Spec:
    """Clock + PC + lever ROM of the CPU4 floor plan, with hand-laid straight buses."""
    from scripts.rom_ctrl import rom_ctrl
    parts = {"clock": (load(LIBRARY / "cpu_parts" / f"cpu_clock{SUFFIX}"), (44, 0, 94)),
             "pc": (load(LIBRARY / "cpu_parts" / f"cpu_pc{SUFFIX}"), (98, 0, 0)),
             "rom": (rom_ctrl("rom", words), (44, 0, 0))}
    build = Build()
    named, inputs = {}, {}
    for part, (spec, at) in parts.items():
        build.merge(spec.build, at)
        for cell, pos in spec.named.items():
            if f"{part}.{cell}" in FETCH_NAMED:
                named[f"{part}.{cell}"] = tuple(a + b for a, b in zip(pos, at))
        for pin, pos in spec.inputs.items():
            inputs[f"{part}.{pin}"] = tuple(a + b for a, b in zip(pos, at))
    for i, z in enumerate([4, 7, 10, 13]):
        _wire(build, [(97, z), (91, z)])
        del inputs[f"rom.pc{i}"]
    for i, z in enumerate([19, 22, 25, 28]):
        _wire(build, [(92, z), (98, z)])
        del inputs[f"pc.imm{i}"]
    reps = [_wire(build, [(84, 93), (84, 90), (104, 90), (104, 39)]),
            _wire(build, [(88, 93), (88, 92), (108, 92), (108, 39)])]
    assert reps[0] == reps[1], reps
    del inputs["pc.cap"], inputs["pc.com"]
    spec = Spec(name, build, inputs=inputs, named=named, description=(
        "CPU4 fetch loop: the two-phase clock drives the program counter, whose value "
        "addresses the 16x8 lever ROM (Fibonacci program); the ROM's n field goes back to "
        "the PC's jump input. jt, hlt and rst are driven by the test, since the control "
        "decoder, ALU and registers are not built yet."))
    spec.tests = [fetch_test(words)]
    return spec


def fetch_test(words) -> dict:
    def expect(pc):
        want = {f"pc.s{i}": pc >> i & 1 for i in range(4)}
        want |= {f"rom.pimm{i}": words[pc] >> i & 1 for i in range(4)}
        want |= {f"rom.op{i}": words[pc] >> (4 + i) & 1 for i in range(4)}
        return {"expect": want}
    steps = [{"drive": {"clock.start": 1}}, {"wait": 2}, {"drive": {"clock.start": 0}},
             {"wait": FETCH_SAMPLE - 2}]
    # pc 0..6 counting; at pc 6 (JC 8, n = 8) jt is held over one CAP, so pc 8 follows;
    # hlt over three CAPs keeps pc 8; then counting resumes.
    plan = [(pc, {}) for pc in range(6)] + [(6, {"pc.jt": 1}), (8, {"pc.jt": 0, "pc.hlt": 1}),
            (8, {}), (8, {}), (8, {"pc.hlt": 0}), (9, {}), (10, {})]
    for pc, drive in plan:
        steps.append(expect(pc))
        if drive:
            steps.append({"drive": drive})
        steps.append({"wait": 200})
    return {"name": "fetch", "settle": 40, "steps": steps}


if __name__ == "__main__":
    for spec in generated():
        destination(spec.name).write_text(dump(spec))
        print("wrote", spec.name)
