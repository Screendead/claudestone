import pytest

from redstone import fileformat
from redstone.build import Build
from redstone.fileformat import Spec
from redstone.library import name_of, path_of, paths
from redstone.harness import probe_functions
from scripts.lint import lint


@pytest.mark.parametrize("path", paths(), ids=name_of)
def test_library_lints_clean(path):
    assert lint(fileformat.load(path)) == []


def spec(blocks, **kw):
    b = Build()
    for pos, s in blocks.items():
        b.place(pos, s)
    return Spec("t", b, **kw)


def test_dust_without_floor():
    assert lint(spec({(0, 1, 0): "redstone_wire"})) == ["redstone_wire at (0, 1, 0) has nothing below"]


def test_dust_on_floor_and_ground_level_ok():
    assert lint(spec({(0, 0, 0): "stone", (0, 1, 0): "redstone_wire", (2, 0, 0): "repeater"})) == []


def test_wall_torch_hangs_on_opposite_side():
    ok = spec({(1, 1, 0): "stone", (0, 1, 0): "redstone_wall_torch[facing=west]"})
    assert lint(ok) == []
    bad = spec({(1, 1, 0): "stone", (0, 1, 0): "redstone_wall_torch[facing=east]"})
    assert "hangs on (-1, 1, 0)" in lint(bad)[0]


def test_ceiling_lever():
    assert lint(spec({(0, 2, 0): "lever[face=ceiling,facing=north]"}))


def test_input_inside_build():
    s = spec({(0, 0, 0): "stone"}, inputs={"a": (0, 0, 0)})
    assert "must be air" in lint(s)[0]


def test_named_cell_in_air_and_unreadable_output():
    s = spec({(0, 0, 0): "stone"}, inputs={"a": (1, 0, 0)}, outputs={"o": (0, 0, 0), "p": (5, 0, 0)},
             named={"o": (0, 0, 0), "p": (5, 0, 0)},
             tests=[{"name": "t", "truth_table": "a | o\n0 | 0"}])
    found = lint(s)
    assert any("cell p" in m and "is air" in m for m in found)
    assert any("'o'" in m and "carries no signal" in m for m in found)


def test_use_needs_plain_support():
    s = spec({(0, 0, 0): "glass", (0, 1, 0): "lever[face=floor,facing=north]"}, named={"l": (0, 1, 0)},
             tests=[{"name": "t", "steps": [{"use": "l"}]}])
    assert "plain full blocks" in lint(s)[0]


def test_unknown_block_id():
    assert lint(spec({(0, 0, 0): "waxed_copper"})) == ["unknown block 'waxed_copper' in minecraft:waxed_copper"]


def test_bad_property_value_and_name():
    found = lint(spec({(0, 0, 0): "repeater[facing=up]", (2, 0, 0): "repeater[facing=north,lit=true]"}))
    assert any("facing=up is not one of" in m for m in found)
    assert any("no property 'lit'" in m for m in found)
    assert len(found) == 2


def test_block_entity_nbt_ignored_and_unknown_entity():
    s = spec({(0, 0, 0): 'hopper[facing=down]{Items:[{id:"minecraft:redstone",count:1}]}'})
    assert lint(s) == []
    s.build.summon((0.5, 1, 0.5), "minecart_hopper")
    assert lint(s) == ["unknown entity type 'minecraft:minecart_hopper'"]


def test_yaml_bool_cell_name(tmp_path):
    f = tmp_path / "t.redstone.yaml"
    f.write_text("name: t\npalette:\n  '.': air\n  '=': stone\n  a: {input: on}\nlayers:\n  0: |\n    =a\n")
    assert lint(fileformat.load(f)) == ["input True is a bool, not a name; quote it in the YAML"]


def test_rcon_length():
    long_run = "fill ~0 ~1 ~0 ~0 ~1 ~0 barrel{Items:[" + ",".join(['{id:"minecraft:stone",count:1}'] * 50) + "]}"
    s = spec({(0, 0, 0): "stone"}, tests=[{"name": "t", "steps": [{"run": long_run}, {"check": "if block ~0 ~0 ~0 stone"}]}])
    found = lint(s)
    assert len(found) == 1 and "run command is" in found[0] and "RCON" in found[0]


def test_plot_bounds():
    big = spec({(0, 0, 0): "stone", (0, 30, 0): "stone"})
    assert lint(big) and "main plot" in lint(big)[0]
    big.path = path_of("vwire_glass_zigzag_long")
    assert lint(big) == []


