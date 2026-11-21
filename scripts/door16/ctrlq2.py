"""Controller for QUART door slices of any number of row pairs (PROGRESS.md "QUART rework", stage 3+): ctrlq's
layout with tile-safe ends and observer towers (as pc/layout6): each class's upper pairs get every signal from a tower
standing on a tap of the pair below's end chain, 6 gt per level.

Tile rules for an end cell inside the x-band zone (x >= -14, z ZD-5..ZD): only a pair's top row at k2..k5 or its door
plane, since the other class's bands pass right below (honey/slime at k1..k5 of its top row) and above (k1 of its
bottom row). End chains therefore come in along z from outside the zone, at the pair's top row.
call setup(N, pairs) first."""
import sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import geomq                                   # noqa: E402
sys.modules['geom'] = geomq
import layout2 as L2                           # noqa: E402,F401
import layout3 as L3                           # noqa: E402
import router as R                             # noqa: E402
from circuit import Circuit                    # noqa: E402

OLD_ZD = 16
N = ZD = DZ = PAIRS = None
bq = None
ODD_DX = -3
UP = lambda p, k=1: (p[0], p[1] + k, p[2])
UPSTREAM = set()   # base-pair hand cells ahead of the taps
CHAINS = {}        # net -> [e1, e2, e3] tap repeaters of the base pair, in signal order
CLASS_NETS = {'e': [], 'o': []}


def setup(n, pairs=2):
    global N, ZD, DZ, bq, PAIRS
    L3.SNAKE_ENDS.clear()
    for k in ('CLOSE2', 'CLOSE3', 'ZASE', 'ZASO'):
        L3.SNAKE.pop(k, None)
    if n > 5:                       # one stack of sticks: the counter's return hopper has 5 slots (door16_full)
        L2.SHOVEL = lambda k: '{Items:[{Slot:0b,id:"minecraft:stick",count:%d}]}' % k
        L3.SIG = lambda k: 1 + (14 * k) // (64 * 9)
    bq = geomq.setup(n, pairs, obs_k4=True)
    N, ZD, PAIRS = n, geomq.ZD, pairs
    DZ = ZD - OLD_ZD
    L3.ROWS = COMPACT['rows'] or (-7, -5, -3, -1, 1, 3, 5, 7, 9)
    if COMPACT['closek_lines']:
        CLOSEK_LINES[0] = COMPACT['closek_lines']
    L3.SZ_SHORT = COMPACT['sz_short']
    if COMPACT['first']:
        L3.FIRST = list(COMPACT['first'])
    L3.BOUNDS = COMPACT['bounds'] or (-24 if n <= 5 else -40, 13, -24, ZD + 30)
    L3.PREV.clear()
    if COMPACT['pin']:              # routes kept from an earlier build (start and goal unchanged), reused when free
        import pickle
        PINNED.update(pickle.load(open(HERE / COMPACT['pin'], 'rb')))
        L3.PREV.update(PINNED)
    return bq


PINNED = {}
_remember = L3.remember


def remember(c):
    _remember(c)
    L3.PREV.update(PINNED)


L3.remember = remember


def copy_module(c, fn, move):
    k = Circuit({})
    k.marks = dict(c.marks)
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


def run(c, p, d, n, net, k=1):
    """n repeaters from p in direction d (signal direction); returns the list."""
    out = []
    for i in range(n):
        q = R.add(p, R.H[d], i)
        c.rep(q, d, net)
        out.append(q)
    return out


def timer_east(c, N):
    """COMPACT['ladder_e']: layout3.timer with the ladder flowing east from T_0 (x0, y, zt), so the spit master sits
    at its west end (x0 - 2) between the classes' ends without the ladder reaching west of it; the feed (LADF) comes
    into T_0 from the north, the timer split TMR 7 cells north of T_0, the spit master's relay goes north."""
    m = c.marks
    x0, zt, y = L3.LAD['x0'], L3.LAD['zt'], L3.LAD['y']
    for i in range(N):
        xi = x0 + 3 * i
        c.block((xi, y, zt), 'LADT'); c.block((xi, y, zt + 2), 'LADC')
        c.rep((xi, y, zt + 1), 'south', 'LADR')
        if i < N - 1:
            c.rep((xi + 1, y, zt), 'east', 'LADT', delay=2); c.rep((xi + 2, y, zt), 'east', 'LADT', delay=1)
            c.rep((xi + 2, y, zt + 2), 'west', 'LADC'); c.rep((xi + 1, y, zt + 2), 'west', 'LADC')
    c.rep((x0 - 1, y, zt + 2), 'west', 'LADC')
    b = (x0 - 2, y, zt + 2)
    c.put(b, 'waxed_copper_bulb[lit=false,powered=false]', 'XSM', 'bulb')
    m['xsm'] = b
    m['xs_comp'], m['xsm_out'] = L3.relay_low(c, b, 'north', 'XSP')
    c.rep((b[0], y, b[2] + 1), 'north', 'CLOSE')
    c.put(L3.XHM, 'waxed_copper_bulb[lit=false,powered=false]', 'XHM', 'bulb')
    m['xhm'] = L3.XHM
    m['xh_comp'], m['xhm_out'] = L3.relay_low(c, L3.XHM, 'north', 'XHP')
    lf = [(x0, y, z) for z in range(zt - 1, zt - 7, -1)]
    for p in lf:
        c.rep(p, 'south', 'LADF')
    m.setdefault('dl', {}).update(LADF=lf, TAPA=[], TAPB=[], XHPO=[], XSPO=[])
    m['tmr'] = m['tmr_e'] = (x0, y, zt - 7)
    c.block(m['tmr'], 'TMR')
    c.obs((x0, y - 1, zt - 7), 'down', 'TMR')


