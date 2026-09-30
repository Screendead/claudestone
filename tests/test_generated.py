from scripts.generate import LIBRARY, generated

from redstone.fileformat import dump


def test_generated_files_are_current():
    stale = [s.name for s in generated() if (LIBRARY / f"{s.name}.redstone.yaml").read_text() != dump(s)]
    assert not stale, f"run `python -m scripts.generate`: {stale} out of date"
