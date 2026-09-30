"""Rotate and mirror builds about the y axis the way `place template` does.

A transform is `quarter_turns` clockwise seen from above (vanilla Rotation.CLOCKWISE_90 is
one turn: north -> east) after an optional mirror in x (Mirror.FRONT_BACK: x -> -x). Mirror
comes first, as in StructureTemplate (`state.mirror(m).rotate(r)`). The pivot is the
build's origin; positions are not shifted back to non-negative coordinates.

Property tables follow the 26.3 source (net/minecraft/...), including its non-geometric
cases, so a rotated build matches `place template ... strict` block for block:
- world/level/block/Rotation.java, Mirror.java: direction and 0-15 `rotation` maps.
- world/level/levelgen/structure/templatesystem/StructureTemplate.java: `transform` for
  block and entity positions, and the entity yaw formula in placeEntities.
- HorizontalDirectionalBlock, DirectionalBlock subclasses (PistonBaseBlock, ObserverBlock,
  DispenserBlock, ...): `facing` rotated; mirrored via Mirror.getRotation, which flips
  east/west only. AnvilBlock has no mirror override, so an anvil keeps its facing.
- RotatedPillarBlock.rotatePillar, NetherPortalBlock: `axis` x <-> z on odd turns only.
- StandingSignBlock, CeilingHangingSignBlock, BannerBlock, SkullBlock: `rotation` in 16ths.
- RedstoneWireBlock, CrossCollisionBlock (fences, panes, bars), WallBlock, TripWireBlock,
  VineBlock, MossyCarpetBlock, HugeMushroomBlock, MultifaceBlock (glow lichen, sculk vein,
  resin clump support all six faces, so canRotate/canMirrorX hold): side keys permuted.
  FireBlock and ChorusPlantBlock (PipeBlock) do not override rotate, so they keep them.
- BaseRailBlock.rotate/mirror: rail `shape` tables below.
- StairBlock.mirror: only x-axis facings change, and inner shapes keep their side.
- DoorBlock.mirror: facing as above and `hinge` always cycles.
- ChestBlock: `type` (left/right) is left alone.
- CrafterBlock, JigsawBlock: `orientation` via OctahedralGroup.rotate(FrontAndTop), which is
  the pair (rotate(front), rotate(top)) (com/mojang/math/OctahedralGroup.java).
- HangingEntity.rotate/mirror, ItemFrame (`Facing`, 3D id), Painting (`facing`, 2D id).
"""

import math
import re

from .build import Build, Pos

HORIZONTAL = ["north", "east", "south", "west"]  # clockwise from above
DATA_3D = ["down", "up", "north", "south", "west", "east"]  # Direction.get3DDataValue
DATA_2D = ["south", "west", "north", "east"]  # Direction.get2DDataValue

RAIL_CW90 = {  # BaseRailBlock.rotate, CLOCKWISE_90
    "ascending_east": "ascending_south", "ascending_west": "ascending_north",
    "ascending_north": "ascending_east", "ascending_south": "ascending_west",
    "north_south": "east_west", "east_west": "north_south",
    "south_east": "south_west", "south_west": "north_west",
    "north_west": "north_east", "north_east": "south_east",
}
RAIL_MIRROR_X = {  # BaseRailBlock.mirror, FRONT_BACK; shapes not listed are unchanged
    "ascending_east": "ascending_west", "ascending_west": "ascending_east",
    "south_east": "south_west", "south_west": "south_east",
    "north_west": "north_east", "north_east": "north_west",
}
STAIRS_MIRROR_X = {"outer_left": "outer_right", "outer_right": "outer_left"}  # x-axis facings only

RAILS = {"rail", "powered_rail", "detector_rail", "activator_rail"}
UNROTATED_SIDES = {"fire", "chorus_plant"}
UNMIRRORED_FACING = {"anvil", "chipped_anvil", "damaged_anvil"}
SKULLS = {"skeleton_skull", "wither_skeleton_skull", "zombie_head", "player_head",
          "creeper_head", "dragon_head", "piglin_head"}
ATTACHED_ENTITIES = {"item_frame", "glow_item_frame", "painting", "leash_knot"}

