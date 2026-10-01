import pytest

from redstone import door_timing as dt
from redstone.door_timing import AIR, DOOR, HEAD, MOVING, SURFACE, Cell, Entity, Moving, Observation, Run

# A 1x2 door facing north: hallway x=2, y=1..2, z=0..4, frame at z=2. A sticky piston at x=0
# facing east keeps each door block in the wall cell x=1 when open and pushes it into the frame.
H = dt.Hallway.of([(2, y, z) for y in (1, 2) for z in range(5)], [(2, y, 2) for y in (1, 2)], "north")
FRAME = [(2, 1, 2), (2, 2, 2)]
WALL = [(1, 1, 2), (1, 2, 2)]
HOLD = 45


def obs(cells=None, entities=()):
    base = {p: Cell(SURFACE) for p in H.surface} | {p: Cell(AIR) for p in H.hallway}
    return Observation(base | (cells or {}), tuple(entities))


def moving(moved, progress, extending=True, source=False, facing="east"):
    return Cell(MOVING, Moving(moved, progress, extending, source, facing))


def run(before, frames):
    return Run(before, frames + [frames[-1]] * HOLD)


def each(cells, cell):
    return {p: cell for p in cells}


OPEN = obs(each(WALL, Cell(DOOR)))
CLOSED = obs(each(FRAME, Cell(DOOR)) | each(WALL, Cell(HEAD)))


def pull_open(extra=None, entities=None):
    """Standard 2 gt open: the extended sticky piston retracts, pulling the door blocks."""
    frames = [obs(each(WALL, moving(DOOR, 0.0, extending=False))),
              obs(each(WALL, moving(DOOR, 0.5, extending=False))),
              OPEN]
    for t, cells in (extra or {}).items():
        while len(frames) <= t:
            frames.append(OPEN)
        frames[t] = obs({**frames[t].cells, **cells})
    for t, es in (entities or {}).items():
        frames[t] = obs(frames[t].cells, es)
    return run(CLOSED, frames + [OPEN])


def push_close():
    """Standard 2 gt close: door blocks pushed into the frame, the arm following into the wall."""
    return run(OPEN, [obs(each(FRAME, moving(DOOR, 0.0)) | each(WALL, moving(HEAD, 0.0, source=True))),
                      obs(each(FRAME, moving(DOOR, 0.5)) | each(WALL, moving(HEAD, 0.5, source=True))),
                      CLOSED])


def test_front_is_frame_plane_and_the_north_side():
    assert (2, 1, 0) in H.front and (1, 1, 2) in H.front and (2, 3, 2) in H.front
    assert (2, 1, 3) not in H.front and (3, 2, 4) not in H.front


def test_two_gt_open():
    r = pull_open()
    w, period = dt.settle(r)
    assert (w, period) == (2, 1)
    assert dt.opening_time(H, r, w) == 2
    assert dt.visible_time(H, r, w) == 2
    # The frame cells emptying at tick 0 belong to the pull, not to instant moves ending at 0.
    assert [(m.cell, m.origin, m.start, m.end) for m in dt.movements(r, H.visible)] == [
        ((1, 1, 2), (2, 1, 2), 0, 2), ((1, 2, 2), (2, 2, 2), 0, 2)]


def test_two_gt_close_and_super_seamless():
    o, c = pull_open(), push_close()
    t = dt.door_times(H, o, c)
    assert (t.open, t.open_visible, t.close, t.close_visible) == (2, 2, 2, 2)
    s = dt.seamless(H, o, t.w_open, c, t.w_close)
    assert s == dt.Seamless("L", "L", "L", "L", "L") and s.tier() == "SUPER"


def test_zero_tick_close():
    # The block is spat into the frame within tick 0; no moving_piston is ever seen.
    c = run(OPEN, [CLOSED])
    w, _ = dt.settle(c)
    assert w == 0
    assert dt.closing_time(H, c, w) == 0
    assert dt.visible_time(H, c, w) == 0
    assert dt.seamless(H, pull_open(), 2, c, w).closing == "L"


def test_cut_pulse_ends_one_tick_after_start():
    c = run(OPEN, [obs(each(FRAME, moving(DOOR, 0.0))), CLOSED])
    assert {m.end - m.start for m in dt.movements(c, H.visible) if m.cell in FRAME} == {1}
    assert dt.closing_time(H, c, dt.settle(c)[0]) == 1


