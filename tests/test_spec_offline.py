"""spec.run against a fake Rig that serves scripted snapshots, so step semantics are checked
without a server."""

import json

import pytest

from redstone import spec as spec_module
from redstone.build import Build
from redstone.fileformat import Spec, parse_truth_table
from redstone.plots import MAIN

OUT, Q = (1, 1, 0), (2, 1, 0)


class FakeRig:
    """Snapshots come from `script(tick)`; commands are logged with the tick they ran at."""

    def __init__(self, script=lambda tick: {}, replies=None):
        self.plot, self.heading, self.levels = MAIN.name, [], {}
        self.tick, self.script, self.replies = 0, script, replies or {}
        self.log: list[tuple[int, str]] = []

    def load(self, build, probe=None, drivers=frozenset()):
        self.loaded, self.drivers = build, drivers

    def abs(self, pos):
        return " ".join(map(str, pos))

    def step(self, n=1):
        self.tick += n

    def snapshot(self):
        return {OUT: 0, Q: 0} | self.script(self.tick)

    def drive(self, pos, on):
        self.log.append((self.tick, f"drive {pos} {on}"))

    def run(self, command):
        if not command.startswith("title"):
            self.log.append((self.tick, command))
        return ""

    def command(self, command):
        self.log.append((self.tick, command))
        return self.replies.get(command, (True, ""))


@pytest.fixture(autouse=True)
def traces(tmp_path, monkeypatch):
    monkeypatch.setattr(spec_module, "TRACE_DIR", tmp_path)
    return tmp_path


def make_spec(steps=(), **test):
    return Spec("fake", Build(), inputs={"a": (0, 1, 0)}, outputs={"out": OUT}, named={"out": OUT, "q": Q},
                tests=[{"name": "t", "settle": 0, "steps": list(steps), **test}])


def run(rig, s):
    return spec_module.run(rig, s, s.tests[0])


def square(on_from, on_to):
    return lambda tick: {OUT: 1 if on_from <= tick < on_to else 0}


def test_wave_passes_and_advances_one_tick_per_character():
    rig = FakeRig(square(2, 6))
    run(rig, make_spec([{"wave": {"out": "0011110000"}}, {"run": "say after"}]))
    assert rig.log[-1] == (10, "say after")


def test_wave_mismatch_names_tick_and_cell():
    rig = FakeRig(square(2, 5))
    with pytest.raises(AssertionError, match=r"tick 5: wave out: expected 1, got 0 at character 6 of 0011110000"):
        run(rig, make_spec([{"wave": {"out": "0011110000"}}, {"run": "say after"}]))
    assert rig.log[-1] == (10, "say after")


def test_wave_x_is_dont_care_and_short_strings_stop_early():
    rig = FakeRig(lambda tick: {OUT: tick % 2, Q: 1 if tick >= 2 else 0})
    run(rig, make_spec([{"wave": {"out": "xxxxxx", "q": "xx11"}}]))
    with pytest.raises(AssertionError, match="wave q: expected 0, got 1"):
        run(FakeRig(lambda tick: {Q: 1}), make_spec([{"wave": {"q": "x0"}}]))


def test_repeat_expands_in_order():
    rig = FakeRig()
    run(rig, make_spec([{"repeat": {"times": 3, "steps": [{"drive": {"a": 1}}, {"wait": 2}]}}]))
    assert [t for t, c in rig.log if c.startswith("drive")] == [0, 2, 4]


def test_repeat_nests_and_notes_iterations(traces):
    rig = FakeRig()
    inner = {"repeat": {"times": 2, "steps": [{"wait": 1}]}}
    run(rig, make_spec([{"repeat": {"times": 2, "steps": [inner]}}]))
    assert rig.tick == 4
    events = [f["event"] for f in json.loads((traces / "fake" / "t.json").read_text())["frames"]]
    assert [e for e in events if e.startswith("repeat")] == ["repeat 1/2", "repeat 1/2", "repeat 2/2",
                                                             "repeat 2/2", "repeat 1/2", "repeat 2/2"]


def test_failures_are_collected_and_the_trace_written(traces):
    rig = FakeRig()
    steps = [{"expect": {"out": 1}}, {"wait": 3}, {"expect": {"q": 1}}, {"run": "say end"}]
    with pytest.raises(AssertionError) as e:
        run(rig, make_spec(steps))
    assert str(e.value) == "tick 0: expected out=1, got out=0 (and 1 more)"
    assert rig.log[-1] == (3, "say end")
    trace = json.loads((traces / "fake" / "t.json").read_text())
    assert trace["failures"] == ["tick 0: expected out=1, got out=0", "tick 3: expected q=1, got q=0"]


