"""Stage 1 of the pairs controller: everything under the machines (rows <= 1) and inside the machines' x/z footprint,
except the in-tile ends. door16_band_ctrl's logic core (lever, counter, gates, risers) moved to (3..10, -2..1, 2..11);
compact hand modules derive each kick from its spit near the ends (an observer on the spit line's last repeater), so
one routed net per pair and signal reaches each end; every other line is routed under the door."""
import sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from circuit import Circuit           # noqa: E402
import router as R                    # noqa: E402
import geom                           # noqa: E402
import layout2 as L2                  # noqa: E402

OBS = 'obsidian'
D = (12, -10, -28)                     # old core coords -> under the door
BOUNDS = (-14, 13, -5, 35)
ROWS = (-7, -5, -3, -1, 1, 3, 5, 7, 9)


def tr(p):
    return (p[0] + D[0], p[1] + D[1], p[2] + D[2])


SIG = lambda N: 1 + (14 * N) // 9          # comparator reading the counter dropper (N unstackable shovels)


def core(c, N):
    """door16_band_ctrl's lever module, counter and gates and the three risers, built at the old coordinates and
    copied in moved by D."""
    k = Circuit({})
    k.marks = {}
    T = k.turtle
    k.obs((-4, 5, 29), 'south', 'LP')
    k.block((-4, 5, 28), 'LP')
    T((-3, 5, 28), 'east', 'LP').fwd(1).turn('south').fwd(1)
    k.rep((-3, 5, 30), 'east', 'LVC')
    k.rep((-2, 5, 30), 'south', 'GC')
    k.rep((-2, 5, 31), 'south', 'CLOSE')
    k.obs((-2, 6, 31), 'down', 'CLOSE')
    k.block((-2, 7, 31), 'CLOSE')
    k.rep((-5, 5, 30), 'west', 'LV')
    k.block((-6, 5, 30), 'LV')
    k.torch((-7, 5, 30), 'east', 'NLV')
    k.rep((-8, 5, 30), 'west', 'NLV', powered=True)
    k.rep((-9, 5, 30), 'south', 'GS', locked=True)
    k.block((-9, 5, 31), 'STORE')                         # split: STORE_E, STORE_O, KZB
    T((-5, 5, 28), 'west', 'LP').fwd(4).turn('south').fwd(1)
    k.rep((-4, 5, 31), 'south', 'LV3')
    k.put((-4, 5, 32), 'hopper[facing=south,enabled=true]', 'CNT', 'hopper')
    k.put((-4, 5, 33), 'dropper[facing=north,triggered=false]' + L2.SHOVEL(N), 'CNT', 'dropper')
    k.support((-4, 5, 33))
    T((-4, 5, 36), 'north', 'DFIRE').fwd(3)
    k.block((-4, 5, 37), 'ZB')
    k.rep((-5, 5, 37), 'west', 'GF')
    k.rep((-3, 5, 37), 'east', 'GR', locked=True)
    sig = SIG(N)
    k.comp((-3, 5, 33), 'east', 'ED', powered=True, nbt='{OutputSignal:%d}' % sig)
    t = T((-2, 5, 33), 'east', 'ED').fwd(1, powered=True).turn('south').fwd(1, powered=True).turn('west')
    t.fwd(1, powered=True).turn('south').fwd(1, powered=True)
    k.comp((-5, 5, 33), 'west', 'ED2', powered=True, nbt='{OutputSignal:%d}' % sig)
    k.block((-6, 5, 33), 'ED2')
    k.rep((-6, 5, 34), 'south', 'ED2', powered=True)
    k.block((-6, 5, 35), 'ED2')
    k.torch((-5, 5, 35), 'west', 'NE', lit=False)
    k.rep((-5, 5, 36), 'south', 'NE')
    k.rep((-6, 5, 37), 'west', 'FETCH')
    k.obs((-6, 6, 37), 'down', 'FETCH')
    k.block((-6, 7, 37), 'FETCH')
    k.rep((-2, 5, 37), 'east', 'REB')
    k.obs((-2, 6, 37), 'down', 'REB')
    k.block((-2, 7, 37), 'REB')
    for p, st in k.cells.items():
        c.put(tr(p), st, k.net[p], k.meta[p]['kind'], **{a: b for a, b in k.meta[p].items() if a != 'kind'})
    c.marks.update(IL=tr((-4, 5, 30)), gs=tr((-9, 5, 30)), gc=tr((-2, 5, 30)), gs_in=tr((-9, 5, 28)),
                   close=tr((-2, 7, 31)), gf=tr((-5, 5, 37)), gr=tr((-3, 5, 37)), zb=tr((-4, 5, 37)),
                   xk_src=tr((-6, 7, 37)), reb=tr((-2, 7, 37)), store=tr((-9, 5, 31)))


