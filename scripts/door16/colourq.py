"""Colour door16_quart's plain stone by circuit (redstone.circuits traces it), plus an input-side legend.

apply(ns) takes pairs_ctrlq's globals once the grid is final and returns (grid, legend fixtures, key text, report).
Seeds: every non-stone, non-obsidian cell, classed by the generator's net (controller), machine (bands) or feed; all
quartz is fixed as the door's. The tracer then decides every stone (and obsidian, reported only) by the signal that
powers it, or by the component it supports. Provenance (the net that placed each stone) is checked against it."""
import re
import sys
from collections import Counter
from pathlib import Path

from redstone import circuits  # noqa: E402

CLASSES = {
    'feed': ('white', 'Input', 'and centre feed', '', ''),
    'logic': ('purple', 'Controller', 'logic: gates,', 'counter, fetch,', 'store gate'),
    'master': ('magenta', 'Masters: ladder,', 'timer taps,', 'spit/hold bulbs,', 'close pulses'),
    'sense': ('pink', 'Home sensors', 'and arrival', 'filters', ''),
    'kick': ('red', 'Kick lines', '(x-band, ZA, ZB,', 'close kick,', 'K_Z lock)'),
    'spit': ('yellow', 'Spit lines', '(x-band spits,', 'ZA spits)', ''),
    'store': ('orange', 'Store lines', '(ZB spits)', '', ''),
    'hold': ('blue', 'Hold lines', '(door pistons', 'held shut)', ''),
    'tower': ('cyan', 'Observer towers', '(pair to pair)', '', ''),
    'delay': ('light_blue', 'Delay lines', '(snakes, tuned', 'repeaters)', ''),
    circuits.SHARED: ('black', 'Shared', '(powered by two', 'circuits)', ''),
}
LEGEND_EXTRA = [('slime_block', 'Slime: even', 'x-bands and', 'every z-band', '(storage)'),
                ('honey_block', 'Honey: odd', 'x-bands', '', ''),
                ('quartz_block', 'Quartz: door,', 'stacks and', 'front ring', '')]
NETS = {
    'logic': 'LP LV LV3 LVC GC GS NLV NE CNT DFIRE ED ED2 FETCH REB STORE ZB GF GR',
    'master': 'LADT LADC LADR LADF TMR TAPA TAPB XSM XHM XSP XHP CLOSE CLOSE2 CLOSE3',
    'sense': 'SX SXM SXA SXT SXB XARR ZARR SZ GZ KZ',
    'kick': 'XK XKE XKO ZBKE ZBKO ZAKE ZAKO CLOSEK KZB',
    'spit': 'XSE XSO XSPE XSPO ZASE ZASO',
    'store': 'STOREE STOREO ZBSO',
    'hold': 'XHE XHO XHPE XHPO',
}
NET_CLASS = {n: k for k, v in NETS.items() for n in v.split()}
PLAIN = 'stone'


def net_class(net):
    if re.search(r'T\d+$', net):
        return 'tower'
    return NET_CLASS[re.sub(r'\d+$', '', net)]


def snake_cells(L3):
    out = {}
    for net, ((x0, y, z0), length, lines) in L3.SNAKE.items():
        for j in range(lines):
            z = z0 + 2 * j
            xs = range(x0, x0 + length)
            out.update({(x, y, z): net for x in xs})
            end = (x0 + length if j % 2 == 0 else x0 - 1, y, z)
            out[end] = net
            if j < lines - 1:
                out[(end[0], y, z + 1)] = out[(end[0], y, z + 2)] = net
    return out


def sign(*lines):
    msgs = ','.join('"%s"' % t for t in (list(lines) + ['', '', '', ''])[:4])
    return 'oak_wall_sign[facing=north,waterlogged=false]{front_text:{messages:[%s]}}' % msgs


