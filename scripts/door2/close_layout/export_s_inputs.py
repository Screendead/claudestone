"""Export design_c, the close feeds, P_R, the S feed without G_S and its hold, the trigger chain, DP's seven blocks
and p10_v's two (fixture) + the 13 blocks of s_inputs.py as a scratch spec:
library/mechanics/close_s_inputs_probe.redstone.yaml. Each test opens the door on the input, drops the input and
checks, after the ticks that decide it, that the cells the close moves or must leave alone are what the simulator
has after that tick, with the levels of DT, DS, DP, the tap, p10_v's dusts and the feed's D_1, D_2 and D_F. No
command follows the input: the only commands of a test are the load's and, in a control, the one that takes a
block out with setblock air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the
build, and without R_F, D_F, R_C or C_F the first test must fail, so the checks are live.
Written and replayed only: the spec has not run on a server.
Run from the repo root: python -m scripts.door2.close_layout.export_s_inputs"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, s_feed as s, trigger as t, dp_off as o, p10_v as pv, s_inputs as si
from scripts.door2.close_layout import export_trigger as xt, export_dp_off as xd
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_s_inputs_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = {f.DT: "dt", s.DS: "ds", f.DP: "dp", o.TAP: "tap", pv.D_V: "dv", pv.NV_IN: "nv_in", pv.NV_V: "nv_v", pv.NV_E: "nv_e",
         pv.NV_P8: "nv_p8", si.D_1: "d1", si.D_2: "d2", si.D_F: "df"}
MINE = set(si.MINE)
# the cells of every earlier step (G_S's and RB_F's parking cell among them: air here) and this one's
ALL = list(dict.fromkeys(xt.CHAIN + xt.LATER + xd.DPC + [pv.D_V, pv.R_V, pv.R_P10, si.R_F, si.R_C, si.Q_C, si.A_C, si.C_F, si.CUT,
                                                        si.Q_F, si.S_2, s.HOLD_G]))
# test name: (cell removed before the opening, last tick, ticks after which cells are checked: 2 is c0, 12 is c10)
TESTS = {
    "one input and no command after it: stages 0 to 4 as before; the feed lit at c10 and F_S out; RB_F at (1,5,1) after "
    "c12; S at (1,3) after c13, out at c14; the cut on the step after c14; RB_F pulled and S spat at c15; RB_F home after "
    "c17": (None, si.LAST, (2, 5, 6, 10, 12, 13, 14, 15, 16, 17, 19, 22), ALL),
    "without the 4-tick repeater nothing reads RB_ST: the feed stays dark, F_S stays in, S lands at (1,3) and stays in, "
    "C stays at (1,2) (control)": (si.R_F, 16, (12, 14, 16, 18), ALL),
    "without the cut stone the step is never cut: F_S and S stay out, RB_F stays at (1,5,1) (control)":
        (si.C_F, 18, (12, 14, 16, 17, 20), ALL),
}


def main():
    b = si.build()
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
        ticks = si.idle(last)
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
        frames = si.noted(w, ticks).frames
        for k, (cmds, (blocks_, moving)) in enumerate(zip(ticks, frames), 1):
            steps += [{"drive": {"in": 0}} if c == DRIVER else setb(c, {"rb": "redstone_block"}.get(st.n, st.n)) for c, st in cmds]
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, cells)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for the S feed's inputs, stage 5 of the 3x3 door's close (door2/close_layout/s_inputs.py). The close "
            "runs from one falling input, no command after it. Written and replayed in the simulator; not yet run on a server. The "
            "design_c door, the close feeds, P_R, the S feed's F_S and RB_F (G_S and its hold are taken out), the trigger chain, "
            "DP's seven blocks and the two of P10 and V are fixture; the design is 13 blocks, here in door coordinates (door + "
            f"{str(off).replace(' ', '')} = spec). The trigger chain's redstone block RB_ST is pushed up to (2,8,0) at c0 and "
            "lands there at the end of c2. R_F, a 4-tick repeater at (2,8,1) facing north on glass, reads it and turns on at "
            "c10. Dust D_1 (2,8,2) on glass and D_2 (1,8,2) on a stone carry the signal to D_F (1,7,3), one step down on the "
            "stone (1,6,3) above F_S: 15, 14, 13. F_S (1,5,3) extends at c10 and stays out; RB_F lands at (1,5,1) at the end of "
            "c12 and lights DS, while S is moving in. S lands on the lit cell at the end of c13 and extends at c14, pushing C "
            "to (1,1). R_C, a 1-tick repeater at (0,8,2) facing east on glass, reads D_2 and powers the stone (-1,8,2) at c12; "
            "A_C, a sticky piston at (-1,8,3) facing east, pushes the stone C_F from (0,8,3) to (1,8,3), above D_F and beside "
            "D_2, where it lands at the end of c14 and cuts the step: D_F reads 0. At c15 F_S retracts and pulls RB_F, DS "
            "reads 0 and S is spat: S retracted at (1,3), C real at (1,1), (1,2) air. RB_F is home at (1,5,2) at the end of "
            "c17. R_F and R_C stay on and A_C out while RB_ST is at (2,8,0); RB_ST's return is not designed. Each test checks "
            "the frame 5 ticks into the opening and the open state, then the cells the close moves or must leave alone and the "
            "levels of DT, DS, DP, the tap, D_V, NV at (-1,4,-4), (-1,3,-1), (5,5,0) and (4,5,0), D_1, D_2 and D_F against the "
            "simulator after c0, c3, c4, c8, c10, c11, c12, c13, c14, c15, c17 and c20 (after c10: R_F on, D_F 13, F_S out, "
            "its head and RB_F moving; after c12: RB_F at (1,5,1), DS 15, A_C out, its head and C_F moving; after c13: S at "
            "(1,3), W_T out; after c14: S out, C moving, C_F at (1,8,3), D_F 0; after c15: F_S, RB_F, S and W_T moving, DS 0; "
            "after c17: RB_F at (1,5,2), F_S in). Controls remove one block with setblock air strict before the opening: R_F "
            "(the feed stays dark, F_S never moves, S lands at (1,3) and stays in, C stays at (1,2)) or C_F (A_C pushes "
            "nothing, D_F stays 13, F_S and S stay out).")
    spec = {"name": "close_s_inputs_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
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
    blocks = d.full_blocks(si.build())
    for y, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, y, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    put = {"air": AIR, "redstone_block": t.RB}
    named = {v: k for k, v in NAMES.items()}
    drops = {"the build": (), "without R_F": (si.R_F,), "without D_F": (si.D_F,), "without R_C": (si.R_C,), "without C_F": (si.C_F,)}
    for label, drop in drops.items():
        failed = []
        for test in spec["tests"]:
            w, _ = d.make_world(si.build(drop=drop))
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
