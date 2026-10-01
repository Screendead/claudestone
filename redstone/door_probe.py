"""Function text for watching a piston door tick by tick (design sections 2.2 and 4).

Two probes, both run under `execute positioned <build origin>` like `probe_functions`:

- The hallway probe writes a class code per visible cell into `redstone_ai:probe h.c<i>`,
  the whole block entity of any moving_piston there into `h.m<i>` (its `progress` is
  progressO: 0.0 in the tick the move starts, 0.5 in the next), and for each hallway box
  the count of foreign entities in `h.n<b>` and their full NBT in the list `h.e`.
- The occupancy functions keep a union over ticks in `redstone_ai:occ`: `any.c<i>` (not
  air), `circ.c<i>` (circuitry), `door.c<i>` (door material, possibly moving) and
  `shell.c<i>` (something reached the region's outer layer: grow the margin). `occ`
  covers every cell outside the hallway, `occ_hall` the hallway cells, called only in
  the open state. Nothing resets them except `occ_reset`.

Block predicates resolve tags when a function is parsed, so the tags from `write_tags`
must be in the pack before the `reload` that loads these functions.
"""

import json
import re
from itertools import product
from pathlib import Path

from .build import Pos, namespaced
from .harness import PACK, PROBE_CHUNK

Box = tuple[Pos, Pos]

KNOWN_BLOCKS = set(json.loads((Path(__file__).with_name("blocks.json")).read_text())["blocks"])

PROBE = f"{PACK}:probe"
OCC = f"{PACK}:occ"
DOOR_TAG = f"#{PACK}:door_material"
SURFACE_TAG = f"#{PACK}:surface_material"
# #minecraft:air is air, cave_air and void_air (VanillaBlockTagsProvider).
AIR_TAG = "#minecraft:air"
# Entities the harness puts in the hallway itself (a mannequin standing in for a player)
# carry this tag and are not the door's.
RIG_TAG = "rig_dummy"
ENTITIES = f"type=!player,tag=!{RIG_TAG}"

AIR, DOOR, SURFACE, MOVING, HEAD, OTHER = 0, 1, 2, 3, 4, 9
# moving_piston `facing` is saved as Direction.get3DDataValue.
FACING = ("down", "up", "north", "south", "west", "east")
# Lowest priority first: every cell gets OTHER, then each match overwrites, so the last
# match wins. When a block is both door and surface material, the code says DOOR and the
# cell's position has to tell a door block from the hallway's walls.
CLASSES = ((HEAD, "minecraft:piston_head"), (MOVING, "minecraft:moving_piston"),
           (SURFACE, SURFACE_TAG), (DOOR, DOOR_TAG), (AIR, AIR_TAG))

# Occupancy region: build bounds and hallway, grown this far on every side and clamped
# to the plot.
MARGIN = 2
# Rules 4.2 exempt "outer-surface and hallway blocks that fit the type"; a block of the
# surface material elsewhere (a support under dust, say) is circuitry. True exempts the
# material wherever it stands, as the design's first draft did.
SURFACE_EXEMPT_ANYWHERE = False


def box_cells(box: Box) -> list[Pos]:
    lo, hi = box
    return [(x, y, z) for x, y, z in product(*(range(min(a, b), max(a, b) + 1) for a, b in zip(lo, hi)))]


def cells(boxes: list[Box]) -> set[Pos]:
    return {p for box in boxes for p in box_cells(box)}


def visible_cells(hallway: list[Box], visible: list[Box] | None = None) -> set[Pos]:
    """The hallway and the cells seen from it: by default every face neighbour of a
    hallway cell; glass types declare their own boxes."""
    hall = cells(hallway)
    if visible is not None:
        return hall | cells(visible)
    faces = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    return hall | {(x + dx, y + dy, z + dz) for x, y, z in hall for dx, dy, dz in faces}


def _block_ids(materials: list[str]) -> list[str]:
    ids = [namespaced(m) for m in materials]
    unknown = [m for m in ids if m.removeprefix("minecraft:") not in KNOWN_BLOCKS or "[" in m or "{" in m]
    if unknown:
        raise ValueError(f"not plain block ids of this version: {unknown}")
    return ids


def tag_files(door_material: list[str], surface_material: list[str]) -> dict[str, str]:
    """Tag name -> JSON for data/<pack>/tags/block/<name>.json."""
    return {name: json.dumps({"values": _block_ids(m)}, indent=2)
            for name, m in (("door_material", door_material), ("surface_material", surface_material))}


def write_tags(pack_root: Path, tags: dict[str, str]) -> None:
    tag_dir = pack_root / "data" / PACK / "tags" / "block"
    tag_dir.mkdir(parents=True, exist_ok=True)
    for name, body in tags.items():
        (tag_dir / f"{name}.json").write_text(body)


