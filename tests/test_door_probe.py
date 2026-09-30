import json
import re

import pytest

from redstone.door_probe import (KNOWN_BLOCKS, MARGIN, OCC_RESET, OTHER, cells, door_functions,
                                 hallway_probe_functions, occupancy_functions, read_flags, read_hallway,
                                 tag_files, visible_cells, write_tags)
from redstone.harness import PROBE_CHUNK

# A 3x3 door: a hallway 3 wide, 3 high and 5 deep in a quartz shell, the frame across
# its middle, a lever on the east wall.
HALLWAY = [((1, 1, 0), (3, 3, 4))]
FRAME = cells([((1, 1, 2), (3, 3, 2))])
LEVER = (5, 2, 1)
BOUNDS = ((0, 0, 0), (8, 4, 6))
PLOT = (48, 32, 48)
SURFACE = visible_cells(HALLWAY) - cells(HALLWAY)
DOOR = ["smooth_quartz"]
WALLS = ["smooth_quartz", "quartz_bricks"]

OUR_TAGS = {"#redstone_ai:door_material", "#redstone_ai:surface_material", "#minecraft:air"}
COORD = r"~-?\d+ ~-?\d+ ~-?\d+"
STORAGE_PATH = re.compile(r"storage redstone_ai:(probe h(\.(c|m|n)\d+|\.e)?|occ (any|circ|door|shell)\.c\d+|occ e) ")


def lines_of(chunks):
    return [line for chunk in chunks for line in chunk.splitlines()]


def assert_valid(lines):
    for line in lines:
        assert line.startswith(("execute ", "data modify storage ")), line
        for block in re.findall(r"(?<![#\w])minecraft:([a-z_]+)", line):
            assert block in KNOWN_BLOCKS, line
        assert set(re.findall(r"#[a-z_]+:[a-z_]+", line)) <= OUR_TAGS, line
        for pos in re.findall(r"(?:block|positioned) (\S+ \S+ \S+)", line):
            assert re.fullmatch(COORD, pos), line
        assert STORAGE_PATH.search(line), line


def occupancy():
    return occupancy_functions(BOUNDS, HALLWAY, FRAME | {LEVER}, SURFACE, DOOR, WALLS, PLOT)


def test_tags_are_block_ids_of_this_version(tmp_path):
    tags = tag_files(DOOR, WALLS)
    assert json.loads(tags["surface_material"]) == {"values": ["minecraft:smooth_quartz", "minecraft:quartz_bricks"]}
    write_tags(tmp_path, tags)
    assert json.loads((tmp_path / "data/redstone_ai/tags/block/door_material.json").read_text()) == {
        "values": ["minecraft:smooth_quartz"]}
    for bad in (["smooth_quartzz"], ["piston[facing=up]"]):
        with pytest.raises(ValueError):
            tag_files(bad, [])


def test_visible_cells_are_the_hallway_and_its_face_neighbours():
    visible = visible_cells(HALLWAY)
    assert len(visible) == 45 + 2 * 15 + 2 * 15 + 2 * 9
    assert (0, 2, 2) in visible and (0, 0, 2) not in visible
    assert visible_cells(HALLWAY, [((1, 1, 5), (3, 3, 7))]) == cells(HALLWAY) | cells([((1, 1, 5), (3, 3, 7))])


def test_hallway_probe_codes_each_cell_last_match_wins():
    chunks, probed = hallway_probe_functions(HALLWAY)
    assert len(chunks) == 1 and probed == sorted(visible_cells(HALLWAY))
    lines = lines_of(chunks)
    assert_valid(lines)
    assert lines[0] == "data modify storage redstone_ai:probe h set value {}"
    i = probed.index((2, 2, 2))
    cell = [line for line in lines if f"h.c{i} " in line or f"h.m{i} " in line]
    assert cell == [
        f"data modify storage redstone_ai:probe h.c{i} set value 9",
        f"execute if block ~2 ~2 ~2 minecraft:piston_head run data modify storage redstone_ai:probe h.c{i} set value 4",
        f"execute if block ~2 ~2 ~2 minecraft:moving_piston run data modify storage redstone_ai:probe h.c{i} set value 3",
        f"execute if block ~2 ~2 ~2 #redstone_ai:surface_material run data modify storage redstone_ai:probe h.c{i} set value 2",
        f"execute if block ~2 ~2 ~2 #redstone_ai:door_material run data modify storage redstone_ai:probe h.c{i} set value 1",
        f"execute if block ~2 ~2 ~2 #minecraft:air run data modify storage redstone_ai:probe h.c{i} set value 0",
        f"execute if block ~2 ~2 ~2 minecraft:moving_piston run data modify storage redstone_ai:probe h.m{i} set from block ~2 ~2 ~2",
    ]
    assert lines[-2:] == [
        "execute positioned ~1 ~1 ~0 align xyz store result storage redstone_ai:probe h.n0 int 1 "
        "if entity @e[type=!player,tag=!rig_dummy,dx=2,dy=2,dz=4]",
        "execute positioned ~1 ~1 ~0 align xyz as @e[type=!player,tag=!rig_dummy,dx=2,dy=2,dz=4] "
        "run data modify storage redstone_ai:probe h.e append from entity @s",
    ]


def test_probe_splits_into_functions_below_the_command_chain_limit():
    chunks, probed = hallway_probe_functions([((0, 0, 0), (39, 19, 9))])
    sizes = [len(c.splitlines()) for c in chunks]
    assert len(chunks) > 1 and max(sizes) <= PROBE_CHUNK
    assert sum(sizes) == 1 + 7 * len(probed) + 2
    assert chunks[0].startswith("data modify storage redstone_ai:probe h set value {}")
    assert all(" h set value" not in c for c in chunks[1:])


