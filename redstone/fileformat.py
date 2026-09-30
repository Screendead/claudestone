"""The `.redstone.yaml` format: a build, its named cells, and its tests, as data.

    name: and_gate
    description: Both inputs inverted by torches, merged, inverted again.
    palette:                     # one character -> one cell
      ".": air
      "=": smooth_stone
      "-": redstone_wire
      ">": repeater[facing=west]
      a: {input: a}              # driver cell: air in the build, where the harness
                                 # places or removes a redstone block
      o: {output: out, block: redstone_wire}
      L: {name: lamp, block: redstone_lamp}   # a named cell tests can read or use
    layers:                      # keyed by y; row = z from north (top) to south,
      0: |                       # column = x from west (left) to east
        .=====
      1: |
        a>#t-o
    tests:
      - name: logic
        truth_table: |           # 1/0 per named cell; inputs left of |, checks right
          a b | out
          0 0 | 0
        delay: 6                 # optional: worst-case ticks from input change to output
        max_delay: 8             # optional: upper bound instead of an exact delay
      - name: pulse
        steps:                   # run in order
          - drive: {a: 1}        # set input drivers
          - use: lever           # click a named lever or button
          - wait: 6              # advance ticks
          - expect: {lamp: 1}    # 1 = dust powered / lamp or torch lit / diode powered

Cell origin is the top-left character of each layer. Every layer grid must have the
same width and height.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .build import Build, Pos

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


def _norm(state: str) -> str:
    return state if ":" in state.split("[")[0] else "minecraft:" + state


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

    def cell(self, name: str) -> Pos:
        if name in self.inputs:
            return self.inputs[name]
        return self.named[name]


def load(path: Path | str) -> Spec:
    path = Path(path)
    doc = yaml.safe_load(path.read_text())
    palette = {str(k): v for k, v in doc["palette"].items()}
    spec = Spec(doc["name"], Build(), description=doc.get("description", ""), tests=doc.get("tests", []), path=path)
    shape = None
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
                    spec.inputs[entry["input"]] = pos
                    continue
                spec.build.place(pos, entry["block"])
                name = entry.get("output") or entry.get("name")
                spec.named[name] = pos
                if "output" in entry:
                    spec.outputs[name] = pos
    return spec


def dump(spec: Spec) -> str:
    """Serialise a spec, choosing glyphs automatically. Round-trips through load()."""
    cells: dict[Pos, str] = dict(spec.build.blocks)
    labels: dict[Pos, dict] = {}
    for name, pos in spec.inputs.items():
        labels[pos] = {"input": name}
    for name, pos in spec.named.items():
        key = "output" if name in spec.outputs else "name"
        labels[pos] = {key: name, "block": _short(cells[pos])}
    everything = list(cells) + list(labels)
    xs, ys, zs = zip(*everything)
    lo_x, lo_z = min(0, min(xs)), min(0, min(zs))
    if lo_x < 0 or lo_z < 0:
        raise ValueError("spec cells must have non-negative x and z")
    width, depth = max(xs) + 1, max(zs) + 1

    palette: dict[str, object] = {".": "air"}
    by_state: dict[str, str] = {"minecraft:air": "."}
    spare = [c for c in "ABCDEFGHIJKMNOPQSTUVWXYZbcdefghijklmpqrstwxyz0123456789" if c not in GLYPHS.values()]

    def next_free() -> str:
        return next(c for c in spare if c not in palette)

    def glyph_for_state(state: str) -> str:
        if state not in by_state:
            g = GLYPHS.get(state) or next_free()
            by_state[state] = g
            palette[g] = _short(state)
        return by_state[state]

    def glyph_for_label(label: dict) -> str:
        name = label.get("input") or label.get("output") or label.get("name")
        g = name[0] if name[0] not in palette and name[0] not in GLYPHS.values() else next_free()
        palette[g] = label
        return g

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
    doc["palette"] = palette
    doc["layers"] = layers
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


_Dumper.add_representer(str, _str)
_Dumper.add_representer(dict, _dict)


def parse_truth_table(text: str) -> tuple[list[str], list[str], list[tuple[dict, dict]]]:
    lines = [l for l in text.strip().split("\n") if l.strip()]
    head_in, head_out = (part.split() for part in lines[0].split("|"))
    rows = []
    for line in lines[1:]:
        vals_in, vals_out = (list(map(int, re.findall(r"[01]", part))) for part in line.split("|"))
        rows.append((dict(zip(head_in, map(bool, vals_in))), dict(zip(head_out, map(bool, vals_out)))))
    return head_in, head_out, rows
