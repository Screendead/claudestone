"""Helpers: door-coordinate builds for sim.py, per-tick door-plane maps, schedule checks."""
import sys
sys.setrecursionlimit(50000)
from scripts.door2.sim import World, B, AIR, DIRS, add

FRAME = [(x, y) for x in range(3) for y in range(3)]
DOORNAMES = {(0, 2): "TL", (1, 2): "TM", (2, 2): "TR", (0, 1): "L", (1, 1): "C", (2, 1): "R",
             (0, 0): "BL", (1, 0): "BM", (2, 0): "BR"}
SLOTS = [(x, -1) for x in range(3)] + [(x, 3) for x in range(3)] + [(-1, y) for y in range(3)] + [(3, y) for y in range(3)]


def ring_cell(x, y):
    return ((x in (-1, 3) and 0 <= y <= 2) or (y in (-1, 3) and 0 <= x <= 2))


class Build:
    def __init__(self, hall=(-3, 6)):
        self.b = {}
        self.role = {}
        self.hall = hall
        self.fixture = set()

    def put(self, p, st, role=None, fixture=False, force=False):
        if isinstance(st, str):
            from simyaml import parse_state
            st = parse_state(st)
        x, y, z = p
        if z != 0 and 0 <= x <= 2 and 0 <= y <= 2 and self.hall[0] <= z <= self.hall[1] and st.n != "air":
            raise ValueError(f"{st} in hallway at {p} ({role})")
        if z != 0 and ring_cell(x, y) and self.hall[0] <= z <= self.hall[1] and st.n != "quartz" and not force:
            raise ValueError(f"{st} in hallway wall at {p} ({role})")
        if p in self.b and self.b[p] != st and not force:
            raise ValueError(f"overlap at {p}: {self.b[p]} ({self.role.get(p)}) vs {st} ({role})")
        self.b[p] = st
        if role:
            self.role[p] = role
        if fixture:
            self.fixture.add(p)
        return p

    def piston(self, p, facing, role, sticky=True, extended=False):
        self.put(p, B("sticky_piston" if sticky else "piston", facing=facing, extended=extended), role)
        if extended:
            self.put(add(p, DIRS[facing]), B("piston_head", facing=facing, sticky=sticky), role + "^")
        return p

    def walls(self):
        for z in range(self.hall[0], self.hall[1] + 1):
            if z == 0:
                continue
            for x in range(-1, 4):
                for y in range(-1, 4):
                    if ring_cell(x, y):
                        self.b[(x, y, z)] = B("quartz")
                        self.role[(x, y, z)] = "wall"


def plane_map(w, z=0, xr=(-3, 6), yr=(-3, 7), roles=None):
    out = []
    for y in range(yr[1], yr[0] - 1, -1):
        row = f"{y:>3} "
        for x in range(xr[0], xr[1] + 1):
            st = w.get((x, y, z))
            n = st.n
            if n == "air":
                s = " ."
            elif n in ("piston", "sticky_piston"):
                f = st.p["facing"]
                s = {"up": "P^", "down": "Pv", "east": "P>", "west": "P<", "north": "Pn", "south": "Ps"}[f]
                if st.p["extended"]:
                    s = s.lower()
            elif n == "piston_head":
                s = "hh"
            elif n == "moving_piston":
                be = w.be.get((x, y, z))
                s = "m" + (be.moved.n[0] if be else "?")
            elif n == "quartz":
                s = "##"
                if roles and roles.get((x, y, z)):
                    s = roles[(x, y, z)][:2].ljust(2)
            elif n == "rb":
                s = "RB"
            elif n == "redstone_wire":
                s = "--" if st.p.get("power", 0) else "__"
            elif n == "repeater":
                s = "r+" if st.p["powered"] else "r-"
            else:
                s = n[:2]
            row += " " + s
        out.append(row)
    out.append("    " + "".join(f"{x:>3}" for x in range(xr[0], xr[1] + 1)))
    return "\n".join(out)


def frame_state(w):
    """list of frame cells holding a door block (real or moving into/out? -> real or moving at the cell)."""
    occ = []
    for (x, y) in FRAME:
        st = w.get((x, y, 0))
        if st.n != "air":
            occ.append((x, y, st.n))
    return occ


def track(w, label_pos):
    """label_pos: dict label -> (x,y,z) of door blocks; returns where each quartz door block is by scanning."""
    pass
