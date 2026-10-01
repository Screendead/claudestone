"""The door harness offline: the `door:` section, its lint, the plan's functions, the
door_cycle test against a fake Rig that simulates the 2x2 proof door, and the plumbing it
needs (chunked build functions, the update pass, block tags, the bigdoor plot)."""

import copy
import json
import re

import pytest

from redstone import door, door_timing as dt, fileformat, remote, spec as spec_module
from redstone.build import Build, write_datapack
from redstone.door_probe import FACING, OCC
from redstone.harness import PROBE_CHUNK, clear_commands
from redstone.library import path_of
from redstone.plots import BIGDOOR, MAIN, PLOTS, plot_for
from scripts import lint as lint_module
from scripts import package as package_module

SPEC = path_of("door_2x2_flush_harness_check")
LEFT, RIGHT = [(4, 1, 1), (4, 2, 1)], [(7, 1, 1), (7, 2, 1)]
FRAME = [(5, 1, 1), (6, 1, 1), (5, 2, 1), (6, 2, 1)]


@pytest.fixture(autouse=True)
def traces(tmp_path, monkeypatch):
    monkeypatch.setattr(spec_module, "TRACE_DIR", tmp_path)
    return tmp_path


def proof():
    return fileformat.load(SPEC)


def with_door(**changes):
    s = proof()
    s.door = copy.deepcopy(s.door) | changes
    return s


# ---- the section ------------------------------------------------------------------------

def test_geometry_leaves_the_hallway_ends_open():
    frame, hallway, surface = door.geometry(proof().door)
    assert sorted(frame) == sorted(FRAME)
    assert hallway == {(x, y, z) for x in (5, 6) for y in (1, 2) for z in (0, 1, 2)}
    # Walls, floor and ceiling beside the hallway, but nothing beyond its two ends.
    assert len(surface) == 24 and not any(z in (-1, 3) for _, _, z in surface)
    assert {(4, 1, 1), (7, 2, 1), (5, 0, 0), (6, 3, 2)} <= surface


@pytest.mark.parametrize("facing,normal", [("east", 0), ("west", 0), ("up", 1), ("down", 1), ("south", 2)])
def test_geometry_of_each_facing(facing, normal):
    d = {"doorway": {"origin": [4, 4, 4], "width": 3, "height": 2, "facing": facing}, "depth": 2}
    frame, hallway, surface = door.geometry(d)
    assert len(frame) == 6 and len({p[normal] for p in frame}) == 1
    assert len(hallway) == 6 * 5 and {p[normal] for p in hallway} == set(range(2, 7))
    assert all(2 <= p[normal] <= 6 for p in surface)
    # Hallway.of takes the frame as one cross-section along the facing.
    dt.Hallway.of(hallway, frame, facing, surface)


def test_sixteen_by_sixteen_reads_960_cells_a_tick_in_one_function():
    s = proof()
    s.door = {"doorway": {"origin": [20, 10, 30], "width": 16, "height": 16, "facing": "north"}}
    _, hallway, surface = door.geometry(s.door)
    assert (len(hallway), len(surface)) == (768, 192)
    from redstone.door_probe import hallway_probe_functions
    chunks, probed = hallway_probe_functions([(min(hallway), max(hallway))], [(p, p) for p in surface])
    assert len(probed) == 960 and len(chunks) == 1
    assert len(chunks[0].splitlines()) < PROBE_CHUNK


def test_door_section_round_trips_through_dump(tmp_path):
    s = proof()
    s.update_pass = "unobserved"
    out = tmp_path / "x.redstone.yaml"
    out.write_text(fileformat.dump(s))
    back = fileformat.load(out)
    assert back.door == s.door and back.update_pass == "unobserved" and back.tests == s.tests
    assert back.build.blocks == s.build.blocks and back.fixtures == s.fixtures
    assert "origin: [5, 1, 1]" in out.read_text()
    assert "update_pass" not in fileformat.dump(proof())


