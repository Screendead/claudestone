"""Generate a QUART door spec from band_quart + ctrlq: `pairs` row pairs (rows 4..), N columns per half, both halves,
one input (fixture repeater on the centre line), facing south (front = side B, which no x-band ever enters), the
front ring of the hallway filled with quartz.

python -m scripts.door16.pairs_ctrlq OUT.yaml N PAIRS [--name NAME] [--open T] [--close T]

door16_quart_compact, byte for byte (about a minute):
python -m scripts.door16.pairs_ctrlq library/door/door16_quart_compact.redstone.yaml 8 8 --v2 \
    --compact scripts/door16/low_snakes.py --colour --name door16_quart_compact --open 13000 --close 1500

scripts/door16/odd_south.py instead of low_snakes.py gives the 74x30 build (close snakes on the bottom routing row),
measured with --measured "door_cycle on satellites: open R 9234, close R 448, front L, tier QUART, volume 99,900 = \
74x30x45 against the 96-wide v4b's 129,600 and door16_quart's 213,840 = 108x30x66"

scripts/door16/final.py instead of odd_south.py gives the 96-wide v4b (odd lines out west), measured with
--measured "door_cycle on dsats: open R 9234, close R 448, front L, tier QUART, volume 129,600 = 96x30x45 \
against door16_quart's 213,840 = 108x30x66, open 166 gt and close 16 gt faster"
"""
import re
import sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] not in ('--compact', '--name', '--open', '--close', '--measured')]
opt = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
OUT, N, PAIRS = Path(args[0]), int(args[1]), int(args[2])
NAME = opt('--name', 'door16_quart_slice')
OPEN_WAIT, CLOSE_WAIT = opt('--open', 9000), opt('--close', 1200)
if '--v2' in sys.argv:
    import ctrlq2 as ctrlq          # noqa: E402
    import timingq2 as timingq      # noqa: E402
else:
    import ctrlq                     # noqa: E402
    import timingq                   # noqa: E402
import geomq as geom                 # noqa: E402
if '--compact' in sys.argv:
    import ast
    ctrlq.COMPACT.update(ast.literal_eval(Path(sys.argv[sys.argv.index('--compact') + 1]).read_text()))
bq = ctrlq.setup(N, PAIRS)
ZD, D0 = geom.ZD, geom.D0
ctl, TIMES, EXTRA = timingq.tuned(N, start=dict(ctrlq.COMPACT.get('zas_start') or {'e': 25, 'o': 25})) if (N > 5 and '--v2' in sys.argv) else timingq.tuned(N)
west = dict(geom.WEST)
west.update(ctl.cells)
IL = ctl.marks['IL']
grid = geom.both(west)
REP_N = 'repeater[facing=north,delay=1,powered=false,locked=false]'
ROWS = [y for n in bq.BANDS for y in bq.rows(n)]
Y0R, Y1R = min(ROWS), max(ROWS)


def wire(*sides):
    return 'redstone_wire[' + ','.join(f'{d}={"side" if d in sides else "none"}'
                                       for d in ('east', 'north', 'south', 'west')) + ',power=0]'


def mirror_wire(b):
    return b.replace('east=', 'TMP=').replace('west=', 'east=').replace('TMP=', 'west=')


# one input for both halves (as pc/pairs_ctrl9): each half's lever cell IL becomes a T of dust lit from the block under
# it, fed by a column of repeaters from a dust line that meets the other half's at a block J on the centre line
X0, Y0, Z0 = IL[0], IL[1] - 1, IL[2]
ZR = Z0 - 7
feed = {IL: wire('east', 'west', 'south'), (X0, Y0, Z0): 'stone'}
for dz, st in ((-1, REP_N), (-2, 'stone'), (-3, REP_N), (-4, 'stone'), (-5, wire('north', 'south')), (-6, REP_N)):
    feed[(X0, Y0, Z0 + dz)] = st
feed[(X0, Y0, ZR)] = wire('east', 'south')
XJ = (geom.X - 1) // 2
for x in range(X0 + 1, XJ):
    feed[(x, Y0, ZR)] = wire('east', 'west')
for p, st in list(feed.items()):
    if 'repeater' in st or 'wire' in st and p != IL:
        feed[(p[0], Y0 - 1, p[2])] = 'stone'
east = {geom.mx(p): mirror_wire(geom.mirror_state(b)) for p, b in feed.items()}
east[(XJ + 1, Y0, ZR)] = wire('east', 'west')
east[(XJ + 1, Y0 - 1, ZR)] = 'stone'
J = (XJ, Y0, ZR)
clash = sorted(p for p in {**feed, **east} if p in grid and p not in (IL, geom.mx(IL)))
assert not clash, clash
grid.update(feed)
grid.update(east)
grid[J] = 'stone'
REP = (XJ, Y0, ZR - 1)
DRIVE = (XJ, Y0, ZR - 2)
FIX = {REP: ('rep', REP_N), (XJ, Y0 - 1, ZR - 1): (None, 'stone')}
# front ring (side B, z = ZD + 1): walls at x D0-1 and D0+2N, floor and ceiling rows; quartz, never moved
RING = {}
for y in range(Y0R, Y1R + 1):
    RING[(D0 - 1, y, ZD + 1)] = RING[(D0 + 2 * N, y, ZD + 1)] = 'quartz_block'
