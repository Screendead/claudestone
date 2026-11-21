"""Controller for door16_band_pairs_ctrl, west half (logical coords, ZD = 16): one panel drives the even pair (rows 4-5,
slot x3) and the odd pair (rows 6-7, slot x-5) in lockstep. The panel is door16_band_ctrl's (gen/layout.py) moved PZ
south; the x-band actuators sit inside each pair's own cells (PROGRESS.md "Pairs controller"); the rebuild timer
(ladder, bulbs) and every long line are routed by router.py around the machines' swept cells."""
import sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from circuit import Circuit           # noqa: E402
import router as R                    # noqa: E402
import geom                           # noqa: E402

SHOVEL = lambda n: '{Items:[' + ','.join(f'{{Slot:{i}b,id:"minecraft:wooden_shovel",count:1}}' for i in range(n)) + ']}'
PZ = 10
ZD = 16
OBS = 'obsidian'


def panel(c, N):
    """door16_band_ctrl's panel and its ZB/ZA ends, the panel moved PZ south; x-band side removed."""
    T = c.turtle
    m = c.marks
    # even ZB ends (unchanged)
    c.put((4, 7, ZD + 7), 'hopper[facing=down,enabled=true]', 'ZBS', 'hopper')
    c.rep((4, 7, ZD + 8), 'north', 'ZBS', sup=OBS)
    c.rep((4, 7, ZD + 9), 'north', 'ZBS'); c.rep((4, 7, ZD + 10), 'north', 'ZBS')
    c.rep((4, 5, ZD + 9), 'north', 'ZBK'); c.rep((4, 5, ZD + 10), 'north', 'ZBK')
    c.obs((8, 5, ZD + 7), 'west', 'SZ')
    c.block((9, 5, ZD + 7), 'SZ')
    # even ZA ends
    c.put((4, 7, 3), 'hopper[facing=down,enabled=true]', 'ZAS', 'hopper')
    c.rep((4, 7, 2), 'south', 'ZAS', sup=OBS)
    c.rep((4, 7, 1), 'south', 'ZAS')
    c.rep((4, 5, 1), 'south', 'ZAK')
    m.update(zbs=(4, 7, ZD + 8), zbk=(4, 5, ZD + 9), zak=(4, 5, 1), sz=(8, 5, ZD + 7))
    z = lambda v: v + PZ
    ZF, ZR, ZS = z(37), z(41), z(43)
    # lever module
    m['IL'] = (-4, 5, z(30))
    c.obs((-4, 5, z(29)), 'south', 'LP')
    c.block((-4, 5, z(28)), 'LP')
    T((-3, 5, z(28)), 'east', 'LP').fwd(1).turn('south').fwd(1)
    c.rep((-3, 5, z(30)), 'east', 'LVC')
    c.rep((-2, 5, z(30)), 'south', 'GC')
    c.rep((-2, 5, z(31)), 'south', 'CLOSE')
    c.obs((-2, 6, z(31)), 'down', 'CLOSE')
    c.block((-2, 7, z(31)), 'CLOSE')
    c.obs((-2, 8, z(32)), 'down', 'CLOSEK')
    c.rep((-2, 7, z(32)), 'south', 'CLOSEK')
    c.block((-2, 9, z(32)), 'CLOSEK')
    c.obs((-6, 8, z(37)), 'up', 'CLOSEK')            # down-riser into the FETCH block (-6,7,z(37))
    t = T((-2, 9, z(33)), 'south', 'CLOSEK').fwd(z(46) - z(33)).turn('west').fwd(3).turn('north').fwd(z(46) - z(37))
    assert t.p == (-6, 9, z(36)), t.p
    c.rep((-5, 5, z(30)), 'west', 'LV')
    c.block((-6, 5, z(30)), 'LV')
    c.torch((-7, 5, z(30)), 'east', 'NLV')
    c.rep((-8, 5, z(30)), 'west', 'NLV', powered=True)
    c.rep((-9, 5, z(30)), 'south', 'GS', locked=True)
    T((-5, 5, z(28)), 'west', 'LP').fwd(4).turn('south').fwd(1)
    c.rep((-4, 5, z(31)), 'south', 'LV3')
    m.update(gs=(-9, 5, z(30)), gc=(-2, 5, z(30)), gs_in=(-9, 5, z(28)), close=(-2, 7, z(31)))
    # counter and gates
    c.put((-4, 5, z(32)), 'hopper[facing=south,enabled=true]', 'CNT', 'hopper')
    c.put((-4, 5, z(33)), 'dropper[facing=north,triggered=false]' + SHOVEL(N), 'CNT', 'dropper')
    c.support((-4, 5, z(33)))
    T((-4, 5, z(36)), 'north', 'DFIRE').fwd(3)
    c.block((-4, 5, z(37)), 'ZB')
    c.rep((-5, 5, z(37)), 'west', 'GF')
    c.rep((-3, 5, z(37)), 'east', 'GR', locked=True)
    sig = 1 + (14 * N) // 9
    c.comp((-3, 5, z(33)), 'east', 'ED', powered=True, nbt='{OutputSignal:%d}' % sig)
    t = T((-2, 5, z(33)), 'east', 'ED').fwd(1, powered=True).turn('south').fwd(1, powered=True).turn('west')
    t.fwd(1, powered=True).turn('south').fwd(1, powered=True)
    c.comp((-5, 5, z(33)), 'west', 'ED2', powered=True, nbt='{OutputSignal:%d}' % sig)
    c.block((-6, 5, z(33)), 'ED2')
    c.rep((-6, 5, z(34)), 'south', 'ED2', powered=True)
    c.block((-6, 5, z(35)), 'ED2')
    c.torch((-5, 5, z(35)), 'west', 'NE', lit=False)
    c.rep((-5, 5, z(36)), 'south', 'NE')
    m.update(gf=(-5, 5, z(37)), gr=(-3, 5, z(37)), zb=(-4, 5, z(37)))
    # ZB arrival: SZ -> GZ (K_Z lock) -> ZARR -> Zb
    for zz in (ZD + 8, ZD + 9, ZD + 10):
        c.rep((9, 5, zz), 'south', 'SZ')
    c.rep((9, 5, ZD + 11), 'south', 'GZ')
    c.rep((8, 5, ZD + 11), 'east', 'KZ', delay=4)
    m.update(gz=(9, 5, ZD + 11), kz=(8, 5, ZD + 11))
    T((9, 5, ZD + 12), 'south', 'ZARR').fwd(z(39) - (ZD + 12)).turn('west').fwd(12).turn('north').fwd(1)
    # FETCH riser and row-7 run; XK starts at the block under the down-riser
    c.rep((-6, 5, ZF), 'west', 'FETCH')
    c.obs((-6, 6, ZF), 'down', 'FETCH')
    c.block((-6, 7, ZF), 'FETCH')
    c.obs((-17, 6, ZF), 'up', 'FETCH')
    T((-7, 7, ZF), 'west', 'FETCH').fwd(11)
    c.block((-17, 5, ZF), 'XK')
    m['xk_src'] = (-17, 5, ZF)
    # STORE: Gs -> x-9 south -> riser -> row 7 east along ZS -> north along x4 (through block at z35: ZBS_o tap)
    c.obs((4, 6, z(33)), 'up', 'ZBK')
    T((-9, 5, z(31)), 'south', 'STORE').fwd(ZS - z(31) + 1)
    c.obs((-9, 6, ZS), 'down', 'STORE')
    c.block((-9, 7, ZS), 'STORE')
    t = T((-8, 7, ZS), 'east', 'STORE').fwd(12).turn('north').fwd(ZS - 1 - (ZD + 10))
    assert t.p == (4, 7, ZD + 10), t.p
    c.cells[(-9, 5, 44)] = 'stone'; c.meta[(-9, 5, 44)] = dict(kind='block')      # ZBS_o tap on the STORE line
    m['zbso_tap'] = (-9, 5, 44)
    # ZBK: detour (as door16_band_ctrl, moved PZ), then north along x4 with a through block at z35 (ZBK_o tap)
    c.block((4, 5, z(33)), 'ZBK')
    t = T((3, 5, z(33)), 'west', 'ZBK').fwd(3).turn('north').fwd(2).turn('east').fwd(3).turn('north')
    t.fwd(z(30) - 1 - (ZD + 10))
    assert t.p == (4, 5, ZD + 10), t.p
    # K_Z branch from the detour's last turn block (4,5,z(30))
    t = T((5, 5, z(30)), 'east', 'KZB').fwd(2).turn('north').fwd(z(30) - 1 - (ZD + 11))
    assert t.p == (7, 5, ZD + 11), t.p
    c.block((7, 5, ZD + 11), 'KZB')
    # REBUILD: Gr -> riser -> row 7 south, west along ZR to x-22, north (ZAS row 7, ZAK row 5 after a detour)
    c.rep((-2, 5, ZF), 'east', 'REB')
    c.obs((-2, 6, ZF), 'down', 'REB')
    c.block((-2, 7, ZF), 'REB')
    T((-2, 7, ZF + 1), 'south', 'REB').fwd(ZR - ZF - 1).turn('west').fwd(19).turn('north')
    c.obs((-22, 6, ZR - 1), 'up', 'ZAK')
    c.block((-22, 5, ZR - 1), 'ZAK')
    m['zr'] = ZR
    return c


