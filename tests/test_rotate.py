import functools

import pytest

from redstone import fileformat
from redstone.build import Build
from redstone.library import paths
from redstone.rotate import (RAIL_CW90, canonical, rotate_entity, rotate_pos, rotate_state, rotate_yaw,
                             rotated)

FRONT_AND_TOP = ["down_east", "down_north", "down_south", "down_west", "up_east", "up_north", "up_south",
                 "up_west", "west_up", "east_up", "north_up", "south_up"]
EXTRA = [
    *(f"oak_stairs[facing={f},half=bottom,shape={s}]" for f in ("north", "east", "south", "west")
      for s in ("straight", "inner_left", "inner_right", "outer_left", "outer_right")),
    "oak_stairs", "oak_door", "oak_door[facing=east,half=upper,hinge=right]", "oak_trapdoor",
    *(f"oak_sign[rotation={r}]" for r in range(16)), "oak_sign", "white_banner", "skeleton_skull",
    "oak_hanging_sign", "oak_wall_sign[facing=west]", "creeper_wall_head",
    *(f"rail[shape={s}]" for s in RAIL_CW90), "rail", "powered_rail[shape=east_west,powered=true]",
    "oak_fence[east=true,north=true]", "cobblestone_wall[north=tall,up=true,west=low]",
    "glass_pane[south=true]", "iron_bars[east=true,west=true]",
    "vine[north=true,up=true]", "glow_lichen[down=true,east=true,up=false]", "sculk_vein[west=true]",
    "brown_mushroom_block[east=false,up=false]", "tripwire[north=true]",
    "redstone_wire[east=up,north=side,power=7]",
    "anvil", "anvil[facing=east]", "fire[east=true]", "chorus_plant[north=true,down=true]",
    "oak_log[axis=x]", "oak_log", "nether_portal", "nether_portal[axis=z]", "chain[axis=z]",
    *(f"crafter[orientation={o}]" for o in FRONT_AND_TOP), "crafter", "jigsaw[orientation=up_west]",
    "observer", "hopper", "hopper[facing=east]", "lightning_rod", "end_rod[facing=west]",
    "lever[face=ceiling,facing=south]", "chest[facing=north,type=left]",
    'oak_sign[rotation=3]{front_text:{messages:["\\"a[b]\\"","","",""]}}',
]


@functools.cache
def states() -> list[str]:
    found = {s for p in paths() for s in fileformat.load(p).build.blocks.values()}
    return sorted(found) + EXTRA


def test_library_is_covered():
    assert len(states()) > 100


def test_four_quarter_turns_are_identity():
    for s in states():
        t = s
        for _ in range(4):
            t = rotate_state(t, 1)
        assert canonical(t) == canonical(s), s
        assert rotate_state(s, 4) == s


def test_mirror_twice_is_identity():
    for s in states():
        assert canonical(rotate_state(rotate_state(s, 0, True), 0, True)) == canonical(s), s


def test_turns_compose():
    for s in states():
        for a in range(4):
            for b in range(4):
                assert canonical(rotate_state(rotate_state(s, a), b)) == canonical(rotate_state(s, a + b)), (s, a, b)


def test_mirror_then_turn_is_turn_back_then_mirror():
    # Vanilla breaks this group law for anvils (no mirror), stairs (partial mirror table).
    for s in states():
        if "anvil" in s or "stairs" in s:
            continue
        for k in range(4):
            assert canonical(rotate_state(s, k, True)) == canonical(rotate_state(rotate_state(s, -k), 0, True)), (s, k)


