"""Squid-ruleset door timing and seamless analysis over per-tick hallway observations.

A Run is O(-1) (the stable state before the input) followed by O(0..n), where O(t) is the
world after tick t's block-entity phase and tick 0 is the tick the input repeater's output
changes. Everything here is pure: the runner that probes the world lives elsewhere.

Movement model (door_harness_design.md section 0): a push or pull started in tick s shows a
moving_piston at the destination with saved progress (progressO) 0.0 at O(s) and 0.5 at
O(s+1), and the real block at O(s+2). A retraction that meets a still-moving block places it
early, at O(s+1). A 0-gt move is never seen moving: the cell simply changes at O(s). The
observed end of each movement is therefore Squid's formula end (standard s+2, pulse s+p,
instant s), and any other progress ladder is a timing-model disagreement.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

Pos = tuple[int, int, int]

AIR, DOOR, SURFACE, MOVING, HEAD, OTHER = 0, 1, 2, 3, 4, 9

# A quartz-like wall reads DOOR when door and surface material share a block, since the probe
# tests the door tag first; both look like hallway composition from inside.
COMPOSITION = frozenset({DOOR, SURFACE})
# An air cell in a wall shows whatever is behind it, which the probe does not see.
HOLES_ARE_CIRCUITRY = True
# "No entities visible": an invisible entity is not visible.
INVISIBLE_ENTITIES_COUNT = False

QUIET_TICKS = 40
MAX_PERIOD = 64
PERIODS = 3
MAX_TICKS = 600

STEP = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0),
        "east": (1, 0, 0), "down": (0, -1, 0), "up": (0, 1, 0)}
OPPOSITE = {"north": "south", "south": "north", "west": "east",
            "east": "west", "down": "up", "up": "down"}

LIGHT, DARK = "L", "D"  # no circuitry and no entities visible / no circuitry visible
COLUMNS = ("front", "opened", "closed", "opening", "closing")
TIERS = {  # section 2.1.4 table, read from the Door Rules doc
    "SUPER": (LIGHT, LIGHT, LIGHT, LIGHT, LIGHT),
    "FULL": (LIGHT, LIGHT, LIGHT, None, None),
    "SEMI": (DARK, DARK, None, None, None),
    "QUART": (DARK, None, None, None, None),
}


class TimingModelError(ValueError):
    """The observations disagree with Squid's movement end formulas."""


class DoorError(ValueError):
    """The run does not reach or hold the expected state."""


@dataclass(frozen=True)
class Moving:
    """A moving_piston block entity: the moved block's class and its saved NBT."""

    moved: int
    progress: float  # the saved `progress`, which is progressO
    extending: bool
    source: bool
    facing: str

    def direction(self) -> str:
        return self.facing if self.extending else OPPOSITE[self.facing]


@dataclass(frozen=True)
class Cell:
    code: int
    moving: Moving | None = None


@dataclass(frozen=True)
class Entity:
    """A non-player entity whose hitbox intersects `cells` of the visible region."""

    id: str
    cells: frozenset[Pos]
    invisible: bool = False


@dataclass(frozen=True)
class Observation:
    cells: Mapping[Pos, Cell]
    entities: tuple[Entity, ...] = ()

    def key(self) -> tuple:
        return (tuple(sorted(self.cells.items())),
                tuple(sorted((e.id, tuple(sorted(e.cells)), e.invisible) for e in self.entities)))


@dataclass
class Run:
    before: Observation
    ticks: list[Observation]

    def at(self, t: int) -> Observation:
        return self.before if t == -1 else self.ticks[t]

    @property
    def last(self) -> int:
        return len(self.ticks) - 1


