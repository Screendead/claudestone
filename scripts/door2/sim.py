"""Tick-phase simulator of the 26.3 mechanics a piston door uses, transcribed from the
decompiled source (mc/src, mc-src): scheduled ticks (phase d), block events (phase g,
FIFO with dedupe), moving-piston block entities (phase j, list order), neighbour updates
(W,E,D,U,N,S, depth first), pistons with quasi-connectivity, redstone blocks, conductors,
repeaters and legacy dust. No slime/honey, observers, torches or entities.

Block tuples: (name, props-dict-as-frozen-items). Names: air, quartz, stone, glass,
obsidian, rb, piston, sticky_piston, piston_head, moving_piston, repeater, redstone_wire.
Positions are (x, y, z); y up."""
from collections import OrderedDict

W, E, D, U, N, S = (-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)
DIRS = {"west": W, "east": E, "down": D, "up": U, "north": N, "south": S}
NAME = {v: k for k, v in DIRS.items()}
UPDATE_ORDER = [W, E, D, U, N, S]
VALUES = [D, U, N, S, W, E]          # Direction.values()
HORIZ = [N, E, S, W]                 # Direction.Plane.HORIZONTAL order
CONDUCTORS = {"quartz", "stone", "obsidian"}
PUSH_BLOCK = {"obsidian", "piston_head", "moving_piston"}
POPPED = {"redstone_wire", "repeater", "comparator", "redstone_torch", "redstone_wall_torch"}
PRIO = {"EXTREMELY_HIGH": -3, "VERY_HIGH": -2, "HIGH": -1, "NORMAL": 0}


def add(p, d, k=1):
    return (p[0] + k * d[0], p[1] + k * d[1], p[2] + k * d[2])


def neg(d):
    return (-d[0], -d[1], -d[2])


class B:
    __slots__ = ("n", "p")

    def __init__(self, n, **p):
        self.n = n
        self.p = p

    def __eq__(self, o):
        return isinstance(o, B) and self.n == o.n and self.p == o.p

    def __repr__(self):
        return self.n + ("[" + ",".join(f"{k}={v}" for k, v in sorted(self.p.items())) + "]" if self.p else "")

    def w(self, **kw):
        q = dict(self.p)
        q.update(kw)
        return B(self.n, **q)


AIR = B("air")


class BE:
    def __init__(self, pos, moved, direction, extending, source):
        self.pos, self.moved, self.dir, self.extending, self.source = pos, moved, direction, extending, source
        self.progress = self.progressO = 0.0
        self.lastTicked = -1
        self.removed = False


