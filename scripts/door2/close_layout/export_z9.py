"""Export design_c with Y12 sticky, every close step's blocks, the two returns, Y12's re-arm and Z11's return (fixture)
+ z9.py's 25 blocks as a scratch spec: library/mechanics/close_z9_probe.redstone.yaml. Each test opens the door on the
input, drops the input and checks, after the ticks that decide it, that the cells of Z9's column, of ARM_Z9's, of D9
and its line, of A_9, P9 and RB9's stroke and of Z11's and Y12's corner are what the simulator has after that tick,
with the levels of the earlier steps' dusts and of the line's; after the last tick it checks every cell the close and
the returns move or must leave alone. The first test then gives Z9 one update (a glass block set under it and taken
out) and checks that it fires.
This is not a design yet: ARM_Z9's mover is a stand-in, ARM_Z9 taken out before c13 and set back before c27 by
setblock with updates; z11.py's stand-in for H11's pull (setblock strict before c56 and c61) is there as before. A
control leaves ARM_Z9's commands out or takes R9_1 out with setblock air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the build, and
without D9 or any of the line's repeaters, dust or stones the first test must fail, so the checks are live.
Written and replayed only: the spec has not run on a server.
Run from the repo root: python -m scripts.door2.close_layout.export_z9"""
import copy, os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, returns as r, west_drives as wd, z11 as z, z9 as n
from scripts.door2.close_layout import export_trigger as xt, export_z11 as xz
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_z9_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = {**xz.NAMES, **{c: f"z9_w{k}" for k, c in enumerate(n.W9, 1)}, (2, 8, 2): "s_line"}
MINE = set(n.MINE)
OWN = [*n.CELLS, n.ABOVE, pp.RB9_OUT, pp.A_9, pp.P9, pp.R_X, pp.R_9, (4, 3, 0), r.POKE]   # Z9's column, ARM_Z9, D9 and its line, A_9, P9, RB9's stroke
CORNER = list(dict.fromkeys([*xz.CORNER, *OWN]))
CELLS = list(dict.fromkeys(xz.CELLS + OWN))
LAST = n.LAST
# test name: (cell removed before the opening, ARM_Z9's commands, ticks after which cells are checked: 2 is c0, 25 is c23; whether Z9 is updated at the end)
TESTS = {
    "ARM_Z9 out and back by command: Z9 in at c16, D9 on its line from c20, pushes RB9 down at c23, in at c52; Z9 fires on an update":
        (None, n.ARM_AT, (2, 14, 18, 22, 24, 25, 26, 27, 28, 29, 32, 46, 52, 54, 56, 76), True),
    "without R9_1 the line stays dark, D9 never moves and P9's landing fires Z9 again at c25 (control)":
        (n.R9_1, n.ARM_AT, (14, 18, 22, 24, 26, 27, 28, 76), False),
    "no command for ARM_Z9: Z9 stays out, D9 is powered from c20 to c51 and its pushes fail (control)":
        (None, None, (18, 22, 24, 25, 26, 54, 76), False),
}


def run_test(b, gone, arm):
    """the build opened and closed from the input with ARM_Z9's and z11.py's stand-in commands: the world's (blocks,
    moving) after the 5th tick of the opening and in the open state, the commands before each tick (cell, block,
    strict), (blocks, moving) after each tick from c-1, and the world after the last."""
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
    for k, what in zip(z.HOLD_AT, ("redstone_block", "air")):
        cmds.setdefault(k + 2, []).append((z.HOLD, what, True))
    for k, what in zip(arm or (), ("air", "redstone_block")):
        cmds.setdefault(k + 2, []).append((n.ARM, what, False))
    before = z.commands()
    for k, fn in n.commands(arm).items():
        before[k] = (lambda g, e: lambda x: (g(x), e(x)))(before[k], fn) if k in before else fn
    x = wd.noted(w, pp.idle(LAST), before=before)
    return early, dict(w.b), cmds, x.frames, x


def poke(x):
    """the world after the run, a glass block set under Z9 and taken out, 4 ticks: (blocks, moving)."""
    y = copy.deepcopy(x)
    y.cmd_set(r.POKE, t.GLASS)
    y.cmd_set(r.POKE, AIR)
    y.run(4)
    return dict(y.b), set(y.be)