for x in range(D0, D0 + 2 * N):
    RING[(x, Y0R - 1, ZD + 1)] = RING[(x, Y1R + 1, ZD + 1)] = 'quartz_block'
clash = sorted(p for p in RING if p in grid)
assert not clash, clash
grid.update(RING)
inputs = {DRIVE: 'door_in'}
assert not set(FIX) & set(grid) and DRIVE not in grid
pts = list(grid) + list(inputs) + list(FIX)
lo = [min(p[i] for p in pts) for i in range(3)]
hi = [max(p[i] for p in pts) for i in range(3)]
SH = tuple(-v for v in lo)
COLOUR = '--colour' in sys.argv
if COLOUR:
    import colourq                   # noqa: E402
    grid, LEGEND, CREPORT = colourq.apply(globals())
    FIX.update(LEGEND)
    pts = list(grid) + list(inputs) + list(FIX)
    assert [min(p[i] for p in pts) for i in range(3)] == lo and [max(p[i] for p in pts) for i in range(3)] == hi


def sp(p):
    return (p[0] + SH[0], p[1] + SH[1], p[2] + SH[2])


GLYPHS = ('ABCDEFGHIJKLMNOPRSTUVWYZabcdefghijklmnopqrstuvwyz0123456789!$%&()*+,-/:;<=>?@[]^_`{}~'
          + ''.join(map(chr, [*range(0x3b1, 0x3ca), *range(0x430, 0x450)])))
blocks = sorted(set(grid.values()))
FIXV = sorted(set(FIX.values()), key=lambda v: (v[0] or '', v[1]))
assert len(blocks) + 1 + len(FIXV) <= len(GLYPHS), len(blocks)
gl = dict(zip(blocks, GLYPHS))
gl_in = GLYPHS[len(blocks)]
gl_fixv = {v: GLYPHS[len(blocks) + 1 + i] for i, v in enumerate(FIXV)}
gl_fix = {p: gl_fixv[v] for p, v in FIX.items()}


def layers():
    out = []
    for y in range(lo[1], hi[1] + 1):
        rows = []
        for z in range(lo[2], hi[2] + 1):
            rows.append(''.join(gl_in if (x, y, z) in inputs else gl_fix[(x, y, z)] if (x, y, z) in FIX
                                else gl[grid[(x, y, z)]] if (x, y, z) in grid else '.'
                                for x in range(lo[0], hi[0] + 1)))
        out.append(f"  {y - lo[1]}: |\n" + ''.join(f"    {r}\n" for r in rows))
    return ''.join(out)


def palette():
    s = "  '.': air\n"
    for b, g in gl.items():
        q = b.replace("'", "''")
        s += f"  '{g}': '{q}'\n"
    for name, st in FIXV:
        s += f"  '{gl_fixv[(name, st)]}': {{" + (f"name: {name}, " if name else '') + f"block: '{st}', fixture: true}}\n"
    return s + f"  '{gl_in}': {{input: door_in}}\n"


def checks(cells):
    items = [f"if block ~{sp(p)[0]} ~{sp(p)[1]} ~{sp(p)[2]} {re.sub(r'[{].*[}]$', '', b)}"
             for p, b in sorted(cells.items())]
    return ''.join(f"  - check: '{' '.join(items[i:i + 12])}'\n" for i in range(0, len(items), 12))


def queue(n):
    s = bq.slot(n)
    row = {x: 'air' for x in range(s, D0 + N)}
    row[s] = 'quartz_block'
    row.update({x: 'quartz_block' for x in range(s + 2, s + 2 + N)})
    return geom.both({(x, y, ZD): b for x, b in row.items() for y in bq.rows(n)})


ALL = dict(grid)
QUEUES = {}
for n in bq.BANDS:
    QUEUES.update(queue(n))
cycle = ("  - drive: {door_in: 1}\n" + f"  - wait: {OPEN_WAIT}\n" + checks(QUEUES) +
         "  - drive: {door_in: 0}\n" + f"  - wait: {CLOSE_WAIT}\n" + checks(ALL))
tests = [("two cycles, the counter and every bulb reset in between", cycle + cycle)]


def door():
    o = sp((D0, Y0R, ZD))
    return (f"door:\n  doorway: {{origin: [{o[0]}, {o[1]}, {o[2]}], width: {2 * N}, height: {Y1R - Y0R + 1}, facing: south}}\n"
            "  depth: 1\n  blocks: closed\n  input: door_in\n  repeater: rep\n")


DOOR_TEST = "- name: door cycle\n  door_cycle: {cycles: 1, max_ticks: %d, quiet: 2500}\n" % (OPEN_WAIT + 3000)