def ladder(c, Xt, Z0, N):
    """door16_band_ctrl's ladder turned to run along z: T at x = Xt flows south from T_0 (Xt,7,Z0), rungs at Xt+1 point
    east, C at Xt+2 flows north into the bulb (Xt+2,7,Z0-2). Pulse i reaches the bulb at T_0 + 4 + 10 i."""
    for i in range(N):
        zi = Z0 + 3 * i
        c.block((Xt, 7, zi), 'LADT'); c.block((Xt + 2, 7, zi), 'LADC')
        c.rep((Xt + 1, 7, zi), 'east', 'LADR')
        if i < N - 1:
            c.rep((Xt, 7, zi + 1), 'south', 'LADT', delay=2); c.rep((Xt, 7, zi + 2), 'south', 'LADT', delay=1)
            c.rep((Xt + 2, 7, zi + 2), 'north', 'LADC'); c.rep((Xt + 2, 7, zi + 1), 'north', 'LADC')
    c.rep((Xt + 2, 7, Z0 - 1), 'north', 'LADC')
    c.put((Xt + 2, 7, Z0 - 2), 'waxed_copper_bulb[lit=false,powered=false]', 'XSM', 'bulb')
    return (Xt + 2, 7, Z0 - 2)


def ends(c):
    """In-tile actuators and sensors (MEASURED in ctrl/exp3 for the even kick and hold)."""
    m = c.marks
    # even pair: kick = hopper in the cell O watches; hold = home-stop obsidian powered from x0; spit hopper as before
    c.put((1, 5, 20), 'hopper[facing=down,enabled=true]', 'XKE', 'hopper')
    for zz in range(21, 31):
        c.rep((1, 5, zz), 'north', 'XKE')
    c.block((1, 5, 31), 'XKE')
    c.obs((1, 6, 31), 'up', 'XKE')                  # down-riser into the block: x3 beside the ZBK line is taken
    c.rep((1, 5, 16), 'east', 'XHE', sup=OBS)
    c.block((0, 5, 16), 'XHE'); c.support((0, 5, 16), OBS)
    c.rep((0, 5, 17), 'north', 'XHE', sup=OBS)
    for zz in range(19, 25):
        c.rep((0, 5, zz), 'north', 'XHE', sup=OBS)
    c.comp((0, 5, 25), 'north', 'XHE')
    c.put((0, 5, 26), 'waxed_copper_bulb[lit=false,powered=false]', 'XHE', 'bulb')
    c.rep((-1, 5, 26), 'east', 'XHPE')
    c.put((2, 7, 17), 'hopper[facing=down,enabled=true]', 'XSE', 'hopper')
    c.rep((1, 7, 17), 'east', 'XSE', sup=OBS)
    c.block((0, 7, 17), 'XSE'); c.support((0, 7, 17), OBS)
    for zz in range(18, 23):
        c.rep((0, 7, zz), 'north', 'XSE', sup=OBS)
    c.support((0, 7, 23), OBS)
    c.comp((0, 7, 23), 'north', 'XSE')
    c.put((0, 7, 24), 'waxed_copper_bulb[lit=false,powered=false]', 'XSE', 'bulb')
    c.rep((0, 7, 25), 'north', 'XSPE', sup=OBS)
    # odd pair: kick, hold and spit from the open wall west of its home; sensor on its N
    c.block((-10, 7, 15), 'XKO')
    c.rep((-9, 7, 15), 'east', 'XKO'); c.rep((-8, 7, 15), 'east', 'XKO')
    c.rep((-7, 7, 16), 'east', 'XHO'); c.rep((-8, 7, 16), 'east', 'XHO')
    c.block((-9, 7, 16), 'XHO')
    c.rep((-9, 7, 17), 'north', 'XHO')
    c.comp((-9, 7, 18), 'north', 'XHO')
    c.put((-9, 7, 19), 'waxed_copper_bulb[lit=false,powered=false]', 'XHO', 'bulb')
    c.put((-6, 9, 15), 'hopper[facing=down,enabled=true]', 'XSO', 'hopper')
    c.rep((-7, 9, 15), 'east', 'XSO', sup=OBS)
    c.block((-8, 9, 15), 'XSO')
    c.rep((-8, 9, 16), 'north', 'XSO'); c.rep((-8, 9, 17), 'north', 'XSO')
    c.comp((-8, 9, 18), 'north', 'XSO')
    c.put((-8, 9, 19), 'waxed_copper_bulb[lit=false,powered=false]', 'XSO', 'bulb')
    c.obs((-6, 7, 11), 'south', 'SX')
    c.rep((-6, 7, 10), 'north', 'SX')
    c.block((-6, 7, 9), 'SX')
    c.rep((-14, 7, 9), 'west', 'GX')
    c.rep((-14, 7, 10), 'north', 'KX', delay=4)
    # odd ZB ends
    c.put((-4, 9, 23), 'hopper[facing=down,enabled=true]', 'ZBSO', 'hopper')
    c.rep((-4, 9, 24), 'north', 'ZBSO', sup=OBS)
    c.rep((-4, 9, 25), 'north', 'ZBSO'); c.rep((-4, 9, 26), 'north', 'ZBSO')
    c.block((-4, 9, 27), 'ZBSO')
    # ZBK_o branches off ZBS_o here and enters R from the west (its back cell (-4,7,25) would wall the crossing):
    # hopper at block + 6 gt, R at block + 14 gt
    c.obs((-5, 8, 27), 'up', 'ZBKO')
    c.rep((-5, 9, 27), 'west', 'ZBKO')
    c.block((-5, 7, 27), 'ZBKO')
    c.rep((-6, 7, 27), 'west', 'ZBKO')
    c.block((-7, 7, 27), 'ZBKO')
    c.rep((-7, 7, 26), 'north', 'ZBKO'); c.rep((-7, 7, 25), 'north', 'ZBKO')
    c.block((-7, 7, 24), 'ZBKO')
    c.rep((-6, 7, 24), 'east', 'ZBKO'); c.rep((-5, 7, 24), 'east', 'ZBKO')
    m.update(gx=(-14, 7, 9), kx=(-14, 7, 10), sx=(-6, 7, 11), xs_e=(0, 7, 24), xs_o=(-8, 9, 19), xh_e=(0, 5, 26),
             xh_o=(-9, 7, 19), hop_xe=(2, 7, 17), hop_xo=(-6, 9, 15), p1_e=(2, 5, 16), p1_o=(-6, 7, 16),
             r_xe=(1, 5, 17), r_xo=(-7, 7, 15), hop_ke=(1, 5, 20))