def apply(ns):
    grid, ctl, geom, L3, cq = ns['grid'], ns['ctl'], ns['geom'], ns['ctrlq'].L3, ns['ctrlq']
    mx, bq = geom.mx, ns['bq']
    feed = set(ns['feed']) | set(ns['east']) | {ns['J']}
    machines = {}
    for name, m in bq.machines().items():
        for p in m:
            machines[p] = machines[mx(p)] = 'xband' if name.startswith('x') else 'zband'
    prov = {}                                  # cell -> the net the generator placed it for ('support' as placed)
    for p, net in ctl.net.items():
        prov[p] = prov[mx(p)] = net
    snakes = snake_cells(L3)
    for p, net in snakes.items():
        assert ctl.net.get(p) == net, (p, net, ctl.net.get(p))
    delay = set(snakes) | set(cq.UPSTREAM)
    for name, cells in ctl.marks['dl'].items():
        for p in cells:
            delay |= {(p[0], p[1] + 4 * L, p[2]) for L in range(cq.PAIRS)
                      if ctl.net.get((p[0], p[1] + 4 * L, p[2]), '').startswith(name)}
    delay |= {mx(p) for p in delay}
    fix_blocks = {p: st for p, (_, st) in ns['FIX'].items()}
    blocks = {**grid, **fix_blocks}
    fixed, seeds = {}, {}
    for p, st in blocks.items():
        b = circuits.parse(st)[0]
        if b == 'quartz_block':
            fixed[p] = 'door'
            continue
        if b in (PLAIN, 'obsidian'):
            continue
        if p in machines:
            cls = machines[p]
        elif p in feed or p in fix_blocks:
            cls = 'feed'
        elif p in delay:
            cls = 'delay'
        else:
            cls = net_class(prov[p])
        seeds.setdefault(cls, set()).add(p)
    t = circuits.trace(blocks, seeds, fixed)
    # never recolour a block whose material something reads: a piston's push line, glue, a note block's instrument
    reads = set()
    for p, st in blocks.items():
        b, pr = circuits.parse(st)
        if b in ('piston', 'sticky_piston'):
            reads |= {tuple(p[i] + k * circuits.STEP[pr['facing']][i] for i in range(3)) for k in range(1, 13)}
        if b == 'note_block':
            reads.add((p[0], p[1] - 1, p[2]))
    stones = [p for p, st in grid.items() if st == PLAIN]
    out = dict(grid)
    kept = Counter()
    for p in stones:
        o = t.owner[p]
        if p in reads or t.how[p] == 'glue':
            kept['material read'] += 1
        elif o is None:
            kept['unassigned'] += 1
        elif o not in CLASSES:
            kept[f'owned by {o}'] += 1
        else:
            out[p] = f'{CLASSES[o][0]}_concrete'
    # provenance check: the net that placed each stone, a support taking the net of the block above it
    expect = {}
    for p in stones:
        net = prov.get(p)
        if p in feed:
            expect[p] = 'feed'
        elif net is None:
            continue
        else:
            if net == 'support':
                net = prov.get((p[0], p[1] + 1, p[2]), 'support')
            above = (p[0], p[1] + 1, p[2])
            expect[p] = ('delay' if (p in delay or (prov.get(p) == 'support' and above in delay)) else
                         net_class(net) if net != 'support' else None)
    expect = {p: e for p, e in expect.items() if e is not None}
    dis = t.disagreements(expect)
    report = dict(
        stones=len(stones),
        traced=Counter(t.owner[p] for p in stones),
        how=Counter(t.how[p] for p in stones),
        recoloured=Counter(out[p] for p in stones if out[p] != PLAIN),
        kept=kept,
        obsidian=Counter(t.owner[p] for p, st in grid.items() if st == 'obsidian'),
        disagree=Counter((e, g) for _, e, g in dis), disagree_cells=dis,
        shared_cells=sorted(p for p in stones if t.owner[p] == circuits.SHARED),
        tracing=t)
    legend = place_legend(ns, blocks, geom)
    return out, legend, report


def place_legend(ns, blocks, geom):
    """A row of key blocks, each with a sign on its north face, near the input, inside the build's box and with no
    neighbour in the build or in any machine's sweep."""
    entries = [(f'{c[0]}_concrete', *c[1:]) for c in CLASSES.values()] + LEGEND_EXTRA
    n = len(entries)
    lo, hi = ns['lo'], ns['hi']
    swept, near, piston = geom.machine_sweeps()
    busy = set(blocks) | {ns['DRIVE']} | swept | {geom.mx(p) for p in swept}
    nb = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    clear = lambda p: p not in busy and all((p[0] + a, p[1] + b, p[2] + c) not in busy for a, b, c in nb)
    dx, dy, dz = ns['DRIVE']
    best = None
    for y in range(lo[1], hi[1] + 1):
        for z in range(lo[2] + 1, hi[2] + 1):
            for x0 in range(lo[0], hi[0] - 2 * (n - 1) + 1):
                cells = [(x0 + 2 * i, y, z) for i in range(n)]
                if all(clear(c) and clear((c[0], c[1], c[2] - 1)) for c in cells):
                    mid = cells[n // 2]
                    d = abs(mid[0] - dx) + abs(y - dy) * 2 + abs(z - dz)
                    if best is None or d < best[0]:
                        best = (d, cells)
    assert best, 'no room for the legend'
    out = {}
    for c, (blk, *text) in zip(best[1], entries):
        out[c] = (None, blk)
        out[(c[0], c[1], c[2] - 1)] = (None, sign(*text))
    return out