@dataclass(frozen=True)
class Hallway:
    hallway: frozenset[Pos]
    frame: frozenset[Pos]
    surface: frozenset[Pos]  # visible cells outside the hallway (walls, floor, ceiling)
    front: frozenset[Pos]  # the part of the visible region on the front side of the frame

    @property
    def visible(self) -> frozenset[Pos]:
        return self.hallway | self.surface

    @classmethod
    def of(cls, hallway: Iterable[Pos], frame: Iterable[Pos], front: str,
           surface: Iterable[Pos] | None = None) -> "Hallway":
        """Default surface: each 6-neighbour of a hallway cell outside the hallway.

        Front: every visible cell level with the frame plane or on its `front` side.
        """
        hallway, frame = frozenset(hallway), frozenset(frame)
        if surface is None:
            surface = {_add(p, d) for p in hallway for d in STEP.values()} - hallway
        surface = frozenset(surface)
        step = STEP[front]
        axis = next(i for i, s in enumerate(step) if s)
        planes = {p[axis] for p in frame}
        if len(planes) != 1:
            raise ValueError(f"frame is not one cross-section along {front}")
        plane = planes.pop()
        front_cells = frozenset(p for p in hallway | surface if (p[axis] - plane) * step[axis] >= 0)
        return cls(hallway, frame, surface, front_cells)


@dataclass(frozen=True)
class Movement:
    """One block movement seen at `cell`, from `origin` (None when it is an in-place change)."""

    cell: Pos
    origin: Pos | None
    blocks: frozenset[int]  # classes of the block(s) involved, air excluded
    start: int
    end: int

    def touches(self, cells: frozenset[Pos]) -> bool:
        return self.cell in cells or self.origin in cells


Pattern = Mapping[Pos, frozenset[int]]


def open_pattern(h: Hallway, fill: Mapping[Pos, int] | None = None) -> Pattern:
    """Hallway cells hold their open composition: air unless the type says otherwise."""
    fill = fill or {}
    return {p: frozenset({fill.get(p, AIR)}) for p in h.hallway}


def closed_pattern(h: Hallway) -> Pattern:
    return {p: frozenset({DOOR if p in h.frame else AIR}) for p in h.hallway}


def matches(obs: Observation, pattern: Pattern) -> bool:
    return all(p in obs.cells and obs.cells[p].code in ok for p, ok in pattern.items())


def pattern_since(run: Run, pattern: Pattern, w: int) -> int:
    """Smallest t >= 0 such that the pattern holds at every tick in [t, w]."""
    if not matches(run.at(w), pattern):
        raise DoorError(f"pattern does not hold at the quiescent tick {w}")
    t = w
    while t > 0 and matches(run.at(t - 1), pattern):
        t -= 1
    return t


def quiescence(run: Run, quiet: int = QUIET_TICKS, max_period: int = MAX_PERIOD,
               periods: int = PERIODS) -> tuple[int, int] | None:
    """(W, period): W is the first tick from which the run repeats with that period to its end.

    Period 1 means static, which needs `quiet` ticks of evidence; a longer period needs
    `periods` repeats. None when the recording shows neither.
    """
    keys = [o.key() for o in run.ticks]
    n = len(keys)
    for t in range(n):
        if all(k == keys[t] for k in keys[t:]):
            # Static from t: every later start is static too, with less evidence.
            return (t, 1) if n - 1 - t >= quiet else None
        for p in range(2, max_period + 1):
            if n - 1 - t < periods * p:
                break
            if all(keys[i] == keys[i + p] for i in range(t, n - p)):
                return t, p
    return None


def settle(run: Run, max_ticks: int = MAX_TICKS, **kw) -> tuple[int, int]:
    q = quiescence(run, **kw)
    if q is None or q[0] > max_ticks:
        raise DoorError(f"no stable state within {max_ticks} ticks: time is unbounded")
    return q