def test_the_proof_spec_lints_clean_and_its_folder_is_the_bigdoor_plot():
    assert plot_for(SPEC) == BIGDOOR
    assert lint_module.lint(proof()) == []


@pytest.mark.parametrize("change,message", [
    ({"doorway": {"origin": [5, 1], "width": 2, "height": 2, "facing": "north"}}, "is not [x, y, z]"),
    ({"doorway": {"origin": [5, 1, 1], "width": 0, "height": 2, "facing": "north"}}, "width 0"),
    ({"doorway": {"origin": [5, 1, 1], "width": 2, "height": 2, "facing": "northish"}}, "facing 'northish'"),
    ({"doorway": {"origin": [5, 0, 1], "width": 2, "height": 2, "facing": "north"}}, "outside the"),
    ({"depth": 0}, "depth 0"),
    ({"tier": "MEGA"}, "tier 'MEGA'"),
    ({"input": "nope"}, "input 'nope'"),
    ({"repeater": "nope"}, "repeater 'nope'"),
    ({"surface": ["white_concret"]}, "not plain block ids"),
    ({"initial": "open"}, "must be placed closed"),
    ({"blocks": ["stone"]}, "not door material"),
    ({"colour": "red"}, "unknown key 'colour'"),
    ({"outer_surface": [[0, 0, 0]]}, "outer_surface"),
])
def test_lint_rejects_bad_door_sections(change, message):
    found = lint_module.lint(with_door(**change))
    assert any(message in m for m in found), found
    with pytest.raises(ValueError):
        door.plan(with_door(**change), BIGDOOR.size)


def test_lint_checks_the_input_fixture():
    s = proof()
    rep = s.named["rep"]
    s.build.blocks[rep] = "minecraft:repeater[facing=south,delay=2]"
    assert any("not a repeater[delay=1]" in m for m in lint_module.lint(s))
    s = proof()
    s.fixtures.discard(s.named["rep"])
    assert any("must be a fixture" in m for m in lint_module.lint(s))
    s = proof()
    s.build.blocks[s.named["rep"]] = "minecraft:repeater[facing=north]"
    assert any("is not behind repeater" in m for m in lint_module.lint(s))
    s = proof()
    s.build.place((6, 0, 5), "redstone_lamp")
    assert any("also powers minecraft:redstone_lamp" in m for m in lint_module.lint(s))
    s = proof()
    s.build.place((5, 1, 0), "stone")
    assert any("hallway cell (5, 1, 0) holds" in m for m in lint_module.lint(s))


def test_lint_checks_door_cycle_keys():
    s = proof()
    s.tests = [{"name": "t", "door_cycle": {"cycles": 0, "reading": "Q", "max_open": -1, "speed": 1, "quiet": 0}}]
    found = lint_module.lint(s)
    for message in ("cycles 0", "reading 'Q'", "max_open -1", "unknown key 'speed'", "quiet 0"):
        assert any(message in m for m in found), (message, found)
    s.door = None
    s.tests = [{"name": "t", "door_cycle": {}}]
    assert any("needs a door: section" in m for m in lint_module.lint(s))
    s = proof()
    s.update_pass = "some"
    assert any("update_pass 'some'" in m for m in lint_module.lint(s))


# ---- plan --------------------------------------------------------------------------------

def test_plan_functions_and_the_static_cells():
    p = door.plan(proof(), BIGDOOR.size)
    assert p.door_material == ["smooth_quartz"] and p.surface_material == ["white_concrete"]
    assert p.static == set(FRAME) | {(5, 0, 4), (5, 0, 5)}
    assert p.hall_fns == ["hall0"] and p.track_fns == ["occ_track0"] and p.occ_fns == ["occ_entities"]
    assert p.functions["door_rep"].startswith("execute if block ~5 ~0 ~4 minecraft:repeater[powered=true] ")
    assert all(len(body.splitlines()) <= PROBE_CHUNK for body in p.functions.values())
    track = p.functions["occ_track0"]
    # Each piston's line is tracked every tick, but never the hallway or the static cells.
    assert "~4 ~1 ~1" in track and "~9 ~2 ~1" in track and "~5 ~1 ~1 " not in track
    assert "~0 ~0 ~3 " not in track  # dust off every piston's line
    fired = [l for l in track.splitlines() if "fired.p" in l]
    assert fired[0] == ("execute unless block ~3 ~1 ~1 minecraft:sticky_piston[facing=east,extended=true] run "
                        f"data modify storage {OCC} fired.p0 set value 1b")
    assert len(fired) == 4
    assert json.loads(p.tags["door_material"]) == {"values": ["minecraft:smooth_quartz"]}


