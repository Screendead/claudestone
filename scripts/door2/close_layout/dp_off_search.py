"""Would one or two more blocks spit P6 as well? A screen on top of dp_off.py's design, with dp_search.py's
blocks, cells and pass rule: each candidate is set without updates into the open state of dp_off's build, then
the close runs from the input with no command; a pass needs stages 0 and 1 done, P11 out after P12's retract
and spat, P6 out and spat, S real at (0,3,0), SP, C and Q where the close needs them and no dust or FP lost, by
c6. dp_off's design alone fails this rule on P6 only: its event is dropped and NA extends it at c4. A pass
still has to be built and opened; dp_off.py does that for the one-block pass, and it fails there.

Cells: the free ones of x -4..-2, y 2..6, z -1..3 (dp_off's blocks take five of dp_search's 40).
Blocks: piston and sticky piston (six facings, retracted), redstone block, stone, glass, dust.

Run from the repo root (sim; about 25 minutes on four cores):
python -m scripts.door2.close_layout.dp_off_search > scripts/door2/close_layout/dp_off_search.txt"""
import json
from multiprocessing import Pool
from scripts.door2.close_layout import trigger as t, dp_off, dp_search as ds


def init():
    ds.W, _ = t.opened(dp_off.build())
    assert not ds.W.be and not ds.W.events
    ds.DUSTS = [c for c, st in ds.W.b.items() if st.n == "redstone_wire"]
    _, occ = t.fixed()
    ds.FREE = [c for c in ds.CELLS if c not in ds.W.b and c not in occ]


def key(cand):
    return [(c, n) for c, (n, _) in cand]


def with_first(i):
    opts = ds.options([])
    return [(key([opts[i], o]), r) for o in opts[i + 1:] if o[0] != opts[i][0] for r in [ds.passes([opts[i], o])] if r]


def said(cand, events):
    return json.dumps([[list(c), n] for c, n in cand]) + " " + "; ".join(events)


if __name__ == "__main__":
    init()
    opts = ds.options([])
    pairs = sum(1 for i, a in enumerate(opts) for o in opts[i + 1:] if o[0] != a[0])
    print(f"== on top of dp_off's seven blocks: {len(ds.FREE)} cells, {len(ds.TYPES)} blocks", flush=True)
    print("   alone:", "passes" if ds.passes([]) else "fails (P6 is not spat)", flush=True)
    ones = [(key([o]), r) for o in opts for r in [ds.passes([o])] if r]
    print(f"   one more block, {len(opts)} candidates: {len(ones)} pass", flush=True)
    for cand, r in ones:
        print("     ", said(cand, r), flush=True)
    with Pool(4, initializer=init) as pool:
        hits = [h for res in pool.imap(with_first, range(len(opts)), chunksize=4) for h in res]
    single = {c for cand, _ in ones for c in cand}
    rest = [(cand, r) for cand, r in hits if not single & set(cand)]
    print(f"   two more blocks, {pairs} candidates: {len(hits)} pass; {len(hits) - len(rest)} of them hold a block that passes alone, "
          f"{len(rest)} do not", flush=True)
    for cand, r in rest:
        print("     ", said(cand, r), flush=True)
    pairs_with = sum(1 for o in opts for c, _ in single if o[0] != c)
    print(f"   of the {pairs_with} pairs that hold a block that passes alone, {pairs_with - (len(hits) - len(rest))} fail: the second block spoils it", flush=True)