def movements(run: Run, cells: Iterable[Pos]) -> list[Movement]:
    """Every block movement seen in `cells`, with its formula-checked end tick.

    A run of moving_piston sightings at a cell is one movement from its origin: 0.0 then
    0.5 then real (standard, end s+2) or 0.0 then real (cut short, end s+1). A change
    between two non-moving states is instant (end = t) unless it is the origin of a
    movement starting at t being vacated.
    """
    cells = frozenset(cells)
    moves: list[Movement] = []
    for pos in sorted(cells):
        t = -1
        while t <= run.last:
            m = _cell(run.at(t), pos).moving
            if m is None:
                t += 1
                continue
            first = t
            ladder = []
            while t <= run.last and (cur := _cell(run.at(t), pos).moving) is not None:
                # 0.0 after a full ladder: the move landed and another began in the same tick.
                if len(ladder) == 2 and cur.progress == 0.0:
                    break
                ladder.append(cur)
                t += 1
            if t > run.last:
                raise TimingModelError(f"{pos} still moving at the end of the recording")
            seen = [x.progress for x in ladder]
            # A move already under way in O(-1) was first sighted before the recording.
            start = first - round(2 * seen[0]) if first == -1 else first
            full = [0.0, 0.5]
            if not (seen == full[:len(seen)] or first == -1 and seen == full[-len(seen):]):
                raise TimingModelError(
                    f"{pos} from tick {start}: progress {seen}, "
                    "expected [0.0, 0.5] (standard) or [0.0] (cut pulse)")
            if len({(x.moved, x.extending, x.source, x.facing) for x in ladder}) != 1:
                raise TimingModelError(f"{pos} from tick {start}: moving block changed mid-move")
            dx, dy, dz = STEP[m.direction()]
            moves.append(Movement(pos, (pos[0] - dx, pos[1] - dy, pos[2] - dz),
                                  frozenset({m.moved}), start, t))
    vacated = {(mv.origin, mv.start, b) for mv in moves for b in mv.blocks}
    for pos in sorted(cells):
        for t in range(run.last + 1):
            before, after = _cell(run.at(t - 1), pos), _cell(run.at(t), pos)
            if MOVING in (before.code, after.code) or before.code == after.code:
                continue
            if after.code == AIR and (pos, t, before.code) in vacated:
                continue
            moves.append(Movement(pos, None, frozenset({before.code, after.code}) - {AIR}, t, t))
    return sorted(moves, key=lambda mv: (mv.end, mv.cell))


def opening_time(h: Hallway, run: Run, w: int, fill: Mapping[Pos, int] | None = None) -> int:
    """Input to the end of the last movement that leaves the hallway in its open pattern.

    Only movements into or out of hallway cells count, so a z-fighting wall swap after the
    hallway is clear adds to visible time but not to this.
    """
    t = pattern_since(run, open_pattern(h, fill), w)
    ends = [mv.end for mv in movements(run, h.visible) if mv.touches(h.hallway) and mv.end <= w]
    return max([t, *ends])


def closing_time(h: Hallway, run: Run, w: int) -> int:
    """Input to the end of the last door-block movement into, out of or within the hallway."""
    ends = [mv.end for mv in movements(run, h.visible)
            if DOOR in mv.blocks and mv.touches(h.hallway) and mv.end <= w]
    if not ends:
        raise DoorError("no door block moved in the hallway")
    t = max(ends)
    if pattern_since(run, closed_pattern(h), w) > t:
        raise DoorError(f"closed pattern does not hold from the last door movement at {t}")
    return t


def visible_time(h: Hallway, run: Run, w: int) -> int | None:
    """Latest tick <= w with visible block movement in the hallway or its surfaces in view.

    Movement at t: a moving_piston in view at O(t), or any cell in view differing between
    O(t-1) and O(t) (the landing, an instant change, a z-fighting swap). A static piston head
    is circuitry, not movement. Capping at w makes a door whose clock moves in view forever
    report the tick its stable state begins.
    """
    if any(_moved_in_view(run, h, t) for t in range(w + 1, run.last + 1)):
        return w
    for t in range(w, -1, -1):
        if _moved_in_view(run, h, t):
            return t
    return None


def _moved_in_view(run: Run, h: Hallway, t: int) -> bool:
    now, then = run.at(t), run.at(t - 1)
    seen = in_view(now, h, h.visible) | in_view(then, h, h.visible)
    return any(_cell(now, p).code == MOVING or _cell(now, p) != _cell(then, p) for p in seen)


@dataclass(frozen=True)
class Times:
    open: int
    open_visible: int | None
    close: int
    close_visible: int | None
    w_open: int
    w_close: int


def door_times(h: Hallway, opening: Run, closing: Run, fill: Mapping[Pos, int] | None = None,
               max_ticks: int = MAX_TICKS) -> Times:
    """The four Squid times; both runs must be repeater-input runs from their own tick 0."""
    w_open, _ = settle(opening, max_ticks)
    w_close, _ = settle(closing, max_ticks)
    return Times(opening_time(h, opening, w_open, fill), visible_time(h, opening, w_open),
                 closing_time(h, closing, w_close), visible_time(h, closing, w_close),
                 w_open, w_close)


