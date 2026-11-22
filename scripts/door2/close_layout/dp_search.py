"""Search for DP's on and off (stage 2 of the close) among added blocks: a screen, not a design. Each candidate
is set without updates into the open state of trigger.py's build (so a piston may stand powered and not
extended, as after an arming the opening does not show), then the close runs from the input with no DP
command. A candidate passes if stages 0 and 1 are done after c0, P11 extends after P12's retract event and is
spat, P6 extends and is spat, S ends real at (0,3,0), SP, C and Q are where the close needs them and no dust
or FP is lost, by c6, and I_A does not extend again. A pass still has to be built and opened: two pass, one idea,
and it fails there (dp.py). The last condition is of 2026-11-22: since the bus's west branch was re-laid from K_in's
top a lit bus powers K_in, so a candidate that lets the bus read DP's pulse (the cut over DP pushed off, say) fires
I_A and P_R again, and NA's death then "spits" P6 at c6; before, a lit west branch reached M_K only.

Families: one and two blocks in the free cells of x -4..-2, y 2..6, z -1..3; and the same again on top of the
pusher south of DP's source cell, sticky piston (-3,4,3) facing north with a redstone block at (-3,4,2).
Blocks: piston and sticky piston (six facings, retracted), redstone block, stone, glass, dust.

Run from the repo root (sim; about an hour on four cores):
python -m scripts.door2.close_layout.dp_search > scripts/door2/close_layout/dp_search.txt"""
import copy, json
from collections import OrderedDict
from multiprocessing import Pool
from scripts.door2.close_layout import trigger as t, feeds as f
from scripts.door2.sim import B

FACES = ["north", "south", "east", "west", "up", "down"]
TYPES = [("piston " + x, B("piston", facing=x, extended=False, id="X")) for x in FACES] + \
        [("sticky " + x, B("sticky_piston", facing=x, extended=False, id="X")) for x in FACES] + \
        [("redstone block", B("rb", id="XR")), ("stone", B("stone")), ("glass", B("glass")), ("dust", B("redstone_wire", power=0))]
CELLS = [(x, y, z) for x in range(-4, -1) for y in range(2, 7) for z in range(-1, 4)]
SOUTH = [((-3, 4, 3), TYPES[6]), ((-3, 4, 2), TYPES[12])]
TICKS = [[x for x in c if x[0] != t.SRC_P] for c in t.staged(through=2)][:8]      # c-1 .. c6
W = FREE = DUSTS = None


def init():
    global W, FREE, DUSTS
    W, _ = t.opened(t.build())
    assert not W.be and not W.events
    DUSTS = [c for c, st in W.b.items() if st.n == "redstone_wire"]
    _, occ = t.fixed()
    FREE = [c for c in CELLS if c not in W.b and c not in occ]


def world(cand):
    """the open state with the candidate's blocks in it (a copy that shares the block objects, which nothing mutates)."""
    w = copy.copy(W)
    w.__class__ = t.Probe
    w.b, w.be, w.tickers, w.sched, w.events, w.log = dict(W.b), {}, [], list(W.sched), OrderedDict(), []
    w.reverse = w.ia_last = False
    for c, (_, st) in cand:
        w.b[c] = st
    return w


def passes(cand):
    w = world(cand)
    ev = []
    for k, cmds in enumerate(TICKS):
        w.log.clear()
        for p, st in cmds:
            w.cmd_set(p, st)
        w.tick()
        ev += [f"c{k - 1} {m}" for (_, ph, m) in w.log if "EXTEND" in m or "RETRACT" in m]
        if k == 1 and (t.at(w, "C")[:2] != ((1, 2, 0), "real") or t.at(w, "P12")[:2] != ((0, 5, 0), "moving")):
            return False
    i12 = next((i for i, m in enumerate(ev) if "RETRACT P12" in m), None)
    i11 = next((i for i, m in enumerate(ev) if "EXTEND P11" in m), None)
    if i12 is None or i11 is None or i11 < i12:
        return False
    if not all(any("RETRACT " + n in m and "SPIT" in m for m in ev) for n in ("P11", "P6")) or any("EXTEND I_A" in m for m in ev):
        return False
    if t.at(w, "S") != ((0, 3, 0), "real", False) or t.at(w, "P11") != ((-2, 3, 0), "real", False):
        return False
    if t.at(w, "C")[0] != (1, 2, 0) or t.at(w, "SP")[0] != (0, 4, 0) or t.at(w, "Q")[0] != (3, 3, 0):
        return False
    if any(w.get(c).n != "redstone_wire" for c in DUSTS) or w.get(f.FP).n != "stone":
        return False
    return [m for m in ev if any(n in m for n in ("P11", "P6", "X@", "P12"))]


def said(cand, events):
    return json.dumps([[list(c), n] for c, (n, _) in cand]) + " " + "; ".join(events)


def options(fixed):
    taken = [c for c, _ in fixed]
    return [(c, ty) for c in FREE for ty in TYPES if c not in taken]


def with_first(args):
    fixed, i = args
    opts = options(fixed)
    return [said(fixed + [opts[i], o], r) for o in opts[i + 1:] if o[0] != opts[i][0] for r in [passes(fixed + [opts[i], o])] if r]


if __name__ == "__main__":
    init()
    for label, fixed in (("free cells", []), ("on top of the south pusher and its block", SOUTH)):
        opts = options(fixed)
        pairs = sum(1 for i, a in enumerate(opts) for o in opts[i + 1:] if o[0] != a[0])
        print(f"== {label}: {len(FREE) - len(fixed)} cells, {len(TYPES)} blocks", flush=True)
        if fixed:
            print("   alone:", "passes" if passes(fixed) else "fails", flush=True)
        hits = [said(fixed + [o], r) for o in opts for r in [passes(fixed + [o])] if r]
        print(f"   one more block, {len(opts)} candidates: {len(hits)} pass", flush=True)
        for h in hits:
            print("     ", h, flush=True)
        with Pool(4, initializer=init) as pool:
            hits = [h for res in pool.imap(with_first, [(fixed, i) for i in range(len(opts))], chunksize=4) for h in res]
        print(f"   two more blocks, {pairs} candidates: {len(hits)} pass", flush=True)
        for h in hits:
            print("     ", h, flush=True)
