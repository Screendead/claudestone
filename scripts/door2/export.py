"""Export the opening as a .redstone.yaml spec (door coords shifted to non-negative)."""
import sys, yaml
import importlib, os
d_mod = importlib.import_module("scripts.door2." + os.environ.get("DESIGN", "design_open"))
globals().update({k: getattr(d_mod, k) for k in dir(d_mod) if not k.startswith("__")})
from scripts.door2.doorkit import ring_cell

DRIVER = (-1, 8, -2)
FIXTURE = {(0, 8, -2), (0, 7, -2)}
SLOTS = [(x, -1) for x in range(3)] + [(x, 3) for x in range(3)] + [(-1, y) for y in range(3)] + [(3, y) for y in range(3)]


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
    if n == "redstone_wire":
        return "redstone_wire"
    if n == "repeater":
        return f"repeater[facing={st.p['facing']},delay={st.p.get('delay', 1)},powered={'true' if st.p['powered'] else 'false'}]"
    return n


def export(b, name="compactB_open"):
    blocks = full_blocks(b)
    allc = list(blocks) + [DRIVER] + list(STRICT_ARM)
    xmin = min(c[0] for c in allc); ymin = min(c[1] for c in allc); zmin = min(c[2] for c in allc)
    xmax = max(c[0] for c in allc); ymax = max(c[1] for c in allc); zmax = max(c[2] for c in allc)
    T = lambda c: (c[0] - xmin, c[1] - ymin, c[2] - zmin)
    glyphs = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZbcdefghijklmnopqrstuvwxyz0123456789!@$%&*+,;:?/<>|~^()[]{}")
    pal = {".": "air"}
    rev = {}
    for c, st in sorted(blocks.items()):
        s = state_str(st)
        key = (s, c in FIXTURE)
        if key not in rev:
            g = next(glyphs)
            rev[key] = g
            pal[g] = {"block": s, "fixture": True} if c in FIXTURE else s
    pal["i"] = {"input": "in"}
    layers = {}
    for y in range(ymin, ymax + 1):
        rows = []
        for z in range(zmin, zmax + 1):
            row = ""
            for x in range(xmin, xmax + 1):
                c = (x, y, z)
                if c == DRIVER:
                    row += "i"
                elif c in blocks:
                    row += rev[(state_str(blocks[c]), c in FIXTURE)]
                else:
                    row += "."
            rows.append(row)
        layers[y - ymin] = "\n".join(rows) + "\n"
    def at(c, what):
        X, Y, Z = T(c)
        return f"if block ~{X} ~{Y} ~{Z} {what}"
    steps = []
    for p in BLOCKERS:
        X, Y, Z = T(p); steps.append({"run": f"setblock ~{X} ~{Y} ~{Z} air strict"})
    for p in STRICT_ARM:
        X, Y, Z = T(p); steps.append({"run": f"setblock ~{X} ~{Y} ~{Z} redstone_block strict"})
    steps.append({"wait": 4})
    frame = [(x, y, 0) for x in range(3) for y in range(3)]
    # closed state intact before the input
    steps += [{"check": at(c, "quartz_block")} for c in frame]
    steps.append({"drive": {"in": 1}})
    steps.append({"wait": 2})                      # after tick t0
    steps += [{"check": at((2, 3, 0), "moving_piston")}, {"check": at((1, 1, 0), "air")},
              {"check": at((1, 2, 0), "moving_piston")}, {"check": at((0, 0, 0), "quartz_block")}]
    steps.append({"wait": 2})                      # after t2
    steps += [{"check": at(c, "air")} for c in [(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0), (2, 1, 0), (0, 2, 0), (1, 1, 0)]]
    steps += [{"check": at((1, 2, 0), "quartz_block")}, {"check": at((2, 2, 0), "quartz_block")}]
    steps.append({"wait": 1})                      # after t3: frame empty
    steps += [{"check": at(c, "air")} for c in frame]
    steps.append({"wait": 5})                      # after t8: open state
    steps += [{"check": at(c, "air")} for c in frame]
    steps += [{"check": at((sx, sy, 0), "quartz_block")} for sx, sy in SLOTS]
    steps += [{"check": at((-1, 3, 0), "sticky_piston[facing=down,extended=false]")},
              {"check": at((3, 3, 0), "sticky_piston[facing=west,extended=false]")},
              {"check": at((0, 5, 0), "sticky_piston[facing=down,extended=true]")},
              {"check": at((-1, 4, 0), "sticky_piston[facing=east,extended=false]")}]
    spec = {"name": name,
            "description": "Design B (mirrored) 3x3 seamless door, opening only: frame empty at t3, slots quartz at t8.",
            "traits": ["piston_based"],
            "palette": pal, "layers": layers,
            "tests": [{"name": "opening", "settle": 20, "steps": steps}]}
    return spec, T


if __name__ == "__main__":
    b = build_open(); route_nets(b)
    out = sys.argv[1] if len(sys.argv) > 1 else "compactB_open.redstone.yaml"
    spec, T = export(b, name=os.path.basename(out).split(".")[0])
    open(out, "w").write(yaml.safe_dump(spec, sort_keys=False, width=1000))
    print("palette", len(spec["palette"]), "layers", len(spec["layers"]))
