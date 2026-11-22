"""Export design_c, the close feeds, P_R and the S feed (fixture) + the trigger chain of trigger.py as a scratch
spec: library/mechanics/close_trigger_probe.redstone.yaml. Each test opens the door on the input, drops the
input and checks, after the ticks that decide it, that the cells the chain moves or must leave alone are what
the simulator has after that tick. Stage 2 and on are still commands between ticks (trigger.staged). The
controls take one block out with setblock air strict before the opening.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the
build, and without K_T, W_T, M_K or the bus dust above P_R the first test must fail, so the checks are live.
Run from the repo root: python -m scripts.door2.close_layout.export_trigger"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, puller as pr, s_feed as s, trigger as t
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_trigger_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = {f.DT: "dt", s.DS: "ds"}
MINE = set(t.MINE)
STAND_INS = [t.SRC_P, s.SRC_10, s.SRC_V, s.SRC_F]
FRAME = [(x, y, 0) for x in range(3) for y in range(3)]
# the cells stages 0 and 1 move or must leave alone
CHAIN = [(1, 4, 0), (1, 3, 0), (1, 2, 0), (0, 5, 0), (0, 4, 0), (0, 3, 0), t.W_T, (1, 5, -1), t.K_T, t.SPC, t.SRC, t.UP,
         t.AP, t.RB_ST, (1, 4, -1), pr.P_R, pr.HEAD, f.RB_T, t.I_A, t.RB_A_HOME, f.RB_A, t.K, f.RB12, t.RB12_UP,
         t.G_UP, t.M_K, (-4, 2, 1), t.WK]
# and those of stages 2 to 5
LATER = [(1, 1, 0), (-1, 3, 0), (-2, 3, 0), (-1, 2, 0), (0, 2, 0), (-2, 2, 0), (-1, 4, 0), (-1, 5, 0), s.P7, (2, 3, 0),
         (2, 2, 0), (3, 4, 0), (3, 3, 0), (3, 2, 0), s.LIT, s.RB_F, s.F_S, s.PARK, s.G_S]
# test name: (cell removed before the opening, schedule, ticks after which cells are checked: 2 is c0)
TESTS = {
    "one input: E0, P_R, the NP12 kill, T's 0-tick and P12's retract in c0; stages 2 to 5 by command":
        (None, t.staged(), (2, 4, 5, 8, 14), CHAIN + LATER),
    "without the spacer K_T moves nothing: the feed stays lit, T and P12 stay out (control)":
        (t.SPC, t.staged(through=2)[:6], (2, 6), CHAIN),
    "without W_T nothing updates T or P12 when the feed dies (control)": (t.W_T, t.staged(through=2)[:6], (2, 6), CHAIN),
    "without the glass beside K the NP12 kill never comes and P11 shoves the top row (control)":
        (t.WK, t.staged(through=2)[:6], (2, 6), CHAIN + [(1, 1, 0), (2, 3, 0), (3, 3, 0), (4, 3, 0)]),
}


def main():
    b = t.build()
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
        return " ".join(f"~{v - o}" for v, o in zip(c, lo))

    def setb(c, what):
        return {"run": f"setblock {at(c)} {what}"}

    def seen(blocks_, moving, cells):
        """checks that the server's cells are the simulator's: block states, moving_piston where a block moves."""
        return [{"check": f"if block {at(c)} " + ("moving_piston" if c in moving else state_str(blocks_.get(c, AIR)))}
                for c in cells] + [{"level": {"dt": blocks_[f.DT].p["power"], "ds": blocks_[s.DS].p["power"]}}]

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
        steps += [{"wait": 4}, {"drive": {"in": 1}}, {"wait": 5}] + seen(w.b, set(w.be), FRAME)
        w.run(t.OPEN_TICKS - 5)
        assert not w.be
        steps += [{"wait": t.OPEN_TICKS - 5}] + seen(w.b, set(), FRAME + cells)
        _, _, frames = t.run(w, ticks)
        for k, (cmds, (blocks_, moving)) in enumerate(zip(ticks, frames), 1):
            steps += [{"drive": {"in": 0}} if c == DRIVER else setb(c, {"rb": "redstone_block"}.get(st.n, st.n)) for c, st in cmds]
            steps.append({"wait": 1})
            if k in checked:
                steps += seen(blocks_, moving, cells)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for the close's trigger chain (door2/close_layout/trigger.py). The design_c door with I_A sticky, "
            "the close feeds, P_R and the S feed are fixture; the design is 36 blocks, here in door coordinates (door + "
            f"{str(off).replace(' ', '')} = spec). A dust bus fed by K_in (1,8,-2) is lit while the input is on. East branch "
            "(2,8,-2), (3,8,-2), (3,8,-1) on stone (3,7,-1) above P_R: P_R's hold. (4,8,-2) on stone (4,7,-2) feeds a 4-tick "
            "repeater (4,7,-1) into piston AP (4,7,0) facing west, which pushes redstone block RB_ST from (3,7,0) to (2,7,0) "
            "beside T's feed dust DT (1,7,0); it lands at t10 j, after T's last update of the opening, so T waits powered "
            "and not updated. West branch from K_in's top, (1,9,-2), (0,10,-2), (0,9,-1), (-1,9,-1), (-2,8,-1), (-3,7,-1), "
            "(-4,6,-1), (-4,5,0), (-4,5,1) on stone (-4,4,1) above sticky piston M_K (-4,3,1) facing down, which holds glass WK (-4,1,1) beside K (-4,1,2), a "
            "piston facing up under RB12, QC-powered by NP12's first dust and armed from the load behind design_c's "
            "blocker at (-4,3,2). A stone cut (-3,5,0) over DP. W_T (1,5,0), a piston facing north "
            "above T, is powered by T's feed stone and blocked by Z_T's head. K_T (2,5,0), a sticky piston facing up, glass "
            "(2,6,0) and RB_ST above it: K_T is QC-powered by RB_ST. The input falls; two ticks later (c0) the repeater "
            "R_in turns off and in that tick's block-event phase: I_A pulls RB_A home, P_R pulls RB_T, M_K pulls WK; Z_T "
            "retracts and K pushes RB12 and gate stone G up (NP12 dies; P12 stays out, QC-powered by the feed stone); "
            "T extends, W_T extends and updates K_T; K_T pushes the glass and RB_ST up, DT dies and K_T, unpowered inside its "
            "own extension, is released at once: the glass is real at (2,7,0), RB_ST moves on to (2,8,0); W_T retracts and "
            "updates T and P12; P12 retracts and pulls the spare, T is spat. After c0 C is real at (1,2), T and P12 "
            "are moving pistons, (1,3) and (0,3) are air and DT reads 0. Stage 2 and on are commands between ticks: "
            "c1 a redstone block at (-3,4,1) (P11 and P6 extend), c2 removed (spat, S real at (0,3)); c3 a redstone "
            "block at (-1,5,1) (P10); c4 removed, blocks at (-1,3,1) (V) and (1,6,3) (F_S); c5 both removed (RB_F spat "
            "to (1,5,1), V spat, S fires at (1,3)); c6 G_S's hold (3,6,1) removed (S spat, C real at (1,1)). NA relights "
            "when RB_A lands (c2 j): P7 is out from c3, P1 to P6 from c4. Each test checks the frame 5 ticks into the "
            "opening and the open state, then the cells the chain moves or must leave alone and the levels of DT and DS "
            "against the simulator. Controls remove one block with setblock air strict before the opening: the glass "
            "under RB_ST (the feed stays lit, T and P12 stay out), W_T (T and P12 get no update), WK (K is not woken, "
            "P12 stays out and P11 shoves the top row).")
    spec = {"name": "close_trigger_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
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
    cell = lambda xyz: tuple(int(v) + o for v, o in zip(xyz, lo))
    blocks = d.full_blocks(t.build())
    for y, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, y, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    put = {"air": AIR, "redstone_block": t.RB}
    named = {v: k for k, v in NAMES.items()}
    drops = {"the build": (), "without K_T": (t.K_T,), "without W_T": (t.W_T,), "without M_K": (t.M_K,),
             "without the dust above P_R": (t.DH,)}
    for label, drop in drops.items():
        failed = []
        for test in spec["tests"]:
            w, _ = d.make_world(t.build(drop=drop))
            bad = 0
            for step in test["steps"]:
                (kind, arg), = step.items()
                if kind == "wait":
                    w.run(arg)
                elif kind == "drive":
                    w.cmd_set(DRIVER, t.RB if arg["in"] else AIR)
                elif kind == "level":
                    bad += sum(w.get(named[n]).p["power"] != v for n, v in arg.items())
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
