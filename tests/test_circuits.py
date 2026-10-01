import pytest

from redstone.circuits import SHARED, is_conductor, is_movable, support_of, trace

REP_E = "repeater[facing=west,delay=1]"     # input on the west, output east
REP_W = "repeater[facing=east,delay=1]"


def line():
    """A's repeater (0,1,0) -> stone (1,1,0) -> repeater (2,1,0) -> stone (3,1,0), all on supports."""
    b = {(0, 1, 0): REP_E, (1, 1, 0): "stone", (2, 1, 0): REP_E, (3, 1, 0): "stone"}
    b.update({(x, 0, 0): "stone" for x in range(4)})
    return b


def test_signal_follows_repeaters_and_supports_take_their_component():
    t = trace(line(), {"a": [(0, 1, 0)]})
    assert t.owner[(1, 1, 0)] == t.owner[(2, 1, 0)] == t.owner[(3, 1, 0)] == "a"
    assert t.how[(1, 1, 0)] == "signal" and t.how[(0, 0, 0)] == "support"
    assert t.owner[(0, 0, 0)] == t.owner[(2, 0, 0)] == "a"
    assert t.owner[(1, 0, 0)] is None and t.owner[(3, 0, 0)] is None      # under blocks, supporting nothing
    assert t.unassigned == {(1, 0, 0), (3, 0, 0)}


def test_another_circuits_seed_is_a_boundary_and_signal_never_runs_backwards():
    t = trace(line(), {"a": [(0, 1, 0)], "b": [(2, 1, 0)]})
    assert t.owner[(1, 1, 0)] == "a" and t.owner[(2, 1, 0)] == "b" and t.owner[(3, 1, 0)] == "b"
    assert t.owner[(2, 0, 0)] == "b"
    assert t.reached[(2, 1, 0)] == {"a": 2}


def test_block_powered_by_two_circuits_at_once_is_shared_and_the_nearer_one_wins():
    b = {(0, 1, 0): REP_E, (1, 1, 0): "stone", (2, 1, 0): REP_W}
    t = trace(b, {"a": [(0, 1, 0)], "b": [(2, 1, 0)]})
    assert t.owner[(1, 1, 0)] == SHARED and t.shared == {(1, 1, 0)}
    b[(-1, 1, 0)], b[(-2, 1, 0)] = "stone", REP_E
    t = trace(b, {"a": [(-2, 1, 0)], "b": [(2, 1, 0)]})
    assert t.owner[(1, 1, 0)] == "b" and t.reached[(1, 1, 0)] == {"a": 3, "b": 1}


def test_a_repeater_reads_only_its_back_and_a_side_diode_locks_it():
    b = {(0, 1, 0): REP_E, (1, 1, 0): "repeater[facing=north,delay=1]", (1, 1, 1): "stone"}
    assert trace(b, {"a": [(0, 1, 0)]}).owner[(1, 1, 0)] == "a"          # lock from the side
    b[(0, 1, 0)] = "stone"
    b[(-1, 1, 0)] = REP_E
    t = trace(b, {"a": [(-1, 1, 0)]})
    assert t.owner[(1, 1, 0)] is None                                      # a powered block beside it: not its back


def test_torch_strongly_powers_the_block_above_and_only_components_around_it():
    b = {(0, 0, 0): "stone", (0, 1, 0): "redstone_torch", (0, 2, 0): "stone", (1, 1, 0): "stone",
         (0, 3, 0): "redstone_wire[east=none,north=none,south=none,west=none,power=0]",
         (-1, 1, 0): "redstone_wire[east=side,north=none,south=none,west=none,power=0]"}
    t = trace(b, {"a": [(0, 1, 0)]})
    assert t.owner[(0, 2, 0)] == "a" and t.owner[(0, 3, 0)] == "a"       # strong block powers the dust on it
    assert t.owner[(-1, 1, 0)] == "a" and t.owner[(1, 1, 0)] is None      # dust beside yes, block beside no
    assert t.owner[(0, 0, 0)] == "a" and t.how[(0, 0, 0)] == "support"


def test_dust_powers_its_block_weakly_and_a_weak_block_powers_no_dust():
    b = {(0, 0, 0): "stone", (1, 0, 0): "stone", (0, 1, 0): "redstone_wire[east=side,north=none,south=none,west=none]",
         (1, 1, 0): "stone", (1, 2, 0): "redstone_wire[east=none,north=none,south=none,west=none]",
         (2, 1, 0): REP_E, (2, 0, 0): "stone", (1, 1, 1): "redstone_torch", (1, 0, 1): "stone",
         (0, 1, 1): "observer[facing=south]"}
    t = trace(b, {"a": [(0, 1, 0)]})
    assert t.owner[(1, 1, 0)] == "a" and t.owner[(2, 1, 0)] == "a"       # pointed-into block, repeater reading it
    assert t.owner[(1, 2, 0)] is None                                       # dust on a weakly powered block
    assert t.owner[(1, 1, 1)] is None                                       # a floor torch on another block
    assert t.owner[(0, 1, 1)] is None                                       # observer: dust state change is not in front


