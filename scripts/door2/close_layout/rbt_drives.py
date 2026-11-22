"""RB_T's return from blocks (door coords): the commands of returns.py's what-if are gone. From the one falling input
and with no command after it, the trigger chain's east side goes home after the close: RB_T under T, P_R out, K_T
in, SPC and a redstone block in RB_ST's closed cell, the S feed's cut reset. 49 blocks on top of p9_p8.py's build
and one of trigger.py's made sticky (K_T); design_c's opening is the same at every tick and the close the same to
c30 in every cell outside the added ones. Everything printed is COMPUTED on the simulator; nothing here ran on a
server.

Not as framed in three ways. RB_ST does not go home: its route takes eight pistons (rbt_route.py), so a second and
a third redstone block stand between its rest cell and its closed cell and each moves on one place. N_T, the
kicker of returns.py's what-if, which needs a source and two pulses, is not used: the kick is done from above by
U_T, which needs neither. And the drives are not sources with a timing each but one pulse on a line of repeaters.

Route   RB_ST (2,8,0) to (3,7,0), rbt_route.py: a redstone block lights DT at (2,7,0) and the bus at (3,8,0), so
        the two-step ways are closed whatever moves it; the two six-step routes of returns.py's screen take the
        step (3,8,1) to (3,7,1) by a sticky piston facing up, which the block it should pull powers by QC; the
        shortest route that can be built has eight steps and a piston for each.
Loop    RB_1 (3,7,1) and RB_2 (3,8,1), two redstone blocks, stand south of RB_ST's closed cell in the closed
        state. In a return RB_1 goes north into (3,7,0), RB_ST comes round over them, up to (2,9,0), east to
        (3,9,0), south to (3,9,1), and one push down moves it and RB_2 a cell each: RB_2 to (3,7,1), RB_ST to
        (3,8,1). The three end in each other's cells; they are the same block (p9_p8.py's TM and TR do the same).
        Five pistons, one for each straight piece of the way: P_U (2,10,0), sticky, facing down, pulls RB_ST up;
        P_E (4,9,0), sticky, facing west, pulls it east; P_S (3,9,-1) pushes it south; P_D (3,10,1) pushes the two
        down; P_N (3,7,3), sticky, facing north, pushes glass G_N (3,7,2) and RB_1 north and pulls G_N back (a
        piston at (3,7,2) is QC-powered by RB_2 and extends in the load).
Kick    U_T, a sticky piston at (2,8,-1) facing down, beside RB_ST's rest cell (2,8,0). RB_ST's landing there
        (c2 j) powers and updates it: out at c3, head at (2,7,-1) above RB_T, through the rest of the close. When
        P_U pulls RB_ST up, U_T is released inside that event and pulls RB_T up to (2,7,-1); K_T, which RB_T held
        out, retracts behind it and, being sticky now, pulls SPC home. Two ticks later RB_ST lands at (2,9,0),
        beside the cell above U_T, ahead of U_T's own base and of RB_T (its move began first; were it the last
        of the three to land, U_T would stay in: the what-if below): U_T is powered by QC when they land and
        update it, goes out again and pushes RB_T back down in front of P_R. It stays out until RB_ST is pulled
        on.
P_R     RB_1 lands in (3,7,0) in the tick RB_T lands at (2,7,-1): P_R is powered by QC, as in the closed state,
        and not updated; before, when RB_T left its front, it was not powered. RB_T's landing in front of it is
        its update: it pushes RB_T to (1,6,-1), under GB and GA. K_T landed three ticks before, so W_T is not
        woken (returns.py's trap). P_R's head landing updates U_T's head: U_T retracts, RB_ST having left (2,9,0).
H_T     Pushes GA, GB and RB_T down once RB_T has landed at (1,6,-1), as in returns.py's what-if.
Timer   One pulse. R_0, a 4-tick repeater at (2,6,3) facing west, reads Q_F, the stone under the S feed's dust
        D_F, lit from c10 d to c14 j: on from c18 d to c26 d. R_1 (3,6,3), 4 ticks, into stone Y_0 (4,6,3): c26 d
        to c34 d. Eight dusts on glass climb from beside Y_0 to (2,10,1), which points into P_U: P_U is out from
        c26 and pulls at c34, the first tick at which a cell outside the added blocks changes after c30. Four
        repeaters read that line: R_N (4,8,3), 4 ticks, into the cell above P_N; R_E (5,9,1), 4 ticks, into stone
        Y_E (5,9,0) beside P_E; R_S (4,10,-1), 4 ticks, reading two dusts on and beside Y_E, into stone Y_S
        (3,10,-1) above P_S; R_H (2,10,-1), 3 ticks, reading Y_S, into the cell above H_T; R_D (3,11,0), 4 ticks,
        reading a dust on Y_S, into the cell above P_D.
Order   c34: P_U pulls (the kick), P_N and P_E go out. c36 j: RB_1 home, RB_ST at (2,9,0), RB_T at (2,7,-1). c37
        U_T pushes RB_T back, c40 P_R takes it, c42 j it is under the column. c42: P_N pulls G_N back, P_E pulls
        RB_ST east, R_S powers P_S, which P_E's head and then the moving block stop; RB_ST's landing at (3,9,0)
        (c44 j) is its update. c45 P_S, c48 H_T, c50 P_D (R_D turns on with RB_ST at rest above RB_2), c50 j RB_T
        under T, c52 j the two redstone blocks a cell lower. The S feed's cut resets by itself once RB_ST has left
        (2,8,0) (s_inputs.py): C_F is home at c46 j. The last piston, P_D, retracts at c58.
QC      A repeater that points into a stone beside the cell above a piston powers the piston by QC and does not
        update it: a first design had P_E's work done by a pusher at (1,9,0) fed that way, and it never fired
        (the last control). So R_N, R_H and R_D point into the air cell above their piston, whose change updates
        it; Y_E and Y_S stand against P_E and P_S, and P_S, powered while it cannot move, is updated by the block
        it pushes.
Margin  Each delay moved alone: R_0 and R_1 may be 3 or 4 ticks (shorter, the return is done but starts before
        c30); R_N 3 or 4 (shorter, RB_1 is in (3,7,0) when RB_T is lifted, and P_R, powered, extends into the
        empty cell); R_E, R_S and R_D 2 to 4; R_H 1 to 4.

Not controls: the sixteen glass blocks carry dust and repeaters (the simulator has no rule for support).
Run from the repo root (sim; about 2 minutes):
python -m scripts.door2.close_layout.rbt_drives > scripts/door2/close_layout/rbt_drives.txt"""
import copy, functools, re
from scripts.door2.close_layout import feeds as f, puller as pr, trigger as t, s_inputs as si, p9_p8 as pp, p10_v as pv, returns as r
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, DIRS, add

