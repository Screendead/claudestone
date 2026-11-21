"""QUART rework of gen/band_pairs.py (PROGRESS.md "QUART rework"): every x-band on side A, as door16_band_kick2's
compact self-reversing band (rows b, t only; even pairs slime, odd pairs honey), z-bands unchanged.

Original docstring follows.
Generate two adjacent row pairs that each store through their own z-stack (PROGRESS.md "Stacking the z-bands").

Same machines as gen/band_open.py (door16_band_open), one half. Adjacent row pairs' z-bands can't share x: a z-band
takes rows b..t+1 (+ watched t+2) at x = slot..slot+4, and same-side pairs sit 2 rows apart. So pairs alternate
between two slots: even pairs as in door16_band_open (x-band home x1..x2, slot x3, z-bands x3..x7); odd pairs pushed
OUT into the wall (x-band home x-7..x-6, slot x-5, z-bands x-5..x-1), leaving x0 (the even x-bands' home obsidian and
kick cells) and a 1-cell gap to the even x-bands' west-half slime at x1.

Band 0 (rows 2-3, side A, odd: home x-7) idle; band 1 (rows 4-5, side B, even: home x1) and band 2 (rows 6-7, side A,
odd: home x-7) each have a ZA (side A, holds the stack) and a ZB (side B, stores into it). Logical x is shifted by
SHIFT in the spec so that the obsidian at x-8 lands on x0.

python band_pairs.py OUT.yaml [N] [--name NAME] [--check]   (--check: geometry lint at this N, no output file)
"""
import sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith('--')]
N = int(args[1]) if len(args) > 1 else 3
NAME = sys.argv[sys.argv.index('--name') + 1] if '--name' in sys.argv else 'door16_quart_pairs'

HA = 9 + N            # the stack's front must stay out of k5, which the x-bands now use
HB = 7
ZD = HA + 3
Z = ZD + HB + 3
Y = 12
EVEN_HOME = -1                               # even slot x3, first door column x13 at N = 8, as in door16_full
ODD_HOME = EVEN_HOME - 11                    # even x-band (x-2..x+3) clear of the odd z-corridor (x+4..x+8)
BANDS = {1: ('A', 4, EVEN_HOME), 2: ('A', 6, ODD_HOME)}   # side, bottom row, x-band home (west half x)
ACTIVE = (1, 2)
GLUE = {1: 'slime_block', 2: 'honey_block'}
OBS_K4 = False
SHIFT = 2 - ODD_HOME                       # odd home obsidian (x-9) -> spec x0
D0 = EVEN_HOME + 4 + max(2 + N, 6)       # past the queue (slot..slot+1+N) and the even z-corridor (slot..slot+4) + gap
XMAX = D0 + N + 3                           # one half; quartz beyond D0+N stands for the east half's columns


def slot(n):
    return BANDS[n][2] + 4


def rows(n):
    return (BANDS[n][1], BANDS[n][1] + 1)


def zk(side, k):
    return ZD - k if side == 'A' else ZD + k


def glue_of(n):
    return GLUE.get(n, 'slime_block' if BANDS[n][1] % 4 == 0 else 'honey_block')


def xband_halves(n):
    """door16_band_kick2's band: (cells, halves) with halves 'w', 'e' or 'fixed'."""
    side, b, xw = BANDS[n]
    g = glue_of(n)
    t, xe, xp = b + 1, xw + 1, xw + 3
    k = lambda i: zk('A', i)
    west = {
        (xw - 1, t, k(2)): 'observer[facing=west]', (xw, t, k(2)): 'sticky_piston[facing=east]',
        (xw - 1, t, k(3)): g, (xw, t, k(3)): g, (xw, t, k(4)): g,
        **{(x, t, k(5)): g for x in range(xw, xp + 1)},
        (xp, t, k(4)): 'observer[facing=north]',
    }
    east = {
        (xe, t, k(2)): g, (xe + 1, t, k(2)): g, (xp, t, k(2)): g,
        (xe, t, k(3)): 'sticky_piston[facing=west]', (xe + 1, t, k(3)): 'observer[facing=east]',
        (xp, t, k(3)): 'note_block',
        (xe + 1, t, k(1)): g, (xp, t, k(1)): g, (xp, b, k(1)): g,
        (xe + 1, t, ZD): 'observer[facing=west]',
        (xp, t, ZD): 'sticky_piston[facing=east]', (xp, b, ZD): 'sticky_piston[facing=east]',
    }
    # home stop: west of G at (xw-1, t, k3) (stage 0-2), or west of the k4 glue (OBS_K4: frees (xw-2, t, k3) for an
    # immovable comparator feeding the kick hopper from the north)
    fixed = {(xw - 1, t, k(4)) if OBS_K4 else (xw - 2, t, k(3)): 'obsidian'}
    cells = {**west, **east, **fixed}
    halves = {**{p: 'w' for p in west}, **{p: 'e' for p in east}, **{p: 'fixed' for p in fixed}}
    return cells, halves