def timer_split(c, N):
    """COMPACT['ladder_split'] = bx: the spit ladder split in two halves on either side of the spit master (bulb at
    (bx, y, zt + 2)): rungs 0..N/2-1 west-flowing as layout3's ladder, rungs N/2.. a mirrored east-flowing ladder
    whose T_0 gets the feed 10 * N/2 gt later through a hairpin of delay-1/2 repeaters (pulses stay <= 4 gt, so the
    10 gt train keeps its gaps in the C lines). Same pulse times as the one-sided ladder (T_0 + 4 + 10 i), half the
    length; the relay goes north, LADF comes from the north through the split block F."""
    m = c.marks
    bx, zt, y = COMPACT['ladder_split'], L3.LAD['zt'], L3.LAD['y']
    h = N // 2
    for sgn, x0, cnt in ((-1, bx - 2, h), (1, bx + 2, N - h)):
        fw, bw = ('west', 'east') if sgn < 0 else ('east', 'west')
        for i in range(cnt):
            xi = x0 + sgn * 3 * i
            c.block((xi, y, zt), 'LADT'); c.block((xi, y, zt + 2), 'LADC')
            c.rep((xi, y, zt + 1), 'south', 'LADR')
            if i < cnt - 1:
                c.rep((xi + sgn, y, zt), fw, 'LADT', delay=2); c.rep((xi + 2 * sgn, y, zt), fw, 'LADT', delay=1)
                c.rep((xi + 2 * sgn, y, zt + 2), bw, 'LADC'); c.rep((xi + sgn, y, zt + 2), bw, 'LADC')
        c.rep((x0 - sgn, y, zt + 2), bw, 'LADC')
        c.rep((x0, y, zt - 1), 'south', 'LADT')
    b = (bx, y, zt + 2)
    c.put(b, 'waxed_copper_bulb[lit=false,powered=false]', 'XSM', 'bulb')
    m['xsm'] = b
    m['xs_comp'], m['xsm_out'] = L3.relay_low(c, b, 'north', 'XSP')
    c.rep((bx, y, zt + 3), 'north', 'CLOSE')
    F = (bx - 2, y, zt - 2)
    c.block(F, 'LADT')
    hp = [(bx - 1, y, zt - 2, 'east')] + [(bx, y, z, 'north') for z in range(zt - 3, zt - 8, -1)] + \
        [(bx + 1, y, zt - 8, 'east')] + [(bx + 2, y, z, 'south') for z in range(zt - 7, zt - 1)]
    units = 5 * h                               # T_0(east) - T_0(west) = 10 h gt; both end with a delay-1 feed
    for i, (x, yy, z, d) in enumerate(hp):
        k = 2 if units - 2 >= len(hp) - 1 - i else 1
        units -= k
        c.rep((x, yy, z), d, 'LADT', delay=k)
    assert units == 0, units
    c.block((bx, y, zt - 2), 'LADT'); c.block((bx, y, zt - 8), 'LADT'); c.block((bx + 2, y, zt - 8), 'LADT')
    c.put(L3.XHM, 'waxed_copper_bulb[lit=false,powered=false]', 'XHM', 'bulb')
    m['xhm'] = L3.XHM
    m['xh_comp'], m['xhm_out'] = L3.relay_low(c, L3.XHM, 'north', 'XHP')
    lf = [(bx - 2, y, z) for z in range(zt - 3, zt - 9, -1)]
    for p in lf:
        c.rep(p, 'south', 'LADF')
    m.setdefault('dl', {}).update(LADF=lf, TAPA=[], TAPB=[], XHPO=[], XSPO=[])
    m['tmr'] = m['tmr_e'] = (bx - 2, y, zt - 9)
    c.block(m['tmr'], 'TMR')
    c.obs((bx - 2, y - 1, zt - 9), 'down', 'TMR')


def fold(c, net, end, sx, k):
    """A two-row repeater line (2k + 1 repeaters, all tunable, delay_serpentine's fold) running along x away from
    `end` (sx = +1: east of it) on its row, turning through z + 1, and back on row z + 2. Returns (reps, goal)."""
    ex, y, z = end
    dx = {1: 'east', -1: 'west'}
    reps = []
    for i in range(k):                         # first row (z + 2), toward the turn
        q = (ex + sx * (1 + i), y, z + 2)
        c.rep(q, dx[sx], net); reps.append(q)
    xt = ex + sx * (1 + k)
    c.block((xt, y, z + 2), net)
    c.rep((xt, y, z + 1), 'north', net); reps.append((xt, y, z + 1))
    c.block((xt, y, z), net)
    for i in range(k - 1, -1, -1):             # back along the end's row into the end block
        q = (ex + sx * (1 + i), y, z)
        c.rep(q, dx[-sx], net); reps.append(q)
    c.block((ex, y, z + 2), net)              # entry block, fed from the south
    return reps, ((ex, y, z + 3), 'north')


