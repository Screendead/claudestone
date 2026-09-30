"""Runs the tests declared in a Spec against a live Rig, optionally recording a trace."""

import dataclasses
import json
from pathlib import Path

from . import watch
from .build import Build, Pos
from .fileformat import Spec, parse_truth_table
from .harness import Rig, checked
from .plots import MAIN

# Well under the torch burnout rate of 8 toggles per 60 ticks, even for a torch that
# toggles on every row.
SETTLE = 20
HOLD = 10
TRACE_DIR = Path(__file__).resolve().parent.parent / "traces"
# Cell names of the second copy in a tile test.
TILE_PREFIX = "B."


class Recorder:
    """Keeps every snapshot a test takes. Dense: every signal cell, every tick, with each
    comparator's output strength under `levels`. Otherwise only the named cells, and only
    when a test step reads them."""

    def __init__(self, rig: Rig, dense: bool):
        self.rig, self.dense, self.frames, self.tick = rig, dense, [], 0
        self.failures: list[str] = []
        self.loops: list[str] = []  # "i/n" of each enclosing repeat

    def frame(self, event: str = "") -> dict:
        snap = self.rig.snapshot()
        frame = {"tick": self.tick, "event": event, "signals": _keyed(snap)}
        if self.dense:
            frame["levels"] = _keyed(self.rig.levels)
        self.frames.append(frame)
        return snap

    def wait(self, n: int) -> dict:
        if not self.dense:
            if n:
                self.rig.step(n)
                self.tick += n
            return self.frame()
        snap = None
        for _ in range(n):
            self.rig.step(1)
            self.tick += 1
            snap = self.frame()
        return snap if snap is not None else self.frame()

    def advance(self, n: int) -> None:
        """Step n ticks; a sparse trace records nothing for them."""
        if self.dense:
            if n:
                self.wait(n)
        elif n:
            self.rig.step(n)
            self.tick += n

    def fail(self, message: str) -> None:
        where = f"tick {self.tick}" + (f" (repeat {' '.join(self.loops)})" if self.loops else "")
        self.failures.append(f"{where}: {message}")


def _keyed(values: dict) -> dict:
    return {",".join(map(str, p)): v for p, v in values.items() if v}


def _on(spec: Spec, snap: dict, name: str) -> bool:
    return snap[spec.named[name]] > 0


def _announce(rig: Rig, title: str, subtitle: str) -> None:
    if rig.plot != MAIN.name:
        rig.heading = [{"text": title + "\n", "color": "red", "bold": True},
                       {"text": subtitle + "\n", "color": "#DDDDDD"}]
        return _sign(rig, "")
    status(rig, subtitle)


def status(rig: Rig, text: str) -> None:
    """Progress of a test. In the main plot the watch director shows it (redstone.watch)."""
    if rig.plot != MAIN.name:
        return _sign(rig, text)
    if _watched(rig):
        watch.set_status(rig.plot, text)


def _watched(rig) -> bool:
    """A rig on a server (not the offline fake) reports to the watch director."""
    return getattr(rig, "server", None) is not None


def _sign(rig: Rig, text: str) -> None:
    """Several plots test in turn, so each shows its progress on its own status sign
    (drawn by scripts.plots) instead of on everyone's screen."""
    body = rig.heading + [{"text": text, "color": "yellow"}]
    checked(rig.display, f"data merge entity @e[type=text_display,tag=plot_status,tag={rig.plot},limit=1] "
                         f"{{text:{json.dumps({'text': '', 'extra': body})}}}")


def run(rig: Rig, spec: Spec, test: dict, trace: bool = False) -> dict:
    if _watched(rig):
        watch.autostart()
    _announce(rig, spec.name, test["name"])
    try:
        # A Docker satellite's rig (redstone.remote) runs _run in the container.
        result = rig.run_spec(spec, test, trace) if hasattr(rig, "run_spec") else _run(rig, spec, test, trace)
    except BaseException:
        _event(rig, "result", spec, test, passed=False)
        _idle(rig, spec, test, passed=False)
        raise
    _event(rig, "result", spec, test, passed=True, delay=result.get("delay"))
    _idle(rig, spec, test, passed=True)
    return result


