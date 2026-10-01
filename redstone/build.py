import json
import re
from dataclasses import dataclass, field
from pathlib import Path

Pos = tuple[int, int, int]

DATA_PACK_FORMAT = [121, 0]  # Minecraft 26.3


@dataclass
class Build:
    """A build is a sparse grid of block states, relative to its origin (0, 0, 0)."""

    blocks: dict[Pos, str] = field(default_factory=dict)
    # Summoned after the blocks exist: (x, y, z) as block-relative floats, entity id, SNBT.
    entities: list[tuple[tuple[float, float, float], str, str]] = field(default_factory=list)

    def place(self, pos: Pos, state: str) -> "Build":
        self.blocks[pos] = namespaced(state)
        return self

    def summon(self, pos: tuple[float, float, float], entity: str, nbt: str = "") -> "Build":
        self.entities.append((pos, namespaced(entity), nbt))
        return self

    def merge(self, other: "Build", offset: Pos = (0, 0, 0)) -> "Build":
        for pos, state in other.shifted(offset).blocks.items():
            if pos in self.blocks and self.blocks[pos] != state:
                raise ValueError(f"overlap at {pos}: {self.blocks[pos]} vs {state}")
            self.blocks[pos] = state
        self.entities += other.shifted(offset).entities
        return self

    def shifted(self, offset: Pos) -> "Build":
        dx, dy, dz = offset
        return Build({(x + dx, y + dy, z + dz): s for (x, y, z), s in self.blocks.items()},
                     [((x + dx, y + dy, z + dz), e, n) for (x, y, z), e, n in self.entities])

    def with_base(self, material: str = "minecraft:smooth_stone") -> "Build":
        """Add a support block under every block in layer y=1 that lacks one."""
        for x, y, z in list(self.blocks):
            if y == 1 and (x, 0, z) not in self.blocks:
                self.blocks[(x, 0, z)] = material
        return self

    def bounds(self) -> tuple[Pos, Pos]:
        xs, ys, zs = zip(*self.blocks)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def to_commands(self, update: str = "all") -> list[str]:
        """setblock every block, summon the entities, then the update pass. `update` is a
        spec's `update_pass`: "all" clones every block onto itself; "none" skips the pass;
        "unobserved" sets observers last and clones every block but those an observer faces,
        since a clone swaps its block through a barrier and so pulses an observer watching
        it (CloneCommands); "strict" sets every block with `setblock ... strict` (no
        neighbour or shape updates at all) and runs no pass, so no observer sees the build
        being placed."""
        if update not in UPDATE_PASSES:
            raise ValueError(f"update pass {update!r} is not one of {', '.join(UPDATE_PASSES)}")
        # Bottom-up so attached blocks (torches, dust, levers) have their support first.
        order = sorted(self.blocks, key=lambda p: (p[1], p[0], p[2]))
        if update == "strict":
            return ([f"setblock ~{x} ~{y} ~{z} {self.blocks[(x, y, z)]} strict" for x, y, z in order]
                    + [f"summon {e} ~{x} ~{y} ~{z} {n}".rstrip() for (x, y, z), e, n in self.entities])
        watched = set()
        if update == "unobserved":
            observers = [p for p in order if block_id(self.blocks[p]) == "minecraft:observer"]
            order = [p for p in order if p not in set(observers)] + observers
            watched = {tuple(a + b for a, b in zip(p, STEP[facing(self.blocks[p])])) for p in observers}
        place = [f"setblock ~{x} ~{y} ~{z} {self.blocks[(x, y, z)]}" for x, y, z in order]
        # setblock only updates the placed block's own neighbours at placement time, so a
        # block placed after its power source never notices it. Cloning each block onto
        # itself runs updateNeighborsAt(pos) once the whole build exists, like the final
        # pass of structure-block placement.
        cloned = [] if update == "none" else [p for p in sorted(self.blocks, key=lambda p: (p[1], p[0], p[2]))
                                              if p not in watched]
        clones = [f"clone ~{x} ~{y} ~{z} ~{x} ~{y} ~{z} ~{x} ~{y} ~{z} replace force" for x, y, z in cloned]
        summon = [f"summon {e} ~{x} ~{y} ~{z} {n}".rstrip() for (x, y, z), e, n in self.entities]
        return place + summon + clones

    def to_mcfunction(self, update: str = "all") -> str:
        return "\n".join(self.to_commands(update)) + "\n"

    def to_functions(self, chunk: int, update: str = "all") -> list[str]:
        """to_commands as function bodies of at most `chunk` commands, to be run in order,
        each by its own command: one call runs at most max_command_sequence_length (65536)
        commands, nested calls included (Commands.executeCommandInContext)."""
        commands = self.to_commands(update)
        return ["\n".join(commands[i:i + chunk]) + "\n" for i in range(0, len(commands), chunk)] or ["\n"]


UPDATE_PASSES = ("all", "none", "unobserved", "strict")
STEP = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0),
        "down": (0, -1, 0), "up": (0, 1, 0)}


def block_id(state: str) -> str:
    return re.split(r"[\[{]", state)[0]


# registerDefaultState of the blocks whose facing the harness reads.
DEFAULT_FACING = {"minecraft:observer": "south", "minecraft:piston": "north", "minecraft:sticky_piston": "north"}


def facing(state: str) -> str | None:
    m = re.search(r"[\[,]facing=(\w+)", state.split("{")[0])
    return m.group(1) if m else DEFAULT_FACING.get(block_id(namespaced(state)))


def namespaced(state: str) -> str:
    """Add minecraft: to a bare id; properties and block-entity NBT may follow it."""
    return state if ":" in re.split(r"[\[{]", state)[0] else "minecraft:" + state


def write_datapack(datapacks_dir: Path, name: str, functions: dict[str, str],
                   tags: dict[str, str] | None = None) -> Path:
    """Write a data pack whose functions are callable as `/function <name>:<key>` and whose
    block tags (key -> JSON) are `#<name>:<key>`; functions and tags not given are removed."""
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
    tags = tags or {}
    tag_dir = root / "data" / name / "tags" / "block"
    for stale in tag_dir.glob("*.json"):
        if stale.stem not in tags:
            stale.unlink()
    if tags:
        tag_dir.mkdir(parents=True, exist_ok=True)
    for key, body in tags.items():
        (tag_dir / f"{key}.json").write_text(body)
    return root
