"""Draw every plot's border and name in the world: python -m scripts.plots"""

import json

from redstone.harness import ensure_server
from redstone.plots import MAIN, PLOTS
from redstone.rcon import Rcon

GAP = 2  # border distance from the plot's edge


def draw(r: Rcon) -> None:
    r.cmd("kill @e[type=text_display,tag=plot_label]")
    r.cmd("kill @e[type=text_display,tag=plot_status]")
    for p in PLOTS.values():
        (ox, oy, oz), (sx, sy, sz) = p.origin, p.size
        x0, z0, x1, z1 = ox - GAP, oz - GAP, ox + sx - 1 + GAP, oz + sz - 1 + GAP
        r.cmd(f"forceload add {x0} {z0} {x1} {z1}")
        ground = f"{p.colour}_concrete"
        for a, b in (((x0, z0), (x1, z0)), ((x0, z1), (x1, z1)), ((x0, z0), (x0, z1)), ((x1, z0), (x1, z1))):
            r.cmd(f"fill {a[0]} {oy - 1} {a[1]} {b[0]} {oy - 1} {b[1]} {ground}")
        for x, z in ((x0, z0), (x0, z1), (x1, z0), (x1, z1)):
            r.cmd(f"fill {x} {oy} {z} {x} {oy + sy - 1} {z} {p.colour}_stained_glass")
        text = json.dumps({"text": p.name, "color": "white", "bold": True})
        r.cmd(f"summon text_display {ox + sx / 2} {oy + 3} {z0 - 1} "
              f"{{Tags:[plot_label],billboard:\"center\",text:{text},"
              f"transformation:{{scale:[8f,8f,8f],translation:[0f,0f,0f],"
              f"left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]}}}}")
        if p.name != MAIN.name:
            r.cmd(f"summon text_display {ox + sx / 2} {oy + sy + 2} {oz + sz / 2} "
                  f"{{Tags:[plot_status,{p.name}],billboard:\"center\",line_width:300,background:-1442840576,"
                  f"text:{{text:\"idle\",color:\"#DDDDDD\"}},"
                  f"transformation:{{scale:[7f,7f,7f],translation:[0f,0f,0f],"
                  f"left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]}}}}")


if __name__ == "__main__":
    ensure_server()
    draw(Rcon())