def in_view(obs: Observation, h: Hallway, cells: frozenset[Pos]) -> frozenset[Pos]:
    """Hallway cells, plus surface cells beside a hallway cell not filled by a solid block.

    A wall cell behind a closed door block is hidden, so a retracted head there is not seen.
    A moving door or wall block hides what follows it: the renderer draws it between its
    origin and destination, covering the cross-section.
    """
    open_hall = {p for p in h.hallway if not _solid(_cell(obs, p))}
    return frozenset(p for p in cells if p in h.hallway or
                     any(_add(p, d) in open_hall for d in STEP.values()))


def exposure(obs: Observation, h: Hallway, cells: frozenset[Pos]) -> str | None:
    """LIGHT, DARK, or None when circuitry is visible among `cells`."""
    cells = in_view(obs, h, cells)
    for p in cells:
        c = _cell(obs, p)
        if c.code in (HEAD, OTHER):
            return None
        if c.code == MOVING and (c.moving.source or c.moving.moved not in COMPOSITION):
            return None
        if HOLES_ARE_CIRCUITRY and c.code == AIR and p in h.surface:
            return None
    seen = any(e.cells & cells for e in obs.entities if INVISIBLE_ENTITIES_COUNT or not e.invisible)
    return DARK if seen else LIGHT


def worst(grades: Iterable[str | None]) -> str | None:
    rank = {LIGHT: 2, DARK: 1, None: 0}
    return min(grades, key=rank.__getitem__, default=LIGHT)


@dataclass(frozen=True)
class Seamless:
    front: str | None
    opened: str | None
    closed: str | None
    opening: str | None
    closing: str | None

    def tier(self) -> str | None:
        got = [getattr(self, c) for c in COLUMNS]
        for name, need in TIERS.items():
            if all(n is None or worst([g, n]) == n for g, n in zip(got, need)):
                return name
        return None


def seamless(h: Hallway, opening: Run, w_open: int, closing: Run, w_close: int) -> Seamless:
    """Grade each tier column. Stable windows run from W to the end of the recording, so a
    periodic stable state is judged in every phase; motion windows are ticks 0..W-1.
    """
    v = h.visible
    closed_state = [closing.at(t) for t in range(w_close, closing.last + 1)] + [opening.before]
    open_state = [opening.at(t) for t in range(w_open, opening.last + 1)] + [closing.before]
    return Seamless(
        front=worst(exposure(o, h, h.front) for o in closed_state),
        opened=worst(exposure(o, h, v) for o in open_state),
        closed=worst(exposure(o, h, v) for o in closed_state),
        opening=worst(exposure(opening.at(t), h, v) for t in range(w_open)),
        closing=worst(exposure(closing.at(t), h, v) for t in range(w_close)),
    )


@dataclass(frozen=True)
class ResetScan:
    results: dict[int, bool] = field(default_factory=dict)
    k_star: int | None = None
    reset: int | None = None


def reset_search(trial: Callable[[int], bool], k_min: int, k_max: int, visible: int) -> ResetScan:
    """Linear scan of re-toggle offsets k (ticks after the first input's tick 0).

    k* is the smallest k from which every tested offset up to k_max passes ("at any time
    thereafter"); R = k* - visible, negative when the door can be re-toggled before its
    visible time ends. Pass/fail is not assumed monotonic, so every k is tried.
    """
    results = {k: bool(trial(k)) for k in range(k_min, k_max + 1)}
    k_star = None
    for k in range(k_max, k_min - 1, -1):
        if not results[k]:
            break
        k_star = k
    return ResetScan(results, k_star, None if k_star is None else k_star - visible)


def _solid(c: Cell) -> bool:
    if c.code == MOVING:
        return not c.moving.source and c.moving.moved in COMPOSITION
    return c.code in COMPOSITION


def _cell(obs: Observation, pos: Pos) -> Cell:
    return obs.cells.get(pos, Cell(AIR))


def _add(a: Pos, b: Pos) -> Pos:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]