SZ_SHORT = False


def zb_even(c):
    """Even ZB: spit hopper fed through (4,7,24); an observer on that repeater starts the kick 8 gt after the hopper,
    entering R through a block behind it."""
    c.put((4, 7, 23), 'hopper[facing=down,enabled=true]', 'STOREE', 'hopper')
    c.rep((4, 7, 24), 'north', 'STOREE', sup=OBS)
    c.obs((3, 7, 24), 'east', 'ZBKE')
    c.block((2, 7, 24), 'ZBKE')
    c.obs((2, 6, 25), 'up', 'ZBKE')
    c.rep((2, 7, 25), 'south', 'ZBKE')
    c.block((2, 5, 25), 'ZBKE')
    c.rep((3, 5, 25), 'east', 'ZBKE')
    c.block((4, 5, 25), 'ZBKE')
    # arrival: SZ watches the ZB's N; a short line to GZ, K_Z locks GZ's side
    c.obs((8, 5, 23), 'west', 'SZ')
    T = c.turtle                                          # a folded line, so GZ's input comes after the K_Z lock
    # 15 delay-1 repeaters as before, folded west instead of east so nothing stands in the doorway's prism (x >= 13)
    if SZ_SHORT:    # 9 repeaters: the K_Z line's tuned delay (KZB) keeps GZ's input 4 gt after the lock
        t = T((9, 5, 23), 'east', 'SZ').fwd(2).turn('south').fwd(7)
    else:
        t = T((9, 5, 23), 'east', 'SZ').fwd(3).turn('south').fwd(1).turn('west').fwd(4).turn('south').fwd(1) \
            .turn('east').fwd(3).turn('south').fwd(3)
    assert t.p == (11, 5, 31), t.p
    c.rep((11, 5, 31), 'south', 'GZ')
    c.rep((10, 5, 31), 'east', 'KZ', delay=4)              # 8 gt lock, set to open 4 gt before the departure
    c.marks.update(sz=(8, 5, 23), gz=(11, 5, 31), kz=(10, 5, 31), zbk_e_in=(4, 5, 25), gz_in=(11, 5, 30))


def za(c):
    """ZA spit hoppers and kicks, kick 8 gt after the hopper through an observer on the spit line (both pairs)."""
    # even
    c.put((4, 7, 3), 'hopper[facing=down,enabled=true]', 'ZASE', 'hopper')
    c.rep((4, 7, 2), 'south', 'ZASE', sup=OBS)
    for zz in (1, 0, -1, -2):                             # chain lengths set each pair's ZA phase
        c.rep((4, 7, zz), 'south', 'ZASE')
    c.obs((3, 7, 2), 'east', 'ZAKE')
    c.block((2, 7, 2), 'ZAKE')
    c.obs((2, 6, 1), 'up', 'ZAKE')
    c.rep((2, 7, 1), 'north', 'ZAKE')
    c.block((2, 5, 1), 'ZAKE')
    c.rep((3, 5, 1), 'east', 'ZAKE')
    c.block((4, 5, 1), 'ZAKE')
    # odd
    c.put((-4, 9, 3), 'hopper[facing=down,enabled=true]', 'ZASO', 'hopper')
    c.rep((-4, 9, 2), 'south', 'ZASO', sup=OBS)
    for zz in (1, 0, -1, -2, -3):
        c.rep((-4, 9, zz), 'south', 'ZASO')
    c.block((-4, 9, -4), 'ZASO')
    for x in range(-3, 2):
        c.rep((x, 9, -4), 'west', 'ZASO')
    c.obs((-5, 9, 2), 'east', 'ZAKO')
    c.block((-6, 9, 2), 'ZAKO')
    c.obs((-6, 8, 1), 'up', 'ZAKO')
    c.rep((-6, 9, 1), 'north', 'ZAKO')
    c.block((-6, 7, 1), 'ZAKO')
    c.rep((-5, 7, 1), 'east', 'ZAKO')
    c.block((-4, 7, 1), 'ZAKO')
    c.marks.update(r_e_in=(4, 5, 1), r_o_in=(-4, 7, 1))