def x_ends(c):
    m = c.marks
    xs = {}
    for n, cls in ((1, 'E'), (2, 'O')):
        side, b, xw = bq.BANDS[n]
        t, xp = b + 1, xw + 3
        # kick: hopper in O's watched cell, fed from the north by a comparator (immovable beside the west half's
        # glue), reps along z from outside the zone; taps e1..e3 are the first three
        kick = (xw - 2, t, ZD - 2)
        c.put(kick, 'hopper[facing=down,enabled=true]', f'XK{cls}', 'hopper')
        # an obsidian block north of the hopper carries the pulse (comparators drop 2 gt pulses; anything movable
        # there sits beside the west half's glue), fed by repeaters along z with obsidian supports (x = xw-2 borders
        # the odd z-corridor's slime one row down in the upper even pairs)
        c.block((xw - 2, t, ZD - 3), f'XK{cls}', 'obsidian')
        for z in range(ZD - 8, ZD - 3):
            c.put((xw - 2, t - 1, z), 'obsidian', 'support', 'support')
            c.rep((xw - 2, t, z), 'south', f'XK{cls}')
        if cls == 'O':
            reps = run(c, (xw - 2, t, ZD - 11), 'south', 3, 'XKO')
            CHAINS['XKO'] = reps[:3]
            kick_goal = ((xw - 2, t, ZD - 12), 'south')
        else:       # taps and their towers away from the corridor, at x = xw+1, turning in through an obsidian corner
            c.block((xw - 2, t, ZD - 9), 'XKE', 'obsidian')
            c.rep((xw - 1, t, ZD - 9), 'west', 'XKE')
            c.rep((xw, t, ZD - 9), 'west', 'XKE')
            c.block((xw + 1, t, ZD - 9), 'XKE')
            # a repeater must follow every tap: a tower's top block powers only a repeater, never the next block
            reps = run(c, (xw + 1, t, ZD - 13), 'south', 4, 'XKE')
            CHAINS['XKE'] = reps[:3]
            kick_goal = ((xw + 1, t, ZD - 14), 'south')
        # spit: hopper in Ob's watched cell <- rep <- comparator <- bulb <- block <- reps along z
        spit = (xw + 1, t, ZD)
        c.put(spit, 'hopper[facing=down,enabled=true]', f'XS{cls}', 'hopper')
        c.rep((xw + 1, t, ZD + 1), 'north', f'XS{cls}')
        c.comp((xw + 1, t, ZD + 2), 'north', f'XS{cls}')
        c.put((xw + 1, t, ZD + 3), 'waxed_copper_bulb[lit=false,powered=false]', f'XS{cls}', 'bulb')
        c.block((xw, t, ZD + 3), f'XS{cls}')
        nsp = 8 if N <= 5 else 13      # 3 taps + delay line (a spit train takes delay 2 at most)
        if cls == 'O' and COMPACT['nsp_o']:
            nsp = COMPACT['nsp_o']
        if cls == 'E':
            reps = run(c, (xw, t, ZD + 3 + nsp), 'north', nsp, f'XSP{cls}')
            spit_goal = ((xw, t, ZD + 4 + nsp), 'north')
        elif COMPACT['odd_south']:  # the line along z one column west, into a block that drives a repeater
            for dct in (c.cells, c.net, c.meta):    # into the bulb from the west (x min stays at the band's)
                dct.pop((xw, t, ZD + 3), None)
            c.rep((xw, t, ZD + 3), 'east', f'XS{cls}')
            c.block((xw - 1, t, ZD + 3), f'XS{cls}')
            reps = run(c, (xw - 1, t, ZD + 3 + nsp), 'north', nsp, f'XSP{cls}')
            spit_goal = ((xw - 1, t, ZD + 4 + nsp), 'north')
        else:                       # the odd ZB kick loop holds x-10..-8 at z ZD+8..11: runs go west instead
            reps = run(c, (xw - nsp, t, ZD + 3), 'east', nsp, f'XSP{cls}')
            spit_goal = ((xw - nsp - 1, t, ZD + 3), 'east')
        CHAINS[f'XSP{cls}'] = reps[:3]
        m.setdefault('dl', {})[f'XSP{cls}'] = reps[3:]
        # hold: repeaters into P(t) (P(b) by QC) <- comparator <- bulb <- block <- reps along z
        c.rep((xp, t, ZD + 1), 'north', f'XH{cls}')
        c.rep((xp, t, ZD + 2), 'north', f'XH{cls}')
        c.rep((xp, t, ZD + 3), 'north', f'XH{cls}')
        c.comp((xp, t, ZD + 4), 'north', f'XH{cls}')
        c.put((xp, t, ZD + 5), 'waxed_copper_bulb[lit=false,powered=false]', f'XH{cls}', 'bulb')
        c.block((xp - 1, t, ZD + 5), f'XH{cls}')
        if cls == 'E':
            reps = run(c, (xp - 1, t, ZD + 13), 'north', 8, f'XHP{cls}')
            hold_goal = ((xp - 1, t, ZD + 14), 'north')
        elif COMPACT['odd_south']:  # block x = xw, repeaters into the bulb from the west, the line along z at x = xw
            nh = COMPACT['nhp_o'] or 8
            for dct in (c.cells, c.net, c.meta):
                dct.pop((xp - 1, t, ZD + 5), None)
            c.rep((xp - 1, t, ZD + 5), 'east', f'XH{cls}')
            c.rep((xp - 2, t, ZD + 5), 'east', f'XH{cls}')
            c.block((xp - 3, t, ZD + 5), f'XH{cls}')
            reps = run(c, (xp - 3, t, ZD + 5 + nh), 'north', nh, f'XHP{cls}')
            # the line's turn is placed here, not routed: a block south of the line, fed from the east. Any routed
            # way into this column ends on a block beside the spit line (x = xw - 1), which the router never
            # allows, and the spit route then has no way past it (PROGRESS.md, "odd lines along z")
            c.block((xp - 3, t, ZD + 6 + nh), f'XHP{cls}')
            hold_goal = ((xp - 2, t, ZD + 6 + nh), 'west')
        else:
            nh = COMPACT['nhp_o'] or 8
            reps = run(c, (xp - 1 - nh, t, ZD + 5), 'east', nh, f'XHP{cls}')
            hold_goal = ((xp - 2 - nh, t, ZD + 5), 'east')
        CHAINS[f'XHP{cls}'] = reps[:3]
        m.setdefault('dl', {})[f'XHP{cls}'] = reps[3:]
        xs[cls] = dict(kick=kick, spit=spit, spit_bulb=(xw + 1, t, ZD + 3), spit_comp=(xw + 1, t, ZD + 2),
                       hold_bulb=(xp, t, ZD + 5), hold_comp=(xp, t, ZD + 4), p_t=(xp, t, ZD),
                       kick_goal=kick_goal, spit_goal=spit_goal, hold_goal=hold_goal)
    # odd home sensor + arrival filter (ctrlq), base pair only
    side, b, xw = bq.BANDS[2]
    t = b + 1
    c.obs((xw - 1, t, ZD - 1), 'north', 'SX')
    c.block((xw - 1, t, ZD), 'SX')
    m['sx'], m['sx_blk'] = (xw - 1, t, ZD - 1), (xw - 1, t, ZD)
    y, z = 1, 8
    X = lambda x: x + COMPACT['sx_dx']          # the arrival filter moved east (COMPACT), same shape
    z += COMPACT['sx_dz']
    c.rep((X(-12), y, z), 'west', 'SXM', delay=4)
    c.put((X(-13), y, z), 'waxed_copper_bulb[lit=false,powered=false]', 'SXA', 'bulb')
    c.comp((X(-14), y, z), 'west', 'SXA')
    c.block((X(-15), y, z), 'SXA')
    c.torch((X(-15), y, z - 1), 'south', 'SXT', lit=True)
    c.rep((X(-16), y, z - 1), 'west', 'SXT', powered=True)
    c.put((X(-17), y, z - 1), 'waxed_copper_bulb[lit=false,powered=true]', 'SXB', 'bulb')
    cp, blk = L3.relay_low(c, (X(-17), y, z - 1), 'west', 'XARR')
    m.update(gx_in=(X(-11), y, z), sxm=(X(-12), y, z), sxa=(X(-13), y, z), sxb=(X(-17), y, z - 1), xarr_src=blk)
    m['xs'] = xs


