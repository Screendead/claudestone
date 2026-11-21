"""Export the whole design_c door (fixtures) + the reduced part 3 (X_C, gate, live side, L0, D_W) as a scratch probe.
Run from the repo root: python -m scripts.door2.parts.w1.export_probe -> scripts/door2/parts/w1/close_wave1_probe.redstone.yaml"""
import os, sys, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
from scripts.door2.parts.w1 import gen_wave1_t as g
from scripts.door2.parts.w1.gen_wave1_t import d, add

DRIVER = (-1, 8, -2)
FIXTURE_RIN = {(0, 8, -2), (0, 7, -2)}
NAMES = {g.X_C: "x_c", g.D_W: "d_w", g.W1[0]: "l0", g.LIVE[1]: "live", (1, 4, -1): "z_t", (0, 5, 0): "p12",
         (1, 7, -2): "i_a", (1, 4, 0): "t"}


def state_str(st):
    n = st.n
    if n == "quartz":
        return "quartz_block"
    if n in ("piston", "sticky_piston"):
        return f"{n}[facing={st.p['facing']},extended={'true' if st.p['extended'] else 'false'}]"
    if n == "piston_head":
        return f"piston_head[facing={st.p['facing']},type={'sticky' if st.p.get('sticky') else 'normal'}]"
    if n == "rb":
        return "redstone_block"
    if n == "repeater":
        return f"repeater[facing={st.p['facing']},delay={st.p.get('delay', 1)},powered={'true' if st.p['powered'] else 'false'}]"
    return n


def main():
    b, mine = g.build()
    blocks = d.full_blocks(b)
    allc = list(blocks) + [DRIVER] + list(d.STRICT_ARM) + [g.ARM_DW]
    lo = [min(c[i] for c in allc) for i in range(3)]
    hi = [max(c[i] for c in allc) for i in range(3)]
    T = lambda c: (c[0] - lo[0], c[1] - lo[1], c[2] - lo[2])
    glyphs = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZbcdefghjkmnopqrstuvwxyz0123456789!@$%&*+,;:?/<>|~^()[]{}")
    pal = {".": "air", "i": {"input": "in"}}
    rev = {}
    for c, st in sorted(blocks.items()):
        s = state_str(st)
        fx = c not in mine
        key = (s, fx, NAMES.get(c))
        if key not in rev:
            gl = next(glyphs)
            rev[key] = gl
            ent = {"block": s}
            if fx:
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
                    row += rev[(state_str(blocks[c]), c not in mine, NAMES.get(c))]
                else:
                    row += "."
            rows.append(row)
        layers[y - lo[1]] = "\n".join(rows) + "\n"

    def at(c):
        X, Y, Z = T(c)
        return f"~{X} ~{Y} ~{Z}"

    def chk(c, what):
        return {"check": f"if block {at(c)} {what}"}

    load = [{"run": f"setblock {at(p)} air strict"} for p in d.BLOCKERS]
    load += [{"run": f"setblock {at(p)} redstone_block strict"} for p in d.STRICT_ARM]
    load.append({"wait": 4})
    frame = [(x, y, 0) for x in range(3) for y in range(3)]
    opening = [{"drive": {"in": 1}},
               {"wave": {"x_c": "0" * 16, "d_w": "0" * 16, "l0": "0" * 16, "live": "1" * 16}}]
    opening += [chk(c, "air") for c in frame]
    scaffold = [{"run": f"setblock {at(g.S_X)} stone strict"},
                {"run": f"setblock {at(g.ARM_DW)} redstone_block strict"}]
    close_wave = {"x_c": "0011111111111", "d_w": "0011111111111", "l0": "0000000000000",
                  "i_a": "1100000000000", "live": "1100000000000", "z_t": "1111111111111", "p12": "1111111111111", "t": "0000000000000"}
    t1 = load + opening + scaffold + [
        {"drive": {"in": 0}}, {"wait": 1},
        chk(g.G_W, "stone"), chk((4, 7, -1), "air"), chk((5, 8, -1), "air"), chk(g.RB_W, "redstone_block"),
        {"level": {"live": 14}},
        {"wait": 1},
        chk(g.G_W, "moving_piston"), chk((4, 7, -1), "moving_piston"), chk(g.S_X, "moving_piston"),
        chk(g.RB_W, "moving_piston"), chk((5, 8, -1), "moving_piston"),
        {"level": {"l0": 0, "live": 0}},
        {"expect": {"x_c": 1, "d_w": 1, "z_t": 1}},
        chk((1, 5, -2), "air"), chk((1, 6, -2), "moving_piston"),
        {"wait": 2},
        chk(g.G_W, "stone"), chk((4, 7, -1), "stone"), chk((5, 8, -1), "redstone_block"), chk(g.RB_W, "stone"),
        {"expect": {"x_c": 1, "d_w": 1, "z_t": 1}}, {"level": {"l0": 0, "live": 0}},
        chk((1, 6, -2), "redstone_block"), chk((1, 6, -1), "redstone_block"),
    ]
    t2 = load + opening + scaffold + [
        {"drive": {"in": 0}},
        {"wave": close_wave}]
    t3 = load + opening + scaffold + [
        {"run": f"setblock {at(g.D_W)} air strict"},
        {"drive": {"in": 0}}, {"wait": 1}, {"level": {"l0": 0, "live": 14}},
        {"wait": 1}, {"level": {"l0": 13, "live": 14}}, {"expect": {"x_c": 1}},
        {"wait": 1}, {"level": {"l0": 13, "live": 14}},
        {"wait": 1}, {"level": {"l0": 0, "live": 14}}, chk(g.G_W, "stone")]
    desc = ("Scratch probe for door part 3 (starter + wave 1), reduced to what design_c's geometry allows: "
            "the whole design_c door with part 1's sticky I_A is fixture; the design is 12 blocks. Starter X_C (door "
            "(1,7,-1), piston east) sits on RB_T (1,6,-1), which powers it. An obsidian blocker at S_X (2,7,-1) keeps it "
            "still through the opening, then is swapped for stone with setblock strict (scaffold). X_C is woken by "
            "I_A's retract base update in c0 g (E0) and pushes S_X and gate G_W (3,7,-1), which opens the step "
            "between live dust (3,7,-2) (fed by RB_W (4,8,-1) via (4,8,-2)) and dead dust L0 (3,6,-1). D_W (2,8,-1), "
            "armed by a strict redstone block at (2,8,0), is woken by the update at X_C's arm cell, after the "
            "gate update, and pushes S_D and RB_W east, so L0 is live only inside c0 g. Door coords + (4,3,8) = spec.")
    spec = {"name": "close_wave1_probe", "description": desc, "traits": ["piston_based"],
            "palette": pal, "layers": layers,
            "tests": [{"name": "close starter and gate in c0", "settle": 20, "steps": t1},
                      {"name": "close waves c-2..c10", "settle": 20, "steps": t2},
                      {"name": "without D_W the gate holds L0 live (control)", "settle": 20, "steps": t3}]}

    class Lit(str):
        pass
    yaml.add_representer(Lit, lambda dd, s: dd.represent_scalar("tag:yaml.org,2002:str", s, style="|"))
    spec["layers"] = {y: Lit(v) for y, v in sorted(spec["layers"].items())}
    out = os.path.join(HERE, "close_wave1_probe.redstone.yaml")
    yaml.dump(spec, open(out, "w"), sort_keys=False, width=200)
    print("wrote", out, "offset", [-v for v in lo])


if __name__ == "__main__":
    main()
