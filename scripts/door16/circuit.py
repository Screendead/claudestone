"""Hand-placed redstone with a turtle, plus a coupling checker.

Cells carry (block state, net). Directions are signal directions: east +x, west -x, south +z, north -z."""
D = {'east': (1, 0, 0), 'west': (-1, 0, 0), 'south': (0, 0, 1), 'north': (0, 0, -1), 'up': (0, 1, 0), 'down': (0, -1, 0)}
OPP = {'east': 'west', 'west': 'east', 'north': 'south', 'south': 'north', 'up': 'down', 'down': 'up'}


def add(p, d, k=1):
    v = D[d]
    return (p[0] + k * v[0], p[1] + k * v[1], p[2] + k * v[2])


class Circuit:
    def __init__(self, fixed=None):
        self.cells = {}          # pos -> state
        self.net = {}            # pos -> net
        self.meta = {}           # pos -> dict(kind, toward, ...)
        self.fixed = dict(fixed or {})   # machine cells (never overwritten)
        self.errors = []

    def put(self, p, state, net, kind='block', **m):
        if p in self.fixed:
            self.errors.append(f'{net}: {p} is a machine cell ({self.fixed[p]})')
        if p in self.cells and (self.cells[p] != state or self.net[p] != net):
            if not (kind == 'support' and self.meta[p]['kind'] in ('support', 'block')):
                self.errors.append(f'{net}: {p} taken by {self.net[p]} ({self.cells[p]}), wanted {state}')
            return
        self.cells[p] = state
        self.net[p] = net
        self.meta[p] = dict(kind=kind, **m)

    def support(self, p, state='stone'):
        q = (p[0], p[1] - 1, p[2])
        if q in self.cells or q in self.fixed:
            return
        self.put(q, state, 'support', 'support')

    def rep(self, p, toward, net, delay=1, powered=False, locked=False, sup='stone'):
        facing = OPP[toward]
        self.put(p, f'repeater[facing={facing},delay={delay},powered={str(powered).lower()},'
                    f'locked={str(locked).lower()}]', net, 'rep', toward=toward, delay=delay)
        self.support(p, sup)

    def comp(self, p, toward, net, mode='compare', powered=False, nbt=''):
        facing = OPP[toward]
        self.put(p, f'comparator[facing={facing},mode={mode},powered={str(powered).lower()}]{nbt}', net, 'comp',
                 toward=toward)
        self.support(p)

    def obs(self, p, watch, net, powered=False):
        """observer at p watching the neighbour in direction `watch`; it outputs to the opposite side."""
        self.put(p, f'observer[facing={watch},powered={str(powered).lower()}]', net, 'obs', watch=watch,
                 toward=OPP[watch])

    def block(self, p, net, state='stone'):
        self.put(p, state, net, 'block')

    def torch(self, p, attached, net, lit=True):
        facing = OPP[attached]
        self.put(p, f'redstone_wall_torch[facing={facing},lit={str(lit).lower()}]', net, 'torch', attached=attached)

    def turtle(self, p, toward, net, y=None):
        return Turtle(self, p, toward, net)


class Turtle:
    """Places a line: fwd(n) puts n repeaters at the cursor along the signal direction; turn(d) puts a block at the
    cursor and continues in direction d; end() puts a block at the cursor (read by what comes next)."""
    def __init__(self, c, p, toward, net):
        self.c, self.p, self.d, self.net, self.reps = c, p, toward, net, 0
        self.gt = 0

    def fwd(self, n=1, delay=1, powered=False):
        for _ in range(n):
            self.c.rep(self.p, self.d, self.net, delay=delay, powered=powered)
            self.p = add(self.p, self.d)
            self.reps += 1
            self.gt += 2 * delay
        return self

    def turn(self, d, state='stone'):
        self.c.block(self.p, self.net, state)
        self.p = add(self.p, d)
        self.d = d
        return self

    def through(self, state='stone'):
        self.c.block(self.p, self.net, state)
        self.p = add(self.p, self.d)
        return self

    def end(self, state='stone'):
        self.c.block(self.p, self.net, state)
        return self


CONSUMERS = ('rep', 'comp', 'piston', 'hopper', 'dropper', 'bulb', 'torch')


def kind_of(state):
    s = state.split('[')[0].replace('minecraft:', '')
    if s == 'repeater':
        return 'rep'
    if s == 'comparator':
        return 'comp'
    if s in ('sticky_piston', 'piston'):
        return 'piston'
    if s in ('hopper', 'dropper', 'note_block'):
        return s if s != 'note_block' else 'note'
    if 'copper_bulb' in s:
        return 'bulb'
    if 'torch' in s:
        return 'torch'
    if s == 'observer':
        return 'obs'
    if s in ('air',):
        return 'air'
    if s in ('slime_block', 'honey_block'):
        return 'slime'
    return 'block'


def prop(state, key):
    import re
    m = re.search(rf'{key}=(\w+)', state)
    return m.group(1) if m else None


