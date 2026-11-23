"""Export design_c with Y12 sticky, every close step's blocks, the two returns and Y12's re-arm (fixture) + z11.py's 3
blocks as a scratch spec: library/mechanics/close_z11_probe.redstone.yaml. Each test opens the door on the input,
drops the input and checks, after the ticks that decide it, that the cells of Z11's column, of RB11's park, of P10's
and P11's corner, of Y12's corner and of the west side are what the simulator has after that tick, with the levels
of the earlier steps' dusts; after the last tick it checks every cell the close and the returns move or must leave
alone.
This is not a design yet: H11's second drive is a stand-in, a redstone block set at (-3,6,0) before c56 and taken
out before c61, both with setblock strict. Those two commands follow the input; a control leaves them out or takes
H11 or R11 out with setblock air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the build, and
with H11 a plain piston or without H11, D11 or R11 the first test must fail, so the checks are live.
Written and replayed only: the spec has not run on a server.
Run from the repo root: python -m scripts.door2.close_layout.export_z11"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, west_drives as wd, y12 as y, y12_holds as h, z11 as z
from scripts.door2.close_layout import export_trigger as xt, export_y12_holds as xh
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_z11_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = xh.NAMES
MINE = set(z.MINE)
OWN = [*z.CELLS, z.P10, (-1, 4, 0), (-1, 3, 0), z.P11]                    # Z11's column, RB11's park, the 3 blocks, the stand-in's cell, P10 to V
CORNER = list(dict.fromkeys([*xh.CORNER, *OWN]))
CELLS = list(dict.fromkeys(xh.CELLS + OWN))
# test name: (cell removed before the opening, the stand-in's two commands, ticks after which cells are checked: 2 is c0, 63 is c61)
TESTS = {
    "stand-in drive: H11 spits RB11 at c3, Z11 in at c61, RB11 pulled back after c63, pushed home by D11 after c66, Z11 armed":
        (None, z.HOLD_AT, (2, 4, 5, 6, 7, 10, 12, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 72, 76)),
    "no command after the input: H11 spits RB11 at c3, P10 waits for c8; D11 pushes into the empty cell at c60, Y12 stays out (control)":
        (None, None, (4, 5, 6, 7, 10, 12, 60, 62, 63, 64, 66, 68, 70, 76)),
    "without H11 RB11 holds Z11 out and D11 never moves (control)": (z.H11, z.HOLD_AT, (5, 58, 62, 63, 64, 66, 68, 76)),
    "without R11 RB11 comes back to (-2,5,1) and stays there, (-2,4,1) left empty (control)": (z.R11, z.HOLD_AT, (60, 63, 64, 65, 66, 68, 76)),
}


def run_test(b, gone, hold):
    """the build opened and closed from the input with a test's stand-in commands: the world's (blocks, moving)
    after the 5th tick of the opening and in the open state, the commands before each tick (cell, block), and
    (blocks, moving) after each tick from c-1."""
    w, _ = d.make_world(b)
    if gone:
        w.cmd_set_silent(gone, AIR)
    w.run(4)
    w.cmd_set(DRIVER, t.RB)
    w.run(5)
    early = dict(w.b), set(w.be)
    w.run(t.OPEN_TICKS - 5)
    assert not w.be
    cmds = {}
    for n in (hold or ()):
        cmds.setdefault(n + 2, []).append((z.HOLD, "redstone_block" if n == hold[0] else "air"))
    return early, dict(w.b), cmds, wd.noted(w, pp.idle(z.LAST), before=z.commands(hold)).frames


def main():
    b = z.build()
    blocks = d.full_blocks(b)
    allc = list(blocks) + [DRIVER, z.HOLD] + list(d.STRICT_ARM)
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
        for zz in range(lo[2], hi[2] + 1):
            rows.append("".join("i" if (x, yy, zz) == DRIVER else
                                rev[(state_str(blocks[(x, yy, zz)]), (x, yy, zz) not in MINE, NAMES.get((x, yy, zz)))]
                                if (x, yy, zz) in blocks else "." for x in range(lo[0], hi[0] + 1)))
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
    for name, (gone, hold, checked) in TESTS.items():
        assert len(name.encode()) <= 140, name                      # the trace file is named after the test
        early, opened, cmds, frames = run_test(b, gone, hold)
        cells, corner = [c for c in CELLS if c != gone], [c for c in CORNER if c != gone]
        steps = list(load) + ([setb(gone, "air strict")] if gone else [])
        steps += [{"wait": 4}, {"drive": {"in": 1}}, {"wait": 5}] + seen(*early, xt.FRAME)
        steps += [{"wait": t.OPEN_TICKS - 5}] + seen(opened, set(), xt.FRAME + cells)
        for k, (blocks_, moving) in enumerate(frames, 1):
            steps += [{"drive": {"in": 0}}] * (k == 1)
            steps += [setb(c, what + " strict") for c, what in cmds.get(k, [])]
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, cells if k == max(checked) else corner)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for the return of Z11, the relay under P11's power block, after the close (door2/close_layout/z11.py). Not "
            "a design yet: H11's second drive is a stand-in, two commands after the input. Written and replayed in the simulator; not "
            "yet run on a server. The design_c door with Y12 made a sticky piston, every close step's blocks, the two returns and Y12's "
            f"re-arm are fixture; the design is 3 blocks, here in door coordinates (door + {str(off).replace(' ', '')} = spec). After the "
            "close Z11 (-2,3,1) is out, held by ARM_Z11 (-2,4,2) and by its payload RB11 at (-2,5,1) (QC). H11, a sticky piston at "
            "(-3,5,1) facing east, is fired by DP's pulse: RB_D lands under it in DP's source cell at the end of c2 and leaves at c3, so "
            "H11 pushes RB11 east at c3 and is spat: RB11 rests at (-1,5,1), beside P10, from c3; P11's head is moving through (-1,3,0) "
            "then and P10 waits for c8 as before. Z11, held by ARM_Z11 alone, retracts at c61 when U_Y lifts ARM_Z11 (Y12's re-arm). "
            "The stand-in, a redstone block at (-3,6,0) beside the cell above H11, is set before c56 and taken out before c61 with "
            "setblock strict: W_Y's extension beside H11 at c58 updates it and it goes out into the empty (-2,5,1); Z11's retract at "
            "c61 updates it, unpowered, and it pulls RB11 back into (-2,5,1) (end of c63). D11, a piston at (-2,6,1) facing down, is "
            "powered from c60 to c68 by R11, a 4-tick repeater at (-2,7,2) on U_Y facing south that reads stone S_U (-2,7,3) and points "
            "into the cell above D11: RB11's landing updates it and it pushes RB11 into (-2,4,1) at c64, while ARM_Z11 is moving; "
            "ARM_Z11 lands at the end of c66, RB11 right after it, and Z11, powered again, cannot push RB11 into D11's head; D11 goes "
            "in at c68. At the end Z11 is in, powered by ARM_Z11 and not updated, RB11 at (-2,4,1), (-2,5,1) and (-1,5,1) empty, and "
            "Y12's re-arm is as close_y12_holds_probe has it. Each test checks the frame 5 ticks into the opening and the open state, "
            "then the cells of Z11's column, RB11's park, P10 to V, Y12's corner and the west side and the dust levels against the "
            "simulator after the ticks that decide it, and after its last tick every cell the close and the returns move or must leave "
            "alone. Controls: without the stand-in H11 stays in, R11 comes on at c60 with (-2,5,1) empty and D11's head arrives beside "
            "U_Y's, which retracts a tick early: Y12 stays out; with H11 taken out with setblock air strict before the opening, RB11 "
            "holds Z11 out; with R11 taken out, RB11 comes back to (-2,5,1) and stays there.")
    spec = {"name": "close_z11_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
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
    blocks = d.full_blocks(z.build())
    for yy, text in spec["layers"].items():
        for zz, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, yy, zz)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    named = {v: k for k, v in NAMES.items()}
    builds = {"the build": {}, "with H11 a plain piston": dict(swap={z.H11: t.pis("piston", "east", "H11")}),
              **{f"without {z.NAMES[c]}": dict(drop=(c,)) for c in (z.H11, z.D11, z.R11)}}
    for label, kw in builds.items():
        failed = []
        gone = set(kw.get("drop", ()))
        for test in spec["tests"]:
            w, _ = d.make_world(z.build(**kw))
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
                        assert m.group(4) in ("air", "redstone_block") and m.group(5), step
                        w.cmd_set_silent(c, AIR if m.group(4) == "air" else z.HOLD_BLOCK)
            failed.append(bad)
        print(f"replayed in the simulator, {label}: failed checks per test {failed}")
        assert failed[0] if kw else not any(failed), label


if __name__ == "__main__":
    main()
