"""The west side's return from blocks (door coords): after the close and with no command after the one falling
input, the trigger chain's west blocks go home: RB12 on K under G, K in and armed as the load leaves it, M_K in,
WK beside K. 34 blocks on top of rbt_drives.py's build, no measured block changed; design_c's opening is the same
at every tick, the close the same to c30 and rbt_drives.py's return of the east side the same to its end in
every cell outside the added ones. Everything printed is COMPUTED on the simulator; nothing here ran on a server.

Not as framed in two ways. RB12 does not go round by (-5,2,2), the route of returns.py's screen: it is pulled one
cell west and pushed back, a kick as RB_T's was, and one push from above then takes G and RB12 down together. And
the closed state is not all restored: G ends at (-4,3,2), where the opening puts it, not at (-3,3,2), which holds
Y12's head while Y12 is out. G's last step belongs to the step that re-arms Y12; until then the gate over L is
open and RB12, home, lights NP12 again.

After   The close leaves RB12 at (-4,3,2) on K's head, G above it at (-4,4,2), K out (RB12 is its payload, two
        above it: QC), M_K out (RB12 beside it) with WK pushed back beside K.
Kick    P_W, a sticky piston at (-6,3,2) facing east, is out in the closed state, its head at (-5,3,2), held by
        RB_W, a redstone block north of it at (-6,3,1). A_W, a sticky piston at (-6,4,1) facing down, pushes RB_W
        down to (-6,2,1) and pulls it back. RB_W's leaving updates P_W inside A_W's event: it retracts and pulls
        RB12 west to (-5,3,2), where it powers nothing. K and M_K, updated by RB12's leaving and unpowered,
        retract in that phase; M_K pulls WK up to (-4,2,1). RB_W's landing back beside P_W updates it: it pushes
        RB12 east again and stays out, as loaded. It is held by a block, not pulsed, so that it never retracts
        with G in front of it (it would pull G west: the what-if below).
M_K     RB12's landing back at (-4,3,2) powers and updates M_K: it pushes WK down. RB12 there powers K again,
        and WK's landing beside K, two ticks after M_K's push, would update K: RB12 must have left by then.
Down    P_G, a sticky piston at (-4,6,2) facing down, over glass SPG (-4,5,2), pushes SPG, G and RB12 down one
        cell: G to (-4,3,2), RB12 to (-4,2,2). RB12's leaving releases M_K two ticks after its push, so M_K
        leaves WK beside K (a sticky piston released within 2 gt of its push leaves the block: P9, F_S) and
        WK's landing finds K unpowered. RB12 lands on K and lights L, which powers K by QC and updates it: its
        push would have to move G, which is still moving, and after that stands under SPG and P_G's head. P_G
        pulls SPG back; K is left powered and not updated under RB12 and G, as the open state has it and as the
        load leaves it under its blocker. P_G stands two above G's cell because the bus's last dust (-4,5,1)
        points into (-4,5,2).
Timer   One pulse, from rbt_drives.py's line. R_W, a 4-tick repeater at (1,10,2), reads the line's dust
        (2,10,2), lit from c26 to c34; R_M (-1,10,2), 4 ticks, is on from c42 d to c50 d. Seven dusts run from
        it west at y 10 and down four stone steps, north of P_G's column and south of the bus's west branch, to
        D_A (-6,6,1), on glass two above A_W: A_W is powered by QC and updated by D_A's change. R_X (-6,6,2),
        4 ticks, reads D_A and powers stone Y_X (-6,6,3); R_G (-5,6,3), 4 ticks, reads Y_X and powers stone Y_G
        (-4,6,3), south of P_G: on from c58 d to c66 d.
Order   c42 A_W out, P_W pulls RB12, K and M_K in. c44 j RB12 at (-5,3,2), WK at (-4,2,1). c50 A_W pulls RB_W
        back, c52 j it lands, c53 P_W out, c55 j RB12 at (-4,3,2). c56 M_K out. c58 P_G out, M_K released: WK
        real at (-4,1,1). c60 j RB12 at (-4,2,2), G at (-4,3,2), L 15. c66 P_G in, c68 j SPG home. The east
        side's return (rbt_drives.py, c34 to c58) is over when RB12 lands: NP12's relight updates W_T, which
        RB_T powers by QC while it stands at (1,6,-1), c42 j to c47 (the control with the line 14 ticks early).
Margin  Each delay moved alone: R_W and R_M 1 to 4 ticks, and together; R_X and R_G 3 or 4 (P_G's push has to
        fall in c56 to c58: after M_K's extension, before WK lands).
Gate    G's closed cell (-3,3,2) is Y12's head: G goes home only when Y12 retracts, and Y12 is held by ARM_Z11
        and RB_D, the relays' step. From c60 j RB12 lights L, the step to H is open, NP12 is lit as in the open
        state, P12 is powered (its push stops on V's head) and A_D is powered and not updated: the relays' step
        starts from that. Y12 made sticky (a measured block; what-if) pulls G home from (-4,3,2) by itself.

Not controls: the nine glass blocks carry dust and repeaters (the simulator has no rule for support).
Run from the repo root (sim; under a minute):
python -m scripts.door2.close_layout.west_drives > scripts/door2/close_layout/west_drives.txt"""
import copy, re
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, p10_v as pv, returns as r, rbt_drives as rd, dp_off as o
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, DIRS, add

