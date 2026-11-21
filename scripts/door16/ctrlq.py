"""Controller for the QUART pairs (PROGRESS.md "QUART rework"), one half, logical coords. Reuses layout3's logic core,
counter and gates, ZB/ZA end modules, timer (ladder, masters) and rip-up router, with:
  * door-side modules moved to this frame (ZD = 12 + N here; layout3's frame had ZD 16 at N = 5),
  * the odd pair's z-band ends moved 3 west (odd slot x-8),
  * new x-band ends for door16_band_kick2's band: kick hopper in the cell O watches, spit hopper in the cell the
    door-plane observer watches, hold = repeater into the upper door piston from side B, odd home sensor SX watching
    the odd band's O from k1.
call setup(N) first."""
import sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import geomq                                   # noqa: E402
sys.modules['geom'] = geomq
import layout2 as L2                           # noqa: E402
import layout3 as L3                           # noqa: E402
import router as R                             # noqa: E402
from circuit import Circuit                    # noqa: E402

OLD_ZD = 16
N = ZD = DZ = None
bq = None
ODD_DX = -3


def setup(n, pairs=2):
    global N, ZD, DZ, bq
    bq = geomq.setup(n, pairs)
    N, ZD = n, geomq.ZD
    DZ = ZD - OLD_ZD
    L3.BOUNDS = (-20, 13, -8, 36)
    L3.PREV.clear()
    return bq


def copy_module(c, fn, move):
    """Run a layout3 module on a scratch circuit and copy its cells into c through move(p, net) -> p'."""
    k = Circuit({})
    k.marks = dict(c.marks)
    k.turtle = lambda p, toward, net, y=None: L3.Circuit.turtle(k, p, toward, net)
    fn(k)
    for p, st in k.cells.items():
        net = k.net[p]
        owner = net if net != 'support' else k.net.get((p[0], p[1] + 1, p[2]), 'support')
        c.put(move(p, owner), st, net, k.meta[p]['kind'], **{a: b for a, b in k.meta[p].items() if a != 'kind'})
    return k


def zshift(p, net=None):
    return (p[0], p[1], p[2] + DZ)


def odd_move(p, net):
    if net in ('ZASO', 'ZAKO'):
        return (p[0] + ODD_DX, p[1], p[2])
    return p


def x_ends(c):
    """New x-band ends (one half). Even pair rows 4-5 home x-1; odd pair rows 6-7 home x-12."""
    m = c.marks
    xs = {}
    for n, cls in ((1, 'E'), (2, 'O')):
        side, b, xw = bq.BANDS[n]
        t, xp = b + 1, xw + 3
        kick = (xw - 2, t, ZD - 2)
        c.put(kick, 'hopper[facing=down,enabled=true]', f'XK{cls}', 'hopper')
        if cls == 'E':
            # x-4 and west at row 5 lies beside the odd z-corridor: fed from below through an observer
            c.obs((xw - 2, t - 1, ZD - 2), 'down', 'XKE')
            kin = (xw - 2, t - 1, ZD - 2)
        else:
            c.rep((xw - 3, t, ZD - 2), 'east', f'XK{cls}')
            kin = (xw - 3, t, ZD - 2)
        spit = (xw + 1, t, ZD)
        c.put(spit, 'hopper[facing=down,enabled=true]', f'XS{cls}', 'hopper')
        c.rep((xw + 1, t, ZD + 1), 'north', f'XS{cls}')
        c.comp((xw + 1, t, ZD + 2), 'north', f'XS{cls}')
        c.put((xw + 1, t, ZD + 3), 'waxed_copper_bulb[lit=false,powered=false]', f'XS{cls}', 'bulb')
        if cls == 'O':                                                 # delay line for the odd hold
            dl = [(xp - k, t, ZD + 5) for k in range(1, 6)]
            for q in dl:
                c.rep(q, 'east', 'XHPO')
            m.setdefault('dl', {})['XHPO'] = dl
        c.rep((xp, t, ZD + 1), 'north', f'XH{cls}')                    # into P(t); P(b) by QC
        c.rep((xp, t, ZD + 2), 'north', f'XH{cls}')
        c.rep((xp, t, ZD + 3), 'north', f'XH{cls}')
        c.comp((xp, t, ZD + 4), 'north', f'XH{cls}')
        c.put((xp, t, ZD + 5), 'waxed_copper_bulb[lit=false,powered=false]', f'XH{cls}', 'bulb')
        # both bulbs are fed from the west: the cells beside the slot corridor (x = xp) are no place for a route
        xs[cls] = dict(kick=kick, kick_in=kin, spit=spit, spit_bulb=(xw + 1, t, ZD + 3),
                       spit_comp=(xw + 1, t, ZD + 2), hold_bulb=(xp, t, ZD + 5), hold_comp=(xp, t, ZD + 4),
                       p_t=(xp, t, ZD), hold_in=(xp, t, ZD + 1))
    # odd home sensor: watches the odd band's O from k1, outputs into a block in the door plane west of the band
    side, b, xw = bq.BANDS[2]
    t = b + 1
    c.obs((xw - 1, t, ZD - 1), 'north', 'SX')
    c.block((xw - 1, t, ZD), 'SX')
    m['sx'], m['sx_blk'] = (xw - 1, t, ZD - 1), (xw - 1, t, ZD)
    # Arrival filter (replaces layout3's GX/K_X): SX fires twice on the odd band's departure (O pulsed, O moving away,
    # 6 gt apart) and twice on its arrival (O moving in, O pulsed, 4 gt apart) (MEASURED, quart/sx.out). A delay-4
    # repeater merges each pair into one pulse, which toggles bulb A (lit while the band is out); a torch reads A's
    # comparator, so bulb B toggles once per arrival only, and a relay gives one 2 gt pulse per toggle of B.
    y, z = 1, 8
    c.rep((-12, y, z), 'west', 'SXM', delay=4)
    c.put((-13, y, z), 'waxed_copper_bulb[lit=false,powered=false]', 'SXA', 'bulb')
    c.comp((-14, y, z), 'west', 'SXA')
    c.block((-15, y, z), 'SXA')
    c.torch((-15, y, z - 1), 'south', 'SXT', lit=True)
    c.rep((-16, y, z - 1), 'west', 'SXT', powered=True)
    c.put((-17, y, z - 1), 'waxed_copper_bulb[lit=false,powered=true]', 'SXB', 'bulb')
    cp, blk = L3.relay_low(c, (-17, y, z - 1), 'west', 'XARR')
    m.update(gx_in=(-11, y, z), sxm=(-12, y, z), sxa=(-13, y, z), sxb=(-17, y, z - 1), xarr_src=blk)
    m['xs'] = xs


