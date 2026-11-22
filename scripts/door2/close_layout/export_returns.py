"""Export design_c and every close step's blocks (fixture) + returns.py's five what-if blocks as a scratch spec:
library/mechanics/close_returns_probe.redstone.yaml. The five: D9, the down-pusher at (4,5,1) of Z9's return, and
RB_T's four, the down-pusher H_T at (1,9,-1), its glass spacers GA (1,7,-1) and GB (1,6,-1) and the kicker N_T at
(2,6,-3). It measures returns.py's two what-ifs, Z9 returned in place and RB_T returned down the column, each with
its drives stood in for by commands after the input (ARM_Z9 taken out and set back and a redstone block above D9;
redstone blocks beside N_T and above H_T, RB_ST set home). So it is a probe of the mechanisms, not a design: the
design may have no command after the input (RB_T's is rbt_drives.py, probed by close_rbt_drives_probe). Each test opens the door on the input, drops it, checks
after the ticks that decide it the cells the close moves or must leave alone and the what-if's cells against the
simulator; the Z9 tests then give Z9 one update (a glass block set under it and taken out) and check whether it
fires.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the build;
without D9 the first test must fail and without H_T or N_T the fourth, so the checks are live.
Written and replayed only: the spec has not run on a server with these blocks.
Run from the repo root: python -m scripts.door2.close_layout.export_returns"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, returns as r
from scripts.door2.close_layout import export_trigger as xt, export_p9_p8 as x9
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_returns_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = x9.NAMES
MINE = {r.D9, *r.RBT_BLOCKS}
CELLS = list(dict.fromkeys(x9.ALL + [r.Z9, pp.RB9_CLOSED, pp.RB9_OPEN, r.ARM, r.D9, r.SRC, (4, 3, 0)] + r.EAST))
LAST = 32
# test name: (the ticks' commands, ticks after which cells are checked: 2 is c0, 18 is c16; whether Z9 is updated at the end)
TESTS = {
    "Z9 in place, by command: ARM_Z9 out before c13, Z9 in at c16, RB9 over it after c22, D9 pushes it down at c23, ARM_Z9 back "
    "before c27, D9 in at c29: Z9, RB9 and ARM_Z9 as the closed state has them, and Z9 fires on an update":
        (r.z9_ticks(last=LAST), (2, 18, 20, 22, 24, 25, 26, 27, 30, 34), True),
    "the blocker: ARM_Z9 back before c23, Z9 powered at P9's landing (c24) and RB9's (c25), its push stopped by RB9 moving "
    "and by D9's head; Z9 fires on an update after D9 is in": (r.z9_ticks(arm_on=23, last=LAST), (18, 24, 25, 26, 27, 30, 34), True),
    "without D9's source RB9 stays over Z9 and P9's landing at c24 fires Z9 again (control)":
        (r.z9_ticks(src_on=None, src_off=None, last=LAST), (18, 24, 26, 27, 34), True),
    "RB_T home, by command: N_T pulls it north at c34 and K_T retracts, RB_ST home before c37, N_T pushes it back at c38, P_R "
    "takes it at c41, H_T pushes GA, GB and RB_T down at c45": (r.rbt_ticks(), (2, 34, 36, 38, 40, 42, 43, 45, 47, 49, 50, 54, 60), False),
    "without the kick K_T's base lands behind RB_T and wakes W_T, whose head takes RB_T's cell; H_T's push stops on it (control)":
        (r.rbt_ticks(kick=None, home=31, poke=32, back=None, src=(40, 43), spc=None, last=46), (34, 36, 37, 39, 42, 44, 48), False),
    "without H_T's source RB_T stays at (1,6,-1) under the spacers (control)": (r.rbt_ticks(src=None), (36, 45, 49, 54, 60), False),
}


def main():
    b = r.probe_build()
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
        return [{"check": f"if block {at(c)} " + ("moving_piston" if c in moving else state_str(blocks_.get(c, AIR)))}
                for c in cells] + [{"level": {n: blocks_[c].p["power"] for c, n in NAMES.items() if c in blocks_}}]

    load = [setb(p, "air strict") for p in d.BLOCKERS] + [setb(p, "redstone_block strict") for p in d.STRICT_ARM]
    tests = []
    for name, (ticks, checked, update) in TESTS.items():
        w, _ = d.make_world(b)
        steps = list(load)
        w.run(4)
        w.cmd_set(DRIVER, t.RB)
        w.run(5)
        steps += [{"wait": 4}, {"drive": {"in": 1}}, {"wait": 5}] + seen(w.b, set(w.be), xt.FRAME)
        w.run(t.OPEN_TICKS - 5)
        assert not w.be
        steps += [{"wait": t.OPEN_TICKS - 5}] + seen(w.b, set(), xt.FRAME + CELLS)
        x = pp.noted(w, ticks)
        for k, (cmds, (blocks_, moving)) in enumerate(zip(ticks, x.frames), 1):
            steps += [{"drive": {"in": 0}} if c == DRIVER else setb(c, {"rb": "redstone_block"}.get(st.n, st.n)) for c, st in cmds]
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, CELLS)
        if update:
            x.cmd_set(r.POKE, t.GLASS)
            x.cmd_set(r.POKE, AIR)
            x.run(4)
            steps += [setb(r.POKE, "glass"), setb(r.POKE, "air"), {"wait": 4}] + seen(x.b, set(x.be), [r.Z9, pp.RB9_CLOSED, pp.RB9_OPEN, r.D9])
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for the returns of the 3x3 door's close (door2/close_layout/returns.py): Z9, one of design_c's four relays "
            "that face up, re-armed in place, and RB_T pushed home down a column. The drives are stood in for by commands after the "
            "input, so this measures the mechanisms and is not a design. Written and replayed in the simulator; not yet run on a "
            "server with these blocks. The design_c door and every close step's blocks (the close feeds, P_R, the S feed and its "
            "inputs, the trigger chain, DP's seven, P10 and V's two, p9_p8's nine and stone) are fixture; the blocks added are D9, a "
            "piston at (4,5,1) facing down, H_T, a piston at (1,9,-1) facing down, glass GA (1,7,-1) and GB (1,6,-1) under it, and "
            f"N_T, a sticky piston at (2,6,-3) facing south, here in door coordinates (door + {str(off).replace(' ', '')} = spec). "
            "Z9: after the close Z9 is out, held by its arm ARM_Z9 at (5,3,1) "
            "and by RB9 at (4,4,1), above its head, both by QC. ARM_Z9 is taken out by command before c13: when A_9 pushes RB9 "
            "east at c16, Z9 is updated with no power and retracts. A_9 pulls RB9 back over it, RB9 lands at (4,4,1) at the end "
            "of c22 and powers Z9 without updating it. A redstone block set above D9 by command before c21 (D9's stand-in source) "
            "has D9 updated by RB9's landing: it pushes RB9 down at c23, so RB9 is moving when P9's base lands beside Z9 at the end "
            "of c24, and RB9 lands on Z9 at the end of c25. ARM_Z9 is set back by command before c27 (its landing does not update "
            "Z9) and the source taken out before c29 (D9 retracts). Z9 is then in, powered and not updated, RB9 at (4,3,1) and "
            "ARM_Z9 at (5,3,1), as the closed state has them; a glass block set under Z9 and taken out fires it. The second test "
            "sets ARM_Z9 back before c23: Z9 is powered when P9's base lands and when RB9 lands, and its push fails, first on RB9 "
            "moving, then on D9's head in (4,4,1), the cell where the load puts an obsidian blocker. The third has no source for "
            "D9: RB9 stays over Z9 and P9's landing fires Z9 again at c25. "
            "RB_T: Z_T lifts RB_T, GB and GA together at t3, so after the close GB is at (1,7,-1), GA at (1,8,-1) and RB_T at "
            "(2,6,-1), where P_R's pull left it and where it holds K_T out by QC. A redstone block beside N_T (its stand-in source, "
            "(3,6,-3)) before c32 and out before c34: N_T goes out and in and pulls RB_T north to (2,6,-2); K_T, a sticky piston "
            "since rbt_drives.py, retracts and pulls SPC home to (2,6,0). RB_ST is "
            "taken out of (2,8,0) and set at (3,7,0), its closed cell, before c37: it powers P_R by QC without updating it. The "
            "source again before c38: N_T pushes RB_T back, its landing at the end of c40 updates P_R, and P_R pushes it to (1,6,-1) "
            "at c41; the source out before c43. A redstone block above H_T ((1,10,-1)) before c45: H_T pushes GA, GB and RB_T down "
            "one cell and RB_T lands at (1,5,-1) at the end of c47; the block out before c48, H_T retracts. "
            "RB_T, GA, GB, P_R, K_T, SPC, Z_T, W_T and the S feed's cut are then as the closed state has "
            "them. The fifth test leaves the kick out (RB_ST home before c31, a glass block set and cleared beside P_R before c32): "
            "K_T's base lands in the same tick as RB_T, behind it, and wakes W_T, which RB_T at (1,6,-1) powers by QC; W_T's head "
            "takes (1,5,-1) and H_T's push at c40 stops on it. The sixth has no source for H_T: RB_T stays at (1,6,-1). "
            "Each test checks the frame 5 ticks into the opening and "
            "the open state, then the cells the close moves or must leave alone, the what-ifs' cells and the levels of DT, DS, DP, "
            "the tap, D_V, NV's four dusts, D_1, D_2, D_F, LY and D_8 against the simulator after the ticks that decide it, and in "
            "the Z9 tests Z9, RB9's two cells and D9 four ticks after the update.")
    spec = {"name": "close_returns_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
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
    """the spec's own steps, parsed from the YAML, on the simulator: failed checks per test, with and without D9."""
    spec = yaml.safe_load(open(path))
    cell = lambda xyz: tuple(int(v) + o_ for v, o_ in zip(xyz, lo))
    blocks = d.full_blocks(r.probe_build())
    for y, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, y, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    put = {"air": AIR, "redstone_block": t.RB, "glass": t.GLASS}
    named = {v: k for k, v in NAMES.items()}
    for label, b, must_fail in (("the build", r.probe_build(), None), ("without D9", r.probe_build(drop=(r.D9,)), 0),
                                ("without H_T", r.probe_build(drop=(r.H_T,)), 3), ("without N_T", r.probe_build(drop=(r.N_T,)), 3)):
        failed = []
        for test in spec["tests"]:
            w, _ = d.make_world(b)
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
                        bad += ("moving_piston" if c in w.be else state_str(w.get(c))) != m.group(4)
                    elif not m.group(5):
                        w.cmd_set(c, put[m.group(4)])
                    elif c not in d.BLOCKERS and c not in d.STRICT_ARM:
                        raise AssertionError(step)
            failed.append(bad)
        print(f"replayed in the simulator, {label}: failed checks per test {failed}")
        assert not any(failed) if must_fail is None else failed[must_fail], label


if __name__ == "__main__":
    main()