LAD = dict(x0=3, zt=18, y=1)         # ladder along x under the even x-band (side B), rows 0..1
XHM = (-8, 1, 28)


def ladder_x(c, x0, zt, y, N):
    """door16_band_ctrl's ladder: T at z = zt flows west from T_0 (x0,y,zt), rungs at zt+1 point south, C at zt+2 flows
    east into the bulb (x0+2,y,zt+2). Pulse i reaches the bulb at T_0 + 4 + 10 i."""
    for i in range(N):
        xi = x0 - 3 * i
        c.block((xi, y, zt), 'LADT'); c.block((xi, y, zt + 2), 'LADC')
        c.rep((xi, y, zt + 1), 'south', 'LADR')
        if i < N - 1:
            c.rep((xi - 1, y, zt), 'west', 'LADT', delay=2); c.rep((xi - 2, y, zt), 'west', 'LADT', delay=1)
            c.rep((xi - 2, y, zt + 2), 'east', 'LADC'); c.rep((xi - 1, y, zt + 2), 'east', 'LADC')
    c.rep((x0 + 1, y, zt + 2), 'east', 'LADC')
    b = (x0 + 2, y, zt + 2)
    c.put(b, 'waxed_copper_bulb[lit=false,powered=false]', 'XSM', 'bulb')
    return b


def relay_low(c, bulb, d, net):
    """Comparator reading `bulb` toward d, a repeater, an observer under the repeater, a block two rows down: one pulse
    per toggle. Returns (comparator, block)."""
    v = R.H[d]
    cp, rp = R.add(bulb, v), R.add(bulb, v, 2)
    c.obs((rp[0], rp[1] - 1, rp[2]), 'up', net)
    blk = (rp[0], rp[1] - 2, rp[2])
    c.block(blk, net)
    c.comp(cp, d, net)
    c.rep(rp, d, net)
    return cp, blk


def timer(c, N):
    m = c.marks
    x0, zt, y = LAD['x0'], LAD['zt'], LAD['y']
    b = ladder_x(c, x0, zt, y, N)
    m['xsm'] = b
    m['xs_comp'], m['xsm_out'] = relay_low(c, b, 'east', 'XSP')
    c.rep((b[0], y, b[2] + 1), 'north', 'CLOSE')          # close toggles the spit master from the south
    hx, hy, hz = XHM
    c.put(XHM, 'waxed_copper_bulb[lit=false,powered=false]', 'XHM', 'bulb')
    m['xhm'] = XHM
    m['xh_comp'], m['xhm_out'] = relay_low(c, XHM, 'north', 'XHP')
    DL = {"TAPA": [(x, hy, hz) for x in range(hx - 1, hx - 5, -1)],             # east into the master
          'TAPB': [(x, hy, hz) for x in range(hx + 1, hx + 19)],                # west into the master
          'XHPO': [(-9, 7, z) for z in range(20, 27)],
          'XSPO': [(-8, 9, z) for z in range(20, 26)],
          'LADF': [(x, y, zt) for x in range(x0 + 1, x0 + 7)]}
    dirs = {'TAPA': 'east', 'TAPB': 'west', 'XHPO': 'north', 'XSPO': 'north', 'LADF': 'west'}
    for net, cells in DL.items():
        for p in cells:
            if p not in c.cells:
                c.rep(p, dirs[net], net)
    m.setdefault('dl', {}).update(DL)
    m['tA_end'], m['tB_end'] = DL['TAPA'][0], DL['TAPB'][0]
    c.block((x0 + 7, y, zt), 'TMR')                       # timer split: ladder feed, tap A, tap B
    m['tmr'] = (x0 + 7, y, zt)
    c.obs((x0 + 7, y - 1, zt), 'down', 'TMR')             # fed from below


