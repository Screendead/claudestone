"""Regenerate library/*.redstone.yaml files that come from generators."""

from pathlib import Path

from redstone.fileformat import dump
from redstone.pla import pla

LIBRARY = Path(__file__).resolve().parent.parent / "library"


def generated():
    yield pla("pla_xor", ["a", "b"], {"out": [{"a": True, "b": False}, {"a": False, "b": True}]},
              "XOR from the generic sum-of-products generator; must agree with xor_gate.")
    odd = [dict(zip("abc", bits)) for bits in
           [(True, False, False), (False, True, False), (False, False, True), (True, True, True)]]
    yield pla("full_adder", ["a", "b", "c"], {
        "sum": odd,
        "carry": [{"a": True, "b": True}, {"a": True, "c": True}, {"b": True, "c": True}],
    }, "One-bit full adder (c = carry in) from the sum-of-products generator.")


if __name__ == "__main__":
    for spec in generated():
        (LIBRARY / f"{spec.name}.redstone.yaml").write_text(dump(spec))
        print("wrote", spec.name)