def test_failure_in_repeat_names_iteration():
    rig = FakeRig(square(0, 3))
    with pytest.raises(AssertionError, match=r"^tick 4 \(repeat 3/3\): expected out=1"):
        run(rig, make_spec([{"repeat": {"times": 3, "steps": [{"expect": {"out": 1}}, {"wait": 2}]}}]))


def test_finally_runs_after_a_failure():
    rig = FakeRig()
    with pytest.raises(AssertionError, match="expected out=1"):
        run(rig, make_spec([{"expect": {"out": 1}}], **{"finally": ["gamerule advance_time true", "time set 0"]}))
    assert [c for _, c in rig.log[-2:]] == ["gamerule advance_time true", "time set 0"]


def test_finally_error_does_not_hide_the_test_failure():
    rig = FakeRig(replies={"bad": (False, "Oops")})
    with pytest.raises(AssertionError, match=r"expected out=1.*\(and 1 more\)"):
        run(rig, make_spec([{"expect": {"out": 1}}], **{"finally": ["bad"]}))


def test_run_fails_on_command_error_but_not_on_benign_replies():
    replies = {"clone": (False, "The source and destination areas cannot overlap"),
               "cond": (False, ""), "kill": (False, "No entity was found"),
               "merge": (False, "Nothing changed. The specified properties already have these values"),
               "test": (False, "Test failed"), "same": (False, "Could not set the block"),
               "objective": (False, "An objective already exists by that name"),
               "time": (False, "Clock minecraft:overworld is already at time marker minecraft:noon"),
               "rule": (False, "Game rule tnt_explodes is already set to false")}
    ok = make_spec([{"run": c} for c in replies if c != "clone"])
    run(FakeRig(replies=replies), ok)
    with pytest.raises(AssertionError, match="run clone: The source and destination areas cannot overlap"):
        run(FakeRig(replies=replies), make_spec([{"run": "clone"}]))


def test_log_records_the_reply(traces):
    rig = FakeRig(replies={"data get block ~ ~ ~ Items": (True, "Hopper has the following block data: []")})
    run(rig, make_spec([{"log": "data get block ~ ~ ~ Items"}]))
    frames = json.loads((traces / "fake" / "t.json").read_text())["frames"]
    assert frames[-1]["event"] == "log data get block ~ ~ ~ Items"
    assert frames[-1]["reply"] == "Hopper has the following block data: []"


# A truth-table row takes SETTLE + HOLD = 30 ticks whatever it measures, so with settle: 0
# row i is driven at tick 30 * i.
BUFFER = "a | out\n0 | 0\n1 | 1\n"


def test_truth_table_measures_each_output_edge():
    result = run(FakeRig(square(34, 62)), make_spec(truth_table=BUFFER))
    assert result == {"delay": 4, "delays": {"out": {"rise": 4, "fall": 2}}}


def test_delays_assert_exact_per_edge_and_bound():
    run(FakeRig(square(34, 62)), make_spec(truth_table=BUFFER, delays={"out": {"rise": 4, "fall": 2}}))
    run(FakeRig(square(34, 62)), make_spec(truth_table=BUFFER, delays={"out": 4}, max_delays={"out": {"fall": 2}}))
    with pytest.raises(AssertionError, match="measured out fall delay 2 ticks, spec says 3"):
        run(FakeRig(square(34, 62)), make_spec(truth_table=BUFFER, delays={"out": {"fall": 3}}))
    with pytest.raises(AssertionError, match="measured out rise delay 4 ticks exceeds bound 3"):
        run(FakeRig(square(34, 62)), make_spec(truth_table=BUFFER, max_delays={"out": {"rise": 3}}))
    with pytest.raises(AssertionError, match="never makes out fall"):
        run(FakeRig(square(34, 99)), make_spec(truth_table=BUFFER, reset=False, delays={"out": {"fall": 2}}))


def test_glitch_free_fails_a_dip_after_the_first_match():
    def dip(tick):
        return {OUT: 1 if 34 <= tick < 62 and tick != 40 else 0}
    run(FakeRig(dip), make_spec(truth_table=BUFFER))
    with pytest.raises(AssertionError, match="out glitched to 0 at tick 10 after the change"):
        run(FakeRig(dip), make_spec(truth_table=BUFFER, glitch_free=True))


