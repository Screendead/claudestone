"""Export design_c, the close feeds, P_R, the S feed, the trigger chain and DP's seven blocks (fixture) + the two
blocks of p10_v.py as a scratch spec: library/mechanics/close_p10_v_probe.redstone.yaml. Each test opens the
door on the input, drops the input and checks, after the ticks that decide it, that the cells the close moves or
must leave alone are what the simulator has after that tick, with the levels of DT, DS, DP, the tap, the feed's
dust and NV at R_V, at V and at P8. No command stands in for P10 or V; stage 5 is commands between ticks
(p10_v.staged). The controls take one block out with setblock air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the
build, and without D_V or R_V the first test must fail, so the checks are live.
Written and replayed only: the spec has not run on a server.
Run from the repo root: python -m scripts.door2.close_layout.export_p10_v"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, s_feed as s, trigger as t, dp_off as o, p10_v as pv
from scripts.door2.close_layout import export_trigger as xt, export_dp_off as xd
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_p10_v_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = {f.DT: "dt", s.DS: "ds", f.DP: "dp", o.TAP: "tap", pv.D_V: "dv", pv.NV_IN: "nv_in", pv.NV_V: "nv_v", pv.NV_E: "nv_e",
         pv.NV_P8: "nv_p8"}
MINE = set(pv.MINE)
STAND_INS = [s.SRC_F]
ALL = list(dict.fromkeys(xt.CHAIN + xt.LATER + xd.DPC + [pv.D_V, pv.R_V, pv.R_P10]))
# test name: (cell removed before the opening, schedule, ticks after which cells are checked: 2 is c0, 10 is c8)
TESTS = {
    "one input: stages 0 to 2 as before; P10 out at c8 on NA's repeater; V lands lit at c10, extends at c11 and stays "
    "out; S at (1,3) after c13; stage 5 by command": (None, pv.staged(last=17), (2, 5, 6, 10, 12, 13, 15, 16, 17, 19), ALL),
    "without the feed's dust the repeater reads nothing: NV stays dark, V lands and stays in, S stays at (0,3) (control)":
        (pv.D_V, pv.idle(14), (6, 12, 13, 16), ALL),
    "without the repeater NA's dust powers nothing: NV stays dark, V stays in (control)": (pv.R_V, pv.idle(14), (6, 12, 13, 16), ALL),
}


def main():
    b = pv.build()
    blocks = d.full_blocks(b)
    allc = list(blocks) + [DRIVER] + STAND_INS + list(d.STRICT_ARM)
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
    for name, (gone, ticks, checked, cells) in TESTS.items():
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
        frames = pv.noted(w, ticks).frames
        for k, (cmds, (blocks_, moving)) in enumerate(zip(ticks, frames), 1):
            steps += [{"drive": {"in": 0}} if c == DRIVER else setb(c, {"rb": "redstone_block"}.get(st.n, st.n)) for c, st in cmds]
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, cells)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for P10 and V, stages 3 and 4 of the 3x3 door's close (door2/close_layout/p10_v.py). Written and "
            "replayed in the simulator; not yet run on a server. The design_c door, the close feeds, P_R, the S feed, the "
            "trigger chain and DP's seven blocks are fixture; the design is 2 blocks, here in door coordinates (door + "
            f"{str(off).replace(' ', '')} = spec). A dust D_V at (1,4,-4) stands on the hallway's roof between NA's dusts "
            "(2,4,-4) and (1,4,-3); a 1-tick repeater R_V at (0,4,-4) facing east, on the roof beside it, reads it and "
            "powers NV's dust (-1,4,-4), four dusts up the line from (-1,3,-1), the dust that points south into V's cell "
            "(-1,3,0). NV is the opening's own feed of V, cut at t2 by the stone above (1,6,-6) and dark from then on; "
            "R_V feeds it west of the cut. In the opening NA dies at t0, R_V turns off at t2 ahead of the cut and V "
            "retracts at t3 as before. The input falls; two ticks later (c0) the trigger chain runs stages 0 and 1, and "
            "DP's blocks stage 2 at c3 (S real at (0,3)). NA relights when RB_A lands at the end of c2. R_V turns on at "
            "c4: NV's west branch is lit, 15 at (-1,4,-4) and 12 at (-1,3,-1), 1 at (5,5,0) and 0 at (4,5,0), the dust "
            "that points into P8's quasi-connectivity cell, so P8 stays in. No command drives P10 or V. P10's own "
            "3-tick repeater (-1,5,-1) on NA turns on at c8: P10 extends, pushes V into (-1,3,0) and stays out. V lands "
            "on the lit cell at the end of c10 and extends at c11, pushing S, which lands at (1,3) at the end of c13. V "
            "stays out, its head in (0,3), as in the closed door. Stage 5 is commands between ticks: c12 a redstone "
            "block at (1,6,3) (F_S); c13 removed (RB_F spat to (1,5,1) while S moves in; S lands lit and fires at c14); "
            "c15 G_S's hold (3,6,1) removed (S spat, C real at (1,1)). Each test checks the frame 5 ticks into the "
            "opening and the open state, then the cells the close moves or must leave alone and the levels of DT, DS, "
            "DP, the tap, D_V and NV at (-1,4,-4), (-1,3,-1), (5,5,0) and (4,5,0) against the simulator after c0, c3, c4, "
            "c8, c10, c11, c13, c14, c15 and c17 (after c4: R_V on, (-1,3,0) air; after c8: P10's head and V moving; "
            "after c10: V retracted at (-1,3,0), P10 out; after c11: V out, its head and S moving; after c13: S at "
            "(1,3)). Controls remove one block with setblock air strict before the opening: D_V (R_V never turns on) or "
            "R_V; in both NV stays dark, V lands at (-1,3,0) and stays in, and S stays at (0,3).")
    spec = {"name": "close_p10_v_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
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
    blocks = d.full_blocks(pv.build())
    for y, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, y, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    put = {"air": AIR, "redstone_block": t.RB}
    named = {v: k for k, v in NAMES.items()}
    drops = {"the build": (), "without D_V": (pv.D_V,), "without R_V": (pv.R_V,)}
    for label, drop in drops.items():
        failed = []
        for test in spec["tests"]:
            w, _ = d.make_world(pv.build(drop=drop))
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
