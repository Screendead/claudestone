"""Piston door tests: the `door:` section of a spec and the `door_cycle` test.

Wires door_probe (function text), door_timing (times and seamless grades) and door_volume
(the Squid volume) into a Rig (design: docs/research/door_harness_design.md, T3, T4, T6,
T7, T9, T12).

Input (T7): the door's input is a drive cell behind a fixture `repeater[delay=1]`. The
harness places the redstone block and steps one tick at a time; tick 0 is the first tick
at whose end the repeater's `powered` has flipped. The door is placed with the input off in
its `initial` state, and each change of the input toggles it.

Each tick of an operation the hallway probe reads the hallway (the doorway and `depth`
cells on each side of it) and the walls, floor and ceiling beside it, never the build:
for a 16x16 doorway at depth 1 that is 768 + 192 = 960 cells. Blocks moving out of the
doorway land in those cells, so every movement's progress ladder is seen. The operation
ends when the observations are static for door_timing.QUIET_TICKS, or the test's `quiet`
(or periodic).

Volume (T4, T12): the occupancy flags in storage are a union over the whole cycle. The
full region (build bounds and hallway, grown by door_probe.MARGIN, inside the plot) is
flagged only in the stable states; each tick flags only the cells on each piston's line
(its head cell and the 12 it can push through), which is where blocks move, and notes
which pistons fired (their base ever not in its placed state). A fired piston's head cell
counts even if no observation saw the head (an extend and retract within one tick).
Blocks moved by a piston that has itself been moved are seen only in the stable states.
"""

import re
from dataclasses import dataclass, field

from . import door_probe, door_timing as dt, door_volume as dv
from .build import STEP, Pos, block_id, facing, namespaced
from .harness import PACK, parse_state

FACINGS = ("north", "south", "east", "west", "up", "down")
INITIAL = ("closed", "open")
READINGS = ("R", "H1", "R1")
TIER_RANK = {"SUPER": 4, "FULL": 3, "SEMI": 2, "QUART": 1}
DOOR_KEYS = {"doorway", "depth", "blocks", "surface", "input", "repeater", "lever", "device", "outer_surface", "tier",
             "initial"}
DOORWAY_KEYS = {"origin", "width", "height", "facing"}
CYCLE_KEYS = {"cycles", "reading", "tier", "max_open", "max_close", "max_open_visible", "max_close_visible",
              "max_volume", "max_ticks", "quiet"}
PISTONS = ("minecraft:piston", "minecraft:sticky_piston")
PUSH_LIMIT = 12
# Ticks from placing the drive block to the fixture repeater's output changing: a delay-1
# repeater takes 2, or 1 for an input in the player phase (MC-172213).
MAX_LEAD = 8
AIR_IDS = {"air", "cave_air", "void_air"}
# The at-rest scan compares each slab of the region with the slab this far above it, which
# no plot reaches (plots stand at y=56 and are at most 64 tall).
SKY = 128


def _axes(face: str) -> tuple[int, int, int]:
    """(normal, width, height) axes of a doorway facing `face`."""
    if face in ("north", "south"):
        return 2, 0, 1
    if face in ("east", "west"):
        return 0, 2, 1
    return 1, 0, 2


def _unit(axis: int, n: int = 1) -> Pos:
    return tuple(n if a == axis else 0 for a in range(3))


def _add(a: Pos, b: Pos) -> Pos:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def geometry(door: dict) -> tuple[list[Pos], set[Pos], set[Pos]]:
    """(doorway cells, hallway cells, surface cells). The hallway is the doorway and `depth`
    cells on each side along its facing; the surface is every face neighbour of the hallway
    within that slab, so the hallway's two open ends are not walls."""
    way = door["doorway"]
    normal, wide, high = _axes(way["facing"])
    origin = tuple(way["origin"])
    frame = [_add(_add(origin, _unit(wide, i)), _unit(high, j))
             for j in range(way["height"]) for i in range(way["width"])]
    depth = door.get("depth", 1)
    hallway = {_add(p, _unit(normal, k)) for p in frame for k in range(-depth, depth + 1)}
    plane = origin[normal]
    surface = {_add(p, d) for p in hallway for d in STEP.values()} - hallway
    surface = {p for p in surface if abs(p[normal] - plane) <= depth}
    return frame, hallway, surface


def _bare(state: str) -> str:
    return block_id(namespaced(state)).removeprefix("minecraft:")


