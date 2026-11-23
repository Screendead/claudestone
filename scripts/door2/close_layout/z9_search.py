"""Where ARM_Z9's mover and D9's source can come from (door coords): the screens behind z9.py. Everything is computed
on z9.py's build without D9's line (D9 and ARM_Z9's two commands kept), in the simulator; nothing here ran on a
server.

1. Every one-step move of ARM_Z9 out of (5,3,1): pushed from the cell behind it or pulled by a sticky piston two cells
   away (built out, its head beside ARM_Z9's cell): what stands in the piston's cell and in the cell ARM_Z9 goes to,
   and what a redstone block there powers. The one free puller cell, (5,1,1), with a sticky piston built out there:
   what powers it in the closed state, in the open state and at every tick of the close.
2. Every cell from which a block powers D9 (beside it, or beside the cell above it, QC): what is there, what a
   redstone block there would power besides D9, and whether a dust there would be updated by LY's death at t0 g.
3. The signals of the run (dust, repeaters, redstone blocks at rest) that are dark in the closed state and at every
   tick of the opening and lit after c22 and c23, the window D9's source needs, with how far each is from D9's cells.
4. Every single block (dust, dot, stone, redstone block, repeater of each facing and delay, piston and sticky piston
   of each facing; dust and repeaters on glass where the cell under them is free) in every free cell up to six steps
   from D9 or from the cell above it, from the input with ARM_Z9's commands: does Z9 go home?
Run from the repo root (sim; about 10 minutes on four cores; it uses every core):
python -m scripts.door2.close_layout.z9_search > scripts/door2/close_layout/z9_search.txt"""
import os, multiprocessing as mp
from scripts.door2.close_layout import feeds as f, trigger as t, p9_p8 as pp, returns as r, rbt_drives as rd, west_drives as wd, y12_holds_search as hs, z11 as z, z9 as n
from scripts.door2.close_layout.feeds import d, B, AIR, power_sources
from scripts.door2.sim import World, DIRS, add, neg

LO, HI = (-6, -3, -8), (7, 11, 5)                                       # the box, 14 x 15 x 14 = 2940
LINE = tuple(n.LINE)


def base(**kw):
    return n.build(drop=LINE, **kw)


def status(c, taken):
    return "free" if c not in taken and not r.plane_or_hall(c) else "taken"


def label(cl, c):
    st = cl.get(c)
    return st.p.get("id") or st.n


def what(cl, c, taken):
    return label(cl, c) if cl.get(c).n != "air" else status(c, taken)


def dist(a, b_):
    return sum(abs(p - q) for p, q in zip(a, b_))


def screen_arm(cl, taken, ref):
    print("== 1. one-step moves of ARM_Z9 out of (5,3,1)")
    for name, dv in DIRS.items():
        away = add(n.ARM, dv)
        for kind, pc in (("push", add(n.ARM, dv, -1)), ("pull", add(n.ARM, dv, 2))):
            facing = name if kind == "push" else [m for m, e in DIRS.items() if e == neg(dv)][0]
            line = f"   {kind} {name}: piston at {pc} facing {facing} ({what(cl, pc, taken)})"
            if kind == "pull":
                line += f", built out with its head at {add(pc, DIRS[facing])} ({what(cl, add(pc, DIRS[facing]), taken)})"
            pw = hs.rb_powers(cl, away) if cl.get(away).n == "air" else None
            line += f"; ARM_Z9 to {away} ({what(cl, away, taken)}" + (f"; a redstone block there powers {pw or 'nothing'}" if pw is not None else "") + ")"
            if kind == "push" and what(cl, pc, taken) == "free":
                res = []
                for kd in ("piston", "sticky_piston"):
                    moved, first = wd.against(base(swap={pc: t.pis(kd, facing, "M")}), ref, {pc})
                    res.append(f"{kd}: " + ("moves in the load" if moved else ("changes " + ", ".join(f"{c} at {k}" for c, k in sorted(
                        first.items(), key=lambda x: wd.tick_key(x[1]))[:3])) if first else "changes nothing"))
                line += " | " + "; ".join(res)
            print(line)
    pul, head = (5, 1, 1), (5, 2, 1)
    b = base(swap={pul: t.pis("sticky_piston", "up", "P_A", ext=True), head: B("piston_head", facing="up", sticky=True)})
    pcl, moved = d.make_world(b)
    op, _ = t.opened(b)
    _, w, _ = n.run(b, arm=None)
    held = []
    for k, (bl, _) in enumerate(w.frames):
        x = World()
        x.b = bl
        held += [k - 1] * bool(power_sources(x, pul))
    print(f"   the puller at {pul}, a sticky piston facing up built out, its head at {head}: moved during load:", moved or "none",
          "| powered in the closed state by", [x for _, x in power_sources(pcl, pul)], "| in the open state by", [x for _, x in power_sources(op, pul)],
          f"| in the close, no command, powered after {len(held)} of the {len(w.frames)} ticks c-1 to c{n.LAST}: ARM_Z9 powers it by QC through its own "
          "head cell, so it never lets go")
    print("   so ARM_Z9 has no mover: (5,2,1) is the only free cell it can go to, and there it powers Z9 directly and holds its own puller out; "
          "(5,3,2) holds LY's glass under the dust (5,4,2), which a redstone block there would light; (5,4,1) is RB9's stroke, beside LY's dust; "
          "(6,3,1) is S_L, (5,3,0) R_9, (4,3,1) Z9's head cell")