H_T, GA, GB, COLUMN, RB_T_HOME = r.H_T, r.GA, r.GB, r.COLUMN, r.RB_T_HOME
U_T, PARK = (2, 8, -1), (2, 7, -1)                                   # the kicker, and where it parks RB_T
P_U, P_E, P_S, P_D, P_N = (2, 10, 0), (4, 9, 0), (3, 9, -1), (3, 10, 1), (3, 7, 3)
G_N, RB_1, RB_2 = (3, 7, 2), (3, 7, 1), (3, 8, 1)
WAY = ((2, 9, 0), (3, 9, 0), (3, 9, 1))                              # RB_ST's cells between its rest cell and RB_2's
R_0, R_1, Y_0 = (2, 6, 3), (3, 6, 3), (4, 6, 3)
CLIMB = ((5, 6, 3), (6, 7, 3), (5, 8, 3), (5, 9, 2), (4, 10, 2), (3, 10, 2), (2, 10, 2), (2, 10, 1))
R_N, R_E, Y_E, D_E, R_S, Y_S, R_H, D_D, R_D = (4, 8, 3), (5, 9, 1), (5, 9, 0), ((5, 10, 0), (5, 10, -1)), (4, 10, -1), (3, 10, -1), \
    (2, 10, -1), (3, 11, -1), (3, 11, 0)