# Default `facing` of blocks whose state may omit it; anything not listed has no facing
# as far as this module knows. Horizontal-facing blocks default north; the 6-way ones
# below are the registerDefaultState exceptions.
FACING_DEFAULT = {"observer": "south", "hopper": "down", "end_rod": "up", "amethyst_cluster": "up"}
FACING_UP_SUFFIXES = ("lightning_rod", "shulker_box", "_amethyst_bud")
FACING_NORTH = {
    "piston", "sticky_piston", "piston_head", "moving_piston", "dispenser", "dropper",
    "barrel", "command_block", "chain_command_block", "repeating_command_block", "repeater",
    "comparator", "chest", "trapped_chest", "ender_chest", "furnace", "blast_furnace",
    "smoker", "lectern", "lever", "tripwire_hook", "end_portal_frame", "calibrated_sculk_sensor",
    "chiseled_bookshelf", "decorated_pot", "ladder", "bell", "grindstone", "stonecutter",
    "loom", "beehive", "bee_nest", "vault", "carved_pumpkin", "jack_o_lantern", "cocoa",
    "big_dripleaf", "big_dripleaf_stem", "small_dripleaf", "pink_petals", "wildflowers",
    "leaf_litter", "dried_ghast", "campfire", "soul_campfire", "attached_melon_stem",
    "attached_pumpkin_stem", "redstone_wall_torch", "wall_torch", "soul_wall_torch",
    "copper_wall_torch", *UNMIRRORED_FACING,
}
FACING_NORTH_SUFFIXES = (
    "_button", "_trapdoor", "_door", "_fence_gate", "_stairs", "_bed", "_wall_sign",
    "_wall_hanging_sign", "_wall_banner", "_wall_head", "_wall_skull", "_glazed_terracotta",
    "_shelf", "copper_golem_statue", "copper_chest", "_wall_fan",
)


def defaults(block: str) -> dict[str, str]:
    """Default values of the properties a transform can change, for a namespaced or bare id."""
    b = block.removeprefix("minecraft:")
    d = {}
    if b in FACING_DEFAULT:
        d["facing"] = FACING_DEFAULT[b]
    elif b.endswith(FACING_UP_SUFFIXES):
        d["facing"] = "up"
    elif b in FACING_NORTH or b.endswith(FACING_NORTH_SUFFIXES):
        d["facing"] = "north"
    if b.endswith("_stairs"):
        d["shape"] = "straight"
    if b.endswith("_door"):
        d["hinge"] = "left"
    if b in RAILS:
        d["shape"] = "north_south"
    if b == "nether_portal":
        d["axis"] = "x"
    if b in ("crafter", "jigsaw"):
        d["orientation"] = "north_up"
    if b in SKULLS:
        d["rotation"] = "0"
    elif b.endswith(("_sign", "_banner")) and "_wall_" not in b:
        d["rotation"] = "8"
    return d


def parse_state(state: str) -> tuple[str, dict[str, str], str]:
    """Split `id[k=v,...]{nbt}` into id, properties in written order, and the raw NBT."""
    m = re.fullmatch(r"([^\[{]+)(?:\[([^\]]*)\])?(\{.*\})?", state, re.S)
    if not m:
        raise ValueError(f"not a block state: {state!r}")
    props = dict(kv.split("=", 1) for kv in (m.group(2) or "").split(",") if kv)
    return m.group(1), props, m.group(3) or ""


def format_state(block: str, props: dict[str, str], nbt: str = "") -> str:
    inner = ",".join(f"{k}={v}" for k, v in sorted(props.items()))
    return block + (f"[{inner}]" if props else "") + nbt


def canonical(state: str) -> str:
    """The state with transformable defaults written out and keys sorted, for comparison."""
    block, props, nbt = parse_state(state)
    return format_state(block, defaults(block) | props, nbt)


def turn(direction: str, quarter_turns: int) -> str:
    if direction not in HORIZONTAL:
        return direction
    return HORIZONTAL[(HORIZONTAL.index(direction) + quarter_turns) % 4]