# ---- a fake world ------------------------------------------------------------------------

def moving(block, progress, extending, source, face):
    """A moving_piston as 26.3 prints it (seen live): a default state is a bare id."""
    state = (f'{{Name: "minecraft:{block}", Properties: {{facing: "{face}", short: "false", type: "sticky"}}}}'
             if block == "piston_head" else f'"minecraft:{block}"')
    return (f'{{blockState: {state}, components: {{}}, x: 377, facing: {FACING.index(face)}b, progress: {progress}f, '
            f'y: 57, z: 211, source: {int(source)}b, id: "minecraft:piston", extending: {int(extending)}b}}')


class DoorWorld:
    """The 2x2 proof door: the fixture repeater switches `lead` ticks after the drive, and
    the pistons move `delay` ticks after that (repeater 2 + torch 2), landing 2 later.
    `zero_tick` makes the opening a 0-tick pull (no head in the wall the tick before)."""

    def __init__(self, plan, lead=2, delay=4, start_open=False, zero_tick=False, flags=None, entities=None,
                 rest=None):
        self.plan, self.lead, self.delay, self.zero_tick = plan, lead, delay, zero_tick
        self.changes: list[tuple[int, bool]] = []  # (tick of the drive, input on)
        self.start_open, self.flags, self.entities = start_open, flags, entities or []
        self.rest = rest or {}  # block ids by cell, what the at-rest scan sees

    def rep(self, tick):
        on = False
        for at, v in self.changes:
            if tick >= at + self.lead:
                on = v
        return on

    def cells(self, tick) -> dict:
        """Code or moving_piston text of each wall and frame cell; anything else is hallway
        air or wall."""
        state = "open" if self.start_open else "closed"
        since = None
        for at, v in self.changes:
            t0 = at + self.lead + self.delay
            if tick >= t0:
                state, since = ("open" if v != self.start_open else "closed"), tick - t0
        out = {}
        sides = [(LEFT, "east", (5,)), (RIGHT, "west", (6,))]
        for ring, face, _ in sides:
            for pos in ring:
                frame = (pos[0] + (1 if face == "east" else -1), pos[1], pos[2])
                if since is None or since >= 2:
                    out[pos], out[frame] = (1, 0) if state == "open" else (4, 1)
                    if state == "closed" and self.zero_tick:
                        out[pos] = 0
                elif state == "open":
                    out[pos], out[frame] = moving("smooth_quartz", since / 2, False, False, face), 0
                else:
                    out[pos] = moving("piston_head", since / 2, True, True, face)
                    out[frame] = moving("smooth_quartz", since / 2, True, False, face)
        return out