def north(c):
    """ZAS along z-2 (row 7) and ZAK along z-1 (row 5) from x-22 to both pairs' ZA ends; the odd ends at x-4 rise two
    rows off the lines (observer risers)."""
    m = c.marks
    ZR = m['zr']
    T = c.turtle
    t = T((-22, 7, ZR - 1), 'north', 'ZAS').fwd(ZR + 1).turn('east').fwd(17)
    assert t.p == (-4, 7, -2), t.p
    t.fwd(8).turn('south').fwd(2)
    assert t.p == (4, 7, 1), t.p
    c.obs((-4, 8, -2), 'down', 'ZASO')
    c.block((-4, 9, -2), 'ZASO')
    for zz in (-1, 0, 1):
        c.rep((-4, 9, zz), 'south', 'ZASO')
    c.rep((-4, 9, 2), 'south', 'ZASO', sup=OBS)
    c.put((-4, 9, 3), 'hopper[facing=down,enabled=true]', 'ZASO', 'hopper')
    w = m.get('zak_w', 4)
    t = T((-23, 5, ZR - 1), 'west', 'ZAK').fwd(w).turn('north').fwd(1).turn('east').fwd(w).turn('north')
    t.fwd(ZR - 3).turn('east').fwd(17)
    assert t.p == (-4, 5, -1), t.p
    t.fwd(8).turn('south').fwd(1)
    assert t.p == (4, 5, 1), t.p
    c.obs((-4, 6, -1), 'down', 'ZAKO')
    c.block((-4, 7, -1), 'ZAKO')
    c.rep((-4, 7, 0), 'south', 'ZAKO'); c.rep((-4, 7, 1), 'south', 'ZAKO')
    m.update(zak_o=(-4, 7, 1), zas_o=(-4, 9, 2), zas_hop_o=(-4, 9, 3), zas_hop=(4, 7, 3))