HEAD_N = (3, 8, 3)                                                   # the cell above P_N
LAST = 62                                                            # the runs end after c62
LO, HI = r.LO, (7, 11, 3)                                            # the box with these blocks: one layer higher


def rep(facing, delay):
    return B("repeater", facing=facing, delay=delay, powered=False)


COLUMN_BLOCKS = {H_T: t.pis("piston", "down", "H_T"), GA: B("glass", id="GA"), GB: B("glass", id="GB")}
KICK = {U_T: t.pis("sticky_piston", "down", "U_T")}
LOOP = {P_U: t.pis("sticky_piston", "down", "P_U"), P_E: t.pis("sticky_piston", "west", "P_E"), P_S: t.pis("piston", "south", "P_S"),
        P_D: t.pis("piston", "down", "P_D"), P_N: t.pis("sticky_piston", "north", "P_N"), G_N: B("glass", id="G_N"),
        RB_1: B("rb", id="RB_1"), RB_2: B("rb", id="RB_2")}
REPEATERS = {R_0: rep("west", 4), R_1: rep("west", 4), R_N: rep("east", 4), R_E: rep("south", 4), R_S: rep("east", 4),
             R_H: rep("east", 3), R_D: rep("north", 4)}
STONES = {Y_0: t.STONE, Y_E: t.STONE, Y_S: t.STONE}
DUSTS = {c: t.DUST for c in (*CLIMB, *D_E, D_D)}
GLASSES = {(x, y - 1, z): t.GLASS for x, y, z in (*REPEATERS, *CLIMB, D_E[1])}
TIMER = {**REPEATERS, **STONES, **DUSTS, **GLASSES}
MINE = {**COLUMN_BLOCKS, **KICK, **LOOP, **TIMER}
NAMES = {R_0: "R_0", R_1: "R_1", R_N: "R_N", R_E: "R_E", R_S: "R_S", R_H: "R_H", R_D: "R_D", Y_0: "Y_0", Y_E: "Y_E", Y_S: "Y_S",
         CLIMB[0]: "the dust beside Y_0", CLIMB[2]: "the dust R_N reads", CLIMB[-1]: "the dust into P_U", D_E[0]: "the dust on Y_E",
         D_E[1]: "the dust R_S reads", D_D: "the dust on Y_S", **{c: st.p["id"] for c, st in {**COLUMN_BLOCKS, **KICK, **LOOP}.items()}}
MY_PISTONS = {st.p["id"]: c for c, st in MINE.items() if st.n in ("piston", "sticky_piston")}
# cells the added blocks move through, and the cells the return must leave as the closed state has them: returns.py's
# east side without its own kicker, the loop, the timer
MOVED = (PARK, *WAY, HEAD_N, *COLUMN)
EAST = [c for c in r.EAST if c not in (r.N_T, r.PARK, r.SRC_N, r.SRC_H, r.POKE_R)]
CELLS = list(dict.fromkeys([*EAST, *MINE, *MOVED]))
SHOW = ("EXTEND", "RETRACT", "cancel", "failed", "dropped", *(f"repeater {c} " for c in REPEATERS),
        *(f"land rb@{c}" for c in (t.UP, PARK, pr.HEAD, GB, RB_T_HOME, t.RB_ST, *WAY, RB_1, RB_2)), f"land glass@{t.SPC}",
        f"land stone@{si.C_F}")
SEEN = (*MY_PISTONS, "P_R", "K_T", "W_T", "Z_T", "T", "A_C", "AP", "I_A")


