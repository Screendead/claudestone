"""Export design_c, the close feeds, P_R, the S feed and its inputs, the trigger chain, DP's seven blocks and p10_v's
two (fixture) + the nine blocks and the stone of p9_p8.py as a scratch spec:
library/mechanics/close_p9_p8_probe.redstone.yaml. Each test opens the door on the input, drops the input and
checks, after the ticks that decide it, that the cells the close moves or must leave alone are what the simulator
has after that tick, with the levels of DT, DS, DP, the tap, p10_v's dusts, the S feed's D_1, D_2 and D_F, LY at
(6,4,1) and (6,3,0) and D_8. No command follows the input: the only commands of a test are the load's and, in a
control, the one that takes a block out with setblock air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the
build, and without R_X, A_9, S_L (the glass left there), R_9 or R_8 the first test must fail, so the checks are
live.
Written and replayed only: the spec has not run on a server.
Run from the repo root: python -m scripts.door2.close_layout.export_p9_p8"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp
from scripts.door2.close_layout import export_trigger as xt, export_s_inputs as xi
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_p9_p8_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = {**xi.NAMES, pp.LY_UP: "ly_up", pp.LY_9: "ly", pp.D_8: "d8"}
MINE = set(pp.MINE)
# the cells of every earlier step and this one's: its blocks, RB9's three cells, P9, P5 and its head, the static block
ALL = list(dict.fromkeys(xi.ALL + [pp.R_X, pp.A_9, pp.RB9_CLOSED, pp.RB9_OPEN, pp.RB9_OUT, pp.S_L, pp.R_9, pp.R_8, pp.O_8, pp.P9,
                                   pp.P5, (3, 1, 0), (3, 0, 0)]))
# test name: (cell removed before the opening, last tick, ticks after which cells are checked: 2 is c0, 22 is c20)
TESTS = {
    "one input and no command after it: stages 0 to 5 as before; R_X on at c16 and A_9 out; RB9 at (5,4,1) after c18, LY "
    "lit; R_9 on at c20, P9 out, RB9 pulled; P9 spat at c22, TM at (2,2), TR at (1,2); A_9 home after c22; P8 out at c23; Q "
    "at (3,2) after c25: the door plane closed": (None, pp.LAST, (2, 6, 12, 14, 16, 17, 18, 20, 22, 24, 25, 27, 32), ALL),
    "without R_9 nothing reads LY: A_9 moves RB9 out and back, LY is lit after c18 and dark after c20, P9 stays in, TM stays "
    "at (3,2) and P8 stays in (control)": (pp.R_9, 25, (18, 20, 22, 24, 27), ALL),
    "without R_8 nothing powers P8: P9 pushes TM and TR and is spat, A_9 comes home, P8 stays in and Q stays at (3,3) "
    "(control)": (pp.R_8, 25, (6, 22, 24, 25, 27), ALL),
}


def main():
    b = pp.build()
    blocks = d.full_blocks(b)
    allc = list(blocks) + [DRIVER] + list(d.STRICT_ARM)
    lo = [min(c[i] for c in allc) for i in range(3)]
    hi = [max(c[i] for c in allc) for i in range(3)]
    glyphs = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZbcdefghjkmnopqrstuvwxyz0123456789!@$%&*+,;:?/<>|~^()[]{}")
    pal = {".": "air", "i": {"input": "in"}}
    rev = {}
    for c, st in sorted(blocks.items()):
        key = (state_str(st), c not in MINE, NAMES.get(c))
        if key not in rev:
            rev[key] = next(glyphs)
            ent = {"block": key[0]}
            if key[1]:
                ent["fixture"] = True
            if key[2]:
                ent["name"] = key[2]
            pal[rev[key]] = ent if len(ent) > 1 else key[0]
    layers = {}
    for y in range(lo[1], hi[1] + 1):
        rows = []
        for z in range(lo[2], hi[2] + 1):
            rows.append("".join("i" if (x, y, z) == DRIVER else
                                rev[(state_str(blocks[(x, y, z)]), (x, y, z) not in MINE, NAMES.get((x, y, z)))]
                                if (x, y, z) in blocks else "." for x in range(lo[0], hi[0] + 1)))
        layers[y - lo[1]] = "\n".join(rows) + "\n"

    def at(c):
        return " ".join(f"~{v - o_}" for v, o_ in zip(c, lo))

    def setb(c, what):
        return {"run": f"setblock {at(c)} {what}"}

    def seen(blocks_, moving, cells):
        """checks that the server's cells are the simulator's: block states, moving_piston where a block moves."""
        return [{"check": f"if block {at(c)} " + ("moving_piston" if c in moving else state_str(blocks_.get(c, AIR)))}
                for c in cells] + [{"level": {n: blocks_[c].p["power"] for c, n in NAMES.items() if c in blocks_}}]

    load = [setb(p, "air strict") for p in d.BLOCKERS] + [setb(p, "redstone_block strict") for p in d.STRICT_ARM]
    tests = []
    for name, (gone, last, checked, cells) in TESTS.items():
        ticks = pp.idle(last)
        w, _ = d.make_world(b)
        steps = list(load)
        if gone:
            w.cmd_set_silent(gone, AIR)
            steps.append(setb(gone, "air strict"))
            cells = [c for c in cells if c != gone]
        w.run(4)
        w.cmd_set(DRIVER, t.RB)
        w.run(5)
        steps += [{"wait": 4}, {"drive": {"in": 1}}, {"wait": 5}] + seen(w.b, set(w.be), xt.FRAME)
        w.run(t.OPEN_TICKS - 5)
        assert not w.be
        steps += [{"wait": t.OPEN_TICKS - 5}] + seen(w.b, set(), xt.FRAME + cells)
        frames = pp.noted(w, ticks).frames
        for k, (cmds, (blocks_, moving)) in enumerate(zip(ticks, frames), 1):
            steps += [{"drive": {"in": 0}} if c == DRIVER else setb(c, {"rb": "redstone_block"}.get(st.n, st.n)) for c, st in cmds]
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, cells)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for the last stages of the 3x3 door's close, P9's 0-tick and P8 (door2/close_layout/p9_p8.py). The close "
            "runs from one falling input to the closed door's plane, no command after it. Written and replayed in the simulator; "
            "not yet run on a server. The design_c door, the close feeds, P_R, the S feed and its inputs, the trigger chain, DP's "
            "seven blocks and the two of P10 and V are fixture; the design is nine blocks and a stone in place of one of the door's "
            f"glass blocks, here in door coordinates (door + {str(off).replace(' ', '')} = spec). P7 has no block: it fires at c3 on "
            "NA and TR lands at (2,2) at the end of c5. So P9 fires after stage 5 and pushes two blocks, TM from (3,2) to (2,2) and "
            "TR on to (1,2), then P8 pushes Q down to (3,2); Q never fires. R_X, a 2-tick repeater at (2,5,1) facing west on glass "
            "(2,4,1), reads (1,5,1), where the S feed's redstone block RB_F stands from the end of c12 to c15: on at c16, off at "
            "c20. A_9, a sticky piston at (3,4,1) facing east under the cell R_X points into, pushes RB9, the door's own redstone "
            "block at (4,4,1) in the open state, to (5,4,1), beside the dust LY at (5,4,2) and (6,4,1): it lands at the end of c18. "
            "The stone at (6,3,1) under LY's dust (6,4,1) passes the level down to LY's dust (6,3,0): 15 and 14. R_9, a 1-tick "
            "repeater at (5,3,0) facing east on glass (5,2,0), reads that dust and points into the cell above P9: on at c20, when "
            "A_9 pulls RB9 back, off at c22. P9 extends at c20 and is spat at c22: TM real at (2,2), TR at (1,2) at the end of c22. "
            "R_8, a 1-tick repeater at (3,5,-1) facing north on the door's stone (3,4,-1), reads D_8, a dust at (3,5,-2) on glass "
            "(3,4,-2) that reads NA's dust (2,4,-2) up the step, and points into the cell above P8: on in the closed state, off in "
            "the opening, on from c4. The obsidian at (3,-1,0) under the static block (3,0,0) keeps P8 from pushing Q, TM and R "
            "down until P9 has taken TM away. A_9 lands at (3,4,1), south of P8, at the end of c22 and that update fires P8 at "
            "c23: Q is at (3,2) at the end of c25 and the door plane is the closed door's (TM and TR in each other's cells). The "
            "returns of the opening's relays and of the trigger chain's blocks are not designed. Each test checks the frame 5 "
            "ticks into the opening and the open state, then the cells the close moves or must leave alone and the levels of DT, "
            "DS, DP, the tap, D_V, NV's four dusts, D_1, D_2, D_F, LY at (6,4,1) and (6,3,0) and D_8 against the simulator after c0, "
            "c4, c10, c12, c14, c15, c16, c18, c20, c22, c23, c25 and c30 (after c16: R_X on, A_9 out, its head and RB9 moving; "
            "after c18: RB9 at (5,4,1), LY 15 and 14, R_9 off; after c20: R_X off, R_9 on, A_9 and RB9 moving back, P9 out, its "
            "head, TM and TR moving, LY 0; after c22: R_9 off, P9 moving in, TM at (2,2), TR at (1,2), (3,2) air, A_9 at (3,4,1), "
            "RB9 at (4,4,1); after c23: P8 out, its head and Q moving; after c25: Q at (3,2), P9 in). Controls remove one block "
            "with setblock air strict before the opening: R_9 (A_9 still moves RB9 out and back and LY is lit after c18, but P9 "
            "never moves, TM stays at (3,2) and P8 stays in) or R_8 (P9's 0-tick runs, P8 has no power when A_9 lands and stays "
            "in, Q stays at (3,3)).")
    spec = {"name": "close_p9_p8_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
            "layers": layers, "tests": tests}

    class Lit(str):
        pass
    yaml.add_representer(Lit, lambda dd, v: dd.represent_scalar("tag:yaml.org,2002:str", v, style="|"))
    spec["layers"] = {y: Lit(v) for y, v in sorted(spec["layers"].items())}
    path = os.path.join(HERE, "..", "..", "..", OUT)
    with open(path, "w") as fh:
        yaml.dump(spec, fh, sort_keys=False, width=200)
    print("wrote", OUT, "offset", list(off), "tests", len(tests), "steps", sum(len(x["steps"]) for x in tests))
    replay(path, lo)


def replay(path, lo):
    """the spec's own steps, parsed from the YAML, on the simulator: failed checks per test, per build."""
    spec = yaml.safe_load(open(path))
    cell = lambda xyz: tuple(int(v) + o_ for v, o_ in zip(xyz, lo))
    blocks = d.full_blocks(pp.build())
    for y, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, y, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    put = {"air": AIR, "redstone_block": t.RB}
    named = {v: k for k, v in NAMES.items()}
    drops = {"the build": (), "without R_X": (pp.R_X,), "without A_9": (pp.A_9,), "with the glass left at S_L": (pp.S_L,),
             "without R_9": (pp.R_9,), "without R_8": (pp.R_8,)}
    for label, drop in drops.items():
        failed = []
        for test in spec["tests"]:
            w, _ = d.make_world(pp.build(drop=drop))
            bad = 0
            for step in test["steps"]:
                (kind, arg), = step.items()
                if kind == "wait":
                    w.run(arg)
                elif kind == "drive":
                    w.cmd_set(DRIVER, t.RB if arg["in"] else AIR)
                elif kind == "level":
                    bad += sum(w.get(named[n]).p.get("power") != v for n, v in arg.items())
                else:
                    m = re.fullmatch(r"(?:setblock|if block) ~(\d+) ~(\d+) ~(\d+) (\S+?)( strict)?", arg)
                    c = cell(m.groups()[:3])
                    if kind == "check":
                        bad += c not in drop and ("moving_piston" if c in w.be else state_str(w.get(c))) != m.group(4)
                    elif not m.group(5):
                        w.cmd_set(c, put[m.group(4)])
                    elif c not in d.BLOCKERS and c not in d.STRICT_ARM:      # make_world has set those
                        assert m.group(4) == "air", step
                        w.cmd_set_silent(c, AIR)
            failed.append(bad)
        print(f"replayed in the simulator, {label}: failed checks per test {failed}")
        assert failed[0] if drop else not any(failed), label


if __name__ == "__main__":
    main()
