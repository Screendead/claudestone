"""Replay design B (door_3x3_design.md §3.2) in pistonsim. Expected: open 3, seamless 6 (motion start)."""
from scripts.door2.verdict.pistonsim import *

DOOR = {'TL': (0, 2), 'TM': (1, 2), 'TR': (2, 2), 'L': (0, 1), 'C': (1, 1), 'R': (2, 1),
        'BL': (0, 0), 'BM': (1, 0), 'BR': (2, 0)}
F = {'D': 'D', 'U': 'U', 'E': 'E', 'W': 'W'}


def P(name, facing, held=False):
    return ('P', name, facing, True, held)


def build():
    b = walls()
    for n, (x, y) in DOOR.items():
        b[(x, y, 0)] = ('Q', n)
    pist = [('P1', (0, 4), 'D', 1), ('P2', (1, 4), 'D', 1), ('P3', (2, 4), 'D', 1),
            ('P4', (-2, 1), 'E', 1), ('P5', (4, 1), 'W', 1), ('P6', (-2, 0), 'E', 1),
            ('P7', (2, -2), 'U', 1), ('Q', (3, 0), 'W', 0), ('S', (1, -1), 'U', 0),
            ('P8', (3, -2), 'U', 1), ('P9', (4, 0), 'W', 0), ('V', (-1, -1), 'E', 1),
            ('T', (1, -2), 'U', 0), ('P10', (-1, -3), 'U', 1), ('P11', (-2, -1), 'E', 0),
            ('P12', (0, -3), 'U', 0)]
    for n, (x, y), f, held in pist:
        b[(x, y, 0)] = P(n, f, bool(held))
        if held:
            b[add((x, y, 0), DIRS[f])] = ('HEAD', n, f)
    b[(0, -2, 0)] = ('Q', 'qq')
    b[(-1, 2, 0)] = ('Q', 'static_l')
    b[(3, 2, 0)] = ('Q', 'static_r')
    return b


SCHED = {
    0: [('ret', 'P1'), ('ret', 'P2'), ('ret', 'P3'), ('ret', 'P4'), ('ret', 'P5'), ('ret', 'P6'),
        ('ret', 'P7'), ('0t', 'Q'), ('0t', 'S')],
    3: [('ret', 'P8'), ('0t', 'P9'), ('ret', 'V'), ('0t', 'T')],
    6: [('ret', 'P10'), ('0t', 'P11'), ('0t', 'P12')],
}

if __name__ == '__main__':
    blocks = build()
    print('closed-state problems:', check_closed(blocks, DOOR))
    w = World(blocks)
    res = run(w, SCHED)
    for k, v in sorted(res.items()):
        print('event', k, v)
    print('open-state problems:', check_open(w))
    o, s, vis = metrics(w)
    print(f'design B: opening(S)={o} seamless(S)={s}')
    for t, why, a, b in vis:
        if t >= 3:
            print('  visible move', t, why, a, '->', b)