def flip(direction: str) -> str:
    return {"east": "west", "west": "east"}.get(direction, direction)


def _mirror(block: str, props: dict[str, str]) -> dict[str, str]:
    b = block.removeprefix("minecraft:")
    p = dict(props)
    if b.endswith("_stairs"):
        if p["facing"] in ("east", "west"):
            p["facing"] = flip(p["facing"])
            p["shape"] = STAIRS_MIRROR_X.get(p["shape"], p["shape"])
        return p
    if "facing" in p and b not in UNMIRRORED_FACING:
        p["facing"] = flip(p["facing"])
    if b.endswith("_door"):
        p["hinge"] = {"left": "right", "right": "left"}[p["hinge"]]
    if "rotation" in p:
        r = int(p["rotation"])  # Mirror.mirror(rotation, 16), FRONT_BACK
        p["rotation"] = str((16 - (r - 16 if r > 8 else r)) % 16)
    if "orientation" in p:
        front, top = p["orientation"].split("_")
        p["orientation"] = f"{flip(front)}_{flip(top)}"
    if b in RAILS:
        p["shape"] = RAIL_MIRROR_X.get(p["shape"], p["shape"])
    if b not in UNROTATED_SIDES and ("east" in p or "west" in p):
        e, w = p.pop("east", None), p.pop("west", None)
        p |= {k: v for k, v in (("west", e), ("east", w)) if v is not None}
    return p


def _rotate(block: str, props: dict[str, str], k: int) -> dict[str, str]:
    b = block.removeprefix("minecraft:")
    p = dict(props)
    if "facing" in p:
        p["facing"] = turn(p["facing"], k)
    if "axis" in p and k % 2:
        p["axis"] = {"x": "z", "z": "x"}.get(p["axis"], p["axis"])
    if "rotation" in p:
        p["rotation"] = str((int(p["rotation"]) + 4 * k) % 16)
    if "orientation" in p:
        front, top = p["orientation"].split("_")
        p["orientation"] = f"{turn(front, k)}_{turn(top, k)}"
    if b in RAILS:
        for _ in range(k):
            p["shape"] = RAIL_CW90[p["shape"]]
    if b not in UNROTATED_SIDES:
        sides = {d: p.pop(d) for d in HORIZONTAL if d in p}
        p |= {turn(d, k): v for d, v in sides.items()}
    return p


def rotate_state(state: str, quarter_turns: int = 0, mirror_x: bool = False) -> str:
    """The block state after mirroring in x (if asked) and turning clockwise.

    Properties the input omitted are written only where the result differs from the
    default; NBT is kept as written.
    """
    k = quarter_turns % 4
    if not k and not mirror_x:
        return state
    block, props, nbt = parse_state(state)
    base = defaults(block)
    p = base | props
    if mirror_x:
        p = _mirror(block, p)
    if k:
        p = _rotate(block, p, k)
    p = {key: v for key, v in p.items() if key in props or base.get(key) != v}
    return format_state(block, p, nbt)


def rotate_pos(pos: Pos, quarter_turns: int = 0, mirror_x: bool = False) -> Pos:
    """A block position under the transform (StructureTemplate.transform, pivot 0)."""
    x, y, z = pos
    if mirror_x:
        x = -x
    for _ in range(quarter_turns % 4):
        x, z = -z, x
    return x, y, z


def rotate_point(point: tuple[float, float, float], quarter_turns: int = 0,
                 mirror_x: bool = False) -> tuple[float, float, float]:
    """A point in block coordinates (cell (0,0,0) spans [0,1)^3) under the transform."""
    x, y, z = point
    if mirror_x:
        x = 1.0 - x
    for _ in range(quarter_turns % 4):
        x, z = 1.0 - z, x
    return x, y, z


def rotate_yaw(yaw: float, quarter_turns: int = 0, mirror_x: bool = False) -> float:
    """Entity yaw after the transform: StructureTemplate adds the mirror as a delta,
    rotate(r) + (mirror(m) - yRot), with Entity.mirror(FRONT_BACK) = -yaw."""
    y = -yaw if mirror_x else yaw
    y += 90.0 * (quarter_turns % 4)
    return (y + 180.0) % 360.0 - 180.0


