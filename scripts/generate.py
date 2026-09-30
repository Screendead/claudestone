"""Regenerate library/*.redstone.yaml files that come from generators."""

from pathlib import Path

from redstone.fileformat import dump, load
from redstone.pla import pla
from redstone.route import Circuit

LIBRARY = Path(__file__).resolve().parent.parent / "library"


def generated():
    yield from generated_plas()
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
    yield (Circuit("ripple_adder_2bit").add("F0", fa, (0, 0, 1)).add("F1", fa, (0, 0, 26))
           .connect("F0.carry", "F1.c")
           .build("Two generated full adders with the carry routed from the first to the second.", ripple))


if __name__ == "__main__":
    for spec in generated():
        (LIBRARY / f"{spec.name}.redstone.yaml").write_text(dump(spec))
        print("wrote", spec.name)
