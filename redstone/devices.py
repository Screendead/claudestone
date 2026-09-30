"""Human-facing parts: seven-segment digits, levers and buttons."""

from .build import Build
from .fileformat import Spec

FRAME = "black_concrete"
LAMP = "redstone_lamp"

# Segment -> its three lamps (x, y) on a 5 x 9 face, middle lamp first. Rows are y up.
# The digit faces north, so the viewer looks south and sees +x on their LEFT: the
# right-hand segments b and c are at x = 0.
SEGMENTS = {
    "a": [(2, 9), (3, 9), (1, 9)],
    "b": [(0, 7), (0, 8), (0, 6)],
    "c": [(0, 3), (0, 4), (0, 2)],
    "d": [(2, 1), (3, 1), (1, 1)],
    "e": [(4, 3), (4, 4), (4, 2)],
    "f": [(4, 7), (4, 8), (4, 6)],
    "g": [(2, 5), (3, 5), (1, 5)],
}


def front_view(lit: set[tuple[int, int]]) -> str:
    """The 5 x 9 face as the viewer sees it: # for a lit lamp position."""
    return "\n".join("".join("#" if (x, y) in lit else "." for x in range(4, -1, -1))
                     for y in range(9, 0, -1))


DIGITS = {0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg",
          5: "acdfg", 6: "acdefg", 7: "abc", 8: "abcdefg", 9: "abcdfg"}


def seven_segment(name: str, segments: str = "abcdefg") -> Spec:
    """A digit facing north (-z). Each segment's middle lamp is hard-powered by a
    repeater from behind, and hard power in a lamp lights the lamps touching it; the
    frame blocks between segments keep that from spreading to the next segment. The
    feed repeaters are at least two apart vertically, so each has a block to stand on.
    """
    b = Build()
    lamps = {pos for s in segments for pos in SEGMENTS[s]}
    for x in range(5):
        for y in range(1, 10):
            if (x, y) not in lamps:
                b.place((x, y, 0), FRAME)
    spec = Spec(name, b, description=f"Seven-segment digit showing segments {segments}; input per segment.")
    for s in segments:
        for i, (x, y) in enumerate(SEGMENTS[s]):
            b.place((x, y, 0), LAMP)
            spec.named[f"{s}{i}"] = (x, y, 0)
        x, y = SEGMENTS[s][0]
        b.place((x, y, 1), "repeater[facing=south]").place((x, y - 1, 1), "white_concrete")
        spec.inputs[s] = (x, y, 2)
    lamp_names = sorted(spec.named)
    steps = []
    for s in segments:
        steps += [{"drive": {s: 1}}, {"wait": 8},
                  {"expect": {n: int(n[0] == s) for n in lamp_names}},
                  {"drive": {s: 0}}, {"wait": 8}]
    steps.append({"expect": {n: 0 for n in lamp_names}})
    spec.tests = [{"name": "each segment lights only itself", "steps": steps}]
    return spec


def switch(name: str, block: str) -> Spec:
    """A lever or button on the north face of a block, read by a repeater behind it.
    The player stands to the north; `out` is the dust cell south of the repeater."""
    b = Build()
    b.place((0, 1, 0), f"{block}[face=wall,facing=north,powered=false]")
    b.place((0, 1, 1), "white_concrete").place((0, 1, 2), "repeater[facing=north]")
    b.place((0, 1, 3), "redstone_wire").with_base()
    del b.blocks[(0, 0, 0)]
    spec = Spec(name, b, named={"switch": (0, 1, 0), "out": (0, 1, 3)}, outputs={"out": (0, 1, 3)})
    if "button" in block:
        spec.tests = [{"name": "press gives a pulse", "steps": [
            {"use": "switch"}, {"wait": 4}, {"expect": {"out": 1}}, {"wait": 20}, {"expect": {"out": 0}}]}]
    else:
        spec.tests = [{"name": "flick on and off", "steps": [
            {"use": "switch"}, {"wait": 4}, {"expect": {"out": 1}},
            {"use": "switch"}, {"wait": 4}, {"expect": {"out": 0}}]}]
    spec.description = f"A {block.replace('_', ' ')} for the player, with a wire out the back."
    return spec