def zb_ends(c):
    """Even: layout3's zb_even moved +DZ, its spit line lengthened along z past the ZB home (taps). Odd: spit hopper
    and a kick through the cell behind R (8 gt after the hopper), all at x = slot+1."""
    k = copy_module(c, L3.zb_even, zshift)
    c.marks.update({key: zshift(v) for key, v in k.marks.items() if key in ('sz', 'gz', 'kz', 'zbk_e_in', 'gz_in')})
    me = bq.MARKS[(1, 'B')]
    hx, hy, hz = me['spit']
    ns = COMPACT['storee_n'] or 6     # 3 taps, then at least one repeater (a tower's top block feeds a repeater)
    reps = run(c, (hx, hy, hz + 1 + ns), 'north', ns, 'STOREE')
    CHAINS['STOREE'] = reps[:3]
    c.marks['storee_goal'] = ((hx, hy, hz + 2 + ns), 'north')
    kz = c.marks['kz']                                       # K_Z line: a block behind KZ, fed along z
    c.block((kz[0] - 1, kz[1], kz[2]), 'KZB')
    if COMPACT['kzb_x']:            # the K_Z delay line along x, west of its block (kzb_x repeaters)
        k = COMPACT['kzb_x']
        c.marks.setdefault('dl', {})['KZB'] = run(c, (kz[0] - 1 - k, kz[1], kz[2]), 'east', k, 'KZB')
        c.marks['kzb_goal'] = ((kz[0] - 2 - k, kz[1], kz[2]), 'east')
    else:
        k = COMPACT['kzb_n'] or 6
        c.marks.setdefault('dl', {})['KZB'] = run(c, (kz[0] - 1, kz[1], kz[2] + k), 'north', k, 'KZB')
        c.marks['kzb_goal'] = ((kz[0] - 1, kz[1], kz[2] + k + 1), 'north')
    mo = bq.MARKS[(2, 'B')]
    hx, hy, hz = mo['spit']                                  # (s+1, b+3, ze)
    c.put((hx, hy, hz), 'hopper[facing=down,enabled=true]', 'ZBSO', 'hopper')
    c.rep((hx, hy, hz + 1), 'north', 'ZBSO', sup='obsidian')
    c.rep((hx, hy, hz + 2), 'north', 'ZBSO'); c.rep((hx, hy, hz + 3), 'north', 'ZBSO')
    c.block((hx, hy, hz + 4), 'ZBSO')
    reps = run(c, (hx, hy, hz + 8), 'north', 4, 'ZBSO')
    CHAINS['ZBSO'] = reps[:3]
    c.marks['storeo_goal'] = ((hx, hy, hz + 9), 'north')
    # kick (layout2's ZBK_o): branches off the block at hz+4, enters R from the west, all 2 gt pulses:
    # hopper at block + 6 gt, R at block + 14 gt
    z4 = hz + 4
    c.obs((hx - 1, hy - 1, z4), 'up', 'ZBKO')
    c.rep((hx - 1, hy, z4), 'west', 'ZBKO')
    c.block((hx - 1, hy - 2, z4), 'ZBKO')
    c.rep((hx - 2, hy - 2, z4), 'west', 'ZBKO')
    c.block((hx - 3, hy - 2, z4), 'ZBKO')
    c.rep((hx - 3, hy - 2, z4 - 1), 'north', 'ZBKO'); c.rep((hx - 3, hy - 2, z4 - 2), 'north', 'ZBKO')
    c.block((hx - 3, hy - 2, z4 - 3), 'ZBKO')
    c.rep((hx - 2, hy - 2, z4 - 3), 'east', 'ZBKO'); c.rep((hx - 1, hy - 2, z4 - 3), 'east', 'ZBKO')
    c.marks.update(zbs_o=(hx, hy, hz), zbk_o_in=(hx - 1, hy - 2, z4 - 3))


ZAS_EXTRA = {'e': 0, 'o': 0}
# compaction overrides (None = stage4 placement); set by pairs_ctrlq --compact
COMPACT = dict(bounds=None, lad_x0=None, xhm=None, close2=None, closek=None, taps_x=False, kzb_x=False, za_obs=False, ladder_e=False, ladder_split=None, nsp_o=None, nhp_o=None,
               sx_dx=0, sx_dz=0, close2_len=None, close2_lines=None, closek_len=None, closek_lines=None, rows=None, odd_south=False, first=None, sz_short=False, storee_n=None, kzb_n=None, close3_snake=None, pin=None)