def xk_fanout(c):
    """FETCH block -> two repeaters south -> fan-out block, away from the crowded core."""
    f = c.marks['xk_src']
    c.rep((f[0], f[1], f[2] + 1), 'south', 'XK')
    c.rep((f[0], f[1], f[2] + 2), 'south', 'XK')
    c.block((f[0], f[1], f[2] + 3), 'XK')
    c.marks['fetch'], c.marks['xk_src'] = f, (f[0], f[1], f[2] + 3)


def odd_x_ends(c):
    """layout2's odd x-band ends, with GX under the wall west of the odd home."""
    m = c.marks
    m.update(gx=(-9, 1, 8), kx=(-9, 1, 9), gx_in=(-8, 1, 8))
    c.rep(m['gx'], 'west', 'GX')
    c.rep(m['kx'], 'north', 'KX', delay=4)
    m.setdefault('dl', {})['KX'] = [(-9, 1, z) for z in range(10, 15)]
    for p in m['dl']['KX']:
        c.rep(p, 'north', 'KX')
    c.obs((-10, 6, 15), 'down', 'XKO')                    # the kick block (-10,7,15) is fed from below


def build_hand(N):
    c = Circuit(geom.WEST)
    c.marks = {'N': N}
    L2.ends(c)
    # layout2.ends put GX/KX west of the box and an even ZB_o module; drop GX/KX, keep the rest
    for p in [(-14, 7, 9), (-14, 7, 10), (-14, 6, 9), (-14, 6, 10)]:
        for dct in (c.cells, c.net, c.meta):
            dct.pop(p, None)
    # even kick lane enters its block from below
    for p in [(1, 5, z) for z in range(27, 32)] + [(1, 4, z) for z in range(27, 31)] + [(1, 6, 31)]:
        for dct in (c.cells, c.net, c.meta):
            dct.pop(p, None)
    c.block((1, 5, 27), 'XKE')
    c.obs((1, 4, 27), 'down', 'XKE')
    core(c, N); xk_fanout(c); zb_even(c); za(c); timer(c, N); odd_x_ends(c)
    for net, (o, ln, k) in SNAKE.items():
        e, x = snake(c, net, o, ln, k)
        SNAKE_ENDS[net] = (e, 'east', x)
    for net, z in DBULB.items():
        SNAKE_ENDS[net] = delay_bulb(c, net, z)
    return c


