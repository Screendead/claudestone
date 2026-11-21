"""Independent 26.3 piston replay for 3x3 door schedules (front (a) verdict).

Written from the 26.3 source, not from relax*/door_planner:
  PistonBaseBlock.triggerEvent 139-211, moveBlocks 257-330, isPushable 213-255,
  PistonStructureResolver 25-191, PistonMovingBlockEntity.finalTick 259-280.

Cells are (x, y, z). Frame: x,y in 0..2 at z=0. Hallway: x,y in 0..2, 1<=|z|<=HALL.
Blocks:
  None                      air
  ('Q', name)               quartz-like (door block, spare, wall)
  ('OBS',)                  immovable opaque block
  ('SL', name) / ('HO', n)  slime / honey
  ('P', name, facing, sticky, extended)
  ('HEAD', name, facing)    piston head (IMMOVEABLE)
  ('MOV', moved, dir, extending, source, start)   moving_piston + block entity
A MOV lands at the end of tick start+2 (phase j); from tick start+3 it is real.
"""
import itertools

HALL = 3
DIRS = {'D': (0, -1, 0), 'U': (0, 1, 0), 'N': (0, 0, -1), 'S': (0, 0, 1), 'W': (-1, 0, 0), 'E': (1, 0, 0)}
ORDER = ['D', 'U', 'N', 'S', 'W', 'E']          # Direction.values()


def add(p, d, k=1):
    return (p[0] + d[0] * k, p[1] + d[1] * k, p[2] + d[2] * k)


def neg(d):
    return (-d[0], -d[1], -d[2])


def axis(d):
    return [i for i in range(3) if d[i]][0]


def in_frame(c):
    return 0 <= c[0] <= 2 and 0 <= c[1] <= 2 and c[2] == 0


def in_I(c):
    return 0 <= c[0] <= 2 and 0 <= c[1] <= 2 and abs(c[2]) <= HALL


def in_V(c):
    if in_I(c):
        return False
    return any(in_I(add(c, d)) for d in DIRS.values())


def is_sticky(b):
    return b is not None and b[0] in ('SL', 'HO')


def can_stick(a, b):
    if a is None or b is None:
        return False
    if a[0] == 'HO' and b[0] == 'SL':
        return False
    if a[0] == 'SL' and b[0] == 'HO':
        return False
    return is_sticky(a) or is_sticky(b)


def pushable(b):
    """isPushable for the block kinds used here (all NORMAL push reaction except noted)."""
    if b is None:
        return True
    k = b[0]
    if k == 'P':
        return not b[4]
    if k in ('MOV', 'HEAD', 'OBS'):
        return False
    return True


class Fail(Exception):
    pass


