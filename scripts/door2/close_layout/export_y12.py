"""Export design_c with Y12 sticky, every close step's blocks and the two returns (fixture) + the 8 blocks of y12.py
as a scratch spec: library/mechanics/close_y12_probe.redstone.yaml. Each test opens the door on the input, drops the
input and checks, after the ticks that decide it, that the cells of Y12's corner and of the west side are what the
simulator has after that tick, with the levels of the earlier steps' dusts and of four of NP12's; after the last
tick it checks every cell the close and the returns move or must leave alone.
This is not a design yet: U_Y's hold and B_Y's source are stand-ins. The hold is a redstone block built at (-2,8,2)
(fixture), taken out and set back with setblock strict; the source is a redstone block set and cleared at (-5,3,3)
with plain setblock. Those four commands follow the input; a control leaves two of them out or takes W_Y out with
setblock air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the build, and
with Y12 a plain piston or without U_Y, W_Y, B_Y, S_W, R_F, S_F or D_X the first test must fail, so the checks are live.
Written and replayed only: the spec has not run on a server.
Run from the repo root: python -m scripts.door2.close_layout.export_y12"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, trigger as t, dp_off as o, west_drives as wd, y12 as y
from scripts.door2.close_layout import export_trigger as xt, export_west_drives as xw
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_y12_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = {**xw.NAMES, o.TAP: "np_tap"}
MINE = set(y.MINE)
CORNER = list(dict.fromkeys([*y.CORNER, *xw.WEST]))
CELLS = list(dict.fromkeys(xw.CELLS + CORNER))
# test name: (cell removed before the opening, the hold's two commands, the source's two, last tick, ticks after which
# cells are checked: 2 is c0, 63 is c61)
TESTS = {
    "stand-in hold and source: lift at c61, G home after c63, RB_D left at c65, ARM_Z11 back after c66, Y12 in and armed, A_D never out":
        (None, y.HOLD_AT, y.SRC_AT, y.LAST, (2, 4, 5, 54, 60, 62, 63, 64, 65, 66, 67, 68, 70, 72, 74, 76)),
    "without B_Y's source nothing stands in (-4,3,2): ARM_Z11's landing fires Y12 again at c67 (control)":
        (None, y.HOLD_AT, None, 70, (62, 63, 65, 67, 68, 69, 71, 72)),
    "without W_Y RB_D holds Y12: U_Y lifts ARM_Z11 alone and puts it back, Y12 stays out and NP12 lit (control)":
        (y.W_Y, y.HOLD_AT, None, 70, (60, 62, 63, 65, 66, 68, 72)),
}


def run_test(b, gone, hold, src, last):
    """the build opened and closed with a test's commands: the world's (blocks, moving) after the 5th tick of the
    opening and in the open state, the ticks' input commands, the stand-in commands before each tick (cell, block,
    strict), and (blocks, moving) after each tick from c-1."""
    w, _ = d.make_world(b)
    if gone:
        w.cmd_set_silent(gone, AIR)
    w.run(4)
    w.cmd_set(DRIVER, t.RB)
    w.run(5)
    early = dict(w.b), set(w.be)
    w.run(t.OPEN_TICKS - 5)
    assert not w.be
    opened = dict(w.b)
    ticks, before = y.commands(hold, src, last)
    cmds = {}
    for n in (hold or ()):
        cmds.setdefault(n + 2, []).append((y.HOLD, "air" if n == hold[0] else "redstone_block", True))
    for n in (src or ()):
        cmds.setdefault(n + 2, []).append((y.SRC_B, "redstone_block" if n == src[0] else "air", False))
    return early, opened, cmds, wd.noted(w, ticks, before=before).frames


def main():
    b = y.build()
    blocks = d.full_blocks(b)
    allc = list(blocks) + [DRIVER, y.SRC_B] + list(d.STRICT_ARM)
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
    for yy in range(lo[1], hi[1] + 1):
        rows = []
        for z in range(lo[2], hi[2] + 1):
            rows.append("".join("i" if (x, yy, z) == DRIVER else
                                rev[(state_str(blocks[(x, yy, z)]), (x, yy, z) not in MINE, NAMES.get((x, yy, z)))]
                                if (x, yy, z) in blocks else "." for x in range(lo[0], hi[0] + 1)))
        layers[yy - lo[1]] = "\n".join(rows) + "\n"

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
    for name, (gone, hold, src, last, checked) in TESTS.items():
        assert len(name.encode()) <= 140, name                      # the trace file is named after the test
        early, opened, cmds, frames = run_test(b, gone, hold, src, last)
        cells, corner = [c for c in CELLS if c != gone], [c for c in CORNER if c != gone]
        steps = list(load) + ([setb(gone, "air strict")] if gone else [])
        steps += [{"wait": 4}, {"drive": {"in": 1}}, {"wait": 5}] + seen(*early, xt.FRAME)
        steps += [{"wait": t.OPEN_TICKS - 5}] + seen(opened, set(), xt.FRAME + cells)
        for k, (blocks_, moving) in enumerate(frames, 1):
            steps += [{"drive": {"in": 0}}] * (k == 1)
            steps += [setb(c, what + " strict" * strict) for c, what, strict in cmds.get(k, [])]
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, cells if k == max(checked) else corner)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for the re-arm of Y12, the gate relay of the 3x3 door, after the close (door2/close_layout/y12.py). Not a "
            "design yet: two sources are stand-in commands after the input. Written and replayed in the simulator; not yet run on a "
            "server. The design_c door with Y12 made a sticky piston, every close step's blocks and the two returns are fixture, with "
            f"U_Y's stand-in hold; the design is 8 blocks, here in door coordinates (door + {str(off).replace(' ', '')} = spec). After "
            "the west side's return Y12 (-2,3,2) is out, held by ARM_Z11 on it at (-2,4,2) and by RB_D at (-3,4,2), and gate stone G is "
            "at (-4,3,2). U_Y, a sticky piston at (-2,6,2) facing down, is built out, its head on ARM_Z11, held by a redstone block two "
            "above it at (-2,8,2): the stand-in, taken out before c60 and set back before c63 with setblock strict. W_Y, a sticky piston "
            "at (-3,6,2) facing down above RB_D, is in at rest; stone S_W (-3,7,3) powers it from c52 to c60 through R_F, a 1-tick "
            "repeater at (-4,7,3) that reads stone S_F (-5,7,3) under dust D_X (-6,7,3) on Y_X. B_Y, a piston at (-4,3,3) facing north, "
            "is powered by the second stand-in, a redstone block set at (-5,3,3) before c62 and cleared before c70. The run: P_G's "
            "extension at c58 updates W_Y, which goes out; its head lands on RB_D at the end of c60 and updates it, unpowered since "
            "c60: at c61 it pulls RB_D up. RB12's landing on K at the end of c60 relights NP12, which updates U_Y, unpowered: at c61 "
            "it pulls ARM_Z11 up. With both blocks moving Y12 retracts at c61 and pulls G, which lands at (-3,3,2) at the end of c63 "
            "and puts NP12 out. B_Y's head is in (-4,3,2) from c62. ARM_Z11 and RB_D land one cell up at the end of c63 and U_Y and "
            "W_Y push them down at c64; the DP tap's repeater (-2,6,3), on from c62, turns off at c65 beside W_Y, which leaves RB_D at "
            "(-3,4,2) and retracts; ARM_Z11 lands on Y12 at the end of c66 and Y12, powered, cannot push G into B_Y's head. A_D "
            "(-3,4,3), updated with the tap on when NP12 goes out, cannot push at c64: RB_D is moving into the cell in front of it. "
            "B_Y retracts at c70. At the end Y12 is in, powered by ARM_Z11 and RB_D, G is in its closed cell, NP12 and the tap are "
            "dark, A_D never moved and DP was never lit. In the open state the tap holds W_Y out and it retracts at c2 without "
            "pulling. Each test checks the frame 5 ticks into the opening and the open state, then the cells of Y12's corner and of "
            "the west side and the dust levels against the simulator after the ticks that decide it, and after its last tick every "
            "cell the close and the returns move or must leave alone. Controls: without the second stand-in Y12 fires again at c67; "
            "with W_Y taken out with setblock air strict before the opening (and no second stand-in) U_Y lifts ARM_Z11 alone and "
            "Y12 stays out.")
    spec = {"name": "close_y12_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
            "layers": layers, "tests": tests}

    class Lit(str):
        pass
    yaml.add_representer(Lit, lambda dd, v: dd.represent_scalar("tag:yaml.org,2002:str", v, style="|"))
    spec["layers"] = {yy: Lit(v) for yy, v in sorted(spec["layers"].items())}
    path = os.path.join(HERE, "..", "..", "..", OUT)
    with open(path, "w") as fh:
        yaml.dump(spec, fh, sort_keys=False, width=200)
    print("wrote", OUT, "offset", list(off), "tests", len(tests), "steps", sum(len(x["steps"]) for x in tests))
    replay(path, lo)


def replay(path, lo):
    """the spec's own steps, parsed from the YAML, on the simulator: failed checks per test, per build."""
    spec = yaml.safe_load(open(path))
    cell = lambda xyz: tuple(int(v) + o_ for v, o_ in zip(xyz, lo))
    blocks = d.full_blocks(y.build())
    for yy, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, yy, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    named = {v: k for k, v in NAMES.items()}
    builds = {"the build": {}, "with Y12 a plain piston": dict(y12=t.pis("piston", "west", "Y12")),
              **{f"without {y.NAMES[c]}": dict(drop=(c,)) for c in (y.U_Y, y.W_Y, y.B_Y, y.S_W, y.R_F, y.S_F, y.D_X)}}
    for label, kw in builds.items():
        failed = []
        gone = set(kw.get("drop", ())) | ({y.U_HEAD} if y.U_Y in kw.get("drop", ()) else set())
        for test in spec["tests"]:
            w, _ = d.make_world(y.build(**kw))
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
                        bad += c not in gone and ("moving_piston" if c in w.be else state_str(w.get(c))) != m.group(4)
                    elif c not in d.BLOCKERS and c not in d.STRICT_ARM:      # make_world has set those
                        assert m.group(4) in ("air", "redstone_block"), step
                        (w.cmd_set_silent if m.group(5) else w.cmd_set)(c, AIR if m.group(4) == "air" else y.HOLD_BLOCK if c == y.HOLD else t.RB)
            failed.append(bad)
        print(f"replayed in the simulator, {label}: failed checks per test {failed}")
        assert failed[0] if kw else not any(failed), label


if __name__ == "__main__":
    main()