def nets(c):
    m = c.marks
    src, reb, st = m['xk_src'], m['reb'], m['store']
    cl = m['close']
    xb, xsm = m['xhm_out'], m['xsm_out']
    hx, hy, hz = XHM
    lx, lz, ly = LAD['x0'], LAD['zt'], LAD['y']
    S = lambda p, d: (R.add(p, R.H[d]), d)
    return [
        ('XKE', S(src, 'east'), ((1, 3, 27), 'north'), [src], [(1, 4, 27)]),
        ('XKO', S(src, 'west'), ((-10, 5, 15), 'north'), [src], [(-10, 6, 15)]),
        ('KX', S(src, 'south'), ((-9, 1, 15), 'north'), [src], [(-9, 1, 14)]),
        ('CLOSEK', S(cl, 'north'), ((m['fetch'][0] - 1, m['fetch'][1], m['fetch'][2]), 'east'), [cl], [m['fetch']]),
        ('CLOSE', S(cl, 'east'), ((m['xsm'][0], ly, m['xsm'][2] + 2), 'north'), [cl], [(m['xsm'][0], ly, m['xsm'][2] + 1)]),
        ('STOREE', S(st, 'south'), ((4, 7, 25), 'north'), [st], [(4, 7, 24)]),
        ('STOREO', S(st, 'west'), ((-3, 9, 27), 'west'), [st], [(-4, 9, 27)]),
        ('KZB', S(st, 'east'), ((9, 5, 31), 'east'), [st], [m['kz']]),
        ('ZARR', ((11, 5, 32), 'south'), ((m['zb'][0], m['zb'][1], m['zb'][2] + 1), 'north'), [m['gz']], [m['zb']]),
        ('XARR', ((-10, 1, 8), 'west'), ((m['gs_in'][0] - 1, m['gs_in'][1], m['gs_in'][2]), 'east'), [m['gx']],
         [m['gs_in']]),
        ('SX', ((-7, 7, 9), 'west'), (m['gx_in'], 'west'), [(-6, 7, 9)], [m['gx']]),
        ('ZASE', S(reb, 'east'), ((4, 7, -3), 'south'), [reb], [(4, 7, -2)]),
        ('ZASO', S(reb, 'north'), ((2, 9, -4), 'west'), [reb], [(1, 9, -4)]),
        ('TMR', S(reb, 'south'), ((lx + 7, ly - 2, lz), 'south'), [reb], [(lx + 7, ly - 1, lz)]),
        ('TAPA', ((lx + 7, ly, lz + 1), 'south'), ((hx - 5, hy, hz), "east"), [(lx + 7, ly, lz)], [(hx - 4, hy, hz)]),
        ('TAPB', ((lx + 8, ly, lz), 'east'), ((hx + 19, hy, hz), "west"), [(lx + 7, ly, lz)],
         [(hx + 18, hy, hz)]),
        ('XSPE', S(xsm, 'east'), ((0, 7, 26), 'north'), [xsm], [(0, 7, 25)]),
        ('XSPO', S(xsm, 'south'), ((-8, 9, 26), 'north'), [xsm], [(-8, 9, 25)]),
        ('XHPE', S(xb, 'east'), ((-2, 5, 26), 'east'), [xb], [(-1, 5, 26)]),
        ('XHPO', S(xb, 'south'), ((-9, 7, 27), 'north'), [xb], [(-9, 7, 26)]),
    ]


MAXD = {'XSPE': 2, 'XSPO': 2, 'TMR': 3, 'LADF': 3}


VIA = {}
# -> waypoint (cell, dir): the net passes a repeater there, to lengthen a 2 gt line


SNAKE = {'CLOSEK': ((2, -7, 0), 9, 4)}


def snake(c, net, origin, length, lines):
    """Hand delay line of 2 gt repeaters: `lines` runs of `length` along x, 2 apart in z, joined by turns. Returns
    (entry: the cell a route must reach pointing east into it, exit block)."""
    x0, y, z0 = origin
    xs = [x0 + i for i in range(length)]
    for j in range(lines):
        z = z0 + 2 * j
        d = 'east' if j % 2 == 0 else 'west'
        run = xs if d == 'east' else xs[::-1]
        for x in run:
            c.rep((x, y, z), d, net)
        end = (run[-1] + (1 if d == 'east' else -1), y, z)
        c.block(end, net)
        if j < lines - 1:
            c.rep((end[0], y, z + 1), 'south', net)
            c.block((end[0], y, z + 2), net)
            end = (end[0], y, z + 2)
    return (x0 - 1, y, z0), end


def route_via(bd, name, start, goal, a_s, a_e):
    kw = dict(rows=ROWS, deep=-5, max_cost=800)
    if name not in SNAKE_ENDS:
        return R.route(bd, name, start, goal, allow_start=a_s, allow_end=a_e, **kw)
    entry, edir, ex = SNAKE_ENDS[name]
    p1 = R.route(bd, name, start, (entry, edir), allow_start=a_s, allow_end=[R.add(entry, R.H[edir])], **kw)
    p2 = None
    for d in ('south', 'north', 'east', 'west'):
        q = R.add(ex, R.H[d])
        if q in bd.active or q in bd.blocked:
            continue
        try:
            p2 = R.route(bd, name, (q, d), goal, allow_start=[ex], allow_end=a_e, **kw)
            break
        except RuntimeError:
            continue
    if p2 is None:
        raise RuntimeError(f'no route for {name} out of its delay line')
    return p1 + p2


