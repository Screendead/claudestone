"""Package a library build as a data pack a player can drop into any world.

    python -m scripts.package two_digit_adder

writes dist/<name>/ (and a .zip). In game, stand where you want the front of the build,
face south, then run /function <name>:prepare and /function <name>:build.
The placing function is the exact text the tests ran; the wrapper only positions it.
"""

import shutil
import sys
from pathlib import Path

from redstone.build import write_datapack
from redstone.fileformat import load

ROOT = Path(__file__).resolve().parent.parent
FILL_LIMIT = 32768


def package(name: str, front: tuple[int, int, int] | None = None) -> Path:
    spec = load(ROOT / "library" / f"{name}.redstone.yaml")
    (lo_x, lo_y, lo_z), (hi_x, hi_y, hi_z) = spec.build.bounds()
    # Put the player at the middle of the build's north edge, one block in front of it,
    # with the base one block below their feet.
    ox, oy, oz = front or (-(lo_x + hi_x) // 2, -1, 2)
    x0, x1, z0, z1 = ox + lo_x, ox + hi_x, oz + lo_z, oz + hi_z
    y0, y1 = oy + lo_y, oy + hi_y + 2
    prepare = [f"forceload add ~{x0} ~{z0} ~{x1} ~{z1}",
               'tellraw @s {"text":"Area loaded. Now run /function %s:build" ,"color":"green"}' % name]
    build = []
    for x in range(x0, x1 + 1, 32):
        for z in range(z0, z1 + 1, 32):
            layers = max(1, FILL_LIMIT // (32 * 32))
            for y in range(y0, y1 + 1, layers):
                build.append(f"fill ~{x} ~{y} ~{z} ~{min(x + 31, x1)} ~{min(y + layers - 1, y1)} "
                             f"~{min(z + 31, z1)} air strict")
    build.append(f"execute positioned ~{ox} ~{oy} ~{oz} run function {name}:place")
    build.append('tellraw @s {"text":"Built %s.","color":"green"}' % name)
    out = ROOT / "dist"
    if (out / name).exists():
        shutil.rmtree(out / name)
    pack = write_datapack(out, name, {"prepare": "\n".join(prepare) + "\n",
                                      "build": "\n".join(build) + "\n",
                                      "place": spec.build.to_mcfunction()})
    shutil.make_archive(str(out / name), "zip", pack)
    return pack


if __name__ == "__main__":
    print(package(sys.argv[1]))