def screen_cells(cl, taken):
    print("\n== 2. the cells from which a block powers D9 (4,5,1): beside it, the front (4,4,1) apart, or beside the cell above it (4,6,1)")
    above = n.ABOVE
    cells = [(c, "direct") for c in (add(n.D9, dv) for m, dv in DIRS.items() if m != "down")] + \
            [(c, "QC") for c in (add(above, dv) for m, dv in DIRS.items() if m != "down")]
    for c, how in cells:
        pw = [p for p in hs.rb_powers(cl, c) if not p.startswith("D9")] if cl.get(c).n == "air" else None
        ly = [p for p in pp.LY if dist(c, p) <= 2]
        print(f"   {c} ({how}): {what(cl, c, taken)}" + (f"; a redstone block there also powers {pw or 'nothing else'}" if pw is not None else "")
              + (f"; within two steps of LY's dust {ly}: a dust there is updated at t0 g" if ly else ""))
    print("   D9 itself is beside LY's dust (4,5,2): LY's death at t0 g updates it with (4,4,1) empty, so D9 must be dark then; LY is lit in the closed "
          "state, so nothing that reads LY can power D9")


def screen_signals(cl, w):
    print("\n== 3. signals dark in the closed state and through the opening, lit after c22 and after c23 (the run without D9's line)")
    frames, opening = w.frames, []
    x, _ = d.make_world(base())
    x.run(4)
    x.cmd_set(f.DRIVER, t.RB)
    for k in range(t.OPEN_TICKS):
        x.tick()
        opening.append(dict(x.b))

    def lit(bl, c):
        st = bl.get(c, AIR)
        return st.p.get("power", 0) > 0 if st.n == "redstone_wire" else bool(st.p.get("powered")) if st.n == "repeater" else st.n == "rb"
    targets = [add(n.D9, dv) for m, dv in DIRS.items() if m != "down"] + [add(n.ABOVE, dv) for m, dv in DIRS.items() if m != "down"]
    cells = {c for bl, _ in frames for c, st in bl.items() if st.n in ("redstone_wire", "repeater", "rb")}
    found = []
    for c in sorted(cells):
        if lit(cl.b, c) or any(lit(bl, c) for bl in opening) or not (lit(frames[23][0], c) and lit(frames[24][0], c)):
            continue
        ks = [k - 1 for k, (bl, _) in enumerate(frames) if lit(bl, c)]
        found.append((min(dist(c, q) for q in targets), c, frames[24][0][c], ks))
    for dd, c, st, ks in sorted(found):
        what_ = {"rb": f"a redstone block ({st.p['id']})" if st.p.get("id") else "a redstone block", "repeater": f"a repeater facing {st.p.get('facing')}",
                 "redstone_wire": "dust"}[st.n]
        print(f"   {c} {what_}: lit or at rest there after {rd.spans([f'c{k}' for k in ks])}; "
              f"{dd} steps from the nearest of D9's cells")
    print("   every one lies at x 2 or below; between them and D9's cells stand RB_1 (3,7,1), RB_2 (3,8,1), G_N (3,7,2), ARM_ZS (2,6,2), "
          "R_X (2,5,1), LY at x 3 and the timer's dust at z 3 (z9.py takes the S feed's line round them). R_X (c16 d to c20 d) would do it read by a "
          "2- to 4-tick repeater in its front cell (3,5,1), but that cell is on A_9, whose extension at c16 pops a repeater (z9.txt, what-ifs)")


