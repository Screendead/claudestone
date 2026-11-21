"""Export design_c and the nine close-feed blocks (fixture) + the S feed of s_feed.py as a scratch spec:
library/mechanics/close_s_feed_probe.redstone.yaml. Each test opens the door, replays one of s_feed.py's
staged schedules by commands between ticks (setblock with updates) and checks, after the ticks that decide it,
that the cells the close moves or must leave alone are what the simulator has after that tick.
After writing, the YAML is read back and its steps replayed in the simulator: every test must pass on the
build; without F_S or without RB_F tests A, B and C must fail; without G_S A must fail and B and C pass
(checks on the removed block's own cells left out), so the checks are live.
Run from the repo root: python -m scripts.door2.close_layout.export_s_feed"""
import os, re, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f, s_feed as s
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str
from scripts.door2.sim import AIR

OUT = os.path.join("library", "mechanics", "close_s_feed_probe.redstone.yaml")
DRIVER = f.DRIVER
NAMES = {s.DS: "ds"}
MINE = set(s.ADDED)
STAND_INS = [s.SRC_F, s.SRC_10, s.SRC_V, s.POKE, f.SRC_T, f.SRC_P]
FRAME = [(x, y, 0) for x in range(3) for y in range(3)]
# the cells the close moves through stage 5 or must leave alone, and the feed's own
WATCH = [(1, 3, 0), (1, 2, 0), (1, 1, 0), (1, 4, 0), (0, 3, 0), (-1, 3, 0), (0, 4, 0), (0, 5, 0),
         s.P7, (2, 3, 0), (3, 4, 0), (3, 3, 0), (3, 2, 0), s.LIT, s.RB_F, s.F_S, s.PARK, s.G_S]
# test name: (s_feed schedule, ticks after which WATCH and DS are checked against the simulator)
TESTS = {
    "A: S, spat first, is woken by the dust when RB_F is spat, and spat itself when G_S pulls RB_F out": ("A2", (4, 5, 6, 9)),
    "B: RB_F spat 2 gt before S lands; F_S's second pulse pulls it home and S is spat": ("B", (3, 5, 6, 7, 10)),
    "C: F_S held out, RB_F lands before S; F_S's release pulls it home and S is spat": ("C", (4, 5, 6, 9)),
    "without RB_F S stays in and C stays at (1,2) (control)": ("ctl 1", (5, 9)),
    "RB_F pulled 3 gt after S fires: S pulls C back (control)": ("ctl 3", (5, 8, 11)),
    "RB_F spat before T's retract holds T out, and S never reaches (1,3) (control)": ("ctl 4", (3, 5)),
}


