"""Close-feed constraint map for design_c (door coords).

For every close mover, at the position where it must fire, list each cell that can power it
(direct: its 6 neighbours minus its face; QC: the neighbours of its above cell minus the piston).
For each cell, as a strongly powered conductor (emits into all 6 neighbours) and as dust
(emits only down and along its line), list which OTHER pistons a signal there also powers,
where each piston stands at that moment of the close, and what occupies the cell in the open state.

A co-powered piston is classed by the close order (plan_common.txt):
  SAME   - fires in the same stage anyway (harmless if the feed is timed for both)
  LATER  - must fire later in a chain that depends on M; powering it now breaks the chain (fatal)
  HOLD   - must stay unpowered at that moment (a spat piston before its landing cell, or P12 before its retract)
  RELAY  - an opening relay (extended; today QC-held, so an update is a no-op)
Output: constraints.txt
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["DESIGN"] = "design_c"
from scripts.door2 import design_c as d
from scripts.door2 import volume as v
from scripts.door2.doorkit import ring_cell
from scripts.door2.sim import DIRS, add

N6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
UP, DOWN = (0, 1, 0), (0, -1, 0)

b = v.build_open(); v.route_nets(b)
cells, _ = v.cumulative_cells(b)
OCC = set(cells)
w, _, _ = d.run_open(b, ticks=14)
OPEN = dict(w.b)

# close order (plan_common.txt + small_compactB.md 8.2), one valid linearisation, all in c0 g:
#  0 P12 retract | 1 wave 1: T, P9, P1-P6 | 2 P11 (S -> (0,3)) | 3 P10 (V -> (-1,3)) | 4 V H2 (S -> (1,3))
#  5 S H2 (C -> (1,1)) | 6 P8 (Q -> (3,2)) | 7 Q H2 (TM -> (1,2)) | 8 P7 (TR -> (2,2))
# A piston whose retract event has run is a moving block for the rest of c0 g: signals cannot reach it.
MOVERS = {  # name: (pos at firing, facing, stage)
    "T": ((1, 4, 0), "down", 1), "P9": ((4, 2, 0), "west", 1),
    "P1": ((0, -2, 0), "up", 1), "P2": ((1, -2, 0), "up", 1), "P3": ((2, -2, 0), "up", 1),
    "P4": ((-2, 1, 0), "east", 1), "P5": ((4, 1, 0), "west", 1), "P6": ((-2, 2, 0), "east", 1),
    "P11": ((-2, 3, 0), "east", 2), "P10": ((-1, 5, 0), "down", 3),
    "V": ((-1, 3, 0), "east", 4), "S": ((1, 3, 0), "down", 5),
    "P8": ((3, 4, 0), "down", 6), "Q": ((3, 2, 0), "west", 7), "P7": ((2, 4, 0), "down", 8),
}
# where the spat pistons wait (unpowered) before they fire: name -> list of (pos, facing, first stage, last stage)
WAIT = {"S": [((-1, 3, 0), "down", 0, 2), ((0, 3, 0), "down", 2, 4)],
        "V": [((-1, 4, 0), "east", 0, 3)],
        "Q": [((3, 3, 0), "west", 0, 6)],
        "P12": [((0, 5, 0), "down", 0, 0)]}
# optional stage overrides: CLOSE_STAGES="P6=2,P4=2"
for kv in filter(None, os.environ.get("CLOSE_STAGES", "").split(",")):
    k_, v_ = kv.split("=")
    MOVERS[k_] = (MOVERS[k_][0], MOVERS[k_][1], int(v_))
RELAYS = {"X2": (1, 7, -3), "Z_Q": (6, 3, -3), "Y1": (7, 3, -3), "Z_S": (2, 4, 2), "Z_T": (1, 4, -1),
          "Z9": (4, 2, 1), "Z11": (-2, 3, 1), "Y12": (-2, 3, 2)}
RELAY_FACING = {"X2": "north", "Z_Q": "up", "Y1": "up", "Z_S": "west", "Z_T": "up", "Z9": "up", "Z11": "up",
                "Y12": "west"}


def power_cells(p, facing):
    f = DIRS[facing]
    direct = {add(p, dd) for dd in N6 if dd != f}
    a = add(p, UP)
    qc = {add(a, dd) for dd in N6 if dd != DOWN}
    return direct, qc


def pistons_at(k):
    """(name, pos, facing, class) of every piston that a signal could still reach at stage k"""
    out = []
    for n, (p, f, s) in MOVERS.items():
        if s < k:
            continue                                  # already spat: moving block
        if n in WAIT and s > k:
            for (wp, wf, a, z) in WAIT[n]:
                if a <= k <= z:
                    out.append((n + "@" + str(wp[:2]), wp, wf, "WAIT"))
            continue
        out.append((n, p, f, "SAME" if s == k else "LATER"))
    for (wp, wf, a, z) in WAIT["P12"]:
        if a <= k <= z:
            out.append(("P12", wp, wf, "WAIT"))
    for n, p in RELAYS.items():
        out.append((n, p, RELAY_FACING[n], "RELAY"))
    return out


def reached(c, me, k):
    hits = []
    for n, p, f, cls in pistons_at(k):
        if n == me:
            continue
        dr, qc = power_cells(p, f)
        if c in dr:
            hits.append((n, "direct", cls))
        elif c in qc:
            hits.append((n, "qc", cls))
    return sorted(set(hits))


def occupant(c):
    if c in OPEN:
        st = OPEN[c]
        ident = st.p.get("id", "")
        return f"{st.n}{'(' + ident + ')' if ident else ''}:{b.role.get(c, '')}"
    x, y, z = c
    if (z == 0 and -1 <= x <= 3 and -1 <= y <= 3) or (z != 0 and ((0 <= x <= 2 and 0 <= y <= 2) or ring_cell(x, y))):
        return "hall/frame"
    if c in OCC:
        return "path-of-moving-block"
    return "free"


lines = []
summary = []
for me, (p, f, stage) in MOVERS.items():
    dr, qc = power_cells(p, f)
    lines.append(f"== {me} at {p} facing {f}, stage {stage}")
    best = []
    for kind, cs in (("direct", dr), ("qc", qc)):
        for c in sorted(cs):
            occ = occupant(c)
            # a strongly powered conductor at c reaches every piston that has c as a power cell
            tag_c = reached(c, me, stage)
            fatal = [t for t in tag_c if t[2] in ("LATER", "WAIT")]
            state = "CLEAN" if not fatal else "COUPLED"
            lines.append(f"  {kind:6} {c} occ={occ:38} {state:8} co-powered={tag_c}")
            if not fatal:
                best.append((c, kind, occ))
    summary.append((me, best))

lines.append("")
lines.append("== SUMMARY: cells whose signal, at the mover's stage, reaches no piston that fires later or must wait unpowered (RELAY/SAME allowed)")
for me, best in summary:
    free = [f"{c}{'' if o == 'free' else ' [' + o + ']'}" for c, k, o in best]
    lines.append(f"{me:9} {len(best)} clean: " + "; ".join(free))
open(os.path.join(HERE, os.environ.get("OUT", "constraints.txt")), "w").write("\n".join(lines) + "\n")
print("\n".join(lines[-20:]))
