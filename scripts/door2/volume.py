"""Cumulative Squid volume of the opening: bounding box of every cell any circuitry block or moving block
occupies from the closed state through the open state, excluding frame, door blocks, hallway (interior and
wall ring), static quartz slots and the fixture input repeater/driver."""
import importlib, os
d_mod = importlib.import_module("scripts.door2." + os.environ.get("DESIGN", "design_open"))
globals().update({k: getattr(d_mod, k) for k in dir(d_mod) if not k.startswith("__")})
from scripts.door2.doorkit import ring_cell

FIXTURE = {(0, 8, -2), (-1, 8, -2), (0, 7, -2)}   # R_in, its driver, R_in's support
DOORIDS = set(DOOR.values()) | {"s1", "s2"}


def excluded(p, st, be=None):
    x, y, z = p
    if z == 0 and 0 <= x <= 2 and 0 <= y <= 2:
        return True                     # frame
    if z != 0 and ((0 <= x <= 2 and 0 <= y <= 2) or ring_cell(x, y)):
        return True                     # hallway interior and wall ring (quartz fitting the type)
    if p in FIXTURE:
        return True
    ident = st.p.get("id") if st else None
    if be is not None:
        ident = be.moved.p.get("id")
    if ident in DOORIDS:
        return True                     # door blocks and static slot quartz, wherever they are
    return False


def cumulative_cells(b, ticks=14):
    w, moved = make_world(b)
    cells = {}
    def snap(tag):
        for p, st in w.b.items():
            be = w.be.get(p)
            if st.n == "air" or excluded(p, st, be):
                continue
            cells.setdefault(p, (tag, st.n if not be else "moving:" + be.moved.n))
    snap("closed")
    w.run(4)
    t_in = w.time
    w.cmd_set((-1, 8, -2), B("rb"))
    for i in range(ticks):
        w.tick()
        snap(f"t{w.time - t_in - 2}")
    return cells, w


if __name__ == "__main__":
    b = build_open(); route_nets(b)
    cells, w = cumulative_cells(b)
    xs = [c[0] for c in cells]; ys = [c[1] for c in cells]; zs = [c[2] for c in cells]
    W, H, D = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, max(zs) - min(zs) + 1
    print(f"box x {min(xs)}..{max(xs)} y {min(ys)}..{max(ys)} z {min(zs)}..{max(zs)} -> {W} x {H} x {D} = {W*H*D}")
    print("cells occupied:", len(cells))
    for axis, name in ((0, "x"), (1, "y"), (2, "z")):
        lo = min(c[axis] for c in cells); hi = max(c[axis] for c in cells)
        print(name, "min set by", sorted({(c, cells[c][1], b.role.get(c, '')) for c in cells if c[axis] == lo})[:6])
        print(name, "max set by", sorted({(c, cells[c][1], b.role.get(c, '')) for c in cells if c[axis] == hi})[:6])