def test_a_move_starting_as_the_last_lands_is_a_second_movement():
    # Seen live in LegDen's 10x10: progress 0.0, 0.5, 0.0, 0.5 in one cell.
    floor = (2, 0, 1)
    r = pull_open({3: {floor: moving(SURFACE, 0.0, facing="up")}, 4: {floor: moving(SURFACE, 0.5, facing="up")},
                   5: {floor: moving(SURFACE, 0.0, facing="down")}, 6: {floor: moving(SURFACE, 0.5, facing="down")}})
    assert [(m.start, m.end) for m in dt.movements(r, H.visible) if m.cell == floor] == [(3, 5), (5, 7)]


def test_z_fighting_wall_swap_counts_only_as_visible():
    floor = (2, 0, 1)
    r = pull_open({3: {floor: moving(SURFACE, 0.0, facing="up")},
                   4: {floor: moving(SURFACE, 0.5, facing="up")}})
    w, _ = dt.settle(r)
    assert w == 5
    assert dt.opening_time(H, r, w) == 2
    assert dt.visible_time(H, r, w) == 5
    assert dt.seamless(H, r, w, push_close(), 2).tier() == "SUPER"


def test_wall_motion_behind_closed_door_is_not_visible():
    # After the door lands, the arm cell behind it changes; nobody in the hallway sees it.
    c = run(OPEN, [push_close().ticks[0], push_close().ticks[1], CLOSED,
                   obs(each(FRAME, Cell(DOOR)) | each(WALL, Cell(dt.OTHER)))])
    w, _ = dt.settle(c)
    assert w == 3
    assert dt.visible_time(H, c, w) == 2
    assert dt.seamless(H, pull_open(), 2, c, w).closed == "L"


def test_entity_visible_mid_motion_drops_super_to_full():
    cart = Entity("minecraft:minecart", frozenset({(2, 1, 1)}))
    o = pull_open(entities={1: (cart,)})
    s = dt.seamless(H, o, 2, push_close(), 2)
    assert s.opening == "D" and s.tier() == "FULL"
    ghost = Entity("minecraft:armor_stand", frozenset({(2, 1, 1)}), invisible=True)
    assert dt.seamless(H, pull_open(entities={1: (ghost,)}), 2, push_close(), 2).tier() == "SUPER"


def test_head_seen_while_closing_is_circuitry():
    # The frame is air while the head passes the wall cell beside it.
    c = run(OPEN, [obs(each(WALL, moving(HEAD, 0.0, source=True))), CLOSED])
    s = dt.seamless(H, pull_open(), 2, c, 1)
    assert s.closing is None and s.tier() == "FULL"


def test_hole_in_open_wall_is_circuitry():
    hole = OPEN.cells | {(3, 1, 3): Cell(AIR)}
    o = run(CLOSED, pull_open().ticks[:2] + [obs(hole)])
    s = dt.seamless(H, o, 2, push_close(), 2)
    assert s.opened is None and s.tier() == "QUART"


def test_tier_table():
    L, D = "L", "D"
    assert dt.Seamless(L, L, L, D, L).tier() == "FULL"
    assert dt.Seamless(L, L, D, L, L).tier() == "SEMI"
    assert dt.Seamless(D, D, None, None, None).tier() == "SEMI"
    assert dt.Seamless(D, None, L, L, L).tier() == "QUART"
    assert dt.Seamless(None, L, L, L, L).tier() is None


def test_visible_clock_sets_visible_time_to_stable_state():
    floor = (2, 0, 3)
    cycle = [{floor: moving(SURFACE, 0.0, facing="up")}, {floor: moving(SURFACE, 0.5, facing="up")}, {}, {}]
    frames = pull_open({3 + i: cycle[i % 4] for i in range(4 * 20)}).ticks[:3 + 4 * 20]
    r = Run(CLOSED, frames)
    w, period = dt.settle(r)
    assert (w, period) == (2, 4)
    assert dt.opening_time(H, r, w) == 2
    assert dt.visible_time(H, r, w) == w


def test_short_periodic_tail_is_quiescent():
    floor = (2, 0, 3)
    cycle = [{floor: moving(SURFACE, 0.0, facing="up")}, {floor: moving(SURFACE, 0.5, facing="up")}, {}, {}]
    frames = pull_open({3 + i: cycle[i % 4] for i in range(4 * 5)}).ticks[:3 + 4 * 5]
    assert dt.quiescence(Run(CLOSED, frames)) == (2, 4)


