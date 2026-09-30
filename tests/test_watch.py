"""redstone.watch offline: framing, the event readers, the shot scheduler and the director
against a fake RCON."""

import json
import math
import os
import random
import time

import pytest

from redstone import watch as w
from redstone.plots import MAIN, PLOTS, SURFACE

CFG = dict(w.DEFAULTS)


def test_look_known_directions():
    t = (0.0, 64.0, 0.0)
    assert w.look((0, 64, -10), t) == pytest.approx((0, 0))       # north of it: face south
    assert w.look((10, 64, 0), t) == pytest.approx((90, 0))       # east of it: face west
    assert w.look((-10, 64, 0), t) == pytest.approx((-90, 0))     # west of it: face east
    assert abs(w.look((0, 64, 10), t)[0]) == pytest.approx(180)   # south of it: face north
    assert w.look((0, 74, 0.0001), t)[1] == pytest.approx(90, abs=0.01)  # above: look down
    assert w.look((0, 64 + 10, -10), t) == pytest.approx((0, 45))


def test_facing_is_the_inverse_of_look():
    for yaw, pitch in [(0, 0), (90, 30), (-45, 60), (170, -20)]:
        d = w.facing(yaw, pitch)
        assert w.look((0, 0, 0), d) == pytest.approx((yaw, pitch))


def test_offset_gives_yaw_azimuth_and_pitch_elevation():
    for az, el in [(0, 35), (20, 35), (-20, 50), (90, 10)]:
        eye = tuple(3 * x for x in w.offset(az, el))
        assert w.look(eye, (0, 0, 0)) == pytest.approx((az, el))


def _projections(box, eye, yaw, pitch):
    f = w.facing(yaw, pitch)
    r, u = w.basis(f)
    for p in w.corners(box):
        q = tuple(a - b for a, b in zip(p, eye))
        fwd = sum(a * b for a, b in zip(q, f))
        yield sum(a * b for a, b in zip(q, r)) / fwd, sum(a * b for a, b in zip(q, u)) / fwd, fwd


@pytest.mark.parametrize("seed", range(40))
def test_fit_puts_every_corner_inside_the_field_of_view_and_one_on_the_margin(seed):
    rnd = random.Random(seed)
    lo = [rnd.uniform(-50, 50), rnd.uniform(56, 70), rnd.uniform(-50, 50)]
    box = tuple(lo + [a + rnd.uniform(1, 40) for a in lo])
    az, el = rnd.uniform(-30, 30), rnd.uniform(20, 60)
    d = w.fit_distance(box, az, el)
    eye, yaw, pitch = w.Framing(box, el, d, azimuth=az).pose(0)
    assert (yaw, pitch) == pytest.approx((az, el))
    th, tv = w.half_tangents(CFG["fov"], CFG["aspect"])
    m = CFG["margin"]
    worst = 0
    for x, y, fwd in _projections(box, eye, yaw, pitch):
        assert fwd > 0
        assert abs(x) <= th * m + 1e-9 and abs(y) <= tv * m + 1e-9
        worst = max(worst, abs(x) / (th * m), abs(y) / (tv * m))
    assert worst == pytest.approx(1)


def test_horizontal_field_follows_the_aspect():
    th, tv = w.half_tangents(70, 16 / 9)
    assert math.degrees(2 * math.atan(th)) == pytest.approx(102.45, abs=0.05)
    assert tv == pytest.approx(math.tan(math.radians(35)))
    # A wide flat box needs more distance in 4:3 than in 16:9.
    box = (0, 56, 0, 40, 57, 2)
    assert w.fit_distance(box, 0, 35, aspect=4 / 3) > w.fit_distance(box, 0, 35)


def test_fit_with_a_sideways_slide_keeps_the_box_in_view_at_both_ends():
    box = (0, 56, 0, 9, 60, 3)
    d = w.fit_distance(box, 0, 35, lateral=0.2)
    assert d > w.fit_distance(box, 0, 35)
    f = w.Framing(box, 35, d, dolly=0.2)
    th, tv = w.half_tangents(CFG["fov"], CFG["aspect"])
    for phase in (-1, -0.5, 0, 0.5, 1):
        eye, yaw, pitch = f.pose(phase)
        assert (yaw, pitch) == pytest.approx(f.pose(0)[1:])  # slides without turning
        for x, y, fwd in _projections(box, eye, yaw, pitch):
            assert abs(x) <= th * CFG["margin"] + 1e-9 and abs(y) <= tv * CFG["margin"] + 1e-9
    assert math.dist(f.pose(1)[0], f.pose(-1)[0]) == pytest.approx(0.4 * d)