LAD_XT, LAD_Z0 = -18, 22
TAPS = {'TAPA': -12, 'TAPB': -16}      # through blocks on the REBUILD line's west run (x), branches go north
XHM = (-34, 7, 58)          # hold master bulb: taps A and B toggle it on and off, observers relay each toggle


def relay(c, bulb, d, low, high):
    """Comparator reading `bulb` toward d, a repeater after it, observers above and below the repeater; returns the
    repeater. The nets start from the blocks two rows above (high) and below (low) it."""
    v = R.H[d]
    cp, rp = R.add(bulb, v), R.add(bulb, v, 2)
    c.obs((rp[0], rp[1] - 1, rp[2]), 'up', low); c.block((rp[0], rp[1] - 2, rp[2]), low)
    c.obs((rp[0], rp[1] + 1, rp[2]), 'down', high); c.block((rp[0], rp[1] + 2, rp[2]), high)
    c.comp(cp, d, low)
    c.rep(rp, d, low)
    return rp


def extras(c):
    """Hand pieces that join the routed nets: ladder feed, master-bulb observers, tap branch blocks."""
    m = c.marks
    bulb = ladder(c, LAD_XT, LAD_Z0, m['N'])
    m['xsm'] = bulb
    # ladder feed off the ZAS line: a through block at (-22,7,Z0), three reps east into T_0
    c.cells[(-22, 7, LAD_Z0)] = 'stone'; c.meta[(-22, 7, LAD_Z0)] = dict(kind='block')
    bx, by, bz = bulb
    # a bulb's `powered` changes on both edges of every input pulse, so the relay observers watch a repeater fed by a
    # comparator reading the bulb: one change per toggle
    m['xsm_rep'] = relay(c, bulb, 'east', 'XSPE', 'XSPO')
    c.rep((bx, by, bz - 1), 'south', 'CLOSE')
    hx, hy, hz = XHM
    c.put(XHM, 'waxed_copper_bulb[lit=false,powered=false]', 'XHM', 'bulb')
    m['xhm_rep'] = relay(c, XHM, 'west', 'XHPE', 'XHPO')
    m['xhm'] = XHM
    DL = {}
    DL['TAPA'] = [(hx, hy, z) for z in range(hz + 1, hz + 3)]            # north into the master
    DL['TAPB'] = [(x, hy, hz) for x in range(hx + 1, hx + 13)]           # west into the master
    DL['XHPO'] = [(-9, 7, z) for z in range(20, 27)]
    DL['XSPO'] = [(-8, 9, z) for z in range(20, 26)]
    DL['LADF'] = [(LAD_XT, 7, z) for z in range(LAD_Z0 - 1, LAD_Z0 - 12, -1)]
    dirs = {'TAPA': 'north', 'TAPB': 'west', 'XHPO': 'north', 'XSPO': 'north', 'LADF': 'south'}
    for net, cells in DL.items():
        for p in cells:
            if p not in c.cells:
                c.rep(p, dirs[net], net)
    m['dl'] = DL
    for name, xx in TAPS.items():
        c.cells[(xx, 7, m['zr'])] = 'stone'; c.meta[(xx, 7, m['zr'])] = dict(kind='block')


