"""Tested building blocks.

Conventions: signal flows east (+x). Components sit in layer y=1 on a base at y=0.
Each input is a repeater facing into the part, driven from the cell west of it (the
driver position recorded in `inputs`), so parts never back-feed their sources. Each
output is a dust cell. `delay` is the worst-case input-to-output latency in game
ticks, as measured by the truth-table test.
"""

from dataclasses import dataclass, field

from .build import Build, Pos

SOLID = "white_concrete"


@dataclass
class Part:
    build: Build
    inputs: dict[str, Pos]
    outputs: dict[str, Pos]
    delay: int
    notes: str = field(default="")

    def at(self, offset: Pos) -> "Part":
        def move(p: Pos) -> Pos:
            return tuple(a + b for a, b in zip(p, offset))

        return Part(
            self.build.shifted(offset),
            {k: move(v) for k, v in self.inputs.items()},
            {k: move(v) for k, v in self.outputs.items()},
            self.delay,
            self.notes,
        )


def _input(b: Build, z: int) -> Pos:
    b.place((0, 1, z), "repeater[facing=west]")
    return (-1, 1, z)


def not_gate() -> Part:
    b = Build()
    a = _input(b, 0)
    b.place((1, 1, 0), SOLID).place((2, 1, 0), "redstone_wall_torch[facing=east]")
    b.place((3, 1, 0), "redstone_wire")
    return Part(b.with_base(), {"a": a}, {"out": (3, 1, 0)}, delay=4)


def or_gate() -> Part:
    b = Build()
    a, c = _input(b, 0), _input(b, 2)
    for z in range(3):
        b.place((1, 1, z), "redstone_wire")
    b.place((2, 1, 1), "redstone_wire").place((3, 1, 1), "redstone_wire")
    return Part(b.with_base(), {"a": a, "b": c}, {"out": (3, 1, 1)}, delay=2)


def and_gate() -> Part:
    """Both inputs inverted by torches, the inversions merged, then inverted again."""
    b = Build()
    a, c = _input(b, 0), _input(b, 2)
    for z in (0, 2):
        b.place((1, 1, z), SOLID).place((2, 1, z), "redstone_wall_torch[facing=east]")
    for z in range(3):
        b.place((3, 1, z), "redstone_wire")
    b.place((4, 1, 1), "redstone_wire").place((5, 1, 1), SOLID)
    b.place((6, 1, 1), "redstone_wall_torch[facing=east]").place((7, 1, 1), "redstone_wire")
    return Part(b.with_base(), {"a": a, "b": c}, {"out": (7, 1, 1)}, delay=6)


def bridge_z(b: Build, x: int, z: int) -> None:
    """Carry a southbound dust line over an east-west dust line at (x, 1, z).

    Occupies z-1..z+1 in column x; the caller supplies dust at (x, 1, z-2) and
    (x, 1, z+2). The block over the crossed line only receives weak power, which
    dust does not pick up, so the two signals stay separate.
    """
    b.place((x, 1, z - 1), SOLID).place((x, 2, z - 1), "redstone_wire")
    b.place((x, 2, z), SOLID).place((x, 3, z), "redstone_wire")
    b.place((x, 1, z + 1), SOLID).place((x, 2, z + 1), "redstone_wire")


def xor_gate() -> Part:
    """(A and not B) or (B and not A), each half a subtract-mode comparator.

    Feeding each input to one comparator's rear and the other's side can't be laid
    out flat with both inputs and the output on the edge, so the A branch bridges
    over the B line.
    """
    b = Build()
    a, c = _input(b, 0), _input(b, 2)
    for x in (1, 2, 3):
        b.place((x, 1, 0), "redstone_wire")
    b.place((4, 1, 0), "comparator[facing=west,mode=subtract]")  # A - B
    for x in (1, 2, 3, 4, 5):
        b.place((x, 1, 2), "redstone_wire")
    b.place((4, 1, 1), "repeater[facing=south]")  # B into the A comparator's side
    b.place((6, 1, 2), "comparator[facing=west,mode=subtract]")  # B - A
    bridge_z(b, 2, 2)
    for x in (2, 3, 4, 5, 6):
        b.place((x, 1, 4), "redstone_wire")
    b.place((6, 1, 3), "repeater[facing=south]")  # A into the B comparator's side
    for pos in ((5, 1, 0), (6, 1, 0), (7, 1, 0), (7, 1, 1), (7, 1, 2), (8, 1, 1)):
        b.place(pos, "redstone_wire")
    return Part(b.with_base(), {"a": a, "b": c}, {"out": (8, 1, 1)}, delay=6)