def main():
    b = s.build()
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
                for c in cells] + [{"level": {"ds": blocks_[s.DS].p["power"]}}]

    load = [setb(p, "air strict") for p in d.BLOCKERS] + [setb(p, "redstone_block strict") for p in d.STRICT_ARM]
    load.append({"wait": 4})
    world = f.open_world(b, ticks=16)
    assert not world.be
    opening = [{"drive": {"in": 1}}, {"wait": 16}] + seen(world.b, set(), FRAME + WATCH)

    tests = []
    cases = {**s.CASES, **s.CONTROLS}
    for name, (key, checked) in TESTS.items():
        ticks = cases[key][1][:max(checked)]
        _, _, _, frames = s.run(world, ticks)
        steps = load + opening
        for k, (cmds, (blocks_, moving)) in enumerate(zip(ticks, frames), 1):
            steps += [setb(c, {"rb": "redstone_block"}.get(st.n, st.n)) for c, st in cmds] + [{"wait": 1}]
            if k in checked:
                steps += seen(blocks_, moving, WATCH)
        tests.append({"name": name, "settle": 20, "steps": steps})

    off = tuple(-v for v in lo)
    desc = ("Scratch probe for S's H2 feed in the door close (door2/close_layout/s_feed.py). The whole design_c door "
            "and the nine close-feed blocks of close_feeds_probe are fixture; the design is 5 blocks, here in door "
            f"coordinates (door + {str(off).replace(' ', '')} = spec): sticky piston F_S (1,5,3) facing north; redstone "
            "block RB_F (1,5,2), which F_S pushes to (1,5,1), above the opening's dust DS (1,4,1) on the wall block "
            "beside S's firing cell (1,3,0); sticky piston G_S (3,5,1) facing west, extended, head (2,5,1), which "
            "pulls RB_F out to (2,5,1) when its hold, redstone block (3,6,1), goes. After the opening, the close's "
            "events through stage 5 are emulated by commands between ticks, one stage per tick: k1 RB_A (1,5,-2) and "
            "RB12 removed (E0, NP12 kill: P12 retracts) and a redstone block at (-4,4,0) (P11 and P6 extend, S to "
            "(0,3)); k2 that block removed (P11, P6 spat), a redstone block at (1,7,1) and P_R's hold (4,6,-1) "
            "removed (T extends); k3 the (1,7,1) block removed and glass set and cleared at (1,5,0) above T (T spat, "
            "C real at (1,2); T's retract event is k3 g and T lands at k5 j), a redstone block at (-1,5,1) (P10 "
            "extends, V to (-1,3)); k4 a redstone block at (-1,3,1) and the (-1,5,1) block removed (P10 spat, V lands "
            "lit and pushes S to (1,3)); k5 the (-1,3,1) block removed (V spat: S real at (1,3,0)). F_S is driven by a "
            "redstone block at (1,6,3). Drive A: on k4, off k5 after V's block (S real first, then RB_F spat), G_S's "
            "hold removed k6: S extends at k5 and is spat at k6, C real at (1,1,0), RB_F parked at (2,5,1). Drive B: "
            "on k2, off k3 (RB_F spat right after T's retract), on k6, off k7 (F_S pulls RB_F home): S extends at k5, "
            "spat at k7. Drive C: on k2 (RB_F lands at k4 j), off k6 (pulled home): S extends at k5, spat at k6. Each test "
            "checks the open state, then, after the ticks that decide it, the 18 cells the close moves or must leave "
            "alone and DS's level against the simulator's. T lands at k5 j under a lit DS and stays in because S is "
            "extended below it. Controls: no RB_F, S stays in; a pull 3 gt after S fires, S pulls C back; RB_F spat "
            "before T's retract event, T stays out and S never arrives.")
    spec = {"name": "close_s_feed_probe", "description": desc, "traits": ["piston_based"], "palette": pal,
            "layers": layers, "tests": tests}

    class Lit(str):
        pass
    yaml.add_representer(Lit, lambda dd, v: dd.represent_scalar("tag:yaml.org,2002:str", v, style="|"))
    spec["layers"] = {y: Lit(v) for y, v in sorted(spec["layers"].items())}
    path = os.path.join(HERE, "..", "..", "..", OUT)
    with open(path, "w") as fh:
        yaml.dump(spec, fh, sort_keys=False, width=200)
    print("wrote", OUT, "offset", list(off), "tests", len(tests), "steps", sum(len(t["steps"]) for t in tests))
    replay(path, lo)


def replay(path, lo):
    """the spec's own steps, parsed from the YAML, on the simulator: failed checks per test, per build."""
    spec = yaml.safe_load(open(path))
    cell = lambda xyz: tuple(int(v) + o for v, o in zip(xyz, lo))
    blocks = d.full_blocks(s.build())
    for y, text in spec["layers"].items():
        for z, row in enumerate(text.splitlines()):
            for x, g in enumerate(row):
                c, ent = cell((x, y, z)), spec["palette"][g]
                want = "air" if c == DRIVER else state_str(blocks.get(c, AIR))
                assert (ent if isinstance(ent, str) else ent.get("block", "air")) == want, (c, ent, want)
                assert isinstance(ent, str) or "block" not in ent or ent.get("fixture", False) == (c not in MINE), c
    put = {"air": AIR, "redstone_block": s.RB, "glass": s.GLASS}
    drops = {"the build": (), "without F_S": (s.F_S,), "without RB_F": (s.RB_F,), "without G_S": (s.G_S, s.G_HEAD)}
    for label, drop in drops.items():
        failed = []
        for t in spec["tests"]:
            w, _ = d.make_world(s.build({p: st for p, st in s.ADDED.items() if p not in drop}))
            bad = 0
            for step in t["steps"]:
                (kind, arg), = step.items()
                if kind == "wait":
                    w.run(arg)
                elif kind == "drive":
                    w.cmd_set(DRIVER, s.RB)
                elif kind == "level":
                    bad += w.get(s.DS).p["power"] != arg["ds"]
                else:
                    m = re.fullmatch(r"(?:setblock|if block) ~(\d+) ~(\d+) ~(\d+) (\S+?)( strict)?", arg)
                    c = cell(m.groups()[:3])
                    if kind == "check":
                        bad += c not in drop and ("moving_piston" if c in w.be else state_str(w.get(c))) != m.group(4)
                    elif m.group(5):      # blockers and strict arms: make_world has set them
                        assert c in d.BLOCKERS or c in d.STRICT_ARM, step
                    else:
                        w.cmd_set(c, put[m.group(4)])
            failed.append(bad)
        print(f"replayed in the simulator, {label}: failed checks per test {failed}")
        a_, b_, c_ = failed[:3]
        assert (a_ and not b_ and not c_) if drop == (s.G_S, s.G_HEAD) else (a_ and b_ and c_) if drop else not any(failed), label


if __name__ == "__main__":
    main()