def board(c):
    stat, near_slime, piston = geom.forbidden()
    mq = geom.moving_quartz()
    hard = stat | mq
    near = {R.add(p, v) for p in hard for v in R.NB6}
    bd = R.Board((-30, 12, -8, 60), hard | near | near_slime, hard | near_slime)
    for p, st in c.cells.items():
        if st.startswith('repeater') or st.startswith('comparator'):
            f = st.split('facing=')[1].split(',')[0].split(']')[0]
            q = R.add(p, R.H[R.OPP[f]])
            if q not in c.cells and q not in c.fixed:
                bd.reserved[q] = c.net[p]          # a hand repeater's output cell stays air
    for p, st in c.cells.items():
        if c.meta[p]['kind'] == 'support':
            bd.support[p] = st
            bd.cells[p] = (st, 'support')
        else:
            bd.active[p] = c.net[p]
            bd.cells[p] = (st, c.net[p])
    return bd


def nets(c):
    m = c.marks
    src = m['xk_src']
    bx, by, bz = m['xsm']
    cl = m['close']
    zt = m['zbso_tap']
    out = [
        ('XKE', ((src[0] + 1, 5, src[2]), 'east'), ((1, 7, 31), 'north'), [src], [(1, 6, 31)]),
        ('ZBSO', ((zt[0] - 1, 5, zt[2]), 'west'), ((-4, 9, 28), 'north'), [zt], [(-4, 9, 27)]),
        ('XSPE', ((bx + 3, 5, bz), 'east'), ((0, 7, 26), 'north'), [(bx + 2, 5, bz)], [(0, 7, 25)]),
        ('TAPA', ((TAPS['TAPA'], 7, m['zr'] + 1), 'south'), ((XHM[0], 7, XHM[2] + 3), 'north'),
         [(TAPS['TAPA'], 7, m['zr'])], [(XHM[0], 7, XHM[2] + 2)]),
        ('TAPB', ((TAPS['TAPB'], 7, m['zr'] + 1), 'south'), ((XHM[0] + 13, 7, XHM[2]), 'west'),
         [(TAPS['TAPB'], 7, m['zr'])], [(XHM[0] + 12, 7, XHM[2])]),
        ('XHPE', ((XHM[0] - 3, 5, XHM[2]), 'west'), ((-2, 5, 26), 'east'), [(XHM[0] - 2, 5, XHM[2])], [(-1, 5, 26)]),
        ('XARR', ((-15, 7, 9), 'west'), ((-9, 5, 37), 'south'), [m['gx']], [m['gs_in']]),
        ('CLOSE', ((cl[0], 7, cl[2] - 1), 'north'), ((bx, 7, bz - 2), 'south'), [cl], [(bx, 7, bz - 1)]),
        ('XSPO', ((bx + 3, 9, bz), 'east'), ((-8, 9, 26), 'north'), [(bx + 2, 9, bz)], [(-8, 9, 25)]),
        ('LADF', ((-23, 7, LAD_Z0), 'west'), ((LAD_XT, 7, LAD_Z0 - 12), 'south'), [(-22, 7, LAD_Z0)],
         [(LAD_XT, 7, LAD_Z0 - 11)]),
        ('XHPO', ((XHM[0] - 3, 9, XHM[2]), 'west'), ((-9, 7, 27), 'north'), [(XHM[0] - 2, 9, XHM[2])], [(-9, 7, 26)]),
        ('XKO', ((src[0], 5, src[2] - 1), 'north'), ((-11, 7, 15), 'east'), [src], [(-10, 7, 15)]),
        ('KX', ((src[0] - 1, 5, src[2]), 'west'), ((-14, 7, 11), 'north'), [src], [m['kx']]),
        ('SX', ((-7, 7, 9), 'west'), ((-13, 7, 9), 'west'), [(-6, 7, 9)], [m['gx']]),
    ]
    return out


