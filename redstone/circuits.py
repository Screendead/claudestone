"""Which circuit each block of a build belongs to, traced along the signal graph from seeds.

`trace(blocks, seeds)` floods each circuit forward from its seed cells, one breadth-first
search per circuit, and stops at any cell seeded for another circuit (or `fixed`). Edges:

- signal: a repeater or comparator powers the cell it faces (a solid block strongly), an
  observer the cell behind it, a torch the block above it strongly and the components around
  it; dust the block under it, the cells it points into and the dust it connects to (up and
  down steps included); a strongly powered solid block powers every component and dust
  beside it, a weakly (dust-) powered one every component but dust. Components take only
  what they read: a repeater its back (a diode into its side locks it), a comparator its back
  (diode, dust or redstone block into its side), a torch its own block, a piston any side but
  its front, plus quasi-connectivity (the cell above it) for pistons, droppers and dispensers;
  hoppers, bulbs, note blocks, lamps and doors any side.
- observe: a component, consumer or moved block whose state changes is seen by an observer
  facing it. A powered solid block changes no state and is not observed.
- analog: a container or copper bulb is read by a comparator behind it, or behind the solid
  block behind it.
- glue: a slime or honey block reached by a circuit drags the movable blocks beside it
  (slime and honey don't stick to each other; immovable and popped blocks never move).

Ownership of a cell, in this order:
  1. a seed or fixed cell: its own circuit;
  2. reached by glue: that circuit (several: shared), since it moves with that machine;
  3. reached by signal: the circuit at the smallest graph distance; a tie between circuits
     is shared;
  4. otherwise, the support of attached components (the block under dust, a repeater, a
     comparator or a torch, a wall torch's or lever's block): their circuit (several:
     shared);
  5. otherwise unassigned (None).
"""
from collections import Counter, deque
from dataclasses import dataclass, field

Pos = tuple[int, int, int]
SHARED = "shared"

STEP = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0),
        "down": (0, -1, 0), "up": (0, 1, 0)}
HORIZONTAL = ("north", "south", "west", "east")
UP, DOWN = STEP["up"], STEP["down"]

DIODES = {"repeater", "comparator"}
TORCHES = {"redstone_torch", "redstone_wall_torch"}
SWITCHES = {"lever"}
QC = {"piston", "sticky_piston", "dropper", "dispenser"}
CONSUMERS = QC | {"hopper", "note_block", "redstone_lamp", "tnt", "powered_rail", "activator_rail", "bell", "crafter"}
CONSUMER_SUFFIXES = ("copper_bulb", "_door", "_trapdoor", "_fence_gate")
ANALOG = {"hopper", "dropper", "dispenser", "chest", "trapped_chest", "barrel", "furnace", "blast_furnace", "smoker",
          "brewing_stand", "composter", "cauldron", "jukebox", "lectern", "crafter", "chiseled_bookshelf"}
ANALOG_SUFFIXES = ("copper_bulb", "shulker_box")
STICKY = {"slime_block", "honey_block"}
NON_CONDUCTORS = (STICKY | DIODES | TORCHES | SWITCHES | {
    "air", "redstone_wire", "redstone_block", "observer", "piston", "sticky_piston", "piston_head", "moving_piston",
    "hopper", "glass", "tinted_glass", "ice", "glowstone", "sea_lantern", "beacon", "scaffolding", "ladder", "chest",
    "trapped_chest", "lectern", "cauldron", "composter", "bell", "barrier", "light"})
NON_CONDUCTOR_SUFFIXES = ("_glass", "_glass_pane", "_slab", "_stairs", "_leaves", "_fence", "_wall", "_carpet", "_sign",
                          "_banner", "_button", "_pressure_plate", "_door", "_trapdoor", "_fence_gate", "copper_bulb",
                          "rail", "shulker_box", "_bed", "_head", "_skull", "_shelf")
IMMOVABLE = {"obsidian", "crying_obsidian", "bedrock", "barrier", "reinforced_deepslate", "end_portal_frame",
             "enchanting_table", "ender_chest", "respawn_anchor", "beacon", "spawner", "piston_head", "moving_piston",
             "command_block", "chain_command_block", "repeating_command_block", "structure_block", "jigsaw",
             "light", "lodestone", "vault", "trial_spawner"} | ANALOG
POPPED = DIODES | TORCHES | SWITCHES | {"redstone_wire", "air", "scaffolding", "ladder"}
POPPED_SUFFIXES = ("_button", "_pressure_plate", "_carpet", "_sign", "_banner", "_bed", "_head", "_skull", "_door",
                   "shulker_box")


def parse(state: str) -> tuple[str, dict[str, str]]:
    """Bare block id and properties; block-entity NBT is dropped."""
    block, _, rest = state.split("{")[0].partition("[")
    return block.removeprefix("minecraft:"), dict(kv.split("=", 1) for kv in rest.rstrip("]").split(",") if kv)


def _add(p: Pos, d: Pos, k: int = 1) -> Pos:
    return (p[0] + k * d[0], p[1] + k * d[1], p[2] + k * d[2])