class World:
    def __init__(self, blocks):
        self.w = dict(blocks)
        self.t = 0
        self.log = []          # (tick, kind, from, to, what)
        self.fired = {}        # piston name -> last event tick

    def get(self, c):
        return self.w.get(c)

    def set(self, c, b):
        if b is None:
            self.w.pop(c, None)
        else:
            self.w[c] = b

    def find(self, name):
        for c, b in self.w.items():
            if b[0] in ('P', 'Q', 'SL', 'HO') and b[1] == name:
                return c
        raise Fail(f'{name}: not found as a real block at t{self.t}')

    # ---- PistonStructureResolver ----
    def resolve(self, piston_pos, facing, extending):
        d = DIRS[facing]
        push = d if extending else neg(d)
        start = add(piston_pos, d) if extending else add(piston_pos, d, 2)
        to_push = []

        def add_line(s, direction):
            nxt = self.get(s)
            if nxt is None:
                return True
            if not pushable(nxt):
                return True
            if s == piston_pos:
                return True
            if s in to_push:
                return True
            count = 1
            if count + len(to_push) > 12:
                return False
            while is_sticky(nxt):
                p = add(s, neg(push), count)
                prev = nxt
                nxt = self.get(p)
                if nxt is None or not can_stick(prev, nxt) or not pushable(nxt) or p == piston_pos:
                    break
                count += 1
                if count + len(to_push) > 12:
                    return False
            added = 0
            for i in range(count - 1, -1, -1):
                to_push.append(add(s, neg(push), i))
                added += 1
            i = 1
            while True:
                p = add(s, push, i)
                if p in to_push:
                    coll = to_push.index(p)
                    head = to_push[:coll]
                    last = to_push[len(to_push) - added:]
                    mid = to_push[coll:len(to_push) - added]
                    to_push[:] = head + last + mid
                    for j in range(0, coll + added + 1):
                        if is_sticky(self.get(to_push[j])) and not branch(to_push[j]):
                            return False
                    return True
                nxt = self.get(p)
                if nxt is None:
                    return True
                if not pushable(nxt) or p == piston_pos:
                    return False
                if len(to_push) >= 12:
                    return False
                to_push.append(p)
                added += 1
                i += 1

        def branch(frm):
            fs = self.get(frm)
            for dn in ORDER:
                dv = DIRS[dn]
                if axis(dv) == axis(push):
                    continue
                npos = add(frm, dv)
                if can_stick(self.get(npos), fs) and not add_line(npos, dv):
                    return False
            return True

        first = self.get(start)
        if not pushable(first):
            return None
        if not add_line(start, push):
            return None
        i = 0
        while i < len(to_push):
            if is_sticky(self.get(to_push[i])) and not branch(to_push[i]):
                return None
            i += 1
        return to_push, push

    # ---- PistonBaseBlock.moveBlocks ----
    def move_blocks(self, ppos, facing, extending, why):
        d = DIRS[facing]
        arm = add(ppos, d)
        if not extending and self.get(arm) is not None and self.get(arm)[0] == 'HEAD':
            self.set(arm, None)
        r = self.resolve(ppos, facing, extending)
        if r is None:
            return False
        to_push, push = r
        states = [self.get(p) for p in to_push]
        delete = {p: self.get(p) for p in to_push}
        for i in range(len(to_push) - 1, -1, -1):
            src = to_push[i]
            dst = add(src, push)
            delete.pop(dst, None)
            self.set(dst, ('MOV', states[i], facing, extending, False, self.t))
            self.log.append((self.t, why, src, dst, states[i]))
        if extending:
            delete.pop(arm, None)
            self.set(arm, ('MOV', ('HEAD', why, facing), facing, True, True, self.t))
        for p in delete:
            self.set(p, None)
        return True

    def final_tick(self, c):
        b = self.get(c)
        if b is None or b[0] != 'MOV':
            return
        moved, _, _, source, _ = b[1:]
        self.set(c, None if source else moved)

    # ---- triggerEvent ----
    def extend(self, name):
        c = self.find(name)
        b = self.get(c)
        if b[0] != 'P' or b[4]:
            raise Fail(f'{name} cannot extend at t{self.t}: {b}')
        last = self.fired.get(name)
        if last is not None and self.t < last + 3:
            raise Fail(f'{name} fired at t{last}, cannot fire at t{self.t}')
        if not self.move_blocks(c, b[2], True, name):
            raise Fail(f'{name}: extension blocked at t{self.t}')
        self.set(c, ('P', b[1], b[2], b[3], True))
        self.fired[name] = self.t

    def retract(self, name):
        c = None
        for cc, b in self.w.items():
            if b[0] == 'P' and b[1] == name:
                c = cc
        if c is None:
            raise Fail(f'{name}: not a real piston at t{self.t}')
        b = self.get(c)
        if not b[4]:
            raise Fail(f'{name}: retract while not extended at t{self.t}')
        _, nm, facing, sticky, _ = b
        d = DIRS[facing]
        one = add(c, d)
        if self.get(one) is not None and self.get(one)[0] == 'MOV':
            self.final_tick(one)
        self.set(c, ('MOV', ('P', nm, facing, sticky, False), facing, False, True, self.t))
        self.log.append((self.t, nm + ':base', c, c, 'retract'))
        self.fired[nm] = self.t
        if sticky:
            two = add(c, d, 2)
            m = self.get(two)
            if m is not None and m[0] == 'MOV' and m[2] == facing and m[3]:
                # spit: the block at +2 is placed at once
                self.set(two, m[1])
                return 'spit'
            if m is None or not pushable(m):
                self.set(one, None)
                return 'none'
            if not self.move_blocks(c, facing, False, nm):
                raise Fail(f'{nm}: pull blocked at t{self.t}')
            return 'pull'
        self.set(one, None)
        return 'none'

    def zero_tick(self, name):
        self.extend(name)
        return self.retract(name)

    def end_tick(self):
        for c, b in list(self.w.items()):
            if b[0] == 'MOV' and b[5] + 2 <= self.t:
                self.set(c, b[1])   # natural landing (PMBE.tick 294-313) places movedState, source or not
        self.t += 1

    def moving(self):
        return any(b[0] == 'MOV' for b in self.w.values())


def run(world, schedule, horizon=12):
    """schedule: {tick: [(op, piston_name), ...]} with op in {'0t', 'ret', 'ext'}."""
    results = {}
    for t in range(horizon + 1):
        world.t = t
        for op, nm in schedule.get(t, []):
            if op == '0t':
                results[(t, nm)] = world.zero_tick(nm)
            elif op == 'ret':
                results[(t, nm)] = world.retract(nm)
            elif op == 'ext':
                world.extend(nm)
            else:
                raise ValueError(op)
        world.frame_after_g = getattr(world, 'frame_after_g', {})
        world.frame_after_g[t] = [c for c, b in world.w.items() if in_I(c)]
        world.end_tick()
    return results


def check_closed(blocks, door):
    bad = []
    for c, b in blocks.items():
        if in_frame(c):
            if b is None or b[0] != 'Q':
                bad.append(('frame', c, b))
        elif in_I(c):
            bad.append(('hallway not air', c, b))
        elif in_V(c) and c[2] != 0 and b[0] not in ('Q', 'OBS'):
            bad.append(('visible wall cell not quartz', c, b))
    for x in range(3):
        for y in range(3):
            if (x, y, 0) not in blocks:
                bad.append(('frame empty', (x, y, 0)))
    return bad


def check_open(world, wall_ok=('Q',)):
    bad = []
    for c, b in world.w.items():
        if in_I(c):
            bad.append(('interior not air', c, b))
        elif in_V(c) and b[0] not in wall_ok:
            bad.append(('visible cell holds', c, b))
    return bad


def metrics(world):
    # opening (motion-start S): first tick T after whose phase g the interior stays empty
    last_nonempty = max([t for t, cells in world.frame_after_g.items() if cells], default=-1)
    opening = last_nonempty + 1 if last_nonempty >= 0 else 0
    vis = [(t, why, a, b) for (t, why, a, b, _) in world.log
           if (in_V(a) or in_I(a) or in_V(b) or in_I(b))]
    seam = max(t for t, *_ in vis) if vis else 0
    return opening, seam, vis


def walls(extra_skip=()):
    """Quartz walls/floor/ceiling of the hallway (z != 0) and nothing else."""
    out = {}
    for z in range(-HALL, HALL + 1):
        if z == 0:
            continue
        for x in range(-1, 4):
            for y in range(-1, 4):
                c = (x, y, z)
                if in_V(c) and c not in extra_skip:
                    out[c] = ('Q', f'wall{c}')
    return out