@dataclass
class Plan:
    """Everything a door_cycle needs, worked out from the spec before loading."""

    frame: list[Pos]
    hallway: set[Pos]
    surface: set[Pos]
    hall: dt.Hallway
    probed: list[Pos]  # the hallway probe's cell order
    door_material: list[str]
    surface_material: list[str]
    drive: list[Pos]
    repeater: Pos | None
    initial: str
    tier: str | None
    static: set[Pos]
    region: list[Pos]
    pistons: list[tuple[Pos, str]]  # (base, facing) of every piston in the build
    zones: dv.Zones
    functions: dict[str, str]
    tags: dict[str, str]
    hall_fns: list[str]
    track_fns: list[str]
    occ_fns: list[str]
    occ_hall_fns: list[str]
    hall_index: dict[Pos, int] = field(default_factory=dict)
    lever: Pos | None = None  # a lever input, flipped as a player would instead of the repeater
    shell: set[Pos] = field(default_factory=set)  # the region's outer layer, less the clamped core
    exempt_surface: set[Pos] = field(default_factory=set)  # where surface material is not circuitry


def plan(spec, plot_size: Pos) -> Plan:
    """Raises ValueError on a section door.problems would reject."""
    bad = problems(spec, plot_size)
    if bad:
        raise ValueError(f"door section: {bad[0]}" + (f" (and {len(bad) - 1} more)" if len(bad) > 1 else ""))
    door = spec.door
    frame, hallway, surface = geometry(door)
    hall = dt.Hallway.of(hallway, frame, door["doorway"]["facing"], surface)
    door_material = _door_material(spec)
    surface_material = [_bare(m) for m in door.get("surface", door_material)]
    lever = spec.named[door["lever"]] if door.get("lever") else None
    drive = [] if lever else spec.input_cells(door["input"])
    repeater = None if lever else spec.named[door["repeater"]]
    device = {spec.named[door["device"]]} if door.get("device") else set()
    static = set(frame) | set(drive) | {repeater, lever} - {None} | device | set(spec.fixtures)
    outer = door_probe.cells([tuple(map(tuple, b)) for b in door.get("outer_surface", [])])
    exempt_surface = hallway | surface | outer
    hall_box = (tuple(min(p[a] for p in hallway) for a in range(3)), tuple(max(p[a] for p in hallway) for a in range(3)))
    bounds = spec.build.bounds()

    hall_chunks, probed = door_probe.hallway_probe_functions([hall_box], [(p, p) for p in sorted(surface)])
    region, shell = door_probe.occupancy_region(bounds, [hall_box], plot_size)
    pistons = [(p, facing(s)) for p, s in sorted(spec.build.blocks.items()) if block_id(s) in PISTONS]
    in_region = set(region)
    track = {c for base, f in pistons for k in range(1, PUSH_LIMIT + 2)
             for c in [tuple(b + k * d for b, d in zip(base, STEP[f]))]} & in_region - hallway - static
    track_chunks, _, _, _ = door_probe.occupancy_functions(
        bounds, [hall_box], static, exempt_surface, door_material, surface_material, plot_size, track=track,
        door_flags=False)
    fired = [f"execute unless block ~{x} ~{y} ~{z} {block_id(spec.build.blocks[(x, y, z)])}[facing={f},extended="
             f"{parse_state(spec.build.blocks[(x, y, z)])[1].get('extended', 'false')}] run "
             f"data modify storage {door_probe.OCC} fired.p{j} set value 1b"
             for j, ((x, y, z), f) in enumerate(pistons)]
    x, y, z = repeater or lever
    functions = {
        **door_probe.door_functions(hall_chunks, [], []),
        "occ_entities": door_probe.entity_line((region[0], region[-1])) + "\n",
        **{f"occ_track{i}": body for i, body in enumerate(door_probe._chunks(
            [line for c in track_chunks for line in c.splitlines() if line] + fired))},
        "door_rep": f"execute if block ~{x} ~{y} ~{z} minecraft:{'repeater' if repeater else 'lever'}[powered=true] run "
                    f"data modify storage {door_probe.PROBE} h.rep set value 1\n",
        "door_reset": f"data modify storage {door_probe.OCC} fired set value {{}}\n",
        "door_e_clear": f"data modify storage {door_probe.OCC} e set value []\n",
    }
    names = sorted(functions)
    zones = dv.Zones(frozenset(frame), frozenset(static - set(frame)), frozenset(hallway),
                     (region[0], region[-1]), frozenset(door_material), frozenset(surface_material),
                     frozenset(outer))
    return Plan(frame, hallway, surface, hall, probed, door_material, surface_material, drive, repeater,
                door.get("initial", "closed"), door.get("tier"), static, region, pistons, zones, functions,
                door_probe.tag_files(door_material, surface_material),
                _numbered(names, "hall"), _numbered(names, "occ_track"), ["occ_entities"], [],
                {p: i for i, p in enumerate(probed)}, lever, shell, exempt_surface)