def _has(block: str, names: set, suffixes: tuple = ()) -> bool:
    return block in names or block.endswith(suffixes)


def is_conductor(state: str) -> bool:
    """A full solid block that redstone powers. Copper bulbs are taken as non-conducting."""
    return not _has(parse(state)[0], NON_CONDUCTORS, NON_CONDUCTOR_SUFFIXES)


def is_consumer(state: str) -> bool:
    return _has(parse(state)[0], CONSUMERS, CONSUMER_SUFFIXES)


def is_movable(state: str) -> bool:
    """Moved by a piston or glue (not immovable and not popped)."""
    block, props = parse(state)
    if block in ("piston", "sticky_piston") and props.get("extended") == "true":
        return False
    return not (_has(block, IMMOVABLE, ANALOG_SUFFIXES) or _has(block, POPPED, POPPED_SUFFIXES))


def support_of(pos: Pos, state: str) -> Pos | None:
    """The block an attached component hangs on, or None."""
    block, props = parse(state)
    if block in ("redstone_wall_torch", "wall_torch") or block.endswith("_wall_sign"):
        return _add(pos, STEP[props["facing"]], -1)
    if block == "lever" or block.endswith("_button"):
        face = props.get("face", "wall")
        return _add(pos, DOWN if face == "floor" else UP if face == "ceiling" else
                    tuple(-v for v in STEP[props["facing"]]))
    if (block in DIODES | {"redstone_wire", "redstone_torch", "torch"} or block.endswith(("rail", "_pressure_plate",
                                                                                          "_carpet"))):
        return _add(pos, DOWN)
    return None


@dataclass
class Tracing:
    owner: dict[Pos, str | None]          # every block of the build
    how: dict[Pos, str]                    # seed, fixed, glue, signal, support, none
    reached: dict[Pos, dict[str, int]]     # circuit -> graph distance from its seeds, signal or glue
    seeds: dict[Pos, str] = field(default_factory=dict)

    @property
    def shared(self) -> set[Pos]:
        return {p for p, o in self.owner.items() if o == SHARED}

    @property
    def unassigned(self) -> set[Pos]:
        return {p for p, o in self.owner.items() if o is None}

    def counts(self, cells=None) -> Counter:
        return Counter(self.owner[p] for p in (self.owner if cells is None else cells))

    def disagreements(self, expected: dict[Pos, str]) -> list[tuple[Pos, str, str | None]]:
        """(pos, expected, traced) wherever another source (a generator's provenance) differs."""
        return [(p, e, self.owner.get(p)) for p, e in sorted(expected.items()) if self.owner.get(p) != e]


class _Graph:
    def __init__(self, blocks: dict[Pos, str]):
        self.blocks = blocks
        self.parsed = {p: parse(s) for p, s in blocks.items()}
        self.conductor = {p for p, s in blocks.items() if is_conductor(s)}
        self.watchers: dict[Pos, list[Pos]] = {}
        self.readers: dict[Pos, list[Pos]] = {}
        for p, (b, pr) in self.parsed.items():
            if b == "observer":
                self.watchers.setdefault(_add(p, STEP[pr["facing"]]), []).append(p)
            elif b == "comparator":
                back = _add(p, STEP[pr["facing"]])
                self.readers.setdefault(back, []).append(p)
                if back in self.conductor:
                    self.readers.setdefault(_add(back, STEP[pr["facing"]]), []).append(p)

    def kind(self, p: Pos) -> str | None:
        return self.parsed[p][0] if p in self.parsed else None

    def start(self, p: Pos) -> list[tuple]:
        """Nodes a seed cell starts: (pos, mode), mode 'strong'/'weak' for a powered solid block, 'comp' for a
        component, consumer or moved block."""
        out = [(p, "comp")]
        if p in self.conductor:
            out.append((p, "strong"))
        return out

    def emissions(self, node) -> list[tuple[Pos, Pos, str, str | None]]:
        """(source, target, emitter kind, solid-block power: 'strong'/'weak'/None)."""
        p, mode = node
        if mode in ("strong", "weak"):
            return [(p, _add(p, d), "solid-" + mode, None) for d in STEP.values()]
        b, pr = self.parsed[p]
        if b in DIODES:
            return [(p, _add(p, STEP[pr["facing"]], -1), "diode", "strong")]
        if b == "observer":
            return [(p, _add(p, STEP[pr["facing"]], -1), "observer", "strong")]
        if b in TORCHES or b in SWITCHES:
            att = support_of(p, self.blocks[p])
            strong = _add(p, UP) if b in TORCHES else att
            return [(p, _add(p, d), "torch", "strong" if _add(p, d) == strong else None)
                    for d in STEP.values() if _add(p, d) != att or b in SWITCHES]
        if b == "redstone_block":
            return [(p, _add(p, d), "block", None) for d in STEP.values()]
        if b == "redstone_wire":
            out = [(p, _add(p, DOWN), "dust", "weak")]
            for h in HORIZONTAL:
                q = _add(p, STEP[h])
                if pr.get(h, "none") != "none":
                    out.append((p, q, "dust", "weak"))
                    if pr[h] == "up":
                        out.append((p, _add(q, UP), "dust-step", None))
                    if q not in self.conductor:
                        out.append((p, _add(q, DOWN), "dust-step", None))
            return out
        return []

    def receive(self, src: Pos, cell: Pos, kind: str, power: str | None) -> list[tuple]:
        out = []
        below = _add(cell, DOWN)
        if self.kind(below) in QC and below != src and kind != "dust-step":
            out.append((below, "comp"))
        b = self.kind(cell)
        if b is None:
            return out
        pr = self.parsed[cell][1]
        if kind == "dust-step":
            return out + ([(cell, "comp")] if b == "redstone_wire" else [])
        if cell in self.conductor and power is not None and not kind.startswith("solid"):
            out.append((cell, power))
        d = (src[0] - cell[0], src[1] - cell[1], src[2] - cell[2])
        if b == "redstone_wire":
            if kind != "solid-weak":
                out.append((cell, "comp"))
        elif b == "repeater":
            if d == STEP[pr["facing"]] or kind == "diode" and d != tuple(-v for v in STEP[pr["facing"]]):
                out.append((cell, "comp"))
        elif b == "comparator":
            back = STEP[pr["facing"]]
            if d == back or kind in ("diode", "dust", "block") and d[1] == 0 and d != tuple(-v for v in back):
                out.append((cell, "comp"))
        elif b in TORCHES:
            if kind.startswith("solid") and src == support_of(cell, self.blocks[cell]):
                out.append((cell, "comp"))
        elif is_consumer(self.blocks[cell]):
            if not (b in ("piston", "sticky_piston") and d == STEP[pr["facing"]]):
                out.append((cell, "comp"))
        return out

    def successors(self, node) -> list[tuple[tuple, str]]:
        """(next node, edge kind)."""
        p, mode = node
        out = [(n, "signal") for s, t, k, pw in self.emissions(node) for n in self.receive(s, t, k, pw)]
        if mode == "comp":
            out += [((o, "comp"), "observe") for o in self.watchers.get(p, ())]
            b = self.kind(p)
            if b in ANALOG or b.endswith(ANALOG_SUFFIXES):
                out += [((r, "comp"), "analog") for r in self.readers.get(p, ())]
            if b in STICKY:
                for d in STEP.values():
                    q = _add(p, d)
                    if q in self.blocks and is_movable(self.blocks[q]) and {b, self.kind(q)} != STICKY:
                        out.append(((q, "comp"), "glue"))
        return out


