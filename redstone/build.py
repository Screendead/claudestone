import json
from dataclasses import dataclass, field
from pathlib import Path

Pos = tuple[int, int, int]

DATA_PACK_FORMAT = [121, 0]  # Minecraft 26.3


@dataclass
class Build:
    """A build is a sparse grid of block states, relative to its origin (0, 0, 0)."""

    blocks: dict[Pos, str] = field(default_factory=dict)

    def place(self, pos: Pos, state: str) -> "Build":
        if ":" not in state.split("[")[0]:
            state = "minecraft:" + state
        self.blocks[pos] = state
        return self

    def bounds(self) -> tuple[Pos, Pos]:
        xs, ys, zs = zip(*self.blocks)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def to_commands(self) -> list[str]:
        # Bottom-up so attached blocks (torches, dust, levers) have their support first.
        order = sorted(self.blocks, key=lambda p: (p[1], p[0], p[2]))
        place = [f"setblock ~{x} ~{y} ~{z} {self.blocks[(x, y, z)]}" for x, y, z in order]
        # setblock only updates the placed block's own neighbours at placement time, so a
        # block placed after its power source never notices it. Cloning each block onto
        # itself runs updateNeighborsAt(pos) once the whole build exists, like the final
        # pass of structure-block placement.
        update = [f"clone ~{x} ~{y} ~{z} ~{x} ~{y} ~{z} ~{x} ~{y} ~{z} replace force" for x, y, z in order]
        return place + update

    def to_mcfunction(self) -> str:
        return "\n".join(self.to_commands()) + "\n"


def write_datapack(datapacks_dir: Path, name: str, functions: dict[str, str]) -> Path:
    """Write a data pack whose functions are callable as `/function <name>:<key>`."""
    root = datapacks_dir / name
    fn_dir = root / "data" / name / "function"
    fn_dir.mkdir(parents=True, exist_ok=True)
    meta = {"pack": {"description": name, "min_format": DATA_PACK_FORMAT, "max_format": DATA_PACK_FORMAT}}
    (root / "pack.mcmeta").write_text(json.dumps(meta, indent=2))
    for stale in fn_dir.glob("*.mcfunction"):
        if stale.stem not in functions:
            stale.unlink()
    for key, body in functions.items():
        (fn_dir / f"{key}.mcfunction").write_text(body)
    return root