def test_glitch_free_fails_an_unchanged_output_that_moves():
    table = "a | out\n0 | 0\n1 | 0\n"
    run(FakeRig(square(33, 34)), make_spec(truth_table=table))
    with pytest.raises(AssertionError, match="out glitched to 1 at tick 3"):
        run(FakeRig(square(33, 34)), make_spec(truth_table=table, glitch_free=True))


def test_dont_care_output_is_not_checked_and_has_no_edge():
    table = "a | out q\n0 | 0 0\n1 | 1 x\n"
    result = run(FakeRig(lambda t: {OUT: 1 if 34 <= t < 62 else 0, Q: t % 2}), make_spec(truth_table=table))
    assert result["delays"] == {"out": {"rise": 4, "fall": 2}}


def test_reset_false_skips_the_replay_of_the_first_row():
    table = "a | out\n0 | 0\n1 | 1\n0 | 0\n"
    drives = lambda rig: [t for t, c in rig.log if c.startswith("drive")]
    rig = FakeRig(square(31, 61))
    run(rig, make_spec(truth_table=table))
    assert drives(rig) == [0, 30, 60, 90]
    rig = FakeRig(square(31, 61))
    run(rig, make_spec(truth_table=table, reset=False))
    assert drives(rig) == [0, 30, 60]


def test_parse_truth_table_dont_care():
    ins, outs, rows = parse_truth_table("a b | s c\n0 1 | 1 x\n1 1 | x 1\n")
    assert (ins, outs) == (["a", "b"], ["s", "c"])
    assert rows == [({"a": False, "b": True}, {"s": True, "c": None}),
                    ({"a": True, "b": True}, {"s": None, "c": True})]


def test_parse_truth_table_rejects_x_in_inputs():
    with pytest.raises(ValueError, match="only allowed in output columns"):
        parse_truth_table("a b | s\n0 x | 1\n")


def test_initial_places_drivers_in_the_build():
    rig = FakeRig()
    s = make_spec(initial={"a": 1})
    s.extra_inputs = {"a": [(0, 1, 0), (5, 1, 0)]}
    run(rig, s)
    assert rig.drivers == {(0, 1, 0), (5, 1, 0)}
    assert rig.loaded.blocks == {(0, 1, 0): "minecraft:redstone_block", (5, 1, 0): "minecraft:redstone_block"}
    assert s.build.blocks == {}
    commands = rig.loaded.to_commands()
    assert commands.index("setblock ~5 ~1 ~0 minecraft:redstone_block") < min(
        i for i, c in enumerate(commands) if c.startswith("clone"))


def test_drive_sets_every_cell_of_an_input_in_order():
    rig = FakeRig()
    s = make_spec([{"drive": {"a": 1}}])
    s.extra_inputs = {"a": [(0, 1, 0), (5, 1, 0)]}
    run(rig, s)
    assert [c for _, c in rig.log if c.startswith("drive")] == ["drive (0, 1, 0) True", "drive (5, 1, 0) True"]


def test_tile_runs_copy_b_one_row_ahead_and_checks_both():
    b_out = (11, 1, 0)
    driven = {}

    class Rig(FakeRig):
        def drive(self, pos, on):
            driven[pos] = on

        def snapshot(self):
            # out = a in each copy; copy B's cells sit 10 blocks east.
            return {OUT: int(driven.get((0, 1, 0), False)), b_out: int(driven.get((10, 1, 0), False)), Q: 0}

    s = make_spec(truth_table="a | out\n0 | 0\n1 | 1\n1 | 1\n0 | 0", tile=[10, 0, 0], settle=2)
    s.build.place((1, 1, 0), "redstone_wire")
    rig = Rig()
    run(rig, s)
    frames = json.loads((spec_module.TRACE_DIR / "fake" / "t.json").read_text())["frames"]
    assert [f["event"] for f in frames if f["event"].startswith("drive")] == [
        "drive a=0 B.a=1", "drive a=1 B.a=1", "drive a=1 B.a=0", "drive a=0 B.a=0", "drive a=0 B.a=1"]
    assert rig.loaded.blocks == {(1, 1, 0): "minecraft:redstone_wire", b_out: "minecraft:redstone_wire"}

    class Stuck(Rig):
        def snapshot(self):
            return super().snapshot() | {b_out: 0}

    with pytest.raises(AssertionError, match="B.out=1"):
        run(Stuck(), s)
