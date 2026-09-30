import pytest

from redstone.harness import CommandFailed, checked, clear_commands
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