def _numbered(names: list[str], stem: str) -> list[str]:
    return sorted((n for n in names if re.fullmatch(rf"{stem}\d+", n)), key=lambda n: int(n[len(stem):]))


def _door_material(spec) -> list[str]:
    blocks = spec.door.get("blocks", "closed")
    if blocks != "closed":
        return [_bare(b) for b in blocks]
    frame, _, _ = geometry(spec.door)
    return sorted({_bare(spec.build.blocks[p]) for p in frame})


# ---- the section and test, checked offline ---------------------------------------------

def _int(v, least=None) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and (least is None or v >= least)


def _cell(v) -> bool:
    return isinstance(v, list) and len(v) == 3 and all(map(_int, v))


def problems(spec, plot_size: Pos) -> list[str]:
    """What is wrong with a spec's `door:` section; empty when plan() can use it."""
    door = spec.door
    if not isinstance(door, dict):
        return [f"door {door!r} is not a map"]
    out = [f"unknown key {k!r}" for k in door if k not in DOOR_KEYS]
    way = door.get("doorway")
    if not isinstance(way, dict):
        return out + ["needs doorway: {origin: [x, y, z], width: W, height: H, facing: F}"]
    out += [f"doorway: unknown key {k!r}" for k in way if k not in DOORWAY_KEYS]
    if not _cell(way.get("origin")):
        out.append(f"doorway origin {way.get('origin')!r} is not [x, y, z]")
    out += [f"doorway {k} {way.get(k)!r} is not a positive number" for k in ("width", "height") if not _int(way.get(k), 1)]
    if way.get("facing") not in FACINGS:
        out.append(f"doorway facing {way.get('facing')!r} is not one of {', '.join(FACINGS)}")
    if not _int(door.get("depth", 1), 1):
        out.append(f"depth {door['depth']!r} is not a number of cells (1 or more)")
    if door.get("initial", "closed") not in INITIAL:
        out.append(f"initial {door['initial']!r} is not closed or open")
    if door.get("tier") is not None and door["tier"] not in dt.TIERS:
        out.append(f"tier {door['tier']!r} is not one of {', '.join(dt.TIERS)}")
    for k in ("surface",) + (("blocks",) if door.get("blocks", "closed") != "closed" else ()):
        v = door.get(k)
        if v is not None and (not isinstance(v, list) or not v or not all(isinstance(b, str) for b in v)):
            out.append(f"{k} {v!r} is not a list of block ids")
    boxes = door.get("outer_surface", [])
    if not isinstance(boxes, list) or not all(isinstance(b, list) and len(b) == 2 and all(map(_cell, b)) for b in boxes):
        out.append(f"outer_surface {boxes!r} is not a list of [[x, y, z], [x, y, z]] boxes")
    out += _cell_problems(spec, door)
    if out:
        return out
    frame, hallway, surface = geometry(door)
    outside = sorted(p for p in hallway | surface if any(c < 0 or c >= s for c, s in zip(p, plot_size)))
    if outside:
        out.append(f"hallway or its walls reach {outside[0]}, outside the {plot_size} plot (a floor needs y >= 0, "
                   "so the doorway starts at y >= 1)")
    initial = door.get("initial", "closed")
    blocks = {p: b for p, b in spec.build.blocks.items() if _bare(b) not in AIR_IDS}  # a named cell may be air
    if door.get("blocks", "closed") == "closed":
        if initial != "closed":
            out.append("blocks: closed reads the door blocks from the doorway, so the build must be placed closed")
        out += [f"doorway cell {p} is air; blocks: closed needs a door block in every doorway cell"
                for p in frame if p not in blocks]
    clear = hallway - set(frame) if initial == "closed" else hallway
    out += [f"hallway cell {p} holds {blocks[p]} in the {initial} state" for p in sorted(clear) if p in blocks]
    if initial == "closed":
        out += [f"doorway cell {p} holds {blocks[p]}, not door material" for p in frame
                if p in blocks and door.get("blocks", "closed") != "closed"
                and _bare(blocks[p]) not in {_bare(b) for b in door["blocks"]}]
    try:
        door_probe.tag_files(_door_material(spec) if not out else [], [_bare(m) for m in door.get("surface", [])])
    except ValueError as e:
        out.append(str(e))
    return out