def test_dust_steps_up_and_down():
    w = "redstone_wire[east={e},north=none,south=none,west={w}]"
    b = {(0, 0, 0): "stone", (0, 1, 0): w.format(e="up", w="none"), (1, 1, 0): "stone",
         (1, 2, 0): w.format(e="side", w="side"), (2, 0, 0): "stone", (2, 1, 0): w.format(e="none", w="side")}
    t = trace(b, {"a": [(0, 1, 0)]})
    assert t.owner[(1, 2, 0)] == "a" and t.owner[(2, 1, 0)] == "a"
    b[(2, 2, 0)] = "stone"                                                  # a solid block cuts the step down
    t = trace(b, {"a": [(0, 1, 0)]})
    assert t.owner[(2, 2, 0)] == "a" and t.owner[(2, 1, 0)] is None


def test_observer_sees_a_hopper_toggle_and_strongly_powers_its_back():
    b = {(0, 1, 0): REP_E, (0, 0, 0): "stone", (1, 1, 0): "hopper[facing=down,enabled=true]",
         (1, 1, 1): "observer[facing=north]", (1, 1, 2): "stone", (1, 2, 2): "redstone_wire[east=none,north=none]",
         (5, 5, 5): "stone"}
    t = trace(b, {"a": [(0, 1, 0)]})
    assert t.owner[(1, 1, 1)] == "a" and t.owner[(1, 1, 2)] == "a" and t.owner[(1, 2, 2)] == "a"
    assert t.owner[(5, 5, 5)] is None


def test_quasi_connectivity_and_piston_front():
    b = {(0, 2, 0): REP_E, (1, 1, 0): "sticky_piston[facing=up,extended=false]", (1, 2, 0): "glass"}
    assert trace(b, {"a": [(0, 2, 0)]}).owner[(1, 1, 0)] == "a"            # into the cell above it
    b = {(0, 1, 0): REP_E, (1, 1, 0): "piston[facing=west,extended=false]"}
    assert trace(b, {"a": [(0, 1, 0)]}).owner[(1, 1, 0)] is None           # into its front face
    b[(1, 1, 0)] = "piston[facing=south,extended=false]"
    assert trace(b, {"a": [(0, 1, 0)]}).owner[(1, 1, 0)] == "a"


def test_comparator_reads_a_bulb_through_a_block():
    b = {(0, 1, 0): REP_E, (1, 1, 0): "waxed_copper_bulb[lit=false,powered=false]", (1, 1, 1): "stone",
         (1, 1, 2): "comparator[facing=north]", (1, 1, 3): "stone"}
    t = trace(b, {"a": [(0, 1, 0)]})
    assert t.owner[(1, 1, 2)] == "a" and t.owner[(1, 1, 3)] == "a"
    assert t.owner[(1, 1, 1)] is None                                        # the bulb doesn't conduct


def test_glue_drags_movable_blocks_and_beats_signal():
    b = {(0, 1, 0): "slime_block", (1, 1, 0): "stone", (-1, 1, 0): "obsidian", (0, 2, 0): "honey_block",
         (0, 0, 0): "hopper[facing=down,enabled=true]", (0, 1, 1): "observer[facing=north]",
         (0, 1, 2): "stone", (2, 1, 0): REP_W, (0, 1, -1): "repeater[facing=north]"}
    t = trace(b, {"m": [(0, 1, 0)], "a": [(2, 1, 0)]})
    assert t.owner[(1, 1, 0)] == "m" and t.how[(1, 1, 0)] == "glue"
    assert t.owner[(-1, 1, 0)] is None and t.owner[(0, 2, 0)] is None and t.owner[(0, 0, 0)] is None
    assert t.owner[(0, 1, 1)] == "m" and t.owner[(0, 1, 2)] == "m"         # a glued observer fires into its back
    assert t.owner[(0, 1, -1)] is None                                      # repeaters pop, never glued


def test_fixed_cells_stop_every_trace_and_seed_clashes_raise():
    b = {(0, 1, 0): REP_E, (1, 1, 0): "quartz_block", (2, 1, 0): REP_E}
    t = trace(b, {"a": [(0, 1, 0)]}, fixed={(1, 1, 0): "door"})
    assert t.owner[(1, 1, 0)] == "door" and t.owner[(2, 1, 0)] is None
    with pytest.raises(ValueError):
        trace(b, {"a": [(0, 1, 0)], "b": [(0, 1, 0)]})
    with pytest.raises(ValueError):
        trace(b, {"a": [(9, 9, 9)]})


def test_counts_and_disagreements():
    t = trace(line(), {"a": [(0, 1, 0)]})
    assert t.counts()["a"] == 6 and t.counts()[None] == 2
    assert t.disagreements({(1, 1, 0): "a", (3, 1, 0): "b"}) == [((3, 1, 0), "b", "a")]


def test_block_rules():
    assert is_conductor("stone") and is_conductor("minecraft:red_concrete") and is_conductor("note_block")
    assert not is_conductor("glass") and not is_conductor("slime_block") and not is_conductor("observer[facing=up]")
    assert not is_conductor("waxed_copper_bulb[lit=false]")
    assert is_movable("stone") and is_movable("observer[facing=up]") and is_movable("note_block")
    assert not is_movable("obsidian") and not is_movable("hopper") and not is_movable("repeater[facing=up]")
    assert not is_movable("sticky_piston[facing=up,extended=true]")
    assert support_of((0, 1, 0), "redstone_wall_torch[facing=east]") == (-1, 1, 0)
    assert support_of((0, 1, 0), "lever[face=wall,facing=north]") == (0, 1, 1)
    assert support_of((0, 1, 0), "comparator[facing=north]") == (0, 0, 0)
    assert support_of((0, 1, 0), "stone") is None