def _chunks(lines: list[str]) -> list[str]:
    parts = [lines[i:i + PROBE_CHUNK] for i in range(0, len(lines), PROBE_CHUNK)] or [[]]
    return ["\n".join(c) + "\n" for c in parts]


def _at(pos: Pos) -> str:
    return " ".join(f"~{c}" for c in pos)


def _entities_in(box: Box) -> tuple[str, str]:
    """`execute` prefix and selector for the entities whose hitbox meets a box.

    Selector x/y/z take no `~`, so the box corner comes from the execution position; an
    integer `positioned` centres x and z on the block, hence `align`. The selector box is
    [corner, corner + d + 1) and matches any hitbox that intersects it."""
    lo = tuple(min(a, b) for a, b in zip(*box))
    dx, dy, dz = (abs(a - b) for a, b in zip(*box))
    return f"execute positioned {_at(lo)} align xyz", f"@e[{ENTITIES},dx={dx},dy={dy},dz={dz}]"


def hallway_probe_functions(hallway: list[Box], visible: list[Box] | None = None) -> tuple[list[str], list[Pos]]:
    """Functions writing the class code of every visible cell as h.c<i>, a moving_piston's
    block entity as h.m<i>, and per hallway box b the foreign entity count as h.n<b>
    with each entity's NBT appended to h.e. The first function clears h."""
    probed = sorted(visible_cells(hallway, visible))
    lines = [f"data modify storage {PROBE} h set value {{}}"]
    for i, pos in enumerate(probed):
        p = _at(pos)
        lines.append(f"data modify storage {PROBE} h.c{i} set value {OTHER}")
        for code, predicate in CLASSES:
            lines.append(f"execute if block {p} {predicate} run data modify storage {PROBE} h.c{i} set value {code}")
        lines.append(f"execute if block {p} minecraft:moving_piston run "
                     f"data modify storage {PROBE} h.m{i} set from block {p}")
    for b, box in enumerate(hallway):
        at, selector = _entities_in(box)
        lines.append(f"{at} store result storage {PROBE} h.n{b} int 1 if entity {selector}")
        lines.append(f"{at} as {selector} run data modify storage {PROBE} h.e append from entity @s")
    return _chunks(lines), probed


def _state_forms(block: str) -> tuple[str, str]:
    """SNBT a moving_piston's `blockState` takes for a block: BlockState.CODEC saves a
    block's default state as its bare id, and any other state as {Name, Properties}."""
    return f'"{block}"', f'{{Name:"{block}"}}'


def occupancy_region(bounds: Box, hallway: list[Box], plot_size: Pos,
                     margin: int = MARGIN) -> tuple[list[Pos], set[Pos]]:
    """Every cell of the region, sorted, and its shell: the outer layer, less any cell of
    the unclamped core (where the plot edge cut the margin away)."""
    corners = [bounds[0], bounds[1], *(c for box in hallway for c in box)]
    core_lo = tuple(min(c[a] for c in corners) for a in range(3))
    core_hi = tuple(max(c[a] for c in corners) for a in range(3))
    lo = tuple(max(0, c - margin) for c in core_lo)
    hi = tuple(min(s - 1, c + margin) for c, s in zip(core_hi, plot_size))
    region = box_cells((lo, hi))

    def in_core(p):
        return all(a <= c <= b for a, c, b in zip(core_lo, p, core_hi))

    shell = {p for p in region if any(c in (a, b) for a, c, b in zip(lo, p, hi)) and not in_core(p)}
    return region, shell