class FakeDoorRig:
    def __init__(self, world):
        # The main plot: other plots write to a status sign on main.
        self.world, self.plot, self.heading, self.levels = world, MAIN.name, [], {}
        self.origin, self.size, self.tick = BIGDOOR.origin, BIGDOOR.size, 0
        self.calls: list[tuple[int, tuple]] = []
        self.drives: list[tuple[int, tuple, bool]] = []
        self.runs: list[str] = []

    def load(self, build, probe=None, drivers=frozenset(), **kw):
        self.loaded, self.kw = build, kw

    def abs(self, pos):
        return " ".join(map(str, pos))

    def step(self, n=1):
        self.tick += n

    def snapshot(self):
        return {}

    def drive(self, pos, on):
        self.drives.append((self.tick, pos, on))
        if not self.world.changes or self.world.changes[-1][0] != self.tick:
            self.world.changes.append((self.tick, on))

    def use(self, pos):
        self.drive(pos, not (self.world.changes and self.world.changes[-1][1]))

    def run(self, command):
        """The at-rest scan's commands, answered from world.rest."""
        self.runs.append(command)
        rel = lambda xyz: tuple(int(c) - o for c, o in zip(xyz, self.origin))
        nums = re.findall(r"-?\d+", command)
        if command.startswith("execute if blocks "):
            lo, hi = rel(nums[0:3]), rel(nums[3:6])
            inside = any(all(a <= c <= b for a, c, b in zip(lo, p, hi)) for p in self.world.rest)
            return "Test failed" if inside else "Test passed"
        if command.startswith("execute unless block "):
            block = self.world.rest.get(rel(nums[0:3]))
            plan = self.world.plan
            if block is None or ("door_material" in command and block in plan.door_material) or (
                    "surface_material" in command and block in plan.surface_material):
                return "Test failed"
            return "Test passed"
        return ""

    def command(self, command):
        return True, ""

    def call(self, functions, read=None):
        self.calls.append((self.tick, tuple(functions)))
        if read == "redstone_ai:probe h":
            return self.hallway()
        if read == "redstone_ai:occ e":
            found, self.world.entities = self.world.entities, []
            return "Storage redstone_ai:occ has the following contents: [" + ", ".join(found) + "]"
        if read == "redstone_ai:occ":
            return "Storage redstone_ai:occ has the following contents: " + (self.world.flags or "{any: {}}")
        return ""

    def hallway(self):
        plan, cells = self.world.plan, self.world.cells(self.tick)
        parts = []
        for i, pos in enumerate(plan.probed):
            v = cells.get(pos, 2 if pos in plan.surface else 0)
            if isinstance(v, str):
                parts += [f"c{i}: 3", f"m{i}: {v}"]
            else:
                parts.append(f"c{i}: {v}")
        parts += ["n0: 0", "e: []"] + (["rep: 1"] if self.world.rep(self.tick) else [])
        return "Storage redstone_ai:probe has the following contents: {" + ", ".join(parts) + "}"


def run_cycle(world_kw=None, cycle=None, spec=None):
    s = spec or proof()
    if cycle is not None:
        s.tests = [{"name": "cycle", "door_cycle": cycle}]
    world = DoorWorld(door.plan(s, BIGDOOR.size), **(world_kw or {}))
    rig = FakeDoorRig(world)
    return spec_module.run(rig, s, s.tests[0]), rig


# ---- door_cycle --------------------------------------------------------------------------

def test_door_cycle_times_the_proof_door_under_each_reading(traces):
    result, rig = run_cycle()
    d = result["door"]
    assert d["open"] == {"R": 6, "H1": 4, "R1": 6} and d["close"] == {"R": 6, "H1": 6, "R1": 6}
    assert (d["open_visible"], d["close_visible"]) == (6, 6)
    assert d["tier"] == "SUPER" and d["seamless"] == {c: "L" for c in dt.COLUMNS}
    assert d["probe_cells"] == 36 and len(d["cycles"]) == 2
    assert d["cycles"][0]["open"]["lead"] == 2
    assert door.summary(d).startswith("open 6 (R 6, H1 4, R1 6; visible 6), close 6")
    # The data pack carries the door functions and the two tags.
    assert {"hall0", "occ_entities", "occ_track0", "door_rep"} <= set(rig.kw["functions"]) and set(rig.kw["tags"]) == {
        "door_material", "surface_material"}
    trace = json.loads((traces / "door_2x2_flush_harness_check" / "cycle.json").read_text())
    ops = trace["door"]["ops"]
    assert [o["kind"] for o in ops] == ["open", "close", "open", "close"]
    first = ops[0]
    # Per-tick deltas: nothing changes until the pistons start at tick 4.
    assert first["ticks"][:4] == [{}, {}, {}, {}] and first["ticks"][4] and first["ticks"][7] == {}
    assert [m[2:] for m in first["moves"]][:1] == [[4, 6]]