SNAKE_ENDS = {}
DBULB = {}


def delay_bulb(c, net, z, y=1):
    """A tunable delay for a once-per-cycle 2 gt pulse: repeaters (x 11..7, delays tuned) toggle a bulb; a comparator
    reading it, a repeater and an observer under that repeater give one fresh 2 gt pulse per toggle."""
    cells = [(x, y, z) for x in range(11, 6, -1)]
    for p in cells:
        c.rep(p, 'west', net)
    c.put((6, y, z), 'waxed_copper_bulb[lit=false,powered=false]', net, 'bulb')
    c.comp((5, y, z), 'west', net)
    c.obs((4, y - 1, z), 'up', net)
    c.rep((4, y, z), 'west', net)
    c.block((4, y - 2, z), net)
    c.marks.setdefault('dl', {})[net] = cells
    return (12, y, z), 'west', (4, y - 2, z)


def _fresh(N):
    c = build_hand(N)
    assert not c.errors, c.errors
    bd = L2.board(c)
    bd.bounds = BOUNDS
    for n in nets(c):
        bd.reserved.pop(n[1][0], None)
    for n in nets(c):                                   # keep each net's first and last two cells for it
        (p, d), (g, gd) = n[1], n[2]
        for q in (p, R.add(p, R.H[d]), g, R.add(g, R.H[gd], -1)):
            if q not in bd.active and q not in bd.blocked:
                bd.reserved.setdefault(q, n[0])
    return c, bd


def _rip(bd, net, hand):
    for p, (st, n) in list(bd.cells.items()):
        if n == net and p not in hand:
            bd.cells.pop(p); bd.active.pop(p, None); bd.support.pop(p, None)
    for q, n in list(bd.reserved.items()):
        if n == net and q not in hand:
            pass
    for p, (st, n) in list(bd.cells.items()):        # supports shared with the ripped net
        if st.startswith('repeater') or st.startswith('comparator'):
            s_ = (p[0], p[1] - 1, p[2])
            if s_ not in bd.cells:
                bd.support[s_] = 'stone'; bd.cells[s_] = ('stone', n)