K, K_UP, WK, M_K, M_HEAD = t.K, r.RB12_HOME, t.WK, t.M_K, (-4, 2, 1)   # K_UP: K's head cell, RB12's closed cell
UP, G_UP, G_HOME, Y12, L = t.RB12_UP, t.G_UP, (-3, 3, 2), (-2, 3, 2), (-3, 2, 2)
P_W, HEAD_W, RB_W, A_W, PARK_W = (-6, 3, 2), (-5, 3, 2), (-6, 3, 1), (-6, 4, 1), (-6, 2, 1)   # HEAD_W is where RB12 parks
P_G, SPG = (-4, 6, 2), (-4, 5, 2)
R_W, R_M = (1, 10, 2), (-1, 10, 2)
LINE = ((0, 10, 2), (-2, 10, 2), (-2, 10, 1), (-2, 10, 0), (-3, 9, 0), (-4, 8, 0), (-5, 7, 0), (-6, 6, 0), (-6, 6, 1))
STEPS = ((-2, 9, 0), (-3, 8, 0), (-4, 7, 0), (-5, 6, 0))            # stone under a dust that the next one reads down a step
D_A = LINE[-1]
R_X, Y_X, R_G, Y_G = (-6, 6, 2), (-6, 6, 3), (-5, 6, 3), (-4, 6, 3)
TAPPED = rd.CLIMB[6]                                                # (2,10,2), the dust of rbt_drives' line that R_W reads
LAST = 70                                                           # the runs end after c70
LO, HI = (-6, -3, -8), rd.HI                                        # the box with these blocks: two cells further west
V_HEAD, P12 = (0, 3, 0), (0, 5, 0)
ARM_Z11 = (-2, 4, 2)

rep = rd.rep
KICK = {P_W: t.pis("sticky_piston", "east", "P_W", True), HEAD_W: B("piston_head", facing="east", sticky=True),
        RB_W: B("rb", id="RB_W"), A_W: t.pis("sticky_piston", "down", "A_W")}
DOWN = {P_G: t.pis("sticky_piston", "down", "P_G"), SPG: B("glass", id="SPG")}
REPEATERS = {R_W: rep("east", 4), R_M: rep("east", 4), R_X: rep("north", 4), R_G: rep("west", 4)}
STONES = {**{c: t.STONE for c in STEPS}, Y_X: t.STONE, Y_G: t.STONE}
DUSTS = {c: t.DUST for c in LINE}
GLASSES = {(x, y - 1, z): t.GLASS for x, y, z in (*REPEATERS, *LINE) if (x, y - 1, z) not in STEPS}
TIMER = {**REPEATERS, **STONES, **DUSTS, **GLASSES}
MINE = {**KICK, **DOWN, **TIMER}
NAMES = {R_W: "R_W", R_M: "R_M", R_X: "R_X", R_G: "R_G", Y_X: "Y_X", Y_G: "Y_G", D_A: "D_A", LINE[0]: "the dust R_W lights",
         **{c: f"the step stone {c}" for c in STEPS}, **{c: st.p["id"] for c, st in {**KICK, **DOWN}.items() if "id" in st.p}}
MY_PISTONS = {st.p["id"]: c for c, st in MINE.items() if st.n in ("piston", "sticky_piston")}
MOVED = (PARK_W,)                                                   # the free cell the added blocks move through: RB_W's
WEST = (K, K_UP, G_UP, M_K, M_HEAD, WK)                             # trigger.py's cells that end as loaded; UP ends with G in it
COLUMN = (*WEST, UP)                                                # the cells of the earlier steps that this return moves
CELLS = list(dict.fromkeys([*WEST, *MINE, *MOVED]))
SHOW = (*rd.SHOW, *(f"repeater {c} " for c in REPEATERS), *(f"land rb@{c}" for c in (HEAD_W, UP, K_UP, PARK_W, RB_W)),
        f"land stone@{UP}", f"land glass@{M_HEAD}", f"land glass@{WK}", f"land glass@{G_UP}", f"land glass@{SPG}")
SEEN = (*MY_PISTONS, "K", "M_K")


