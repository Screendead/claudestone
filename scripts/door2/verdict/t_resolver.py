"""Unit checks of pistonsim.resolve against expectations read from PistonStructureResolver.java (26.3)."""
from scripts.door2.verdict.pistonsim import *

def mk(blocks, piston, facing, extended=False):
    b = dict(blocks)
    b[piston] = ('P', 'T', facing, True, extended)
    return World(b)

def names(w, r):
    return None if r is None else sorted(w.get(p)[1] if w.get(p)[0] != 'P' else 'P:' + w.get(p)[1] for p in r[0])

cases = []
# 1 back-drag stops at the first non-sticky block (99-113): pull slime with quartz, quartz behind it
w = mk({(0, 2, 0): ('SL', 's'), (0, 3, 0): ('Q', 'a'), (0, 4, 0): ('Q', 'b')}, (0, 0, 0), 'U')
cases.append(('back-drag stops after first non-sticky', names(w, w.resolve((0, 0, 0), 'U', False)), ['a', 's']))
# 2 side branch drags a retracted piston (184 + isPushable), skips an extended one and a moving one
w = mk({(0, 2, 0): ('SL', 's'), (1, 2, 0): ('P', 'r', 'E', True, False), (-1, 2, 0): ('P', 'x', 'W', True, True),
        (0, 2, 1): ('MOV', ('Q', 'm'), 'U', False, False, 0)}, (0, 0, 0), 'U')
cases.append(('branch takes retracted piston, skips extended and moving', names(w, w.resolve((0, 0, 0), 'U', False)), ['P:r', 's']))
# 3 slime and honey do not stick (68-74)
w = mk({(0, 2, 0): ('SL', 's'), (1, 2, 0): ('HO', 'h'), (-1, 2, 0): ('SL', 's2')}, (0, 0, 0), 'U')
cases.append(('slime-honey no stick, slime-slime sticks', names(w, w.resolve((0, 0, 0), 'U', False)), ['s', 's2']))
# 4 limit 12 counts branched blocks (95, 110, 154): push slime carrying 12 quartz sideways -> fail; 11 -> ok
def limit(n):
    # five slimes in a row along z (all branch neighbours of each other), n quartz on their x sides
    b = {(0, 1, z): ('SL', f's{z}') for z in range(-1, 4)}
    cells = [(x, 1, z) for x in (1, -1) for z in range(-1, 4)]
    for c in cells[:n]:
        b[c] = ('Q', f'q{c}')
    w = mk(b, (0, 0, 0), 'U')
    return w.resolve((0, 0, 0), 'U', True)
cases.append(('5 slime + 7 quartz = 12 blocks allowed', limit(7) is not None, True))
cases.append(('5 slime + 8 quartz = 13 blocks refused', limit(8) is None, True))
# 5 a branch whose front cell is immovable fails the whole move (145-146)
w = mk({(0, 1, 0): ('SL', 's'), (1, 1, 0): ('Q', 'q'), (1, 2, 0): ('OBS',)}, (0, 0, 0), 'U')
cases.append(('branch blocked by obsidian fails the move', w.resolve((0, 0, 0), 'U', True), None))
# 6 immovable sticky neighbour is simply skipped (82-83)
w = mk({(0, 1, 0): ('SL', 's'), (1, 1, 0): ('OBS',)}, (0, 0, 0), 'U')
cases.append(('obsidian beside slime is skipped', names(w, w.resolve((0, 0, 0), 'U', True)), ['s']))
# 7 pull: a line in front of a dragged block pushes a retracted piston (122-161)
w = mk({(0, 2, 0): ('SL', 's'), (1, 2, 0): ('SL', 'n'), (1, 1, 0): ('P', 'p2', 'U', True, False)}, (0, 0, 0), 'U')
cases.append(('dragged slime pushes a retracted piston in its line', names(w, w.resolve((0, 0, 0), 'U', False)), ['P:p2', 'n', 's']))
# 8 back-drag does not pass the piston's own cell (106)
w = mk({(0, 1, 0): ('SL', 's')}, (0, 0, 0), 'U')
cases.append(('push: back-drag stops at the pusher', names(w, w.resolve((0, 0, 0), 'U', True)), ['s']))

bad = 0
for label, got, exp in cases:
    ok = got == exp
    bad += not ok
    print(('PASS' if ok else 'FAIL'), label, '| got', got, '| expected', exp)
print('failures:', bad)