@pytest.mark.parametrize("motion", ["orbit", "dolly"])
def test_frame_keeps_the_eye_clear_of_posts_labels_and_other_slots(motion):
    """A small slot on the north edge of a plot with a long name: the plain camera spot is
    in the plot's label."""
    plot = PLOTS["mechanics_1"]
    ox, oy, oz = plot.origin
    cx = ox + plot.size[0] / 2
    box = (cx - 2, oy, oz, cx + 2, oy + 3, oz + 1)
    obstacles = w.fixed_obstacles() + [(cx + 4, oy, oz, cx + 9, oy + 4, oz + 3)]
    plain = w.Framing(box, CFG["elevation"], w.fit_distance(box, 0, CFG["elevation"]))
    assert not w.clear(plain.pose()[0], w.centre(box), obstacles)
    f = w.frame(box, obstacles, CFG, motion)
    assert f.sway or f.dolly
    th, tv = w.half_tangents(CFG["fov"], CFG["aspect"])
    for phase in [x / 80 for x in range(-80, 81)]:
        eye, yaw, pitch = f.pose(phase)
        assert w.clear(eye, w.centre(box), obstacles)
        assert eye[1] - w.EYE >= SURFACE
        for x, y, fwd in _projections(box, eye, yaw, pitch):
            assert abs(x) <= th and abs(y) <= tv and fwd > 0


def test_frame_without_motion_is_still():
    f = w.frame((0, 56, 0, 4, 58, 4), [], CFG, None)
    assert f.sway == f.dolly == 0 and f.pose(1) == f.pose(-1)


def test_motion_starts_still_and_stays_within_its_ends():
    assert w.phase_at(0, CFG) == 0
    assert abs(w.phase_at(0.05, CFG)) < 0.0001
    dt = 1 / CFG["rate"]
    steps = [w.phase_at(i * dt, CFG) for i in range(int(3 * CFG["period"] / dt))]
    assert max(map(abs, steps)) <= 1 + 1e-9 and max(map(abs, steps)) > 0.99
    assert max(abs(a - b) for a, b in zip(steps, steps[1:])) < 2 * 2 * math.pi * dt / CFG["period"]


def test_slot_box_covers_the_centred_build_and_its_label():
    ox, oy, oz = PLOTS["and"].origin
    e = {"slot": [6, 0], "size": [3, 2, 1], "box": [6, 1]}
    assert w.slot_box("and", e) == (ox + 7, oy, oz, ox + 10, oy + 4, oz + 1)


# ---- scheduler -----------------------------------------------------------------------------

def shot(spec, t, priority=w.PLAIN, plot="main", kind="test", box=(0, 56, 0, 4, 58, 4)):
    return w.Shot(plot, spec, box, kind, "running", t, priority)


def test_scheduler_holds_a_shot_for_the_dwell_then_takes_the_newest():
    s = w.Scheduler(dict(CFG, dwell=8))
    s.offer(shot("a", 0), 0)
    assert s.pick(0, [])[0].spec == "a"
    s.offer(shot("b", 1), 1)
    s.offer(shot("c", 2), 2)
    assert s.pick(7.9, []) == (s.current, False) and s.current.spec == "a"
    got, cut = s.pick(8, [])
    assert cut and got.spec == "c"
    assert s.pick(16, [])[0].spec == "b"


def test_scheduler_prefers_failures_then_new_variants():
    s = w.Scheduler(CFG)
    s.offer(shot("a", 0), 0)
    s.pick(0, [])
    s.offer(shot("fail", 1, w.FAIL), 1)
    s.offer(shot("new", 2, w.NEW), 2)
    s.offer(shot("live", 3, w.LIVE), 3)
    assert [s.pick(t, [])[0].spec for t in (8, 16, 24)] == ["fail", "new", "live"]