def test_occupancy_region_is_grown_clamped_and_guarded_by_a_shell():
    occ, occ_hall, region, shell = occupancy()
    lo, hi = region[0], region[-1]
    # The build sits at the plot's corner, so the low sides have no margin to grow into.
    assert (lo, hi) == ((0, 0, 0), (8 + MARGIN, 4 + MARGIN, 6 + MARGIN))
    shell_cells = {region[i] for i in shell}
    assert all(not (0 <= x <= 8 and 0 <= y <= 4 and 0 <= z <= 6) for x, y, z in shell_cells)
    assert (10, 3, 3) in shell_cells and (4, 6, 3) in shell_cells and (4, 0, 3) not in shell_cells
    squeezed = occupancy_functions(((0, 0, 0), (47, 4, 6)), HALLWAY, set(), set(), DOOR, WALLS, PLOT)
    assert squeezed[2][0][0] == 0 and squeezed[2][-1][0] == 47


def test_occupancy_flags_every_cell_but_frame_and_lever_and_hallway_only_in_occ_hall():
    occ, occ_hall, region, shell = occupancy()
    body, hall = lines_of(occ), lines_of(occ_hall)
    assert_valid(body + hall)

    def flagged(lines):
        return {int(i) for line in lines for i in re.findall(r" any\.c(\d+) ", line)}
    assert {region[i] for i in flagged(body)} == set(region) - cells(HALLWAY) - {LEVER}
    assert {region[i] for i in flagged(hall)} == cells(HALLWAY) - FRAME
    assert {int(i) for line in body for i in re.findall(r" shell\.c(\d+) ", line)} == shell
    assert body[-1] == ("execute positioned ~0 ~0 ~0 align xyz as @e[type=!player,tag=!rig_dummy,dx=10,dy=6,dz=8] "
                        "run data modify storage redstone_ai:occ e append from entity @s")


def test_surface_material_is_circuitry_away_from_the_surfaces():
    occ, _, region, _ = occupancy()
    body = lines_of(occ)

    def cell(pos):
        i = region.index(pos)
        return [line for line in body if f".c{i} " in line]
    wall, inside = cell((0, 2, 2)), cell((7, 2, 5))
    assert wall[1] == ("execute unless block ~0 ~2 ~2 #minecraft:air unless block ~0 ~2 ~2 #redstone_ai:door_material "
                       "unless block ~0 ~2 ~2 #redstone_ai:surface_material unless block ~0 ~2 ~2 minecraft:moving_piston "
                       f"run data modify storage redstone_ai:occ circ.c{region.index((0, 2, 2))} set value 1b")
    assert "surface_material" not in inside[1]
    moved = 'unless data block ~0 ~2 ~2 {source:0b,blockState:{Name:"minecraft:%s"}}'
    assert all(moved % m in wall[2] for m in ("smooth_quartz", "quartz_bricks"))
    assert "quartz_bricks" not in inside[2] and "smooth_quartz" in inside[2]
    assert inside[4] == ("execute if block ~7 ~2 ~5 minecraft:moving_piston if data block ~7 ~2 ~5 "
                         '{source:0b,blockState:{Name:"minecraft:smooth_quartz"}} '
                         f"run data modify storage redstone_ai:occ door.c{region.index((7, 2, 5))} set value 1b")


def test_door_functions_and_reset():
    probe, _ = hallway_probe_functions(HALLWAY)
    occ, occ_hall, _, _ = occupancy()
    assert set(door_functions(probe, occ, occ_hall)) == {"hall0", "occ0", "occ_hall0", "occ_reset"}
    assert OCC_RESET.splitlines() == [f"data modify storage redstone_ai:occ {k} set value {v}"
                                      for k, v in (("any", "{}"), ("circ", "{}"), ("door", "{}"),
                                                   ("shell", "{}"), ("e", "[]"))]


def test_read_hallway_parses_codes_moving_pistons_and_entity_counts():
    reply = ('Storage redstone_ai:probe has the following contents: {s: {b0: 1}, h: {c0: 0, c1: 3, '
             'm1: {blockState: {Name: "minecraft:smooth_quartz"}, extending: 1b, facing: 2b, '
             'id: "minecraft:piston", keepPacked: 0b, progress: 0.5f, source: 0b, x: 130, y: 57, z: 131}, '
             'c2: 1, m3: {blockState: {Name: "minecraft:sticky_piston", Properties: {extended: "true", facing: "north"}}, '
             'extending: 0b, facing: 3b, progress: 0.0f, source: 1b}, c3: 3, n0: 2, e: [{Pos: [1.0d, 2.0d, 3.0d]}]}}')
    codes, moving, counts = read_hallway(reply, 5, 1)
    assert codes == [0, 3, 1, 3, OTHER]
    assert moving == {1: {"progress": 0.5, "extending": True, "source": False, "facing": "north", "block": "minecraft:smooth_quartz"},
                      3: {"progress": 0.0, "extending": False, "source": True, "facing": "south", "block": "minecraft:sticky_piston"}}
    assert counts == [2]


def test_read_flags():
    reply = ("Storage redstone_ai:occ has the following contents: {any: {c0: 1b, c12: 1b}, circ: {c12: 1b}, "
             "door: {}, e: [], shell: {c3: 1b}}")
    assert read_flags(reply) == {"any": {0, 12}, "circ": {12}, "door": set(), "shell": {3}}
