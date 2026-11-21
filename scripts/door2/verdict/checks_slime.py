"""Extra checks on the slime-carrier replay: every visible cell filled with quartz, push-list sizes, controls."""
import copy
from scripts.door2.verdict.pistonsim import *
from scripts.door2.verdict import replay_slime as R


def strict_open(w):
    bad = []
    for x in range(-3, 6):
        for y in range(-3, 6):
            for z in range(-HALL, HALL + 1):
                c = (x, y, z)
                b = w.get(c)
                if in_I(c) and b is not None:
                    bad.append(('interior', c, b))
                if in_V(c) and (b is None or b[0] != 'Q'):
                    bad.append(('visible', c, b))
    return bad


def replay(sched):
    w = World(R.build())
    try:
        run(w, sched)
    except Fail as e:
        return None, str(e)
    return w, None


# 1. main replay, strict open state, push-list sizes
w = World(R.build())
orig = w.resolve
sizes = {}
def spy(ppos, facing, extending):
    r = orig(ppos, facing, extending)
    b = w.get(ppos)
    sizes[(w.t, b[1] if b else ppos, 'ext' if extending else 'pull')] = None if r is None else len(r[0])
    return r
w.resolve = spy
run(w, R.SCHED)
print('strict open-state problems:', strict_open(w))
print('largest structures:', sorted(((v, str(k)) for k, v in sizes.items() if v), reverse=True)[:4])
o, s, vis = metrics(w)
print('opening(S)', o, 'seamless(S)', s)

# 2. controls: drop one event, expect failure or a worse result
for t, ev in [(3, ('0t', 'T3')), (0, ('0t', 'Z')), (0, ('0t', 'P2')), (3, ('0t', 'Wp')),
              (3, ('0t', 'AX')), (3, ('0t', 'CF')), (0, ('0t', 'Y'))]:
    sc = copy.deepcopy(R.SCHED)
    sc[t].remove(ev)
    w2, err = replay(sc)
    if err:
        print(f'control without {ev} at t{t}: replay fails: {err}')
    else:
        o2, s2, _ = metrics(w2)
        print(f'control without {ev} at t{t}: opening {o2}, seamless {s2}, open-state problems {len(strict_open(w2))}')

# 3. order sensitivity at t3: move T3 first / last
for label, order in [('T3 first', ['T3']), ('Y before ZP', None)]:
    sc = copy.deepcopy(R.SCHED)
    if label == 'T3 first':
        sc[3].remove(('0t', 'T3')); sc[3].insert(0, ('0t', 'T3'))
    else:
        sc[3].remove(('0t', 'Y')); sc[3].insert(sc[3].index(('0t', 'ZP')), ('0t', 'Y'))
    w3, err = replay(sc)
    print(f'order variant "{label}":', err or f'ok, strict problems {len(strict_open(w3))}')