def couplings(c):
    """Every place where one element feeds another, as (from_net, from_pos, to_net, to_pos, how).
    Uses both controller cells and machine cells."""
    allc = {**c.fixed, **c.cells}
    nets = dict(c.net)
    out = []
    dirs = ['east', 'west', 'north', 'south', 'up', 'down']
    for p, st in allc.items():
        k = kind_of(st)
        if k in ('rep', 'comp'):
            toward = OPP[prop(st, 'facing')]
            f = add(p, toward)
            out.append((p, f, 'out'))
            # side locks: a diode beside p pointing into p
        elif k == 'obs':
            facing = prop(st, 'facing')
            out.append((p, add(p, OPP[facing]), 'out'))
            out.append((add(p, facing), p, 'watched'))
    res = []
    for src, dst, how in out:
        a, b = nets.get(src, 'machine'), nets.get(dst, 'machine')
        if how == 'watched':
            if dst in c.cells and (src in allc):
                res.append((a, src, b, dst, 'watched-by'))
            continue
        if dst not in allc:
            continue
        kd = kind_of(allc[dst])
        if kd in ('rep', 'comp'):
            toward = OPP[prop(allc[dst], 'facing')]
            back = add(dst, OPP[toward])
            if back == src:
                res.append((a, src, b, dst, 'input'))
            elif kd == 'rep' and add(src, OPP[prop(allc[src], 'facing')] if kind_of(allc[src]) in ('rep', 'comp') else 'up') == dst:
                res.append((a, src, b, dst, 'SIDE-LOCK'))
            elif kd == 'comp':
                res.append((a, src, b, dst, 'comp-side'))
        elif kd in ('piston', 'hopper', 'dropper', 'bulb', 'note'):
            res.append((a, src, b, dst, f'powers-{kd}'))
        elif kd == 'block':
            # strongly powered block: everything around it that reads it
            for d in dirs:
                q = add(dst, d)
                if q == src or q not in allc:
                    continue
                kq = kind_of(allc[q])
                if kq in ('rep', 'comp'):
                    tq = OPP[prop(allc[q], 'facing')]
                    if add(q, OPP[tq]) == dst:
                        res.append((a, src, nets.get(q, 'machine'), q, f'via-block {dst}'))
                elif kq in ('piston', 'hopper', 'dropper', 'bulb', 'note'):
                    res.append((a, src, nets.get(q, 'machine'), q, f'via-block {dst} powers-{kq}'))
                elif kq == 'torch':
                    res.append((a, src, nets.get(q, 'machine'), q, f'via-block {dst} torch?'))
    return res


def render(c, y, xs, zs, extra=None):
    allc = {**c.fixed, **c.cells}
    G = {'rep': {'east': '>', 'west': '<', 'north': '^', 'south': 'v'}, }
    lines = []
    for z in zs:
        row = ''
        for x in xs:
            p = (x, y, z)
            st = allc.get(p)
            if st is None:
                row += '.'
                continue
            k = kind_of(st)
            if k == 'rep':
                ch = G['rep'][OPP[prop(st, 'facing')]]
                if prop(st, 'delay') != '1':
                    ch = {'>': ')', '<': '(', '^': 'A', 'v': 'V'}[ch]
                row += ch
            elif k == 'comp':
                row += 'c'
            elif k == 'obs':
                row += {'east': 'E', 'west': 'W', 'north': 'N', 'south': 'S', 'up': 'U', 'down': 'D'}[prop(st, 'facing')]
            elif k == 'block':
                row += '#' if p in c.cells else ('X' if 'obsidian' in st else ('Q' if 'quartz' in st else '%'))
            else:
                row += {'piston': 'P', 'hopper': 'H', 'dropper': 'd', 'bulb': 'b', 'torch': 't', 'slime': 's',
                        'note': 'n'}.get(k, '?')
        lines.append(f'{z:4d} {row}')
    return '\n'.join(lines)


def torch(c, p, attached, net):
    """wall torch at p attached to the block in direction `attached` (lit by default)."""
    facing = OPP[attached]
    c.put(p, f'redstone_wall_torch[facing={facing},lit=true]', net, 'torch', attached=attached)


def propagate(c, src, t0=0, stop=None):
    """Rise times (gt) of every controller/machine cell reached from `src` (a cell that turns on at t0).
    rep: +2*delay; comparator, observer: +2; blocks and bulbs pass power on at once; observers fire 2 gt after the
    cell they watch changes. Torches are not followed (they invert)."""
    allc = {**c.fixed, **c.cells}
    import heapq
    best = {src: t0}
    pq = [(t0, src)]
    dirs = ['east', 'west', 'north', 'south', 'up', 'down']
    while pq:
        t, p = heapq.heappop(pq)
        if t > best.get(p, 1e9) or (stop and p in stop):
            continue
        st = allc.get(p, 'air')
        k = kind_of(st)
        outs = []
        if k in ('rep', 'comp'):
            outs.append(add(p, OPP[prop(st, 'facing')]))
        elif k == 'obs':
            outs.append(add(p, OPP[prop(st, 'facing')]))
        # observers watching p
        for d in dirs:
            q = add(p, d)
            sq = allc.get(q)
            if sq and kind_of(sq) == 'obs' and add(q, prop(sq, 'facing')) == p:
                nt = t + 2
                if nt < best.get(q, 1e9):
                    best[q] = nt; heapq.heappush(pq, (nt, q))
        for o in outs:
            so = allc.get(o, 'air')
            ko = kind_of(so)
            cand = []
            if ko in ('rep', 'comp'):
                if add(o, prop(so, 'facing')) == p:          # o's input side faces p
                    cand.append((o, (int(prop(so, 'delay') or 1) * 2) if ko == 'rep' else 2))
            elif ko == 'block':
                cand.append((o, 0))
                for d in dirs:
                    q = add(o, d)
                    sq = allc.get(q)
                    if q == p or not sq:
                        continue
                    kq = kind_of(sq)
                    if kq in ('rep', 'comp') and add(q, prop(sq, 'facing')) == o:
                        cand.append((q, int(prop(sq, 'delay') or 1) * 2 if kq == 'rep' else 2))
                    elif kq in ('bulb', 'hopper', 'dropper', 'piston'):
                        cand.append((q, 0))
            elif ko in ('bulb', 'hopper', 'dropper', 'piston'):
                cand.append((o, 0))
            for q, dt in cand:
                nt = t + dt
                if nt < best.get(q, 1e9):
                    best[q] = nt; heapq.heappush(pq, (nt, q))
    return best