Entity = tuple[tuple[float, float, float], str, str]


def rotate_entity(entity: Entity, quarter_turns: int = 0, mirror_x: bool = False) -> Entity:
    """An entity (position, id, SNBT) under the transform.

    Block-attached entities (item frames, paintings, leash knots) are moved by their cell
    and summoned at its centre: they snap to the cell they are summoned in, and the
    point transform would push a position on a cell edge into the next cell. Their
    facing comes from `Facing`/`facing`, not yaw, and is mirrored before it is turned,
    like their cell. (StructureTemplate turns a hanging entity's direction before
    mirroring it, so with both a mirror and an odd turn vanilla would face it off its
    wall.) Other entities get the point transform and a `Rotation` yaw.
    """
    (x, y, z), kind, nbt = entity
    k = quarter_turns % 4
    if not k and not mirror_x:
        return entity
    bare = kind.removeprefix("minecraft:")
    if bare in ATTACHED_ENTITIES:
        if _snbt_get(nbt, "block_pos") is not None:
            raise ValueError(f"{kind}: explicit block_pos is not supported")
        cx, _, cz = rotate_pos((math.floor(x), 0, math.floor(z)), k, mirror_x)
        for key, ids in (("Facing", DATA_3D), ("facing", DATA_2D)):
            raw = _snbt_get(nbt, key)
            if raw is not None:
                d = ids[int(raw.rstrip("bB"))]
                d = turn(flip(d) if mirror_x else d, k)
                nbt = _snbt_set(nbt, key, f"{ids.index(d)}b")
        return (cx + 0.5, y, cz + 0.5), kind, nbt
    pos = rotate_point((x, y, z), k, mirror_x)
    raw = _snbt_get(nbt, "Rotation")
    yaw, pitch = ("0.0f", "0.0f") if raw is None else raw.strip("[]").split(",")
    old = float(yaw.strip().rstrip("fFdD"))
    new = rotate_yaw(old, k, mirror_x)
    if new != old:
        nbt = _snbt_set(nbt, "Rotation", f"[{new:g}f,{pitch.strip()}]")
    return pos, kind, nbt


def rotated(build: Build, quarter_turns: int = 1, mirror_x: bool = False) -> Build:
    """A new Build: every block and entity under the transform, about the origin."""
    return Build({rotate_pos(p, quarter_turns, mirror_x): rotate_state(s, quarter_turns, mirror_x)
                  for p, s in build.blocks.items()},
                 [rotate_entity(e, quarter_turns, mirror_x) for e in build.entities])


def _top_level_keys(nbt: str) -> dict[str, tuple[int, int]]:
    """Span of each top-level value in a compound SNBT, by key."""
    spans = {}
    depth, i, key_start, value_start, key = 0, 0, None, None, None
    while i < len(nbt):
        c = nbt[i]
        if c in "\"'":
            i = nbt.index(c, i + 1)
            while nbt[i - 1] == "\\":
                i = nbt.index(c, i + 1)
        elif c in "{[":
            depth += 1
            if depth == 1:
                key_start = i + 1
        elif c in "}]":
            if depth == 1 and key is not None:
                spans[key] = (value_start, i)
            depth -= 1
        elif depth == 1 and c == ":" and key is None:
            key = nbt[key_start:i].strip().strip("\"'")
            value_start = i + 1
        elif depth == 1 and c == ",":
            if key is not None:
                spans[key] = (value_start, i)
            key, key_start = None, i + 1
        i += 1
    return spans


def _snbt_get(nbt: str, key: str) -> str | None:
    span = _top_level_keys(nbt).get(key)
    return None if span is None else nbt[span[0]:span[1]].strip()


def _snbt_set(nbt: str, key: str, value: str) -> str:
    span = _top_level_keys(nbt).get(key)
    if span:
        return nbt[:span[0]] + value + nbt[span[1]:]
    if not nbt.strip():
        return f"{{{key}:{value}}}"
    body = nbt.strip()[1:-1].strip()
    return "{" + (body + "," if body else "") + f"{key}:{value}" + "}"