def build(drop=(), swap=None):
    """p9_p8.py's build (K_T sticky: trigger.py) with the 48 blocks; `drop` leaves cells out, `swap` replaces or adds
    some. GB stands in (1,6,-1), a cell of the opening: Z_T lifts it with RB_T (returns.py)."""
    b = pp.build()
    for c, st in {**MINE, **(swap or {})}.items():
        if c not in drop:
            b.b[c] = st
            b.role[c] = "rbt_drives"
    return b


class Noted(pp.Noted):
    """p9_p8's Noted with this step's lines."""

    def L(self, msg):
        World.L(self, msg)
        if any(x in msg for x in SHOW):
            self.lines.append((self.tick_no, self.phase, self.cur if self.phase == "g" and self.seen is not None else None, msg))


def noted(w, ticks=None, first=-1, before=None, **kw):
    """a copy of w taken through ticks (each: its commands, then the tick; default: the input off, then nothing to
    c`LAST`), with the shown lines and (blocks, moving cells) after each tick. `before` {tick number: function of
    the world} acts ahead of that tick (sim only)."""
    w = copy.deepcopy(w)
    w.__class__ = Noted
    w.reverse, w.ia_last, w.first = kw.get("reverse", False), kw.get("ia_last", False), None
    w.lvl, w.order, w.seen, w.after, w.said, w.lines, w.noted, w.fed, w.power, w.frames = {}, [], None, None, [], [], [], [], [], []
    w.reached, w.woke, w.held = {}, {"P8": [], "P9": [], "A_9": []}, []
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


def lands_after(cell):
    """before c36: RB_ST put behind the moving block at `cell` in the order the moving blocks tick in (sim only)."""
    def act(w):
        rb = next(be for be in w.tickers if be.pos == WAY[0] and not be.removed)
        w.tickers.remove(rb)
        w.tickers.insert(next(i for i, be in enumerate(w.tickers) if be.pos == cell) + 1, rb)
    return act


def verdict(w, cl):
    """what keeps the trigger chain's east side, the S feed's cut and the added blocks from the loaded closed state
    `cl`, cell for cell and labels apart, their pistons from the closed state's power, T from RB_T's, and the door
    plane from the closed door's; empty when the return is done."""
    bad = [f"{c} {'moving' if c in w.be else w.get(c)}" for c in CELLS if c in w.be or pp.bare(w.get(c)) != pp.bare(cl.get(c))]
    bad += [f"{st.p['id']} powered by {[x for _, x in power_sources(w, c)]}" for c, st in cl.b.items()
            if c in CELLS and c != r.T_CELL and st.n in ("piston", "sticky_piston") and pp.bare(w.get(c)) == pp.bare(st)
            and power_sources(w, c) != power_sources(cl, c)]
    bad += ["T not powered by RB_T"] * (("qc", RB_T_HOME) not in power_sources(w, r.T_CELL))
    return bad + pp.verdict_end(w, cl) + [f"moving at {sorted(w.be)}"] * bool(w.be)


def run(b, ticks=None, opened=None, **kw):
    """b opened from the input and taken through the close and the return: (closed state, noted world, verdict)."""
    cl = d.make_world(b)[0]
    w = noted(t.opened(b)[0] if opened is None else opened, ticks, **kw)
    return cl, w, verdict(w, cl)


def said(w, first=2, names=SEEN, lands=True):
    return [x for x in pv.told(w) if pv.tick_of(x) >= first and (any(f" {n}@" in x for n in names) or (lands and " land " in x)
                                                                 or "repeater" in x)]


def where(w):
    return ", ".join(f"{n} {t.at(w, n)[0]}" + {True: " out", False: " in", None: ""}[t.at(w, n)[2]]
                     for n in ("RB_T", "P_R", "K_T", "SPC", "U_T", "RB_ST", "RB_1", "RB_2", "G_N", "GB"))


def bare_events(w):
    """the piston events of each tick with the three redstone blocks' labels (and TM's and TR's) taken out."""
    return [[re.sub(r"(RB_ST|RB_1|RB_2|TM|TR)@", "@", m) for m in tick] for tick in pv.per_tick(w, -1, LAST)]


