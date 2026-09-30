"""library/<building block>/<variant>.redstone.yaml. Spec names are unique across folders,
because test ids, traces and packaged data packs are keyed by name alone."""

from pathlib import Path

LIBRARY = Path(__file__).resolve().parent.parent / "library"
SUFFIX = ".redstone.yaml"


def paths() -> list[Path]:
    return sorted(LIBRARY.rglob("*" + SUFFIX))


def name_of(path: Path) -> str:
    return path.name.removesuffix(SUFFIX)


def path_of(name: str) -> Path:
    found = [p for p in paths() if name_of(p) == name]
    if len(found) != 1:
        raise LookupError(f"{name}: {len(found)} library files have this name")
    return found[0]