def occupancy_functions(bounds: Box, hallway: list[Box], static: set[Pos], surface: set[Pos],
                        door_material: list[str], surface_material: list[str], plot_size: Pos,
                        margin: int = MARGIN, track: set[Pos] | None = None
                        ) -> tuple[list[str], list[str], list[Pos], set[int]]:
    """(occ chunks, occ_hall chunks, region cells, shell indices).

    `bounds` is the build's bounds, `static` the frame and input device cells (never
    flagged), `surface` the hallway and outer surface cells, where the surface material
    is not circuitry. Index i of every flag is the cell's index in the region list.
    With `track`, only those cells get lines (with the same indices), for a per-tick pass
    over the cells blocks can move through.
    """
    door_ids = _block_ids(door_material)
    surface_ids = _block_ids(surface_material)
    region, shell = occupancy_region(bounds, hallway, plot_size, margin)
    hall = cells(hallway)
    occ, occ_hall, shell_index = [], [], set()
    for i, pos in enumerate(region):
        if pos in static or (track is not None and pos not in track):
            continue
        p = _at(pos)
        on_surface = SURFACE_EXEMPT_ANYWHERE or pos in surface
        exempt = f"unless block {p} {DOOR_TAG}" + (f" unless block {p} {SURFACE_TAG}" if on_surface else "")
        moved_exempt = "".join(f" unless data block {p} {{source:0b,blockState:{form}}}"
                               for m in door_ids + (surface_ids if on_surface else []) for form in _state_forms(m))
        lines = [
            f"execute unless block {p} {AIR_TAG} run data modify storage {OCC} any.c{i} set value 1b",
            f"execute unless block {p} {AIR_TAG} {exempt} unless block {p} minecraft:moving_piston run "
            f"data modify storage {OCC} circ.c{i} set value 1b",
            f"execute if block {p} minecraft:moving_piston{moved_exempt} run "
            f"data modify storage {OCC} circ.c{i} set value 1b",
            f"execute if block {p} {DOOR_TAG} run data modify storage {OCC} door.c{i} set value 1b",
            *(f"execute if block {p} minecraft:moving_piston if data block {p} {{source:0b,blockState:{form}}} "
              f"run data modify storage {OCC} door.c{i} set value 1b" for m in door_ids for form in _state_forms(m)),
        ]
        if pos in shell:
            shell_index.add(i)
            lines.append(f"execute unless block {p} {AIR_TAG} run data modify storage {OCC} shell.c{i} set value 1b")
        (occ_hall if pos in hall else occ).extend(lines)
    at, selector = _entities_in((region[0], region[-1]))
    occ.append(f"{at} as {selector} run data modify storage {OCC} e append from entity @s")
    return _chunks(occ), _chunks(occ_hall), region, shell_index


OCC_RESET = "".join(f"data modify storage {OCC} {key} set value {empty}\n"
                    for key, empty in (("any", "{}"), ("circ", "{}"), ("door", "{}"), ("shell", "{}"), ("e", "[]")))


def door_functions(hallway_probe: list[str], occ: list[str], occ_hall: list[str]) -> dict[str, str]:
    """Function name -> body, to merge into the one `write_datapack` call (it deletes
    functions it is not given)."""
    return {**{f"hall{i}": body for i, body in enumerate(hallway_probe)},
            **{f"occ{i}": body for i, body in enumerate(occ)},
            **{f"occ_hall{i}": body for i, body in enumerate(occ_hall)},
            "occ_reset": OCC_RESET}


def compound(snbt: str, key: str) -> str | None:
    """The `{...}` value of a key in `data get` output, matched by brace depth."""
    m = re.search(rf"(?:^|[{{,]\s*){re.escape(key)}: \{{", snbt)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    for j in range(start, len(snbt)):
        depth += {"{": 1, "}": -1}.get(snbt[j], 0)
        if depth == 0:
            return snbt[start:j + 1]
    raise ValueError(f"unbalanced SNBT after {key}")


def read_hallway(reply: str, count: int, boxes: int) -> tuple[list[int], dict[int, dict], list[int]]:
    """Parse `data get storage redstone_ai:probe h`: the code of each probed cell, the
    moving_piston fields {progress, extending, source, facing, block} by cell index, and the
    entity count per hallway box."""
    h = compound(reply, "h") or "{}"
    top = h[1:-1]
    while re.search(r"\{[^{}]*\}", top):
        top = re.sub(r"\{[^{}]*\}", "", top)
    codes = {int(i): int(v) for i, v in re.findall(r"\bc(\d+): (\d+)", top)}
    counts = {int(b): int(v) for b, v in re.findall(r"\bn(\d+): (\d+)", top)}
    moving = {}
    for i in (int(i) for i in re.findall(r"\bm(\d+): \{", h)):
        m = compound(h, f"m{i}")
        # A default state is saved as its bare id, any other as {Name, Properties}.
        name = re.search(r'blockState: (?:"([^"]+)"|\{.*?Name: "([^"]+)")', m)
        moving[i] = {"progress": float(re.search(r"\bprogress: (-?[\d.]+)f", m).group(1)),
                     "extending": re.search(r"\bextending: (\d)b", m).group(1) == "1",
                     "source": re.search(r"\bsource: (\d)b", m).group(1) == "1",
                     "facing": FACING[int(re.search(r"\bfacing: (\d)b", m).group(1))],
                     "block": (name.group(1) or name.group(2)) if name else None}
    return [codes.get(i, OTHER) for i in range(count)], moving, [counts.get(b, 0) for b in range(boxes)]


def read_flags(reply: str) -> dict[str, set[int]]:
    """Parse `data get storage redstone_ai:occ`: flagged cell indices per key."""
    return {key: {int(i) for i in re.findall(r"\bc(\d+): 1b", compound(reply, key) or "")}
            for key in ("any", "circ", "door", "shell")}
