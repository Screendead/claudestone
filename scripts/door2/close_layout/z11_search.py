"""Where H11's second drive can come from (door coords): the screens behind z11.py. Everything is computed on
y12_holds.py's build (1) or on z11.py's build without its stand-in (2 and 3), in the simulator; nothing here ran
on a server.

1. Every one-step move of RB11 out of its open cell (-2,5,1): pushed from the cell behind it or pulled by a sticky
   piston two cells away (built out, its head beside RB11's cell). For a pusher in a free cell, whether a
   retracted piston of each kind there changes y12_holds.py's opening or close; what a redstone block in the cell
   it goes to powers. H11 at (-3,5,1) is the only mover whose cells are free and whose block lands where it powers
   nothing that waits: DP's pulse fires it at c3.
2. Every cell from which a block powers H11 (beside it, or beside the cell above it, QC): what is there, what a
   redstone block there powers besides H11, and which waiting pistons a dust there would update (two steps).
3. Every single block (dust, dot, stone, redstone block, repeater of each facing and delay, piston and sticky
   piston of each facing; dust and repeaters on glass where the cell under them is free) in every free cell up to
   six steps from H11 or from the cell above it, on z11.py's build without the stand-in, run from the input with
   no command: does Z11 go home with Y12's re-arm as y12_holds.py has it?
Run from the repo root (sim; about 30 minutes on one core, it uses every core):
python -m scripts.door2.close_layout.z11_search > scripts/door2/close_layout/z11_search.txt"""
import os, multiprocessing as mp
from scripts.door2.close_layout import trigger as t, returns as r, rbt_drives as rd, west_drives as wd, y12_holds as h, y12_holds_search as hs, z11 as z
from scripts.door2.close_layout.feeds import d, B
from scripts.door2.sim import DIRS, add, neg

WAITING = {"W_Y": (-3, 6, 2), "U_Y": (-2, 6, 2), "D11": z.D11, "P_G": (-4, 6, 2), "P10": z.P10, "P11": z.P11, "Z11": z.Z11, "Y12": (-2, 3, 2),
           "M_K": (-4, 3, 1), "A_D": (-3, 4, 3), "B_Y": (-4, 3, 3), "V": (-1, 3, 0)}
LO, HI = (-6, -3, -8), (7, 11, 5)                                       # the box, 14 x 15 x 14 = 2940
BUS = {(-4, 5, 1), (-4, 5, 0), (-4, 6, -1), (-3, 7, -1), (-2, 8, -1)}                 # the bus's west branch, its last dusts


def status(c, taken):
    return "free" if c not in taken and not r.plane_or_hall(c) else "taken"


def label(cl, c):
    st = cl.get(c)
    return st.p.get("id") or st.n


def screen_movers(cl, taken, href):
    print("== 1. one-step moves of RB11 out of (-2,5,1)")
    for name, dv in DIRS.items():
        away = add(z.UP, dv)
        for kind, pc in (("push", add(z.UP, dv, -1)), ("pull", add(z.UP, dv, 2))):
            facing = name if kind == "push" else [n for n, e in DIRS.items() if e == neg(dv)][0]
            head = add(pc, DIRS[facing])
            where = label(cl, pc) if cl.get(pc).n != "air" else status(pc, taken)
            dest = label(cl, away) if cl.get(away).n != "air" else status(away, taken)
            pw = [p for p in hs.rb_powers(cl, away)] if cl.get(away).n == "air" and away not in taken else None
            line = f"   {kind} {name}: piston at {pc} facing {facing} ({where})"
            if kind == "pull":
                line += f", built out with its head at {head} ({label(cl, head) if cl.get(head).n != 'air' else status(head, taken)})"
            line += f"; RB11 to {away} ({dest}" + (f"; a redstone block there powers {pw or 'nothing'}" if pw is not None else "") + ")"
            if kind == "push" and where == "free":
                res = []
                for n in ("piston", "sticky_piston"):
                    b = h.build()
                    b.b[pc] = t.pis(n, facing, "M")
                    moved, first = wd.against(b, href, {pc})
                    res.append(f"{n}: " + ("moves in the load" if moved else ("changes " + ", ".join(f"{c} at {k}" for c, k in sorted(first.items(), key=lambda x: wd.tick_key(x[1]))[:3])) if first else "changes nothing"))
                line += " | " + "; ".join(res)
            print(line)
    print("   (-3,5,1) push east is H11: it changes only (-2,5,1) and (-1,5,1), from c3 (RB_D's pulse in DP's source cell under it). The block at (-1,5,1) "
          "powers P10, out and powered from c8 (z11.txt); at (-3,5,1) it would light the bus's last dust (-4,5,1), at (-2,6,1) and (-2,5,0) "
          "it would power U_Y and P10 or P11")


