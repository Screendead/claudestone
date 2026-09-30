"""Squid volume of a door: the bounding box of everything its wiring ever occupies.

Door Rules 4.2: width * height * depth of the circuitry, cumulative across every
opening/closing operation and both stable states, blocks and entities alike, excluding
(1) door, outer-surface and hallway blocks that fit the type, the door frame and the input
device, (2) anything inside the hallway except in the open state, (3) entities the designer
shows need not reach outside the wiring, and (4) the part of an entity's hitbox where a
block could still be placed by hand.

The caller observes the world once per tick and passes the observations here; nothing in
this module talks to a server. Two numbers come out: V_any counts every non-air block, V_circ
leaves out door material wherever it stands (whether a door block retracted into the wall is
circuitry is not settled by the rules text) and surface material only on the outer surface
and in the hallway; elsewhere, a support under dust say, it is wiring (door_probe does the same).
"""

import math
import struct
from collections.abc import Iterable
from dataclasses import dataclass, field

from .entity_dims import BLOCKS_BUILDING, ENTITY_DIMS

Pos = tuple[int, int, int]
Box = tuple[Pos, Pos]  # inclusive corners, min then max
Aabb = tuple[tuple[float, float, float], tuple[float, float, float]]

AIR = frozenset({"air", "cave_air", "void_air"})
MARGIN = 2  # layers of observed cells around the build and hallway; the outermost is the shell
# Voxel-shape merging treats coordinates within 1e-7 as one (IndirectMerger), so a hitbox
# overlapping a cell by no more than this doesn't stop a block being placed there.
TOUCH = 1e-7
# Exception 4 read by its "i.e.": a hitbox occupies only cells where it stops a hand-placed
# block, and only blocksBuilding entities do. False counts every entity's overlapped cells.
PLACEMENT_BLOCKING_ONLY = True


@dataclass(frozen=True)
class Entity:
    id: str  # entity type, with or without minecraft:
    pos: tuple[float, float, float]  # feet: the centre of the hitbox's bottom face
    scale: float = 1.0  # baby mobs 0.5, slimes their size, the scale attribute
    name: str = ""  # matched against the spec's volume-exempt entities


@dataclass(frozen=True)
class Tick:
    """One observation. blocks maps each occupied cell to its block id; a moving_piston cell
    gives the id of the block it carries, so a moving head is circuitry and a moving door
    block is door material. open is true only in the stable open state."""

    blocks: dict[Pos, str]
    entities: tuple[Entity, ...] = ()
    open: bool = False


@dataclass(frozen=True)
class Zones:
    frame: frozenset[Pos]
    device: frozenset[Pos]  # the input device's cell(s)
    hallway: frozenset[Pos]
    region: Box  # observed cells; its outermost layer is the shell
    door_material: frozenset[str]
    surface_material: frozenset[str]
    outer_surface: frozenset[Pos] = frozenset()  # cells here holding surface material are ignored
    exempt: frozenset[str] = frozenset()  # entity names excluded under exception 3


@dataclass
class Volume:
    any: set[Pos] = field(default_factory=set)
    circ: set[Pos] = field(default_factory=set)
    shell: set[Pos] = field(default_factory=set)  # occupied cells on or beyond the shell

    @property
    def v_any(self) -> int:
        return size(self.any)

    @property
    def v_circ(self) -> int:
        return size(self.circ)

    @property
    def ok(self) -> bool:
        return not self.shell


def bare(block_id: str) -> str:
    return block_id.split("[")[0].split("{")[0].removeprefix("minecraft:")


def cells(boxes: Iterable[Box]) -> frozenset[Pos]:
    return frozenset((x, y, z) for (x0, y0, z0), (x1, y1, z1) in boxes
                     for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) for z in range(z0, z1 + 1))


def bounds(occupied: Iterable[Pos]) -> Box | None:
    occupied = list(occupied)
    if not occupied:
        return None
    xs, ys, zs = zip(*occupied)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def dims(box: Box | None) -> Pos:
    if box is None:
        return 0, 0, 0
    lo, hi = box
    return tuple(b - a + 1 for a, b in zip(lo, hi))


def size(occupied: Iterable[Pos]) -> int:
    w, h, d = dims(bounds(occupied))
    return w * h * d


def region(boxes: Iterable[Box], margin: int = MARGIN, clamp: Box | None = None) -> Box:
    """The build's and hallway's joint bounding box grown by margin, inside clamp if given."""
    lo, hi = bounds(p for box in boxes for p in box)
    lo, hi = tuple(a - margin for a in lo), tuple(b + margin for b in hi)
    if clamp:
        lo, hi = tuple(map(max, lo, clamp[0])), tuple(map(min, hi, clamp[1]))
    return lo, hi


def on_shell(pos: Pos, box: Box) -> bool:
    """On box's outermost layer or outside it."""
    return any(p <= a or p >= b for p, a, b in zip(pos, *box))


def head_cell(base: Pos, facing: str) -> Pos:
    """The cell a piston's head enters; count it for any piston that ever fired an event."""
    dx, dy, dz = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0),
                  "east": (1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}[facing]
    return base[0] + dx, base[1] + dy, base[2] + dz


def _f32(v: float) -> float:
    return struct.unpack("f", struct.pack("f", v))[0]


def hitbox(entity: Entity) -> Aabb:
    """EntityDimensions.makeBoundingBox, float arithmetic as in the game."""
    w, h = ENTITY_DIMS[bare(entity.id)]
    half = _f32(_f32(_f32(w) * _f32(entity.scale)) / 2)
    h = _f32(_f32(h) * _f32(entity.scale))
    x, y, z = entity.pos
    return (x - half, y, z - half), (x + half, y + h, z + half)


def _span(lo: float, hi: float) -> range:
    first = math.floor(lo)
    return range(first, max(first, math.ceil(hi)))


def aabb_cells(box: Aabb) -> set[Pos]:
    """Cells a hitbox overlaps by more than TOUCH on every axis."""
    (x0, y0, z0), (x1, y1, z1) = box
    axes = []
    for lo, hi in ((x0, x1), (y0, y1), (z0, z1)):
        axes.append([i for i in _span(lo, hi) if min(hi, i + 1) - max(lo, i) > TOUCH])
    return {(x, y, z) for x in axes[0] for y in axes[1] for z in axes[2]}


def entity_cells(entity: Entity) -> set[Pos]:
    """Cells the entity keeps a hand-placed block out of; none if it never blocks placement.
    A marker armor stand must be passed as id 'marker' or left out."""
    kind = bare(entity.id)
    if kind not in ENTITY_DIMS:
        raise KeyError(f"unknown entity type {entity.id!r}")
    if PLACEMENT_BLOCKING_ONLY and kind not in BLOCKS_BUILDING:
        return set()
    return aabb_cells(hitbox(entity))


def volume(ticks: Iterable[Tick], zones: Zones) -> Volume:
    out = Volume()
    excluded = zones.frame | zones.device
    for tick in ticks:
        occupied = [(p, bare(b)) for p, b in tick.blocks.items() if bare(b) not in AIR]
        for entity in tick.entities:
            if entity.name not in zones.exempt:
                occupied += [(p, None) for p in entity_cells(entity)]
        for pos, block in occupied:
            if on_shell(pos, zones.region):
                out.shell.add(pos)
            if pos in excluded or (pos in zones.hallway and not tick.open):
                continue
            if pos in zones.outer_surface and block in zones.surface_material:
                continue
            out.any.add(pos)
            fits = block in zones.door_material or (block in zones.surface_material and pos in zones.hallway)
            if not fits:
                out.circ.add(pos)
    return out