def _idle(rig: Rig, spec: Spec, test: dict, passed: bool) -> None:
    """A plot's status sign keeps only the last result once its test ends."""
    if rig.plot == MAIN.name:
        return
    body = [{"text": "idle\n", "color": "#DDDDDD"},
            {"text": f"last: {spec.name}\n{test['name']} ", "color": "#BBBBBB"},
            {"text": "pass" if passed else "fail", "color": "green" if passed else "red"}]
    try:
        checked(rig.display, f"data merge entity @e[type=text_display,tag=plot_status,tag={rig.plot},limit=1] "
                             f"{{text:{json.dumps({'text': '', 'extra': body})}}}")
    except Exception:
        pass  # a sign must not turn a finished test's result into an error


def _event(rig, kind: str, spec: Spec, test: dict, **fields) -> None:
    if not _watched(rig):
        return
    box = None
    try:
        box = watch.world_box(rig.origin, rig.loaded) if rig.loaded.blocks else None
    except Exception:
        pass
    watch.emit(kind, plot=rig.plot, server=rig.server.name, spec=spec.name, test=test["name"], box=box, **fields)


def _run(rig: Rig, spec: Spec, test: dict, trace: bool) -> dict:
    if "tile" in test:
        spec = tiled(spec, tuple(test["tile"]))
    build, drivers = spec.build, set()
    if test.get("initial"):
        build = Build(dict(spec.build.blocks), list(spec.build.entities))
        drivers = {p for n, on in test["initial"].items() if on for p in _cells(spec, n, "tile" in test)}
        for p in drivers:
            build.place(p, "redstone_block")
    rig.load(build, probe=None if trace else set(spec.named.values()), drivers=drivers)
    _event(rig, "test", spec, test)
    rec = Recorder(rig, trace)
    rec.frame("loaded")
    snap = rec.wait(test.get("settle", _settle(test)))
    result = {}
    try:
        if "truth_table" in test:
            result["delay"], result["delays"] = _truth_table(rig, spec, test, rec, snap)
            _check_delays(test, result["delay"], result["delays"])
        for step in test.get("steps", []):
            _step(rig, spec, step, rec)
    finally:
        _cleanup(rig, test, rec)
        _write_trace(spec, test, rec)
    if rec.failures:
        more = len(rec.failures) - 1
        raise AssertionError(rec.failures[0] + (f" (and {more} more)" if more else ""))
    return result


def tiled(spec: Spec, offset: Pos) -> Spec:
    """The spec and a second copy of it at `offset`, whose cells are named with
    TILE_PREFIX. Raises if the copies place different blocks in one cell."""
    def moved(ps):
        return [tuple(a + b for a, b in zip(p, offset)) for p in ps]

    b = TILE_PREFIX
    return dataclasses.replace(
        spec, build=Build().merge(spec.build).merge(spec.build, offset),
        inputs=spec.inputs | {b + n: moved([p])[0] for n, p in spec.inputs.items()},
        extra_inputs=spec.extra_inputs | {b + n: moved(spec.input_cells(n)) for n in spec.extra_inputs},
        outputs=spec.outputs | {b + n: moved([p])[0] for n, p in spec.outputs.items()},
        named=spec.named | {b + n: moved([p])[0] for n, p in spec.named.items()},
        fixtures=spec.fixtures | set(moved(spec.fixtures)), reserved=spec.reserved | set(moved(spec.reserved)))


def _cells(spec: Spec, name: str, tile: bool) -> list[Pos]:
    """An input's cells, in both copies of a tile test."""
    return spec.input_cells(name) + (spec.input_cells(TILE_PREFIX + name) if tile else [])


def _settle(test: dict) -> int:
    per_output = [w for d in (test.get("delays", {}), test.get("max_delays", {})) for v in d.values()
                  for w in (v.values() if isinstance(v, dict) else [v])]
    return max(SETTLE, max([test.get("max_delay", 0), test.get("delay", 0), *per_output]) + 4)