def _cell_problems(spec, door) -> list[str]:
    if "lever" in door:
        if "input" in door or "repeater" in door:
            return ["give lever, or input and repeater, not both"]
        name = door["lever"]
        if name not in spec.named or parse_state(spec.build.blocks[spec.named[name]])[0] != "minecraft:lever":
            return [f"lever {name!r} is not a named lever cell"]
        return [] if door.get("device") in (None, *spec.named) else [f"device {door['device']!r} is not a named cell"]
    out = []
    name = door.get("input")
    if name not in spec.inputs:
        out.append(f"input {name!r} is not an input of the spec")
    rep = door.get("repeater")
    if rep not in spec.named:
        return out + [f"repeater {rep!r} is not a named cell"]
    pos = spec.named[rep]
    block, props = parse_state(spec.build.blocks[pos])
    if block != "minecraft:repeater" or props.get("delay", "1") != "1":
        out.append(f"repeater {rep!r} is {spec.build.blocks[pos]}, not a repeater[delay=1]")
    if pos not in spec.fixtures:
        out.append(f"repeater {rep!r} must be a fixture: it is the test's input, not the door's")
    if out:
        return out
    behind = _add(pos, STEP[props.get("facing", "north")])
    drive = spec.input_cells(name)
    if behind not in drive:
        out.append(f"input {name!r} is not behind repeater {rep!r} (its input side is {behind})")
    for cell in drive:
        touched = [_add(cell, d) for d in STEP.values() if _add(cell, d) in spec.build.blocks and _add(cell, d) != pos]
        out += [f"drive cell {cell} also powers {spec.build.blocks[t]} at {t}; only the repeater may touch it"
                for t in touched]
    dev = door.get("device")
    if dev is not None and dev not in spec.named:
        out.append(f"device {dev!r} is not a named cell")
    return out


def cycle_problems(spec, cfg) -> list[str]:
    if cfg is None:
        cfg = {}
    if not isinstance(cfg, dict):
        return [f"door_cycle {cfg!r} is not a map"]
    out = [] if spec.door is not None else ["door_cycle needs a door: section"]
    out += [f"door_cycle: unknown key {k!r}" for k in cfg if k not in CYCLE_KEYS]
    if not _int(cfg.get("cycles", 1), 1):
        out.append(f"door_cycle cycles {cfg['cycles']!r} is not a positive number")
    if cfg.get("reading", "R") not in READINGS:
        out.append(f"door_cycle reading {cfg['reading']!r} is not one of {', '.join(READINGS)}")
    if cfg.get("tier") is not None and cfg["tier"] not in dt.TIERS:
        out.append(f"door_cycle tier {cfg['tier']!r} is not one of {', '.join(dt.TIERS)}")
    out += [f"door_cycle {k} {cfg[k]!r} is not a number of ticks" for k in
            ("max_open", "max_close", "max_open_visible", "max_close_visible") if k in cfg and not _int(cfg[k], 0)]
    out += [f"door_cycle {k} {cfg[k]!r} is not a positive number" for k in ("max_volume", "max_ticks", "quiet")
            if k in cfg and not _int(cfg[k], 1)]
    return out


# ---- reading the world ------------------------------------------------------------------

def _contents(reply: str) -> str:
    return reply.partition("has the following contents: ")[2].strip()


def _class(block: str | None, plan: Plan) -> int:
    if block is None:
        return dt.OTHER
    name = block.removeprefix("minecraft:")
    if name in AIR_IDS:
        return dt.AIR
    if name in plan.door_material:
        return dt.DOOR
    if name in plan.surface_material:
        return dt.SURFACE
    return dt.HEAD if name == "piston_head" else dt.OTHER


def _top(body: str) -> str:
    while re.search(r"\{[^{}]*\}|\[[^\[\]]*\]", body[1:-1]):
        body = body[0] + re.sub(r"\{[^{}]*\}|\[[^\[\]]*\]", "", body[1:-1]) + body[-1]
    return body