def main():
    b = n.build()
    blocks = d.full_blocks(b)
    allc = list(blocks) + [DRIVER, z.HOLD, r.POKE] + list(d.STRICT_ARM)
    lo = [min(c[i] for c in allc) for i in range(3)]
    hi = [max(c[i] for c in allc) for i in range(3)]
    glyphs = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZbcdefghjkmnopqrstuvwxyz0123456789!@$%&*+,;:?/<>|~^()[]{}αβγδεζηθκλμνξπρστυφχψω")
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
                for c in cells] + [{"level": {nm: blocks_[c].p["power"] for c, nm in NAMES.items() if c in blocks_}}]

    load = [setb(p, "air strict") for p in d.BLOCKERS] + [setb(p, "redstone_block strict") for p in d.STRICT_ARM]
    tests = []
    for name, (gone, arm, checked, poked) in TESTS.items():
        assert len(name.encode()) <= 140, name                      # the trace file is named after the test
        early, opened, cmds, frames, x = run_test(b, gone, arm)
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
        if poked:
            steps += [setb(r.POKE, "glass"), setb(r.POKE, "air"), {"wait": 4}] + seen(*poke(x), [n.Z9, n.HEAD, n.OPEN, n.D9, r.POKE])
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for Z9's re-arm in place after the close, D9's source made of blocks (door2/close_layout/z9.py). Not a design "
            "yet: ARM_Z9's mover is a stand-in, two commands after the input. Written and replayed in the simulator; not yet run on a "
            "server. The design_c door with Y12 made a sticky piston, every close step's blocks, the two returns, Y12's re-arm and "
            "Z11's return (with its stand-in for H11's pull: a redstone block set at (-3,6,0) before c56 and taken out before c61, "
            "setblock strict) are fixture; the design is 25 blocks, here in door coordinates (door + " + str(off).replace(" ", "") +
            " = spec). After the close Z9 (4,2,1), an up relay, is out, held by ARM_Z9 (5,3,1) beside the cell above it (QC) and by "
            "RB9 at (4,4,1). ARM_Z9 is taken out by setblock before c13; RB9's departure at c16 (A_9's push) updates Z9 and it "
            "retracts. A_9 brings RB9 back over it at the end of c22, which powers Z9 without an update. D9, a piston at (4,5,1) "
            "facing down, is powered from c20 by its line: R9_1, a 1-tick repeater at (2,8,3) facing north, reads the S feed's "
            "dust (2,8,2) (lit c10 to c42, from RB_ST at (2,8,0)); dust W9_1 to W9_3 along z 4 at y 8; R9_2 and R9_3, 1-tick "
            "repeaters facing west at (5,8,4) and (6,8,4), past the timer's dust; dust W9_4 (7,8,4); R9_4, a 1-tick repeater "
            "facing south at (7,8,3); dust W9_5 (7,8,2), W9_6 (7,7,1) and W9_7 (6,6,1) stepping down, the first two on stone; "
            "R9_5, a 1-tick repeater at (5,6,1) facing east, pointing into (4,6,1), the cell above D9; ten glass blocks under "
            "the rest. RB9's landing updates D9: it pushes RB9 down at c23, so RB9 is moving when P9's base lands beside Z9 at "
            "the end of c24, and lands on Z9's head cell at the end of c25. ARM_Z9 is set back by setblock before c27; its "
            "landing does not update Z9. R9_5 turns off at c52 and D9 retracts. Z9 is then in, powered and not updated, RB9 at "
            "(4,3,1), ARM_Z9 at (5,3,1), as the closed state has them; a glass block set under Z9 and taken out fires it. "
            "Controls: with R9_1 taken out with setblock air strict before the opening the line stays dark, D9 never moves and "
            "P9's landing fires Z9 again at c25; with no command for ARM_Z9, Z9 stays out and D9's pushes into RB9 over Z9's "
            "head fail. Each test checks the frame 5 ticks into the opening and the open state, then Z9's column, ARM_Z9, D9 and "
            "its line, A_9, P9 and RB9's stroke, Z11's and Y12's corner and the dust levels against the simulator after the "
            "ticks that decide it, and after its last tick every cell the close and the returns move or must leave alone.")
    spec = {"name": "close_z9_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
            "layers": layers, "tests": tests}

    class Lit(str):
        pass
    yaml.add_representer(Lit, lambda dd, v: dd.represent_scalar("tag:yaml.org,2002:str", v, style="|"))
    spec["layers"] = {yy: Lit(v) for yy, v in sorted(spec["layers"].items())}
    path = os.path.join(HERE, "..", "..", "..", OUT)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(spec, fh, sort_keys=False, width=200, allow_unicode=True)
    print("wrote", OUT, "offset", list(off), "tests", len(tests), "steps", sum(len(x["steps"]) for x in tests))
    replay(path, lo)


def replay(path, lo):
    """the spec's own steps, parsed from the YAML, on the simulator: failed checks per test, per build."""
    spec = yaml.safe_load(open(path, encoding="utf-8"))
    cell = lambda xyz: tuple(int(v) + o_ for v, o_ in zip(xyz, lo))
    blocks = d.full_blocks(n.build())
    for yy, text in spec["layers"].items():
        for zz, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, yy, zz)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    named = {v: k for k, v in NAMES.items()}
    put = {"air": AIR, "redstone_block": t.RB, "glass": t.GLASS}
    builds = {"the build": {}, **{f"without {n.NAMES[c]}": dict(drop=(c,)) for c in n.MINE if c not in n.GLASSES}}
    for label, kw in builds.items():
        failed = []
        gone = set(kw.get("drop", ()))
        for test in spec["tests"]:
            w, _ = d.make_world(n.build(**kw))
            bad = 0
            for step in test["steps"]:
                (kind, arg), = step.items()
                if kind == "wait":
                    w.run(arg)
                elif kind == "drive":
                    w.cmd_set(DRIVER, t.RB if arg["in"] else AIR)
                elif kind == "level":
                    bad += sum(w.get(named[nm]).p.get("power") != v for nm, v in arg.items() if named[nm] not in gone)
                else:
                    m = re.fullmatch(r"(?:setblock|if block) ~(\d+) ~(\d+) ~(\d+) (\S+?)( strict)?", arg)
                    c = cell(m.groups()[:3])
                    if kind == "check":
                        bad += c not in gone and ("moving_piston" if c in w.be else state_str(w.get(c))) != m.group(4)
                    elif not m.group(5):
                        w.cmd_set(c, put[m.group(4)])
                    elif c not in d.BLOCKERS and c not in d.STRICT_ARM:      # make_world has set those
                        assert m.group(4) in ("air", "redstone_block"), step
                        w.cmd_set_silent(c, AIR if m.group(4) == "air" else z.HOLD_BLOCK)
            failed.append(bad)
        print(f"replayed in the simulator, {label}: failed checks per test {failed}")
        assert failed[0] if kw else not any(failed), label


if __name__ == "__main__":
    main()
