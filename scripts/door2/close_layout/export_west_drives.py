"""Export design_c, every close step's blocks and rbt_drives.py's 49 (fixture) + the 34 blocks of west_drives.py as a
scratch spec: library/mechanics/close_west_drives_probe.redstone.yaml. Each test opens the door on the input, drops
the input and checks, after the ticks that decide it, that the west side's cells are what the simulator has after
that tick, with the levels of the earlier steps' dusts, of four of the line's and of three of NP12's; after the
last tick it checks every cell the close and the two returns move or must leave alone. No command follows the
input: the only commands of a test are the load's and, in a control, the one that takes a block out with setblock
air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the build,
and without R_W, R_M, A_W, RB_W, P_W, R_X, Y_X, R_G, Y_G, P_G or SPG the first test must fail, so the checks are live.
Written and replayed only: the spec has not run on a server.
Run from the repo root: python -m scripts.door2.close_layout.export_west_drives"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, dp_off as o, west_drives as wd
from scripts.door2.close_layout import export_trigger as xt, export_rbt_drives as xr
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_west_drives_probe.redstone.yaml")
DRIVER = f.DRIVER
H, G12 = (-3, 3, 3), (0, 6, 0)
NAMES = {**xr.NAMES, wd.LINE[0]: "west_w", wd.LINE[1]: "west_m", wd.LINE[3]: "west_s", wd.D_A: "west_a", wd.L: "np_l", H: "np_h", G12: "np_g12"}
MINE = set(wd.MINE)
# the west side: the added blocks and the cells they move through, the column, G's closed cell and Y12, the DP tap and
# its piston and block, P12 with the two cells under it, and W_T with RB_T's two cells east of the door
WEST = list(dict.fromkeys([*wd.CELLS, *wd.COLUMN, wd.G_HOME, wd.Y12, o.R_D, o.Q_D, o.A_D, o.RB_D, wd.P12, (0, 4, 0), wd.V_HEAD,
                           t.W_T, (1, 5, -1), (1, 6, -1)]))
CELLS = list(dict.fromkeys(xr.CELLS + WEST))
# test name: (cell removed before the opening, last tick, ticks after which cells are checked: 2 is c0, 44 is c42)
TESTS = {
    "one input and no command after it: RB12 pulled west at c42, back at c55, down onto K under G after c60, K and M_K in":
        (None, wd.LAST, (2, 5, 36, 44, 46, 52, 54, 55, 57, 58, 60, 62, 64, 68, 70, 72)),
    "without R_M the line stays dark: nothing moves in the west, RB12 stays on K's head (control)": (wd.R_M, 62, (5, 36, 44, 46, 62, 64)),
    "without R_G nothing reaches P_G: RB12 comes back and stays, WK's landing fires K again at c59 (control)":
        (wd.R_G, wd.LAST, (44, 46, 54, 57, 58, 60, 61, 62, 64, 72)),
}


def main():
    b = wd.build()
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
        assert len(name.encode()) <= 140, name                      # the trace file is named after the test
        ticks = pp.idle(last)
        w, _ = d.make_world(b)
        steps = list(load)
        cells, west = CELLS, WEST
        if gone:
            w.cmd_set_silent(gone, AIR)
            steps.append(setb(gone, "air strict"))
            cells, west = [c for c in cells if c != gone], [c for c in west if c != gone]
        w.run(4)
        w.cmd_set(DRIVER, t.RB)
        w.run(5)
        steps += [{"wait": 4}, {"drive": {"in": 1}}, {"wait": 5}] + seen(w.b, set(w.be), xt.FRAME)
        w.run(t.OPEN_TICKS - 5)
        assert not w.be
        steps += [{"wait": t.OPEN_TICKS - 5}] + seen(w.b, set(), xt.FRAME + cells)
        frames = wd.noted(w, ticks).frames
        for k, (cmds, (blocks_, moving)) in enumerate(zip(ticks, frames), 1):
            steps += [{"drive": {"in": 0}} for c, st in cmds]
            assert all(c == DRIVER for c, st in cmds)
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, cells if k == max(checked) else west)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for the return of the west side of the 3x3 door's trigger chain after the close, from the one input with no "
            "command (door2/close_layout/west_drives.py). RB12, K, M_K and WK go back to the closed state; G ends at (-4,3,2), where "
            "the opening puts it (its closed cell holds Y12's head). Written and replayed in the simulator; not yet run on a server. "
            "The design_c door, every close step's blocks and the 49 blocks of the east side's return are fixture; the design is 34 "
            f"blocks, here in door coordinates (door + {str(off).replace(' ', '')} = spec). After the close RB12 is at (-4,3,2) on the "
            "head of K (-4,1,2), which it holds out by QC, G is above it at (-4,4,2), and M_K (-4,3,1) is out, held by RB12, with glass "
            "WK at (-4,1,1) beside K. The kick: P_W, a sticky piston at (-6,3,2) facing east, is built out, its head at (-5,3,2), held "
            "by RB_W, a redstone block at (-6,3,1); A_W, a sticky piston at (-6,4,1) facing down, pushes RB_W down to (-6,2,1) and "
            "pulls it back. The push down: P_G, a sticky piston at (-4,6,2) facing down, over glass SPG (-4,5,2). The timer is one "
            "pulse from the east return's line: R_W, a 4-tick repeater at (1,10,2), reads its dust (2,10,2), lit from c26 to c34; a "
            "dust joins it to R_M (-1,10,2), 4 ticks, on from c42 to c50; eight dusts run from R_M, three at y 10 and then down four "
            "stone steps, to D_A (-6,6,1) on S_A, a stone on A_W. R_X (-6,6,2), 4 ticks, reads D_A and powers stone Y_X (-6,6,3); "
            "R_G (-5,6,3), 4 ticks, reads Y_X and powers stone Y_G (-4,6,3) beside P_G from c58 to c66. The run: at c42 A_W goes out; inside that event P_W, released, "
            "pulls RB12 west, and K and M_K, released by RB12, retract, M_K pulling WK up. At the end of c44 RB12 is at (-5,3,2) and "
            "WK at (-4,2,1). At c50 A_W pulls RB_W back; it lands beside P_W at the end of c52 and P_W goes out at c53, pushing RB12 "
            "back to (-4,3,2), where it lands at the end of c55 and powers M_K, which pushes WK down at c56. At c58 P_G pushes SPG, G "
            "and RB12 down; RB12's leaving releases M_K two ticks after its push, so M_K leaves WK at (-4,1,1) and retracts. At the "
            "end of c60 RB12 lands on K at (-4,2,2) and lights L (-3,2,2), which powers K by QC and updates it: K stays in, G being in "
            "(-4,3,2) above RB12, under SPG and P_G's head. P_G pulls SPG back at c66; it is home at the end of c68. From the end of "
            "c60 the dust H (-3,3,3) reads L, G being off the step: NP12 is lit as in the open state (G12 on P12 at 8), the DP tap's "
            "repeater (-2,6,3) is on from c62, P12 stays in (V's head is under the spare block) and A_D stays in. Each test checks "
            "the frame 5 ticks into the opening and the open state, then the west side's cells and the dust levels against the "
            "simulator after the ticks that decide it, and after its last tick every cell the close and the two returns move or must "
            "leave alone. Controls remove one block with setblock air strict before the opening: R_M (the line stays dark and "
            "nothing moves in the west) or R_G (RB12 is kicked and comes back, P_G stays in, WK lands beside K at the end of c58 "
            "with RB12 two above K, and K goes out again at c59).")
    spec = {"name": "close_west_drives_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
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
    blocks = d.full_blocks(wd.build())
    for y, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, y, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    named = {v: k for k, v in NAMES.items()}
    drops = {"the build": (), **{f"without {wd.NAMES[c]}": (c,) for c in (wd.R_W, wd.R_M, wd.A_W, wd.RB_W, wd.P_W, wd.R_X, wd.Y_X, wd.R_G,
                                                                           wd.Y_G, wd.P_G, wd.SPG)}}
    for label, drop in drops.items():
        failed = []
        for test in spec["tests"]:
            w, _ = d.make_world(wd.build(drop=drop))
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
