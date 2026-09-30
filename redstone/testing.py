import itertools
from collections.abc import Callable

from .harness import Rig
from .parts import Part

# Well under the torch burnout rate of 8 toggles per 60 ticks, even for a torch that
# toggles on every row.
SETTLE = 20
HOLD = 10


def check_truth_table(
    rig: Rig, part: Part, fn: Callable[..., dict[str, bool]], settle: int = SETTLE
) -> int:
    """Drive every input combination and check the outputs. Returns the measured
    worst-case delay: ticks from the input change until the outputs are all correct."""
    rig.load(part.build)
    rig.step(settle)
    names = sorted(part.inputs)
    worst = 0
    rows = list(itertools.product([False, True], repeat=len(names)))
    for row in rows + [rows[0]]:  # end with all-off to check the part resets
        values = dict(zip(names, row))
        expected = fn(**values)
        for name, on in values.items():
            rig.drive(part.inputs[name], on)

        def matches() -> bool:
            return all(rig.powered(part.outputs[o]) == v for o, v in expected.items())

        ticks = 0
        while not matches():
            if ticks >= settle:
                raise AssertionError(
                    f"inputs {values}: outputs never matched {expected} within {settle} ticks\n{rig.dump()}"
                )
            rig.step(1)
            ticks += 1
        worst = max(worst, ticks)
        rig.step(settle - ticks + HOLD)
        if not matches():
            raise AssertionError(f"inputs {values}: outputs changed after settling\n{rig.dump()}")
    return worst