def build(drop=(), swap=None):
    """rbt_drives.py's build with the 34 blocks; `drop` leaves cells out (P_W's head with P_W), `swap` replaces or
    adds some."""
    b = rd.build()
    drop = (*drop, HEAD_W) if P_W in drop else drop
    for c, st in {**MINE, **(swap or {})}.items():
        if c not in drop:
            assert c in (swap or {}) or c not in b.b, c
            b.b[c] = st
            b.role[c] = "west_drives"
    return b


class Noted(rd.Noted):
    """rbt_drives' Noted with this step's lines; `late` (tick, cell) puts that cell's block events behind those
    queued in phase d of that tick (sim only)."""
    late = None

    def L(self, msg):
        World.L(self, msg)
        if any(x in msg for x in SHOW):
            self.lines.append((self.tick_no, self.phase, self.cur if self.phase == "g" and self.seen is not None else None, msg))

    def repeater_tick(self, p):
        rd.Noted.repeater_tick(self, p)
        if self.late and self.tick_no == self.late[0]:
            for key in [k for k in self.events if k[0] == self.late[1]]:
                self.events.move_to_end(key)


def noted(w, ticks=None, first=-1, before=None, late=None, **kw):
    """rbt_drives.noted with this module's Noted: a copy of w taken through ticks (each: its commands, then the
    tick; default: the input off, then nothing to c`LAST`), with the shown lines, K's updates while it is in and
    (blocks, moving cells) after each tick. `before` {tick number: function of the world} acts ahead of that tick,
    `late` is Noted.late (both sim only)."""
    w = copy.deepcopy(w)
    w.__class__ = Noted
    w.reverse, w.ia_last, w.first, w.backwards, w.late = kw.get("reverse", False), kw.get("ia_last", False), None, kw.get("backwards", False), late
    w.lvl, w.order, w.seen, w.after, w.said, w.lines, w.noted, w.fed, w.power, w.frames = {}, [], None, None, [], [], [], [], [], []
    w.reached, w.woke, w.held = {}, {"P8": [], "P9": [], "A_9": [], "K": []}, []
    for k, cmds in enumerate(pp.idle(LAST) if ticks is None else ticks):
        w.log.clear()
        w.tick_no = k + first
        for c, blk in cmds:
            w.cmd_set(c, blk)
        if before and w.tick_no in before:
            before[w.tick_no](w)
        w.tick()
        w.frames.append((dict(w.b), set(w.be)))
    return w


def verdict_west(w, cl):
    """what keeps the west side from the loaded closed state `cl`: K, its head cell with RB12 in it, M_K and its
    head cell, WK, the cell above G's and the added blocks, cell for cell; K, M_K and the added pistons from the
    closed state's power; L from its level; and G from (-4,3,2), where the opening puts it (its closed cell is
    Y12's head: not this step's). Empty when the return is done."""
    bad = [f"{c} {'moving' if c in w.be else w.get(c)}" for c in CELLS if c in w.be or pp.bare(w.get(c)) != pp.bare(cl.get(c))]
    bad += [f"{st.p['id']} powered by {[x for _, x in power_sources(w, c)]}" for c, st in cl.b.items()
            if c in CELLS and st.n in ("piston", "sticky_piston") and pp.bare(w.get(c)) == pp.bare(st) and power_sources(w, c) != power_sources(cl, c)]
    bad += [f"G {t.at(w, 'G')[:2]}"] * (t.at(w, "G")[:2] != (UP, "real")) + [f"L {w.get(L).p['power']}"] * (w.get(L).p["power"] != cl.get(L).p["power"])
    return bad


def verdict(w, cl):
    """verdict_west and rbt_drives' verdict (the east side, the S feed's cut, the door plane, nothing moving)."""
    return verdict_west(w, cl) + rd.verdict(w, cl)


def run(b, ticks=None, opened=None, **kw):
    """b opened from the input and taken through the close and the returns: (closed state, noted world, verdict)."""
    cl = d.make_world(b)[0]
    w = noted(t.opened(b)[0] if opened is None else opened, ticks, **kw)
    return cl, w, verdict(w, cl)


def west_line(x):
    """whether a told line is this step's: its pistons, K or M_K, its repeaters, a landing west of x -3."""
    return any(f" {n}@" in x for n in SEEN) or any(f"repeater {c} " in x for c in REPEATERS) or \
        (" land " in x and int(x.split("@(")[1].split(",")[0]) <= -4)


def said(w, first=2, last=LAST):
    return [x for x in pv.told(w) if first <= pv.tick_of(x) <= last and west_line(x)]


def where(w):
    return ", ".join(f"{n} {t.at(w, n)[0]}" + {True: " out", False: " in", None: ""}[t.at(w, n)[2]]
                     for n in ("RB12", "G", "K", "M_K", "WK", "P_W", "RB_W", "A_W", "P_G", "SPG"))


