"""Machine geometry for the QUART controller: band_quart's pairs (all x-bands on side A), west half, and the cells every
machine sweeps (logical coords). Same interface as pc/geom8: WEST, both(), mx(), forbidden(), moving_quartz(),
machine_sweeps(), NB, add. Configure with geomq.setup(N, pairs) before use."""
import sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

NB = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
STICKY = ('slime_block', 'honey_block')
bq = None
N = ZD = D0 = X = None
WEST = {}


def add(p, v, k=1):
    return (p[0] + k * v[0], p[1] + k * v[1], p[2] + k * v[2])


def setup(n, pairs=2, obs_k4=False):
    """pairs: number of row pairs from row 4 up (even pairs at rows 4, 8, .., odd at 6, 10, ..)."""
    global bq, N, ZD, D0, X, WEST
    argv = sys.argv
    sys.argv = ['x', 'OUT', str(n)]
    sys.modules.pop('band_quart', None)
    import band_quart
    sys.argv = argv
    bq = band_quart
    bq.OBS_K4 = obs_k4
    bands = {}
    for i in range(pairs):
        b = 4 + 2 * i
        bands[i + 1] = ('A', b, bq.EVEN_HOME if i % 2 == 0 else bq.ODD_HOME)
    bq.BANDS.clear(); bq.BANDS.update(bands)
    bq.ACTIVE = tuple(bands)
    bq.GLUE.clear()
    bq.grid.clear(); bq.inputs.clear(); bq.Z_HALVES.clear(); bq.MARKS.clear()
    for k in bands:
        bq.grid.update(bq.xband(k))
    bq.XMAX = bq.D0 + n + 3
    for x in range(bq.D0, bq.XMAX):
        for k in bands:
            for y in bq.rows(k):
                bq.grid[(x, y, bq.ZD)] = 'quartz_block'
    for k in bands:
        s = bq.slot(k)
        for y in bq.rows(k):
            bq.grid[(s, y, bq.ZD)] = 'quartz_block'
        za, ha, ma = bq.zband(k, 'A')
        zb, hb, mb = bq.zband(k, 'B')
        bq.grid.update(za); bq.grid.update(zb)
        bq.Z_HALVES[(k, 'A')], bq.Z_HALVES[(k, 'B')] = ha, hb
        bq.MARKS[(k, 'A')], bq.MARKS[(k, 'B')] = ma, mb
        for y in bq.rows(k):
            bq.grid[(s, y, ma['behind'][2])] = 'obsidian'
            bq.grid[(s, y, mb['slot'][2])] = 'quartz_block'
            bq.grid[(s, y, ma['slot'][2])] = 'quartz_block'
    N, ZD, D0 = n, bq.ZD, bq.D0
    X = 2 * (D0 + n)                      # mirror: x -> X - 1 - x (centre between D0+N-1 and D0+N)
    WEST = {p: b for p, b in bq.grid.items() if p[0] < D0 + n}
    return bq


FLIP = {'east': 'west', 'west': 'east'}


def mirror_state(b):
    for f, g in FLIP.items():
        if f'facing={f}' in b:
            return b.replace(f'facing={f}', f'facing={g}')
    return b


def mx(p):
    return (X - 1 - p[0], p[1], p[2])


def both(cells):
    out = dict(cells)
    out.update({mx(p): mirror_state(b) for p, b in cells.items()})
    return out


def machine_sweeps():
    """(swept, sticky_swept, piston_swept), west half, every machine over its whole travel with half-step lags."""
    ms = bq.machines()
    travel = {**{f'x{n}': (0, 1, D0 + N - 6 - bq.BANDS[n][2]) for n in bq.BANDS},
              **{f'z{n}B': (2, -1, bq.HB + bq.HA - 4) for n in bq.ACTIVE}, **{f'z{n}A': (2, 1, bq.HA - 2) for n in bq.ACTIVE}}
    swept, sticky, piston = set(), set(), set()
    for name, m in ms.items():
        axis, sgn, dist = travel[name]
        for d in range(dist + 1):
            for lag in (0, 1):
                for p, (blk, h) in m.items():
                    dd = {'e': sgn * (d + lag), 'w': sgn * d}.get(h, 0)
                    q = list(p); q[axis] += dd; q = tuple(q)
                    swept.add(q)
                    if blk in STICKY:
                        sticky.add(q)
                    if 'piston' in blk:
                        piston.add(q)
    return swept, sticky, piston


def forbidden():
    swept, sticky, piston = machine_sweeps()
    near = {add(p, v) for p in sticky for v in NB}
    return set(WEST) | swept, near, piston


def moving_quartz():
    """Door-plane rows from each x-band's door pistons to the centre, and each pair's slot line (stacks, spacers)."""
    out = {(x, y, ZD) for n in bq.BANDS for x in range(bq.BANDS[n][2] + 3, D0 + N) for y in bq.rows(n)}
    for n in bq.ACTIVE:
        s = bq.slot(n)
        ma, mb = bq.MARKS[(n, 'A')], bq.MARKS[(n, 'B')]
        out |= {(s, y, z) for y in bq.rows(n) for z in range(ma['behind'][2], mb['P'][2] + 1)}
    return out
