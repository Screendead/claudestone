"""Repeater-line router on rows 5/7/9/11 (supports one row below), for 2 gt pulse nets (risers allowed) and level nets
(no risers). Nets keep a one-cell gap from each other's active cells; supports are inert and may touch anything."""
import heapq
H = {'east': (1, 0, 0), 'west': (-1, 0, 0), 'south': (0, 0, 1), 'north': (0, 0, -1)}
OPP = {'east': 'west', 'west': 'east', 'north': 'south', 'south': 'north', 'up': 'down', 'down': 'up'}
PERP = {'east': ('north', 'south'), 'west': ('north', 'south'), 'north': ('east', 'west'), 'south': ('east', 'west')}
NB6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
ROWS = (5, 7, 9, 11)


def add(p, v, k=1):
    return (p[0] + k * v[0], p[1] + k * v[1], p[2] + k * v[2])


class Board:
    def __init__(self, bounds, blocked, sup_blocked=()):
        self.bounds = bounds              # (x0, x1, z0, z1) inclusive
        self.blocked = set(blocked)       # no controller block at all
        self.sup_blocked = set(sup_blocked)
        self.active = {}                  # cell -> net (reps, blocks, observers, end components)
        self.support = {}                 # cell -> state
        self.reserved = {}                # cell -> net: must stay air (a riser rep's output cell)
        self.cells = {}                   # cell -> (state, net)

    def inb(self, p):
        x0, x1, z0, z1 = self.bounds
        return x0 <= p[0] <= x1 and z0 <= p[2] <= z1

    def rep_out(self, q):
        st = self.cells.get(q, ('',))[0]
        if not st.startswith('repeater'):
            return None
        f = st.split('facing=')[1].split(',')[0].split(']')[0]
        return add(q, H[OPP[f]])

    def free_active(self, p, net, allow=(), rep_dir=None):
        if not self.inb(p) or p in self.blocked or p in self.active or p in self.support \
                or self.reserved.get(p, net) != net:
            return False
        for v in NB6:
            q = add(p, v)
            o = self.active.get(q)
            if o is not None and o != net and q not in allow:
                # two repeaters side by side are independent unless one points into the other
                qo = self.rep_out(q)
                if rep_dir and qo is not None and qo != p and add(p, H[rep_dir]) != q and v[1] == 0:
                    continue
                qs = self.cells.get(q, ('',))[0]
                if qs.startswith('observer'):
                    f = qs.split('facing=')[1].split(',')[0].split(']')[0]
                    dv = {'up': (0, 1, 0), 'down': (0, -1, 0), **H}[f]
                    if p != add(q, dv) and p != add(q, dv, -1):
                        continue                # beside an observer, neither watched by it nor fed by it
                if rep_dir and v[1] == 0 and 'torch' in self.cells.get(q, ('',))[0] \
                        and add(p, H[rep_dir], -1) != q and add(p, H[rep_dir]) != q:
                    continue                    # a torch beside a repeater's side does not touch it
                return False
        return True

    def free_support(self, p):
        if p in self.support or (p in self.active and self.cells[p][0].split('[')[0] in ('stone', 'obsidian', 'observer')):
            return True
        if not self.inb(p) or p in self.blocked or p in self.sup_blocked or p in self.active or p in self.reserved:
            return False
        return True

    def place(self, p, state, net, kind='active'):
        if kind == 'support':
            if p in self.support or p in self.active:
                return
            self.support[p] = state
        else:
            self.active[p] = net
        self.cells[p] = (state, net)


def rep_state(d, delay=1):
    return f'repeater[facing={OPP[d]},delay={delay}]'