def odd_zb(c):
    """layout2's odd ZB ends (spit hopper, kick entering R from the west), moved to the odd slot x-8 and this ZD."""
    s = bq.slot(2)
    mb = bq.MARKS[(2, 'B')]
    hx, hy, hz = mb['spit']                                    # (s+1, b+3, ze)
    c.put((hx, hy, hz), 'hopper[facing=down,enabled=true]', 'ZBSO', 'hopper')
    c.rep((hx, hy, hz + 1), 'north', 'ZBSO', sup='obsidian')
    c.rep((hx, hy, hz + 2), 'north', 'ZBSO'); c.rep((hx, hy, hz + 3), 'north', 'ZBSO')
    c.block((hx, hy, hz + 4), 'ZBSO')
    z4 = hz + 4
    c.obs((hx - 1, hy - 1, z4), 'up', 'ZBKO')
    c.rep((hx - 1, hy, z4), 'west', 'ZBKO')
    c.block((hx - 1, hy - 2, z4), 'ZBKO')
    c.rep((hx - 2, hy - 2, z4), 'west', 'ZBKO')
    c.block((hx - 3, hy - 2, z4), 'ZBKO')
    c.rep((hx - 3, hy - 2, z4 - 1), 'north', 'ZBKO'); c.rep((hx - 3, hy - 2, z4 - 2), 'north', 'ZBKO')
    c.block((hx - 3, hy - 2, z4 - 3), 'ZBKO')
    c.rep((hx - 2, hy - 2, z4 - 3), 'east', 'ZBKO'); c.rep((hx - 1, hy - 2, z4 - 3), 'east', 'ZBKO')
    c.marks.update(zbs_o=(hx, hy, hz), zbk_o_in=(hx - 1, hy - 2, z4 - 3), zbso_end=(hx, hy, hz + 4))


def build_hand(n):
    c = Circuit(geomq.WEST)
    c.marks = {'N': n}
    L3.core(c, n)
    L3.xk_fanout(c)
    k = copy_module(c, L3.zb_even, zshift)
    c.marks.update({key: zshift(v) for key, v in k.marks.items() if key in ('sz', 'gz', 'kz', 'zbk_e_in', 'gz_in')})
    kz = c.marks['kz']                                         # K_Z delay line, west of the lock
    c.marks.setdefault('dl', {})['KZB'] = [(kz[0] - k, kz[1], kz[2]) for k in range(1, 5)]
    for q in c.marks['dl']['KZB']:
        c.rep(q, 'east', 'KZB')
    k = copy_module(c, L3.za, odd_move)
    c.marks.update(r_e_in=(4, 5, 1), r_o_in=(-4 + ODD_DX, 7, 1))
    L3.LAD.update(x0=3, zt=ZD + 2, y=1)
    L3.XHM = (-8, 1, ZD + 12)
    L3.timer(c, n)
    for net in ('XHPO', 'XSPO'):                               # layout3's odd delay lines sat at the old odd ends
        for p in [p for p in c.cells if c.net[p] == net]:
            for dct in (c.cells, c.net, c.meta):
                dct.pop(p, None)
        for q in [p for p in c.cells if c.net[p] == 'support' and (p[0], p[1] + 1, p[2]) not in c.cells
                  and p in [(x, y - 1, z) for (x, y, z) in c.marks['dl'][net]]]:
            for dct in (c.cells, c.net, c.meta):
                dct.pop(q, None)
        c.marks['dl'].pop(net)
    odd_zb(c)
    x_ends(c)
    for net, (o, ln, kk) in L3.SNAKE.items():
        e, x = L3.snake(c, net, o, ln, kk)
        L3.SNAKE_ENDS[net] = (e, 'east', x)
    return c