def _check_delays(test: dict, delay: int, delays: dict) -> None:
    if "delay" in test and delay != test["delay"]:
        raise AssertionError(f"measured delay {delay} ticks, spec says {test['delay']}")
    if "max_delay" in test and delay > test["max_delay"]:
        raise AssertionError(f"measured delay {delay} ticks exceeds bound {test['max_delay']}")
    for key, exact in (("delays", True), ("max_delays", False)):
        for out, want in test.get(key, {}).items():
            seen = delays.get(out, {})
            for edge, w in (want.items() if isinstance(want, dict) else [(None, want)]):
                what = out if edge is None else f"{out} {edge}"
                if not seen or edge is not None and edge not in seen:
                    raise AssertionError(f"{key} {what}: the table never makes {out} {edge or 'change'}")
                got = max(seen.values()) if edge is None else seen[edge]
                if exact and got != w:
                    raise AssertionError(f"measured {what} delay {got} ticks, spec says {w}")
                if not exact and got > w:
                    raise AssertionError(f"measured {what} delay {got} ticks exceeds bound {w}")


def _cleanup(rig, test, rec):
    """The test's `finally` commands. Never raises, so a failure already in flight stays the
    one reported."""
    for command in test.get("finally", []):
        try:
            ok, reply = rig.command(command)
        except Exception as e:
            rec.fail(f"finally {command}: {e}")
            continue
        if _failed(ok, reply):
            rec.fail(f"finally {command}: {reply}")


def _truth_table(rig, spec, test, rec, snap) -> tuple[int, dict]:
    """Returns the worst all-outputs-match tick over the rows, and per output the worst
    first-match tick of each edge (`rise`/`fall` from the value the previous row ended on)."""
    _, _, rows = parse_truth_table(test["truth_table"])
    if "tile" in test:
        b, n = TILE_PREFIX, len(rows)
        rows = [(ins | {b + k: v for k, v in rows[(i + 1) % n][0].items()},
                 outs | {b + k: v for k, v in rows[(i + 1) % n][1].items()}) for i, (ins, outs) in enumerate(rows)]
    if test.get("reset", True):
        rows = rows + [rows[0]]  # end on the first row to check it resets
    settle = _settle(test)
    glitch_free = test.get("glitch_free", False)
    worst, delays = 0, {}
    for i, (inputs, expected) in enumerate(rows, 1):
        status(rig, f"{spec.name}: row {i}/{len(rows)}  {_fmt(inputs)}")
        before = {o: _on(spec, snap, o) for o in expected}
        want = {o: v for o, v in expected.items() if v is not None}
        for name, on in inputs.items():
            for pos in spec.input_cells(name):
                rig.drive(pos, on)
        snap = rec.frame(f"drive {_fmt(inputs)}")
        first, ticks = {}, 0
        while True:
            _glitches(spec, snap, want, before, first, ticks, inputs, glitch_free)
            if all(_on(spec, snap, o) == v for o, v in want.items()):
                break
            if ticks >= settle:
                raise AssertionError(f"inputs {_fmt(inputs)}: expected {_fmt(want)}, "
                                     f"got {_fmt({o: _on(spec, snap, o) for o in want})} after {settle} ticks")
            snap = rec.wait(1)
            ticks += 1
        worst = max(worst, ticks)
        for o, v in want.items():
            if before[o] != v:
                edge = delays.setdefault(o, {})
                edge["rise" if v else "fall"] = max(edge.get("rise" if v else "fall", 0), first[o])
        if glitch_free:
            for _ in range(settle - ticks + HOLD):
                snap = rec.wait(1)
                ticks += 1
                _glitches(spec, snap, want, before, first, ticks, inputs, True)
        else:
            snap = rec.wait(settle - ticks + HOLD)
        got = {o: _on(spec, snap, o) for o in want}
        if any(got[o] != v for o, v in want.items()):
            raise AssertionError(f"inputs {_fmt(inputs)}: expected {_fmt(want)}, got {_fmt(got)} "
                                 f"{settle + HOLD} ticks after the change")
    for o in [o for o in delays if o.startswith(TILE_PREFIX)]:
        edges = delays.setdefault(o.removeprefix(TILE_PREFIX), {})
        for e, w in delays.pop(o).items():
            edges[e] = max(edges.get(e, 0), w)
    return worst, delays


def _glitches(spec, snap, want, before, first, ticks, inputs, glitch_free):
    """Notes each output's first match; with glitch_free, fails an output that leaves its
    expected value after matching, or that should not change and does."""
    for o, v in want.items():
        now = _on(spec, snap, o)
        if now == v:
            first.setdefault(o, ticks)
        elif glitch_free and (o in first or before[o] == v):
            raise AssertionError(f"inputs {_fmt(inputs)}: {o} glitched to {int(now)} at tick {ticks} "
                                 f"after the change (expected {int(v)})")