def xband(n):
    return xband_halves(n)[0]


ZREL = {  # (flight half, plane k, row): block; 'fwd' toward the door, 'back' away from it, 'away' = +x (cross)
    ('w', 3, 't'): 'observer[facing=away]', ('w', 2, 't'): 'slime_block', ('w', 1, 't'): 'sticky_piston[facing=fwd]',
    ('w', 2, 't1'): 'slime_block', ('w', 3, 't1'): 'slime_block', ('w', 4, 't1'): 'slime_block',
    ('e', 4, 't1'): 'observer[facing=up]',
    ('e', 2, 't'): 'sticky_piston[facing=back]', ('e', 1, 't'): 'slime_block', ('e', 1, 'b'): 'slime_block',
    ('e', 1, 't1'): 'observer[facing=up]', ('e', 0, 't'): 'sticky_piston[facing=fwd]',
    ('e', 0, 'b'): 'sticky_piston[facing=fwd]', ('e', 2, 'b'): 'slime_block', ('e', 3, 'b'): 'slime_block',
    ('e', 4, 'b'): 'slime_block', ('e', 3, 't'): 'observer[facing=away]', ('e', 4, 't'): 'note_block',
}


def zband(n, side):
    """Rotated x-band at the pair's slot: plane k -> x = slot + k, flight along z toward the door plane."""
    b = BANDS[n][1]
    rowy = {'b': b, 't': b + 1, 't1': b + 2}
    s = slot(n)
    h = HA if side == 'A' else HB
    sgn = -1 if side == 'A' else 1
    ze = ZD + sgn * h
    zf = {'e': ze, 'w': ze + sgn, 'w-1': ze + 2 * sgn}
    fwd, back = ('south', 'north') if side == 'A' else ('north', 'south')
    cells, halves = {}, {}
    for (f, k, r), blk in ZREL.items():
        blk = blk.replace('=fwd', f'={fwd}').replace('=back', f'={back}').replace('=away', '=east')
        p = (s + k, rowy[r], zf[f])
        cells[p] = blk
        halves[p] = 'w' if (f, k, r) == ('e', 4, 't1') else f    # W rides the west half
    cells[(s + 2, b + 1, zf['w-1'])] = 'obsidian'
    halves[(s + 2, b + 1, zf['w-1'])] = 'fixed'
    marks = {
        'kick': (s + 1, b + 1, zf['w-1']), 'spit': (s + 1, b + 3, ze),
        'slot': (s, b, ze - sgn), 'P': (s, b, ze), 'behind': (s, b, ze + sgn), 'sgn': sgn,
    }
    return cells, halves, marks


grid, inputs, Z_HALVES, MARKS = {}, {}, {}, {}
for n in BANDS:
    grid.update(xband(n))
for x in range(D0, XMAX):
    for n in BANDS:
        for y in rows(n):
            grid[(x, y, ZD)] = 'quartz_block'
