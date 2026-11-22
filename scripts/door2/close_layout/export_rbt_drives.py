"""Export design_c and every close step's blocks (fixture; K_T sticky) + the 49 blocks of rbt_drives.py as a scratch
spec: library/mechanics/close_rbt_drives_probe.redstone.yaml. Each test opens the door on the input, drops the input
and checks, after the ticks that decide it, that the cells the close and the return move or must leave alone are
what the simulator has after that tick, with the levels of the earlier steps' dusts and of seven of the timer's.
No command follows the input: the only commands of a test are the load's and, in a control, the one that takes a
block out with setblock air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the build,
and without R_0, U_T, P_U, R_N, P_E, R_S, R_H or R_D the first test must fail, so the checks are live.
Written and replayed only: the spec has not run on a server.
Run from the repo root: python -m scripts.door2.close_layout.export_rbt_drives"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, rbt_drives as rd
from scripts.door2.close_layout import export_trigger as xt, export_p9_p8 as x9
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_rbt_drives_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = {**x9.NAMES, rd.CLIMB[0]: "line_y0", rd.CLIMB[2]: "line_n", rd.CLIMB[3]: "line_e", rd.CLIMB[-1]: "line_u", rd.D_E[0]: "e_on",
         rd.D_E[1]: "e_s", rd.D_D: "s_d"}
MINE = set(rd.MINE)
CELLS = list(dict.fromkeys(x9.ALL + rd.CELLS))
# test name: (cell removed before the opening, last tick, ticks after which cells are checked: 2 is c0, 36 is c34)
TESTS = {
    "one input and no command after it: U_T out at c3; P_U out at c26 and RB_ST pulled up at c34, U_T pulling RB_T up and "
    "K_T pulling SPC home in that tick; a redstone block in (3,7,0) and RB_T at (2,7,-1) after c36; RB_T back in front of P_R "
    "after c39, at (1,6,-1) after c42, under T after c50; the three redstone blocks a place on after c52; everything in "
    "after c60": (None, rd.LAST, (2, 5, 7, 20, 28, 36, 38, 39, 41, 42, 44, 45, 46, 49, 50, 52, 54, 58, 62, 64)),
    "without R_0 nothing reads the S feed's pulse: nothing starts, RB_ST stays at (2,8,0) and U_T out above RB_T "
    "(control)": (rd.R_0, 52, (7, 20, 28, 38, 54)),
    "without U_T there is no kick: the redstone blocks go round, RB_T stays in front of P_R and K_T out under SPC "
    "(control)": (rd.U_T, rd.LAST, (5, 36, 38, 42, 52, 64)),
    "without R_N no redstone block comes into (3,7,0): P_R is unpowered when RB_T lands in front of it and stays in, and "
    "U_T lifts RB_T again at c48, when H_T's push updates it (control)": (rd.R_N, rd.LAST, (36, 38, 41, 42, 44, 50, 52, 54, 64)),
}


def main():
    b = rd.build()
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
    for name, (gone, last, checked) in TESTS.items():
        ticks = pp.idle(last)
        w, _ = d.make_world(b)
        steps = list(load)
        cells = CELLS
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
        frames = rd.noted(w, ticks).frames
        for k, (cmds, (blocks_, moving)) in enumerate(zip(ticks, frames), 1):
            steps += [{"drive": {"in": 0}} for c, st in cmds]
            assert all(c == DRIVER for c, st in cmds)
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, cells)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for the return of the 3x3 door's trigger chain after the close, from the one input with no command "
            "(door2/close_layout/rbt_drives.py). RB_T, P_R, K_T, SPC and the redstone block that P_R and the T feed start from go "
            "back to the closed state. Written and replayed in the simulator; not yet run on a server. The design_c "
            "door and every close step's blocks are fixture, K_T (2,5,0) now a sticky piston; the design is 49 blocks, here in door "
            f"coordinates (door + {str(off).replace(' ', '')} = spec). After the close RB_T is at (2,6,-1), in front of the "
            "retracted P_R, and holds K_T out by QC; SPC is at (2,7,0) and RB_ST at (2,8,0). The kick: U_T, a sticky piston at "
            "(2,8,-1) facing down, beside RB_ST's rest cell, is powered and updated by RB_ST's landing at the end of c2 and goes "
            "out at c3, its head above RB_T. The loop: two more redstone blocks, RB_1 (3,7,1) and RB_2 (3,8,1), stand south of "
            "RB_ST's closed cell (3,7,0); RB_1 goes north into it and RB_ST comes round on top of RB_2, so each of the three ends "
            "in the next one's cell. P_U (2,10,0), sticky, facing down, pulls RB_ST up; P_E (4,9,0), sticky, facing west, pulls it "
            "east; P_S (3,9,-1) pushes it south; P_D (3,10,1) pushes it and RB_2 down; P_N (3,7,3), sticky, facing north, pushes "
            "glass G_N (3,7,2) and RB_1 north and pulls G_N back. The column: H_T (1,9,-1) facing down over glass GA and GB, which "
            "Z_T lifts with RB_T in the opening. The timer is one pulse: R_0, a 4-tick repeater at (2,6,3), reads the stone under "
            "the S feed's dust D_F (lit c10 to c14) and is on from c18 to c26; R_1 (3,6,3), 4 ticks, powers stone Y_0 (4,6,3) from "
            "c26 to c34; eight dusts on glass climb from beside Y_0 to (2,10,1) and point into P_U. Four repeaters read that line: "
            "R_N (4,8,3) into the cell above P_N, R_E (5,9,1) into stone Y_E (5,9,0) beside P_E, R_S (4,10,-1), reading two dusts "
            "on and beside Y_E, into stone Y_S (3,10,-1) above P_S, all 4 ticks; R_H (2,10,-1), 3 ticks, reads Y_S and points into "
            "the cell above H_T; R_D (3,11,0), 4 ticks, reads a dust on Y_S and points into the cell above P_D. The run: P_U goes "
            "out at c26. At c34 the line goes dark and P_U pulls RB_ST up; inside that event U_T, released, pulls RB_T up to "
            "(2,7,-1), and K_T, released by RB_T, pulls SPC home to (2,6,0); in the same tick P_N pushes RB_1 into (3,7,0) and P_E "
            "goes out. At the end of c36 RB_ST lands at (2,9,0), beside the cell above U_T, ahead of U_T's own base: U_T is "
            "powered by QC when it lands and goes out again at c37, pushing RB_T back down. RB_T lands in front of P_R at the end "
            "of c39; P_R, powered by the redstone block in (3,7,0) since the end of c36, goes out at c40 and RB_T lands at "
            "(1,6,-1) at the end of c42; U_T retracts at c43. At c42 P_N pulls G_N back and P_E pulls RB_ST east; R_S powers P_S, "
            "which cannot move until RB_ST lands at (3,9,0) at the end of c44; P_S pushes it south at c45. H_T goes out at c48 "
            "and RB_T lands at (1,5,-1), under T, at the end of c50. P_D pushes RB_ST and RB_2 down at c50: RB_2 lands at (3,7,1) "
            "and RB_ST at (3,8,1) at the end of c52. The S feed's cut resets by itself (C_F home at the end of c46). The last "
            "piston, P_D, retracts at c58. Each test checks the frame 5 ticks into the opening and the open state, then the cells "
            "the close and the return move or must leave alone and the dust levels against the simulator after the ticks that "
            "decide it; the first test ends with every cell of the trigger chain's east side, of the S feed's cut and of the 49 "
            "blocks as loaded (the three redstone blocks one place on). Controls remove one block with setblock air strict "
            "before the opening: R_0 (nothing starts), U_T (no kick: the redstone blocks go round and RB_T stays where it was) or "
            "R_N (no redstone block comes into (3,7,0), P_R stays in, and U_T, updated by H_T's push at c48, lifts RB_T again).")
    spec = {"name": "close_rbt_drives_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
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
    blocks = d.full_blocks(rd.build())
    for y, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, y, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    named = {v: k for k, v in NAMES.items()}
    drops = {"the build": (), **{f"without {rd.NAMES[c]}": (c,) for c in (rd.R_0, rd.U_T, rd.P_U, rd.R_N, rd.P_E, rd.R_S, rd.R_H, rd.R_D)}}
    for label, drop in drops.items():
        failed = []
        for test in spec["tests"]:
            w, _ = d.make_world(rd.build(drop=drop))
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
                    elif c not in d.BLOCKERS and c not in d.STRICT_ARM:      # make_world has set those
                        assert m.group(4) == "air" and m.group(5), step
                        w.cmd_set_silent(c, AIR)
            failed.append(bad)
        print(f"replayed in the simulator, {label}: failed checks per test {failed}")
        assert failed[0] if drop else not any(failed), label


if __name__ == "__main__":
    main()
