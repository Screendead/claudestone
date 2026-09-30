"""Lint a spec, run its tests on the server, and print one line per result.

    python -m scripts.try <spec>... [--test NAME]... [--trace]

Runs in the plot of the spec's folder (redstone.plots.plot_for) if there is one, else in
$REDSTONE_PLOT, else in main. --test runs only the named tests. Every run writes a trace
for scripts.look: sparse (the named cells, at the ticks the test reads them) unless
--trace asks for every cell on every tick. The reply of each `log` step is printed under
its test's result line.
"""

import argparse
import io
import json
import os
import sys
import time
from contextlib import redirect_stdout

import pytest

from redstone import fileformat, library, spec as spec_module
from redstone.plots import plot_for
from redstone.traits import design_blocks, dimensions, violations
from scripts import look
from scripts.lint import lint


class Collect:
    def __init__(self):
        self.results = {}  # test name -> (ok, message)
        self.delays = {}

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or (report.when == "setup" and report.failed):
            name = report.nodeid.split("::", 2)[-1].removeprefix("test_spec[").removesuffix("]").split("::", 1)[-1]
            msg = ""
            if report.failed:
                crash = report.longrepr.reprcrash
                msg = " ".join(crash.message.removeprefix("AssertionError: ").split()) if crash else str(report.longrepr)
            self.results[name] = (report.passed, msg)


def run_tests(s, tests) -> tuple[Collect, bool]:
    c = Collect()
    real = spec_module.run

    def run(rig, sp, test, trace=False):
        result = real(rig, sp, test, trace)
        c.delays[(sp.name, test["name"])] = result.get("delay"), result.get("delays")
        return result

    spec_module.run = run
    ids = [f"tests/test_library.py::test_spec[{s.name}::{t['name']}]" for t in tests]
    try:
        with redirect_stdout(io.StringIO()):
            pytest.main(["-p", "no:terminal", "-p", "no:cacheprovider", "-W", "ignore", *ids], plugins=[c])
    finally:
        spec_module.run = real
    return c, all(c.results.get(t["name"], (False,))[0] for t in tests)


def _fmt_delays(delay: int, delays: dict) -> str:
    """`delay 4; sum rise 4 fall 2, cout rise 2`: the worst case per output and edge."""
    per = ", ".join(f"{o} " + " ".join(f"{e} {w}" for e, w in sorted(edges.items(), key=lambda e: e[0] != "rise"))
                    for o, edges in (delays or {}).items())
    return f"delay {delay}" + (f"; {per}" if per else "")


def logged(spec: str, test: str, since: float) -> list[str]:
    """The `log` steps of this run's trace, with the server's replies."""
    path = spec_module.TRACE_DIR / spec / f"{test}.json"
    if not path.exists() or path.stat().st_mtime < since:
        return []
    return [f"  tick {f['tick']}: {f['event']}\n    {f['reply']}" for f in json.loads(path.read_text())["frames"]
            if "reply" in f]


def main(argv) -> int:
    ap = argparse.ArgumentParser(prog="try")
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--test", action="append", default=[], help="run only this test (repeatable)")
    ap.add_argument("--trace", action="store_true")
    a = ap.parse_args(argv)
    bad, default_plot = False, os.environ.get("REDSTONE_PLOT", "main")
    for name in a.specs:
        s = fileformat.load(library.path_of(name))
        tests = [t for t in s.tests if not a.test or t["name"] in a.test]
        unknown = [n for n in a.test if n not in {t["name"] for t in s.tests}]
        if unknown:
            print(f"{name}: no test {', '.join(map(repr, unknown))}; its tests are: "
                  + ", ".join(repr(t["name"]) for t in s.tests))
            return 2
        errors = lint(s)
        for e in errors:
            print(f"{name}: {e}")
        if errors:
            bad = True
            continue
        plot = plot_for(s.path)
        os.environ["REDSTONE_PLOT"] = plot.name if plot else default_plot
        print(f"plot: {os.environ['REDSTONE_PLOT']}")
        if a.trace:
            os.environ["REDSTONE_TRACE"] = "1"
        started = time.time()
        c, ok = run_tests(s, tests)
        bad |= not ok
        for t in tests:
            passed, msg = c.results.get(t["name"], (False, "did not run"))
            delay, delays = c.delays.get((s.name, t["name"]), (None, None))
            print(f"PASS {t['name']}" + (f" ({_fmt_delays(delay, delays)})" if delay is not None else "") if passed
                  else f"FAIL {t['name']}: {msg}")
            for line in logged(s.name, t["name"], started):
                print(line)
            if not passed and a.trace:
                print(look.trace_table(s.name, t["name"]))
        v = violations(s)
        print("; ".join(v) if v else "traits ok")
        w, h, d = dimensions(s)
        print(f"size {w}x{h}x{d}, volume {w * h * d}, blocks {len(design_blocks(s))}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