for n in ACTIVE:
    side, b, home = BANDS[n]
    s, t = slot(n), b + 1
    for y in rows(n):
        grid[(s, y, ZD)] = 'quartz_block'                       # the x-band's spacer, as the close leaves it
    za, ha, ma = zband(n, 'A')
    zb, hb, mb = zband(n, 'B')
    grid.update(za)
    grid.update(zb)
    Z_HALVES[(n, 'A')], Z_HALVES[(n, 'B')] = ha, hb
    MARKS[(n, 'A')], MARKS[(n, 'B')] = ma, mb
    for y in rows(n):
        grid[(s, y, ma['behind'][2])] = 'obsidian'               # the store chain ends immovable
        grid[(s, y, mb['slot'][2])] = 'quartz_block'             # ZB's permanent spacer
        grid[(s, y, ma['slot'][2])] = 'quartz_block'             # ZA's permanent spacer
    inputs[(home - 2, t, zk('A', 2))] = f'kick{n}'          # the cell O watches
    inputs[mb['kick']] = f'zb{n}'
    inputs[ma['kick']] = f'za{n}'


def spit_cell(n, which):
    side, b, home = BANDS[n]
    return {'x': (home + 1, b + 1, ZD), 'a': MARKS[(n, 'A')]['spit'], 'b': MARKS[(n, 'B')]['spit']}[which]


def sx(p):
    return (p[0] + SHIFT, p[1], p[2])


# --- geometry lint (COMPUTED): overlaps and slime contacts between different machines, at home and in lockstep -------
def machines():
    """name -> {cell: (block, half)} for every machine at home; halves: 'w'/'e' move, 'fixed' never moves."""
    out = {}
    for n in BANDS:
        cells, halves = xband_halves(n)
        out[f'x{n}'] = {p: (blk, halves[p]) for p, blk in cells.items()}
    for (n, side), hv in Z_HALVES.items():
        out[f'z{n}{side}'] = {p: (grid[p], hv[p]) for p in hv}
    return out


def static_items():
    """Blocks that only move when pushed or pulled: quartz (door, spacers, stacks), obsidian."""
    used = set().union(*[set(m) for m in machines().values()])
    return {p: b for p, b in grid.items() if p not in used}


def moved(m, de, dw, axis):
    out = {}
    for p, (blk, h) in m.items():
        d = {'e': de, 'w': dw}.get(h, 0)
        q = list(p)
        q[axis] += d
        out[tuple(q)] = blk
    return out


NB = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


def contacts(mov, still):
    """Overlaps, and moving slime face-adjacent to any block of the other machine (the next move would drag it).
    Still slime beside a moving non-sticky block is harmless (only sticky blocks pull their neighbours)."""
    bad = [('overlap', p) for p in mov if p in still]
    sticky = ('slime_block', 'honey_block')
    for p, blk in mov.items():
        if blk not in sticky:
            continue
        for d in NB:
            q = (p[0] + d[0], p[1] + d[1], p[2] + d[2])
            if q in still and {blk, still[q]} != set(sticky) and not still[q].startswith('obsidian'):
                bad.append(('sticky', p, q, still[q]))
    return bad


def lint():
    ms = machines()
    problems = []
    names = sorted(ms)
    home = {k: moved(v, 0, 0, 0) for k, v in ms.items()}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for c in [c for c in contacts(home[a], home[b]) if c[0] == 'overlap']:
                problems.append(('home', a, b, c))
    # each machine moving alone (others at home), then every ZB together and every ZA together (same geometry, same
    # step count, so lockstep keeps them level); halves: level, or the leading half one ahead
    # farthest e-half displacement: x-band P parks at x(D0+N-3); ZB's P stops 4 short of ZA's P (spacer, block,
    # ZB spacer between); ZA's P stops on k2A
    travel = {**{f'x{n}': (0, 1, D0 + N - 6 - BANDS[n][2]) for n in BANDS},
              **{f'z{n}B': (2, -1, HB + HA - 4) for n in ACTIVE}, **{f'z{n}A': (2, 1, HA - 2) for n in ACTIVE}}
    groups = [[k] for k in names] + [[f'z{n}B' for n in ACTIVE], [f'z{n}A' for n in ACTIVE]]
    for movers in groups:
        axis, sgn, dist = travel[movers[0]]
        for d in range(0, dist + 1):
            for lag in ((0, 1) if d < dist else (0,)):
                cur = {k: (moved(ms[k], sgn * (d + lag), sgn * d, axis) if k in movers else home[k]) for k in names}
                for a in movers:
                    for b in names:
                        if b != a:
                            for c in contacts(cur[a], cur[b]):
                                problems.append(('+'.join(movers), d, lag, a, b, c))
    return problems