def k_updates(w, first, last=LAST):
    """K's updates while it is in: tick and phase, powered or not, free to push or blocked."""
    return "; ".join(dict.fromkeys(f"c{k}{ph} " + ("powered" if on else "not powered") + (", free" if ok else ", blocked")
                                   for k, ph, on, ok in w.woke["K"] if first <= k <= last)) or "none"


def frames(b, last=LAST):
    """what moved during the load, then (blocks, moving cells) after each tick of the opening and of the close and
    the returns to c`last`."""
    w, moved = d.make_world(b)
    yield moved
    w.run(4)
    w.cmd_set(f.DRIVER, t.RB)
    for k in range(t.OPEN_TICKS + last + 2):
        if k == t.OPEN_TICKS:
            w.cmd_set(f.DRIVER, AIR)
        w.tick()
        yield dict(w.b), set(w.be)


def tick_key(x):
    return (0 if x[0] == "t" else 1000) + int(x[1:])


def against(b, ref, skip=()):
    """b beside the frames `ref` of rbt_drives.py's build: what moved during the load, and for each cell outside
    `skip` that differs at any tick, the first tick at which it does."""
    g = frames(b)
    moved, first = next(g), {}
    for k, ((bl, be), (rb, rbe)) in enumerate(zip(g, ref)):
        for c in (set(bl) | set(rb) | be | rbe) - set(skip):
            if (bl.get(c) != rb.get(c) or (c in be) != (c in rbe)) and c not in first:
                first[c] = r.tick_name(k)
    return moved, first


def differs(first, upto=None):
    """the ticks in against()'s result, in order; `upto` n keeps those of the opening and of the close to c<n>."""
    return sorted({x for x in first.values() if upto is None or tick_key(x) <= 1000 + upto}, key=tick_key)


def west_reversed(w):
    """before a tick: the moving blocks west of x -3 are put in reverse order among themselves (sim only)."""
    idx = [i for i, be in enumerate(w.tickers) if not be.removed and be.pos[0] <= -4]
    for i, be in zip(idx, [w.tickers[i] for i in reversed(idx)]):
        w.tickers[i] = be


def bare_events(w):
    """the piston events of each tick with the three redstone blocks' labels (and TM's and TR's) taken out."""
    return [[re.sub(r"(RB_ST|RB_1|RB_2|TM|TR)@", "@", m) for m in tick] for tick in pv.per_tick(w, -1, LAST)]


def second(b, w, cl):
    """the world after the returns with every other cell set back as loaded, without updates (a stand-in for the
    returns not designed), opened again: the cells set back, the ticks at which the second opening differs from
    the first, labels apart, and the second close and returns."""
    x = copy.deepcopy(w)
    x.__class__ = World
    back = [c for c in set(cl.b) | set(x.b) if pp.bare(cl.get(c)) != pp.bare(x.get(c))]
    for c in back:
        x.cmd_set_silent(c, cl.get(c))
    a, _ = d.make_world(b)
    for y in (a, x):
        y.run(4)
        y.cmd_set(f.DRIVER, t.RB)
    differ = []
    for k in range(t.OPEN_TICKS):
        a.tick()
        x.tick()
        differ += [f"t{k - 1}"] * (set(a.be) != set(x.be) or {c: pp.bare(st) for c, st in a.b.items()} != {c: pp.bare(st) for c, st in x.b.items()})
    return back, differ, noted(x)


def escapes(piston, facing):
    """for each cell beside a piston from which a redstone block powers it: the neighbour cells into which one push
    takes the block out of every cell that powers the piston (its own neighbours and the QC cells)."""
    near = [add(piston, dv) for dv in DIRS.values() if dv != DIRS[facing]]
    qc = [add(add(piston, DIRS["up"]), dv) for dv in DIRS.values() if dv != DIRS["down"]]
    return {c: [x for x in (add(c, dv) for dv in DIRS.values()) if x != piston and x not in near and x not in qc] for c in near}


def after(w, cmds, ticks=8):
    """a plain copy of the world after the returns, with commands (cell, block, with updates or not) and then
    `ticks` ticks: (world, its piston events and landings)."""
    x = copy.deepcopy(w)
    x.__class__ = World
    x.log.clear()
    t0 = x.time
    for c, st, loud in cmds:
        (x.cmd_set if loud else x.cmd_set_silent)(c, st)
    x.run(ticks)
    return x, [f"+{tm - t0}{ph} {m.split(':')[0] if 'RETRACT' in m and 'PULL' not in m else m}" for tm, ph, m in x.log
               if any(k in m for k in ("EXTEND", "RETRACT", "land rb", "land stone"))]