def test_door_cycle_reads_only_the_hallway_each_tick_and_the_region_at_rest():
    _, rig = run_cycle()
    per_tick = [f for t, f in rig.calls if "hall0" in f]
    assert all(f == ("hall0", "door_rep", "occ_track0") for f in per_tick[1:])
    assert per_tick[0] == ("hall0", "door_rep")  # O(-1), before the first input
    whole = [t for t, f in rig.calls if f == ("occ_entities",)]
    assert len(whole) == 5  # placed, then after each of the four operations
    assert rig.calls[0][1] == ("occ_reset", "door_reset")
    # At rest the region is narrowed by slabs compared with the air above them, never a
    # function over every cell.
    assert rig.runs and all(r.startswith(("execute if blocks ", "execute unless block ")) for r in rig.runs)
    assert not any(n.startswith(("occ0", "occ_hall")) for n in rig.kw["functions"])
    # Each operation drives once and waits for quiet.
    assert [on for _, _, on in rig.drives] == [True, False, True, False]


def test_door_cycle_quiet_sets_how_long_an_operation_records_after_its_last_change(traces):
    def recorded(cycle):
        result, _ = run_cycle(None, cycle)
        trace = json.loads((traces / "door_2x2_flush_harness_check" / "cycle.json").read_text())
        return result["door"], [(len(o["ticks"]), o["w"]) for o in trace["door"]["ops"]]
    d40, ops40 = recorded({"cycles": 1})
    d100, ops100 = recorded({"cycles": 1, "quiet": 100})
    assert [n - w for n, w in ops40] == [41, 41] and [n - w for n, w in ops100] == [101, 101]
    assert [w for _, w in ops40] == [w for _, w in ops100] and d40["open"] == d100["open"]


def test_zero_tick_pull_is_instant_only_under_r1():
    result, _ = run_cycle({"zero_tick": True}, {"cycles": 1})
    assert result["door"]["open"] == {"R": 6, "H1": 4, "R1": 4}


@pytest.mark.parametrize("cycle,message", [
    ({"max_open": 5}, "door open time 6 ticks (R) exceeds bound 5"),
    ({"max_close": 5, "reading": "H1"}, "door close time 6 ticks (H1) exceeds bound 5"),
    ({"max_open_visible": 3}, "door open visible time 6 ticks exceeds bound 3"),
    ({"max_volume": 7}, "door volume 8 (4x2x1) exceeds bound 7"),
])
def test_door_cycle_bounds_fail_the_test(cycle, message, traces):
    with pytest.raises(AssertionError, match=re.escape(message)):
        run_cycle({"flags": "{any: {}, circ: {}, fired: {p0: 1b, p3: 1b}}"}, cycle | {"cycles": 1})
    trace = json.loads((traces / "door_2x2_flush_harness_check" / "cycle.json").read_text())
    assert message in trace["failures"][0] and trace["door"]["result"]


def test_open_reading_passes_a_bound_r_fails():
    result, _ = run_cycle(cycle={"cycles": 1, "max_open": 4, "reading": "H1"})
    assert result["door"]["reading"] == "H1"


def test_a_door_that_does_not_stand_closed_names_the_update_pass(traces):
    with pytest.raises(dt.DoorError, match="update_pass"):
        run_cycle({"start_open": True})
    assert "update_pass" in json.loads((traces / "door_2x2_flush_harness_check" / "cycle.json").read_text())["failures"][0]


def test_a_repeater_that_never_switches_stops_the_test():
    with pytest.raises(dt.DoorError, match="did not switch"):
        run_cycle({"lead": 50})