class World:
    def __init__(self):
        self.b = {}
        self.be = {}
        self.tickers = []          # BE list order
        self.sched = []            # (due, prio, sub, pos, name)
        self.sub = 0
        self.events = OrderedDict()
        self.time = 0
        self.handling = False
        self.phase = "-"
        self.log = []
        self.should_signal = True
        self.depth = 0

    # ---------- access ----------
    def get(self, p):
        return self.b.get(p, AIR)

    def is_conductor(self, p):
        return self.get(p).n in CONDUCTORS

    def L(self, msg):
        self.log.append((self.time, self.phase, msg))

    # ---------- setBlock ----------
    def set(self, p, st, flags=3, moved=False):
        old = self.get(p)
        if old == st:
            return
        if st.n == "air":
            self.b.pop(p, None)
        else:
            self.b[p] = st
        if old.n != st.n and p in self.be and old.n == "moving_piston" and st.n != "moving_piston":
            pass
        self.affect_after_removal(p, old, st, bool(flags & 64))
        self.on_place(p, st, old)
        if flags & 1:
            self.update_neighbors(p)

    def affect_after_removal(self, p, old, new, moved):
        if old.n == new.n:
            return
        if old.n in ("repeater", "comparator") and not moved:
            self.update_in_front(p, old)
        if old.n in ("redstone_torch", "redstone_wall_torch"):
            for d in VALUES:
                self.update_neighbors(add(p, d))
        if old.n == "redstone_wire" and not moved:
            for d in VALUES:
                self.update_neighbors(add(p, d))

    def on_place(self, p, st, old):
        if st.n in ("piston", "sticky_piston"):
            if old.n != st.n and p not in self.be:
                self.check_extend(p)
        elif st.n in ("repeater", "comparator"):
            self.update_in_front(p, st)
        elif st.n in ("redstone_torch", "redstone_wall_torch"):
            for d in VALUES:
                self.update_neighbors(add(p, d))
        elif st.n == "redstone_wire" and old.n != "redstone_wire":
            self.wire_update(p)
            self.update_neighbors(add(p, D))
            self.update_neighbors(add(p, U))

    # ---------- neighbour updates ----------
    def update_neighbors(self, p, skip=None):
        for d in UPDATE_ORDER:
            if skip is not None and d == skip:
                continue
            self.neighbor_changed(add(p, d))

    def neighbor_changed(self, p):
        st = self.get(p)
        n = st.n
        if n in ("piston", "sticky_piston"):
            self.check_extend(p)
        elif n == "piston_head":
            base = add(p, neg(DIRS[st.p["facing"]]))
            bs = self.get(base)
            fitting = (bs.n in ("piston", "sticky_piston") and bs.p["facing"] == st.p["facing"] and bs.p["extended"]) or \
                      (bs.n == "moving_piston" and bs.p["facing"] == st.p["facing"])
            if fitting:
                self.neighbor_changed(base)
        elif n in ("repeater", "comparator"):
            self.repeater_check(p, st)
        elif n == "redstone_wire":
            self.wire_update(p)
        elif n in ("redstone_torch", "redstone_wall_torch"):
            lit = st.p.get("lit", True)
            if lit == self.torch_powered(p, st) and not self.will_tick_this_tick(p):
                self.schedule(p, n, 2, "NORMAL")

    def torch_tick(self, p):
        st = self.get(p)
        lit = st.p.get("lit", True)
        pw = self.torch_powered(p, st)
        if lit and pw:
            self.set(p, st.w(lit=False), 3)
            self.L(f"torch {p} off")
        elif not lit and not pw:
            self.set(p, st.w(lit=True), 3)
            self.L(f"torch {p} on")

    def update_in_front(self, p, st):
        f = DIRS[st.p["facing"]]
        front = add(p, neg(f))
        self.neighbor_changed(front)
        self.update_neighbors(front, skip=f)

    # ---------- signals ----------
    def wire_conn(self, p):
        """horizontal dirs the wire at p points to (legacy shape rules)."""
        st = self.get(p)
        up_ok = not self.is_conductor(add(p, U))
        conn = []
        for d in HORIZ:
            q = add(p, d)
            qs = self.get(q)
            c = False
            if up_ok and (self.is_conductor(q) or qs.n in ("glass", "rb")) and self.get(add(q, U)).n == "redstone_wire":
                c = True
            elif qs.n in ("redstone_wire", "rb"):
                c = True
            elif qs.n == "repeater" and DIRS[qs.p["facing"]] in (d, neg(d)):
                c = True
            elif not self.is_conductor(q) and self.get(add(q, D)).n == "redstone_wire":
                c = True
            if c:
                conn.append(d)
        if not conn:
            return [] if st.p.get("dot") else list(HORIZ)
        s = set(conn)
        ns = N not in s and S not in s
        ew = E not in s and W not in s
        if ns:
            s |= {E, W}
        if ew:
            s |= {N, S}
        return list(s)

    def torch_attached(self, p, st):
        if st.n == "redstone_torch":
            return add(p, D), D
        f = DIRS[st.p["facing"]]
        return add(p, neg(f)), neg(f)

    def torch_powered(self, p, st):
        a, d = self.torch_attached(p, st)
        return self.has_signal(a, d)

    def own_signal(self, p, d):
        """getSignal of block at p toward a receiver at p - d (d = receiver->p)."""
        st = self.get(p)
        n = st.n
        if n == "rb":
            return 15
        if n == "redstone_torch":
            return 15 if st.p.get("lit", True) and d != U else 0
        if n == "redstone_wall_torch":
            return 15 if st.p.get("lit", True) and DIRS[st.p["facing"]] != d else 0
        if n in ("repeater", "comparator"):
            return 15 if st.p["powered"] and DIRS[st.p["facing"]] == d else 0
        if n == "redstone_wire":
            if not self.should_signal or d == D:
                return 0
            pw = st.p.get("power", 0)
            if pw == 0:
                return 0
            if d == U:
                return pw
            return pw if neg(d) in self.wire_conn(p) else 0
        return 0

    def direct_signal(self, p, d):
        st = self.get(p)
        if st.n in ("redstone_torch", "redstone_wall_torch"):
            return self.own_signal(p, d) if d == D else 0
        if st.n in ("repeater", "comparator"):
            return self.own_signal(p, d)
        if st.n == "redstone_wire":
            return self.own_signal(p, d) if self.should_signal else 0
        return 0

    def direct_signal_to(self, p):
        return max(self.direct_signal(add(p, d), d) for d in VALUES)

    def signal(self, p, d):
        s = self.own_signal(p, d)
        if self.is_conductor(p):
            s = max(s, self.direct_signal_to(p))
        return s

    def has_signal(self, p, d):
        return self.signal(p, d) > 0

    def best_neighbor_signal(self, p):
        return max(self.signal(add(p, d), d) for d in VALUES)

    # ---------- dust ----------
    def wire_update(self, p):
        st = self.get(p)
        if st.n != "redstone_wire":
            return
        self.should_signal = False
        bs = self.best_neighbor_signal(p)
        self.should_signal = True
        target = bs
        if bs < 15:
            ws = 0
            above_cond = self.is_conductor(add(p, U))
            for d in HORIZ:
                q = add(p, d)
                ws = max(ws, self.wire_power(q))
                if self.is_conductor(q) and not above_cond:
                    ws = max(ws, self.wire_power(add(q, U)))
                elif not self.is_conductor(q):
                    ws = max(ws, self.wire_power(add(q, D)))
            target = max(bs, ws - 1)
        if st.p.get("power", 0) != target:
            self.b[p] = st.w(power=target)
            self.L(f"wire {p} power {st.p.get('power', 0)}->{target}")
            # HashSet order in game (locational); fixed order here
            for q in [p] + [add(p, d) for d in VALUES]:
                self.update_neighbors(q)

    def wire_power(self, q):
        s = self.get(q)
        return s.p.get("power", 0) if s.n == "redstone_wire" else 0

    # ---------- repeater ----------
    def repeater_input(self, p, st):
        f = DIRS[st.p["facing"]]
        back = add(p, f)
        i = self.signal(back, f)
        if i >= 15:
            return i
        bs = self.get(back)
        return max(i, bs.p.get("power", 0) if bs.n == "redstone_wire" else 0)

    def repeater_check(self, p, st):
        on = st.p["powered"]
        should = self.repeater_input(p, st) > 0
        if on != should and not self.will_tick_this_tick(p):
            f = DIRS[st.p["facing"]]
            os_ = self.get(add(p, neg(f)))
            if os_.n in ("repeater", "comparator") and DIRS[os_.p["facing"]] != neg(f):
                prio = "EXTREMELY_HIGH"
            elif st.n == "comparator":
                prio = "NORMAL"
            elif on:
                prio = "VERY_HIGH"
            else:
                prio = "HIGH"
            self.schedule(p, st.n, 2 * st.p.get("delay", 1), prio)

    def repeater_tick(self, p):
        st = self.get(p)
        on = st.p["powered"]
        should = self.repeater_input(p, st) > 0
        if st.n == "comparator":
            if on != should:
                self.set(p, st.w(powered=should), 2)
                self.L(f"comparator {p} {'on' if should else 'off'}")
            return
        if on and not should:
            self.set(p, st.w(powered=False), 2)
            self.L(f"repeater {p} off")
        elif not on:
            self.set(p, st.w(powered=True), 2)
            self.L(f"repeater {p} on")
            if not should:
                self.schedule(p, "repeater", 2 * st.p.get("delay", 1), "VERY_HIGH")

    # ---------- scheduled ticks ----------
    def schedule(self, p, name, delay, prio):
        for t in self.sched:
            if t[3] == p and t[4] == name:
                return
        self.sub += 1
        self.sched.append((self.time + delay, PRIO[prio], self.sub, p, name))

    def will_tick_this_tick(self, p):
        return p in getattr(self, "_collected", set())

    # ---------- pistons ----------
    def neighbor_signal(self, p, facing):
        for d in VALUES:
            if d != facing and self.has_signal(add(p, d), d):
                return True
        above = add(p, U)
        for d in VALUES:
            if d != D and self.has_signal(add(above, d), d):
                return True
        return False

    def is_pushable(self, p, st, push_dir, allow_destroy, conn_dir):
        n = st.n
        if n == "air":
            return True
        if n in ("piston", "sticky_piston"):
            return not st.p["extended"]
        if n in PUSH_BLOCK:
            return False
        if n in POPPED:
            return allow_destroy
        return True

    def resolve(self, pp, facing, extending):
        if extending:
            push = facing
            start = add(pp, facing)
        else:
            push = neg(facing)
            start = add(pp, facing, 2)
        to_push, to_destroy = [], []
        st = self.get(start)
        if not self.is_pushable(start, st, push, False, facing):
            if extending and st.n in POPPED:
                return True, [], [start]
            return False, [], []
        if st.n == "air" or start == pp:
            return True, [], []
        to_push.append(start)
        i = 1
        while True:
            q = add(start, push, i)
            qs = self.get(q)
            if qs.n == "air":
                return True, to_push, to_destroy
            if not self.is_pushable(q, qs, push, True, push) or q == pp:
                return False, [], []
            if qs.n in POPPED:
                to_destroy.append(q)
                return True, to_push, to_destroy
            if len(to_push) >= 12:
                return False, [], []
            to_push.append(q)
            i += 1

    def check_extend(self, p):
        st = self.get(p)
        f = DIRS[st.p["facing"]]
        ext = self.neighbor_signal(p, f)
        if ext and not st.p["extended"]:
            ok, _, _ = self.resolve(p, f, True)
            if ok:
                self.block_event(p, st.n, 0, f)
        elif not ext and st.p["extended"]:
            two = add(p, f, 2)
            ts = self.get(two)
            ev = 1
            be = self.be.get(two)
            if ts.n == "moving_piston" and DIRS[ts.p["facing"]] == f and be and be.extending and \
                    (be.progressO < 0.5 or self.time == be.lastTicked or self.handling):
                ev = 2
            self.block_event(p, st.n, ev, f)

    def block_event(self, p, name, b0, f):
        key = (p, name, b0, f)
        if key not in self.events:
            self.events[key] = True
            self.L(f"queue {name}@{p} ev{b0}")

    def add_be(self, be):
        self.be[be.pos] = be
        self.tickers.append(be)

    def remove_be(self, p):
        be = self.be.pop(p, None)
        if be:
            be.removed = True

    def final_tick(self, be):
        if be.progressO < 1.0:
            be.progress = be.progressO = 1.0
            self.remove_be(be.pos)
            if self.get(be.pos).n == "moving_piston":
                ns = AIR if be.source else be.moved
                self.set(be.pos, ns, 3)
                self.neighbor_changed(be.pos)

    def trigger(self, p, st, b0, f):
        ext = self.neighbor_signal(p, f)
        if ext and b0 in (1, 2):
            self.set(p, st.w(extended=True), 2)
            self.L(f"{st.n}@{p} ev{b0} cancelled (powered)")
            return
        if not ext and b0 == 0:
            self.L(f"{st.n}@{p} ev0 dropped (unpowered)")
            return
        sticky = st.n == "sticky_piston"
        if b0 == 0:
            if not self.move_blocks(p, f, True, sticky):
                self.L(f"{st.n}@{p} ev0 resolve failed")
                return
            self.L(f"EXTEND {st.p.get('id', st.n)}@{p} {NAME[f]}")
            self.set(p, st.w(extended=True), 67)
        else:
            arm = add(p, f)
            be = self.be.get(arm)
            if be:
                self.final_tick(be)
            mv = B("moving_piston", facing=NAME[f])
            self.set(p, mv, 276)
            self.add_be(BE(p, st.w(extended=False), f, False, True))
            self.update_neighbors(p)
            what = "retract"
            if sticky:
                two = add(p, f, 2)
                ts = self.get(two)
                be2 = self.be.get(two)
                piece = False
                if ts.n == "moving_piston" and be2 and be2.dir == f and be2.extending:
                    self.final_tick(be2)
                    piece = True
                    what = f"retract+SPIT {two}"
                if not piece:
                    pullable = ts.n != "air" and self.is_pushable(two, ts, neg(f), False, f) and \
                        (ts.n not in POPPED and ts.n not in PUSH_BLOCK)
                    if b0 != 1 or not pullable:
                        self.set(arm, AIR, 3)
                    else:
                        self.move_blocks(p, f, False, True)
                        what = f"retract+PULL {ts.p.get('id', ts.n)}@{two}"
            else:
                self.set(arm, AIR, 3)
            self.L(f"RETRACT {st.p.get('id', st.n)}@{p} ev{b0}: {what}")

    def move_blocks(self, pp, f, extending, sticky):
        arm = add(pp, f)
        if not extending and self.get(arm).n == "piston_head":
            self.set(arm, AIR, 276)
        ok, to_push, to_destroy = self.resolve(pp, f, extending)
        if not ok:
            return False
        push = f if extending else neg(f)
        delete = OrderedDict((q, self.get(q)) for q in to_push)
        states = [self.get(q) for q in to_push]
        for q in reversed(to_destroy):
            self.set(q, AIR, 18)
        for i in range(len(to_push) - 1, -1, -1):
            q = add(to_push[i], push)
            delete.pop(q, None)
            mv = B("moving_piston", facing=NAME[f])
            self.set(q, mv, 324)
            self.add_be(BE(q, states[i], f, extending, False))
        if extending:
            delete.pop(arm, None)
            mv = B("moving_piston", facing=NAME[f])
            self.set(arm, mv, 324)
            head = B("piston_head", facing=NAME[f], sticky=sticky)
            self.add_be(BE(arm, head, f, True, True))
        for q in delete:
            self.set(q, AIR, 82)
        for q in reversed(to_destroy):
            self.update_neighbors(q)
        for q in reversed(to_push):
            self.update_neighbors(q)
        if extending:
            self.update_neighbors(arm)
        return True

    # ---------- tick ----------
    def tick(self):
        self.time += 1
        self.handling = True
        self.phase = "d"
        due = sorted(t for t in self.sched if t[0] <= self.time)
        due.sort(key=lambda t: (t[1], t[2]))
        self.sched = [t for t in self.sched if t[0] > self.time]
        self._collected = {t[3] for t in due}
        for t in due:
            self._collected.discard(t[3])
            if self.get(t[3]).n == t[4] and t[4] in ("repeater", "comparator"):
                self.repeater_tick(t[3])
            elif self.get(t[3]).n == t[4] and t[4] in ("redstone_torch", "redstone_wall_torch"):
                self.torch_tick(t[3])
        self._collected = set()
        self.phase = "g"
        while self.events:
            (p, name, b0, f), _ = self.events.popitem(last=False)
            st = self.get(p)
            if st.n == name:
                self.trigger(p, st, b0, f)
            else:
                self.L(f"event {name}@{p} ev{b0} skipped (now {st.n})")
        self.handling = False
        self.phase = "j"
        for be in list(self.tickers):
            if be.removed:
                continue
            be.lastTicked = self.time
            be.progressO = be.progress
            if be.progressO >= 1.0:
                self.remove_be(be.pos)
                if self.get(be.pos).n == "moving_piston":
                    self.set(be.pos, be.moved, 67)
                    self.neighbor_changed(be.pos)
                    self.L(f"land {be.moved.n}@{be.pos}")
            else:
                be.progress = min(1.0, be.progress + 0.5)
        self.tickers = [t for t in self.tickers if not t.removed]
        self.phase = "-"

    # ---------- harness ----------
    def load(self, blocks):
        for p, st in blocks.items():
            if st.n != "air":
                self.b[p] = st
        for p in sorted(blocks):
            self.update_neighbors(p)

    def cmd_set_silent(self, p, st):
        """setblock ... strict: no neighbour or shape updates, no onPlace side effects."""
        if st.n == "air":
            self.b.pop(p, None)
        else:
            self.b[p] = st

    def cmd_set(self, p, st):
        self.phase = "cmd"
        self.set(p, st, 3)
        self.phase = "-"

    def run(self, n):
        for _ in range(n):
            self.tick()

    def find(self, ident):
        """cell of a tagged block (real, or moving_piston carrying it); returns (pos, 'real'|'moving')."""
        for p, st in self.b.items():
            if st.p.get("id") == ident:
                return p, "real"
        for p, be in self.be.items():
            if be.moved.p.get("id") == ident:
                return p, "moving"
        return None, None


def power_sources(w, p):
    """(kind, cell) pairs powering the piston at p: direct neighbours and QC cells."""
    st = w.get(p)
    f = DIRS[st.p["facing"]]
    out = []
    for d in VALUES:
        if d != f and w.has_signal(add(p, d), d):
            out.append(("direct", add(p, d)))
    above = add(p, U)
    for d in VALUES:
        if d != D and w.has_signal(add(above, d), d):
            out.append(("qc", add(above, d)))
    return out


def piston_report(w, expect):
    """expect: id -> bool (powered). Returns list of mismatch strings."""
    bad = []
    for p, st in sorted(w.b.items()):
        if st.n not in ("piston", "sticky_piston"):
            continue
        ident = st.p.get("id", str(p))
        src = power_sources(w, p)
        want = expect.get(ident)
        got = bool(src)
        if want is None:
            if got:
                bad.append(f"{ident}@{p} unexpected power {src}")
        elif want != got:
            bad.append(f"{ident}@{p} powered={got} want {want} {src}")
    return bad
