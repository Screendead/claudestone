"""Run a plot's specs, or named specs, through pytest, each test in its spec's plot, and print
one line per result.

    python -m scripts.retest <plot>... [--spec NAME]... [--failed] [-k EXPR] [--trace]

A plot's specs are those plot_for puts there; `main` means the specs with no plot (mechanics,
builds, input). --failed keeps only the tests whose last result was a failure: the plot's
showroom record where there is one, else the test's trace (a test with neither is kept).
-k filters further, as pytest's -k does. Tests are chosen by spec and test name, not by
pytest id, so names with spaces or brackets need no quoting. Specs that fail lint are
reported and skipped. $REDSTONE_PLOT, if set, still decides where every test builds.
"""

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from redstone import door, fileformat, library, showroom, spec as spec_module
from redstone.library import name_of
from redstone.plots import MAIN, PLOTS, plot_for
from scripts.lint import lint

LIBRARY_TESTS = Path(__file__).resolve().parent.parent / "tests" / "test_library.py"


class Session:
    """A pytest plugin that keeps only the chosen (spec, test) cases of tests/test_library.py
    and collects their outcomes and measurements."""

    def __init__(self, wanted: set[tuple[str, str]]):
        self.wanted = wanted
        self.ids: dict[str, tuple[str, str]] = {}
        self.results: dict[tuple[str, str], tuple[bool, str]] = {}
        self.measured: dict[tuple[str, str], dict] = {}

    @pytest.hookimpl(trylast=True)  # after -k, so `ids` holds only what will run
    def pytest_collection_modifyitems(self, config, items):
        keep, drop = [], []
        for item in items:
            params = getattr(getattr(item, "callspec", None), "params", {})
            key = (name_of(params["path"]), params.get("name")) if "path" in params else None
            if key in self.wanted:
                self.ids[item.nodeid] = key
                keep.append(item)
            else:
                drop.append(item)
        if drop:
            config.hook.pytest_deselected(items=drop)
        items[:] = keep

    def pytest_runtest_logreport(self, report):
        key = self.ids.get(report.nodeid)
        if key and (report.when == "call" or (report.when == "setup" and report.failed)):
            msg = ""
            if report.failed:
                crash = report.longrepr.reprcrash
                msg = " ".join(crash.message.removeprefix("AssertionError: ").split()) if crash else str(report.longrepr)
            self.results[key] = (report.passed, msg)


def run_tests(cases: list[tuple[str, str]], k: str | None = None) -> Session:
    """Run (spec name, test name) cases of the library in one pytest session."""
    session = Session(set(cases))
    real = spec_module.run

    def run(rig, sp, test, trace=False):
        result = real(rig, sp, test, trace)
        session.measured[(sp.name, test["name"])] = result
        return result

    spec_module.run = run
    args = ["-p", "no:terminal", "-p", "no:cacheprovider", "-W", "ignore", str(LIBRARY_TESTS)]
    try:
        with redirect_stdout(io.StringIO()):
            pytest.main(args + (["-k", k] if k else []), plugins=[session])
    finally:
        spec_module.run = real
    return session


def fmt_delays(delay: int, delays: dict) -> str:
    """`delay 4; sum rise 4 fall 2, cout rise 2`: the worst case per output and edge."""
    per = ", ".join(f"{o} " + " ".join(f"{e} {w}" for e, w in sorted(edges.items(), key=lambda e: e[0] != "rise"))
                    for o, edges in (delays or {}).items())
    return f"delay {delay}" + (f"; {per}" if per else "")


def fmt_throughput(measured: list[dict]) -> str:
    """`throughput feed 10 in 80 ticks (9000/h)`, one entry per throughput step."""
    return "; ".join(f"throughput {m.get('to', m.get('from'))} {m.get('arrived', m.get('left'))} in {m['ticks']} ticks "
                     f"({m['per_hour']}/h)" for m in measured)


def outcome(test: str, passed: bool, msg: str, result: dict | None) -> str:
    result = result or {}
    notes = ([fmt_delays(result["delay"], result.get("delays"))] if result.get("delay") is not None else []) + (
        [fmt_throughput(result["throughput"])] if result.get("throughput") else []) + (
        [door.summary(result["door"])] if result.get("door") else [])
    return f"PASS {test}" + (f" ({'; '.join(notes)})" if notes else "") if passed else f"FAIL {test}: {msg}"


def last_failed(spec, test: str) -> bool:
    """Whether the test's last recorded run failed; True when nothing records one."""
    plot = plot_for(spec.path) if spec.path else None
    if plot is not None:
        entry = showroom.load_state(plot.name)["specs"].get(spec.name, {})
        if test in entry.get("results", {}):
            return entry["results"][test]["result"] == "fail"
    trace = spec_module.TRACE_DIR / spec.name / f"{test}.json"
    try:
        return bool(json.loads(trace.read_text())["failures"])
    except (OSError, ValueError, KeyError):
        return True


def specs_of(plot: str) -> list:
    out = []
    for path in library.paths():
        home = plot_for(path)
        if (home.name if home else MAIN.name) == plot:
            out.append(fileformat.load(path))
    return out


def main(argv) -> int:
    ap = argparse.ArgumentParser(prog="retest")
    ap.add_argument("plots", nargs="*", help="run every spec whose plot this is (main: specs with no plot)")
    ap.add_argument("--spec", action="append", default=[], help="run this spec (repeatable)")
    ap.add_argument("--failed", action="store_true", help="only tests whose last result was a failure")
    ap.add_argument("-k", help="pytest -k expression over the chosen tests' ids")
    ap.add_argument("--trace", action="store_true", help="record every cell on every tick")
    a = ap.parse_args(argv)
    if not a.plots and not a.spec:
        ap.error("name a plot or --spec")
    unknown = [p for p in a.plots if p not in PLOTS]
    if unknown:
        ap.error(f"no plot {', '.join(unknown)}; plots are {', '.join(PLOTS)}")
    specs = {s.name: s for p in a.plots for s in specs_of(p)}
    for name in a.spec:
        s = fileformat.load(library.path_of(name))
        specs[s.name] = s
    bad = False
    cases = []
    for s in specs.values():
        errors = lint(s)
        for e in errors:
            print(f"{s.name}: {e}")
        bad |= bool(errors)
        if not errors:
            cases += [(s.name, t["name"]) for t in s.tests if not a.failed or last_failed(s, t["name"])]
    if not cases:
        print("nothing to run")
        return 1 if bad else 0
    if a.trace:
        os.environ["REDSTONE_TRACE"] = "1"
    session = run_tests(cases, a.k)
    for spec, test in cases:
        if a.k and (spec, test) not in session.ids.values():
            continue
        passed, msg = session.results.get((spec, test), (False, "did not run"))
        bad |= not passed
        print(f"{spec}: " + outcome(test, passed, msg, session.measured.get((spec, test))))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
