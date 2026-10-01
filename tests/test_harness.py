import pytest

from redstone import servers
from redstone.docker_sats import DOCKER_SATELLITES
from redstone.harness import IDLE_RATE, SPRINT_MIN, WARP_RATE, CommandFailed, Rig, checked, clear_commands
from redstone.plots import FOLDER_PLOT, PLOTS, plot_for
from redstone.library import LIBRARY, path_of


class Stub:
    def __init__(self, reply):
        self.reply = reply

    def cmd(self, command):
        return self.reply


def test_checked_raises_on_unloaded_position():
    with pytest.raises(CommandFailed):
        checked(Stub("That position is not loaded"), "setblock 0 0 0 stone")
    assert checked(Stub("Changed the block at 0, 0, 0"), "setblock 0 0 0 stone")


def test_clear_kills_around_and_above_the_plot():
    *fills, kill = clear_commands((100, 56, 200), (48, 32, 48))
    assert all(f.startswith("fill ") and f.endswith("air strict") for f in fills)
    assert kill == ("kill @e[type=!player,tag=!plot_label,tag=!plot_status,tag=!watch_cam,"
                    "x=98,y=56,z=198,dx=51,dy=263,dz=51]")


def test_every_building_block_folder_has_a_plot():
    folders = {p.name for p in LIBRARY.iterdir() if p.is_dir()} - {"mechanics", "builds", "input"}
    assert {f for f in folders if plot_for(LIBRARY / f / "x.redstone.yaml") is None} == set()
    assert set(FOLDER_PLOT.values()) <= set(PLOTS)
    assert plot_for(path_of("seg_dec_bcd")).name == "seven_segment"
    assert plot_for(LIBRARY / "mechanics" / "x.redstone.yaml") is None
    assert plot_for(path_of("ref_wiki_subtraction_xor_basic")).name == "references"


def test_plots_do_not_overlap():
    # Borders and labels stand 2 blocks outside each plot, so keep 5 clear between plots.
    boxes = [(p.name, p.origin[0], p.origin[2], p.origin[0] + p.size[0], p.origin[2] + p.size[2])
             for p in PLOTS.values()]
    for i, (a, ax0, az0, ax1, az1) in enumerate(boxes):
        for b, bx0, bz0, bx1, bz1 in boxes[i + 1:]:
            assert ax1 + 5 <= bx0 or bx1 + 5 <= ax0 or az1 + 5 <= bz0 or bz1 + 5 <= az0, (a, b)


def test_only_runs_that_build_in_mains_copy_of_a_plot_hold_its_lock_throughout():
    sat1, sat6 = servers.SERVERS["sat1"], servers.SERVERS["sat6"]
    assert servers.holds_plot_lock("main", [sat6])
    assert servers.holds_plot_lock("xor", [servers.MAIN])
    assert not servers.holds_plot_lock("xor", [sat1, sat6])
    assert servers.plot_lock("xor").name == "xor.lock"
    assert servers.plot_lock("xor", sat6).name == "xor@sat6.lock"
    assert servers.pinned("auto") is None
    assert servers.pinned("sat1,dsat2") == [sat1, servers.SERVERS["dsat2"]]


class Clock:
    """Game time advances by a `tick step`, or a `tick sprint` as 26.3 runs it (n + 1 ticks
    for n >= 2); `fail_at` makes that gametime query raise."""

    def __init__(self, fail_at=None):
        self.time, self.log, self.fail_at, self.queries = 0, [], fail_at, 0

    def cmd(self, command):
        self.log.append(command)
        if command.startswith("tick step "):
            self.time += int(command.split()[-1])
            return f"Stepping {command.split()[-1]} tick(s)"
        if command.startswith("tick sprint "):
            n = int(command.split()[-1])
            self.time += n + 1 if n >= 2 else n
            return "The game is sprinting"
        if command == "tick query":
            return "The game is frozenTarget tick rate: 20.0 per second."
        if command == "time query gametime":
            self.queries += 1
            if self.queries == self.fail_at:
                raise ConnectionError("rcon dropped")
            return f"The time is {self.time}"
        return ""


def _rig(clock, server=servers.MAIN):
    rig = Rig.__new__(Rig)
    rig.r = clock
    rig.rate, rig.idle_rate = IDLE_RATE, IDLE_RATE if server == servers.MAIN else WARP_RATE
    rig.sprint = server != servers.MAIN
    return rig


def test_advance_raises_the_tick_rate_only_for_the_batch():
    clock = Clock()
    _rig(clock)._advance(5)
    rates = [c for c in clock.log if c.startswith("tick rate")]
    assert rates == [f"tick rate {WARP_RATE}", f"tick rate {IDLE_RATE}"]
    assert clock.log.index(f"tick rate {WARP_RATE}") < clock.log.index("tick step 5")
    assert clock.log[-1] == f"tick rate {IDLE_RATE}" and clock.time == 5
    clock.log.clear()
    _rig(clock)._advance(0)
    assert clock.log == []


def test_advance_restores_the_tick_rate_when_polling_fails():
    clock = Clock(fail_at=2)
    with pytest.raises(ConnectionError):
        _rig(clock)._advance(3)
    assert clock.log[-1] == f"tick rate {IDLE_RATE}"


@pytest.mark.parametrize("server", [servers.SATELLITES[0], DOCKER_SATELLITES[0]], ids=lambda s: s.name)
def test_satellites_stay_at_warp_rate_between_batches(server):
    clock = Clock()
    rig = _rig(clock, server)
    for n in (5, 3, 170):
        rig._advance(n)
    assert [c for c in clock.log if c.startswith("tick rate")] == [f"tick rate {WARP_RATE}"]
    assert clock.time == 178
    assert [c for c in clock.log if c.startswith("tick ")][1:3] == ["tick step 5", "tick step 3"]
    rig.release()
    assert clock.log[-2:] == [f"tick rate {IDLE_RATE}", "tick unfreeze"]


@pytest.mark.parametrize("server", [servers.SATELLITES[0], DOCKER_SATELLITES[0]], ids=lambda s: s.name)
def test_satellites_sprint_long_waits_to_the_same_tick(server):
    clock = Clock()
    rig = _rig(clock, server)
    for n in (SPRINT_MIN - 1, SPRINT_MIN, 6400):
        start = clock.time
        rig._advance(n)
        assert clock.time - start == n
    steps = [c for c in clock.log if c.startswith(("tick step", "tick sprint"))]
    assert steps == [f"tick step {SPRINT_MIN - 1}", f"tick sprint {SPRINT_MIN - 1}", "tick sprint 6399"]


def test_main_never_sprints():
    clock = Clock()
    _rig(clock)._advance(6400)
    assert "tick step 6400" in clock.log and not any("sprint" in c for c in clock.log)


def test_main_releases_without_a_second_rate_change():
    clock = Clock()
    rig = _rig(clock)
    rig._advance(2)
    clock.log.clear()
    rig.release()
    assert clock.log == ["tick unfreeze"]
