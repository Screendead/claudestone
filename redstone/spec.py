"""Runs the tests declared in a Spec against a live Rig, optionally recording a trace."""

import json
from pathlib import Path

from .fileformat import Spec, parse_truth_table
from .harness import Rig

# Well under the torch burnout rate of 8 toggles per 60 ticks, even for a torch that
# toggles on every row.
SETTLE = 20
HOLD = 10
TRACE_DIR = Path(__file__).resolve().parent.parent / "traces"


class Recorder:
    def __init__(self, rig: Rig, enabled: bool):
        self.rig, self.enabled, self.frames, self.tick = rig, enabled, [], 0

    def frame(self, event: str = "") -> dict:
        snap = self.rig.snapshot()
        if self.enabled:
            self.frames.append({"tick": self.tick, "event": event,
                                "signals": {",".join(map(str, p)): v for p, v in snap.items() if v}})
        return snap

    def wait(self, n: int) -> dict:
        snap = None
        for _ in range(n) if self.enabled else ():
            self.rig.step(1)
            self.tick += 1
            snap = self.frame()
        if not self.enabled and n:
            self.rig.step(n)
            self.tick += n
        return snap if snap is not None else self.rig.snapshot()


def _on(spec: Spec, snap: dict, name: str) -> bool:
    return snap[spec.named[name]] > 0


def run(rig: Rig, spec: Spec, test: dict, trace: bool = False) -> dict:
    rig.load(spec.build)
    rec = Recorder(rig, trace)
    rec.frame("loaded")
    rec.wait(max(SETTLE, test.get("max_delay", test.get("delay", 0)) + 4))
    result = {}
    try:
        if "truth_table" in test:
            result["delay"] = _truth_table(rig, spec, test, rec)
            if "delay" in test and result["delay"] != test["delay"]:
                raise AssertionError(f"measured delay {result['delay']} ticks, spec says {test['delay']}")
            if "max_delay" in test and result["delay"] > test["max_delay"]:
                raise AssertionError(f"measured delay {result['delay']} ticks exceeds bound {test['max_delay']}")
        for step in test.get("steps", []):
            _step(rig, spec, step, rec)
    finally:
        if trace:
            _write_trace(spec, test, rec)
    return result


def _truth_table(rig, spec, test, rec) -> int:
    _, _, rows = parse_truth_table(test["truth_table"])
    settle = max(SETTLE, test.get("max_delay", test.get("delay", 0)) + 4)
    worst = 0
    for inputs, expected in rows + [rows[0]]:  # end on the first row to check it resets
        for name, on in inputs.items():
            rig.drive(spec.inputs[name], on)
        snap = rec.frame(f"drive {_fmt(inputs)}")
        ticks = 0
        while not all(_on(spec, snap, o) == v for o, v in expected.items()):
            if ticks >= settle:
                raise AssertionError(f"inputs {_fmt(inputs)}: expected {_fmt(expected)}, "
                                     f"got {_fmt({o: _on(spec, snap, o) for o in expected})} after {settle} ticks")
            snap = rec.wait(1)
            ticks += 1
        worst = max(worst, ticks)
        snap = rec.wait(settle - ticks + HOLD)
        got = {o: _on(spec, snap, o) for o in expected}
        if any(got[o] != v for o, v in expected.items()):
            raise AssertionError(f"inputs {_fmt(inputs)}: expected {_fmt(expected)}, got {_fmt(got)} "
                                 f"{settle + HOLD} ticks after the change")
    return worst


def _step(rig, spec, step, rec):
    (kind, arg), = step.items()
    if kind == "drive":
        for name, on in arg.items():
            rig.drive(spec.inputs[name], bool(on))
        rec.frame(f"drive {_fmt(arg)}")
    elif kind == "use":
        rig.use(spec.named[arg])
        rec.frame(f"use {arg}")
    elif kind == "wait":
        rec.wait(arg)
    elif kind == "expect":
        snap = rig.snapshot()
        got = {n: _on(spec, snap, n) for n in arg}
        if any(got[n] != bool(v) for n, v in arg.items()):
            raise AssertionError(f"tick {rec.tick}: expected {_fmt(arg)}, got {_fmt(got)}")
    else:
        raise ValueError(f"unknown step {kind!r}")


def _fmt(d: dict) -> str:
    return " ".join(f"{k}={int(bool(v))}" for k, v in d.items())


def _write_trace(spec, test, rec):
    out = TRACE_DIR / spec.name / f"{test['name']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"spec": str(spec.path) if spec.path else None, "name": spec.name,
                               "test": test["name"], "frames": rec.frames}))
