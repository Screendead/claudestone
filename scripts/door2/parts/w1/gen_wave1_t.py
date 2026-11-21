"""Part 3 reduced to what the geometry allows without new cuts: starter X_C, gate G_W, W1 to T only, D_W.
Door coords; design_c + part 1 (I_A sticky). Run from the repo root: python -m scripts.door2.parts.w1.gen_wave1_t [--export]"""
import os, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.setrecursionlimit(50000)
os.environ.setdefault("DESIGN", "design_c")
from scripts.door2 import design_c as d
from scripts.door2.sim import World, B, AIR, DIRS, add, power_sources

X_C, S_X, G_W = (1, 7, -1), (2, 7, -1), (3, 7, -1)
D_W, S_D, RB_W, ARM_DW = (2, 8, -1), (3, 8, -1), (4, 8, -1), (2, 8, 0)
H2_RESERVE = (2, 9, -1)
LIVE = [(4, 8, -2), (3, 7, -2)]                 # RB_W -> (4,8,-2) -> (3,7,-2): live side of the gate
W1 = [(3, 6, -1)]                                # L0: the dead side's first cell (no wave piston is reachable)
SUPPORT = {(4, 7, -2): "stone", (3, 6, -2): "stone", (3, 5, -1): "glass"}   # upper ends of down-steps conduct
T_STONE = None
DRIVER = (-1, 8, -2)


def base_build():
    b = d.build_open()
    d.route_nets(b)
    b.b[(1, 7, -2)] = B("sticky_piston", facing="down", extended=False, id="I_A")   # part 1
    return b


def build():
    b = base_build()
    from scripts.door2 import volume as v
    occ = set(v.cumulative_cells(b)[0])
    mine = {}

    def put(p, st, role):
        assert p not in b.b, (p, b.b[p], role)
        assert p not in occ, (p, role)
        b.put(p, st, role)
        mine[p] = role

    put(X_C, B("piston", facing="east", extended=False, id="X_C"), "X_C")
    put(S_X, B("obsidian"), "S_X")               # blocker while the door opens; stone set strict before the close
    put(G_W, B("stone", id="G_W"), "G_W")
    put(D_W, B("piston", facing="east", extended=False, id="D_W"), "D_W")
    put(S_D, B("stone"), "S_D")
    put(RB_W, B("rb", id="RB_W"), "RB_W")
    for c in LIVE + W1:
        sup = add(c, (0, -1, 0))
        put(sup, B(SUPPORT[sup]), "W1_s")
        put(c, B("redstone_wire", power=0), "W1" if c in W1 else "LIVE")
    return b, mine


def scaffold(w):
    w.cmd_set_silent(S_X, B("stone"))
    w.cmd_set_silent(ARM_DW, B("rb"))


def simulate(b, open_ticks=14, close_ticks=12, drop_dw=False):
    w, _ = d.make_world(b)
    w.run(4)
    w.log.clear()
    w.cmd_set(DRIVER, B("rb"))
    for _ in range(open_ticks):
        w.tick()
    open_log = list(w.log)
    scaffold(w)
    if drop_dw:
        w.cmd_set_silent(D_W, AIR)
    w.log.clear()
    t_in = w.time
    w.cmd_set(DRIVER, AIR)
    frames = {}
    for _ in range(close_ticks):
        w.tick()
        c = w.time - t_in - 2
        frames[c] = copy.deepcopy(w.b)
    return w, t_in, open_log, frames


def show(w, t_in, open_log, frames):
    for (t, ph, m) in open_log:
        if any(str(p) in m for p in [X_C, D_W]) or "X_C" in m or "D_W" in m:
            print("OPENING", t, ph, m)
    for (t, ph, m) in w.log:
        if any(k in m for k in ("EXTEND", "RETRACT", "queue", "skipped", "dropped", "cancel", "failed")):
            print(f"  c{t - t_in - 2:+d}{ph} {m}")
    for c, bb in sorted(frames.items()):
        g = lambda p: bb.get(p, AIR)
        print(f"c{c}: (1,2)={g((1,2,0))} (1,3)={g((1,3,0))} T={g((1,4,0))} P12={g((0,5,0))} (0,3)={g((0,3,0))} "
              f"X_C={g(X_C)} D_W={g(D_W)} Z_T={g((1,4,-1))} L0={g(W1[0])} live={g(LIVE[1])} (3,7,-1)={g(G_W)} (4,7,-1)={g((4,7,-1))} (5,8,-1)={g((5,8,-1))}")


if __name__ == "__main__":
    b, mine = build()
    print("added", len(mine), sorted(mine.items()))
    r = simulate(b)
    show(*r)
    print("---- control: no D_W")
    b2, _ = build()
    show(*simulate(b2, drop_dw=True))
