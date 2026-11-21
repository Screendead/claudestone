"""Export design_c, the close feeds, P_R, the S feed and the trigger chain (fixture) + DP's seven blocks of
dp_off.py as a scratch spec: library/mechanics/close_dp_off_probe.redstone.yaml. Each test opens the door on the
input, drops the input and checks, after the ticks that decide it, that the cells the close moves or must leave
alone are what the simulator has after that tick, with the levels of DT, DS, DP and the tap. No command stands
in for DP; stages 3 to 5 are commands between ticks (dp_off.staged). The controls take one block out with
setblock air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the
build, and without A_D, Q_D, RB_D or R_D the first test must fail, so the checks are live.
Written and replayed only: the spec has not run on a server.
Run from the repo root: python -m scripts.door2.close_layout.export_dp_off"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, s_feed as s, trigger as t, dp_off as o, export_trigger as xt
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_dp_off_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = {f.DT: "dt", s.DS: "ds", f.DP: "dp", o.TAP: "tap"}
MINE = set(o.MINE)
STAND_INS = [s.SRC_10, s.SRC_V, s.SRC_F]
# DP's own cells and the two door pistons it serves, with the cells they push into
DPC = [o.LIT, o.RB_D, o.A_D, o.R_D, o.Q_D, o.P11, o.P6, (-1, 3, 0), (0, 3, 0), (-1, 2, 0), (0, 2, 0), f.FP]
ALL = list(dict.fromkeys(xt.CHAIN + xt.LATER + DPC))
# test name: (cell removed before the opening, schedule, ticks after which cells are checked: 2 is c0, 5 is c3)
TESTS = {
    "one input: stages 0 and 1 in c0, RB_D in at c2, P11 out and spat in c3, RB_D pulled home; P6 on NA at c4; "
    "stages 3 to 5 by command": (None, o.staged(), (2, 4, 5, 6, 9, 15), ALL),
    "without RB_D the piston pushes nothing: DP stays dark, P11 stays in and S at (-1,3) (control)":
        (o.RB_D, o.staged(through=2)[:8], (2, 4, 5, 8), ALL),
    "without the repeater the piston is never powered (control)": (o.R_D, o.staged(through=2)[:8], (2, 4, 5, 8), ALL),
    "without the tap dust the repeater never turns on (control)": (o.TAP, o.staged(through=2)[:8], (2, 4, 5, 8), ALL),
}


def main():
    b = o.build()
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
        _, _, frames = t.run(w, ticks)
        for k, (cmds, (blocks_, moving)) in enumerate(zip(ticks, frames), 1):
            steps += [{"drive": {"in": 0}} if c == DRIVER else setb(c, {"rb": "redstone_block"}.get(st.n, st.n)) for c, st in cmds]
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, cells)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for DP's on and off, stage 2 of the 3x3 door's close (door2/close_layout/dp_off.py). Written and "
            "replayed in the simulator; not yet run on a server. The design_c door, the close feeds, P_R, the S feed and "
            "the trigger chain are fixture; the design is 7 blocks, here in door coordinates (door + "
            f"{str(off).replace(' ', '')} = spec). Redstone block RB_D rests at (-3,4,2), south of the source cell (-3,4,1) "
            "of DP (-3,4,0), the dust on the stone that powers P11 (-2,3,0); sticky piston A_D (-3,4,3) faces north behind "
            "it. A_D's only power is stone Q_D (-3,6,3), two above it (quasi-connectivity), strongly powered by a 1-tick "
            "repeater R_D (-2,6,3) facing east on glass (-2,5,3). R_D reads the tap, a dust at (-1,6,3) on glass (-1,5,3), "
            "which reads NP12's dust (0,5,3) down the step; the glass passes nothing back. In the opening NP12 lights at "
            "t6 and R_D turns on at t8, updating Q_D's neighbours but not A_D, which waits powered and not updated. The "
            "input falls; two ticks later (c0) the trigger chain runs stages 0 and 1 in one block-event phase, and K's "
            "event kills NP12: the dust under A_D dies and updates it, R_D is still on, A_D extends. R_D turns off at c2 "
            "with no update of A_D. At the end of c2 RB_D lands at (-3,4,1) and lights DP, whose change updates P11; "
            "then A_D's head lands, which updates A_D, now unpowered. In c3's block-event phase P11 extends, A_D pulls "
            "RB_D (a moving block at once, DP 0), and DP's change updates P11, which is spat: S real at (0,3). P6's "
            "extension, queued by P11's, finds its feed dark and is dropped; P6 extends at c4 on NA's repeater with P1 "
            "to P5 and stays out. RB_D and A_D are home after c5. Stages 3 to 5 are commands between ticks, one tick "
            "later than in close_trigger_probe: c4 a redstone block at (-1,5,1) (P10); c5 removed, blocks at (-1,3,1) (V) "
            "and (1,6,3) (F_S); c6 both removed (RB_F spat to (1,5,1), V spat, S fires at (1,3)); c7 G_S's hold (3,6,1) "
            "removed (S spat, C real at (1,1)). Each test checks the frame 5 ticks into the opening and the open state, "
            "then the cells the close moves or must leave alone and the levels of DT, DS, DP and the tap against the "
            "simulator after c0, c2, c3 and later ticks (after c2: RB_D at (-3,4,1), A_D out, DP 15, R_D off; after c3: "
            "RB_D and P11 moving, S at (0,3), DP 0). Controls remove one block with setblock air strict before the "
            "opening: RB_D (DP stays dark, P11 stays in), the repeater (A_D is never powered), the tap dust (the "
            "repeater never turns on).")
    spec = {"name": "close_dp_off_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
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
    blocks = d.full_blocks(o.build())
    for y, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, y, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    put = {"air": AIR, "redstone_block": t.RB}
    named = {v: k for k, v in NAMES.items()}
    drops = {"the build": (), "without A_D": (o.A_D,), "without Q_D": (o.Q_D,), "without RB_D": (o.RB_D,),
             "without R_D": (o.R_D,)}
    for label, drop in drops.items():
        failed = []
        for test in spec["tests"]:
            w, _ = d.make_world(o.build(drop=drop))
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
