"""T's wake in c0 without a command: sticky puller P_R (3,6,-1) facing west, extended through the closed state and
the opening with its head at (2,6,-1); RB_T lands against that head at t3. Held by redstone block HOLD (4,6,-1)
(stand-in for whatever the close chain removes). At c0 the hold goes, P_R retracts and pulls RB_T to (2,6,-1),
Z_T loses power (RB_A already pulled home by E0), retracts, and its retract event updates T under the lit feed.
Sim only (replay-only). Run from the repo root: python -m scripts.door2.close_layout.puller"""
import copy
from scripts.door2.close_layout import feeds as f
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources

P_R, HEAD, HOLD = (3, 6, -1), (2, 6, -1), (4, 6, -1)


def build():
    b = f.build(extra=True)
    from scripts.door2 import volume as v
    occ = set(v.cumulative_cells(b)[0])
    for p, st in ((P_R, B("sticky_piston", facing="west", extended=True, id="P_R")),
                  (HEAD, B("piston_head", facing="west", sticky=True)), (HOLD, B("rb"))):
        assert p not in b.b and p not in occ, p
        b.b[p] = st
    return b


if __name__ == "__main__":
    base = f.open_world(f.build(extra=True))
    w = f.open_world(build())
    print("open-state differences vs feeds-only build:", f.diff(f.snapshot(base), f.snapshot(w)) or "none")
    print("cells differing outside P_R/head/hold:",
          [p for p in set(base.b) | set(w.b) if p not in (P_R, HEAD, HOLD) and base.b.get(p) != w.b.get(p)
           and not (base.b.get(p) and w.b.get(p) and base.b[p].n == w.b[p].n == "redstone_wire")] or "none")
    print("P_R in the open state:", w.get(P_R), power_sources(w, P_R), "head:", w.get(HEAD), "RB_T at (1,6,-1):", w.get(f.RB_T))
    for name, steps in {
        "C: E0 + NP12 kill; next tick T feed lit and P_R's hold removed":
            [([(f.RB_A, AIR), (f.RB12, AIR)], 1), ([(f.SRC_T, B("rb")), (HOLD, AIR)], 3)],
        "C-ctl: hold removed, no T feed":
            [([(f.RB_A, AIR), (f.RB12, AIR)], 1), ([(HOLD, AIR)], 3)],
    }.items():
        ww = copy.deepcopy(w)
        s0 = f.snapshot(ww)
        log = f.close_probe(ww, steps)
        print(f"\n== {name}")
        for m in log:
            print("   ", m)
        print("   changed:", f.diff(s0, f.snapshot(ww)), "| RB_T:", [p for p, st in ww.b.items() if st.n == "rb" and p in (f.RB_T, HEAD)])
