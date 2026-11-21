"""Close feeds for T and P6 that need no change to design_c's opening blocks (door coords).

T  : stone FT (1,6,0) is a QC cell of T (and of P12, harmless once P12's retract event has run);
     dust DT (1,7,0) on it; stone cut CT (0,7,0) keeps DT and G12 (0,6,0) apart both ways.
     T is three cells from DT, so lighting DT does not update T. The wake is Z_T's retraction:
     moving RB_T off (1,6,-1) unpowers Z_T (head forwarding), and Z_T's retract event updates T.
P6 : fires with P11 (stage 2, after P12's retract). Stone FP (-3,3,0) powers P11 directly and P6 by QC
     through P11's cell; dust DP (-3,4,0) on it; stone cut CP (-3,4,-1) keeps DP off NA (-3,3,-1).
     DP's storm updates P11; P11's extension updates P6.
Probe sources (placed by command at close time): SRC_T (1,7,1) south of DT, SRC_P (-4,4,0) west of DP.
Run from the repo root: python -m scripts.door2.close_layout.feeds  (sim; replay-only)."""
import os, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.setrecursionlimit(50000)
os.environ.setdefault("DESIGN", "design_c")
from scripts.door2 import design_c as d
from scripts.door2.sim import B, AIR, add, power_sources

FT, DT, CT = (1, 6, 0), (1, 7, 0), (0, 7, 0)
FP, DP, CP = (-3, 3, 0), (-3, 4, 0), (-3, 4, -1)
SRC_T, SRC_P = (1, 7, 1), (-4, 4, 0)
R_T, SRC_R = (0, 6, -1), (0, 7, -1)   # RB_T mover: piston east, pushes RB_T (1,6,-1) -> (2,6,-1); probe power above it
RB12, RB_T, RB_A = (-4, 2, 2), (1, 6, -1), (1, 5, -2)
DRIVER = (-1, 8, -2)
ADDED = {FT: B("stone"), DT: B("redstone_wire", power=0), CT: B("stone"),
         FP: B("stone"), DP: B("redstone_wire", power=0), CP: B("stone")}
R_T_BLOCK = B("piston", facing="east", extended=False, id="R_T")
WATCH = ["T", "P7", "P8", "P9", "P10", "P11", "P12", "P1", "P2", "P3", "P4", "P5", "P6", "Q", "S", "V",
         "Z_T", "Z_Q", "Y1", "Z_S", "Z9", "Z11", "Y12", "X2", "I_A"]


def build(extra=True, with_rt=False):
    b = d.build_open()
    d.route_nets(b)
    if extra:
        from scripts.door2 import volume as v
        occ = set(v.cumulative_cells(b)[0])
        add_ = {**ADDED, **({R_T: R_T_BLOCK} if with_rt else {})}
        for p, st in add_.items():
            assert p not in b.b and p not in occ, p
            b.b[p] = st
            b.role[p] = "close"
    return b


def open_world(b, ticks=14):
    w, _ = d.make_world(b)
    w.run(4)
    w.log.clear()
    w.cmd_set(DRIVER, B("rb"))
    for _ in range(ticks):
        w.tick()
    return w


def snapshot(w):
    out = {}
    for n in WATCH:
        p, kind = w.find(n)
        st = w.get(p) if p else None
        out[n] = (p, kind, st.p.get("extended") if st is not None and kind == "real" else None)
    for c in [(x, y, 0) for x in range(-1, 4) for y in range(-1, 4)]:
        st = w.get(c)
        be = w.be.get(c)
        out[c] = (be.moved.p.get("id", be.moved.n) + "~") if be else (st.p.get("id", st.n))
    return out


def diff(a, b_):
    return {k: (a[k], b_[k]) for k in a if a[k] != b_[k]}


def close_probe(w, steps):
    """steps: list of (commands, ticks). commands: list of (pos, state or AIR)."""
    log = []
    k = 0
    for cmds, ticks in steps:
        for p, st in cmds:
            w.cmd_set(p, st)
        for _ in range(ticks):
            w.log.clear()
            w.tick()
            k += 1
            log += [f"k{k}{ph} {m}" for (t, ph, m) in w.log
                    if any(x in m for x in ("EXTEND", "RETRACT", "queue", "skipped", "failed", "cancel", "land"))]
    return log


if __name__ == "__main__":
    base = open_world(build(extra=False))
    mine = open_world(build(extra=True))
    sa, sb = snapshot(base), snapshot(mine)
    print("opening, design_c vs design_c+feeds, open-state differences:", diff(sa, sb) or "none")
    ref = {p: st for p, st in base.b.items()}
    dif = [p for p in set(ref) | set(mine.b) if p not in ADDED and ref.get(p) != mine.b.get(p)
           and not (ref.get(p) and mine.b.get(p) and ref[p].n == mine.b[p].n == "redstone_wire")]
    print("cell differences outside the added blocks:", dif or "none")
    print("added blocks in the open state:", {p: (mine.get(p), power_sources(mine, p) if mine.get(p).n in ("piston", "sticky_piston") else "") for p in ADDED})
    wrt = open_world(build(extra=True, with_rt=True))
    print("refuted RB_T mover R_T (0,6,-1) facing east: open-state block", wrt.get(R_T), "powered by", power_sources(wrt, R_T),
          "| RB_T now at", [p for p, st in wrt.b.items() if st.p.get("id") == "RB_T"] or "moving")

    cases = {
        # RB_A (1,5,-2) is taken away first: in the door E0 (I_A sticky, part 1) pulls it home in c0 g
        "A: kill NP12; next tick light T feed + remove RB_T": [([(RB_A, AIR), (RB12, AIR)], 1), ([(SRC_T, B("rb")), (RB_T, AIR)], 3)],
        "A-ctl1: T feed only (no Z_T wake)": [([(RB_A, AIR), (RB12, AIR)], 1), ([(SRC_T, B("rb"))], 3)],
        "A-ctl2: remove RB_T only (no T feed)": [([(RB_A, AIR), (RB12, AIR)], 1), ([(RB_T, AIR)], 3)],
        "A-ctl3: T feed lit before the NP12 kill": [([(RB_A, AIR), (SRC_T, B("rb"))], 1), ([(RB12, AIR)], 1), ([(RB_T, AIR)], 3)],
        "B: kill NP12; next tick light the P6+P11 feed": [([(RB12, AIR)], 1), ([(SRC_P, B("rb"))], 3)],
        "B-ctl: P6+P11 feed lit with NP12 alive": [([(SRC_P, B("rb"))], 3)],
    }
    for name, steps in cases.items():
        w = copy.deepcopy(mine)
        s0 = snapshot(w)
        log = close_probe(w, steps)
        print(f"\n== {name}")
        for m in log:
            print("   ", m)
        print("   changed:", {k: v for k, v in diff(s0, snapshot(w)).items()})