# --- tests -----------------------------------------------------------------------------------------------------------
GLYPHS = iter('ABCDEFGHIJKLMNOPRSTUVWYZabcdefghijklmnopqrstuvwyz0123456789')
state_glyph = {blk: next(GLYPHS) for blk in sorted(set(grid.values()))}
input_glyph = {name: next(GLYPHS) for name in sorted(set(inputs.values()))}
W = XMAX + SHIFT


def layers():
    out = []
    for y in range(Y):
        rs = []
        for z in range(Z):
            row = ''
            for x in range(W):
                p = (x - SHIFT, y, z)
                row += input_glyph[inputs[p]] if p in inputs else state_glyph[grid[p]] if p in grid else '.'
            rs.append(row)
        out.append(f"  {y}: |\n" + ''.join(f"    {r}\n" for r in rs))
    return ''.join(out)


def palette():
    s = "  '.': air\n"
    for blk, g in state_glyph.items():
        s += f"  {g}: '{blk}'\n" if '[' in blk else f"  {g}: {blk}\n"
    for name, g in input_glyph.items():
        s += f"  {g}: {{input: {name}}}\n"
    return s


def checks(cells):
    items = [f"if block ~{x + SHIFT} ~{y} ~{z} {b}" for (x, y, z), b in sorted(cells.items())]
    return ''.join(f"  - check: '{' '.join(items[i:i + 12])}'\n" for i in range(0, len(items), 12))


def setblocks(cells, blk):
    return ''.join(f"  - run: 'setblock ~{x + SHIFT} ~{y} ~{z} {blk}'\n" for x, y, z in cells)


def spit(ns, which):
    cells = [spit_cell(n, which) for n in ns]
    return setblocks(cells, 'stone') + setblocks(cells, 'air')


def pulse(names):
    return ("  - drive: {" + ', '.join(f'{m}: 1' for m in names) + "}\n  - wait: 2\n"
            + "  - drive: {" + ', '.join(f'{m}: 0' for m in names) + "}\n")


def store(ns):
    return spit(ns, 'b') + "  - wait: 6\n" + pulse([f'zb{n}' for n in ns]) + f"  - wait: {2 * 10 * (HB + HA) + 40}\n"


def fetch_steps(n, k):
    return D0 + k - (BANDS[n][2] + 3) - 1


def fetch(ns, k):
    return pulse([f'kick{n}' for n in ns]) + f"  - wait: {max(20 * fetch_steps(n, k) + 60 for n in ns)}\n"


def open_steps(ns):
    return store(ns) + ''.join(fetch(ns, k) + store(ns) for k in range(N))


def retrieve(ns):
    """As in door16_band_open: ZA spits the stack toward the door, the x-band spits each arrival into the queue; P held
    out for the last one, so ZA's spacer stops on its head and ZA goes home with it."""
    s = spit(ns, 'a') + "  - wait: 6\n" + pulse([f'za{n}' for n in ns]) + "  - wait: 54\n"   # one more ZA step than band_pairs (HA + 1)
    for _ in range(N):
        s += spit(ns, 'x') + "  - wait: 10\n"
    hold = [(BANDS[n][2] + 3, y, ZD + 1) for n in ns for y in rows(n)]   # side B, inside the wall, beside each P
    s += setblocks(hold, 'redstone_block') + "  - wait: 40\n" + setblocks(hold, 'air')
    return s + f"  - wait: {20 * HA + 60}\n"


def line(n, fill):
    """Pair n's slot line from behind ZA's P to behind ZB's P, door plane excluded; fill = z's holding quartz."""
    ma, mb, s = MARKS[(n, 'A')], MARKS[(n, 'B')], slot(n)
    fixed = {ma['behind'][2]: 'obsidian', ma['P'][2]: 'sticky_piston[facing=south,extended=false]',
             mb['P'][2]: 'sticky_piston[facing=north,extended=false]', mb['behind'][2]: 'air'}
    return {(s, y, z): fixed.get(z, 'quartz_block' if z in fill else 'air')
            for y in rows(n) for z in range(ma['behind'][2], mb['behind'][2] + 1) if z != ZD}


