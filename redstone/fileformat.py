"""The `.redstone.yaml` format: a build, its named cells, and its tests, as data.

    name: and_gate
    description: Both inputs inverted by torches, merged, inverted again.
    traits: [compact, silent]    # optional, from redstone.traits.VOCABULARY; the
                                 # checkable ones are checked by tests/test_traits.py
    palette:                     # one character -> one cell
      ".": air
      "=": smooth_stone
      "-": redstone_wire
      ">": repeater[facing=west]
      a: {input: a}              # driver cell: air in the build, where the harness
                                 # places or removes a redstone block; several glyphs
                                 # with one input name are one signal driven at each cell
      F: {block: redstone_torch, fixture: true}   # placed and tested, but not part of
                                 # the design: left out of its size and trait checks
      _: {reserve: true}         # air that belongs to the design (piston travel):
                                 # counts in its size, and no block may fill it
      o: {output: out, block: redstone_wire}
      L: {name: lamp, block: redstone_lamp}   # a named cell tests can read or use
    layers:                      # keyed by y; row = z from north (top) to south,
      0: |                       # column = x from west (left) to east
        .=====
      1: |
        a>#t-o
    tests:
      - name: logic
        truth_table: |           # 1/0 per named cell (x: don't care, outputs only);
                                 # inputs left of |, checks right
          a b | out
          0 0 | 0
          1 1 | x
        delay: 6                 # optional: worst-case ticks from input change to output
        max_delay: 8             # optional: upper bound instead of an exact delay
        delays: {out: {rise: 6, fall: 2}}   # optional: exact worst case per output and edge
                                 # (a number: over both edges); max_delays: bounds
        glitch_free: true        # optional: an output may not leave its expected value
                                 # once matched, nor move at all if the row keeps it
        reset: false             # optional: don't end by replaying the first row
        initial: {a: 1}          # optional: drivers placed with the build, before its
                                 # update pass, so the input is high from placement
        tile: [1, 0, 0]          # optional: also build a second copy at this offset, fed
                                 # row i+1 while the first copy gets row i; both checked
      - name: pulse
        settle: 200              # optional: ticks to wait after loading (default 20)
        steps:                   # run in order
          - drive: {a: 1}        # set input drivers
          - use: lever           # click a named lever or button
          - wait: 6              # advance ticks
          - expect: {lamp: 1}    # 1 = the cell carries signal (see docs/AUTHORING.md)
          - level: {cmp: 7}      # exact 0-15 strength of dust, a comparator or an analog block
          - wave: {out: '0011', q: 'x1'}   # 1/0/x (don't care) per tick, from this tick:
                                 # character i is checked i ticks later; the step
                                 # advances max(len) ticks
          - repeat: {times: 3, steps: [{drive: {a: 1}}, {wait: 2}]}   # nests
          - run: fill ~0 ~1 ~0 ~0 ~1 ~0 hopper   # any command; ~ is the build origin;
                                 # fails if the command does
          - log: data get block ~0 ~1 ~0 Items   # like run; the reply goes in the trace
          - check: if block ~3 ~1 ~0 redstone_wire[power=7]   # execute if/unless chain
          - insert: {cell: feed, item: cobblestone, count: 10}   # into a container at a named
                                 # cell or [x, y, z]; items: [{id, count}, ...] fill slots from
                                 # slot (default 0) on; clear: true empties it first
          - expect_items: {cell: [7, 1, 8], item: cobblestone, min: 30}   # the total over its
                                 # slots, of item (default any) in slot (default all): count,
                                 # min and/or max, or empty: true
          - throughput: {from: feed, to: [7, 1, 8], item: cobblestone, ticks: 800, min: 90}
                                 # items that reach `to` (or leave `from`) in the next ticks;
                                 # the count and rate per hour go in the trace and the result
        finally:                 # commands run after the steps, even when a step failed
          - gamerule advance_time true

      - name: door
        door_cycle: {cycles: 2, max_open: 6, max_close: 6, reading: R, tier: FULL, max_volume: 108}
                                 # needs a door: section (below). Opens and closes the door
                                 # `cycles` times through its fixture repeater, probing the
                                 # hallway every tick; times under each reading (R, H1, R1),
                                 # visible times, seamless grades and the volume go in the
                                 # result and the trace. Optional bounds: max_open, max_close
                                 # (in the given reading, default R), max_open_visible,
                                 # max_close_visible, tier (default the door's), max_volume,
                                 # max_ticks (per operation, default 600), quiet (static
                                 # ticks that end an operation, default 40)

    update_pass: all             # optional: all (default), none (no clone-onto-itself pass),
                                 # unobserved (observers set last, and the blocks they
                                 # face not cloned, so placing doesn't pulse them) or
                                 # strict (every block set with `setblock ... strict`, no
                                 # updates at all, and no pass)

    door:                        # optional: a piston door, for door_cycle tests
      doorway: {origin: [5, 1, 1], width: 2, height: 2, facing: north}
                                 # origin is the min corner; facing is the front, the side
                                 # the player comes from (up/down for a trapdoor-like door)
      depth: 1                   # hallway cells checked on each side of the doorway
      blocks: closed             # door material: what the doorway holds as placed (the
                                 # build must then be placed closed), or a list of ids
      surface: [white_concrete]  # hallway composition (default: the door blocks)
      input: door_in             # the input whose drive cell feeds the fixture repeater
      repeater: rep              # a named fixture repeater[delay=1] with the drive cell
                                 # behind it; tick 0 is the tick its output changes
                                 # (or instead lever: <named lever>, flipped like a click;
                                 # tick 0 is then the first tick after the click)
      device: lever              # optional: the player's input device, left out of volume
      outer_surface: [[[0, 0, 0], [9, 3, 0]]]   # optional boxes of outer wall, not circuitry
      initial: closed            # the state as placed, with the input off (default closed)
      tier: FULL                 # optional: the seamless tier door_cycle checks

    entities:                    # optional, summoned after the blocks are placed
      - {type: minecart, pos: [2.0, 1.0, 0.0], nbt: '{Invulnerable:1b}'}
                                 # pos is relative to the centre of the origin cell
                                 # (the build runs under `execute positioned <int>`,
                                 # which centres x and z): [2.0, 1.0, 0.0] is the middle
                                 # of cell (2,1,0), and .5 on x or z is a cell edge

Block states in the palette may carry block-entity NBT, e.g.
`'hopper[facing=down]{Items:[{id:"minecraft:redstone",count:1}]}'`.

Cell origin is the top-left character of each layer. Every layer grid must have the
same width and height.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .build import Build, Pos, namespaced

# Preferred glyphs when writing a file; anything else gets the next free letter.
GLYPHS = {
    "minecraft:air": ".",
    "minecraft:smooth_stone": "=",
    "minecraft:white_concrete": "#",
    "minecraft:stone": "S",
    "minecraft:redstone_wire": "-",
    "minecraft:repeater[facing=west]": ">",
    "minecraft:repeater[facing=east]": "<",
    "minecraft:repeater[facing=north]": "v",
    "minecraft:repeater[facing=south]": "^",
    "minecraft:redstone_torch": "*",
    "minecraft:redstone_wall_torch[facing=east]": ")",
    "minecraft:redstone_wall_torch[facing=west]": "(",
    "minecraft:redstone_wall_torch[facing=south]": "u",
    "minecraft:redstone_wall_torch[facing=north]": "n",
    "minecraft:redstone_lamp": "L",
    "minecraft:redstone_block": "R",
}


_norm = namespaced


def _short(state: str) -> str:
    return state.removeprefix("minecraft:")


@dataclass
class Spec:
    name: str
    build: Build
    inputs: dict[str, Pos] = field(default_factory=dict)
    outputs: dict[str, Pos] = field(default_factory=dict)
    named: dict[str, Pos] = field(default_factory=dict)  # includes outputs
    tests: list[dict] = field(default_factory=list)
    description: str = ""
    path: Path | None = None
    traits: list[str] = field(default_factory=list)
    fixtures: set[Pos] = field(default_factory=set)
    reserved: set[Pos] = field(default_factory=set)
    # Every cell of an input with more than one; `inputs` holds each input's first cell.
    extra_inputs: dict[str, list[Pos]] = field(default_factory=dict)
    # The `door:` section as written; redstone.door.plan reads it.
    door: dict | None = None
    update_pass: str = "all"  # Build.to_commands

    def cell(self, name: str) -> Pos:
        if name in self.inputs:
            return self.inputs[name]
        return self.named[name]

    def input_cells(self, name: str) -> list[Pos]:
        return self.extra_inputs.get(name) or [self.inputs[name]]


def load(path: Path | str) -> Spec:
    path = Path(path)
    doc = yaml.safe_load(path.read_text())
    palette = {str(k): v for k, v in doc["palette"].items()}
    spec = Spec(doc["name"], Build(), description=doc.get("description", ""), tests=doc.get("tests", []), path=path,
                traits=doc.get("traits", []), door=doc.get("door"), update_pass=doc.get("update_pass", "all"))
    for e in doc.get("entities", []):
        spec.build.summon(tuple(e["pos"]), e["type"], e.get("nbt", ""))
    shape, cells = None, {}
    for y, grid in doc["layers"].items():
        rows = grid.rstrip("\n").split("\n")
        if shape is None:
            shape = (len(rows), len(rows[0]))
        if (len(rows), max(map(len, rows))) != shape or len(set(map(len, rows))) != 1:
            raise ValueError(f"{path}: layer {y} is not {shape[0]} rows of {shape[1]}")
        for z, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch not in palette:
                    raise ValueError(f"{path}: layer {y} row {z} col {x}: {ch!r} not in palette")
                entry = palette[ch]
                pos = (x, int(y), z)
                if isinstance(entry, str):
                    if _norm(entry) != "minecraft:air":
                        spec.build.place(pos, entry)
                    continue
                if "input" in entry:
                    cells.setdefault(entry["input"], []).append(pos)
                    continue
                if entry.get("reserve"):
                    spec.reserved.add(pos)
                    continue
                spec.build.place(pos, entry["block"])
                if entry.get("fixture"):
                    spec.fixtures.add(pos)
                name = entry.get("output") or entry.get("name")
                if name is None:
                    continue
                spec.named[name] = pos
                if "output" in entry:
                    spec.outputs[name] = pos
    spec.inputs = {n: ps[0] for n, ps in cells.items()}
    spec.extra_inputs = {n: ps for n, ps in cells.items() if len(ps) > 1}
    return spec


def dump(spec: Spec) -> str:
    """Serialise a spec, choosing glyphs automatically. Round-trips through load()."""
    cells: dict[Pos, str] = dict(spec.build.blocks)
    labels: dict[Pos, dict] = {}
    for name in spec.inputs:
        for pos in spec.input_cells(name):
            labels[pos] = {"input": name}
    for pos in spec.fixtures:
        labels[pos] = {"block": _short(cells[pos]), "fixture": True}
    for name, pos in spec.named.items():
        key = "output" if name in spec.outputs else "name"
        labels[pos] = {key: name, "block": _short(cells[pos])} | ({"fixture": True} if pos in spec.fixtures else {})
    for pos in spec.reserved:
        labels[pos] = {"reserve": True}
    everything = list(cells) + list(labels)
    xs, ys, zs = zip(*everything)
    lo_x, lo_z = min(0, min(xs)), min(0, min(zs))
    if lo_x < 0 or lo_z < 0:
        raise ValueError("spec cells must have non-negative x and z")
    width, depth = max(xs) + 1, max(zs) + 1

    palette: dict[str, object] = {".": "air"}
    by_state: dict[str, str] = {"minecraft:air": "."}
    # Greek letters only once the ASCII glyphs run out, so existing files dump unchanged.
    spare = [c for c in "ABCDEFGHIJKMNOPQSTUVWXYZbcdefghijklmpqrstwxyz0123456789"
             "αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΦΨΩ" if c not in GLYPHS.values()]

    def next_free() -> str:
        return next(c for c in spare if c not in palette)

    def glyph_for_state(state: str) -> str:
        if state not in by_state:
            g = GLYPHS.get(state) or next_free()
            by_state[state] = g
            palette[g] = _short(state)
        return by_state[state]

    by_label: dict[str, str] = {}

    def glyph_for_label(label: dict) -> str:
        key = repr(sorted(label.items()))
        if key not in by_label:
            name = label.get("input") or label.get("output") or label.get("name") or ("_" if "reserve" in label else "")
            g = name[0] if name and name[0] not in palette and name[0] not in GLYPHS.values() else next_free()
            by_label[key] = g
            palette[g] = label
        return by_label[key]

    layers = {}
    for y in sorted(set(ys)):
        rows = []
        for z in range(depth):
            row = ""
            for x in range(width):
                pos = (x, y, z)
                if pos in labels:
                    row += glyph_for_label(labels[pos])
                else:
                    row += glyph_for_state(cells.get(pos, "minecraft:air"))
            rows.append(row)
        layers[y] = "\n".join(rows) + "\n"

    doc = {"name": spec.name}
    if spec.description:
        doc["description"] = spec.description
    if spec.traits:
        doc["traits"] = spec.traits
    if spec.update_pass != "all":
        doc["update_pass"] = spec.update_pass
    doc["palette"] = palette
    doc["layers"] = layers
    if spec.build.entities:
        doc["entities"] = [{"type": _short(e), "pos": list(p), **({"nbt": n} if n else {})}
                           for p, e, n in spec.build.entities]
    if spec.door is not None:
        doc["door"] = _flow_lists(spec.door)
    if spec.tests:
        doc["tests"] = spec.tests
    return yaml.dump(doc, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=1000)


class _Dumper(yaml.SafeDumper):
    pass


def _str(dumper, s):
    style = "|" if "\n" in s else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", s, style=style)


def _dict(dumper, d):
    # Flow style for small palette entries keeps one glyph per line.
    flow = all(not isinstance(v, (dict, list)) for v in d.values()) and len(d) <= 3 and not any(
        isinstance(v, str) and "\n" in v for v in d.values())
    return dumper.represent_mapping("tag:yaml.org,2002:map", d, flow_style=flow)


class _Flow(list):
    """A list of scalars written on one line: [3, 1, 2]."""


def _flow_lists(value):
    if isinstance(value, dict):
        return {k: _flow_lists(v) for k, v in value.items()}
    if isinstance(value, list):
        items = [_flow_lists(v) for v in value]
        return _Flow(items) if all(not isinstance(v, (dict, list)) for v in items) else items
    return value


_Dumper.add_representer(str, _str)
_Dumper.add_representer(dict, _dict)
_Dumper.add_representer(_Flow, lambda d, v: d.represent_sequence("tag:yaml.org,2002:seq", v, flow_style=True))


def parse_truth_table(text: str) -> tuple[list[str], list[str], list[tuple[dict, dict]]]:
    """Rows of ({input: bool}, {output: bool, or None for x = don't care})."""
    lines = [l for l in text.strip().split("\n") if l.strip()]
    head_in, head_out = (part.split() for part in lines[0].split("|"))
    rows = []
    for line in lines[1:]:
        part_in, part_out = line.split("|")
        if "x" in part_in:
            raise ValueError(f"row {line.strip()!r}: x (don't care) is only allowed in output columns")
        vals_in = [v == "1" for v in re.findall(r"[01]", part_in)]
        vals_out = [None if v == "x" else v == "1" for v in re.findall(r"[01x]", part_out)]
        rows.append((dict(zip(head_in, vals_in)), dict(zip(head_out, vals_out))))
    return head_in, head_out, rows