def build(N, delays=None, tries=400, verbose=False, restarts=12):
    import random
    first = list(FIRST)
    for r in range(restarts):
        try:
            return _build(N, delays, tries // 4, verbose, first)
        except _Stuck as e:
            name = e.args[0]
            if verbose:
                print('restart with', name, 'first')
            rest = [n for n in first if n != name]
            if r % 2:
                random.Random(r).shuffle(rest)
            first = [name] + rest
    raise RuntimeError('routing failed')


class _Stuck(Exception):
    pass


FIRST = ['KZB', 'XSPE', 'XSPO', 'TMR', 'TAPA', 'ZASE', 'ZASO']


PREV = {}         # net -> (cells {pos: (state, net)}, support set, reserved {pos: net}, path): reused when still free


def _place_prev(bd, name, hand):
    cells, sup, res, path = PREV[name][:4]
    for q in cells:
        if q in bd.cells or q in bd.blocked:
            return None
        if q in bd.reserved and bd.reserved[q] != name:
            return None
    for q, v in cells.items():
        bd.cells[q] = v
        if q in sup:
            bd.support[q] = v[0]
        else:
            bd.active[q] = name
    bd.reserved.update(res)
    return path


def _build(N, delays, tries, verbose, first):
    from collections import Counter
    fails = Counter()
    c, bd = _fresh(N)
    hand = set(bd.cells)
    base_res = dict(bd.reserved)
    spec = {n[0]: n for n in nets(c)}
    queue = first + [k for k in spec if k not in first]
    paths, steps = {}, 0
    for name in list(queue):
        if name in PREV and PREV[name][4:] == (spec[name][1:3],):
            p = _place_prev(bd, name, hand)
            if p is not None:
                paths[name] = p
                queue.remove(name)
    while queue:
        steps += 1
        name = queue.pop(0)
        if steps > tries:
            raise _Stuck(name)
        _, start, goal, a_s, a_e = spec[name]
        try:
            paths[name] = route_via(bd, name, start, goal, a_s, a_e)
            continue
        except RuntimeError:
            fails[name] += 1
            if fails[name] > 4:
                raise _Stuck(name)
        c2, b2 = _fresh(N)
        try:
            ideal = route_via(b2, name, start, goal, a_s, a_e)
        except RuntimeError:
            raise RuntimeError(f'{name} cannot route even alone')
        cells = {q for q, (st, n) in b2.cells.items() if n == name and q not in hand}
        near = cells | {R.add(q, v) for q in cells for v in R.NB6}
        victims = {bd.cells[q][1] for q in near if q in bd.cells and q not in hand} - {name, 'support'}
        victims &= set(paths)
        import copy
        swapped = False
        for y in sorted(victims):                    # try a single swap first: rip y, route name, re-route y
            tb = copy.deepcopy(bd)
            _rip(tb, y, hand)
            tb.reserved = {q: n for q, n in tb.reserved.items() if n != y or q in base_res}
            try:
                px = route_via(tb, name, start, goal, a_s, a_e)
                py = route_via(tb, y, *spec[y][1:3], spec[y][3], spec[y][4])
            except RuntimeError:
                continue
            bd.__dict__.update(tb.__dict__)
            paths[name], paths[y] = px, py
            swapped = True
            if verbose:
                print('swap', y, 'for', name)
            break
        if swapped:
            continue
        if verbose:
            print('rip', sorted(victims), 'for', name)
        for v in victims:
            _rip(bd, v, hand)
            bd.reserved = {q: n for q, n in bd.reserved.items() if n != v or q in base_res}
            paths.pop(v)
        clash = [q for q in cells if q in bd.cells and bd.cells[q][1] != name]
        if not clash:
            for q in cells:                                  # the ideal path is free now: copy it
                st, n = b2.cells[q]
                bd.cells[q] = (st, n)
                (bd.support if q in b2.support else bd.active)[q] = st if q in b2.support else n
            for q, n in b2.reserved.items():
                if n == name:
                    bd.reserved[q] = n
            paths[name] = ideal
        else:
            queue.append(name)
        queue.extend(sorted(victims))
    for p, (st, net) in bd.cells.items():
        if p not in c.cells:
            c.net[p] = net
            c.meta[p] = dict(kind='support' if p in bd.support else 'routed')
        c.cells[p] = st
    dl = c.marks['dl']
    for name, gt in (delays or {}).items():
        if not gt:
            continue
        reps = (paths.get(name, []) if name != 'LADF' else paths['TMR']) + [('rep', p) for p in dl.get(name, [])]
        if name == 'LADF':
            reps = [('rep', p) for p in dl['LADF']]
        R.set_delays(bd, reps, gt, maxd=MAXD.get(name, 4))
    for p, (st, net) in bd.cells.items():
        c.cells[p] = st
    c.paths, c.board = paths, bd
    c.spec_nets = {n[0]: n for n in nets(c)}
    return c


def remember(c):
    """Keep c's routes for the next build (only nets whose start and goal are unchanged reuse them)."""
    bd = c.board
    hand = {p for p in c.cells if c.meta[p]['kind'] not in ('routed',) and c.meta[p]['kind'] != 'support'}
    PREV.clear()
    for name, path in c.paths.items():
        cells = {q: v for q, v in bd.cells.items() if v[1] == name and c.meta.get(q, {}).get('kind') in ('routed', 'support')}
        sup = {q for q in cells if q in bd.support}
        res = {q: n for q, n in bd.reserved.items() if n == name}
        PREV[name] = (cells, sup, res, path, c.spec_nets[name][1:3])