def nets(c):
    m = c.marks
    src, reb, st = m['xk_src'], m['reb'], m['store']
    cl = m['close']
    xb, xsm = m['xhm_out'], m['xsm_out']
    hx, hy, hz = L3.XHM
    lx, lz, ly = L3.LAD['x0'], L3.LAD['zt'], L3.LAD['y']
    S = lambda p, d: (R.add(p, R.H[d]), d)
    xs = m['xs']
    W = lambda p: (p[0] - 1, p[1], p[2])
    up = lambda p: (p[0], p[1], p[2] + 1)
    e, o = xs['E'], xs['O']
    zbs_e = (4, 7, 24 + DZ - 1 + 1)
    return [
        ('XKE', S(src, 'east'), ((e['kick_in'][0], e['kick_in'][1] - 1, e['kick_in'][2]), 'north'), [src], [e['kick_in']]),
        ('XKO', S(src, 'west'), (W(o['kick_in']), 'east'), [src], [o['kick_in']]),
        ('CLOSEK', S(cl, 'north'), ((m['fetch'][0] - 1, m['fetch'][1], m['fetch'][2]), 'east'), [cl], [m['fetch']]),
        ('CLOSE', S(cl, 'east'), ((m['xsm'][0], ly, m['xsm'][2] + 2), 'north'), [cl], [(m['xsm'][0], ly, m['xsm'][2] + 1)]),
        ('STOREE', S(st, 'south'), ((4, 7, 25 + DZ), 'north'), [st], [(4, 7, 24 + DZ)]),
        ('STOREO', S(st, 'west'), (R.add(m['zbso_end'], R.H['east']), 'west'), [st], [m['zbso_end']]),
        ('KZB', S(st, 'east'), (W(m['dl']['KZB'][-1]), 'east'), [st], [m['dl']['KZB'][-1]]),
        ('ZARR', ((11, 5, 32 + DZ), 'south'), ((m['zb'][0], m['zb'][1], m['zb'][2] + 1), 'north'), [m['gz']], [m['zb']]),
        ('XARR', S(m['xarr_src'], 'east'), ((m['gs_in'][0] - 1, m['gs_in'][1], m['gs_in'][2]), 'east'),
         [m['xarr_src']], [m['gs_in']]),
        ('SX', S(m['sx_blk'], 'west'), (m['gx_in'], 'west'), [m['sx_blk']], [m['sxm']]),
        ('ZASE', S(reb, 'east'), ((4, 7, -3), 'south'), [reb], [(4, 7, -2)]),
        ('ZASO', S(reb, 'north'), ((2 + ODD_DX, 9, -4), 'west'), [reb], [(1 + ODD_DX, 9, -4)]),
        ('TMR', S(reb, 'south'), ((lx + 7, ly - 2, lz), 'south'), [reb], [(lx + 7, ly - 1, lz)]),
        ('TAPA', ((lx + 7, ly, lz + 1), 'south'), ((hx - 5, hy, hz), "east"), [(lx + 7, ly, lz)], [(hx - 4, hy, hz)]),
        ('TAPB', ((lx + 8, ly, lz), 'east'), ((hx + 19, hy, hz), "west"), [(lx + 7, ly, lz)], [(hx + 18, hy, hz)]),
        ('XSPE', S(xsm, 'east'), (W(e['spit_bulb']), 'east'), [xsm], [e['spit_bulb']]),
        ('XSPO', S(xsm, 'south'), (W(o['spit_bulb']), 'east'), [xsm], [o['spit_bulb']]),
        ('XHPE', S(xb, 'east'), (W(e['hold_bulb']), 'east'), [xb], [e['hold_bulb']]),
        ('XHPO', S(xb, 'south'), (W(m['dl']['XHPO'][-1]), 'east'), [xb], [m['dl']['XHPO'][-1]]),
    ]


L3.build_hand = build_hand
L3.nets = nets
L3.FIRST = ['KZB', 'XSPE', 'XSPO', 'XHPE', 'XHPO', 'TMR', 'TAPA', 'ZASE', 'ZASO']


def build(n, delays=None, verbose=False):
    return L3.build(n, delays=delays, verbose=verbose)


if __name__ == '__main__':
    setup(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
    c = build_hand(N)
    print('hand errors', c.errors[:10])
    c = build(N, verbose=True)
    print('cells', len(c.cells), 'nets', sorted(c.paths))
