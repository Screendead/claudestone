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

# Building-block plots, north of the main area in rows of five, all one square size.
FAMILIES = ["not", "or", "and", "xor", "wire",
            "vertical_wire", "crossing", "delay", "rs_latch", "d_latch",
            "t_flip_flop", "pulse", "clock", "adder", "mux",
            "decoder", "counter", "shift_register", "analog", "seven_segment"]
# Workbenches for proving how individual blocks behave (library/mechanics).
FAMILIES += [f"mechanics_{i}" for i in range(1, 9)]
# Rebuilt community designs (library/<block>/ref_*), the baselines in docs/WINS.md, stand
# apart from our own designs; then builds for survival play (library/survival) and storage
# tech (library/storage).
FAMILIES += ["references", "survival", "storage"]
COLOURS = ["red", "orange", "yellow", "lime", "green", "cyan", "light_blue", "blue",
           "purple", "magenta", "pink", "brown", "red", "orange", "yellow", "lime",
           "green", "cyan", "light_blue", "blue"] + ["white", "light_gray"] * 4 + ["black", "lime", "purple"]
SIZE = (72, 32, 72)
# With its border a plot spans 76 blocks; at a pitch of 80 from x and z origins 2 past a
# chunk edge, each plot forceloads exactly 5 x 5 chunks.
PITCH = 80
COLUMNS = 5

PLOTS = {MAIN.name: MAIN} | {
    f: Plot(f, (130 + PITCH * (i % COLUMNS), SURFACE, 50 - PITCH * (i // COLUMNS)), SIZE, COLOURS[i])
    for i, f in enumerate(FAMILIES)}
REFERENCES = PLOTS["references"]
# Piston doors up to 16x16 with their mechanism, apart from the grid: east of main and south
# of the grid's last column, x and z origins 2 past a chunk edge, so with its border it
# forceloads 8 x 8 chunks.
BIGDOOR = Plot("bigdoor", (370, SURFACE, 210), (112, 64, 112), "gray")
PLOTS[BIGDOOR.name] = BIGDOOR
# A computer and its parts, south of main, x and z origins 2 past a chunk edge: cpu
# forceloads 8 x 8 chunks with its border, cpu_parts 5 x 5.
CPU = Plot("cpu", (130, SURFACE, 370), (120, 48, 120), "black")
CPU_PARTS = Plot("cpu_parts", (258, SURFACE, 370), SIZE, "gray")
PLOTS[CPU.name] = CPU
PLOTS[CPU_PARTS.name] = CPU_PARTS

# Library folders that share another building block's plot; a folder named after a plot
# uses it, and the rest (mechanics, builds, input) have none.
FOLDER_PLOT = {"nand": "and", "nor": "or", "xnor": "xor", "binary_decoder": "decoder", "encoder": "decoder",
               "bcd_to_7seg": "seven_segment", "d_flip_flop": "d_latch", "demux": "mux",
               "dual_edge": "pulse", "falling_edge": "pulse", "rising_edge": "pulse",
               "pulse_extender": "pulse", "pulse_limiter": "pulse", "full_adder": "adder",
               "half_adder": "adder", "register": "shift_register", "signal_strength": "analog",
               "door": BIGDOOR.name}


def plot_for(path) -> Plot | None:
    """The plot for a library file: references for a ref_* file, else from its folder, or
    None if its folder has none."""
    if Path(path).name.startswith("ref_"):
        return REFERENCES
    folder = Path(path).parent.name
    name = FOLDER_PLOT.get(folder, folder)
    return PLOTS[name] if name in PLOTS and name != MAIN.name else None
