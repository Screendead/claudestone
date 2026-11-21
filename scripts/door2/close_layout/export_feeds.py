"""Export design_c (fixture) + the close feeds of feeds.py as a scratch spec: close_feeds_probe.redstone.yaml.
The close's c0 events are emulated by commands between ticks (setblock with updates); see each test.
Run from the repo root: python -m scripts.door2.close_layout.export_feeds"""
import os, sys, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.close_layout import feeds as f
from scripts.door2.close_layout import puller as pr
from scripts.door2.close_layout.feeds import d
from scripts.door2.parts.w1.export_probe import state_str

DRIVER = f.DRIVER
NAMES = {(1, 4, 0): "t", (-2, 2, 0): "p6", (-2, 3, 0): "p11", (0, 5, 0): "p12", (1, 4, -1): "z_t",
         (2, 4, 0): "p7", (3, 4,0): "p8", (-1, 5, 0): "p10", (-1, 3, 0): "s",
         (-2, 1, 0): "p4", f.DT: "dt", f.DP: "dp"}
MINE = set(f.ADDED) | {pr.P_R, pr.HEAD, pr.HOLD}


def main():
    b = pr.build()
    blocks = d.full_blocks(b)
    extra_cells = [DRIVER, f.SRC_T, f.SRC_P] + list(d.STRICT_ARM)
    allc = list(blocks) + extra_cells
    lo = [min(c[i] for c in allc) for i in range(3)]
    hi = [max(c[i] for c in allc) for i in range(3)]
    T = lambda c: (c[0] - lo[0], c[1] - lo[1], c[2] - lo[2])
    glyphs = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZbcdefghjkmnopqrstuvwxyz0123456789!@$%&*+,;:?/<>|~^()[]{}")
    pal = {".": "air", "i": {"input": "in"}}
    rev = {}
    for c, st in sorted(blocks.items()):
        s = state_str(st)
        key = (s, c not in MINE, NAMES.get(c))
        if key not in rev:
            gl = next(glyphs)
            rev[key] = gl
            ent = {"block": s}
            if c not in MINE:
                ent["fixture"] = True
            if NAMES.get(c):
                ent["name"] = NAMES[c]
            pal[gl] = ent if len(ent) > 1 else s
    layers = {}
    for y in range(lo[1], hi[1] + 1):
        rows = []
        for z in range(lo[2], hi[2] + 1):
            row = ""
            for x in range(lo[0], hi[0] + 1):
                c = (x, y, z)
                if c == DRIVER:
                    row += "i"
                elif c in blocks:
                    row += rev[(state_str(blocks[c]), c not in MINE, NAMES.get(c))]
                else:
                    row += "."
            rows.append(row)
        layers[y - lo[1]] = "\n".join(rows) + "\n"

    def at(c):
        X, Y, Z = T(c)
        return f"~{X} ~{Y} ~{Z}"

    def chk(c, what):
        return {"check": f"if block {at(c)} {what}"}

    def setb(c, what):
        return {"run": f"setblock {at(c)} {what}"}

    load = [setb(p, "air strict") for p in d.BLOCKERS]
    load += [setb(p, "redstone_block strict") for p in d.STRICT_ARM]
    load.append({"wait": 4})
    frame = [(x, y, 0) for x in range(3) for y in range(3)]
    opening = [{"drive": {"in": 1}}, {"wait": 16}] + [chk(c, "air") for c in frame] + [
        chk((0, 3, 0), "quartz_block"), chk((1, 3, 0), "quartz_block"), chk((-1, 2, 0), "quartz_block"),
        {"expect": {"t": 0, "p6": 0, "p11": 0, "p12": 1, "z_t": 1, "p7": 0, "p8": 0, "p10": 0, "s": 0}},
        {"level": {"dt": 0, "dp": 0}}]
    quiet = {"p7": 0, "p8": 0, "p10": 0}
    still = [chk((-1, 4, 0), "sticky_piston[facing=east,extended=false]"),
             chk((3, 3, 0), "sticky_piston[facing=west,extended=false]")]
    e0 = [setb((1, 5, -2), "air")]            # stands in for E0: sticky I_A pulls RB_A home in c0 g
    kill = [setb(f.RB12, "air")]              # stands in for K pushing RB12 (NP12 dies, P12 retract queued)

    t_p6 = load + opening + e0 + kill + [
        {"wait": 1}, chk((0, 5, 0), "moving_piston"), chk((0, 3, 0), "air"),
        setb(f.SRC_P, "redstone_block"), {"level": {"dp": 15}},
        {"wait": 1}, {"expect": dict(p6=1, p11=1, **quiet)},
        chk((0, 2, 0), "moving_piston"), chk((0, 3, 0), "moving_piston"), chk((-1, 2, 0), "moving_piston"),
        chk((-1, 3, 0), "moving_piston"), *still,
        {"wait": 2}, chk((0, 2, 0), "quartz_block"), chk((0, 3, 0), "sticky_piston[facing=down,extended=false]"),
        chk((-1, 2, 0), "piston_head"), chk((-1, 3, 0), "piston_head"), {"expect": quiet}, *still]
    t_p6_ctl = load + opening + e0 + [
        setb(f.SRC_P, "redstone_block"), {"wait": 1}, {"expect": {"p6": 1, "p11": 1}},
        {"wait": 2}, chk((1, 3, 0), "quartz_block"), chk((4, 3, 0), "sticky_piston[facing=west,extended=false]")]
    t_t = load + opening + e0 + kill + [
        {"wait": 1}, chk((0, 5, 0), "moving_piston"),
        setb(f.SRC_T, "redstone_block"), setb((1, 6, -1), "air"), {"level": {"dt": 15}},
        {"wait": 1}, chk((1, 4, -1), "moving_piston"), {"expect": dict(t=1, **quiet)},
        chk((1, 2, 0), "moving_piston"), chk((1, 3, 0), "moving_piston"), *still,
        {"wait": 2}, chk((1, 2, 0), "quartz_block"), {"expect": dict(t=1, **quiet)}, *still]
    t_t_nowake = load + opening + e0 + kill + [
        {"wait": 1}, setb(f.SRC_T, "redstone_block"), {"level": {"dt": 15}},
        {"wait": 1}, {"expect": {"t": 0, "z_t": 1}}, chk((1, 3, 0), "quartz_block"),
        {"wait": 2}, {"expect": {"t": 1}}]
    t_t_early = load + opening + e0 + [
        setb(f.SRC_T, "redstone_block"), {"wait": 1}, *kill, {"wait": 3},
        {"expect": {"p12": 1}}, chk((0, 3, 0), "quartz_block")]
    # per-tick opening: frame and slot cells as the simulator has them with the 6 close blocks in place
    from scripts.door2.sim import B as SB
    wsim, _ = d.make_world(b)
    wsim.run(4)
    wsim.cmd_set(DRIVER, SB("rb"))
    cells = frame + [(x, -1, 0) for x in range(3)] + [(x, 3, 0) for x in range(3)] + \
        [(-1, y, 0) for y in range(3)] + [(3, y, 0) for y in range(3)]
    per_tick = load + [{"drive": {"in": 1}}]
    for i in range(18):
        wsim.tick()
        per_tick.append({"wait": 1})
        for c in cells:
            q = wsim.get(c).n == "quartz" and c not in wsim.be
            per_tick.append({"check": f"{'if' if q else 'unless'} block {at(c)} quartz_block"})
    t_pull = load + opening + e0 + kill + [
        {"wait": 1}, setb(f.SRC_T, "redstone_block"), setb(pr.HOLD, "air"),
        {"wait": 1}, chk(pr.P_R, "moving_piston"), chk((1, 4, -1), "moving_piston"), {"expect": dict(t=1, **quiet)},
        chk((1, 2, 0), "moving_piston"), *still,
        {"wait": 2}, chk(pr.HEAD, "redstone_block"), chk(f.RB_T, "air"), chk((1, 2, 0), "quartz_block"),
        {"expect": dict(t=1, **quiet)}, *still]
    t_pull_ctl = load + opening + e0 + kill + [
        {"wait": 1}, setb(pr.HOLD, "air"),
        {"wait": 1}, chk((1, 4, -1), "moving_piston"), {"expect": {"t": 0}},
        {"wait": 2}, chk(pr.HEAD, "redstone_block"), {"expect": {"t": 0}}, chk((1, 3, 0), "quartz_block")]
    desc = ("Scratch probe for the door close (door2/close_layout/feeds.py). The whole design_c door is fixture; the "
            "design is 9 blocks: T's feed (stone (1,6,0), a QC cell of T and P12; dust DT (1,7,0) on it; stone cut "
            "(0,7,0) keeping DT off G12 (0,6,0)) and the P6+P11 feed (stone (-3,3,0): P11 direct, P6 by QC through "
            "P11's cell; dust DP (-3,4,0); stone cut (-3,4,-1) keeping DP off NA (-3,3,-1)). After the opening, the "
            "close's c0 events are emulated by commands between ticks: RB_A (1,5,-2) removed (E0), RB12 removed "
            "(NP12 kill), redstone blocks at (1,7,1) and (-4,4,0) light DT and DP, RB_T (1,6,-1) removed (Z_T's wake), or instead "
            "the hold (4,6,-1) of sticky puller P_R (3,6,-1, facing west, head (2,6,-1)) removed, so P_R pulls RB_T to "
            "(2,6,-1) and Z_T retracts. "
            "Door coords + (4,3,8) = spec coords.")
    spec = {"name": "close_feeds_probe", "description": desc, "traits": ["piston_based"],
            "palette": pal, "layers": layers,
            "tests": [{"name": "opening frame and slots per tick match the simulator", "settle": 20, "steps": per_tick},
                      {"name": "P6 and P11 fire together after P12's retract", "settle": 20, "steps": t_p6},
                      {"name": "P6+P11 feed with NP12 alive pushes the top row (control)", "settle": 20, "steps": t_p6_ctl},
                      {"name": "T fires when Z_T retracts under its lit feed", "settle": 20, "steps": t_t},
                      {"name": "T fires when puller P_R takes RB_T off Z_T", "settle": 20, "steps": t_pull},
                      {"name": "P_R without the T feed retracts Z_T but T stays (control)", "settle": 20, "steps": t_pull_ctl},
                      {"name": "lit T feed alone does not wake T until the spare lands (control)", "settle": 20, "steps": t_t_nowake},
                      {"name": "T feed lit before the NP12 kill holds P12 out (control)", "settle": 20, "steps": t_t_early}]}

    class Lit(str):
        pass
    yaml.add_representer(Lit, lambda dd, s: dd.represent_scalar("tag:yaml.org,2002:str", s, style="|"))
    spec["layers"] = {y: Lit(v) for y, v in sorted(spec["layers"].items())}
    out = os.path.join(HERE, "close_feeds_probe.redstone.yaml")
    yaml.dump(spec, open(out, "w"), sort_keys=False, width=200)
    print("wrote", out, "offset", [-v for v in lo])


if __name__ == "__main__":
    main()