def job_runs(args):
    name, extra = args
    try:
        b = base(swap=extra)
        _, w, bad = n.run(b)
    except (KeyError, AssertionError):
        return name, "broken"
    if not bad:
        return name, "done"
    return name, "D9 out in time" if any(" D9@" in m and "EXTEND" in m and 22 <= z.pv.tick_of(m) <= 24 for m in z.pv.told(w)) else "no"


def init():
    r.worlds()


def screen_blocks(cl, taken):
    print("\n== 4. one block near D9, on z9.py's build without D9's line, from the input with ARM_Z9's commands")
    skip = {n.D9, n.ABOVE, n.HEAD, n.OPEN, n.ARM, n.Z9, pp.RB9_OUT}
    cells = sorted(c for c in ((x, y_, z_) for x in range(LO[0], HI[0] + 1) for y_ in range(LO[1], HI[1] + 1) for z_ in range(LO[2], HI[2] + 1))
                   if (dist(c, n.D9) <= 6 or dist(c, n.ABOVE) <= 6) and c not in taken and c not in skip and not r.plane_or_hall(c))
    palette = [("dust", B("redstone_wire", power=0, cross=True)), ("dot", B("redstone_wire", power=0, dot=True)), ("stone", t.STONE), ("redstone block", t.RB)]
    palette += [(f"repeater {fc} {k}", rd.rep(fc, k)) for fc in hs.HORIZONTAL for k in (1, 2, 3, 4)]
    palette += [(f"{kd} {fc}", t.pis(kd, fc, "X")) for kd in ("piston", "sticky_piston") for fc in DIRS]
    jobs = []
    for c in cells:
        under = add(c, DIRS["down"])
        for name, st in palette:
            extra = {c: st}
            if st.n in ("redstone_wire", "repeater"):
                us = cl.get(under)
                if us.n == "air":
                    if under in taken or under in skip or r.plane_or_hall(under):
                        continue
                    extra[under] = t.GLASS
                elif not (us.n in ("stone", "glass", "quartz", "obsidian", "rb") or (us.n in ("piston", "sticky_piston") and us.p["facing"] == "down")):
                    continue
            jobs.append((f"{name} at {c}" + (" on glass" if len(extra) > 1 else ""), extra))
    with mp.Pool(os.cpu_count(), initializer=init) as pool:
        res = pool.map(job_runs, jobs, chunksize=8)
    count = {k: sum(v == k for _, v in res) for k in ("done", "D9 out in time", "no", "broken")}
    print(f"   {len(cells)} free cells in the box, {len(jobs)} runs (dust and repeaters only where something can carry them): Z9 home in",
          [m for m, v in res if v == "done"] or "none", "|", "; ".join(f"{k}: {v}" for k, v in count.items()),
          "(broken: the block breaks a dust or a check of the build; 'D9 out in time': D9 pushes at c22 to c24 but the re-arm still fails)")
    print("   the runs in which D9 pushes at c22 to c24:", "; ".join(m for m, v in res if v == "D9 out in time") or "none")


if __name__ == "__main__":
    r.worlds()
    zb = z.build()
    _, zw, _ = z.run(zb)
    bb = base()
    bcl, bw, _ = n.run(bb)
    taken = (hs.taken_by(zb, zw) | hs.taken_by(bb, bw)) - set(LINE)
    ref = list(wd.frames(bb))[1:]
    screen_arm(bcl, taken, ref)
    screen_cells(bcl, taken)
    screen_signals(bcl, bw)
    screen_blocks(bcl, taken)