@pytest.mark.parametrize("state, turns, mirror, want", [
    ("minecraft:repeater[delay=2,facing=north]", 1, False, "minecraft:repeater[delay=2,facing=east]"),
    ("repeater[facing=west,locked=true]", 3, False, "repeater[facing=south,locked=true]"),
    ("comparator[facing=east,mode=subtract]", 0, True, "comparator[facing=west,mode=subtract]"),
    ("sticky_piston[facing=up]", 1, True, "sticky_piston[facing=up]"),
    ("observer", 1, False, "observer[facing=west]"),
    ("observer", 2, False, "observer[facing=north]"),
    ("barrel", 1, False, "barrel[facing=east]"),
    ("hopper", 1, False, "hopper"),
    ("stone", 3, True, "stone"),
    ("redstone_wire[east=up,west=side]", 1, False, "redstone_wire[north=side,south=up]"),
    ("redstone_wire[east=up,north=side,power=7]", 2, False, "redstone_wire[power=7,south=side,west=up]"),
    ("redstone_wire[east=up,north=side]", 0, True, "redstone_wire[north=side,west=up]"),
    ("oak_fence[north=true]", 3, False, "oak_fence[west=true]"),
    ("cobblestone_wall[north=tall,up=true]", 1, False, "cobblestone_wall[east=tall,up=true]"),
    ("vine[north=true,up=true]", 1, False, "vine[east=true,up=true]"),
    ("glow_lichen[down=true,west=true]", 1, False, "glow_lichen[down=true,north=true]"),
    ("fire[east=true]", 1, False, "fire[east=true]"),
    ("oak_log[axis=x]", 1, False, "oak_log[axis=z]"),
    ("oak_log[axis=x]", 2, False, "oak_log[axis=x]"),
    ("nether_portal", 1, False, "nether_portal[axis=z]"),
    ("oak_sign", 1, False, "oak_sign[rotation=12]"),
    ("oak_sign[rotation=3]", 0, True, "oak_sign[rotation=13]"),
    ("oak_sign[rotation=8]", 0, True, "oak_sign[rotation=8]"),
    ("skeleton_skull", 3, False, "skeleton_skull[rotation=12]"),
    # BaseRailBlock tables for CLOCKWISE_180 and COUNTERCLOCKWISE_90, and FRONT_BACK.
    ("rail[shape=south_east]", 2, False, "rail[shape=north_west]"),
    ("rail[shape=ascending_north]", 2, False, "rail[shape=ascending_south]"),
    ("rail[shape=ascending_east]", 3, False, "rail[shape=ascending_north]"),
    ("rail[shape=south_west]", 3, False, "rail[shape=south_east]"),
    ("rail[shape=north_east]", 3, False, "rail[shape=north_west]"),
    ("rail", 1, False, "rail[shape=east_west]"),
    ("detector_rail[shape=ascending_north]", 0, True, "detector_rail[shape=ascending_north]"),
    ("rail[shape=north_east]", 0, True, "rail[shape=north_west]"),
    ("activator_rail[shape=ascending_west]", 0, True, "activator_rail[shape=ascending_east]"),
    # StairBlock.mirror FRONT_BACK: z-facing stairs are untouched, inner shapes keep their side.
    ("oak_stairs[facing=north,shape=outer_left]", 0, True, "oak_stairs[facing=north,shape=outer_left]"),
    ("oak_stairs[facing=east,shape=outer_left]", 0, True, "oak_stairs[facing=west,shape=outer_right]"),
    ("oak_stairs[facing=east,shape=inner_left]", 0, True, "oak_stairs[facing=west,shape=inner_left]"),
    ("oak_stairs[facing=east,shape=outer_left]", 1, False, "oak_stairs[facing=south,shape=outer_left]"),
    ("oak_door[facing=north]", 0, True, "oak_door[facing=north,hinge=right]"),
    ("oak_door[facing=east,hinge=right]", 0, True, "oak_door[facing=west,hinge=left]"),
    ("anvil[facing=east]", 0, True, "anvil[facing=east]"),
    ("anvil[facing=east]", 1, False, "anvil[facing=south]"),
    ("chest[facing=east,type=left]", 0, True, "chest[facing=west,type=left]"),
    ("crafter", 1, False, "crafter[orientation=east_up]"),
    ("crafter[orientation=up_west]", 1, False, "crafter[orientation=up_north]"),
    ("crafter[orientation=down_east]", 0, True, "crafter[orientation=down_west]"),
    ("oak_sign[rotation=3]{x:[1]}", 1, False, "oak_sign[rotation=7]{x:[1]}"),
])
def test_hand_checked(state, turns, mirror, want):
    assert rotate_state(state, turns, mirror) == want