if __name__ == '__main__':
    head = (f"The full 16x16 in-plane piston door, QUART-seamless (door_cycle on dsats: open R 9400, close R 464, front L, "
            f"tier QUART): {PAIRS} row pairs (rows {Y0R}-{Y1R}), {N} columns per half, both halves, one input. "
            if (N, PAIRS) == (8, 8) else
            f"QUART-seamless in-plane piston door slice: {PAIRS} row pairs (rows {Y0R}-{Y1R}), {N} columns per half, both "
            "halves, one input. ")
    desc = (head + "Every x-band runs on the back side of the door plane (door16_band_kick2's self-reversing "
            "bands, slime and honey alternating by pair), so the front hallway plane and its walls, floor and ceiling "
            "never see a machine; the front ring is quartz and never moves. Storage as door16_quart_pairs (ZB, ZA); "
            "controller after door16_full's (logic core, counter, ladder, master bulbs, routed lines) with new x-band "
            "ends: kick hopper in the cell O watches, spit hopper in the cell the door-plane observer watches, hold "
            "repeater into the upper door piston from the front side inside the wall, and the odd band's home sensor "
            "watching its O through an arrival filter (merge repeater, bulb, torch, bulb, relay). Generator: "
            "scripts/door16/pairs_ctrlq.py.")
    if '--compact' in sys.argv:
        meas = sys.argv[sys.argv.index('--measured') + 1] if '--measured' in sys.argv else 'door_cycle pending'
        desc = (f"door16_quart compacted ({meas}): the same 16x16 QUART door, machines and logic, with the "
                "controller packed toward the machines' footprint. The spit ladder is split in two four-rung halves "
                "either side of its master bulb (clock_burst_split_ladder), so it no longer reaches 20 blocks past the "
                "odd bands; each ZA spit line's extra delay is a packed observer path beside its first tap "
                "(delay_observer_cube, observer_chain_pulse_merge: a 2 gt pulse stays one 2 gt pulse) instead of a "
                "13-block hairpin; the hold taps are two-row folds level with the hold master (delay_serpentine's "
                "fold) instead of 14-block lines; the K_Z and even ZB spit lines are shorter (the K_Z lock is still "
                "tuned to open 4 gt before GZ), the odd arrival filter sits 6 blocks east, the second close pulse's "
                "snake is shorter and bulb B's parity pulse runs through a short snake of its own (both keep door16_quart's close "
                "windows), and the store and kick lines keep routes pinned from an earlier build. Every timing target of "
                "door16_quart is kept (spits R+56+10j, holds R+138..R+178, close kick 34/20 gt after the close spits). "
                "Nothing stands in the doorway's prism (the even ZB sensor line is folded west of x 13). Generator: "
                "scripts/door16/pairs_ctrlq.py --compact.")
        if ctrlq.COMPACT['odd_south']:
            desc += (" The odd bands' spit and hold lines run south along z beside the band instead of out west, "
                     "which takes the build from 96 to 74 blocks wide; the hold line's turn into its column is placed "
                     "by hand, since the router never lays a block beside the spit line.")
        if -7 not in ctrlq.L3.ROWS:
            desc += (" The bottom routing row is gone: the close kick's and second close pulse's snakes sit in the rows "
                     "above it, bulb B's pulse needs no snake of its own, the routes keep off the input feed, and every "
                     "route that never used that row is kept (pin_v3.pkl). The input feed still needs its supports one "
                     "below the lever cell, so this frees one layer, and the controller no longer reaches the outermost "
                     "column on each side: 72x29x45. Open, store and hold timings and the close kick are unchanged, "
                     "bulb B's second toggle too; the second close spit comes 6 gt earlier and the rebuild after the "
                     "ZB arrival 2 gt earlier.")
    if COLOUR:
        key = '; '.join(f"{c[0].replace('_', ' ')}: {' '.join(w for w in c[1:] if w)}" for c in colourq.CLASSES.values())
        desc += (" Colour key (plain stone recoloured to concrete by circuit, traced by redstone.circuits from the "
                 "generator's components; legend signs north of the input repeater): " + key +
                 "; slime and honey are the band machines, quartz the door, stacks and front ring, and the stone "
                 "left is support that carries no signal and holds up nothing.")
    text = (f"name: {NAME}\ndescription: \"{desc}\"\ntraits: [piston_based, entityless]\nupdate_pass: strict\n"
            f"palette:\n{palette()}layers:\n{layers()}{door()}tests:\n" +
            ''.join(f"- name: {n}\n  steps:\n{s}" for n, s in tests) + DOOR_TEST)
    OUT.write_text(text)
    print(OUT, 'size', [hi[i] - lo[i] + 1 for i in range(3)], 'shift', SH, 'IL', sp(IL), 'cells', len(grid))
    print('timing', TIMES)
    if COLOUR:
        for k in ('stones', 'traced', 'how', 'recoloured', 'kept', 'obsidian', 'disagree'):
            print(k, dict(CREPORT[k]) if hasattr(CREPORT[k], 'items') else CREPORT[k])
        print('shared', CREPORT['shared_cells'])
