"""Export design_c with Y12 sticky, every close step's blocks and the two returns (fixture) + y12.py's 8 blocks and
y12_holds.py's 14 as a scratch spec: library/mechanics/close_y12_holds_probe.redstone.yaml. Nothing is set by command
after the input. Each test opens the door on the input, drops the input and checks, after the ticks that decide
it, that the cells of Y12's corner, of the west side, of the 22 blocks and of A_C and C_F are what the simulator
has after that tick, with the levels of the earlier steps' dusts, of four of NP12's and of the added dusts; after the last tick it
checks every cell the close and the returns move or must leave alone. A control takes one block out with setblock
air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the build, and
with Y12 a plain piston or without RB_U, H_U, S_U, D_U, D_S, D_Z, R_B, S_B, D_B, S_B2, D_Y, U_Y or W_Y the first test
must fail, so the checks are live.
Written and replayed only: the spec has not run on a server.
Run from the repo root: python -m scripts.door2.close_layout.export_y12_holds"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, trigger as t, dp_off as o, p9_p8 as pp, west_drives as wd, y12 as y, y12_holds as h
from scripts.door2.close_layout import export_trigger as xt, export_west_drives as xw, s_inputs as si
from scripts.door2.close_layout.feeds import d, B
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_y12_holds_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = {**xw.NAMES, o.TAP: "np_tap", h.D_S: "y12h_ds", h.D_U: "y12h_du", h.D_Z: "y12h_dz", h.D_B: "y12h_db", h.D_Y: "y12h_dy"}
MINE = set(y.MINE) | set(h.MINE)
CORNER = list(dict.fromkeys([*y.CORNER, *xw.WEST, *h.MINE, *h.MOVED, si.A_C, si.C_F, si.CUT]))    # A_C and C_F: D_U must not move them
CELLS = list(dict.fromkeys(xw.CELLS + CORNER))
# test name: (cell removed before the opening, ticks after which cells are checked: 2 is c0, 63 is c61)
TESTS = {
    "from the input alone: RB_U out c12 to c46 and c52 to c62, U_Y lit by S_U at c58, the lift at c61, G home after c63, B_Y out c64 to c72":
        (None, (2, 4, 5, 14, 16, 46, 48, 54, 56, 60, 62, 63, 64, 65, 66, 67, 68, 70, 74, 76)),
    "without H_U RB_U stays home: NP12's relight finds U_Y powered, Y12 stays out and A_D goes out at c67 (control)":
        (h.H_U, (54, 60, 62, 63, 65, 66, 69, 76)),
    "without R_B nothing powers B_Y: ARM_Z11's landing at c66 j fires Y12 again at c67 (control)":
        (h.R_B, (64, 66, 68, 69, 71, 76)),
}


def run_test(b, gone):
    """the build opened and closed from the input, no command: the world's (blocks, moving) after the 5th tick of
    the opening and in the open state, and (blocks, moving) after each tick from c-1."""
    w, _ = d.make_world(b)
    if gone:
        w.cmd_set_silent(gone, AIR)
    w.run(4)
    w.cmd_set(DRIVER, t.RB)
    w.run(5)
    early = dict(w.b), set(w.be)
    w.run(t.OPEN_TICKS - 5)
    assert not w.be
    return early, dict(w.b), wd.noted(w, pp.idle(h.LAST)).frames


def main():
    b = h.build()
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
    for name, (gone, checked) in TESTS.items():
        assert len(name.encode()) <= 140, name                      # the trace file is named after the test
        early, opened, frames = run_test(b, gone)
        cells, corner = [c for c in CELLS if c != gone], [c for c in CORNER if c != gone]
        steps = list(load) + ([setb(gone, "air strict")] if gone else [])
        steps += [{"wait": 4}, {"drive": {"in": 1}}, {"wait": 5}] + seen(*early, xt.FRAME)
        steps += [{"wait": t.OPEN_TICKS - 5}] + seen(opened, set(), xt.FRAME + cells)
        for k, (blocks_, moving) in enumerate(frames, 1):
            steps += [{"drive": {"in": 0}}] * (k == 1)
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, cells if k == max(checked) else corner)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for the re-arm of Y12, the gate relay of the 3x3 door, after the close, from blocks "
            "(door2/close_layout/y12_holds.py): nothing is set by command after the input. Written and replayed in the simulator; not yet "
            "run on a server. The design_c door with Y12 made a sticky piston, every close step's blocks and the two returns are fixture; "
            f"the design is y12.py's 8 blocks and y12_holds.py's 14, here in door coordinates (door + {str(off).replace(' ', '')} = spec). "
            "U_Y, a sticky piston at (-2,6,2) facing down, built out on ARM_Z11 (-2,4,2), is held by redstone block RB_U (-1,7,2), beside "
            "the cell above it. H_U, a sticky piston at (-1,7,3) facing north, under A_C, pushes RB_U to (-1,7,1) and pulls it back: from c12 "
            "to c44, while Q_C powers A_C's cell, and from c52 to c60, while stone S_U (-2,7,3) is powered by dust D_U on it, which dust D_S on "
            "S_W lights with S_W (dust D_Z at (-2,8,4) on glass keeps D_U from pointing into A_C). S_U powers U_Y too, so W_Y's extension at "
            "c58 finds it powered; from c60 to c62 nothing does, and NP12's relight at the end of c60 makes U_Y pull ARM_Z11 up at c61 while "
            "W_Y pulls RB_D: Y12 retracts and pulls G home to (-3,3,2) (end of c63). RB_U is home at the end of c62 and U_Y pushes ARM_Z11 "
            "back at c64. R_B, a 3-tick repeater at (-4,6,4) facing north, reads Y_G and powers stone S_B (-4,6,5) from c64 to c72; dust D_B "
            "under it steps down to dust D_Y (-4,4,4), which points into the cell above B_Y: B_Y (-4,3,3) puts its head into (-4,3,2) at "
            "c64, so ARM_Z11's landing on Y12 at the end of c66 cannot fire it, and goes in at c72. A_D never moves; NP12 and the tap end "
            "dark. Each test checks the frame 5 ticks into the opening and the open state, then the cells of Y12's corner, of the west side "
            "and of the 22 blocks and the dust levels against the simulator after the ticks that decide it, and after its last tick every "
            "cell the close and the returns move or must leave alone. Controls: with H_U taken out with setblock air strict before the "
            "opening, U_Y stays out and so does Y12; with R_B taken out, Y12 fires again at c67.")
    spec = {"name": "close_y12_holds_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
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
    blocks = d.full_blocks(h.build())
    for yy, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, yy, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    named = {v: k for k, v in NAMES.items()}
    builds = {"the build": {}, "with Y12 a plain piston": dict(y12=t.pis("piston", "west", "Y12")),
              **{f"without {h.NAMES[c]}": dict(drop=(c,)) for c in (h.RB_U, h.H_U, h.S_U, h.D_U, h.D_S, h.D_Z, h.R_B, h.S_B, h.D_B, h.S_B2, h.D_Y)},
              **{f"without {y.NAMES[c]}": dict(drop=(c,)) for c in (y.U_Y, y.W_Y)}}
    for label, kw in builds.items():
        failed = []
        gone = set(kw.get("drop", ())) | ({y.U_HEAD} if y.U_Y in kw.get("drop", ()) else set())
        for test in spec["tests"]:
            w, _ = d.make_world(h.build(**kw))
            bad = 0
            for step in test["steps"]:
                (kind, arg), = step.items()
                if kind == "wait":
                    w.run(arg)
                elif kind == "drive":
                    w.cmd_set(DRIVER, t.RB if arg["in"] else AIR)
                elif kind == "level":
                    bad += sum(w.get(named[n]).p.get("power") != v for n, v in arg.items() if named[n] not in gone)
                else:
                    m = re.fullmatch(r"(?:setblock|if block) ~(\d+) ~(\d+) ~(\d+) (\S+?)( strict)?", arg)
                    c = cell(m.groups()[:3])
                    if kind == "check":
                        bad += c not in gone and ("moving_piston" if c in w.be else state_str(w.get(c))) != m.group(4)
                    elif c not in d.BLOCKERS and c not in d.STRICT_ARM:      # make_world has set those
                        assert m.group(4) == "air" and m.group(5), step
                        w.cmd_set_silent(c, AIR)
            failed.append(bad)
        print(f"replayed in the simulator, {label}: failed checks per test {failed}")
        assert failed[0] if kw else not any(failed), label


if __name__ == "__main__":
    main()