def test_volume_from_flags_fired_pistons_and_entities():
    p = door.plan(proof(), BIGDOOR.size)
    idx = {c: i for i, c in enumerate(p.region)}
    any_cells = [(0, 0, 1), (11, 0, 3), (4, 3, 0)]
    circ_cells = [(0, 0, 1), (11, 0, 3)]
    flags = ("{any: {" + ", ".join(f"c{idx[c]}: 1b" for c in any_cells) + "}, circ: {"
             + ", ".join(f"c{idx[c]}: 1b" for c in circ_cells) + "}, door: {}, e: [], shell: {}, fired: {p0: 1b}}")
    ox, oy, oz = BIGDOOR.origin
    cart = f'{{id: "minecraft:minecart", Pos: [{ox + 1.5}d, {oy + 4.0}d, {oz + 2.5}d], UUID: [I; 1, 2, 3, 4]}}'
    result, _ = run_cycle({"flags": flags, "entities": [cart]}, {"cycles": 1})
    v = result["door"]["volume"]
    # Circuitry spans x 0..11, y 0..4 (the minecart), z 1..3; the fired piston's head
    # cell (4, 1, 1) lies inside, and nothing reached the region's edge.
    assert v["box"] == [[0, 0, 1], [11, 4, 3]] and v["circ"] == 12 * 5 * 3
    assert v["any"] == 12 * 5 * 4 and v["heads"] == 1 and v["shell"] == []


def test_parse_hallway_reads_entities_and_the_repeater():
    p = door.plan(proof(), BIGDOOR.size)
    ox, oy, oz = BIGDOOR.origin
    hall = p.probed.index((5, 1, 0))
    reply = ("Storage redstone_ai:probe has the following contents: {c0: 2, n0: 1, e: [{id: \"minecraft:armor_stand\", "
             f"Pos: [{ox + 5.5}d, {oy + 1.0}d, {oz + 0.5}d], Invisible: 1b, UUID: [I; 1, 2, 3, 4]}}], rep: 1}}")
    obs, rep = door.parse_hallway(reply, p, BIGDOOR.origin)
    assert rep and obs.cells[p.probed[0]].code == 2 and obs.cells[p.probed[1]].code == dt.OTHER
    (e,), = [obs.entities]
    assert e.id == "armor_stand" and e.invisible and (5, 1, 0) in e.cells and (5, 2, 0) in e.cells
    assert hall >= 0
    assert not door.parse_hallway("Storage redstone_ai:probe has the following contents: {c0: 0}", p,
                                  BIGDOOR.origin)[1]


# ---- the plumbing ------------------------------------------------------------------------

def observed_build():
    b = Build()
    b.place((0, 0, 0), "stone").place((1, 0, 0), "observer[facing=west]").place((2, 0, 0), "redstone_wire")
    return b


def test_update_pass_options():
    b = observed_build()
    every = b.to_commands()
    assert sum(c.startswith("clone") for c in every) == 3
    assert not any(c.startswith("clone") for c in b.to_commands("none"))
    quiet = b.to_commands("unobserved")
    # The observer is set last and the stone it watches is not cloned.
    assert [c for c in quiet if c.startswith("setblock")][-1].startswith("setblock ~1 ~0 ~0 minecraft:observer")
    assert [c.split()[1] for c in quiet if c.startswith("clone")] == ["~1", "~2"]
    with pytest.raises(ValueError):
        b.to_commands("some")


def test_build_functions_split_under_the_command_chain_limit():
    b = Build({(x, 0, z): "minecraft:stone" for x in range(200) for z in range(200)})
    parts = b.to_functions(PROBE_CHUNK)
    assert len(parts) == 2 and all(len(p.splitlines()) <= PROBE_CHUNK for p in parts)
    lines = [l for p in parts for l in p.splitlines()]
    assert lines == b.to_commands()
    # Every setblock comes before the first clone, across the parts.
    assert max(i for i, l in enumerate(lines) if l.startswith("setblock")) < lines.index(
        next(l for l in lines if l.startswith("clone")))