def test_scheduler_updates_the_current_shot_without_a_cut():
    s = w.Scheduler(CFG)
    s.offer(shot("a", 0), 0)
    s.pick(0, [])
    s.offer(w.Shot("main", "a", (0, 56, 0, 4, 58, 4), "result", "fail", 3, w.FAIL, "row 2"), 3)
    assert not s.pending and s.current.status == "fail"
    assert s.pick(9, []) == (s.current, False)


def test_scheduler_drops_stale_events():
    s = w.Scheduler(dict(CFG, stale=30))
    s.offer(shot("a", 0), 0)
    s.pick(0, [])
    s.offer(shot("old", 1), 1)
    assert s.pick(40, [])[0].spec == "a"


def test_scheduler_tours_recent_builds_when_idle():
    s = w.Scheduler(dict(CFG, dwell=8, tour_dwell=16))
    tour = [shot("t1", 0, kind="placed"), shot("t2", 0, kind="placed")]
    s.offer(shot("a", 0), 0)
    s.pick(0, tour)
    assert s.pick(10, tour) == (s.current, False)  # held past the dwell: nothing new yet
    got, cut = s.pick(16, tour)
    assert cut and got.kind == "tour" and got.spec in ("t1", "t2")
    first = got.spec
    got, _ = s.pick(32, tour)
    assert got.spec != first
    s.offer(shot("b", 33), 33)
    assert s.pick(40, tour)[0].spec == "b"  # an event beats the tour after the dwell


def test_scheduler_keeps_a_live_shot_while_it_updates():
    s = w.Scheduler(dict(CFG, dwell=8, tour_dwell=16))
    tour = [shot("t", 0, kind="placed")]
    s.offer(shot("a", 0), 0)
    s.pick(0, tour)
    for t in range(1, 40, 3):
        s.offer(shot("a", t), t)
        assert s.pick(t, tour)[0].spec == "a"


# ---- sources -------------------------------------------------------------------------------

def _showroom(dir, plot, specs):
    (dir / f"{plot}.json").write_text(json.dumps({"specs": specs}))


def _entry(t, result="pass", slot=(0, 0)):
    return {"slot": list(slot), "size": [3, 2, 1], "box": [4, 1], "tested": t,
            "results": {"logic": {"result": result, "delay": 2}}}