def door_rows(n, cells):
    return {(x, y, ZD): b for x, b in cells.items() for y in rows(n)}


def open_checks(n):
    ma, mb = MARKS[(n, 'A')], MARKS[(n, 'B')]
    rowsx = {**{x: 'air' for x in range(slot(n), D0 + N)}, **{x: 'quartz_block' for x in range(D0 + N, XMAX)}}
    front = ma['slot'][2] + N + 2
    return checks(door_rows(n, rowsx)) + checks(line(n, set(range(ma['slot'][2], front)) | {mb['slot'][2]}))


def queue_checks(n):
    s, ma, mb = slot(n), MARKS[(n, 'A')], MARKS[(n, 'B')]
    rowsx = {**{x: 'air' for x in range(s, D0 + N)}, **{x: 'quartz_block' for x in range(D0 + N, XMAX)},
             s: 'quartz_block', **{x: 'quartz_block' for x in range(s + 2, s + 2 + N)}}
    return checks(door_rows(n, rowsx)) + checks(line(n, {ma['slot'][2], mb['slot'][2]}))


def still(ns):
    """Every block that must be where it started: everything but the moving pairs' slot lines and door rows."""
    return {p: b for p, b in grid.items()
            if not any((p[0] == slot(n) or p[2] == ZD) and p[1] in rows(n) for n in ns)}


def test(ns):
    return (open_steps(ns) + ''.join(open_checks(n) for n in ns) + checks(still(ns))
            + retrieve(ns) + ''.join(queue_checks(n) for n in ns) + checks(still(ns)))


tests = [
    (f"rows 4-5 (slime x-band, slot x{slot(1)}) store {N} columns and rebuild their queue alone, rows 6-7 never move", test([1])),
    (f"rows 6-7 (honey x-band, slot x{slot(2)}) store {N} columns and rebuild their queue alone, rows 4-5 never move", test([2])),
    (f"both pairs in lockstep, same-tick kicks and spits", test([1, 2])),
]

if __name__ == '__main__':
    probs = lint()
    print('geometry lint at N =', N, ':', len(probs), 'problems')
    for p in probs[:20]:
        print('  ', p)
    if '--check' in sys.argv:
        sys.exit(0)
    text = f"""name: {NAME}
description: "Two adjacent row pairs of the in-plane 16x16 door for a QUART-seamless build (rows 4-5 and 6-7, one half, {N} columns each): every x-band runs on the same side of the door plane (side A), so the other side's hallway plane and walls never see a machine. The x-bands are door16_band_kick2's self-reversing bands, each inside its own two rows: rows 4-5 slime, rows 6-7 honey, so their glue beside the door plane never sticks across the pair boundary. Storage is door16_band_pairs': per pair a ZB (home deep on side B, crossing the door plane only at its slot, inside the wall) pushes [spacer, slot block] into a stack on side A, and a ZA pushes the stack back for the queue. ZA's home is one plane deeper than in door16_band_pairs (HA = 9 + N), because the x-bands now use a fifth plane and the stack's front must stay out of it. Slots alternate between pairs: even pair slot x{slot(1)} (x-band x{BANDS[1][2] - 2}..x{BANDS[1][2] + 3}), odd pair slot x{slot(2)} pushed out into the wall (x-band x{BANDS[2][2] - 2}..x{BANDS[2][2] + 3}); the first door column is x{D0}, past the even z-corridor. Spec x = logical x + {SHIFT}. Stand-ins for the controller: the kicks (a block in the cell O watches), the home spits (a block flicked in the cell the observer behind the upper door piston watches), and the held door pistons (redstone blocks beside them on side B, inside the wall). Lockstep is proven; arbitrary timing is not (an odd x-band must not fly while the even ZB crosses its rows)."
traits: [piston_based, entityless]
update_pass: strict
palette:
""" + palette() + "layers:\n" + layers() + "tests:\n" + ''.join(
        f"- name: {name}\n  steps:\n{steps}" for name, steps in tests)
    out = Path(args[0]) if args else Path(f'{NAME}.redstone.yaml')
    out.write_text(text)
    print(out, 'W', W, 'Y', Y, 'Z', Z, 'ZD', ZD, 'D0', D0, 'SHIFT', SHIFT)
