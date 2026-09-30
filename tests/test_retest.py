"""scripts.retest offline: which cases it picks and how it reports them, with pytest's run
of the library replaced by a fake session, plus a collect-only pass over the real library."""

import io
import json
from contextlib import redirect_stdout

import pytest

from redstone import fileformat, library, showroom, spec as spec_module
from redstone.plots import plot_for
from scripts import retest


class FakeSession:
    def __init__(self, cases, k):
        self.cases, self.k = cases, k
        self.ids = {f"id{i}": c for i, c in enumerate(cases)}
        self.results = {c: (c[1] != "bad", "" if c[1] != "bad" else "expected out=1, got out=0") for c in cases}
        self.measured = {c: {"delay": 2, "delays": {"out": {"rise": 2}}} for c in cases}


@pytest.fixture
def ran(monkeypatch, tmp_path):
    calls = []

    def run_tests(cases, k=None):
        calls.append((cases, k))
        return FakeSession(cases, k)

    monkeypatch.setattr(retest, "run_tests", run_tests)
    monkeypatch.setattr(showroom, "STATE", tmp_path / "showroom")
    monkeypatch.setattr(spec_module, "TRACE_DIR", tmp_path / "traces")
    return calls


def main(*argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = retest.main(list(argv))
    return code, out.getvalue().splitlines()


def not_specs():
    return [fileformat.load(p) for p in library.paths() if plot_for(p) and plot_for(p).name == "not"]


def test_a_plot_runs_every_test_of_its_specs(ran):
    code, lines = main("not")
    want = [(s.name, t["name"]) for s in not_specs() for t in s.tests]
    assert want and sorted(ran[0][0]) == sorted(want)
    assert code == 0 and len(lines) == len(want)
    assert all(line.startswith(f"{s}: PASS {t} (delay 2; out rise 2)") for line, (s, t) in zip(lines, ran[0][0]))


def test_main_means_the_specs_with_no_plot(ran):
    main("main")
    specs = {s for s, _ in ran[0][0]}
    assert specs and all(plot_for(library.path_of(s)) is None for s in specs)


def test_named_specs_and_k_pass_through(ran):
    s = not_specs()[0]
    main("--spec", s.name, "-k", "logic")
    assert ran == [([(s.name, t["name"]) for t in s.tests], "logic")]


def test_failed_keeps_showroom_failures_else_trace_failures(ran, tmp_path):
    s = not_specs()[0]
    other = next(x for x in not_specs() if x.name != s.name)
    tests = [t["name"] for t in s.tests]
    showroom.save_state("not", {"specs": {s.name: {"results": {tests[0]: {"result": "fail"}}},
                                          other.name: {"results": {t["name"]: {"result": "pass"} for t in other.tests}}}})
    main("--spec", s.name, "--spec", other.name, "--failed")
    # Tests of s with no showroom record and no trace count as failed.
    assert ran[0][0] == [(s.name, t) for t in tests]
    for t in tests[1:]:
        trace = tmp_path / "traces" / s.name / f"{t}.json"
        trace.parent.mkdir(parents=True, exist_ok=True)
        trace.write_text(json.dumps({"failures": []}))
    main("--spec", s.name, "--failed")
    assert ran[1][0] == [(s.name, tests[0])]


def test_failures_and_lint_problems_set_the_exit_code(ran, monkeypatch):
    s = not_specs()[0]
    monkeypatch.setattr(retest, "run_tests", lambda cases, k=None: FakeSession([(c[0], "bad") for c in cases], k))
    code, lines = main("--spec", s.name)
    assert code == 1 and lines[0] == f"{s.name}: FAIL {s.tests[0]['name']}: did not run"
    monkeypatch.setattr(retest, "lint", lambda spec: ["cell x is air"])
    assert main("--spec", s.name) == (1, [f"{s.name}: cell x is air", "nothing to run"])


def test_outcome_lines():
    measured = {"throughput": [{"to": "feed", "ticks": 80, "arrived": 10, "per_hour": 9000},
                               {"from": [0, 1, 0], "ticks": 20, "left": 1, "per_hour": 3600}]}
    assert retest.outcome("flow", True, "", measured) == (
        "PASS flow (throughput feed 10 in 80 ticks (9000/h); throughput [0, 1, 0] 1 in 20 ticks (3600/h))")
    assert retest.outcome("flow", False, "boom", measured) == "FAIL flow: boom"


def test_the_session_selects_by_spec_and_test_name_on_the_real_library():
    s = not_specs()[0]
    t = s.tests[-1]["name"]
    session = retest.Session({(s.name, t)})
    with redirect_stdout(io.StringIO()):
        pytest.main(["-p", "no:terminal", "-p", "no:cacheprovider", "--collect-only", str(retest.LIBRARY_TESTS)],
                    plugins=[session])
    assert list(session.ids.values()) == [(s.name, t)]
    for k, kept in ((t.split()[0], True), ("zzzz", False)):
        session = retest.Session({(s.name, x["name"]) for x in s.tests})
        with redirect_stdout(io.StringIO()):
            pytest.main(["-p", "no:terminal", "-p", "no:cacheprovider", "--collect-only", "-k", k,
                         str(retest.LIBRARY_TESTS)], plugins=[session])
        assert ((s.name, t) in session.ids.values()) == kept
        assert all(k in x for _, x in session.ids.values())
