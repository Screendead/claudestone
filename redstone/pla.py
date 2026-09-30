"""Programmable logic array: any sum-of-products function as a regular grid.

Two NOR planes. Input lines run south along z as dust at y=3 on blocks at y=2. Term rows
run east along x as dust at y=1, passing under the input lines, which only weakly power
their blocks, and dust ignores weak power. A tap is a wall torch on an input line's
block, hanging over the row: it lights the row whenever that input is off. So row t is
NOT(term t). Each row then climbs to y=3 and turns south as a column of the second
plane, whose taps light an output row whenever the column is off, i.e. whenever the
term is true. Output rows are therefore OR of their terms.

Complemented inputs get their own line, fed by a torch from the true line's head.
"""

import itertools
from collections.abc import Callable

from .build import Build, Pos
from .fileformat import Spec

SOLID = "white_concrete"
WIRE = "redstone_wire"
TORCH_TICKS = 2
REPEATER_TICKS = 2  # delay=1
FIRST_ROW = 5  # z rows 0-4 hold input drivers, head repeaters and complement heads
REFRESH_AT = 4  # place a repeater once the signal has decayed to this strength

Literal = tuple[str, bool]
Term = frozenset[Literal]


def _lay(b: Build, path: list[tuple[Pos, str | None]]) -> int:
    """Lay dust along path, swapping in repeaters where the signal would run out.

    Each entry is (position, repeater state allowed there or None). The first cell
    receives full strength. Returns the number of repeaters placed.
    """
    strength = 15
    repeaters = 0
    for i, (pos, repeater) in enumerate(path):
        if i and repeater and strength <= REFRESH_AT:
            b.place(pos, repeater)
            repeaters += 1
            strength = 16
        else:
            if i:
                strength -= 1
            if strength <= 0:
                raise ValueError(f"signal dies at {pos}: no repeater slot in reach")
            b.place(pos, WIRE)
        x, y, z = pos
        if y > 1:
            b.place((x, y - 1, z), SOLID)
    return repeaters


def pla(name: str, inputs: list[str], outputs: dict[str, list[dict[str, bool]]], description: str = "") -> Spec:
    terms: list[Term] = []
    for sop in outputs.values():
        for term in sop:
            key = frozenset(term.items())
            if key not in terms:
                terms.append(key)
    b = Build()
    spec_inputs: dict[str, Pos] = {}

    col_x: dict[Literal, int] = {}
    for i, v in enumerate(inputs):
        x = 1 + 4 * i
        col_x[(v, True)] = x
        spec_inputs[v] = (x, 3, 0)
        b.place((x, 2, 1), SOLID).place((x, 3, 1), "repeater[facing=north]")
        if any((v, False) in t for t in terms):
            col_x[(v, False)] = x + 2
            b.place((x + 1, 2, 2), SOLID).place((x + 1, 3, 2), WIRE)
            b.place((x + 2, 3, 2), SOLID).place((x + 2, 3, 3), "redstone_wall_torch[facing=south]")

    row_z = [FIRST_ROW + 2 * t for t in range(len(terms))]
    col_repeaters: dict[Literal, int] = {}
    for lit, x in col_x.items():
        tapped = {row_z[t] for t, term in enumerate(terms) if lit in term}
        start = 2 if lit[1] else 4
        end = max(tapped, default=start)
        path = [((x, 3, z), None if z in tapped or z == 2 else "repeater[facing=north]")
                for z in range(start, end + 1)]
        col_repeaters[lit] = _lay(b, path)
        for z in tapped:
            b.place((x + 1, 2, z), "redstone_wall_torch[facing=east]")

    plane2_x = max(col_x.values()) + 4
    term_x = [plane2_x + 3 * t for t in range(len(terms))]
    out_z = {name: row_z[-1] + 2 + 2 * k for k, name in enumerate(outputs)}
    end_x = term_x[-1] + 2

    term_repeaters = []
    for t, term in enumerate(terms):
        z, xt = row_z[t], term_x[t]
        taps = {col_x[lit] + 1 for lit in term}
        used_by = {out_z[o] for o, sop in outputs.items() if term in {frozenset(s.items()) for s in sop}}
        path = [((x, 1, z), None if x in taps or x >= xt - 2 else "repeater[facing=west]")
                for x in range(min(taps), xt - 1)]
        path += [((xt - 1, 2, z), None), ((xt, 3, z), None)]
        path += [((xt, 3, zz), None if zz in used_by else "repeater[facing=north]")
                 for zz in range(z + 1, max(used_by) + 1)]
        term_repeaters.append(_lay(b, path))
        for zz in used_by:
            b.place((xt + 1, 2, zz), "redstone_wall_torch[facing=east]")

    spec_outputs: dict[str, Pos] = {}
    bound = 0
    for o, sop in outputs.items():
        z = out_z[o]
        ts = [terms.index(frozenset(s.items())) for s in sop]
        taps = {term_x[t] + 1 for t in ts}
        path = [((x, 1, z), None if x in taps or x == end_x else "repeater[facing=west]")
                for x in range(min(taps), end_x + 1)]
        out_rep = _lay(b, path)
        spec_outputs[o] = (end_x, 1, z)
        for t in ts:
            for lit in terms[t]:
                head = REPEATER_TICKS + (0 if lit[1] else TORCH_TICKS)
                ticks = head + REPEATER_TICKS * (col_repeaters[lit] + term_repeaters[t] + out_rep) + 2 * TORCH_TICKS
                bound = max(bound, ticks)

    b.with_base()
    fn = _evaluator(inputs, outputs)
    header = " ".join(inputs) + " | " + " ".join(outputs)
    lines = [header]
    for row in itertools.product([0, 1], repeat=len(inputs)):
        got = fn(dict(zip(inputs, map(bool, row))))
        lines.append(" ".join(map(str, row)) + " | " + " ".join(str(int(got[o])) for o in outputs))
    test = {"name": "logic", "truth_table": "\n".join(lines) + "\n", "max_delay": bound}
    return Spec(name, b, inputs=spec_inputs, outputs=spec_outputs, named=dict(spec_outputs),
                tests=[test], description=description)


def _evaluator(inputs, outputs) -> Callable[[dict[str, bool]], dict[str, bool]]:
    def fn(values):
        return {o: any(all(values[v] == pol for v, pol in term.items()) for term in sop)
                for o, sop in outputs.items()}
    return fn