PULSE = {}


ORDER = ['ZBSO', 'XKE', 'XHPE', 'XSPE', 'TAPA', 'TAPB']


MAXD = {'LADF': 3, 'XSPE': 2, 'XSPO': 2}   # in a train 10 gt apart a repeater must not outlast the gap


def build(N, order=None, verbose=False, tries=30, tails=None, zak_w=3, delays=None):
    tails = tails or {}
    order = list(order or ORDER)
    for attempt in range(tries):
        c = Circuit(geom.WEST)
        c.marks = {'N': N, 'zak_w': zak_w}
        panel(c, N); ends(c); north(c); extras(c)
        assert not c.errors, c.errors
        bd = board(c)
        bd.bounds = (-44, 12, -8, 66)
        for n in nets(c):
            bd.reserved.pop(n[1][0], None)
        paths = {}
        todo = sorted(nets(c), key=lambda n: order.index(n[0]) if n[0] in order else 99)
        try:
            for name, start, goal, a_s, a_e in todo:
                paths[name] = R.route(bd, name, start, goal, pulse=PULSE.get(name, True), allow_start=a_s,
                                      allow_end=a_e, tail=tails.get(name, 0))
            break
        except RuntimeError:
            if verbose:
                print('failed', name, 'order', order)
            import random
            rest = [n[0] for n in todo if n[0] != name]
            if attempt % 2 == 1:
                random.Random(attempt).shuffle(rest)
            order = [name] + rest
    else:
        raise RuntimeError('routing failed')
    if verbose:
        print('order', order)
    for p, (st, net) in bd.cells.items():
        if p not in c.cells:
            c.cells[p] = st
            c.net[p] = net
            c.meta[p] = dict(kind='support' if p in bd.support else 'routed')
    for name, gt in (delays or {}).items():
        if not gt:
            continue
        if name in c.marks['dl']:
            R.set_delays(bd, paths[name] + [('rep', p) for p in c.marks['dl'][name]], gt, maxd=MAXD.get(name, 4))
        else:
            R.set_delays(bd, paths[name], gt, maxd=MAXD.get(name, 4))
    for p, (st, net) in bd.cells.items():
        c.cells[p] = st
    c.paths, c.board = paths, bd
    return c
