import pytest

from redstone.harness import IDLE_RATE, WARP_RATE, CommandFailed, Rig, checked, clear_commands
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
    assert kill == ("kill @e[type=!player,tag=!plot_label,tag=!plot_status,"
                    "x=98,y=56,z=198,dx=51,dy=263,dz=51]")


def test_every_building_block_folder_has_a_plot():
    folders = {p.name for p in LIBRARY.iterdir() if p.is_dir()} - {"mechanics", "builds", "input"}
    assert {f for f in folders if plot_for(LIBRARY / f / "x.redstone.yaml") is None} == set()
    assert set(FOLDER_PLOT.values()) <= set(PLOTS)
    assert plot_for(path_of("seg_dec_bcd")).name == "seven_segment"
    assert plot_for(LIBRARY / "mechanics" / "x.redstone.yaml") is None


class Clock:
    """Game time advances by a `tick step` only; `fail_at` makes that gametime query raise."""

    def __init__(self, fail_at=None):
        self.time, self.log, self.fail_at, self.queries = 0, [], fail_at, 0

    def cmd(self, command):
        self.log.append(command)
        if command.startswith("tick step "):
            self.time += int(command.split()[-1])
        if command == "time query gametime":
            self.queries += 1
            if self.queries == self.fail_at:
                raise ConnectionError("rcon dropped")
            return f"The time is {self.time}"
        return ""


def _rig(clock):
    rig = Rig.__new__(Rig)
    rig.r = clock
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