def test_write_datapack_writes_and_prunes_block_tags(tmp_path):
    root = write_datapack(tmp_path, "redstone_ai", {"a": "say a\n"}, {"door_material": '{"values": []}'})
    assert (root / "data/redstone_ai/tags/block/door_material.json").exists()
    write_datapack(tmp_path, "redstone_ai", {"a": "say a\n"})
    assert not (root / "data/redstone_ai/tags/block/door_material.json").exists()


def test_clear_fills_stay_under_the_block_limit_in_the_bigdoor_plot():
    *fills, _ = clear_commands(BIGDOOR.origin, BIGDOOR.size)
    volume = 0
    for f in fills:
        x0, y0, z0, x1, y1, z1 = map(int, f.split()[1:7])
        n = (x1 - x0 + 1) * (y1 - y0 + 1) * (z1 - z0 + 1)
        assert n <= 32768
        volume += n
    assert volume == 112 * 64 * 112


def test_bigdoor_plot_is_clear_of_main_and_the_grid_and_chunk_aligned():
    ox, _, oz = BIGDOOR.origin
    assert BIGDOOR.size[0] >= 112 and BIGDOOR.size[1] >= 64 and BIGDOOR.size[2] >= 112
    assert (ox - 2) % 16 == 0 and (oz - 2) % 16 == 0
    chunks = lambda a, n: (a + n - 1 + 2) // 16 - (a - 2) // 16 + 1
    assert chunks(ox, BIGDOOR.size[0]) * chunks(oz, BIGDOOR.size[2]) <= 256  # forceload's limit
    for p in PLOTS.values():
        if p is not BIGDOOR:
            (px, _, pz), (sx, _, sz) = p.origin, p.size
            assert (ox >= px + sx + 5 or px >= ox + BIGDOOR.size[0] + 5
                    or oz >= pz + sz + 5 or pz >= oz + BIGDOOR.size[2] + 5), p.name
    assert MAIN.origin[0] + MAIN.size[0] + 5 <= ox


def test_package_raises_the_chain_limit_for_a_big_build(tmp_path, monkeypatch):
    s = proof()
    s.build = Build({(x, 0, z): "minecraft:stone" for x in range(200) for z in range(200)})
    monkeypatch.setattr(package_module, "load", lambda path: s)
    monkeypatch.setattr(package_module, "path_of", lambda name: SPEC)
    monkeypatch.setattr(package_module, "ROOT", tmp_path)
    pack = package_module.package("big")
    prepare = (pack / "data/big/function/prepare.mcfunction").read_text().splitlines()
    build = (pack / "data/big/function/build.mcfunction").read_text().splitlines()
    assert re.fullmatch(r"gamerule max_command_sequence_length \d+", prepare[0])
    assert int(prepare[0].split()[-1]) > 80000 and build[-1] == "gamerule max_command_sequence_length 65536"
    small = proof()
    monkeypatch.setattr(package_module, "load", lambda path: small)
    pack = package_module.package("small")
    assert "gamerule" not in (pack / "data/small/function/prepare.mcfunction").read_text()


def test_remote_ships_block_data_for_door_probe():
    import base64
    import io
    import tarfile
    names = tarfile.open(fileobj=io.BytesIO(base64.b64decode(remote.code())), mode="r:gz").getnames()
    assert "redstone/blocks.json" in names and "redstone/door.py" in names


def test_blocks_without_a_facing_take_the_game_default():
    s = proof()
    s.build.place((0, 2, 5), "sticky_piston")
    p = door.plan(s, BIGDOOR.size)
    assert ((0, 2, 5), "north") in p.pistons
    assert "unless block ~0 ~2 ~5 minecraft:sticky_piston[facing=north,extended=false] run" in p.functions["occ_track0"]
    b = Build().place((0, 0, 0), "observer").place((0, 0, 1), "stone")
    assert [c.split()[1:4] for c in b.to_commands("unobserved") if c.startswith("clone")] == [["~0", "~0", "~0"]]