def test_level_needs_an_analog_cell():
    s = spec({(0, 0, 0): "stone", (1, 0, 0): "redstone_wire", (2, 0, 0): "comparator[facing=west]",
              (3, 0, 0): "daylight_detector", (5, 0, 0): "redstone_lamp", (6, 0, 0): "hopper"},
             named={"d": (1, 0, 0), "c": (2, 0, 0), "s": (3, 0, 0), "l": (5, 0, 0), "h": (6, 0, 0)},
             tests=[{"name": "t", "steps": [{"level": {"d": 3, "c": 7, "s": 15}}, {"level": {"l": 1, "h": 1}},
                                            {"level": {"x": 1}}, {"level": {"d": 16}}]}])
    found = lint(s)
    assert len(found) == 4
    assert "level 'l'" in found[0] and "no signal strength" in found[0]
    assert "level 'h'" in found[1]
    assert "unknown cell 'x'" in found[2]
    assert "not a strength 0-15" in found[3]


def test_new_cells_are_readable_by_expect():
    cells = {"bulb": "waxed_oxidized_copper_bulb", "rail": "powered_rail", "piston": "sticky_piston",
             "hopper": "hopper", "sun": "daylight_detector", "door": "iron_trapdoor", "gate": "oak_fence_gate"}
    blocks = {(2 * i, 1, 0): s for i, s in enumerate(cells.values())} | {(2 * i, 0, 0): "stone" for i in range(len(cells))}
    named = {n: (2 * i, 1, 0) for i, n in enumerate(cells)}
    assert lint(spec(blocks, named=named, tests=[{"name": "t", "steps": [{"expect": dict.fromkeys(cells, 1)}]}])) == []


def _probe(state):
    b = Build()
    b.place((1, 2, 3), state)
    (body,), probed = probe_functions(b)
    assert probed == [(1, 2, 3)]
    return body.splitlines()


def test_probe_boolean_cells():
    for state, block, prop in (("waxed_copper_bulb", "waxed_copper_bulb", "lit"),
                               ("powered_rail[shape=east_west]", "powered_rail", "powered"),
                               ("sticky_piston[facing=east]", "sticky_piston", "extended")):
        assert _probe(state) == [f"execute if block ~1 ~2 ~3 minecraft:{block}[{prop}=true] run "
                                 f"data modify storage redstone_ai:probe s.b0 set value 1"]


def test_probe_hopper_reads_locked_as_on():
    assert _probe("hopper[facing=down]") == ["execute if block ~1 ~2 ~3 minecraft:hopper[enabled=false] run "
                                             "data modify storage redstone_ai:probe s.b0 set value 1"]


def test_probe_daylight_detector_scans_power():
    lines = _probe("daylight_detector")
    assert len(lines) == 15
    assert lines[6] == ("execute if block ~1 ~2 ~3 minecraft:daylight_detector[power=7] run "
                        "data modify storage redstone_ai:probe s.b0 set value 7")


def test_probe_comparator_stores_output_signal():
    assert _probe("comparator[facing=west]")[-1] == ("execute store result storage redstone_ai:probe s.c0 int 1 run "
                                                     "data get block ~1 ~2 ~3 OutputSignal")


def test_no_probe_for_plain_blocks():
    b = Build()
    b.place((0, 0, 0), "stone")
    assert probe_functions(b)[1] == []


def test_wave_characters_quoting_and_cells():
    s = spec({(0, 0, 0): "stone", (0, 1, 0): "redstone_wire", (1, 0, 0): "stone"}, named={"o": (0, 1, 0), "s": (1, 0, 0)},
             tests=[{"name": "t", "steps": [{"wave": {"o": "01x"}}, {"wave": {"o": 11}}, {"wave": {"o": "012"}},
                                            {"wave": {"s": "1"}}, {"wave": {"z": "1"}}]}])
    found = lint(s)
    assert len(found) == 4
    assert "quote it" in found[0]
    assert "0, 1 and x" in found[1]
    assert "'s'" in found[2] and "carries no signal" in found[2]
    assert "unknown cell 'z'" in found[3]


def test_repeat_is_checked_inside_and_needs_times():
    s = spec({(0, 0, 0): "stone"}, inputs={"a": (1, 0, 0)},
             tests=[{"name": "t", "steps": [{"repeat": {"times": 2, "steps": [{"drive": {"a": 1}},
                                                                              {"repeat": {"times": 1, "steps": [{"drive": {"b": 1}}]}}]}},
                                            {"repeat": {"times": 0, "steps": []}}, {"bogus": 1}]}])
    assert lint(s) == ["test 't': unknown input 'b'", "test 't': repeat needs {times: <positive int>, steps: [...]}, "
                       "not {'times': 0, 'steps': []}", "test 't': unknown step 'bogus'"]