def route(bd, net, start, goal, pulse=True, rows=ROWS, allow_end=(), allow_start=(), max_cost=400, sup='stone',
          tail=0, deep=None):
    """tail: the last `tail` repeaters (the goal's included) come after the last riser, so they can take extra delay."""
    """start = (p, d): first rep at p pointing d (its input is p - d). goal = (q, D): last rep at q pointing D.
    allow_end: cells next to the goal that belong to other nets (the end component). Places and returns the path."""
    (p0, d0), (g, gd) = start, goal
    start_state = (p0, d0, True, 0)       # the source is a block or a component: start with a repeater
    pq = [(0, 0, start_state, None)]
    seen = {}
    parent = {}
    cnt = 0
    while pq:
        f, c, st, par = heapq.heappop(pq)
        if st in seen:
            continue
        seen[st] = c
        parent[st] = par
        p, d, prevblock, k = st
        if (p, d) == (g, gd) and k + 1 >= tail:
            if bd.free_active(p, net, set(allow_end), rep_dir=d) and bd.free_support(add(p, (0, -1, 0))) \
                    and _self_ok(st, parent):
                return _commit(bd, net, st, parent, pulse, sup)
            continue
        if c > max_cost:
            continue
        # move 1: rep at p pointing d
        moves = []
        al = set(allow_start) if c == 0 else set()
        if bd.free_active(p, net, al, rep_dir=d) and bd.free_support(add(p, (0, -1, 0))):
            moves.append(((add(p, H[d]), d, False, min(k + 1, tail)), 1 if deep is None or p[1] <= deep else 2,
                          ('rep', p, d)))
            # risers (pulse nets): rep at p, obs above/below, block two rows away
            if pulse:
                fw = add(p, H[d])
                if fw not in bd.active and fw not in bd.support and fw not in bd.reserved:
                    for dy in (2, -2):
                        if p[1] + dy not in rows:
                            continue
                        o, b = add(p, (0, dy // 2, 0)), add(p, (0, dy, 0))
                        if dy == 2 and not bd.free_active(o, net):
                            continue
                        if dy == -2 and not (bd.free_active(o, net) and bd.free_support(add(o, (0, -1, 0)))):
                            continue
                        if not bd.free_active(b, net):
                            continue
                        for nd in H:
                            moves.append(((add(b, H[nd]), nd, True, 0), 4, ('riser', p, d, dy, nd)))
        if not prevblock and bd.free_active(p, net):
            for nd in PERP[d]:
                moves.append(((add(p, H[nd]), nd, True, k), 1, ('turn', p, nd)))
        for nst, dc, mv in moves:
            if nst in seen or not bd.inb(nst[0]):
                continue
            h = abs(nst[0][0] - g[0]) + abs(nst[0][2] - g[2]) + abs(nst[0][1] - g[1])
            cnt += 1
            heapq.heappush(pq, (c + dc + h, c + dc, nst, (st, mv)))
    raise RuntimeError(f'no route for {net}: {start} -> {goal}')


def _groups(st, parent):
    moves = []
    cur = st
    while parent[cur] is not None:
        prev, mv = parent[cur]
        moves.append(mv)
        cur = prev
    moves.reverse()
    groups = []
    for mv in moves:
        if mv[0] == 'rep':
            groups.append([mv[1], add(mv[1], (0, -1, 0))])
        elif mv[0] == 'turn':
            groups.append([mv[1]])
        else:
            _, p, d, dy, nd = mv
            groups.append([p, add(p, (0, -1, 0)), add(p, (0, dy // 2, 0)), add(p, (0, dy, 0))])
    groups.append([st[0], add(st[0], (0, -1, 0))])
    return groups


def _self_ok(st, parent):
    """No cell used twice, and no face contact between path elements more than one step apart."""
    groups = _groups(st, parent)
    owner = {}
    for i, gcells in enumerate(groups):
        for q in gcells:
            if q in owner and owner[q] != i:
                return False
            owner[q] = i
    act = {}
    for i, gcells in enumerate(groups):
        for q in gcells[:1] + gcells[2:]:
            act[q] = i
    for q, i in act.items():
        for v in NB6:
            j = act.get(add(q, v))
            if j is not None and abs(j - i) > 1:
                return False
    return True


def _commit(bd, net, st, parent, pulse, sup):
    moves = []
    cur = st
    while parent[cur] is not None:
        prev, mv = parent[cur]
        moves.append(mv)
        cur = prev
    moves.reverse()
    path = []
    for mv in moves:
        if mv[0] == 'rep':
            _, p, d = mv
            bd.place(p, rep_state(d), net); bd.place(add(p, (0, -1, 0)), sup, net, 'support')
            path.append(('rep', p, d))
        elif mv[0] == 'turn':
            _, p, nd = mv
            bd.place(p, sup, net)
            path.append(('block', p))
        else:
            _, p, d, dy, nd = mv
            bd.place(p, rep_state(d), net)
            o, b = add(p, (0, dy // 2, 0)), add(p, (0, dy, 0))
            if dy == 2:
                bd.place(add(p, (0, -1, 0)), sup, net, 'support')
                bd.place(o, 'observer[facing=down]', net)
            else:
                bd.place(o, 'observer[facing=up]', net)
            bd.place(b, sup, net)
            bd.reserved[add(p, H[d])] = net
            path.append(('rep', p, d)); path.append(('obs', o)); path.append(('block', b))
    p, d, _, _ = st
    bd.place(p, rep_state(d), net); bd.place(add(p, (0, -1, 0)), sup, net, 'support')
    path.append(('rep', p, d))
    return path


def set_delays(bd, path, extra_gt, maxd=4):
    """Add extra_gt (even) of delay on the reps after the path's last observer (risers need 2 gt pulses)."""
    assert extra_gt % 2 == 0 and extra_gt >= 0, extra_gt
    units = extra_gt // 2
    last_obs = max([i for i, e in enumerate(path) if e[0] == 'obs'], default=-1)
    reps = [e for e in path[last_obs + 1:] if e[0] == 'rep']
    if units > (maxd - 1) * len(reps):
        raise RuntimeError(f'need {units} delay units on {len(reps)} reps')
    for e in reps:
        k = min(maxd - 1, units)
        units -= k
        if k:
            st, net = bd.cells[e[1]]
            bd.cells[e[1]] = (st.replace('delay=1', f'delay={1 + k}'), net)
    return path
