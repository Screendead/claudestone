"""Regenerate library/*.redstone.yaml files that come from generators."""

from pathlib import Path

from redstone.fileformat import dump, load
from redstone.devices import DIGITS, seven_segment, switch
from redstone.pla import or_plane, pla
from redstone.route import Circuit

LIBRARY = Path(__file__).resolve().parent.parent / "library"


def generated():
    yield from generated_plas()
    yield from generated_stages()
    yield from generated_devices()
    yield from generated_circuits()


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

    not_gate = load(LIBRARY / "not_gate.redstone.yaml")
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
    lib = {p.stem.removesuffix(".redstone"): p for p in LIBRARY.glob("*.redstone.yaml")}
    part = {n: load(lib[n]) for n in ("lever_switch", "button_switch", "encoder", "half_adder",
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


if __name__ == "__main__":
    for spec in generated():
        (LIBRARY / f"{spec.name}.redstone.yaml").write_text(dump(spec))
        print("wrote", spec.name)
