"""Design B (mirrored: slot pistons in the top slots), block-level generator.

Door coordinates: x right, y up, z along the hallway; door plane z=0; frame x,y in 0..2.
Everything is built through Build.put so hallway/wall violations raise.
"""
import sys
from scripts.door2.doorkit import Build, B, add
from scripts.door2.sim import World, AIR

Q = lambda ident: B("quartz", id=ident)
DOOR = {(0, 2): "TL", (1, 2): "TM", (2, 2): "TR", (0, 1): "L", (1, 1): "C", (2, 1): "R",
        (0, 0): "BL", (1, 0): "BM", (2, 0): "BR"}


def pis(b, p, facing, name, sticky=True, ext=False):
    b.put(p, B("sticky_piston" if sticky else "piston", facing=facing, extended=ext, id=name), name)
    if ext:
        from scripts.door2.sim import DIRS
        b.put(add(p, DIRS[facing]), B("piston_head", facing=facing, sticky=sticky), name + "^")


def dust(b, p, name, support="glass"):
    b.put(p, B("redstone_wire", power=0), name)
    below = (p[0], p[1] - 1, p[2])
    if below not in b.b:
        b.put(below, B(support), name + "_s")


def rb(b, p, name):
    b.put(p, B("rb", id=name), name)


def door_plane(b):
    for c, n in DOOR.items():
        b.put((c[0], c[1], 0), Q(n), n)
    b.put((-1, 0, 0), Q("s1"), "static")
    b.put((3, 0, 0), Q("s2"), "static")
    pis(b, (0, -2, 0), "up", "P1", ext=True)
    pis(b, (1, -2, 0), "up", "P2", ext=True)
    pis(b, (2, -2, 0), "up", "P3", ext=True)
    pis(b, (-2, 1, 0), "east", "P4", ext=True)
    pis(b, (-2, 2, 0), "east", "P6", ext=True)
    pis(b, (4, 1, 0), "west", "P5", ext=True)
    pis(b, (2, 4, 0), "down", "P7", ext=True)
    pis(b, (3, 4, 0), "down", "P8", ext=True)
    pis(b, (3, 2, 0), "west", "Q")
    pis(b, (4, 2, 0), "west", "P9")
    pis(b, (-1, 3, 0), "east", "V", ext=True)
    pis(b, (1, 3, 0), "down", "S")
    pis(b, (1, 4, 0), "down", "T")
    pis(b, (-1, 5, 0), "down", "P10", ext=True)
    pis(b, (-2, 3, 0), "east", "P11")
    pis(b, (0, 5, 0), "down", "P12")
    b.put((0, 4, 0), Q("SP"), "spare")


def build(variant=None):
    b = Build(hall=(-4, 7))
    b.walls()
    door_plane(b)
    wiring(b)
    return b


def rep(b, p, facing, name, delay=1, support="glass"):
    b.put(p, B("repeater", facing=facing, delay=delay, powered=(name != "R_in")), name)
    below = (p[0], p[1] - 1, p[2])
    if below not in b.b:
        b.put(below, B(support), name + "_s")


def wiring(b):
    # ---- input and P7 feed (NA) ----
    rep(b, (1, 5, -5), "north", "R_in")              # fixture input repeater: input from (1,5,-6)
    pis(b, (1, 5, -4), "south", "I_A", sticky=False)  # pushes RB_A (1,5,-3) -> (1,5,-2): Z_T's QC cell
    rb(b, (1, 5, -3), "RB_A")
    dust(b, (2, 5, -3), "D7e")                        # support (2,4,-3) glass
    dust(b, (2, 4, -2), "D7b", support="quartz")      # sits on ceiling (2,3,-2)
    dust(b, (2, 4, -1), "D7a", support="quartz")      # sits on ceiling (2,3,-1); points S into P7
    b.put((3, 4, -1), B("stone"), "cut_DQ")           # keeps DQ-side dust off the NA net


# ---------------- running ----------------
TRACK = ["TL", "TM", "TR", "L", "C", "R", "BL", "BM", "BR", "SP",
         "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "Q", "P9", "V", "S", "T", "P10", "P11", "P12"]


def simulate(b, drive, ticks=14, settle=20, show=True, extra_track=()):
    w = World()
    w.load(b.b)
    w.run(settle)
    w.log.clear()
    start = w.time
    for p in drive:
        w.cmd_set(p, B("rb"))
    hist = []
    for i in range(ticks):
        w.tick()
        snap = {}
        for n in list(TRACK) + list(extra_track):
            snap[n] = w.find(n)
        hist.append((w.time - start, snap))
    return w, start, hist


def door_report(w, start, hist, t0_offset=2):
    lines = []
    for t, snap in hist:
        tt = t - t0_offset
        frame = [n for n in DOOR.values() if snap[n][0] and 0 <= snap[n][0][0] <= 2 and 0 <= snap[n][0][1] <= 2 and snap[n][0][2] == 0]
        lines.append(f"t{tt:+d}: frame={frame}")
    return "\n".join(lines)


if __name__ == "__main__":
    b = build()
    print(len(b.b), "blocks")
    w, start, hist = simulate(b, [(1, 5, -6)], ticks=10)
    for t in w.log: print(t)