def test_sources_read_new_events_and_wait_for_a_whole_line(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(json.dumps({"kind": "test", "plot": "main", "server": "main", "spec": "old",
                                  "box": [0, 0, 0, 1, 1, 1], "time": 1}) + "\n")
    src = w.Sources(events, tmp_path, tmp_path / "traces", start=100)
    assert src.poll(100) == []  # what was there before the director started is not news
    ev = {"kind": "test", "plot": "main", "server": "main", "spec": "s", "test": "t",
          "box": [128, 56, 128, 131, 58, 129], "time": 101}
    line = json.dumps(ev)
    with open(events, "a") as f:
        f.write(line[:10])
    assert src.poll(101) == []
    with open(events, "a") as f:
        f.write(line[10:] + "\n" + json.dumps(dict(ev, kind="result", passed=False, time=102)) + "\n")
    got = src.poll(102)
    assert [(s.kind, s.status, s.priority) for s in got] == [("test", "running", w.LIVE),
                                                             ("result", "fail", w.FAIL)]
    assert got[0].box == (128, 56, 128, 131, 58, 129)


def test_event_shots_only_for_what_stands_on_main():
    base = {"plot": "and", "spec": "s", "box": [1, 2, 3, 4, 5, 6], "time": 1}
    assert w.event_shot(dict(base, kind="test", server="sat1")) is None
    assert w.event_shot(dict(base, kind="test", server="main")).kind == "test"
    assert w.event_shot(dict(base, kind="result", server="sat1", passed=True)) is None
    assert w.event_shot(dict(base, kind="result", plot="main", server="sat1", passed=True)).status == "pass"


def test_sources_find_new_and_updated_showroom_entries(tmp_path):
    _showroom(tmp_path, "and", {"a": _entry(50)})
    src = w.Sources(tmp_path / "none.jsonl", tmp_path, tmp_path / "traces", start=100)
    assert src.poll(100) == []
    _showroom(tmp_path, "and", {"a": _entry(110), "b": _entry(111, "fail", (6, 0)), "c": _entry(112, slot=(12, 0))})
    got = {s.spec: s for s in src.poll(112)}
    assert got["a"].priority == w.PLAIN and got["b"].priority == w.FAIL and got["c"].priority == w.NEW
    assert got["c"].detail.startswith("new")
    assert src.poll(113) == []


def test_sources_fall_back_to_traces_while_the_event_log_is_quiet(tmp_path):
    spec = tmp_path / "x.redstone.yaml"
    spec.write_text("x")
    traces = tmp_path / "traces" / "x"
    traces.mkdir(parents=True)
    src = w.Sources(tmp_path / "none.jsonl", tmp_path, tmp_path / "traces", start=time.time() - 5)
    src._main_box = lambda path: (128, 56, 128, 130, 57, 129)
    (traces / "t.json").write_text(json.dumps({"spec": str(spec), "name": "x", "test": "a \"b\"",
                                               "sparse": True, "failures": ["tick 3: no"], "frames": []}))
    got = src.poll(time.time())
    assert [(s.spec, s.detail, s.status) for s in got] == [("x", 'a "b"', "fail")]
    assert src.poll(time.time()) == []
    (tmp_path / "none.jsonl").write_text("")
    os.utime(traces / "t.json", (time.time() + 1, time.time() + 1))
    assert src.poll(time.time()) == []  # the event log is live: it has this test already


# ---- director ------------------------------------------------------------------------------

class FakeRcon:
    def __init__(self, players=("Jack",), modes=None):
        self.players, self.modes, self.log = list(players), dict(modes or {}), []
        self.cams, self.frozen = set(), False

    def cmd(self, c):
        self.log.append(c)
        if c == "list":
            return f"There are {len(self.players)} of a max of 20 players online: " + ", ".join(self.players)
        if c.endswith("playerGameType"):
            p = c.split()[3]
            return f"{p} has the following entity data: {self.modes.get(p, 1)}"
        if c.startswith("execute as ") and " run gamemode " in c:
            p, mode = c.split()[2], c.split()[-1]
            self.modes[p] = w.GAMEMODES.index(mode)
        if c == "tick query":
            return ("The game is frozen" if self.frozen else "The game is running normally") + \
                "Target tick rate: 20.0 per second."
        if c.startswith("execute at ") and " run summon item_display" in c:
            self.cams.add(c.split()[2])
        if c == f"kill {w.CAM_SELECTOR}":
            self.cams.clear()
        if c.startswith("kill @e[type=item_display,tag=watch_cam_"):
            self.cams.discard(c.split("watch_cam_")[1].rstrip("]"))
        if c.startswith("execute if entity @e[type=item_display,tag=watch_cam_"):
            return "Test passed" if c.split("watch_cam_")[1].split(",")[0] in self.cams else "Test failed"
        return ""

    def since(self, i, prefix):
        return [c for c in self.log[i:] if c.startswith(prefix)]


def _director(tmp_path, rcon, **cfg):
    src = w.Sources(tmp_path / "events.jsonl", tmp_path, tmp_path / "traces", start=0)
    return w.Director(rcon, src, dict(CFG, **cfg), state_path=tmp_path / "state.json", config_path=None,
                      status_dir=tmp_path / "status", showroom=tmp_path, fallback="creative")


def _run(d, start, end, rate=20):
    for i in range(int(start * rate), int(end * rate)):
        d.tick(i / rate)


def _pose(command):
    return tuple(map(float, command.split()[2:7]))


def test_director_watches_players_and_restores_them_on_opt_out(tmp_path):
    rcon = FakeRcon(["Jack", "Spec"], {"Jack": 0, "Spec": 3})
    d = _director(tmp_path, rcon)
    d.tick(0)
    assert "execute as Jack run gamemode spectator" in rcon.log and "tag Jack add watch" in rcon.log
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["gamemode"] == {"Jack": "survival", "Spec": "creative"}
    rcon.log.clear()
    d.tick(1.1)
    assert not [c for c in rcon.log if "gamemode" in c and "playerGameType" not in c or c.startswith("tag")]
    with w.State(tmp_path / "state.json") as s:
        s["optout"].append("Jack")
    d.tick(2.2)
    assert "execute as Jack run gamemode survival" in rcon.log and "tag Jack remove watch" in rcon.log
    assert d.watched == ["Spec"]


def test_director_picks_up_a_player_who_joins(tmp_path):
    rcon = FakeRcon([])
    d = _director(tmp_path, rcon)
    d.tick(0)
    assert d.watched == []
    rcon.players.append("Late")
    d.tick(1.5)
    assert d.watched == ["Late"] and "execute as Late run gamemode spectator" in rcon.log


GLIDE = f"tp {w.CAM_SELECTOR} "
DURATION = f"execute as {w.CAM_SELECTOR} run data merge entity @s {{teleport_duration:"


def test_entity_camera_attaches_once_then_snaps_to_the_shot_and_glides(tmp_path):
    rcon = FakeRcon()
    _showroom(tmp_path, "and", {"a": _entry(10)})
    d = _director(tmp_path, rcon)
    d.tick(0)
    summon, = rcon.since(0, "execute at Jack run summon item_display ~ ~ ~ ")
    assert '"watch_cam","watch_cam_Jack"' in summon and "teleport_duration:0" in summon
    assert not rcon.since(0, "spectate")  # not before the client has the entity
    _run(d, 0.05, 1.5)
    spectate = f"spectate @e[type=item_display,tag=watch_cam_Jack,limit=1] Jack"
    assert rcon.log.count(spectate) >= 1
    # A snap after attaching: duration 0, then the teleport, then the glide duration.
    after = rcon.log[rcon.log.index(spectate):]
    snap = [c for c in after if c.startswith((DURATION, GLIDE))][:3]
    assert snap[0] == DURATION + "0}" and snap[1].startswith(GLIDE) and snap[2] == DURATION + f"{w.cam_ticks(CFG)}}}"
    assert w.cam_ticks(CFG) == 6
    n = len(rcon.log)
    _run(d, 1.5, 11.5)
    glides = [_pose(c) for c in rcon.since(n, GLIDE)]
    assert 38 <= len(glides) <= 41  # every 0.25 s
    assert len({g[3:] for g in glides}) == 1  # a dolly never turns
    box = w.slot_box("and", _entry(10))
    for a, b in zip(glides, glides[1:]):
        assert math.dist(a[:3], b[:3]) < 0.1
    assert max(math.dist(glides[0][:3], g[:3]) for g in glides) > 0.3
    for g in glides:
        assert g[1] >= SURFACE + w.GROUND_CLEARANCE
    assert not rcon.since(0, "tp @a")  # the players themselves are never teleported
    assert rcon.since(n, spectate)  # re-sent each second: sneaking detaches
    assert len(rcon.since(0, "execute at")) == 1
    bars = rcon.since(0, "title @a[tag=watch] actionbar")
    assert 22 <= len(bars) <= 26 and '"a"' in bars[0] and "green" in bars[0]


def test_entity_camera_cut_snaps_without_new_entities(tmp_path):
    rcon = FakeRcon()
    _showroom(tmp_path, "and", {"a": _entry(10)})
    d = _director(tmp_path, rcon)
    _run(d, 0, 3)
    n = len(rcon.log)
    _showroom(tmp_path, "and", {"a": _entry(10), "b": _entry(100, "fail", (12, 0))})
    d.sources.start = 0
    _run(d, 3, 10)
    assert d.shot.spec == "b"
    assert not rcon.since(n, ("execute at", "kill", "tp @a"))
    assert rcon.since(n, DURATION + "0}")


def test_entity_camera_holds_still_while_main_is_frozen(tmp_path):
    rcon = FakeRcon()
    _showroom(tmp_path, "and", {"a": _entry(10)})
    d = _director(tmp_path, rcon)
    _run(d, 0, 5)
    rcon.frozen = True
    _run(d, 5, 5.5)
    t, n = d.motion_t, len(rcon.log)
    _run(d, 5.5, 10)
    assert not rcon.since(n, GLIDE) and d.motion_t == t
    rcon.frozen = False
    _run(d, 10, 10.6)
    assert rcon.since(n, GLIDE) and d.motion_t - t < 0.3  # eases back in


def test_entity_camera_comes_back_when_cleared_away(tmp_path):
    rcon = FakeRcon()
    _showroom(tmp_path, "and", {"a": _entry(10)})
    d = _director(tmp_path, rcon)
    _run(d, 0, 2)
    rcon.cams.clear()  # a plot clear killed it
    n = len(rcon.log)
    _run(d, 2, 4.5)
    assert len(rcon.since(n, "execute at Jack run summon")) == 1
    assert rcon.since(n, "spectate @e[type=item_display,tag=watch_cam_Jack,limit=1] Jack")
    assert not rcon.since(n, "tp @a")


def test_entity_camera_goes_with_its_watcher(tmp_path):
    rcon = FakeRcon(["Jack", "Ann"])
    _showroom(tmp_path, "and", {"a": _entry(10)})
    d = _director(tmp_path, rcon)
    _run(d, 0, 2)
    assert rcon.cams == {"Jack", "Ann"}
    rcon.players = ["Ann"]
    _run(d, 2, 3.5)
    assert rcon.cams == {"Ann"}
    rcon.players = []
    _run(d, 3.5, 5)
    assert rcon.cams == set()


def test_tp_camera_orbits_by_teleporting_the_players(tmp_path):
    rcon = FakeRcon()
    _showroom(tmp_path, "and", {"a": _entry(10)})
    d = _director(tmp_path, rcon, camera="tp", motion="orbit")
    _run(d, 0, 10)
    tps = [_pose(c) for c in rcon.since(0, "tp @a[tag=watch]")]
    assert 190 <= len(tps) <= 200 and not rcon.since(0, ("execute at", "spectate"))
    box = w.slot_box("and", _entry(10))
    for a, b in zip(tps, tps[1:]):
        assert math.dist(a[:3], b[:3]) < 0.1
    for x, y, z, yaw, pitch in tps:
        assert w.look((x, y + w.EYE, z), w.centre(box)) == pytest.approx((yaw, pitch), abs=0.02)


def test_director_without_motion_holds_still(tmp_path):
    rcon = FakeRcon()
    _showroom(tmp_path, "and", {"a": _entry(10)})
    d = _director(tmp_path, rcon, orbit=False)
    _run(d, 0, 5)
    assert len(set(rcon.since(0, GLIDE))) == 1  # snaps to the shot only (before and after attaching)


def test_director_shows_live_status_of_a_test(tmp_path):
    rcon = FakeRcon()
    d = _director(tmp_path, rcon)
    d.tick(0)
    (tmp_path / "status").mkdir()
    (tmp_path / "status" / "main.json").write_text(json.dumps({"text": "row 3/8  a=1", "time": time.time()}))
    ev = {"kind": "test", "plot": "main", "server": "main", "spec": "latch", "test": "holds",
          "box": [128, 56, 128, 131, 58, 129], "time": time.time() - 0.5}
    (tmp_path / "events.jsonl").write_text(json.dumps(ev) + "\n")
    d.sources.offset = 0
    d.tick(1)
    assert d.shot.spec == "latch"
    assert "row 3/8" in rcon.since(0, "title")[-1]


def test_nobody_watching_sends_no_camera_commands(tmp_path):
    rcon = FakeRcon([])
    _showroom(tmp_path, "and", {"a": _entry(10)})
    d = _director(tmp_path, rcon)
    _run(d, 0, 2)
    assert not rcon.since(0, ("tp", "execute at", "title", "execute as", "spectate"))


def test_tick_query_parsing():
    assert w.running_normally("The game is running normallyTarget tick rate: 20.0 per second.")
    assert not w.running_normally("The game is frozenTarget tick rate: 20.0 per second.")
    assert not w.running_normally("The game is running normallyTarget tick rate: 10000.0 per second.")


# ---- writers -------------------------------------------------------------------------------

@pytest.fixture
def watch_dir(tmp_path, monkeypatch):
    for name, value in {"DIR": tmp_path, "EVENTS": tmp_path / "events.jsonl", "STATUS": tmp_path / "status",
                        "CONFIG": tmp_path / "config.json", "LOCK": tmp_path / "director.lock",
                        "LOG": tmp_path / "director.log", "STATE": tmp_path / "state.json"}.items():
        monkeypatch.setattr(w, name, value)
    monkeypatch.delenv("REDSTONE_WATCH", raising=False)
    return tmp_path


def test_emit_and_status_never_raise(watch_dir, monkeypatch):
    w.emit("test", plot="main")
    w.set_status("main", "row 1")
    assert json.loads((watch_dir / "events.jsonl").read_text())["plot"] == "main"
    assert json.loads((watch_dir / "status" / "main.json").read_text())["text"] == "row 1"
    monkeypatch.setattr(w, "DIR", watch_dir / "events.jsonl" / "no")  # a file where a dir must be
    monkeypatch.setattr(w, "STATUS", watch_dir / "events.jsonl" / "no")
    w.emit("test", plot="main")
    w.set_status("main", "x")


def test_autostart_spawns_one_director_unless_turned_off(watch_dir, monkeypatch):
    spawned = []
    monkeypatch.setattr(w.subprocess, "Popen", lambda argv, **kw: spawned.append(argv))
    monkeypatch.setenv("REDSTONE_WATCH", "0")
    assert not w.autostart() and not spawned
    monkeypatch.delenv("REDSTONE_WATCH")
    w.save_config({"enabled": False})
    assert not w.autostart() and not spawned
    assert w.autostart(force=True) and spawned[-1][-2:] == ["scripts.watch", "run"]
    w.save_config({"enabled": True})
    import fcntl
    with open(w.LOCK, "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        assert w.running() and not w.autostart()
    n = len(spawned)
    assert w.autostart() and len(spawned) == n + 1


def test_config_keeps_only_changes_from_the_defaults(watch_dir):
    w.save_config({"orbit": False})
    assert json.loads((watch_dir / "config.json").read_text()) == {"orbit": False}
    assert w.load_config()["orbit"] is False and w.load_config()["dwell"] == CFG["dwell"]
    (watch_dir / "config.json").write_text("{half")
    assert w.load_config() == CFG


def test_spec_run_reports_to_the_director_and_shows_no_title(watch_dir, monkeypatch):
    from test_spec_offline import FakeRig, make_spec
    from redstone import spec as spec_module
    from redstone.build import Build
    from redstone.servers import MAIN as MAIN_SERVER

    monkeypatch.setattr(spec_module, "TRACE_DIR", watch_dir / "traces")
    started = []
    monkeypatch.setattr(w, "autostart", lambda: started.append(1))
    rig = FakeRig()
    rig.server, rig.origin = MAIN_SERVER, MAIN.origin
    commands = []
    rig.run = lambda c: commands.append(c) or ""
    real_load = rig.load

    def load(build, probe=None, drivers=frozenset()):
        real_load(build, probe, drivers)
        rig.loaded = build
    rig.load = load
    s = make_spec([{"expect": {"out": 1}}])
    s.build = Build().place((0, 0, 0), "stone").place((2, 1, 3), "stone")
    with pytest.raises(AssertionError):
        spec_module.run(rig, s, s.tests[0])
    events = [json.loads(line) for line in (watch_dir / "events.jsonl").read_text().splitlines()]
    ox, oy, oz = MAIN.origin
    assert [(e["kind"], e.get("passed")) for e in events] == [("test", None), ("result", False)]
    assert events[0]["box"] == [ox, oy, oz, ox + 3, oy + 2, oz + 4] and events[0]["server"] == "main"
    assert json.loads((watch_dir / "status" / "main.json").read_text())["text"].startswith("fake: expect")
    assert started and not [c for c in commands if c.startswith("title")]


def test_offline_fake_rig_reports_nothing(watch_dir, monkeypatch):
    from test_spec_offline import FakeRig, make_spec
    from redstone import spec as spec_module
    monkeypatch.setattr(spec_module, "TRACE_DIR", watch_dir / "traces")
    s = make_spec([])
    spec_module.run(FakeRig(), s, s.tests[0])
    assert not (watch_dir / "events.jsonl").exists()