# Replies of a command that did nothing but is not an error: a conditional chain whose
# condition failed, a selector that matched nothing, or a state that was already what the
# command asked for (a merge, a setblock, an objective, a time marker, a gamerule).
BENIGN = ("Test failed", "No entity was found", "Nothing changed", "Could not set the block",
          "An objective already exists by that name")
BENIGN_INSIDE = ("is already at time marker", "is already set to")


def _failed(ok: bool, reply: str) -> bool:
    return not ok and bool(reply) and not reply.startswith(BENIGN) and not any(b in reply for b in BENIGN_INSIDE)


def _step(rig, spec, step, rec):
    (kind, arg), = step.items()
    if kind not in ("wait", "repeat"):
        status(rig, f"{spec.name}: {kind} {_show(kind, arg)}")
    if kind == "drive":
        for name, on in arg.items():
            for pos in spec.input_cells(name):
                rig.drive(pos, bool(on))
        rec.frame(f"drive {_fmt(arg)}")
    elif kind == "use":
        rig.use(spec.named[arg])
        rec.frame(f"use {arg}")
    elif kind == "wait":
        rec.wait(arg)
    elif kind == "expect":
        snap = rec.frame(f"expect {_fmt(arg)}")
        got = {n: _on(spec, snap, n) for n in arg}
        if any(got[n] != bool(v) for n, v in arg.items()):
            rec.fail(f"expected {_fmt(arg)}, got {_fmt(got)}")
    elif kind == "level":
        rec.frame(f"level {_fmt_levels(arg)}")
        got = {n: rig.level(spec.named[n]) for n in arg}
        if got != {n: int(v) for n, v in arg.items()}:
            rec.fail(f"expected level {_fmt_levels(arg)}, got {_fmt_levels(got)}")
    elif kind == "wave":
        _wave(spec, arg, rec)
    elif kind in ("run", "log"):
        ok, reply = rig.command(arg)
        rec.frame(f"{kind} {arg}")
        if kind == "log":
            rec.frames[-1]["reply"] = reply
        if _failed(ok, reply):
            rec.fail(f"{kind} {arg}: {reply}")
    elif kind == "check":
        if not rig.run(f"execute positioned {rig.abs((0, 0, 0))} {arg}").startswith("Test passed"):
            rec.fail(f"check failed: {arg}")
    elif kind == "repeat":
        times = arg["times"]
        for i in range(times):
            rec.loops.append(f"{i + 1}/{times}")
            rec.frame(f"repeat {i + 1}/{times}")
            try:
                for inner in arg["steps"]:
                    _step(rig, spec, inner, rec)
            finally:
                rec.loops.pop()
    else:
        raise ValueError(f"unknown step {kind!r}")


def _wave(spec, arg, rec):
    """Checks character i of each cell's string at i ticks after the step starts, and leaves
    the clock max(len) ticks later, whether or not a character mismatched."""
    n = max(map(len, arg.values()))
    snap = rec.frame(f"wave {_fmt_levels(arg)}")
    for i in range(n):
        if i:
            snap = rec.wait(1)
        for cell, wave in arg.items():
            if i < len(wave) and wave[i] != "x" and _on(spec, snap, cell) != (wave[i] == "1"):
                rec.fail(f"wave {cell}: expected {wave[i]}, got {int(_on(spec, snap, cell))} "
                         f"at character {i + 1} of {wave}")
                rec.advance(n - i)
                return
    rec.advance(1)


def _show(kind, arg) -> str:
    if isinstance(arg, str):
        return arg
    return _fmt_levels(arg) if kind in ("level", "wave") else _fmt(arg)


def _fmt(d: dict) -> str:
    return " ".join(f"{k}={int(bool(v))}" for k, v in d.items())


def _fmt_levels(d: dict) -> str:
    return " ".join(f"{k}={v}" for k, v in d.items())


def _write_trace(spec, test, rec):
    out = TRACE_DIR / spec.name / f"{test['name']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"spec": str(spec.path) if spec.path else None, "name": spec.name,
                               "test": test["name"], "sparse": not rec.dense, "failures": rec.failures,
                               "frames": rec.frames}))