# name: (title, build keywords)
EARLY = {R_M: t.DUST, R_W: rep("east", 1)}
CONTROLS = {
    "no R_W": ("nothing reads rbt_drives' line: nothing starts in the west", dict(drop=(R_W,))),
    "no A_W": ("RB_W stays beside P_W: no kick", dict(drop=(A_W,))),
    "A_W not sticky": ("RB_W is left at (-6,2,1): P_W stays in and RB12 at (-5,3,2), WK at (-4,2,1)", dict(swap={A_W: t.pis("piston", "down", "A_W")})),
    "no RB_W": ("nothing holds P_W: built out, it retracts in the load", dict(drop=(RB_W,))),
    "P_W not sticky": ("it pulls nothing: RB12 stays on K's head", dict(swap={P_W: t.pis("piston", "east", "P_W", True),
                                                                             HEAD_W: B("piston_head", facing="east", sticky=False)})),
    "no P_G": ("RB12 stays at (-4,3,2): WK's landing updates K, which RB12 powers again, and K goes out", dict(drop=(P_G,))),
    "no R_X": ("the same: nothing reaches P_G", dict(drop=(R_X,))),
    "no Y_X": ("the same", dict(drop=(Y_X,))),
    "no R_G": ("the same", dict(drop=(R_G,))),
    "no Y_G": ("the same: R_G points into air beside P_G", dict(drop=(Y_G,))),
    "no SPG": ("P_G's head stops a cell short of G", dict(drop=(SPG,))),
    "P_G not sticky": ("SPG is left at (-4,4,2)", dict(swap={P_G: t.pis("piston", "down", "P_G")})),
    "R_X and R_G both at 3 ticks": ("R_G is on at c54 d, with RB12 still moving into (-4,3,2): P_G's push fails and nothing updates it",
                                    dict(swap={R_X: rep("north", 3), R_G: rep("west", 3)})),
    "the line 14 ticks early (R_M a dust, R_W at 1 tick)": (
        "RB12 lands on K at c46 j, with RB_T at (1,6,-1): NP12's relight updates W_T, which RB_T powers by QC, and W_T's head takes RB_T's "
        "closed cell", dict(swap=EARLY)),
}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    r.worlds()
    rb = rd.build()
    ref = list(frames(rb))[1:]
    rcl, rw, rbad = rd.run(rb, ticks=pp.idle(LAST))
    assert not rbad
    b = build()
    kinds = [st.n for st in MINE.values()]
    print(f"added: {len(MINE)} blocks ({kinds.count('sticky_piston')} sticky pistons, one of them built out with its head, {kinds.count('rb')} redstone "
          f"block, {kinds.count('repeater')} repeaters, {kinds.count('redstone_wire')} dust, {kinds.count('stone')} stone, {kinds.count('glass')} glass: "
          f"SPG and {len(GLASSES)} under dust and repeaters); no measured block changed; no stand-in, no command after the input")
    taken = set(d.full_blocks(rb)) | set(rcl.b) | set(v.cumulative_cells(rb)[0])
    for blocks, be in (*ref, *rw.frames):
        taken |= set(blocks) | be
    print("added blocks in cells that rbt_drives.py's build fills at any tick of the opening, of the close or of its return, or on the door plane "
          "or in the hallway:", ", ".join(f"{NAMES.get(c, c)} {c}" for c in MINE if c in taken or r.plane_or_hall(c)) or "none")
    moved, first = against(b, ref, set(MINE) | set(MOVED))
    print("moved during load:", moved or "none", "| the opening and the close to c30 outside the added blocks:",
          f"differ at {differs(first, 30)}" if differs(first, 30) else "the same at every tick")
    g = frames(b)
    next(g)
    early = sorted({NAMES.get(c, str(c)) for k, (bl, be) in enumerate(g) if k < t.OPEN_TICKS + r.CLOSE for c in (*MINE, *MOVED)
                    if c in be or bl.get(c, AIR) != MINE.get(c, AIR)})
    print("   added cells that are not as loaded after any tick of the opening or of the close to c30:", ", ".join(early) or "none")
    names = {**NAMES, o.TAP: "the DP tap's dust", o.R_D: "the tap's repeater", L: "L"}
    np12 = [c for c, ro in b.role.items() if ro == "NP12"]
    by_tick = {}
    for c, k in sorted(((c, k) for c, k in first.items() if c not in COLUMN), key=lambda x: (tick_key(x[1]), x[0])):
        by_tick.setdefault(k, []).append(f"NP12's dust {c}" if c in np12 and c != L else names.get(c, str(c)))
    print(f"   c31 to c{LAST} against rbt_drives.py's build, cells outside the added blocks that differ: the west column's seven (K, its head cell, "
          "(-4,3,2), (-4,4,2), M_K, its head cell, WK's) from", min((first[c] for c in COLUMN), key=tick_key) + ";",
          "; ".join(f"from {k}: " + ", ".join(ns) for k, ns in by_tick.items()) or "no other", "| every other cell is the same at every tick")
    cells = set(v.cumulative_cells(b)[0])
    cl, w, bad = run(b)
    for blocks, _ in w.frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print("box, opening + close + returns:", t.s.box(cells))
    pw = rd.powered(b, list(MY_PISTONS.values()))
    print("added pistons powered, closed state, opening and close to c30:", "; ".join(
        f"{n} " + ("in the closed state and after every tick, by " + ", ".join(NAMES[x] for _, x in power_sources(cl, c))
                   if len(pw[c]) == t.OPEN_TICKS + r.CLOSE + 1 else rd.spans(pw[c])) for n, c in MY_PISTONS.items()))
    op, _ = t.opened(b)
    print("open state: P_W", t.at(op, "P_W")[1:], "| G", t.at(op, "G")[0], "| SPG", t.at(op, "SPG")[0], "| the four repeaters on:",
          [NAMES[c] for c in REPEATERS if op.get(c).p["powered"]] or "none", "| the line's dust lit:", [c for c in DUSTS if op.get(c).p["power"]] or "none")
    print("where RB_W can stand: each cell beside P_W, and the cells one push takes a redstone block to from there in which it no longer powers P_W:",
          "; ".join(f"{c}: " + (", ".join(map(str, e)) or "none (every neighbour is a QC cell)") for c, e in escapes(P_W, "east").items()))

    print(f"\n== the close and the returns from the input, no command: c-1 to c{LAST}")
    mine_ev, ref_ev = pv.per_tick(w, -1, LAST), pv.per_tick(rw, -1, LAST)
    same = next(n for n in range(-1, LAST + 1) if mine_ev[n + 1] != ref_ev[n + 1])
    east = [x for x in pv.told(w) if pv.tick_of(x) >= same and not west_line(x)] == [x for x in pv.told(rw) if pv.tick_of(x) >= same]
    print(f"   c-1 to c{same - 1}: the piston events of rbt_drives' run, tick by tick; from c{same} the east side's lines are",
          "rbt_drives.txt's" if east else "NOT rbt_drives.txt's", "and the west's are:")
    print("\n".join("   " + x for x in said(w, 26)))
    print("   ->", "FAILS: " + "; ".join(bad) if bad else "done: RB12 at (-4,2,2) on K, L 15; K in, powered by L (QC) and not updated, as loaded; M_K in and "
          "unpowered, WK at (-4,1,1); G at (-4,3,2), (-4,4,2) empty; P_W out, held by RB_W; A_W and P_G in and unpowered, SPG at (-4,5,2), the "
          "repeaters off, the line dark; the east side as rbt_drives.py leaves it; the door plane closed; nothing moving")
    print("   ", where(w))
    parked = noted(t.opened(b)[0], pp.idle(46))
    print("   RB12 parked at (-5,3,2), after c46: pistons it powers:", [st.p.get("id", str(c)) for c, st in parked.b.items()
                                                                       if st.n in ("piston", "sticky_piston") and HEAD_W in [x for _, x in power_sources(parked, c)]] or "none",
          "| K powered by", [x for _, x in power_sources(parked, K)] or "nothing", "| M_K by", [x for _, x in power_sources(parked, M_K)] or "nothing",
          "| WK", t.at(parked, "WK")[0])
    print("   K's updates while it is in, c56 to the end:", k_updates(w, 56))
    rest, dust = pv.differing(cl, w)
    off = [x for x in rest if not any(x.startswith(str(c) + ":") for c in (*pp.PLANE, t.RB_ST, rd.RB_1, rd.RB_2))]
    left = [n for n in r.GROUPS[0][1] + ("K", "M_K", "RB12") if t.at(cl, n) != t.at(w, n)]
    gate = [x for x in off if x.startswith(str(o.R_D) + ":")]
    print(f"   cells outside the door plane that still differ from the closed state: {len(off)} ({len(off) - len(gate)} without the tap's repeater; 28 "
          "before this step):", ", ".join(left), "(the opening's seven relays with their blocks, and G: at (-4,3,2), its closed cell holds Y12's head)",
          f"and the DP tap's repeater {o.R_D}, on" * bool(gate))
    print("   dust that the open gate lights (0 in the closed state):", ", ".join(
        f"{'TAP ' if c == o.TAP else ''}{c} {w.get(c).p['power']}" for c in sorted(dust) if c in np12 or c == o.TAP))
    odd = {st.p["id"]: [x for _, x in power_sources(w, c)] for c, st in sorted(w.b.items()) if st.n in ("piston", "sticky_piston") and "id" in st.p
           and c not in COLUMN and pp.bare(st) == pp.bare(rw.get(c)) and power_sources(w, c) != power_sources(rw, c)}
    print("   pistons outside the west column powered otherwise than after rbt_drives' return:", odd, "(P12 by NP12's dust on and beside it, "
          "A_D by the tap's stone, QC: powered and not updated, as in the open state) | P12's push:",
          "free" if w.resolve(P12, DIRS["down"], True)[0] else f"stops on V's head in {V_HEAD}, under SP", "| A_D", t.at(w, "A_D")[1:])
    print("   piston events against rbt_drives' run:", sum(len(set(a) - set(c)) for a, c in zip(mine_ev, ref_ev)), "added,",
          "none taken away" if all(set(c) <= set(a) for a, c in zip(mine_ev, ref_ev)) else "SOME TAKEN AWAY")
    lv = {}
    for k, (blocks, _) in enumerate(w.frames):
        for c in (TAPPED, LINE[0], LINE[1], LINE[3], LINE[-2], D_A):
            if blocks[c].p["power"]:
                lv.setdefault(c, [blocks[c].p["power"], k - 1, k - 1])[2] = k - 1
    print("   dust levels while lit:", "; ".join(f"{c} {p} after c{a} to c{z}" for c, (p, a, z) in lv.items()), f"| L {w.get(L).p['power']} from c60")

    print("\n== order (must pass): against the run above")
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)), ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("both", dict(reverse=True, ia_last=True)),
                     ("from c30 on, the scheduled ticks of each tick in reverse order, priorities ignored (the repeaters that tick together)",
                      dict(backwards=True)),
                     ("from c40 on, the moving blocks west of x -3 in reverse order (K's base, WK, M_K's base, P_W's base, RB_W and RB12 at c44 j; RB12 "
                      "and P_W's head at c55 j; RB12, G, SPG, P_G's head and M_K's base at c60 j)", dict(before={k: west_reversed for k in range(40, LAST + 1)}))):
        _, x, badx = run(b, **kw)
        print(f"   {name}:", "FAILS: " + "; ".join(badx[:4]) if badx else "done;", "piston events of each tick",
              "the same set" if pv.per_tick(x, -1, LAST) == mine_ev else "DIFFER")

    print("\n== the four delays, each 1 to 4 ticks with the others as built: the returns, and the close to c30 outside the added blocks")
    for c, st in REPEATERS.items():
        out = []
        for k in (1, 2, 3, 4):
            bk = build(swap={c: rep(st.p["facing"], k)})
            _, x, badk = run(bk)
            dk = differs(against(bk, ref, set(MINE) | set(MOVED))[1], 30)
            ev = {n: next((pv.tick_of(m) for m in said(x, 26) if f"{n}@" in m and ("EXTEND" in m if n == "P_G" else "PULL RB12" in m)), None) for n in ("P_W", "P_G")}
            out.append(f"{k} " + ("FAILS" if badk else "done") + f" (the kick at c{ev['P_W']}, P_G " + (f"out at c{ev['P_G']})" if ev["P_G"] else "never out)")
                       + (f", close differs from {dk[0]}" if dk else ""))
        print(f"   {NAMES[c]} (built {st.p['delay']}):", "; ".join(out))
    both = {(i, j): not run(build(swap={R_W: rep("east", i), R_M: rep("east", j)}))[2] for i in (1, 2, 3, 4) for j in (1, 2, 3, 4)}
    print("   R_W and R_M together, each 1 to 4 ticks (the kick at c30 to c42, RB12 home at c48 j to c60 j):", "done in all 16" if all(both.values()) else
          "FAILS at " + ", ".join(map(str, (k for k, ok in both.items() if not ok))))
    b3 = build(swap={R_G: rep("west", 3)})
    cl3 = d.make_world(b3)[0]
    x = noted(t.opened(b3)[0])
    y = noted(t.opened(b3)[0], late=(56, M_K))
    print("   R_G at 3 ticks: P_G's event, queued in c56 d, runs behind M_K's extension, queued in c55 j (first in, first out):",
          "; ".join(m.split(" ", 1)[1].split(":")[0] for m in said(x, 56, 56)), "| K's updates, c56 to the end:", k_updates(x, 56))
    print("      what-if (sim only), M_K's event behind P_G's:", "FAILS: " + "; ".join(verdict(y, cl3)[:3]) if verdict(y, cl3) else "done", "|", where(y),
          "| built at 4 ticks nothing rests on that order")

    print("\n== controls: one thing changed, the same run")
    for name, (title, bkw) in CONTROLS.items():
        bc = build(**bkw)
        mv = d.make_world(bc)[1]
        dc = differs(against(bc, ref, set(MINE) | set(MOVED) | set(bkw.get("swap", {})))[1], 30)
        _, x, badc = run(bc)
        print(f"   {name}: {title}:", "FAILS: " + "; ".join(badc[:4]) + (" ..." if len(badc) > 4 else "") if badc else "done", "|", where(x),
              "| moved during load:" * bool(mv), ", ".join(m.split("@")[0] for m in mv), f"| opening or close to c30 differ from {dc[0]}" if dc else "")
    xe = run(build(swap=EARLY))[1]
    print("      the line 14 ticks early:", "; ".join(m for m in pv.told(xe) if pv.tick_of(m) in (46, 47) and ("W_T@" in m or f"land rb@{K_UP}" in m)),
          "| RB_T after c46:", t.at(noted(t.opened(build(swap=EARLY))[0], pp.idle(46)), "RB_T")[0])
    bx = build(drop=(P_G,), swap={SPG: t.pis("piston", "down", "X")})
    ox, _ = t.opened(bx)
    print("   a piston in SPG's place, (-4,5,2), facing down (what P_G would be without the spacer): in the closed state powered by",
          [x for _, x in power_sources(d.make_world(bx)[0], SPG)] or "nothing", "| open state:", "out" if t.at(ox, "X")[2] else "in", "powered by",
          [x for _, x in power_sources(ox, SPG)], "(the bus's last dust points into it: it would be out through the open state, its head in "
          "(-4,4,2))")
    work = [c for c in MINE if c not in GLASSES and c != HEAD_W]
    left = {c: bool(run(build(drop=(c,)))[2]) for c in work}
    print(f"   each of the {len(work)} blocks that are not glass under a dust or a repeater (P_W with its head) left out, one at a time:",
          "the return FAILS every time" if all(left.values()) else "done without " + ", ".join(f"{NAMES.get(c, c)} {c}" for c, bad_ in left.items() if not bad_))

    print("\n== the input off n ticks after it went on (trigger.py's feed is armed at t10 j): the close (p9_p8's four verdicts) and the returns")
    dusts = [c for c, st in op.b.items() if st.n == "redstone_wire"]
    res = {}
    for n in (8, 9, 10, 11, 12, 16):
        on, _ = t.opened(b, ticks=n)
        res[n] = ("close FAILS" if any(pp.verdicts(on, dusts, cl)) else "close done") + ", " + ("returns FAIL" if verdict(noted(on), cl) else "returns done")
    print("  ", res)

    back, differ2, y = second(b, w, cl)
    print(f"\n== a second cycle (sim only): after the returns the {len(back)} cells that still differ, labels apart, are set back as loaded without "
          "updates (a stand-in for the returns not designed: the seven relays and G, with the dust and the tap that the open gate lights), and the "
          "input goes on again")
    print("   pending after the first returns: scheduled ticks", w.sched or "none", "| block events", list(w.events) or "none")
    print("   the second opening against the first, every cell, labels apart:", f"differs at {differ2}" if differ2 else "the same at every tick")
    bad2 = verdict(y, cl)
    print("   the second close and returns:", "FAILS: " + "; ".join(bad2[:4]) if bad2 else "done;", "piston events of each tick, labels apart,",
          "the same" if bare_events(y) == bare_events(w) else "DIFFER", "|", where(y))

    zb = build(swap={r.D9: r.D9_BLOCK})
    _, z, badz = run(zb)
    print("\n== with D9, the down-pusher of returns.py's what-if for Z9, built as well (its drives are not designed):", "FAILS" if badz else "done;",
          "piston events of each tick", "the same set" if pv.per_tick(z, -1, LAST) == mine_ev else "DIFFER")

    print("\n== what-ifs (sim only) for the step that takes G home: commands after the returns")
    x, ev = after(w, [(RB_W, AIR, True)])
    print("   P_W released (RB_W taken out): it retracts with G in front of it:", "; ".join(ev), "| G", t.at(x, "G")[0], "| so P_W is held, not pulsed")
    ys = t.pis("sticky_piston", "west", "Y12")
    bs = build(swap={Y12: ys})
    mvs, fs = against(bs, list(frames(b))[1:], {Y12, G_HOME})
    cls, ws, bads = run(bs)
    print("   Y12 a sticky piston (a measured block of design_c): moved during load:", mvs or "none", "| the opening, the close and the returns outside "
          "Y12 and its head:", f"differ at {differs(fs)}" if fs else "the same at every tick,", "the returns", "FAIL" if bads else "done")
    x, ev = after(ws, [(o.RB_D, AIR, False), (ARM_Z11, AIR, True)])
    print("      its two holds taken out, RB_D without updates and ARM_Z11 with:", "; ".join(ev), "| G", t.at(x, "G")[0], "| H", x.get((-3, 3, 3)).p["power"],
          "| the tap's repeater", "on" if x.get(o.R_D).p["powered"] else "off", "| A_D", "out" if t.at(x, "A_D")[2] else "in",
          "(H's death updates A_D while the tap still powers it, as at c0; with RB_D in place it would push it into DP's source cell)")
    x, ev = after(w, [(o.RB_D, AIR, False), (ARM_Z11, AIR, True)])
    print("      Y12 as built, the same commands:", "; ".join(ev), "| G", t.at(x, "G")[0], "| H", x.get((-3, 3, 3)).p["power"],
          "(G stays at (-4,3,2): it needs a mover from the west, where P_W's head stands)")
