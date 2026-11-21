"""Candidate 'slime carrier' 3x3 (this verdict's counter-schedule attempt), replayed in pistonsim.

Idea: C is never pulled by a piston in a slot. A slime block N is walked into the bottom-middle
frame cell M at t0 (two spits via the corner (0,0)), then pulled down into slot E by P2 at E2,
dragging C into M. At t3 a second slime S2 in slot (2,-1) is pulled down; it back-drags BM into
(2,-1) and branches into N, which drags C into E and pushes P2 down out of the way. The
slot-transit and drag side effects (walls, floors, BL, the Z piston's slot) are repaired at t3.
"""
import sys
from scripts.door2.verdict.pistonsim import *

DOOR = {'TL': (0, 2), 'TM': (1, 2), 'TR': (2, 2), 'L': (0, 1), 'C': (1, 1), 'R': (2, 1),
        'BL': (0, 0), 'BM': (1, 0), 'BR': (2, 0)}

# name, base, facing, held (extended in the closed state, head at +1)
PISTONS = [
    ('P_TL', (0, 4, 0), 'D', 1), ('P_TM', (1, 4, 0), 'D', 1), ('P_TR', (2, 4, 0), 'D', 1),
    ('P_L', (-2, 1, 0), 'E', 1), ('P_R', (4, 1, 0), 'W', 1), ('P_BR', (4, 0, 0), 'W', 1),
    ('P_BL', (0, -2, 0), 'U', 1),
    ('A', (-2, 0, 0), 'E', 0),      # spits N from slot (-1,0) into corner (0,0)
    ('Z', (-2, -1, 0), 'E', 0),     # carried to (-1,0) by K0 then Y, fires there (H2)
    ('K0', (-3, -1, 0), 'E', 0),
    ('Y', (-1, -2, 0), 'U', 0),
    ('P2', (1, -2, 0), 'U', 0),     # pulls N from M into E at t0 (drags C)
    ('T3', (2, -3, 0), 'U', 0),     # pulls S2 at t3 (drags BM, N, C; pushes P2, BL, P_BL)
    ('XP', (-2, -3, 0), 'U', 0),    # loads spare X into (-2,-1) at t0
    ('Wp', (-2, 0, 1), 'E', 0), ('Wm', (-2, 0, -1), 'E', 0),   # wall restore at t3
    ('PLX', (-4, 1, 0), 'E', 0), ('AX', (-2, 2, 0), 'D', 0), ('ZP', (-3, 0, 0), 'E', 0),
    ('FL1', (-3, -1, 1), 'E', 0), ('FR1', (4, -1, 1), 'W', 0),
    ('FL2', (-2, -1, -1), 'E', 0), ('FR2', (4, -1, -1), 'W', 0),
    ('CF', (-1, -1, 2), 'N', 0),
]
EXTRA = {
    (-1, 0, 0): ('SL', 'N'), (2, -1, 0): ('SL', 'S2'),
    (-2, -2, 0): ('Q', 'X'),
    (-2, -1, 1): ('Q', 'spX'), (-1, -1, 1): ('Q', 'spY'), (3, -1, 1): ('Q', 'spR1'),
    (-1, -1, -1): ('Q', 'spL2'), (3, -1, -1): ('Q', 'spR2'),
    (-1, 2, 0): ('Q', 'static_l'), (3, 2, 0): ('Q', 'static_r'),
}

SCHED = {
    0: [('ret', 'P_TL'), ('ret', 'P_TM'), ('ret', 'P_TR'), ('ret', 'P_L'), ('ret', 'P_R'),
        ('ret', 'P_BR'), ('ret', 'P_BL'),
        ('0t', 'A'), ('0t', 'K0'), ('0t', 'Y'), ('0t', 'Z'), ('0t', 'P2'), ('0t', 'XP')],
    3: [('0t', 'Wp'), ('0t', 'Wm'), ('0t', 'PLX'), ('0t', 'AX'), ('0t', 'ZP'),
        ('0t', 'T3'),
        ('0t', 'FL1'), ('0t', 'FR1'), ('0t', 'FL2'), ('0t', 'FR2'),
        ('0t', 'CF'), ('0t', 'K0'), ('0t', 'Y')],
}


def build():
    b = walls()
    for n, (x, y) in DOOR.items():
        b[(x, y, 0)] = ('Q', n)
    for n, pos, f, held in PISTONS:
        assert pos not in b, (n, pos, b.get(pos))
        b[pos] = ('P', n, f, True, bool(held))
        if held:
            h = add(pos, DIRS[f])
            assert h not in b, (n, h)
            b[h] = ('HEAD', n, f)
    for c, v in EXTRA.items():
        assert c not in b, (c, b[c])
        b[c] = v
    return b


def show(w, z=0, xs=range(-4, 6), ys=range(4, -5, -1)):
    for y in ys:
        row = []
        for x in xs:
            b = w.get((x, y, z))
            if b is None:
                s = '.'
            elif b[0] == 'MOV':
                s = '~' + (b[1][1] if b[1][0] != 'HEAD' else 'h')
            elif b[0] == 'HEAD':
                s = 'hh'
            else:
                s = b[1] if b[0] != 'OBS' else '##'
            row.append(f'{s[:6]:>7}')
        print(f'y={y:>2} ' + ''.join(row))


if __name__ == '__main__':
    blocks = build()
    print('closed-state problems:', check_closed(blocks, DOOR))
    hidden_bad = [(c, v) for c, v in blocks.items()
                  if not in_frame(c) and (in_V(c) and c[2] != 0) and v[0] != 'Q']
    print('closed-state visible non-quartz (z!=0):', hidden_bad)
    w = World(blocks)
    try:
        res = run(w, SCHED)
    except Fail as e:
        print('FAIL:', e)
        print('--- z=0 at failure')
        show(w)
        sys.exit(1)
    for k, v in sorted(res.items()):
        print('event', k, v)
    for z in (0, 1, -1):
        print(f'--- open state, z={z}')
        show(w, z)
    print('open-state problems:', check_open(w))
    o, s, vis = metrics(w)
    print(f'slime carrier: opening(S)={o} seamless(S)={s}')
    ticks = sorted({t for t, *_ in vis})
    print('ticks with visible movement:', ticks)
    for t, why, a, b in vis:
        print('  visible move', t, why, a, '->', b)