def test_rest_scan_finds_the_proof_doors_volume():
    s = proof()
    rest = {p: door._bare(b) for p, b in s.build.blocks.items()}
    result, rig = run_cycle({"rest": rest}, {"cycles": 1})
    v = result["door"]["volume"]
    # Circuitry: torches, pistons, heads, repeaters and dust, x 0..11, y 0..2, z 1..3; the
    # hallway walls, floor and ceiling are surface, and the fixture and drive are left out.
    assert v["box"] == [[0, 0, 1], [11, 2, 3]] and (v["circ"], v["any"]) == (108, 192) and v["shell"] == []
    # Narrowing: one slab test per slab at most, cell tests only in non-empty edge slabs.
    p = door.plan(s, BIGDOOR.size)
    lo, hi = p.region[0], p.region[-1]
    slabs = {r for r in rig.runs if r.startswith("execute if blocks ")}
    assert len(slabs) <= sum(b - a + 1 for a, b in zip(lo, hi))


def test_strict_update_pass_sets_blocks_strict_and_runs_no_pass(tmp_path):
    b = observed_build().summon((0.0, 1.0, 0.0), "minecart")
    commands = b.to_commands("strict")
    assert [c for c in commands if c.startswith("setblock")] == [
        "setblock ~0 ~0 ~0 minecraft:stone strict", "setblock ~1 ~0 ~0 minecraft:observer[facing=west] strict",
        "setblock ~2 ~0 ~0 minecraft:redstone_wire strict"]
    assert commands[-1] == "summon minecraft:minecart ~0.0 ~1.0 ~0.0" and not any("clone" in c for c in commands)
    big = Build({(x, 0, z): "minecraft:stone" for x in range(300) for z in range(300)})
    parts = big.to_functions(PROBE_CHUNK, "strict")
    assert len(parts) == 2 and all(line.endswith(" strict") for part in parts for line in part.splitlines())
    s = proof()
    s.update_pass = "strict"
    assert lint_module.lint(s) == []
    out = tmp_path / "x.redstone.yaml"
    out.write_text(fileformat.dump(s))
    assert fileformat.load(out).update_pass == "strict"


def test_package_places_with_the_specs_update_pass(tmp_path, monkeypatch):
    s = proof()
    s.update_pass = "strict"
    monkeypatch.setattr(package_module, "load", lambda path: s)
    monkeypatch.setattr(package_module, "path_of", lambda name: SPEC)
    monkeypatch.setattr(package_module, "ROOT", tmp_path)
    place = (package_module.package("p") / "data/p/function/place.mcfunction").read_text()
    assert place == s.build.to_mcfunction("strict") and "clone" not in place


def lever_spec():
    s = proof()
    s.build.place((5, 0, 6), "lever[face=floor,facing=north]")
    s.named["lever"] = (5, 0, 6)
    s.door = {k: v for k, v in s.door.items() if k not in ("input", "repeater")} | {"lever": "lever"}
    return s


def test_lever_input_flips_the_lever_and_counts_from_the_next_tick():
    s = lever_spec()
    assert lint_module.lint(s) == []
    p = door.plan(s, BIGDOOR.size)
    assert p.lever == (5, 0, 6) and p.drive == [] and (5, 0, 6) in p.static
    assert p.functions["door_rep"].startswith("execute if block ~5 ~0 ~6 minecraft:lever[powered=true] ")
    # A lever's power changes with the click, so tick 0 is the first tick after it.
    result, _ = run_cycle({"lead": 0}, {"cycles": 1}, spec=s)
    d = result["door"]
    assert d["cycles"][0]["open"]["lead"] == 1 and d["open"]["R"] == 5 and d["close"]["R"] == 5
    for bad, message in (({"input": "door_in"}, "not both"), ({"lever": "nope"}, "not a named lever")):
        s2 = lever_spec()
        s2.door = s2.door | bad
        assert any(message in m for m in lint_module.lint(s2)), bad