def test_short_static_tail_is_not_quiescent():
    assert dt.quiescence(Run(CLOSED, [OPEN] * 20)) is None
    assert dt.quiescence(Run(CLOSED, [CLOSED] * 3 + [OPEN] * 41)) == (3, 1)


def test_visible_clock_quiet_at_the_stable_tick_still_gives_w():
    floor = (2, 0, 3)
    cycle = [{}, {}, {floor: moving(SURFACE, 0.0, facing="up")}, {floor: moving(SURFACE, 0.5, facing="up")}]
    frames = pull_open({3 + i: cycle[i % 4] for i in range(4 * 20)}).ticks[:3 + 4 * 20]
    r = Run(CLOSED, frames)
    w, period = dt.settle(r)
    assert (w, period) == (3, 4)
    assert dt.visible_time(H, r, w) == 3


def test_unbounded_run_fails():
    floor = (2, 0, 3)
    frames = pull_open().ticks[:3] + [obs({floor: Cell(SURFACE if i % (i // 10 + 2) else DOOR)}) for i in range(60)]
    with pytest.raises(dt.DoorError):
        dt.settle(Run(CLOSED, frames))


@pytest.mark.parametrize("ladder", [[0.0, 0.5, 0.5], [0.5], [0.0, 0.0]])
def test_progress_ladder_disagreement(ladder):
    frames = [obs(each(FRAME, moving(DOOR, p))) for p in ladder] + [CLOSED]
    with pytest.raises(dt.TimingModelError):
        dt.movements(run(OPEN, frames), H.visible)


def test_closed_pattern_must_hold_after_last_door_move():
    frames = [CLOSED, obs(CLOSED.cells | {(2, 1, 1): Cell(HEAD)})]
    with pytest.raises(dt.DoorError):
        dt.closing_time(H, run(OPEN, frames), 1)


def test_reset_negative():
    scan = dt.reset_search(lambda k: k >= 3, 2, 12, visible=4)
    assert scan.k_star == 3 and scan.reset == -1
    assert list(scan.results) == list(range(2, 13))


def test_reset_needs_every_later_offset():
    tried = []

    def trial(k):
        tried.append(k)
        return k >= 3 and k != 6

    scan = dt.reset_search(trial, 2, 12, visible=2)
    assert tried == list(range(2, 13))
    assert scan.k_star == 7 and scan.reset == 5


def test_reset_both_directions_and_no_pass():
    closing = dt.reset_search(lambda k: True, 1, 5, visible=2)
    assert (closing.k_star, closing.reset) == (1, -1)
    assert dt.reset_search(lambda k: k < 5, 1, 5, visible=2).k_star is None


def _quiescence_by_definition(keys, quiet=dt.QUIET_TICKS, max_period=dt.MAX_PERIOD, periods=dt.PERIODS):
    n = len(keys)
    for t in range(n):
        if all(k == keys[t] for k in keys[t:]):
            return (t, 1) if n - 1 - t >= quiet else None
        for p in range(2, max_period + 1):
            if n - 1 - t < periods * p:
                break
            if all(keys[i] == keys[i + p] for i in range(t, n - p)):
                return t, p
    return None


def test_quiescence_agrees_with_its_definition_on_random_runs():
    import random
    rnd = random.Random(7)
    frames = [CLOSED, OPEN, obs({(2, 0, 3): Cell(SURFACE)})]
    for _ in range(400):
        head = [rnd.randrange(3) for _ in range(rnd.randrange(0, 30))]
        cyc = [rnd.randrange(3) for _ in range(rnd.choice([1, 1, 2, 3, 5]))]
        keys = head + cyc * rnd.randrange(0, 60)
        quiet = rnd.choice([1, 5, 40])
        run = Run(CLOSED, [frames[k] for k in keys])
        want = _quiescence_by_definition([f.key() for f in run.ticks], quiet, 8)
        assert dt.quiescence(run, quiet, 8) == want
        assert dt.quiescence(run, quiet, 8, keys=keys) == want


def test_quiet_sets_the_static_evidence():
    r = Run(CLOSED, [CLOSED] * 3 + [OPEN] * 41)
    assert dt.quiescence(r, quiet=41) is None and dt.settle(r, quiet=40) == (3, 1)
