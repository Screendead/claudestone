"""CPU4 compact two-phase clock: a folded repeater ring, start once, COM and CAP forever.

The ring has two nodes, X (COM) and Y (CAP), two cells apart on the north face. The chain
X -> Y has cap_at gt of delay and Y -> X the rest of the period. The longer chain (S) is a
rectangle loop on a sheet at y=3 over roof blocks, its ends coming down to X and Y by dust
stairs; the shorter one (F) is a hairpin on the ground between X and Y. Every ring cell is a
repeater except corners and nodes, so the delays are exact; the generator adds up the delays of
the built blocks and fails if they are not period and cap_at. The start logic (a two-repeater
memory, an armed repeater and a subtract comparator that turns the memory's rising edge into
one `width` gt pulse) is on the ground west of X and injects through X's stair block.
"""

import sys
from pathlib import Path

from redstone.build import Build
from redstone.fileformat import Spec, dump

SOLID = "white_concrete"
WIRE = "redstone_wire"
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
FLOW = {(0, -1): "north", (0, 1): "south", (1, 0): "east", (-1, 0): "west"}

CX = 4                       # COM pin x; CAP is CX + 2
SR_DELAY = 3                 # start repeater: stretches a 2 gt start to 6 gt, longer than the memory loop
CHUNK = 100                  # wave steps stay short: spec.status puts the whole step on a sign


def split_units(units, n):
    """n repeater delays in 1..4 that add up to `units`."""
    if not n <= units <= 4 * n:
        raise ValueError(f"{units} delay units do not fit {n} repeaters")
    base, rem = divmod(units, n)
    return [base + 1] * rem + [base] * (n - rem)


def sheet_path(a, b, zb):
    """Cells (x, z) of the sheet loop from the stair top above X's west stair to the one above
    Y's east stair, going west, south, east, north and west again."""
    xl, xr = CX - 2 - a, CX + 4 + b
    p = [(x, 2) for x in range(CX - 2, xl - 1, -1)]
    p += [(xl, z) for z in range(3, zb + 1)]
    p += [(x, zb) for x in range(xl + 1, xr + 1)]
    p += [(xr, z) for z in range(zb - 1, 1, -1)]
    p += [(x, 2) for x in range(xr - 1, CX + 3, -1)]
    return p


def corner_cells(p):
    turns = {p[0], p[-1]}
    for i in range(1, len(p) - 1):
        if (p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) != (p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]):
            turns.add(p[i])
    return turns


# Ground cells that hold dust under the sheet's reach: sheet dust powers the roof under it, and a
# roof powers dust below it. START_DUST are the start logic's dust cells.
START_PIN = (0, 9)           # nothing may sit above a pin cell: a powered roof would feed the integrator's dust there
START_DUST = {(0, 7), (2, 7), (2, 6), (0, 6), (0, 3), (0, 4), (1, 4), (2, 4), (3, 4)}


def choose_sheet(n_min, n_max, ground_dust):
    best = None
    for a in range(0, CX - 1):
        for b in range(0, 4):
            for zb in range(4, 14):
                p = sheet_path(a, b, zb)
                n = len(p) - len(corner_cells(p))
                if n_min <= n <= n_max and not corner_cells(p) & ground_dust and START_PIN not in p:
                    w, d = CX + 5 + b, max(zb + 1, 10)
                    key = (max(w - 10, 0) + max(d - 10, 0), w * d, n)
                    if best is None or key < best[0]:
                        best = (key, a, b, zb, n)
    if best is None:
        raise ValueError("no sheet loop fits")
    return best[1:]


def rep_state(flow, delay):
    return f"repeater[facing={OPP[flow]},delay={delay}]"


