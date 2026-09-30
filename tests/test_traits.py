import pytest

from redstone import fileformat
from redstone.build import Build
from redstone.fileformat import Spec
from redstone.library import name_of, paths
from redstone.traits import UNTILED, dimensions, violations


@pytest.mark.parametrize("path", paths(), ids=name_of)
def test_traits_hold(path):
    assert not violations(fileformat.load(path))


def _spec(traits, tests=(), **kw):
    b = Build().place((0, 0, 0), "stone").place((0, 1, 0), "repeater[facing=west]").place((1, 1, 0), "stone")
    return Spec("t", b, traits=traits, tests=list(tests), **kw)


def test_fixture_torch_is_outside_the_design():
    s = _spec(["lightless"])
    s.build.place((3, 1, 0), "redstone_wall_torch[facing=east]").place((3, 0, 0), "stone")
    assert violations(s) and dimensions(s) == (4, 2, 1)
    s.fixtures = {(3, 1, 0), (3, 0, 0)}
    assert violations(s) == [] and dimensions(s) == (2, 2, 1)


def test_reserved_air_counts_in_dimensions():
    s = _spec([], reserved={(0, 3, 2)})
    assert dimensions(s) == (2, 4, 3)


def test_tileable_and_stackable_need_a_tile_test_in_that_direction():
    level = {"name": "tile", "truth_table": "a | o\n0 | 0", "tile": [2, 0, 0]}
    upward = level | {"tile": [0, 3, 0]}
    assert violations(_spec(["stackable"])) == ["claims 'stackable' but no truth-table test has tile: with dy != 0"]
    assert violations(_spec(["stackable"], [level]))
    assert violations(_spec(["stackable", "tileable"], [level, upward])) == []
    assert violations(_spec(["tileable"], [upward]))


def test_untiled_list_only_shrinks():
    specs = {s.name: s for s in map(fileformat.load, paths())}
    stale = [n for n in UNTILED if n not in specs or not {"tileable", "stackable"} & set(specs[n].traits)
             or any("tile" in t for t in specs[n].tests)]
    assert not stale, f"remove from traits.UNTILED: {stale}"
