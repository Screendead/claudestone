import pytest

from redstone import parts
from redstone.testing import check_truth_table

AT = (2, 0, 2)  # leaves room west of the part for the input drivers

CASES = {
    "not": (parts.not_gate, lambda a: {"out": not a}),
    "or": (parts.or_gate, lambda a, b: {"out": a or b}),
    "and": (parts.and_gate, lambda a, b: {"out": a and b}),
    "xor": (parts.xor_gate, lambda a, b: {"out": a != b}),
}


@pytest.mark.parametrize("name", CASES)
def test_gate(rig, name):
    make, fn = CASES[name]
    part = make().at(AT)
    assert check_truth_table(rig, part, fn) == part.delay
