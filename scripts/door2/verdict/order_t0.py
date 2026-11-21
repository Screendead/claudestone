"""Order dependences of the slime-carrier replay.
(a) swap each adjacent pair; (b) move one event to just after a named later event (targeted pairs)."""
import copy, io, contextlib
from scripts.door2.verdict.pistonsim import *
from scripts.door2.verdict import replay_slime as R
with contextlib.redirect_stdout(io.StringIO()):
    from scripts.door2.verdict.checks_slime import strict_open

def attempt(sched):
    w = World(R.build())
    try:
        run(w, sched)
    except Fail as e:
        return 'FAIL: ' + str(e)
    o, s, _ = metrics(w)
    p = strict_open(w)
    return 'ok' if not p and o == 3 and s == 3 else f'degraded: opening {o}, seamless {s}, {len(p)} open-state problems'

for t in (0, 3):
    evs = R.SCHED[t]
    print(f'--- t{t}, adjacent swaps')
    for i in range(len(evs) - 1):
        sc = copy.deepcopy(R.SCHED)
        sc[t][i], sc[t][i + 1] = sc[t][i + 1], sc[t][i]
        print(f'  {evs[i + 1][1]} before {evs[i][1]}: {attempt(sc)}')

print('--- targeted: move X to just after Y (same tick)')
for t, x, y in [(0, 'P_L', 'A'), (0, 'P_BL', 'A'), (0, 'P_BR', 'Z'), (0, 'P_TM', 'P2'),
                (0, 'A', 'Y'), (0, 'K0', 'Y'), (0, 'Y', 'Z'), (0, 'Z', 'P2'), (0, 'K0', 'XP'),
                (3, 'Wp', 'T3'), (3, 'AX', 'ZP'), (3, 'ZP', 'Y'), (3, 'T3', 'K0'), (3, 'FL1', 'CF'), (3, 'CF', 'K0')]:
    sc = copy.deepcopy(R.SCHED)
    lst = sc[t]
    ex = [e for e in lst if e[1] == x][0]
    lst.remove(ex)
    lst.insert([e[1] for e in lst].index(y) + 1, ex)
    print(f'  {x} after {y} (t{t}): {attempt(sc)}')