def screen_cells(cl, taken):
    print("\n== 2. the cells from which a block powers H11 (-3,5,1): beside it, the front (-2,5,1) apart, or beside the cell above it (-3,6,1)")
    above = add(z.H11, DIRS["up"])
    cells = [(c, "direct") for c in (add(z.H11, dv) for n, dv in DIRS.items() if n != "east")] + \
            [(c, "QC") for c in (add(above, dv) for n, dv in DIRS.items() if n != "down")]
    for c, how in cells:
        what = label(cl, c) if cl.get(c).n != "air" else "free, the stand-in's cell" if c == z.HOLD else status(c, taken)
        pw = [p for p in hs.rb_powers(cl, c) if not p.startswith("H11")] if cl.get(c).n == "air" else None
        near = [n for n, p in WAITING.items() if sum(abs(a - b_) for a, b_ in zip(c, p)) <= 2]
        bus = sorted(p for p in BUS if sum(abs(a - b_) for a, b_ in zip(c, p)) == 1) + \
            sorted(p for p in wd.LINE + wd.STEPS if sum(abs(a - b_) for a, b_ in zip(c, p)) == 1)
        print(f"   {c} ({how}): {what}" + (f"; a redstone block there also powers {pw or 'nothing else'}" if pw is not None else "")
              + f"; a dust there would update {near or 'none of the waiting pistons'}" + (f"; beside the bus or the west timer's line at {bus}" if bus else ""))
    print("   so a drive for H11 reaches it only through (-3,6,0), whose neighbours are the bus's stone (-3,6,-1), the bus's dust (-3,7,-1) "
          "beside (-3,7,0), the bus's dust (-4,5,0) under (-4,6,0), CUT_DP and P10's QC cell (-2,6,0) by (-1,6,0); or through (-3,7,1), which powers "
          "W_Y (QC) and D11 (QC); a dust in any of the free ones is within two steps of W_Y")


def job_runs(args):
    name, extra = args
    try:
        b = z.build(swap=extra)
        _, w, bad = z.run(b, hold=None)
    except (KeyError, AssertionError):
        return name, "broken"
    if not bad:
        return name, "done"
    return name, "H11 out in time" if any(" H11@" in m and "EXTEND" in m and 4 <= z.pv.tick_of(m) <= 60 for m in z.pv.told(w)) else "no"


def init():
    r.worlds()


def screen_blocks(cl, taken):
    print("\n== 3. one block near H11, on z11.py's build without the stand-in, from the input, no command")
    above = add(z.H11, DIRS["up"])
    dist = lambda a, b_: sum(abs(p - q) for p, q in zip(a, b_))
    skip = {*z.MINE, z.UP, z.PARK, z.HEAD, z.Z11, (-2, 7, 1)}
    cells = sorted(c for c in ((x, y_, z_) for x in range(LO[0], HI[0] + 1) for y_ in range(LO[1], HI[1] + 1) for z_ in range(LO[2], HI[2] + 1))
                   if (dist(c, z.H11) <= 6 or dist(c, above) <= 6) and all(lo <= v <= hi for v, lo, hi in zip(c, LO, HI)) and c not in taken and c not in skip and not r.plane_or_hall(c))
    palette = [("dust", B("redstone_wire", power=0, cross=True)), ("dot", B("redstone_wire", power=0, dot=True)), ("stone", t.STONE)]
    palette += [(f"repeater {fc} {k}", rd.rep(fc, k)) for fc in hs.HORIZONTAL for k in (1, 2, 3, 4)]
    palette += [(f"{n} {fc}", t.pis(n, fc, "X")) for n in ("piston", "sticky_piston") for fc in DIRS]
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
    count = {k: sum(v == k for _, v in res) for k in ("done", "H11 out in time", "no", "broken")}
    print(f"   {len(cells)} free cells in the box, {len(jobs)} runs (dust and repeaters only where something can carry them): Z11 home and Y12 re-armed in",
          [n for n, v in res if v == "done"] or "none", "|", "; ".join(f"{k}: {v}" for k, v in count.items()),
          "(broken: the block breaks a dust or a check of the build; 'H11 out in time': H11 goes out again from c4 to c60 but the return still fails)")
    print("   the runs in which H11 goes out again from c4 to c60:", "; ".join(n for n, v in res if v == "H11 out in time") or "none")


if __name__ == "__main__":
    r.worlds()
    hb = h.build()
    hcl, hw, _ = h.run(hb)
    href = list(wd.frames(hb))[1:]
    taken = hs.taken_by(hb, hw)
    screen_movers(hcl, taken, href)
    zb = z.build()
    zcl, zw, _ = z.run(zb)
    ztaken = (taken | hs.taken_by(zb, zw)) - {z.HOLD}
    screen_cells(zcl, ztaken)
    screen_blocks(zcl, ztaken)