def powered(b, cells):
    """the ticks of the opening and of the close to c30 after which each of `cells` is powered, and whether it is in
    the closed state."""
    w, _ = d.make_world(b)
    out = {c: ["closed"] * bool(power_sources(w, c)) for c in cells}
    w.run(4)
    w.cmd_set(f.DRIVER, t.RB)
    for k in range(t.OPEN_TICKS + r.CLOSE):
        if k == t.OPEN_TICKS:
            w.cmd_set(f.DRIVER, AIR)
        w.tick()
        for c in cells:
            if w.get(c).n in ("piston", "sticky_piston") and power_sources(w, c):
                out[c].append(r.tick_name(k))
    return out


def spans(ticks):
    """a list of tick names as first..last runs."""
    out = []
    for x in ticks:
        n = None if x == "closed" else (0 if x[0] == "t" else 1000) + int(x[1:])
        if out and n is not None and out[-1][2] == n - 1:
            out[-1][1:] = [x, n]
        else:
            out.append([x, x, n])
    return ", ".join(a if a == z else f"{a} to {z}" for a, z, _ in out) or "never"


def second(b, w, cl):
    """the world after the return with every other cell set back as loaded, without updates (a stand-in for the
    returns not designed), opened again: the ticks at which the second opening differs from the first, labels
    apart, and the second close and return."""
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


# name: (title, build keywords)
CONTROLS = {
    "no R_0": ("nothing reads the S feed's pulse: nothing starts", dict(drop=(R_0,))),
    "no U_T": ("no kick: K_T stays out under SPC and RB_T in front of P_R, which nothing updates", dict(drop=(U_T,))),
    "U_T not sticky": ("it pulls nothing", dict(swap={U_T: t.pis("piston", "down", "U_T")})),
    "K_T not sticky": ("as measured before this step: K_T retracts and leaves SPC at (2,7,0)", dict(swap={t.K_T: t.pis("piston", "up", "K_T")})),
    "no P_U": ("RB_ST stays at (2,8,0) and holds U_T out", dict(drop=(P_U,))),
    "no P_N": ("no block comes into (3,7,0): P_R is not powered when RB_T lands in front of it", dict(drop=(P_N,))),
    "no R_N": ("the same: nothing powers P_N", dict(drop=(R_N,))),
    "no RB_1": ("the same: P_N pushes glass only", dict(drop=(RB_1,))),
    "no G_N": ("P_N's head stops a cell short of RB_1", dict(drop=(G_N,))),
    "P_N not sticky": ("G_N stays in (3,7,1), under RB_2", dict(swap={P_N: t.pis("piston", "north", "P_N")})),
    "P_N at (3,7,2), no G_N": ("RB_2 is beside the cell above it and powers it by QC: it extends in the load",
                               dict(drop=(P_N, (4, 8, 3), (4, 7, 3)), swap={G_N: t.pis("piston", "north", "P_N")})),
    "no P_E": ("RB_ST stays at (2,9,0) and holds U_T out", dict(drop=(P_E,))),
    "no R_E": ("the same, and nothing reaches P_S, H_T and P_D", dict(drop=(R_E,))),
    "no P_S": ("RB_ST stays at (3,9,0)", dict(drop=(P_S,))),
    "no R_S": ("the same, and nothing reaches H_T and P_D", dict(drop=(R_S,))),
    "no P_D": ("RB_ST stays at (3,9,1), RB_1's cell empty", dict(drop=(P_D,))),
    "no R_D": ("the same", dict(drop=(R_D,))),
    "no RB_2": ("P_D pushes RB_ST one cell: (3,7,1) stays empty", dict(drop=(RB_2,))),
    "no H_T": ("RB_T stays at (1,6,-1)", dict(drop=(H_T,))),
    "no R_H": ("the same", dict(drop=(R_H,))),
    "no GB": ("Z_T lifts RB_T alone and H_T's push ends a cell short (returns.py)", dict(drop=(GB,))),
    "P_E's work by a pusher at (1,9,0) fed through a stone beside the cell above it": (
        "a 4-tick and a 3-tick repeater from the line into a stone at (0,10,0), on from c40 d to c48 d",
        dict(drop=(P_E, R_E, Y_E, *D_E, R_S, (5, 8, 1), (5, 9, -1), (4, 9, -1)),
             swap={(1, 9, 0): t.pis("piston", "east", "P_E"), (1, 9, 2): t.GLASS, (1, 10, 2): rep("east", 4), (0, 10, 2): t.STONE,
                   (0, 9, 1): t.GLASS, (0, 10, 1): rep("south", 3), (0, 10, 0): t.STONE})),
}


