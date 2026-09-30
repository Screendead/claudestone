"""Areas of the shared world, one per stream of work, so that several agents can build at
once and a player can watch each build land in its own bordered square.

Every plot's floor is the world surface (y=56 on the redstone preset). The border is
drawn outside the plot, two blocks clear of it, so it is never part of a test's
neighbourhood and a plot's clear never erases it.
"""

from dataclasses import dataclass
from pathlib import Path

from .build import Pos

SURFACE = 56


@dataclass(frozen=True)
class Plot:
    name: str
    origin: Pos
    size: Pos
    colour: str


MAIN = Plot("main", (128, SURFACE, 128), (192, 24, 192), "white")

# Building-block plots, north of the main area in rows of four.
FAMILIES = ["not", "or", "and", "xor",
            "wire", "vertical_wire", "crossing", "delay",
            "rs_latch", "d_latch", "t_flip_flop", "pulse",
            "clock", "adder", "mux", "decoder",
            "counter", "shift_register", "analog", "seven_segment"]
# Workbenches for proving how individual blocks behave (library/mechanics).
FAMILIES += [f"mechanics_{i}" for i in range(1, 9)]
COLOURS = ["red", "orange", "yellow", "lime", "green", "cyan", "light_blue", "blue",
           "purple", "magenta", "pink", "brown", "red", "orange", "yellow", "lime",
           "green", "cyan", "light_blue", "blue"] + ["white", "light_gray"] * 4
SIZE = (48, 32, 48)
PITCH = 56

PLOTS = {MAIN.name: MAIN} | {
    f: Plot(f, (128 + PITCH * (i % 4), SURFACE, 72 - PITCH * (i // 4)), SIZE, COLOURS[i])
    for i, f in enumerate(FAMILIES)}

# Library folders that share another building block's plot; a folder named after a plot
# uses it, and the rest (mechanics, builds, input) have none.
FOLDER_PLOT = {"nand": "and", "nor": "or", "xnor": "xor", "binary_decoder": "decoder", "encoder": "decoder",
               "bcd_to_7seg": "seven_segment", "d_flip_flop": "d_latch", "demux": "mux",
               "dual_edge": "pulse", "falling_edge": "pulse", "rising_edge": "pulse",
               "pulse_extender": "pulse", "pulse_limiter": "pulse", "full_adder": "adder",
               "half_adder": "adder", "register": "shift_register", "signal_strength": "analog"}


def plot_for(path) -> Plot | None:
    """The plot for a library file, from its folder, or None if its folder has none."""
    folder = Path(path).parent.name
    name = FOLDER_PLOT.get(folder, folder)
    return PLOTS[name] if name in PLOTS and name != MAIN.name else None
