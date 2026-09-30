"""Runs every test declared in library/**/*.redstone.yaml, writing a trace of each into
traces/ for the viewer. Set REDSTONE_TRACE=1 to make the traces per-tick with every cell, and
REDSTONE_PLOT=<plot> to build in that plot of the world (redstone/plots.py) instead of the
main area."""

import os

import pytest

from redstone import fileformat, spec
from redstone.library import name_of, paths


def _cases():
    # Other people may be writing library files while this collects; a file that doesn't
    # load fails test_loads instead of stopping collection.
    for path in paths():
        try:
            tests = fileformat.load(path).tests
        except Exception:
            continue
        yield from ((path, t["name"]) for t in tests)


CASES = list(_cases())


@pytest.mark.parametrize("path", paths(), ids=name_of)
def test_loads(path):
    fileformat.load(path)


@pytest.mark.parametrize("path,name", CASES, ids=[f"{name_of(p)}::{n}" for p, n in CASES])
def test_spec(rig, path, name):
    s = fileformat.load(path)
    test = next(t for t in s.tests if t["name"] == name)
    # conftest's teardown shows the tested build in the plot's showroom with this outcome.
    rig.tested = {"spec": s, "test": name, "delay": None}
    result = spec.run(rig, s, test, trace=bool(os.environ.get("REDSTONE_TRACE")))
    rig.tested["delay"] = result.get("delay")