if __name__ == "__main__":
    from scripts.door2 import volume as v
    b0, cl0, w0, ref, _ = r.worlds()
    free = r.free_in(LO, HI)
    b = build()
    kinds = [st.n for st in MINE.values()]
    print(f"added: {len(MINE)} blocks ({kinds.count('sticky_piston')} sticky pistons, {kinds.count('piston')} pistons, {kinds.count('rb')} redstone "
          f"blocks, {kinds.count('repeater')} repeaters, {kinds.count('redstone_wire')} dust, {kinds.count('stone')} stone, {kinds.count('glass')} glass: "
          f"GA, GB, G_N and {len(GLASSES)} under dust and repeaters); K_T sticky (trigger.py); no stand-in, no command after the input")
    print("added blocks outside the free cells (in the box, empty in the closed state and in every tick of the opening and of the close to c30, "
          "off the door plane and out of the hallway):", ", ".join(f"{NAMES.get(c, c)} {c}" for c in MINE if c not in free) or "none",
          "(GB stands in a cell of the opening: Z_T lifts it with RB_T)")
    moved, differ = r.against(b, set(MINE) | set(MOVED))
    g = r.frames(b)
    next(g)
    early = {}
    for k, ((bl, be), (rb, rbe)) in enumerate(zip(g, ref)):
        for c in (*MINE, *MOVED):
            if c in COLUMN:
                continue
            if (c in be) or (bl.get(c) != (MINE.get(c) if c in MINE else None) and not (bl.get(c) and MINE.get(c) and bl[c].n == MINE[c].n == "redstone_wire"
                                                                                           and bl[c].p["power"] == 0)):
                early.setdefault(NAMES.get(c, str(c)), []).append(r.tick_name(k))
    print("moved during load:", moved or "none", "| the opening and the close to c30 outside the added blocks and the cells they move through:",
          f"differ at {differ}" if differ else "the same at every tick")
    first = {}
    for n, ks in early.items():
        first.setdefault(spans(ks), []).append(n)
    print("   added cells that are not as loaded, by tick (the column's three apart: returns.py):",
          "; ".join(f"{k}: " + ", ".join(ns) for k, ns in first.items()))
    cells = set(v.cumulative_cells(b)[0])
    cl, w, bad = run(b)
    for blocks, _ in w.frames:
        cells |= {p for p, st in blocks.items() if st.n != "air" and not v.excluded(p, st)}
    print("box, opening + close + return:", t.s.box(cells))
    pw = powered(b, list(MY_PISTONS.values()))
    print("added pistons powered, closed state, opening and close to c30:", "; ".join(f"{n} {spans(pw[c])}" for n, c in MY_PISTONS.items()))
    op, _ = t.opened(b)
    print("open state: U_T", t.at(op, "U_T")[1:], "| RB_ST", t.at(op, "RB_ST")[0], "| the timer's repeaters on:",
          [NAMES[c] for c in REPEATERS if op.get(c).p["powered"]] or "none", "| its dust lit:", [c for c in DUSTS if op.get(c).p["power"]] or "none")

    print(f"\n== the close and the return from the input, no command: c-1 to c{LAST}")
    base = pp.noted(t.opened(pp.build())[0], pp.idle(LAST))
    same = next((n for n in range(-1, LAST + 1) if pv.per_tick(w, -1, LAST)[n + 1] != pv.per_tick(base, -1, LAST)[n + 1]), None)
    print(f"   c-1 to c{same - 1}: the piston events of p9_p8's run, tick by tick; then:")
    print("\n".join("   " + x for x in said(w, same)))
    print("   ->", "FAILS: " + "; ".join(bad) if bad else "done: RB_T at (1,5,-1) under GB and GA, T powered by it, Z_T not; P_R out, held by the redstone "
          "block in (3,7,0); K_T in, SPC at (2,6,0); W_T, AP and the S feed's thirteen as the closed state has them; the added pistons in and "
          "unpowered, the repeaters off, the dust dark, a redstone block in (3,7,1) and in (3,8,1), G_N at (3,7,2); the door plane closed; "
          "nothing moving")
    print("   ", where(w))
    labels = sorted(f"{c}: {cl.get(c).p['id']} there, {w.get(c).p['id']} here" for c in CELLS if pp.bare(w.get(c)) == pp.bare(cl.get(c)) and w.get(c) != cl.get(c))
    print("   labels that differ from the loaded closed state:", "; ".join(labels), "(the same block)")
    rest, _ = pv.differing(cl, w)
    off = [x for x in rest if not any(x.startswith(str(c) + ":") for c in pp.PLANE) and not any(x.startswith(str(c) + ":") for c in (t.RB_ST, RB_1, RB_2))]
    names = [n for n in r.GROUPS[0][1] + ("K", "M_K", "RB12") if t.at(cl, n) != t.at(w, n)]
    print(f"   cells outside the door plane that still differ from the closed state: {len(off)}:", ", ".join(names),
          "(the opening's seven relays with their blocks, and the west side: not this step's)")
    mine_ev, ref_ev = pv.per_tick(w, -1, LAST), pv.per_tick(base, -1, LAST)
    print("   piston events against p9_p8's run:", sum(len(set(a) - set(c)) for a, c in zip(mine_ev, ref_ev)), "added,",
          "none taken away" if all(set(c) <= set(a) for a, c in zip(mine_ev, ref_ev)) else "SOME TAKEN AWAY")
    lv = {}
    for k, (blocks, _) in enumerate(w.frames):
        for c in (CLIMB[0], CLIMB[2], CLIMB[3], CLIMB[-1], *D_E, D_D):
            if blocks[c].p["power"]:
                lv.setdefault(c, [blocks[c].p["power"], k - 1, k - 1])[2] = k - 1
    print("   dust levels while lit:", "; ".join(f"{c} {p} after c{a} to c{z}" for c, (p, a, z) in lv.items()))

    print("\n== order (must pass): against the run above")
    for name, kw in (("dust's neighbour updates in reverse order", dict(reverse=True)), ("I_A's retract event behind P_R's and M_K's", dict(ia_last=True)),
                     ("both", dict(reverse=True, ia_last=True))):
        _, x, badx = run(b, **kw)
        print(f"   {name}:", "FAILS" if badx else "done;", "piston events of each tick", "the same set" if pv.per_tick(x, -1, LAST) == mine_ev else "DIFFER")

    print("\n== the seven delays, each 1 to 4 ticks with the others as built: the return, and the close to c30 outside the added blocks")
    for c, st in REPEATERS.items():
        out = []
        for k in (1, 2, 3, 4):
            bk = build(swap={c: rep(st.p["facing"], k)})
            _, _, badk = run(bk)
            _, dk = r.against(bk, set(MINE) | set(MOVED))
            out.append(f"{k} " + ("FAILS" if badk else "done") + (f", close differs from {dk[0]}" if dk else ""))
        print(f"   {NAMES[c]} (built {st.p['delay']}):", "; ".join(out))

    print("\n== controls: one thing changed, the same run")
    for name, (title, bkw) in CONTROLS.items():
        bc = build(**bkw)
        mv = d.make_world(bc)[1]
        _, dc = r.against(bc, set(MINE) | set(MOVED) | set(bkw.get("swap", {})) | {(2, 9, -1)} if "pusher" in name else set(MINE) | set(MOVED) | {t.K_T, t.SPC, t.SRC})
        _, x, badc = run(bc)
        print(f"   {name}: {title}:", "FAILS: " + "; ".join(badc[:4]) + (" ..." if len(badc) > 4 else "") if badc else "done", "|", where(x),
              "| moved during load:" * bool(mv), ", ".join(m.split("@")[0] for m in mv), "| opening or close to c30 differ" * bool(dc and "K_T" not in name))
    pb = build(**CONTROLS["P_E's work by a pusher at (1,9,0) fed through a stone beside the cell above it"][1])
    print("      the pusher at (1,9,0) after c44: powered by", [c for _, c in power_sources(noted(t.opened(pb)[0], pp.idle(44)), (1, 9, 0))],
          "(QC) | RB_ST at", t.at(noted(t.opened(pb)[0], pp.idle(44)), "RB_ST")[0], "| its events to c62:",
          [x for x in said(run(pb)[1], 2, ("P_E",), False) if "repeater" not in x] or "none")

    print("\n== the input off n ticks after it went on (trigger.py's feed is armed at t10 j): the close (p9_p8's four verdicts) and the return")
    dusts = [c for c, st in op.b.items() if st.n == "redstone_wire"]
    res = {}
    for n in (8, 9, 10, 11, 12, 16):
        on, _ = t.opened(b, ticks=n)
        res[n] = ("close FAILS" if any(pp.verdicts(on, dusts, cl)) else "close done") + ", " + ("return FAILS" if verdict(noted(on), cl) else "return done")
    print("  ", res)

    print("\n== what-if (sim only): the order of the landings at c36 j. RB_ST lands at (2,9,0) ahead of U_T's base and of RB_T because its move began "
          "first (P_U's event, level 0; U_T's, level 1) and moving blocks tick in the order their moves began. U_T is updated by its base's "
          "landing and by RB_T's, in front of it; RB_ST's own landing does not update it")
    for title, cell in (("U_T's base ahead of RB_ST, RB_T behind it", U_T), ("both ahead of RB_ST", PARK)):
        _, x, badx = run(b, before={36: lands_after(cell)})
        print(f"   {title}:", "FAILS: " + "; ".join(badx[:4]) if badx else "done", "|", where(x), "| U_T's events from c34:",
              "; ".join(m.split(":")[0].split("level ")[0] + m.split(":")[0].split("@")[0].split()[-2] for m in said(x, 34, ("U_T",), False) if "repeater" not in m))

    back, differ2, y = second(b, w, cl)
    print(f"\n== a second cycle (sim only): after the return the {len(back)} cells that still differ, labels apart, are set back as loaded without updates "
          "(a stand-in for the returns not designed), and the input goes on again")
    print("   pending after the first return: scheduled ticks", w.sched or "none", "| block events", list(w.events) or "none")
    print("   the second opening against the first, every cell, labels apart:", f"differs at {differ2}" if differ2 else "the same at every tick")
    bad2 = verdict(y, cl)
    print("   the second close and return:", "FAILS: " + "; ".join(bad2[:4]) if bad2 else "done;", "piston events of each tick, labels apart,",
          "the same" if bare_events(y) == bare_events(w) else "DIFFER", "|", where(y))

    zb = build(swap={r.D9: r.D9_BLOCK})
    _, z, badz = run(zb)
    print("\n== with D9, the down-pusher of returns.py's what-if for Z9, built as well (its drives are not designed):", "FAILS" if badz else "done;",
          "piston events of each tick", "the same set" if pv.per_tick(z, -1, LAST) == mine_ev else "DIFFER")
