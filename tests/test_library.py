"""Runs every test declared in library/*.redstone.yaml. Set REDSTONE_TRACE=1 to record
per-tick traces into traces/ for the viewer."""

import os
from pathlib import Path

import pytest

from redstone import fileformat, spec

LIBRARY = Path(__file__).resolve().parent.parent / "library"
CASES = [(path, test["name"]) for path in sorted(LIBRARY.glob("*.redstone.yaml"))
         for test in fileformat.load(path).tests]


@pytest.mark.parametrize("path,name", CASES, ids=[f"{p.name.removesuffix('.redstone.yaml')}::{n}" for p, n in CASES])
def test_spec(rig, path, name):
    s = fileformat.load(path)
    test = next(t for t in s.tests if t["name"] == name)
    spec.run(rig, s, test, trace=bool(os.environ.get("REDSTONE_TRACE")))