def build(period, cap_at, width, mutant):
    if period % 2 or cap_at % 2 or width % 2:
        raise ValueError("period, cap_at and width must be even")
    if not 60 <= period <= 200 or not 20 <= cap_at <= period - 30 or not 8 <= width <= 16:
        raise ValueError("period 60..200, 20 <= cap_at <= period - 30, width 8..16 (a delay-4 repeater stretches a shorter pulse)")
    u1, u2 = cap_at // 2, (period - cap_at) // 2          # delay units (2 gt) of X -> Y and Y -> X
    s_first = u1 >= u2                                    # chain 1 on the sheet, chain 2 the hairpin
    u_s, u_f = (u1, u2) if s_first else (u2, u1)
    n_f = max(5, -(-u_f // 4))                            # five: a shorter hairpin's corner touches the start logic
    n_f += (n_f + 1) % 2                                  # a hairpin holds an odd number of repeaters
    zf = (n_f - 1) // 2 + 3                               # its bottom row
    ground_dust = START_DUST | {(CX, 2), (CX + 2, 2), (CX, zf), (CX + 2, zf)}
    a, b, zb, n_s = choose_sheet(-(-u_s // 4), u_s, ground_dust)
    d_s, d_f = split_units(u_s, n_s), split_units(u_f, n_f)

    blocks, names, outputs = {}, {}, {}

    def put(x, y, z, state, name=None, out=False):
        if (x, y, z) in blocks and blocks[(x, y, z)] != state:
            raise ValueError(f"overlap at {(x, y, z)}: {blocks[(x, y, z)]} vs {state}")
        blocks[(x, y, z)] = state
        if name:
            (outputs if out else names)[name] = (x, y, z)

    def rep(x, y, z, flow, d, name=None):
        put(x, y, z, rep_state(flow, d), name)

    def dust(x, y, z, name=None):
        put(x, y, z, WIRE, name)

    # pins, taps, nodes
    for n, x in (("com", CX), ("cap", CX + 2)):
        put(x, 1, 0, WIRE, n, True)
        rep(x, 1, 1, "north", 1)
    dust(CX, 1, 2, "com_node")
    dust(CX + 2, 1, 2, "cap_node")

    # hairpin cells from X down to Y, dust at the nodes and the bottom corners
    down = [(CX, 1, z) for z in range(2, zf)] + [(CX, 1, zf), (CX + 1, 1, zf), (CX + 2, 1, zf)] \
        + [(CX + 2, 1, z) for z in range(zf - 1, 1, -1)]
    f_dust = {down[0], down[-1], (CX, 1, zf), (CX + 2, 1, zf)}
    # sheet cells; stair tops and corners are dust
    path = [(x, 3, z) for x, z in sheet_path(a, b, zb)]
    s_dust = {(x, 3, z) for x, z in corner_cells([(p[0], p[2]) for p in path])}

    chains = {}
    for key, cells, dset, delays in (("f", down if not s_first else down[::-1], f_dust, d_f),
                                     ("s", path if s_first else path[::-1], s_dust, d_s)):
        reps = [c for c in cells if c not in dset]
        assert len(reps) == len(delays), (key, len(reps), len(delays))
        chains[key] = []
        for c in cells:
            if c in dset:
                dust(*c)
        for c, d in zip(reps, delays):
            nxt = cells[cells.index(c) + 1]
            chains[key].append((c, FLOW[(nxt[0] - c[0], nxt[2] - c[2])], d))
    chain1, chain2 = (chains["s"], chains["f"]) if s_first else (chains["f"], chains["s"])
    if mutant == "ring":
        c, f, d = chain2[0]
        chain2[0] = (c, f, d - 1)
    for ch in (chain1, chain2):
        for c, f, d in ch:
            rep(*c, f, d)
    for c in path:
        put(c[0], 2, c[2], SOLID)

    # stairs: X west, Y east
    for sx, dx in ((CX, -1), (CX + 2, 1)):
        put(sx + dx, 1, 2, SOLID)
        dust(sx + dx, 2, 2)
        put(sx + 2 * dx, 2, 2, SOLID)

    # start logic, west of X
    put(0, 1, 9, "air", "start")
    rep(0, 1, 8, "north", SR_DELAY)
    dust(0, 1, 7, "run")
    rep(1, 1, 7, "east", 1)
    dust(2, 1, 7)
    dust(2, 1, 6)
    rep(1, 1, 6, "west", 1)
    dust(0, 1, 6)
    rep(0, 1, 5, "north", 1, "armed")
    for x in range(CX):
        dust(x, 1, 4)
    dust(0, 1, 3)
    w = split_units(width // 2, 1 if width // 2 <= 4 else 2)
    if len(w) == 1:
        dust(1, 1, 3)
    for i, d in enumerate(w):
        rep(CX - 1 - len(w) + i, 1, 3, "east", d)
    put(CX - 1, 1, 3, f"comparator[facing=south,mode=subtract]", "pulse")

    wd = max(x for x, y, z in blocks) + 1
    dp = max(z for x, y, z in blocks) + 1
    for x in range(wd):
        for z in range(dp):
            put(x, 0, z, SOLID)

    sum1 = sum(d for _, _, d in chain1) * 2
    sum2 = sum(d for _, _, d in chain2) * 2
    want = (cap_at, period - cap_at) if mutant is None else (cap_at, period - cap_at - 2)
    if (sum1, sum2) != want:
        raise ValueError(f"ring delays {sum1}+{sum2} gt, wanted {want}")
    info = dict(box=(wd, 4, dp), s_first=s_first, sheet=(a, b, zb, n_s), hairpin=(zf, n_f), chain1=[d for _, _, d in chain1],
                chain2=[d for _, _, d in chain2], sum=(sum1, sum2))
    return blocks, names, outputs, info


def expected(period, cap_at, width, L, t0, n):
    """com and cap strings for ticks t0..t0+n-1 after the first start rise."""
    com = "".join("1" if t >= L and (t - L) % period < width else "0" for t in range(t0, t0 + n))
    cap = "".join("1" if t >= L + cap_at and (t - L - cap_at) % period < width else "0" for t in range(t0, t0 + n))
    return com, cap


def waves(period, cap_at, width, L, t0, n):
    steps = []
    for a in range(t0, t0 + n, CHUNK):
        com, cap = expected(period, cap_at, width, L, a, min(CHUNK, t0 + n - a))
        steps.append({"wave": {"com": com, "cap": cap}})
    return steps


def tests(period, cap_at, width, L, periods):
    quiet = {c: "0" * CHUNK for c in ("com", "cap", "run", "armed", "pulse", "com_node", "cap_node")}
    pulse = [{"drive": {"start": 1}}, {"wait": 2}, {"drive": {"start": 0}}]
    t_ticks = 3 * period + 20
    tl = [(L - 1, {"com": 0, "cap": 0}), (L, {"com": 1, "cap": 0}), (L + width - 1, {"com": 1}),
          (L + width, {"com": 0, "cap": 0}), (L + cap_at - 1, {"com": 0, "cap": 0}), (L + cap_at, {"com": 0, "cap": 1}),
          (L + cap_at + width - 1, {"cap": 1}), (L + cap_at + width, {"com": 0, "cap": 0}), (L + period - 1, None)]
    body, t = [], L - 1
    for when, exp in tl:
        if when > t:
            body.append({"wait": when - t})
        t = when
        if exp:
            body.append({"expect": exp})
    return [
        {"name": "quiet before start", "settle": 0, "steps": [{"wave": quiet}] * 4},
        {"name": "waveform", "steps": pulse + waves(period, cap_at, width, L, 2, t_ticks)},
        {"name": "restart ignored", "steps": pulse + [{"wait": period - 2}] + pulse
         + waves(period, cap_at, width, L, period + 2, 2 * period + 20)},
        {"name": "long run", "steps": pulse + [{"wait": L - 3}, {"repeat": {"times": periods, "steps": body}}]},
    ]


def cpu_clock_compact(name="cpu_clock_compact", period=200, cap_at=150, width=10, mutant=None, periods=40):
    blocks, names, outputs, info = build(period, cap_at, width, mutant)
    b = Build()
    for p in sorted(blocks, key=lambda p: (p[1], p[2], p[0])):
        if blocks[p] != "air":
            b.place(p, blocks[p])
    L = 2 * SR_DELAY + 2 + 2 + 2
    inputs = {"start": names.pop("start")}
    desc = (f"Compact two-phase CPU clock, period {period} gt (library: the ring folded as in "
            f"delay/delay_serpentine, the one-shot as in rising_edge/pulse_rising_comparator, the start memory "
            f"as in d_latch/dl_lock_pair's repeater loop): one start edge sets a two-repeater memory, a subtract "
            f"comparator turns that step into one {width} gt pulse, and the pulse circulates forever in a folded repeater ring "
            f"of {period} gt. COM is the ring node X, CAP the node {cap_at} gt downstream; each pin is fed by one "
            f"repeater, so the two match to the tick. The longer chain runs on a sheet at y=3 over roofs and comes down "
            f"to X and Y by dust stairs, the shorter one is a hairpin on the ground. A second start finds the memory "
            f"set and adds nothing. Box {info['box'][0]}x{info['box'][1]}x{info['box'][2]}: com ({CX},1,0) and cap "
            f"({CX + 2},1,0) on the north face, start (0,1,{info['box'][2] - 1}) on the south face. First COM {L} gt after the start rises.")
    return Spec(name, b, inputs=inputs, outputs=outputs, named={**names, **outputs},
                tests=tests(period, cap_at, width, L, periods), description=desc,
                traits=["comparator_based", "silent", "lightless", "pistonless", "entityless", "tick_accurate"])


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("library/cpu_parts")
    mutant = "--mutant" in sys.argv
    specs = [cpu_clock_compact(), cpu_clock_compact("cpu_clock_compact_p100", 100, 70, periods=20)]
    for s in specs:
        if mutant:
            s = cpu_clock_compact(s.name + "_mutant", **({"period": 100, "cap_at": 70, "periods": 20} if "p100" in s.name else {}), mutant="ring")
        (out / f"{s.name}.redstone.yaml").write_text(dump(s))
        print(s.name, build(*((100, 70) if "p100" in s.name else (200, 150)), 10, None if not mutant else "ring")[3])