def trace(blocks: dict[Pos, str], seeds: dict[str, "set[Pos] | list[Pos]"],
          fixed: dict[Pos, str] | None = None) -> Tracing:
    """seeds: circuit -> cells it starts from. fixed: cells with a set owner that no trace enters or leaves (a
    door's own blocks, say)."""
    g = _Graph(blocks)
    fixed = dict(fixed or {})
    seed_of: dict[Pos, str] = {}
    for name, cells in seeds.items():
        for p in cells:
            if p in seed_of and seed_of[p] != name:
                raise ValueError(f"{p} is a seed of both {seed_of[p]} and {name}")
            if p not in blocks:
                raise ValueError(f"seed {p} of {name} is not a block")
            seed_of[p] = name
    reached: dict[Pos, dict[str, int]] = {}
    glued: dict[Pos, set[str]] = {}
    for name, cells in seeds.items():
        dist = {}
        queue = deque()
        for p in cells:
            for n in g.start(p):
                dist[n] = 0
                queue.append(n)
        while queue:
            n = queue.popleft()
            for m, edge in g.successors(n):
                q = m[0]
                if q not in blocks:
                    continue
                if edge == "glue" and q not in seed_of and q not in fixed:
                    glued.setdefault(q, set()).add(name)
                if m in dist:
                    continue
                dist[m] = dist[n] + 1
                r = reached.setdefault(q, {})
                r[name] = min(r.get(name, dist[m]), dist[m])
                if q in fixed or seed_of.get(q, name) != name:
                    continue
                queue.append(m)
    owner: dict[Pos, str | None] = {}
    how: dict[Pos, str] = {}
    for p in blocks:
        if p in fixed:
            owner[p], how[p] = fixed[p], "fixed"
        elif p in seed_of:
            owner[p], how[p] = seed_of[p], "seed"
        elif p in glued:
            owner[p], how[p] = (next(iter(glued[p])) if len(glued[p]) == 1 else SHARED), "glue"
        elif p in reached:
            best = min(reached[p].values())
            names = [c for c, v in reached[p].items() if v == best]
            owner[p], how[p] = (names[0] if len(names) == 1 else SHARED), "signal"
    supported: dict[Pos, set] = {}
    for p, s in blocks.items():
        sup = support_of(p, s)
        if sup in blocks and sup not in owner and owner.get(p) is not None:
            supported.setdefault(sup, set()).add(owner[p])
    for p, names in supported.items():
        owner[p], how[p] = (next(iter(names)) if len(names) == 1 else SHARED), "support"
    for p in blocks:
        if p not in owner:
            owner[p], how[p] = None, "none"
    return Tracing(owner, how, reached, seed_of)