CLOSEK_LINES = [4]             # the close kick's delay-1 snake (layout3: 9 x 4)     # fixed delay-1 repeaters ahead of each ZA spit line's taps (set by timingq2.tuned)


def za_ends(c):
    """layout3's ZA ends; a ZA spit line can't take delay settings (its taps' towers and the observer deriving the
    ZA kick both need 2 gt pulses), so its delay is extra delay-1 repeaters ahead of the taps."""
    copy_module(c, L3.za, odd_move)
    c.marks.update(r_e_in=(4, 5, 1), r_o_in=(-4 + ODD_DX, 7, 1))
    CHAINS['ZASE'] = [(4, 7, -2), (4, 7, -1), (4, 7, 0)]
    CHAINS['ZASO'] = [(-2 + 0, 9, -4), (-3, 9, -4), (-4, 9, -4)]
    ke, ko = ZAS_EXTRA['e'], ZAS_EXTRA['o']
    c.marks['zase_goal'] = ((4, 7, -3), 'south')
    c.marks['zaso_goal'] = ((-1, 9, -4), 'west')
    if COMPACT['za_obs']:
        return za_obs(c)
    if N <= 5:                      # stage 3 (door16_quart_slice4): straight lines
        run(c, (4, 7, -2 - ke), 'south', ke, 'ZASE')
        c.marks['zase_goal'] = ((4, 7, -3 - ke), 'south')
        if ko:
            c.block((-1, 9, -4), 'ZASO')
            run(c, (-1, 9, -4 - ko), 'south', ko, 'ZASO')
            c.marks['zaso_goal'] = ((-1, 9, -5 - ko), 'south')
    else:                           # hairpins of 2m + 1 delay-1 repeaters right at the ends, so the routes stay put
        before = set(c.cells)
        if ke:
            m = max(1, (ke - 1) // 2)
            run(c, (4, 7, -2 - m), 'south', m, 'ZASE')                 # column into the first tap
            c.block((4, 7, -3 - m), 'ZASE')
            c.rep((5, 7, -3 - m), 'west', 'ZASE')
            c.block((6, 7, -3 - m), 'ZASE')
            run(c, (6, 7, -3), 'north', m, 'ZASE')
            c.marks['zase_goal'] = ((6, 7, -2), 'north')
        if ko:
            m = max(1, (ko - 1) // 2)
            c.block((-1, 9, -4), 'ZASO')
            run(c, (-1, 9, -4 - m), 'south', m, 'ZASO')
            c.block((-1, 9, -5 - m), 'ZASO')
            c.rep((0, 9, -5 - m), 'west', 'ZASO')
            c.block((1, 9, -5 - m), 'ZASO')
            run(c, (1, 9, -5), 'north', m, 'ZASO')
            c.marks['zaso_goal'] = ((1, 9, -4), 'north')
        UPSTREAM.update(set(c.cells) - before)      # fed by the route: not copied to the upper pairs


def obs_box(n, corner, grow, nxmax=6):
    """An observer path of n cells in a box at `corner` growing along `grow` (signs per axis), ending at `corner`, and
    its input cell: the path is a full serpentine of the box (rows along x, then z, then layers) with the first
    v - n cells of its bottom layer left as air for the route to enter through, so the input sits in the bottom
    layer (an odd height puts it on an odd routing row). Returns (cells in signal order, input cell, signal direction there)."""
    import itertools
    best = None
    for nx, ny, nz in itertools.product(range(1, nxmax + 1), range(1, 10, 2), range(1, 7)):
        v = nx * ny * nz
        if v - nx * nz < n <= v and (best is None or (nz, v, -ny) < best[0]):
            best = ((nz, v, -ny), (nx, ny, nz))
    nx, ny, nz = best[1]
    flat = [(x if z % 2 == 0 else nx - 1 - x, z) for z in range(nz) for x in range(nx)]
    full = [(-1, 0, 0)]
    for y in range(ny):
        full += [(x, y, z) for x, z in (flat if y % 2 == 0 else flat[::-1])]
    r = len(full) - 1 - n
    end = full[-1]
    dims = (nx, ny, nz)

    def m(p):
        return tuple(corner[i] + grow[i] * (p[i] if end[i] == 0 else dims[i] - 1 - p[i]) for i in range(3))
    cells = [m(p) for p in full[r + 1:]]
    inp = m(full[r])
    d = tuple(cells[0][i] - inp[i] for i in range(3))
    return cells, inp, {(1, 0, 0): 'east', (-1, 0, 0): 'west', (0, 0, 1): 'south', (0, 0, -1): 'north'}[d]


def place_obs(c, net, path, inp, out_cell):
    """Observers along path, each facing the one before it (the first faces inp, the route's last repeater); the
    last outputs into out_cell."""
    D = {(1, 0, 0): 'east', (-1, 0, 0): 'west', (0, 1, 0): 'up', (0, -1, 0): 'down', (0, 0, 1): 'south',
         (0, 0, -1): 'north'}
    prev = inp
    for p in path:
        c.put(p, f'observer[facing={D[tuple(prev[i] - p[i] for i in range(3))]},powered=false]', net, 'obs')
        prev = p
    last = path[-1]
    assert tuple(2 * last[i] - out_cell[i] for i in range(3)) == path[-2], (net, path[-2:], out_cell)


def za_obs(c):
    """COMPACT['za_obs']: each ZA spit line's extra delay as an observer path packed in a box beside its first tap
    (delay_observer_cube; observer_chain_pulse_merge: a 2 gt pulse stays one 2 gt pulse), instead of a hairpin."""
    before = set(c.cells)
    for cls, e1, fin, grow, net, nxm in (('e', (4, 7, -2), (4, 7, -3), (1, -1, -1), 'ZASE', 6),
                                         ('o', (-2, 9, -4), (-1, 9, -4), (1, -1, -1), 'ZASO', 4)):
        n = ZAS_EXTRA[cls]
        corner = tuple(2 * fin[i] - e1[i] for i in range(3))
        path, inp, d = obs_box(n - 1, corner, grow, nxm)
        place_obs(c, net, path + [fin], inp, e1)
        c.marks['zase_goal' if cls == 'e' else 'zaso_goal'] = (inp, d)
    UPSTREAM.update(set(c.cells) - before)


EVEN_NETS = ['XKE', 'XSE', 'XSPE', 'XHE', 'XHPE', 'STOREE', 'ZBKE', 'ZASE', 'ZAKE']
ODD_NETS = ['XKO', 'XSO', 'XSPO', 'XHO', 'XHPO', 'ZBSO', 'ZBKO', 'ZASO', 'ZAKO']
TOWER_NETS = {'e': ['XKE', 'XSPE', 'XHPE', 'STOREE', 'ZASE'], 'o': ['XKO', 'XSPO', 'XHPO', 'ZBSO', 'ZASO']}


def check_taps(c):
    for n, ch in CHAINS.items():
        for e in ch:
            st = c.cells[e]
            f = st.split('facing=')[1].split(',')[0]
            nxt = R.add(e, R.H[R.OPP[f]])
            assert c.cells.get(nxt, '').startswith('repeater') or nxt not in c.cells and False, (n, e, nxt, c.cells.get(nxt))


def towers(c):
    check_taps(c)
    """Copy each class's end modules to its upper pairs; level L's tower stands on tap e_L of the pair below."""
    base = {p: (st, c.net[p], c.meta[p]) for p, st in c.cells.items()}
    sup = {p: st for p, (st, n, mt) in base.items() if mt['kind'] == 'support'}
    owner = lambda p: base[p][1] if base[p][1] != 'support' else base.get(UP(p), (None, 'support'))[1]
    levels = {'e': (PAIRS + 1) // 2 - 1, 'o': PAIRS // 2 - 1}
    for cls, nets in (('e', EVEN_NETS), ('o', ODD_NETS)):
        tn = TOWER_NETS[cls]
        for L in range(1, levels[cls] + 1):
            skip = set().union(*[set(CHAINS[n][:L - 1]) for n in tn])
            tops = {CHAINS[n][L - 1] for n in tn}
            tower = {UP(CHAINS[n][L - 1], 4 * (L - 1) + k) for n in tn for k in (1, 2, 3)}
            for p, (st, net, mt) in base.items():
                o = owner(p)
                if o not in nets or p in skip or p in UPSTREAM or (mt['kind'] == 'support' and UP(p) in UPSTREAM):
                    continue
                q = UP(p, 4 * L)
                if mt['kind'] == 'support':
                    if q not in tower and q not in c.cells:
                        c.put(q, st, 'support', 'support')
                    continue
                if p in tops:
                    c.block(q, f'{net}{L}')
                    continue
                c.put(q, st, f'{net}{L}', mt['kind'], **{a: b for a, b in mt.items() if a != 'kind'})
            for n in tn:
                w = UP(CHAINS[n][L - 1], 4 * (L - 1))
                for k in (1, 2, 3):
                    q = UP(w, k)
                    if q in c.cells and c.meta[q]['kind'] == 'support':
                        del c.cells[q], c.net[q], c.meta[q]
                    c.obs(q, 'down', f'{n}T{L}')


def parity(c):
    """Even N: the spit master toggles N + 1 times a cycle (ladder, close) and bulb B N + 1 (fetch arrivals, the close's
    arrival), so both would end lit. A second close pulse, taken off the close kick's snake and delayed ~120 gt more
    (a delay-1 snake), after every x-band has left home and long before any returns, toggles both once more (MEASURED:
    taken off the close itself it reached bulb B while the odd band was still home and lit bulb B's torch, so B
    missed the toggle). Bulb B's extra pulse reaches the store gate,
    which the input being off keeps locked."""
    m = c.marks
    bx, by, bz = m['xsm']
    for q in [(bx, by, bz + 1), (bx, by - 1, bz + 1)]:          # layout3's close repeater and its support
        for dct in (c.cells, c.net, c.meta):
            dct.pop(q, None)
    c.rep((bx, by, bz + 1), 'north', 'CLOSE')
    c.block((bx, by, bz + 2), 'CLOSE')                          # merge: the close line and the second pulse
    m['close_goal'] = ((bx, by, bz + 3), 'north')
    m['close2_goal'] = ((bx - 1, by, bz + 2), 'east')
    sb = m['sxb']
    c.rep((sb[0], sb[1], sb[2] - 1), 'south', 'CLOSE3')         # into bulb B from the north
    m['close3_goal'] = ((sb[0], sb[1], sb[2] - 2), 'south')
    L3.SNAKE['CLOSE2'] = (COMPACT['close2'] or (-18, -7, 12), COMPACT['close2_len'] or 7, COMPACT['close2_lines'] or 4)
    if COMPACT['close3_snake']:     # bulb B's pulse runs through a snake of its own after the second spit's, so the
        L3.SNAKE['CLOSE3'] = COMPACT['close3_snake']    # two are timed apart      # MEASURED window: even bands away ~13260..13440 (f8c.out)


def build_hand(n):
    CHAINS.clear()
    UPSTREAM.clear()
    L3.SNAKE['CLOSEK'] = (COMPACT['closek'] or (2, -7, 0), COMPACT['closek_len'] or 9, CLOSEK_LINES[0])
    c = Circuit(geomq.WEST)
    c.marks = {'N': n}
    L3.core(c, n)
    L3.xk_fanout(c)
    zb_ends(c)
    za_ends(c)
    # N = 8: the masters between the classes' ends (on the even side the odd lines ran ~40 gt longer)
    L3.LAD.update(x0=COMPACT['lad_x0'] or (3 if n <= 5 else -12), zt=ZD + 2, y=1)
    # hold master beside the spit master, so each class's spit and hold lines run alike (a master on one class's side
    # skews that class's hold against its spits by tens of gt)
    L3.XHM = COMPACT['xhm'] or ((7, 1, ZD + 9) if n <= 5 else (-8, 1, ZD + 12))     # even N: room for the parity merge at ZD+5..7
    (timer_split if COMPACT['ladder_split'] is not None else timer_east if COMPACT['ladder_e'] else L3.timer)(c, n)
    hx, hy, hz = L3.XHM
    for p in c.marks['dl']['TAPB']:
        for dct in (c.cells, c.net, c.meta):
            dct.pop(p, None)
        q = (p[0], p[1] - 1, p[2])
        if c.net.get(q) == 'support':
            for dct in (c.cells, c.net, c.meta):
                dct.pop(q, None)
    c.block((hx + 1, hy, hz), 'TAPB')
    c.marks['dl']['TAPB'] = run(c, (hx + 1, hy, hz + 6), 'north', 6, 'TAPB')
    c.marks['tB_end'] = (hx + 1, hy, hz)
    c.marks['tapb_goal'] = ((hx + 1, hy, hz + 7), 'north')
    if n % 2 == 0:                  # N = 8 holds need ~40 gt more on both taps: tap A along z too, both longer
        for p in c.marks['dl']['TAPA'] + c.marks['dl']['TAPB']:
            for q in (p, (p[0], p[1] - 1, p[2])):
                if c.net.get(q) in ('TAPA', 'TAPB', 'support'):
                    for dct in (c.cells, c.net, c.meta):
                        dct.pop(q, None)
        c.block((hx - 1, hy, hz), 'TAPA')
        c.marks['tA_end'] = (hx - 1, hy, hz)
        if COMPACT['taps_x']:       # both tap lines along x, level with the hold master: tap B (hold off, the later)
            # from the far side of the timer, tap A from the near side
            for q in ((hx - 1, hy, hz), (hx + 1, hy, hz)):
                for dct in (c.cells, c.net, c.meta):
                    dct.pop(q, None)
            c.block((hx + 1, hy, hz), 'TAPA'); c.block((hx - 1, hy, hz), 'TAPB')
            c.marks['tA_end'], c.marks['tB_end'] = (hx + 1, hy, hz), (hx - 1, hy, hz)
            k = COMPACT['taps_x']
            c.marks['dl']['TAPA'], c.marks['tapa_goal'] = fold(c, 'TAPA', (hx + 1, hy, hz), 1, k)
            c.marks['dl']['TAPB'], c.marks['tapb_goal'] = fold(c, 'TAPB', (hx - 1, hy, hz), -1, k)
        else:
            c.marks['dl']['TAPA'] = run(c, (hx - 1, hy, hz + 14), 'north', 14, 'TAPA')
            c.marks['tapa_goal'] = ((hx - 1, hy, hz + 15), 'north')
            c.marks['dl']['TAPB'] = run(c, (hx + 1, hy, hz + 14), 'north', 14, 'TAPB')
            c.marks['tapb_goal'] = ((hx + 1, hy, hz + 15), 'north')
    for net in ('XHPO', 'XSPO'):
        for p in [p for p in c.cells if c.net[p] == net]:
            for dct in (c.cells, c.net, c.meta):
                dct.pop(p, None)
        for q in [p for p in c.cells if c.net[p] == 'support' and (p[0], p[1] + 1, p[2]) not in c.cells]:
            for dct in (c.cells, c.net, c.meta):
                dct.pop(q, None)
        c.marks['dl'].pop(net)
        c.errors = [e for e in c.errors if not e.startswith(f'{net}: ')]     # those old lines may hit the machines
    x_ends(c)
    if n % 2 == 0:
        parity(c)
    towers(c)
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
    W = lambda p: (p[0] - 1, p[1], p[2])
    e, o = m['xs']['E'], m['xs']['O']
    nx = lambda g: R.add(g[0], R.H[g[1]])
    return [
        ('XKE', S(src, 'east'), e['kick_goal'], [src], [nx(e['kick_goal'])]),
        ('XKO', S(src, 'west'), o['kick_goal'], [src], [nx(o['kick_goal'])]),
        ('CLOSEK', S(cl, 'north'), ((m['fetch'][0] - 1, m['fetch'][1], m['fetch'][2]), 'east'), [cl], [m['fetch']]),
        ('CLOSE', S(cl, 'east'), m.get('close_goal', ((m['xsm'][0], ly, m['xsm'][2] + 2), 'north')), [cl],
         [nx(m['close_goal']) if 'close_goal' in m else (m['xsm'][0], ly, m['xsm'][2] + 1)]),
        ('STOREE', S(st, 'south'), m['storee_goal'], [st], [nx(m['storee_goal'])]),
        ('STOREO', S(st, 'west'), m['storeo_goal'], [st], [nx(m['storeo_goal'])]),
        ('KZB', S(st, 'east'), m['kzb_goal'], [st], [nx(m['kzb_goal'])]),
        ('ZARR', ((11, 5, 32 + DZ), 'south'), ((m['zb'][0], m['zb'][1], m['zb'][2] + 1), 'north'), [m['gz']], [m['zb']]),
        ('XARR', S(m['xarr_src'], 'east'), ((m['gs_in'][0] - 1, m['gs_in'][1], m['gs_in'][2]), 'east'),
         [m['xarr_src']], [m['gs_in']]),
        ('SX', S(m['sx_blk'], 'west'), (m['gx_in'], 'west'), [m['sx_blk']], [m['sxm']]),
        ('ZASE', S(reb, 'east'), m['zase_goal'], [reb], [nx(m['zase_goal'])]),
        ('ZASO', S(reb, 'north'), m['zaso_goal'], [reb], [nx(m['zaso_goal'])]),
    ] + ([
        ('TMR', S(reb, 'south'), ((m['tmr'][0], ly - 2, m['tmr'][2]), 'south'), [reb], [(m['tmr'][0], ly - 1, m['tmr'][2])]),
        ('TAPA', S(m['tmr'], 'west'), m['tapa_goal'], [m['tmr']], [nx(m['tapa_goal'])]),
        ('TAPB', S(m['tmr'], 'north'), m['tapb_goal'], [m['tmr']], [nx(m['tapb_goal'])]),
    ] if 'tmr_e' in m else [
        ('TMR', S(reb, 'south'), ((lx + 7, ly - 2, lz), 'south'), [reb], [(lx + 7, ly - 1, lz)]),
        ('TAPA', ((lx + 7, ly, lz + 1), 'south'), m.get('tapa_goal', ((hx - 5, hy, hz), "east")), [(lx + 7, ly, lz)],
         [nx(m['tapa_goal']) if 'tapa_goal' in m else (hx - 4, hy, hz)]),
        ('TAPB', ((lx + 8, ly, lz), 'east'), m['tapb_goal'], [(lx + 7, ly, lz)], [nx(m['tapb_goal'])]),
    ]) + [
        ('XSPE', S(xsm, 'east'), e['spit_goal'], [xsm], [nx(e['spit_goal'])]),
        ('XSPO', S(xsm, 'west'), o['spit_goal'], [xsm], [nx(o['spit_goal'])]),
        ('XHPE', S(xb, 'east'), e['hold_goal'], [xb], [nx(e['hold_goal'])]),
        ('XHPO', S(xb, 'south'), o['hold_goal'], [xb], [nx(o['hold_goal'])]),
    ] + ([('CLOSE2', S(L3.SNAKE_ENDS['CLOSEK'][2], 'west' if CLOSEK_LINES[0] % 2 == 0 else 'south'), m['close2_goal'],
            [L3.SNAKE_ENDS['CLOSEK'][2]],
            [nx(m['close2_goal'])]),
           ('CLOSE3', S(L3.SNAKE_ENDS['CLOSE2'][2], 'south'), m['close3_goal'], [L3.SNAKE_ENDS['CLOSE2'][2]],
            [nx(m['close3_goal'])])] if 'close2_goal' in m else [])


def feed_keepout(IL):
    """The cells of pairs_ctrlq's input feed (a repeater column north from under the lever cell IL, then a dust row
    east to the centre line at z IL-7, on supports one lower) and every cell beside them: no route may use them."""
    x0, y0, z0 = IL[0], IL[1] - 1, IL[2]
    xj = (geomq.X - 1) // 2
    feed = [(x0, y0, z0 + dz) for dz in range(-7, 0)] + [(x, y0, z0 - 7) for x in range(x0 + 1, xj + 2)] \
        + [(xj, y0, z0 - 8), (xj, y0, z0 - 9)]
    feed += [(x, y - 1, z) for x, y, z in feed]
    return {(x + dx, y + dy, z + dz) for x, y, z in feed for dx, dy, dz in R.NB6 + [(0, 0, 0)]}


_fresh = L3._fresh


def fresh(N):
    """Without the bottom routing row, routes come up level with the input feed: keep them off it."""
    c, bd = _fresh(N)
    if -7 not in L3.ROWS:
        bd.blocked |= {q for q in feed_keepout(c.marks['IL']) if q not in bd.cells}
    return c, bd


L3._fresh = fresh
L3.build_hand = build_hand
L3.nets = nets
L3.FIRST = ['CLOSEK', 'KZB', 'STOREE', 'XKE', 'XKO', 'XARR', 'XSPE', 'XSPO', 'XHPE', 'XHPO', 'TMR', 'TAPA', 'ZASE', 'ZASO']


TAILS = {'ZASE': 6, 'ZASO': 6, 'KZB': 2}        # repeaters after a route's last riser, for tuning delay
_route_via = L3.route_via


def route_via(bd, name, start, goal, a_s, a_e):
    if name in TAILS and name not in L3.SNAKE_ENDS:
        return R.route(bd, name, start, goal, allow_start=a_s, allow_end=a_e, rows=L3.ROWS, deep=-5, max_cost=800,
                       tail=TAILS[name])
    return _route_via(bd, name, start, goal, a_s, a_e)


L3.route_via = route_via


AFTER_TAPS = ('XSPE', 'XSPO', 'XHPE', 'XHPO')


def build(n, delays=None, verbose=False):
    """Delays on nets with taps go only on their repeaters after the taps (a stretched pulse would make each tower
    fire twice), and are copied to every upper pair."""
    d = dict(delays or {})
    after = {k: d.pop(k) for k in AFTER_TAPS if k in d}
    assert not d.get('ZASE') and not d.get('ZASO'), d
    d.pop('ZASE', None); d.pop('ZASO', None)
    c = L3.build(n, delays=d, verbose=verbose)
    bd = c.board
    for name, gt in after.items():
        if not gt:
            continue
        reps = [('rep', p) for p in c.marks['dl'][name]]
        R.set_delays(bd, reps, gt, maxd=L3.MAXD.get(name, 4))
        for p in c.marks['dl'][name]:
            st = bd.cells[p][0]
            c.cells[p] = st
            for L in range(1, PAIRS):
                q = UP(p, 4 * L)
                if q in c.cells and c.net.get(q, '').startswith(name):
                    c.cells[q] = st
    return c


if __name__ == '__main__':
    import checkq
    setup(int(sys.argv[1]), int(sys.argv[2]))
    c = build_hand(N)
    print('hand errors', c.errors[:10])
    pr = checkq.sweep(c)
    print('sweep problems', len(pr))
    for p in pr[:40]:
        print('  ', p)