def parse_hallway(reply: str, plan: Plan, origin: Pos) -> tuple[dt.Observation, bool]:
    """The observation in a `data get storage redstone_ai:probe h` reply, and whether the
    fixture repeater was powered."""
    body = _contents(reply) or "{}"
    codes, moving, counts = door_probe.read_hallway("{h: " + body + "}", len(plan.probed), 1)
    cells = {}
    for i, pos in enumerate(plan.probed):
        m = moving.get(i)
        cells[pos] = dt.Cell(codes[i], dt.Moving(_class(m["block"], plan), m["progress"], m["extending"],
                                                 m["source"], m["facing"]) if m and codes[i] == dt.MOVING else None)
    entities = ()
    if any(counts):
        from .spec import snbt
        entities = tuple(_hall_entity(e, plan, origin) for e in _unique(snbt(body)[0].get("e", [])))
    return dt.Observation(cells, entities), bool(re.search(r"[{,]\s*rep: 1\b", _top(body)))


def _unique(entities: list[dict]) -> list[dict]:
    seen, out = set(), []
    for e in entities:
        key = str(e.get("UUID", id(e)))
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def _entity(nbt: dict, origin: Pos) -> dv.Entity:
    pos = tuple(float(p) - o for p, o in zip(nbt.get("Pos", [0, 0, 0]), origin))
    return dv.Entity(str(nbt.get("id", "unknown")), pos)


