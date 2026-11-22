"""Would one added block do for stages 3 and 4? A screen under p10_v.py's two: each candidate is built into
dp_off.py's build (loaded, settled, opened from the input: no block is set into the open state), then the close
runs from the input with no command. A pass needs nothing moved during the load, the opening's pistons and door
plane the same at every tick, and by c14 S real at (1,3,0) and retracted, V at (-1,3,0), in or out, P10 out, C at
(1,2,0), SP, TL, Q and TM where the close needs them, T, P12, P11 and P8 in and no dust lost. dp_off's build
alone fails it on S and V only (P10 extends at c8 on NA's repeater); p10_v's two blocks pass it.

Cells: the free ones of x -3..1, y 2..7, z -7..2: every free cell within two of V's power cells, of P10's and of
NV's west branch. Blocks: piston and sticky piston (six facings, retracted), redstone block, stone, glass, dust,
and a repeater in four facings at 1 to 4 ticks. The simulator has no rule for support: a dust or a repeater
that passes still has to stand on something.

Run from the repo root (sim; about 4 minutes on four cores):
python -m scripts.door2.close_layout.p10_v_search > scripts/door2/close_layout/p10_v_search.txt"""
import json
from multiprocessing import Pool
from scripts.door2.close_layout import feeds as f, trigger as t, dp, dp_off as o, dp_search as ds, p10_v as pv
from scripts.door2.close_layout.feeds import d, B

TYPES = ds.TYPES + [(f"repeater {x} {n}", B("repeater", facing=x, delay=n, powered=False)) for x in ("north", "south", "east", "west")
                    for n in (1, 2, 3, 4)]
CELLS = [(x, y, z) for x in range(-3, 2) for y in range(2, 8) for z in range(-7, 3)]
LAST = 14
WANT = {"S": (pv.S_CELL, "real", False), "P10": (pv.P10, "real", True), "C": ((1, 2, 0), "real", None), "T": ((1, 4, 0), "real", False),
        "P12": ((0, 5, 0), "real", False), "SP": ((0, 4, 0), "real", None), "P11": (o.P11, "real", False), "TL": ((0, 2, 0), "real", None),
        "P8": ((3, 4, 0), "real", False), "Q": ((3, 3, 0), "real", False), "TM": ((3, 2, 0), "real", None)}
REF = FREE = DUSTS = None


def opening(b):
    """(the world after the load, what moved in it), then the world after each tick of the opening."""
    w, moved = d.make_world(b)
    yield w, moved
    w.run(4)
    w.cmd_set(f.DRIVER, t.RB)
    for _ in range(t.OPEN_TICKS):
        w.tick()
        yield w


def init():
    global REF, FREE, DUSTS
    steps = opening(o.build())
    next(steps)
    REF = [f.snapshot(w) for w in steps]
    w, _ = t.opened(o.build())
    DUSTS = [c for c, st in w.b.items() if st.n == "redstone_wire"]
    _, occ = t.fixed()
    FREE = [c for c in CELLS if dp.free(w, occ, c) and not (c[2] != 0 and 0 <= c[0] <= 2 and 0 <= c[1] <= 2)]


def passes(cand):
    """cand: {cell: block}. The V, S and P10 events of the close if the candidate passes, else False."""
    steps = opening(o.build(swap=cand))
    w, moved = next(steps)
    if moved:
        return False
    for ref in REF:
        w = next(steps)
        if f.diff(ref, f.snapshot(w)):
            return False
    w = pv.noted(w, pv.idle(LAST))
    if any(t.at(w, n) != x for n, x in WANT.items()) or t.at(w, "V")[:2] != (pv.V_CELL, "real"):
        return False
    if any(w.get(c).n != "redstone_wire" for c in DUSTS):
        return False
    return [f"c{k} {m}" for k, m in pv.moves(w) if k > 3 and any(n in m for n in (" V@", " S@", " P10@", " X@"))]


def one(i):
    c, (name, st) = OPTS[i]
    r = passes({c: st})
    return (c, name, r) if r else None


def options():
    return [(c, ty) for c in FREE for ty in TYPES]


init()
OPTS = options()

if __name__ == "__main__":
    print(f"== on top of dp_off's build: {len(FREE)} cells, {len(TYPES)} blocks", flush=True)
    print("   alone:", "passes" if passes({}) else "fails (S stays at (0,3,0): nothing powers V)", flush=True)
    r = passes(pv.MINE)
    print("   p10_v's two blocks:", "pass: " + "; ".join(r) if r else "FAIL", flush=True)
    with Pool(4) as pool:
        hits = [h for h in pool.imap(one, range(len(OPTS)), chunksize=16) if h]
    print(f"   one block, {len(OPTS)} candidates: {len(hits)} pass", flush=True)
    for c, name, r in hits:
        print("     ", json.dumps([list(c), name]), "; ".join(r), flush=True)
