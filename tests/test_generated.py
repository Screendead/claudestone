import yaml
from scripts.generate import destination, generated

from redstone.fileformat import dump, load
from redstone.library import name_of, paths


def test_generated_files_are_current():
    stale = [s.name for s in generated() if destination(s.name).read_text() != dump(s)]
    assert not stale, f"run `python -m scripts.generate`: {stale} out of date"


def test_names_are_unique():
    names = [name_of(p) for p in paths()]
    assert len(names) == len(set(names)), sorted(n for n in names if names.count(n) > 1)


SHAPES = """name: t
palette:
  .: air
  '=': stone
  s: {input: s}
  F: {block: redstone_torch, fixture: true}
  r: {name: reader, block: 'comparator[facing=west]', fixture: true}
  _: {reserve: true}
  o: {output: out, block: redstone_wire}
layers:
  0: |
    s=o=_Fr=s
"""


def test_multi_cell_input_fixture_and_reserve_round_trip(tmp_path):
    f = tmp_path / "t.redstone.yaml"
    f.write_text(SHAPES)
    s = load(f)
    assert s.inputs == {"s": (0, 0, 0)} and s.input_cells("s") == [(0, 0, 0), (8, 0, 0)]
    assert s.fixtures == {(5, 0, 0), (6, 0, 0)} and s.named["reader"] == (6, 0, 0)
    assert s.reserved == {(4, 0, 0)} and (4, 0, 0) not in s.build.blocks
    f.write_text(dump(s))
    again = load(f)
    assert (again.inputs, again.extra_inputs, again.fixtures, again.reserved, again.named, again.build.blocks) == (
        s.inputs, s.extra_inputs, s.fixtures, s.reserved, s.named, s.build.blocks)
    assert dump(again) == dump(s)
    assert [k for k, v in yaml.safe_load(dump(s))["palette"].items() if v == {"input": "s"}] == ["s"]