def _cells_of(entity: dv.Entity) -> set[Pos]:
    """Every cell the hitbox overlaps (seen from the hallway, any entity shows)."""
    if dv.bare(entity.id) in dv.ENTITY_DIMS:
        return dv.aabb_cells(dv.hitbox(entity))
    return {tuple(int(c // 1) for c in entity.pos)}


def _hall_entity(nbt: dict, plan: Plan, origin: Pos) -> dt.Entity:
    e = _entity(nbt, origin)
    return dt.Entity(dv.bare(e.id), frozenset(_cells_of(e) & set(plan.probed)), bool(nbt.get("Invisible", 0)))


class Probe:
    """The door's reads and writes, through Rig.call (one RCON sequence each)."""

    def __init__(self, rig, plan: Plan):
        self.rig, self.plan = rig, plan
        self.rest_any: set[Pos] = set()
        self.rest_circ: set[Pos] = set()

    def observe(self, track: bool = False) -> tuple[dt.Observation, bool]:
        fns = self.plan.hall_fns + ["door_rep"] + (self.plan.track_fns if track else [])
        return parse_hallway(self.rig.call(fns, f"{PACK}:probe h"), self.plan, self.rig.origin)

    def reset(self) -> None:
        self.rig.call(["occ_reset", "door_reset"])

    def stable(self, opened: bool) -> None:
        """At rest: flag the region's entities, and find the outermost occupied cells on each
        side of the region (the hallway counts only when open). A function testing every
        cell of a big build's region is too big for a satellite to parse (44 MB for LegDen's
        10x10 ran a 1 GB heap out of memory), so the region is narrowed from each face slab
        by slab, comparing a slab with the air SKY blocks above it, and only the cells of
        the first slab that isn't air are tested one by one."""
        self.rig.call(self.plan.occ_fns)
        skip = self.plan.static | (set() if opened else self.plan.hallway)
        empty: dict[tuple, bool] = {}
        self.rest_any |= self._extremes(skip, empty, circ=False)
        self.rest_circ |= self._extremes(skip, empty, circ=True)

    def _yes(self, command: str) -> bool:
        return self.rig.run(command).startswith("Test passed")

    def _abs(self, pos: Pos) -> str:
        return " ".join(str(o + c) for o, c in zip(self.rig.origin, pos))

    def _extremes(self, skip: set[Pos], empty: dict, circ: bool) -> set[Pos]:
        lo, hi = self.plan.region[0], self.plan.region[-1]
        found = set()
        for axis in range(3):
            for coords in (range(lo[axis], hi[axis] + 1), range(hi[axis], lo[axis] - 1, -1)):
                for c in coords:
                    a, b = list(lo), list(hi)
                    a[axis] = b[axis] = c
                    if (axis, c) not in empty:
                        sky = (a[0], a[1] + SKY, a[2])
                        empty[axis, c] = self._yes(f"execute if blocks {self._abs(tuple(a))} {self._abs(tuple(b))} "
                                                   f"{self._abs(sky)} all")
                    if empty[axis, c]:
                        continue
                    hit = next((p for p in door_probe.box_cells((tuple(a), tuple(b)))
                                if p not in skip and self._occupied(p, circ)), None)
                    if hit is not None:
                        found.add(hit)
                        break
        return found

    def _occupied(self, pos: Pos, circ: bool) -> bool:
        p = self._abs(pos)
        test = f"execute unless block {p} {door_probe.AIR_TAG}"
        if circ:
            test += f" unless block {p} {door_probe.DOOR_TAG}"
            if door_probe.SURFACE_EXEMPT_ANYWHERE or pos in self.plan.exempt_surface:
                test += f" unless block {p} {door_probe.SURFACE_TAG}"
        return self._yes(test)

    def entities(self) -> list[dict]:
        """The entities flagged since the last call, which it forgets."""
        from .spec import snbt
        body = _contents(self.rig.call([], f"{PACK}:occ e"))
        self.rig.call(["door_e_clear"])
        return _unique(snbt(body)[0]) if body.startswith("[") else []

    def flags(self) -> tuple[dict[str, set[int]], set[int]]:
        reply = self.rig.call([], f"{PACK}:occ")
        fired = door_probe.compound(reply, "fired") or ""
        return door_probe.read_flags(reply), {int(j) for j in re.findall(r"\bp(\d+): 1b", fired)}


# ---- the test ---------------------------------------------------------------------------

@dataclass
class Op:
    kind: str  # "open" or "close"
    run: dt.Run
    lead: int  # ticks from the drive to tick 0
    w: int = 0
    period: int = 1
    times: dict = field(default_factory=dict)
    visible: int | None = None


def _status(rig, spec, text):
    from .spec import status
    status(rig, f"{spec.name}: {text}")


def operate(rig, probe: Probe, plan: Plan, before: dt.Observation, rep_before: bool, on: bool, rec,
            max_ticks: int, quiet: int = dt.QUIET_TICKS) -> tuple[dt.Run, int]:
    """Set the input and record O(0..W+quiet). Tick 0 is the first observation in which the
    fixture repeater has flipped; with a lever input, the first tick after the flip (the
    player phase, so components it schedules fire a tick earlier: MC-172213)."""
    if plan.lever:
        rig.use(plan.lever)
    for pos in plan.drive:
        rig.drive(pos, on)
    rec.frame(f"door input {int(on)}")
    lead = 0
    while True:
        rig.step(1)
        rec.tick += 1
        lead += 1
        obs, rep = probe.observe(track=True)
        if rep != rep_before:
            break
        if lead >= MAX_LEAD:
            raise dt.DoorError(f"the fixture repeater did not switch within {MAX_LEAD} ticks of the input")
    # Keys as small ints, and a repeated observation stored once: an operation may run for
    # thousands of ticks of 960 cells.
    ids = {obs.key(): 0}
    ticks, keys = [obs], [0]
    limit = max_ticks + quiet + dt.PERIODS * dt.MAX_PERIOD
    run = dt.Run(before, ticks)
    trailing = 1
    while len(ticks) <= limit:
        if trailing > quiet or (len(ticks) % 32 == 0 and dt.quiescence(run, quiet, keys=keys)):
            break
        rig.step(1)
        rec.tick += 1
        obs, _ = probe.observe(track=True)
        key = ids.setdefault(obs.key(), len(ids))
        trailing = trailing + 1 if key == keys[-1] else 1
        ticks.append(ticks[-1] if key == keys[-1] else obs)
        keys.append(key)
    return run, lead


def _cell_at(obs: dt.Observation, pos: Pos) -> dt.Cell:
    return obs.cells.get(pos, dt.Cell(dt.AIR))


def zero_tick_pull(run: dt.Run, mv: dt.Movement) -> bool:
    """A pull whose piston head was not at the block's destination the tick before: the
    piston extended and retracted within one tick."""
    if mv.origin is None or mv.start < 0:
        return False
    m = _cell_at(run.at(mv.start), mv.cell).moving
    return (m is not None and not m.extending and not m.source
            and _cell_at(run.at(mv.start - 1), mv.cell).code != dt.HEAD)


def _ends(h: dt.Hallway, run: dt.Run, w: int, door_only: bool) -> list[tuple[int, int]]:
    """(rule end, R1 end) of each movement into, out of or within the hallway."""
    out = []
    for mv in dt.movements(run, h.visible):
        if not mv.touches(h.hallway) or mv.end > w or (door_only and dt.DOOR not in mv.blocks):
            continue
        out.append((mv.end, mv.start if zero_tick_pull(run, mv) else mv.end))
    return out


def readings(h: dt.Hallway, op: Op) -> dict:
    """The operation's end under each reading of the rules (HANDOFF open question):
    R, the rule as written (each movement ends at its landing, start + 2); H1, the tick the
    hallway holds its final pattern of real blocks (a pull counts once its origin is air);
    R1, as R but a 0-tick pull counts as instant (ends at its start)."""
    run, w = op.run, op.w
    if op.kind == "open":
        since = dt.pattern_since(run, dt.open_pattern(h), w)
        ends = _ends(h, run, w, door_only=False)
        return {"R": dt.opening_time(h, run, w), "H1": since, "R1": max([since, *(r1 for _, r1 in ends)])}
    ends = _ends(h, run, w, door_only=True)
    if not ends:
        raise dt.DoorError("no door block moved in the hallway")
    return {"R": dt.closing_time(h, run, w), "H1": dt.pattern_since(run, dt.closed_pattern(h), w),
            "R1": max(r1 for _, r1 in ends)}


def _delta(prev: dt.Observation | None, obs: dt.Observation, index: dict[Pos, int]) -> dict:
    """The cells whose reading changed since prev, by probe index: a code, or for a
    moving_piston [code, progress, moved class, extending, source, facing]."""
    out = {}
    for pos, cell in obs.cells.items():
        if prev is None or _cell_at(prev, pos) != cell:
            m = cell.moving
            out[str(index[pos])] = cell.code if m is None else [cell.code, m.progress, m.moved, int(m.extending),
                                                                int(m.source), m.facing]
    return out


def _trace(op: Op, plan: Plan) -> dict:
    frames, prev = [], op.run.before
    for obs in op.run.ticks:
        frames.append(_delta(prev, obs, plan.hall_index))
        prev = obs
    moves = [[list(mv.cell), list(mv.origin) if mv.origin else None, mv.start, mv.end]
             for mv in _safe_moves(op, plan)]
    return {"kind": op.kind, "lead": op.lead, "w": op.w, "period": op.period, "times": op.times,
            "visible": op.visible, "before": _delta(None, op.run.before, plan.hall_index), "ticks": frames,
            "moves": moves}


def _safe_moves(op: Op, plan: Plan) -> list:
    try:
        return dt.movements(op.run, plan.hall.visible)
    except dt.TimingModelError:
        return []


def _worst(values):
    values = [v for v in values if v is not None]
    return max(values) if values else None


def cycle(rig, spec, test: dict, rec, plan: Plan) -> dict:
    """Run test["door_cycle"]: `cycles` times open and close (or close and open), from the
    settled build. Times, seamless grades and the volume go in the result and the trace;
    a bound broken is a collected failure (rec.fail)."""
    cfg = test.get("door_cycle") or {}
    reading = cfg.get("reading", "R")
    max_ticks = cfg.get("max_ticks", dt.MAX_TICKS)
    quiet = cfg.get("quiet", dt.QUIET_TICKS)
    h = plan.hall
    probe = Probe(rig, plan)
    rec.door = {"probed": [list(p) for p in plan.probed], "ops": []}
    probe.reset()
    before, rep = probe.observe()
    pattern = dt.closed_pattern(h) if plan.initial == "closed" else dt.open_pattern(h)
    if not dt.matches(before, pattern):
        raise dt.DoorError(f"the door does not stand {plan.initial} after settling (a door the update pass sets "
                           "off: try update_pass: unobserved or none, see AUTHORING.md)")
    state, on = plan.initial, False
    phases: list[tuple[list[dict], bool]] = []
    probe.stable(opened=state == "open")
    phases.append((probe.entities(), state == "open"))
    ops: list[Op] = []
    for c in range(cfg.get("cycles", 1)):
        for _ in range(2):
            kind = "open" if state == "closed" else "close"
            on = not on
            _status(rig, spec, f"door cycle {c + 1}: {kind}")
            run, lead = operate(rig, probe, plan, before, rep, on, rec, max_ticks, quiet)
            op = Op(kind, run, lead)
            ops.append(op)
            phases.append((probe.entities(), False))
            state = "open" if kind == "open" else "closed"
            probe.stable(opened=state == "open")
            phases.append((probe.entities(), state == "open"))
            rec.frame(f"door {state}")
            try:
                op.w, op.period = dt.settle(run, max_ticks, quiet=quiet)
                op.times = readings(h, op)
                op.visible = dt.visible_time(h, run, op.w)
            finally:
                rec.door["ops"].append(_trace(op, plan))
            # Tick 0 was the repeater's flip, and the input stays put until the next operation.
            before, rep = run.ticks[-1], not rep
    result = _report(plan, ops, reading)
    result["volume"] = _volume(plan, probe, phases)
    _check(cfg, result, reading, plan, rec)
    rec.door["result"] = result
    return result


def _report(plan: Plan, ops: list[Op], reading: str) -> dict:
    h = plan.hall
    cycles, grades = [], []
    for i in range(0, len(ops) - 1, 2):
        a, b = ops[i], ops[i + 1]
        opening, closing = (a, b) if a.kind == "open" else (b, a)
        s = dt.seamless(h, opening.run, opening.w, closing.run, closing.w)
        grades.append(s)
        cycles.append({op.kind: {**op.times, "visible": op.visible, "lead": op.lead, "settled": op.w}
                       for op in (a, b)} | {"seamless": _grades(s), "tier": s.tier()})
    worst = dt.Seamless(*(dt.worst(getattr(s, c) for s in grades) for c in dt.COLUMNS))
    out = {"reading": reading, "probe_cells": len(plan.probed), "cycles": cycles}
    for kind in ("open", "close"):
        mine = [op for op in ops if op.kind == kind]
        out[kind] = {r: max(op.times[r] for op in mine) for r in READINGS}
        out[f"{kind}_visible"] = _worst(op.visible for op in mine)
    out["seamless"], out["tier"] = _grades(worst), worst.tier()
    return out


def _grades(s: dt.Seamless) -> dict:
    return {c: getattr(s, c) for c in dt.COLUMNS}


def _volume(plan: Plan, probe: Probe, phases) -> dict:
    flags, fired = probe.flags()
    region = plan.region
    blocks_any = {region[i] for i in flags["any"]} | probe.rest_any
    blocks_circ = {region[i] for i in flags["circ"]} | probe.rest_circ
    heads = {dv.head_cell(plan.pistons[j][0], plan.pistons[j][1]) for j in fired if j < len(plan.pistons)}
    heads -= plan.static | plan.hallway
    known, unknown = [], set()
    for entities, opened in phases:
        ticks = []
        for nbt in entities:
            e = _entity(nbt, probe.rig.origin)
            if dv.bare(e.id) in dv.ENTITY_DIMS:
                ticks.append(e)
            else:
                unknown |= _cells_of(e)
        known.append(dv.Tick({}, tuple(ticks), opened))
    ev = dv.volume(known, plan.zones)
    v = dv.Volume(blocks_any | heads | ev.any | unknown, blocks_circ | heads | ev.circ | unknown,
                  {region[i] for i in flags["shell"]} | (probe.rest_any & plan.shell) | ev.shell)
    box = dv.bounds(v.circ)
    return {"any": v.v_any, "circ": v.v_circ, "dims": list(dv.dims(box)),
            "box": [list(box[0]), list(box[1])] if box else None, "heads": len(heads - blocks_circ),
            "shell": sorted(map(list, v.shell))}


def _check(cfg: dict, result: dict, reading: str, plan: Plan, rec) -> None:
    for kind in ("open", "close"):
        bound = cfg.get(f"max_{kind}")
        if bound is not None and result[kind][reading] > bound:
            rec.fail(f"door {kind} time {result[kind][reading]} ticks ({reading}) exceeds bound {bound}")
        bound = cfg.get(f"max_{kind}_visible")
        got = result[f"{kind}_visible"]
        if bound is not None and got is not None and got > bound:
            rec.fail(f"door {kind} visible time {got} ticks exceeds bound {bound}")
    tier = cfg.get("tier", plan.tier)
    if tier is not None and TIER_RANK.get(result["tier"], 0) < TIER_RANK[tier]:
        rec.fail(f"door seamless tier {result['tier'] or 'none'} is below {tier}: {_fmt(result['seamless'])}")
    vol = result["volume"]
    if vol["shell"]:
        rec.fail(f"door volume: something reached the edge of the observed region at {vol['shell'][0]}; "
                 "the margin is too small to measure it")
    if cfg.get("max_volume") is not None and vol["circ"] > cfg["max_volume"]:
        rec.fail(f"door volume {vol['circ']} ({'x'.join(map(str, vol['dims']))}) exceeds bound {cfg['max_volume']}")


def _fmt(grades: dict) -> str:
    return " ".join(f"{c}={g or '-'}" for c, g in grades.items())


def summary(result: dict) -> str:
    """One line for a test result."""
    r = result["reading"]
    o, c = result["open"], result["close"]
    v = result["volume"]
    return (f"open {o[r]} (R {o['R']}, H1 {o['H1']}, R1 {o['R1']}; visible {result['open_visible']}), "
            f"close {c[r]} (R {c['R']}, H1 {c['H1']}, R1 {c['R1']}; visible {result['close_visible']}), "
            f"{result['tier'] or 'not seamless'}, volume {v['circ']} ({'x'.join(map(str, v['dims']))})")