def test_log_and_finally_count_the_success_wrapper():
    near = "say " + "x" * (1400 - len("execute positioned 0 56 0 store success storage redstone_ai:probe ok int 1 run say ") - 10)
    s = spec({(0, 0, 0): "stone"}, tests=[{"name": "t", "steps": [{"log": near + "y" * 20}], "finally": [near + "y" * 20, near]}])
    found = lint(s)
    assert len(found) == 2 and found[0].startswith("test 't': log command is") and "finally command is" in found[1]


def test_gamerule_change_needs_a_finally_restore():
    steps = [{"run": "gamerule random_tick_speed 4096"}, {"repeat": {"times": 1, "steps": [{"run": "gamerule tnt_explodes false"}]}},
             {"log": "gamerule advance_time"}, {"run": "gamerule random_tick_speed 3"}]
    s = spec({(0, 0, 0): "stone"}, tests=[{"name": "t", "steps": steps, "finally": ["gamerule tnt_explodes true"]}])
    assert lint(s) == ["test 't': run changes gamerule random_tick_speed but finally does not restore it "
                       "(a failed or killed test leaves it, and the world saves it)"]
    s.tests[0]["finally"].append("gamerule random_tick_speed 3")
    assert lint(s) == []


def test_truth_table_options():
    cells = {(0, 0, 0): "stone", (0, 1, 0): "redstone_wire"}
    base = {"name": "t", "truth_table": "a | o\n0 | 0\n1 | x"}
    lint_test = lambda **kw: lint(spec(cells, inputs={"a": (1, 1, 0)}, outputs={"o": (0, 1, 0)},
                                       named={"o": (0, 1, 0)}, tests=[{**base, **kw}]))
    assert lint_test(delays={"o": {"rise": 2, "fall": 0}}, max_delays={"o": 3}, glitch_free=True, reset=False) == []
    assert lint_test(delays={"p": 2}) == ["test 't': delays 'p' is not an output column of the truth table"]
    assert lint_test(max_delays={"o": {"up": 2}}) == ["test 't': max_delays 'o': 'up' must be rise or fall"]
    assert lint_test(delays={"o": -1}) == ["test 't': delays 'o': -1 is not a number of ticks"]
    assert lint_test(reset="no") == ["test 't': reset 'no' is not true or false"]
    no_table = spec(cells, tests=[{"name": "t", "glitch_free": True, "steps": []}])
    assert lint(no_table) == ["test 't': glitch_free needs a truth_table"]


def test_reserved_cell_holding_a_block():
    s = spec({(0, 0, 0): "stone", (1, 0, 0): "stone"}, reserved={(1, 0, 0), (2, 0, 0)})
    assert lint(s) == ["reserved cell (1, 0, 0) holds minecraft:stone"]


def test_every_cell_of_a_multi_cell_input_is_checked():
    s = spec({(0, 0, 0): "stone", (0, 1, 0): "redstone_wire"}, inputs={"s": (1, 0, 0)},
             extra_inputs={"s": [(1, 0, 0), (0, 0, 0)]})
    assert lint(s) == ["input s at (0, 0, 0) is inside the build (minecraft:stone); the driver cell must be air"]


def test_initial_and_tile():
    cells = {(0, 0, 0): "stone", (0, 1, 0): "redstone_wire"}
    base = {"name": "t", "truth_table": "a | o\n0 | 0"}
    lint_test = lambda **kw: lint(spec(cells, inputs={"a": (1, 1, 0)}, outputs={"o": (0, 1, 0)},
                                       named={"o": (0, 1, 0)}, tests=[{**base, **kw}]))
    assert lint_test(initial={"a": 1}, tile=[2, 0, 0]) == []
    assert lint_test(initial={"b": 1, "a": 2}) == ["test 't': initial: unknown input 'b'", "test 't': initial 'a': 2 is not 1 or 0"]
    assert lint_test(tile=[0, 0]) == ["test 't': tile [0, 0] is not a nonzero offset [dx, dy, dz]"]
    assert lint_test(tile=[1, 0, 0]) == [
        "test 't': tile [1, 0, 0]: input a at (1, 1, 0) is inside the build (minecraft:redstone_wire); the driver cell must be air"]
    assert "test 't': tile [0, 1, 0]: the copies overlap at (0, 1, 0)" in lint_test(tile=[0, 1, 0])[0]
    assert "exceed" in lint_test(tile=[0, 0, -1])[0]