def test_positions_match_structure_template():
    # StructureTemplate.transform with pivot 0: CW90 (-z, x), 180 (-x, -z), CCW90 (z, -x).
    p = (2, 5, 7)
    assert [rotate_pos(p, k) for k in range(4)] == [(2, 5, 7), (-7, 5, 2), (-2, 5, -7), (7, 5, -2)]
    assert rotate_pos(p, 1, True) == (-7, 5, -2)
    assert rotate_pos((0, 0, -1), 1) == (1, 0, 0)  # north of origin goes east, like facing


def test_rotated_build_keeps_blocks_next_to_what_they_face():
    b = Build().place((0, 1, 0), "repeater[facing=south]").place((0, 1, 1), "stone").place((0, 1, -1), "redstone_block")
    for k in range(4):
        for m in (False, True):
            r = rotated(b, k, m)
            (pos, state), = [(p, s) for p, s in r.blocks.items() if "repeater" in s]
            facing = state.split("facing=")[1].rstrip("]")
            step = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0)}[facing]
            behind = tuple(a + d for a, d in zip(pos, step))  # repeater input side
            assert r.blocks[behind] == "minecraft:stone"
    assert b.blocks[(0, 1, 0)] == "minecraft:repeater[facing=south]"


def test_yaw_follows_structure_template():
    assert rotate_yaw(0, 1) == 90  # facing south turns to face west
    assert rotate_yaw(90, 0, True) == -90  # west mirrored in x faces east
    assert rotate_yaw(90, 1, True) == 0  # west, mirrored east, turned south


def test_free_entity_moves_by_point_and_gets_yaw():
    e = ((1.5, 1.0, 3.5), "minecraft:tnt_minecart", "")
    assert rotate_entity(e, 1) == ((-2.5, 1.0, 1.5), "minecraft:tnt_minecart", "{Rotation:[90f,0.0f]}")
    pos, _, nbt = rotate_entity(((0.5, 1, 0.5), "armor_stand", "{Rotation:[90f,10f],Tags:[\"a\"]}"), 2)
    assert pos == (0.5, 1, 0.5) and nbt == "{Rotation:[-90f,10f],Tags:[\"a\"]}"
    t = e
    for _ in range(4):
        t = rotate_entity(t, 1)
    assert t[0] == e[0]


def test_item_frame_keeps_its_cell_and_turns_its_facing():
    nbt = '{Facing:2b,Item:{id:"minecraft:stick",count:1},ItemRotation:2b}'
    pos, kind, out = rotate_entity(((0.0, 1.5, 0.0), "minecraft:item_frame", nbt), 1)
    assert pos == (0.5, 1.5, 0.5) and out == nbt.replace("Facing:2b", "Facing:5b")  # north -> east
    pos, _, out = rotate_entity(((4.5, 1.5, 1.5), "item_frame", "{Facing:5b}"), 1, True)
    assert pos == (-0.5, 1.5, -3.5) and out == "{Facing:2b}"  # east, mirrored west, turned north
    pos, _, out = rotate_entity(((2.0, 1.0, 0.0), "painting", "{facing:2b}"), 2)
    assert pos == (-1.5, 1.0, 0.5) and out == "{facing:0b}"  # 2D: north -> south


def test_block_pos_is_refused():
    with pytest.raises(ValueError):
        rotate_entity(((0, 1, 0), "item_frame", "{block_pos:[I;0,1,0]}"), 1)


def test_rotated_library_builds_have_no_collisions():
    for p in paths():
        b = fileformat.load(p).build
        for k in range(4):
            r = rotated(b, k, k == 3)
            assert len(r.blocks) == len(b.blocks) and len(r.entities) == len(b.entities)
