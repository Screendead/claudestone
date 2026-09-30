"""Lint a spec, run its tests on the server, and print one line per result.

    python -m scripts.try <spec>... [--test NAME]... [--trace]

Runs in the plot of the spec's folder (redstone.plots.plot_for) if there is one, else in
$REDSTONE_PLOT, else in main. --test runs only the named tests. Every run writes a trace
for scripts.look: sparse (the named cells, at the ticks the test reads them) unless
--trace asks for every cell on every tick. The reply of each `log` step is printed under
its test's result line.
"""

import argparse
import json
import os
import sys
import time

from redstone import fileformat, library, spec as spec_module
from redstone.plots import plot_for
from redstone.traits import design_blocks, dimensions, violations
from scripts import look
from scripts.lint import lint
from scripts.retest import outcome, run_tests


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
        session = run_tests([(s.name, t["name"]) for t in tests])
        for t in tests:
            passed, msg = session.results.get((s.name, t["name"]), (False, "did not run"))
            bad |= not passed
            print(outcome(t["name"], passed, msg, session.measured.get((s.name, t["name"]))))
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
