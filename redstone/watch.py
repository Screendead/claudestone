"""The camera director: moves the players on main so they watch the harness work, hands-off.

One director process (`python -m scripts.watch run`, started by `autostart`) owns the
players' camera and the small status text, so concurrent tests, satellites and agents never
fight over them. It reads what happened from files the harness writes anyway:

- server/watch/events.jsonl: `test` (a build was loaded, with its world box) and `result`
  events from redstone.spec, appended by `emit`;
- server/watch/status/<plot>.json: the latest progress line of a test, from `set_status`;
- server/showroom/<plot>.json: each variant stood in a showroom slot, with its result;
- traces/<spec>/<test>.json: finished main-plot tests, used only while events.jsonl is quiet
  (a pytest started before the events existed).

Every online player on main is watched (tag `watch`, spectator mode) unless opted out with
`python -m scripts.watch off`; the gamemode each had before is kept in state.json and restored
on opt-out. Settings live in config.json and are reread while the director runs.

Writers (`emit`, `set_status`, `autostart`) never raise: a test must not fail or slow because
the director is missing or broken.
"""

import fcntl
import json
import math
import os
import re
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field, replace
from pathlib import Path

from .plots import MAIN, PLOTS, SURFACE
from . import servers
from .servers import ROOT

DIR = ROOT / "watch"
EVENTS = DIR / "events.jsonl"
STATUS = DIR / "status"
STATE = DIR / "state.json"
CONFIG = DIR / "config.json"
LOCK = DIR / "director.lock"
PID = DIR / "director.pid"
LOG = DIR / "director.log"
SHOWROOM = ROOT / "showroom"
TRACES = ROOT.parent / "traces"
EVENTS_MAX = 1 << 20
TAG = "watch"
EYE = 1.62  # a standing player's eye height; tp places the feet
GAMEMODES = ["survival", "creative", "adventure", "spectator"]

DEFAULTS = {
    "enabled": True,
    "orbit": True,
    "dwell": 8.0,        # seconds a shot is held at least
    "tour_dwell": 16.0,  # seconds per shot when nothing new happens
    "tour_min": 4.0,     # seconds a touring shot is held before an event may cut in
    "camera": "entity",  # or "tp": teleport the players instead (steps, but needs no entity)
    "rate": 20.0,        # director loop, and tp-camera updates, per second
    "glide": 20,         # teleport_duration of the camera entities, ticks: longer is smoother and lags more
    "attach_delay": 0.6, # seconds from summoning the camera entity to spectating it
    "text_every": 0.5,   # the client drops an actionbar after 3 s of its ticks, which run fast in a warp
    "fov": 70.0,         # the client's vertical field of view
    "aspect": 16 / 9,
    "margin": 0.85,      # of the half field of view the build may fill
    "elevation": 35.0,
    "motion": "orbit",   # "orbit": swing round the build; "dolly": slide sideways
    "sway": 20.0,        # degrees either side of north an orbit swings
    "dolly": 0.2,        # how far a dolly slides either side, as a fraction of the distance
    "period": 60.0,      # seconds per full swing
    "stale": 90.0,       # an event not shown within this long is dropped
    "tour_size": 12,
}
MIN_DISTANCE = 6.0
MAX_ELEVATION = 65.0
GROUND_CLEARANCE = 1.5  # of the eye above the surface
# Priorities: a failure first, then a variant not seen before, then a live test on main.
FAIL, NEW, LIVE, PLAIN = 3, 2, 1, 0

Box = tuple[float, float, float, float, float, float]  # x0 y0 z0 x1 y1 z1, the far side exclusive
Vec = tuple[float, float, float]


# ---- writers, called from the harness ----------------------------------------------------

def emit(kind: str, **fields) -> None:
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        if EVENTS.exists() and EVENTS.stat().st_size > EVENTS_MAX:
            EVENTS.replace(EVENTS.with_suffix(".jsonl.1"))
        line = json.dumps({"kind": kind, "time": time.time(), **fields}) + "\n"
        with open(EVENTS, "a") as f:
            f.write(line)
    except Exception:
        pass


def set_status(plot: str, text: str) -> None:
    try:
        STATUS.mkdir(parents=True, exist_ok=True)
        tmp = STATUS / f".{plot}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps({"text": text, "time": time.time()}))
        tmp.replace(STATUS / f"{plot}.json")
    except Exception:
        pass


def world_box(origin, build) -> Box:
    (lx, ly, lz), (hx, hy, hz) = build.bounds()
    ox, oy, oz = origin
    return (ox + lx, oy + ly, oz + lz, ox + hx + 1, oy + hy + 1, oz + hz + 1)


def running() -> bool:
    """Whether a director holds its lock."""
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        with open(LOCK, "a") as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
            fcntl.flock(f, fcntl.LOCK_UN)
            return False
    except OSError:
        return False


def autostart(force: bool = False) -> bool:
    """Start the director in the background unless one runs, `$REDSTONE_WATCH` is 0/off, or
    `scripts.watch stop` turned it off. Whether it started one."""
    try:
        if not force and (os.environ.get("REDSTONE_WATCH", "1").lower() in ("0", "off", "false", "no")
                          or not load_config()["enabled"]):
            return False
        if running():
            return False
        DIR.mkdir(parents=True, exist_ok=True)
        # Detached, and not holding the caller's stdout: a runner waiting for EOF would hang.
        with open(LOG, "a") as log:
            subprocess.Popen([sys.executable, "-m", "scripts.watch", "run"], cwd=ROOT.parent,
                             stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             start_new_session=True)
        return True
    except Exception:
        return False


# ---- settings and player state -------------------------------------------------------------

def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def load_config(path: Path | None = None) -> dict:
    got = _read_json(path or CONFIG, {})
    return DEFAULTS | {k: v for k, v in (got if isinstance(got, dict) else {}).items() if k in DEFAULTS}


def save_config(changes: dict, path: Path | None = None) -> dict:
    path = path or CONFIG
    cfg = load_config(path) | changes
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps({k: v for k, v in cfg.items() if v != DEFAULTS[k]}, indent=1))
    tmp.replace(path)
    return cfg


class State:
    """server/watch/state.json: {"optout": [names], "gamemode": {name: mode to restore}}. A
    name in `gamemode` is a player the director put in spectator. Use as a context manager:
    the CLI and the director both change it."""

    def __init__(self, path: Path | None = None):
        self.path = path or STATE

    def __enter__(self) -> dict:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = open(self.path.with_suffix(".lock"), "a")
        fcntl.flock(self.lock, fcntl.LOCK_EX)
        got = _read_json(self.path, {})
        self.data = {"optout": list(got.get("optout", [])), "gamemode": dict(got.get("gamemode", {}))}
        self.before = json.dumps(self.data, sort_keys=True)
        return self.data

    def __exit__(self, *exc):
        try:
            if json.dumps(self.data, sort_keys=True) != self.before:
                tmp = self.path.with_suffix(f".{os.getpid()}.tmp")
                tmp.write_text(json.dumps(self.data, indent=1, sort_keys=True))
                tmp.replace(self.path)
        finally:
            self.lock.close()


def online(rcon) -> list[str]:
    return online_from(rcon.cmd("list"))


def online_from(reply: str) -> list[str]:
    _, _, names = reply.partition(":")
    return [n.strip() for n in names.split(",") if n.strip()]


def default_gamemode() -> str:
    try:
        props = (ROOT / "server.properties").read_text()
        return re.search(r"^gamemode=(\w+)", props, re.M).group(1)
    except Exception:
        return "creative"


def gamemode_of(rcon, player: str) -> str | None:
    m = re.search(r"data: (\d+)", rcon.cmd(f"data get entity {player} playerGameType"))
    return GAMEMODES[int(m.group(1))] if m and int(m.group(1)) < len(GAMEMODES) else None


def reconcile(rcon, players: list[str], state: dict, fallback: str, seen: set | None = None) -> list[str]:
    """Watch each of `players` that is not opted out; restore those that are and that the
    director had put in spectator. `seen`: players already handled this session. Returns the
    watched ones."""
    watched = []
    for p in players:
        if p in state["optout"]:
            if p in state["gamemode"]:
                rcon.cmd(f"tag {p} remove {TAG}")
                rcon.cmd(f"kill @e[type=item_display,tag={TAG}_cam_{p}]")
                rcon.cmd(f"execute as {p} run gamemode {state['gamemode'].pop(p)}")
            continue
        if p not in state["gamemode"]:
            mode = gamemode_of(rcon, p)
            if mode is None:
                continue
            # A player already in spectator was not put there by us: restore the default.
            state["gamemode"][p] = fallback if mode == "spectator" else mode
            # As the player: changing another player's gamemode tells them so in chat
            # (GameModeCommand.logGamemodeChange).
            rcon.cmd(f"execute as {p} run gamemode spectator")
            rcon.cmd(f"tag {p} add {TAG}")
        elif seen is not None and p not in seen:
            rcon.cmd(f"tag {p} add {TAG}")
        if seen is not None:
            seen.add(p)
        watched.append(p)
    return watched


# ---- framing -------------------------------------------------------------------------------

def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(_dot(a, a))
    return tuple(x / n for x in a)


def centre(box: Box) -> Vec:
    return ((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2)


def corners(box: Box) -> list[Vec]:
    return [(x, y, z) for x in (box[0], box[3]) for y in (box[1], box[4]) for z in (box[2], box[5])]


def look(eye: Vec, target: Vec) -> tuple[float, float]:
    """Minecraft yaw and pitch from eye to target: yaw 0 faces +z (south), 90 faces -x
    (west); a positive pitch looks down."""
    dx, dy, dz = _sub(target, eye)
    return math.degrees(math.atan2(-dx, dz)), math.degrees(math.atan2(-dy, math.hypot(dx, dz)))


def facing(yaw: float, pitch: float) -> Vec:
    y, p = math.radians(yaw), math.radians(pitch)
    return (-math.sin(y) * math.cos(p), -math.sin(p), math.cos(y) * math.cos(p))


def offset(azimuth: float, elevation: float) -> Vec:
    """Unit vector from a target to a camera north of it at azimuth 0; a positive azimuth
    moves the camera east. A camera there has yaw == azimuth and pitch == elevation."""
    a, e = math.radians(azimuth), math.radians(elevation)
    return (math.sin(a) * math.cos(e), math.sin(e), -math.cos(a) * math.cos(e))


def basis(forward: Vec) -> tuple[Vec, Vec]:
    right = _unit(_cross(forward, (0.0, 1.0, 0.0)))
    return right, _cross(right, forward)


def half_tangents(fov: float, aspect: float) -> tuple[float, float]:
    """tan of the half field of view, horizontal and vertical."""
    tv = math.tan(math.radians(fov / 2))
    return tv * aspect, tv


def fit_distance(box: Box, azimuth: float, elevation: float, fov: float = DEFAULTS["fov"],
                 aspect: float = DEFAULTS["aspect"], margin: float = DEFAULTS["margin"],
                 lateral: float = 0.0) -> float:
    """The least distance D from the box centre, along offset(azimuth, elevation), at which a
    camera looking at the centre has every corner within `margin` of each half field of view,
    also when it is moved sideways (without turning) by up to `lateral` * D."""
    c = centre(box)
    f = tuple(-x for x in offset(azimuth, elevation))
    r, u = basis(f)
    th, tv = half_tangents(fov, aspect)
    wide = 1 - lateral / (th * margin)
    if wide <= 0:
        raise ValueError(f"a sideways move of {lateral} of the distance never fits")
    need = 0.0
    for p in corners(box):
        q = _sub(p, c)
        along = _dot(q, f)
        need = max(need, (abs(_dot(q, r)) / (th * margin) - along) / wide, abs(_dot(q, u)) / (tv * margin) - along)
    return need


def _hits(eye: Vec, target: Vec, box: Box) -> bool:
    """Whether the segment from eye to target crosses the box (slab test)."""
    lo, hi = 0.0, 1.0
    d = _sub(target, eye)
    for i in range(3):
        if abs(d[i]) < 1e-9:
            if not box[i] <= eye[i] <= box[i + 3]:
                return False
            continue
        a, b = (box[i] - eye[i]) / d[i], (box[i + 3] - eye[i]) / d[i]
        lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
        if lo > hi:
            return False
    return True


def _inside(p: Vec, box: Box, pad: float = 0.5) -> bool:
    return all(box[i] - pad <= p[i] <= box[i + 3] + pad for i in range(3))


@dataclass(frozen=True)
class Label:
    """A billboarded text_display: a flat panel through its anchor that turns to face the
    camera, `half` blocks either side of the anchor, from y0 to y1."""
    x: float
    z: float
    half: float
    y0: float
    y1: float

    def blocks(self, eye: Vec, target: Vec) -> bool:
        nx, nz = eye[0] - self.x, eye[2] - self.z
        n = math.hypot(nx, nz)
        if n < 1:
            return self.y0 - 1 <= eye[1] <= self.y1 + 1  # the camera is at the anchor
        # Signed distances of the ends from the panel's plane (normal points at the eye).
        de = n
        dt = ((target[0] - self.x) * nx + (target[2] - self.z) * nz) / n
        if dt >= 0:
            return False  # the target is on the camera's side of the panel
        k = de / (de - dt)
        px, py, pz = (e + k * (t - e) for e, t in zip(eye, target))
        return math.hypot(px - self.x, pz - self.z) <= self.half and self.y0 <= py <= self.y1


@dataclass(frozen=True)
class Pillar:
    """Something the eye must stay out of but may see past: the glass corner posts."""
    box: Box


def clear(eye: Vec, target: Vec, obstacles: list, ground: float = SURFACE) -> bool:
    """Whether the eye is above ground, out of every obstacle and sees the target past them."""
    if eye[1] < ground + GROUND_CLEARANCE:
        return False
    for o in obstacles:
        if isinstance(o, Label):
            if o.blocks(eye, target):
                return False
        elif isinstance(o, Pillar):
            if _inside(eye, o.box):
                return False
        elif _inside(eye, o) or _hits(eye, target, o):
            return False
    return True


def _near(o, c: Vec, reach: float) -> bool:
    if isinstance(o, Label):
        return math.hypot(o.x - c[0], o.z - c[2]) < reach + o.half
    box = o.box if isinstance(o, Pillar) else o
    return all(box[i] - reach <= c[i] <= box[i + 3] + reach for i in range(3))


@dataclass
class Framing:
    box: Box
    elevation: float
    distance: float
    sway: float = 0.0   # degrees the camera swings round the box at the ends of its motion
    dolly: float = 0.0  # or: how far it slides sideways there, as a fraction of `distance`
    azimuth: float = 0.0

    def pose(self, phase: float = 0.0) -> tuple[Vec, float, float]:
        """Eye position, yaw and pitch at `phase` (-1..1) of the motion. A slide keeps the
        rotation of phase 0."""
        c = centre(self.box)
        o = offset(self.azimuth + phase * self.sway, self.elevation)
        eye = tuple(ci + self.distance * oi for ci, oi in zip(c, o))
        yaw, pitch = look(eye, c)
        if self.dolly:
            r, _ = basis(facing(yaw, pitch))
            eye = tuple(e + phase * self.dolly * self.distance * ri for e, ri in zip(eye, r))
        return eye, yaw, pitch


LOW_ELEVATION = 50.0  # above this, a smaller motion is tried before a steeper view


def frame(box: Box, obstacles: list, cfg: dict, motion: str | None) -> Framing:
    """A camera that sees the whole box throughout its motion ("orbit": a swing of `sway`
    degrees round it; "dolly": a sideways slide of `dolly` times the distance; None: still),
    with a clear eye and line of sight. Tries, nearest first: the configured elevation up to
    LOW_ELEVATION with the full motion, then half and none, then steeper views the same way."""
    sway = cfg["sway"] if motion == "orbit" else 0.0
    dolly = cfg["dolly"] if motion == "dolly" else 0.0
    base = int(cfg["elevation"])
    low = [e for e in range(base, int(LOW_ELEVATION) + 1, 5)] or [base]
    high = [e for e in range(low[-1] + 5, int(MAX_ELEVATION) + 1, 5)]
    sizes = [1.0, 0.5, 0.0] if sway or dolly else [0.0]
    tiers = [(els, k) for els in (low, high) if els for k in sizes]

    def phases(f: Framing):
        steps = max(1, math.ceil(max(f.sway, f.dolly * f.distance * 4)))
        return [k / steps for k in range(-steps, steps + 1)]

    def fit(e, k):
        azimuths = [a * k * sway for a in (-1, -0.5, 0, 0.5, 1)] if sway else [0.0]
        return max(MIN_DISTANCE, max(fit_distance(box, a, e, cfg["fov"], cfg["aspect"], cfg["margin"], k * dolly)
                                     for a in azimuths))

    c = centre(box)
    reach = 3 * fit(base, 1.0) + 1
    near = [o for o in obstacles if _near(o, c, reach)]
    for scale in (1.0, 1.25, 1.5, 2.0, 2.5, 3.0):
        for els, k in tiers:
            for e in els:
                f = Framing(box, e, fit(e, k) * scale, k * sway, k * dolly)
                if all(clear(f.pose(ph)[0], c, near) for ph in phases(f)):
                    return f
    return Framing(box, base, fit(base, 0.0))


def phase_at(t: float, cfg: dict) -> float:
    """Where the motion is t seconds into a shot, -1..1: a sine whose amplitude eases in, so
    it starts still."""
    if t <= 0:
        return 0.0
    ramp = min(1.0, t / (cfg["period"] / 4))
    ease = ramp * ramp * (3 - 2 * ramp)
    return math.sin(2 * math.pi * t / cfg["period"]) * ease


# ---- what is in the world ------------------------------------------------------------------

def _pad(box: Box, p: float) -> Box:
    return (box[0] - p, box[1] - p, box[2] - p, box[3] + p, box[4] + p, box[5] + p)


def fixed_obstacles() -> list:
    """Each plot's glass corner posts, name label and status sign (scripts.plots draws them)."""
    out = []
    for p in PLOTS.values():
        (ox, oy, oz), (sx, sy, sz) = p.origin, p.size
        x0, z0, x1, z1 = ox - 2, oz - 2, ox + sx + 1, oz + sz + 1
        out += [Pillar(_pad((x, oy, z, x + 1, oy + sy, z + 1), 0.3)) for x in (x0, x1) for z in (z0, z1)]
        cx = ox + sx / 2
        out.append(Label(cx, z0 - 1, (7 * len(p.name) + 2) * 0.025 * 8 / 2 + 0.5, oy + 2.5, oy + 5.5))
        if p.name != MAIN.name:
            # About 25 characters wide: a spec and test name, rarely the full line width.
            out.append(Label(cx, oz + sz / 2, 25 * 6 * 0.025 * 7 / 2 + 0.5, oy + sy + 1.5, oy + sy + 9))
    return out


def slot_box(plot: str, entry: dict) -> Box | None:
    """World box of a showroom entry: its build and the label above it."""
    try:
        (ox, oy, oz) = PLOTS[plot].origin
        (sx, sz), (w, h, d) = entry["slot"], entry["size"]
        x = ox + sx + (entry["box"][0] - w) // 2
        return (x, oy, oz + sz, x + w, oy + h + 2, oz + sz + d)
    except (KeyError, TypeError, ValueError):
        return None


def entry_status(entry: dict) -> str:
    results = [r.get("result") for r in entry.get("results", {}).values()]
    if "fail" in results:
        return "fail"
    return "pass" if results and all(r == "pass" for r in results) else "untested"


COLOUR = {"pass": "green", "fail": "red", "untested": "yellow", "running": "yellow"}


@dataclass
class Shot:
    plot: str
    spec: str
    box: Box
    kind: str      # test, result, placed, tour
    status: str    # running, pass, fail, untested
    time: float
    priority: int = PLAIN
    detail: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return self.plot, self.spec


def showroom_shots(showroom: Path = SHOWROOM) -> list[Shot]:
    out = []
    for path in sorted(showroom.glob("*.json")):
        plot = path.stem
        if plot not in PLOTS:
            continue
        for name, e in _read_json(path, {}).get("specs", {}).items():
            box = slot_box(plot, e)
            if box:
                delays = [r["delay"] for r in e.get("results", {}).values() if r.get("delay") is not None]
                status = entry_status(e)
                out.append(Shot(plot, name, box, "placed", status, e.get("tested", 0),
                                detail=f"{status}" + (f" · {max(delays)} ticks" if delays else "")))
    return out


def slot_obstacles(plot: str, spec: str, showroom: Path = SHOWROOM) -> list[Box]:
    specs = _read_json(showroom / f"{plot}.json", {}).get("specs", {})
    return [b for n, e in specs.items() if n != spec and (b := slot_box(plot, e))]


class Sources:
    """New shots since the last poll, from the event log, the showroom files and, while the
    event log is quiet, finished main-plot traces."""

    def __init__(self, events: Path = EVENTS, showroom: Path = SHOWROOM, traces: Path = TRACES,
                 start: float | None = None):
        self.events, self.showroom, self.traces = events, showroom, traces
        self.start = time.time() if start is None else start
        self.offset, self.inode = None, None
        self.known = {s.key: s.time for s in showroom_shots(showroom)}
        self.trace_seen: dict[Path, float] = {}
        self.last_main: Shot | None = None
        self._box_cache: dict[str, tuple[float, Box | None]] = {}

    def poll(self, now: float) -> list[Shot]:
        out = self._events(now) + self._showroom()
        if not self._events_recent(now):
            out += self._traces()
        for s in out:
            if s.plot == MAIN.name:
                self.last_main = s
        return out

    def _events_recent(self, now: float) -> bool:
        try:
            return now - self.events.stat().st_mtime < 600
        except OSError:
            return False

    def _events(self, now: float) -> list[Shot]:
        try:
            st = self.events.stat()
        except OSError:
            return []
        if self.offset is None:
            self.offset, self.inode = st.st_size, st.st_ino  # only what happens from now on
        if st.st_ino != self.inode or st.st_size < self.offset:
            self.offset, self.inode = 0, st.st_ino
        if st.st_size == self.offset:
            return []
        with open(self.events, "rb") as f:
            f.seek(self.offset)
            data = f.read()
        end = data.rfind(b"\n") + 1  # a line still being written waits for the next poll
        self.offset += end
        out = []
        for line in data[:end].splitlines():
            try:
                shot = event_shot(json.loads(line))
            except (ValueError, TypeError, KeyError):
                continue
            if shot:
                out.append(shot)
        return out

    def _showroom(self) -> list[Shot]:
        out = []
        for s in showroom_shots(self.showroom):
            before = self.known.get(s.key)
            if s.time and (before is None or s.time > before) and s.time > self.start - 1:
                s.priority = FAIL if s.status == "fail" else NEW if before is None else PLAIN
                s.detail = ("new · " if before is None else "") + s.detail
                out.append(s)
            self.known[s.key] = max(s.time, before or 0)
        return out

    def _traces(self) -> list[Shot]:
        out = []
        try:
            dirs = list(os.scandir(self.traces))
        except OSError:
            return []
        for d in dirs:
            if not d.is_dir():
                continue
            for f in os.scandir(d.path):
                try:
                    m = f.stat().st_mtime
                except OSError:
                    continue
                p = Path(f.path)
                if m <= self.start or self.trace_seen.get(p) == m:
                    continue
                self.trace_seen[p] = m
                shot = self._trace_shot(p, m)
                if shot:
                    out.append(shot)
        return sorted(out, key=lambda s: s.time)

    def _trace_shot(self, path: Path, mtime: float) -> Shot | None:
        try:
            with open(path) as f:
                head = f.read(1 << 16)
        except OSError:
            return None
        m = re.search(r'"spec": "([^"]*)", "name": "([^"]*)", "test": "((?:[^"\\]|\\.)*)"', head)
        if not m:
            return None
        box = self._main_box(m.group(1))
        if box is None:
            return None
        failed = not re.search(r'"failures": \[\]', head)
        test = json.loads(f'"{m.group(3)}"')
        return Shot(MAIN.name, m.group(2), box, "result", "fail" if failed else "pass", mtime,
                    FAIL if failed else LIVE, test)

    def _main_box(self, spec_path: str) -> Box | None:
        """Where a spec's build stood in the main plot, if it fits there."""
        try:
            mtime = os.stat(spec_path).st_mtime
            cached = self._box_cache.get(spec_path)
            if cached and cached[0] == mtime:
                return cached[1]
            from .fileformat import load
            build = load(spec_path).build
            box = None
            if build.blocks:
                lo, hi = build.bounds()
                if all(a >= 0 and b < s for a, b, s in zip(lo, hi, MAIN.size)):
                    box = world_box(MAIN.origin, build)
            self._box_cache[spec_path] = (mtime, box)
            return box
        except Exception:
            return None


def event_shot(e: dict) -> Shot | None:
    """A camera shot for an event, if there is something to see on main: a test on the main
    server builds in its plot there; the main plot's result also stands there (mirrored when a
    satellite ran it). Other plots are shown when the showroom places them."""
    plot, server, box = e["plot"], e.get("server"), e.get("box")
    if not box or plot not in PLOTS:
        return None
    box = tuple(box)
    if e["kind"] == "test" and server == "main":
        return Shot(plot, e["spec"], box, "test", "running", e["time"], LIVE, e.get("test", ""))
    if e["kind"] == "result" and (plot == MAIN.name or server == "main"):
        failed = not e.get("passed")
        return Shot(plot, e["spec"], box, "result", "fail" if failed else "pass", e["time"],
                    FAIL if failed else LIVE, e.get("test", ""))
    return None


# ---- choosing shots ------------------------------------------------------------------------

class Scheduler:
    """Holds each shot at least `dwell` seconds, then cuts to the best pending one: highest
    priority, then newest. A shot for what is already on screen updates it without a cut. With
    nothing pending for `tour_dwell` seconds, cycles through recent builds."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.pending: dict[tuple, Shot] = {}
        self.current: Shot | None = None
        self.since = 0.0      # when the current shot was cut to
        self.fresh = 0.0      # when anything last updated it
        self.tour_index = 0

    def offer(self, shot: Shot, now: float) -> None:
        c = self.current
        if c and shot.key == c.key and shot.box == c.box:
            keep = max(c.priority, shot.priority) if shot.kind == c.kind else shot.priority
            self.current = replace(shot, priority=keep)
            self.fresh = now
            return
        old = self.pending.get(shot.key)
        if old and old.priority > shot.priority and old.box == shot.box:
            shot = replace(shot, priority=old.priority)
        self.pending[shot.key] = shot

    def pick(self, now: float, tour: list[Shot]) -> tuple[Shot | None, bool]:
        """The shot to show and whether it is a cut."""
        stale = self.cfg["stale"]
        self.pending = {k: s for k, s in self.pending.items() if now - s.time <= stale}
        held = now - self.since
        dwell = self.cfg["tour_min"] if self.current and self.current.kind == "tour" else self.cfg["dwell"]
        if self.current is None or held >= dwell:
            if self.pending:
                best = max(self.pending.values(), key=lambda s: (s.priority, s.time))
                del self.pending[best.key]
                return self._cut(best, now), True
            idle = now - max(self.since, self.fresh)
            if tour and (self.current is None or idle >= self.cfg["tour_dwell"] and held >= self.cfg["dwell"]):
                choices = [s for s in tour if self.current is None or s.key != self.current.key] or tour
                shot = choices[self.tour_index % len(choices)]
                self.tour_index += 1
                return self._cut(replace(shot, kind="tour", priority=PLAIN), now), True
        return self.current, False

    def _cut(self, shot: Shot, now: float) -> Shot:
        self.current, self.since, self.fresh = shot, now, now
        return shot


# ---- the director --------------------------------------------------------------------------

def caption(shot: Shot, live: str | None) -> dict:
    """The actionbar line: plot, spec, then what is happening."""
    colour = COLOUR.get(shot.status, "gray")
    what = live or shot.detail or shot.status
    if shot.kind == "tour":
        what = shot.detail or shot.status
    return {"text": "", "extra": [{"text": f"{shot.plot} · ", "color": "gray"},
                                  {"text": shot.spec, "color": "white"},
                                  {"text": f"  {what}", "color": colour}]}


CAM = "watch_cam"
CAM_SELECTOR = f"@e[type=item_display,tag={CAM}]"
SNAP_STEP = 0.1  # seconds between the stages of a snap: at least one server tick apart
TICK = 0.05
PACK = "watch"
STORE = "watch:cam"
OBJ = "watch_cam"
# Game ticks the camera function may run past the director's own count of real time. A
# warp that starts before the director sees the freeze plays at most this much of the path;
# a director that stalls longer holds the camera still.
CREDIT = 20
QUEUE_LOW, QUEUE_HIGH = 40, 60  # poses queued: topped up to HIGH when below LOW
EASE_TICKS = 40  # after main ran frozen, the motion speeds back up over this many ticks

# One pose a tick from the queue. `data merge` flips OnGround on alternate ticks, so each
# tick's move differs from the last one sendChanges saw and goes out as an
# EntityPositionSync with exact rotation, not a 1/256-turn byte (ServerEntity.createMovePacket);
# a merge that changes nothing fails without touching the entity. The credit check is how the
# function stays still in a warp: tick functions run while main steps, and `tick query` is
# above their permission level.
TICK_FUNCTION = f"""execute store result score #now {OBJ} run time query gametime
execute unless score #now {OBJ} <= #until {OBJ} run return 0
scoreboard players add #par {OBJ} 1
execute if score #par {OBJ} matches 2.. run scoreboard players set #par {OBJ} 0
execute unless data storage {STORE} q[0] run scoreboard players add #under {OBJ} 1
execute if data storage {STORE} q[0].d0 as {CAM_SELECTOR} run data merge entity @s {{teleport_duration:0}}
execute if data storage {STORE} q[0].x run function {PACK}:move with storage {STORE} q[0]
execute if data storage {STORE} q[0].D run function {PACK}:restore with storage {STORE} q[0]
execute if data storage {STORE} q[0] store result score #done {OBJ} run data get storage {STORE} q[0].n
execute if score #par {OBJ} matches 0 as {CAM_SELECTOR} run data merge entity @s {{OnGround:0b}}
execute if score #par {OBJ} matches 1 as {CAM_SELECTOR} run data merge entity @s {{OnGround:1b}}
data remove storage {STORE} q[0]
"""
PACK_FUNCTIONS = {
    "tick": TICK_FUNCTION,
    "move": f"$execute as {CAM_SELECTOR} run tp @s $(x) $(y) $(z) $(r) $(p)\n",
    "restore": f"$execute as {CAM_SELECTOR} run data merge entity @s {{teleport_duration:$(D)}}\n",
    "load": f"scoreboard objectives add {OBJ} dummy\n",
}


def pack_dir() -> Path:
    return servers.MAIN.dir / servers.MAIN.level_name() / "datapacks"


def install_pack(datapacks: Path) -> bool:
    """Write the camera data pack; whether any file changed."""
    from .build import write_datapack

    root = datapacks / PACK
    files = {root / "data" / PACK / "function" / f"{k}.mcfunction": v for k, v in PACK_FUNCTIONS.items()}
    tags = root / "data" / "minecraft" / "tags" / "function"
    files[tags / "tick.json"] = json.dumps({"values": [f"{PACK}:tick"]})
    files[tags / "load.json"] = json.dumps({"values": [f"{PACK}:load"]})
    try:
        if all(p.read_text() == v for p, v in files.items()):
            return False
    except OSError:
        pass
    write_datapack(datapacks, PACK, PACK_FUNCTIONS)
    tags.mkdir(parents=True, exist_ok=True)
    for p in (tags / "tick.json", tags / "load.json"):
        p.write_text(files[p])
    return True


def cam_ticks(cfg: dict) -> int:
    """teleport_duration of the camera entities while they glide."""
    return max(1, min(59, int(cfg["glide"])))


def _cam_of(player: str, limit: str = ",limit=1") -> str:
    return f"@e[type=item_display,tag={CAM}_{player}{limit}]"


def _number(reply: str) -> int | None:
    m = re.search(r"(-?\d+)", reply)
    return int(m.group(1)) if m else None


def pose_item(pose: tuple, n: int, extra: str = "") -> str:
    x, y, z, yaw, pitch = pose
    return f"{{x:{x:.4f},y:{y:.4f},z:{z:.4f},r:{yaw:.4f},p:{pitch:.4f},n:{n}{extra}}}"


class EntityCamera:
    """Each watcher spectates its own invisible item_display (tags `watch_cam` and
    `watch_cam_<name>`), and all of them move together. A client moves a display entity
    smoothly over its teleport_duration, where a teleported player snaps.

    From the 26.3 source: the client renders from its camera entity at its interpolated
    position and rotation (Camera.alignWithEntity), plus an eye height that eases halfway to
    the entity's each tick (Camera.tick): 1.62 for a player, 0 for a display entity. So the
    camera is attached once and then only these entities move: switching from the player to
    an entity, or between a player view and an entity, shows as a slow drop.

    While main runs normally, the entities are moved by the `watch:tick` function of a data
    pack this class installs on main: it plays one queued pose a tick, so the motion has
    the server's tick clock, not the director's, and every move carries exact rotation (see
    TICK_FUNCTION). The director keeps QUEUE_LOW..QUEUE_HIGH poses queued in storage and
    grants the function game ticks as real time passes (#until). A cut is queued too: a tick
    at teleport_duration 0, a snap, then the glide duration again (a tick's entity data goes
    out after its position).

    The client freezes non-player entities while the server's tick is frozen
    (TickRateManager.isEntityFrozen) and tick functions don't run then, so the camera holds
    still; a cut then goes straight over RCON, whose snap still lands. A spectator is
    attached only if its client has the entity (ClientPacketListener.handleSetCamera ignores
    an unknown id), so a camera is summoned where its player is. The server re-attaches
    nothing by itself: sneaking detaches, and re-sending spectate to an attached player does
    nothing (ServerPlayer.setCamera)."""

    def __init__(self, rcon, cfg: dict, datapacks: Path | None = None):
        self.rcon, self.cfg = rcon, cfg
        self.datapacks = datapacks
        self.pose: tuple | None = None  # eye x y z yaw pitch of the latest queued or snapped pose
        self.cams: set[str] = set()
        self.attach: dict[str, float] = {}  # player -> when to spectate its new camera
        self.snap: list = []  # pending (when, command) stages
        self.next_check = 0.0
        self.installed = False
        self.live = False       # the function drives the camera
        self.clock = None       # (game time, wall time) when main last answered running normally
        self.until = None       # the credit last granted
        self.seq = None         # number of the last pose queued
        self.done = 0           # number of the last pose the function played
        self.marks: list = []   # (number, token) of each queued pose, to resume from
        self.restart = False    # requeue from the first pose not played
        self.cutting = False    # queue a cut next

    def sync(self, watched: list[str], now: float) -> None:
        for p in sorted(self.cams - set(watched)):
            self.rcon.cmd(f"kill {_cam_of(p, '')}")
            self.cams.discard(p)
            self.attach.pop(p, None)
        for p in watched:
            if p not in self.cams:
                self._summon(p, now)

    def _summon(self, player: str, now: float) -> None:
        # At the player, where its client has the chunk; a snap brings it to the shot.
        self.rcon.cmd(f"kill {_cam_of(player, '')}")
        yaw, pitch = (self.pose[3], self.pose[4]) if self.pose else (0.0, 0.0)
        self.rcon.cmd(f"execute at {player} run summon item_display ~ ~ ~ {{Tags:[\"{CAM}\",\"{CAM}_{player}\"],"
                      f"teleport_duration:0,Rotation:[{yaw:.2f}f,{pitch:.2f}f]}}")
        self.cams.add(player)
        self.attach[player] = now + self.cfg["attach_delay"]

    def ticking(self, normal: bool, now: float) -> None:
        """Called a few times a second with whether main runs normally."""
        if normal and not self.installed:
            self._install()
        if normal:
            game = _number(self.rcon.cmd("time query gametime"))
            done = _number(self.rcon.cmd(f"scoreboard players get #done {OBJ}"))
        else:
            game = done = None
        if game is None:
            if self.live:
                self._grant(-1)
                self.live, self.restart = False, True
            self.clock = None
            return
        self.clock = (game, now)
        if done is not None:
            self.done = done
        if self.seq is None:
            self.seq = self.done
        if not self.live:
            self.live, self.restart = True, True
        self.marks = [m for m in self.marks if m[0] > self.done]

    def _install(self) -> None:
        datapacks = self.datapacks or pack_dir()
        if install_pack(datapacks) or f"file/{PACK}" not in self.rcon.cmd("datapack list enabled"):
            self.rcon.cmd("reload")
            if f"file/{PACK}" not in self.rcon.cmd("datapack list enabled"):
                self.rcon.cmd(f'datapack enable "file/{PACK}"')
        self.rcon.cmd(f"scoreboard objectives add {OBJ} dummy")
        self.installed = True

    def _grant(self, until: int) -> None:
        if until != self.until:
            self.rcon.cmd(f"scoreboard players set #until {OBJ} {until}")
            self.until = until

    def cut(self, pose: tuple, now: float, fresh: bool = True) -> None:
        """Jump every camera to `pose`. `fresh`: a new shot, whose motion starts at `pose`;
        otherwise the same shot again from the pose on screen (a new camera attached)."""
        self.pose = pose
        if fresh:
            self.marks = []
        if self.live:
            self.cutting = True
            return
        self.restart = True
        each = f"execute as {CAM_SELECTOR} run data merge entity @s "
        self.rcon.cmd(each + "{teleport_duration:0}")
        self.snap = [(now + SNAP_STEP, lambda: self._tp(self.pose)),
                     (now + 2 * SNAP_STEP, lambda: self.rcon.cmd(each + f"{{teleport_duration:{cam_ticks(self.cfg)}}}"))]

    def _tp(self, pose: tuple) -> None:
        x, y, z, yaw, pitch = pose
        self.rcon.cmd(f"tp {CAM_SELECTOR} {x:.3f} {y:.3f} {z:.3f} {yaw:.2f} {pitch:.2f}")

    def feed(self, now: float, step, rewind) -> None:
        """Keep the queue topped up with `step()` -> (pose, token), one pose per tick of
        motion; `rewind(token, ease)` goes back to where a queued pose was made."""
        if not self.cams:
            self.live = False  # a clock this old must not grant credit to a camera summoned later
        if not self.live or self.snap:
            return
        if self.cutting or self.restart:
            if self.marks:
                rewind(self.marks[0][1], ease=not self.cutting)
            self.marks = []
            items = []
            if self.cutting:
                items.append(f"{{d0:1b,n:{self._next()}}}")
            for i in range(QUEUE_HIGH - len(items)):
                pose, token = step()
                n = self._next()
                self.marks.append((n, token))
                self.pose = pose
                items.append(pose_item(pose, n, f",D:{cam_ticks(self.cfg)}" if self.cutting and i == 1 else ""))
            self._send(items, replace=True)
            self.cutting = self.restart = False
        elif self.seq - self.done < QUEUE_LOW:
            items = []
            while self.seq - self.done < QUEUE_HIGH:
                pose, token = step()
                n = self._next()
                self.marks.append((n, token))
                self.pose = pose
                items.append(pose_item(pose, n))
            self._send(items, replace=False)
        if self.clock:
            game, then = self.clock
            self._grant(game + int((now - then) / TICK) + CREDIT)

    def _next(self) -> int:
        self.seq += 1
        return self.seq

    def _send(self, items: list[str], replace: bool) -> None:
        from scripts.lint import RCON_MAX

        head = [f"data modify storage {STORE} q set value [", f"data modify storage {STORE} in set value ["]
        first = True
        while items:
            prefix = head[0] if replace and first else head[1]
            k = 1
            while k < len(items) and len(prefix) + len(",".join(items[:k + 1])) + 1 <= RCON_MAX:
                k += 1
            self.rcon.cmd(prefix + ",".join(items[:k]) + "]")
            if not (replace and first):
                self.rcon.cmd(f"data modify storage {STORE} q append from storage {STORE} in[]")
            items, first = items[k:], False

    def snapping(self) -> bool:
        return bool(self.snap)

    def keep(self, now: float) -> None:
        while self.snap and now + 1e-6 >= self.snap[0][0]:
            self.snap.pop(0)[1]()
        attached = [p for p, t in self.attach.items() if now + 1e-6 >= t]
        for p in attached:
            del self.attach[p]
            self.rcon.cmd(f"spectate {_cam_of(p)} {p}")
        if attached and self.pose is not None:
            self.cut(self.pose, now, fresh=False)
        if now < self.next_check:
            return
        self.next_check = now + 1
        for p in sorted(self.cams - set(self.attach)):
            if not self.rcon.cmd(f"execute if entity {_cam_of(p)}").startswith("Test passed"):
                self._summon(p, now)  # cleared away with a plot
            else:
                self.rcon.cmd(f"spectate {_cam_of(p)} {p}")

    def remove(self) -> None:
        self.rcon.cmd(f"kill {CAM_SELECTOR}")
        self.rcon.cmd(f"scoreboard players set #until {OBJ} -1")
        self.rcon.cmd(f"data remove storage {STORE} q")
        self.cams.clear()
        self.attach.clear()
        self.snap = []
        self.pose = None
        self.until, self.live, self.marks = -1, False, []


class TpCamera:
    """The fallback: teleport the watchers themselves. Rotation arrives exact, but the client
    snaps to each teleport, so a motion steps rather than glides."""

    def __init__(self, rcon, cfg: dict):
        self.rcon, self.cfg, self.pose = rcon, cfg, None

    def sync(self, watched: list[str], now: float) -> None:
        pass

    def cut(self, pose: tuple, now: float) -> None:
        self.glide(pose)

    def glide(self, pose: tuple) -> None:
        x, y, z, yaw, pitch = pose
        self.pose = pose
        self.rcon.cmd(f"tp @a[tag={TAG}] {x:.3f} {y - EYE:.3f} {z:.3f} {yaw:.2f} {pitch:.2f}")

    def snapping(self) -> bool:
        return False

    def keep(self, now: float) -> None:
        pass

    def remove(self) -> None:
        self.pose = None


def running_normally(reply: str) -> bool:
    """From `tick query`: not frozen, not stepping, and at 20 ticks a second (a warp makes
    the client run its ticks, and so the camera's glide, faster)."""
    if "frozen" in reply or "stepping" in reply.lower():
        return False
    m = re.search(r"Target tick rate: ([\d.]+)", reply)
    return m is None or float(m.group(1)) <= 20.5


class Director:
    """One camera for all watched players. `tick(now)` does whatever is due; the caller
    calls it `rate` times a second."""

    def __init__(self, rcon, sources: Sources, cfg: dict | None = None, state_path: Path = STATE,
                 config_path: Path | None = CONFIG, status_dir: Path = STATUS,
                 showroom: Path = SHOWROOM, fallback: str | None = None, overrides: dict | None = None,
                 datapacks: Path | None = None):
        self.sources = sources
        self.config_path, self.overrides = config_path, overrides or {}
        self.cfg = cfg or load_config(config_path) | self.overrides
        self.state_path, self.status_dir, self.showroom = state_path, status_dir, showroom
        self.fallback = fallback or default_gamemode()
        self.scheduler = Scheduler(self.cfg)
        self.seen: set[str] = set()
        self.watched: list[str] = []
        self.framing: Framing | None = None
        self.shot: Shot | None = None
        self.motion_t = 0.0    # seconds of motion so far in this shot; paused while main is frozen
        self.ease_n = EASE_TICKS  # ticks of motion since the camera function last resumed
        self.datapacks = datapacks
        self.normal = True
        self.last = None
        self.due = {"players": 0.0, "events": 0.0, "config": 0.0, "text": 0.0, "glide": 0.0, "tick": 0.0}
        self.fixed = fixed_obstacles()
        self.camera = None
        self.rcon = rcon
        self.log = None  # a print function for cuts

    @property
    def rcon(self):
        return self._rcon

    @rcon.setter
    def rcon(self, value):
        self._rcon = value
        if self.camera is not None and isinstance(self.camera, self._camera_kind()):
            self.camera.rcon = value
        else:
            self.camera = self._new_camera()

    def _new_camera(self):
        if self._camera_kind() is EntityCamera:
            return EntityCamera(self.rcon, self.cfg, self.datapacks)
        return TpCamera(self.rcon, self.cfg)

    def _camera_kind(self):
        return EntityCamera if self.cfg["camera"] == "entity" else TpCamera

    def motion(self) -> str | None:
        return self.cfg["motion"] if self.cfg["orbit"] else None

    def tick(self, now: float) -> None:
        dt = 0.0 if self.last is None else min(1.0, now - self.last)
        self.last = now
        if now >= self.due["config"] and self.config_path is not None:
            before = (self.cfg["camera"], self.motion())
            self.cfg.update(load_config(self.config_path) | self.overrides)
            if (self.cfg["camera"], self.motion()) != before:
                self.camera.remove()
                self.camera = self._new_camera()
                self.framing = None
            self.due["config"] = now + 2
        if now >= self.due["players"]:
            self.sync_players()
            self.camera.sync(self.watched, now)
            self.due["players"] = now + 1
        if now >= self.due["events"]:
            for shot in self.sources.poll(now):
                self.scheduler.offer(shot, now)
            self.due["events"] = now + 0.5
        if now >= self.due["tick"]:
            normal = running_normally(self.rcon.cmd("tick query"))
            self.normal = normal
            if self.watched and isinstance(self.camera, EntityCamera):
                self.camera.ticking(normal, now)
            self.due["tick"] = now + 0.25
        if not self.watched:
            return
        shot, cut = self.scheduler.pick(now, self.tour())
        if shot is None:
            return
        if cut or self.framing is None or shot.box != self.framing.box or self.camera.pose is None:
            self.framing = frame(shot.box, self.fixed + slot_obstacles(shot.plot, shot.spec, self.showroom),
                                 self.cfg, self.motion())
            self.motion_t, self.ease_n = 0.0, EASE_TICKS
            self.camera.cut(self.pose(), now)
            self.due["glide"] = now + 1 / self.cfg["rate"]
            cut = True
            if self.log:
                f = self.framing
                self.log(f"{time.strftime('%H:%M:%S')} {shot.kind} {shot.plot}/{shot.spec} {shot.status} "
                         f"box {shot.box} el {f.elevation} dist {f.distance:.1f} sway {f.sway:g} "
                         f"dolly {f.dolly:g} -> eye {' '.join(f'{v:.2f}' for v in self.camera.pose)}")
        self.shot = shot
        if isinstance(self.camera, EntityCamera):
            self.camera.feed(now, self.step, self.rewind)
        elif self.motion():
            self.motion_t += dt
            if now + 1e-6 >= self.due["glide"]:
                self.camera.glide(self.pose())
                self.due["glide"] = now + 1 / self.cfg["rate"]
        self.camera.keep(now)
        if cut or now >= self.due["text"]:
            self.text(shot)
            self.due["text"] = now + self.cfg["text_every"]

    def step(self) -> tuple:
        """The pose for the next tick of motion, and a token to rewind to it."""
        token = (self.motion_t, self.ease_n)
        pose = self.pose()
        if self.motion():
            self.motion_t += TICK * min(1.0, self.ease_n / EASE_TICKS)
            self.ease_n += 1
        return pose, token

    def rewind(self, token: tuple, ease: bool) -> None:
        """Back to where `step` made a token; `ease`: speed up from rest again."""
        self.motion_t, self.ease_n = token[0], 0 if ease else token[1]

    def pose(self) -> tuple:
        eye, yaw, pitch = self.framing.pose(phase_at(self.motion_t, self.cfg) if self.motion() else 0.0)
        return (*eye, yaw, pitch)

    def tour(self) -> list[Shot]:
        if self.last is None or self.last >= self.due.get("tour", 0.0):
            self._tour = sorted(showroom_shots(self.showroom), key=lambda s: -s.time)[:self.cfg["tour_size"]]
            self.due["tour"] = (self.last or 0.0) + 2
        shots = list(self._tour)
        if self.sources.last_main:
            shots.insert(0, self.sources.last_main)
        return shots

    def live(self, shot: Shot) -> str | None:
        if shot.kind != "test":
            return None
        got = _read_json(self.status_dir / f"{shot.plot}.json", {})
        if got.get("text") and got.get("time", 0) >= shot.time - 1:
            return got["text"]
        return shot.detail

    def text(self, shot: Shot) -> None:
        self.rcon.cmd(f"title @a[tag={TAG}] actionbar " + json.dumps(caption(shot, self.live(shot))))

    def sync_players(self) -> None:
        reply = self.rcon.cmd("list")
        players = online_from(reply)
        self.seen &= set(players)
        with State(self.state_path) as state:
            watched = reconcile(self.rcon, players, state, self.fallback, self.seen)
        if watched != self.watched and self.log:
            self.log(f"{time.strftime('%H:%M:%S')} watching {', '.join(watched) or 'nobody'} ({reply[:80]!r})")
        self.watched = watched


def _stop(signum, frame):
    raise SystemExit(0)


def run(cfg_overrides: dict | None = None) -> int:
    """The director's main loop, holding the lock for life; returns at once if another
    director holds it. Reconnects when main goes away and gives up after 30 minutes of it.
    Removes its camera entity on the way out."""
    import signal

    from .rcon import Rcon, RconError

    DIR.mkdir(parents=True, exist_ok=True)
    lock = open(LOCK, "a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("director already running")
        return 0
    signal.signal(signal.SIGTERM, _stop)
    PID.write_text(str(os.getpid()))
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} director {os.getpid()} started", flush=True)
    sources = Sources()
    director = None
    down_since = None
    rcon = None
    try:
        while True:
            cfg = load_config() | (cfg_overrides or {})
            if not cfg["enabled"]:
                print("disabled by config; exiting", flush=True)
                return 0
            try:
                rcon = Rcon(port=servers.MAIN.rcon_port, timeout=5)
            except Exception as e:
                rcon = None
                if down_since is None:
                    print(f"{time.strftime('%H:%M:%S')} main not reachable ({e!r}); retrying", flush=True)
                down_since = down_since or time.time()
                if time.time() - down_since > 1800:
                    print("main has been down for 30 minutes; exiting", flush=True)
                    return 0
                time.sleep(5)
                continue
            down_since = None
            if director is None:
                director = Director(rcon, sources, cfg, overrides=cfg_overrides)
                director.log = lambda line: print(line, flush=True)
                director.camera.remove()  # one a crashed director left behind
            director.rcon = rcon
            try:
                while True:
                    began = time.time()
                    director.tick(began)
                    took = time.time() - began
                    if took > 0.5:  # a stall longer than CREDIT ticks holds the orbit still
                        print(f"{time.strftime('%H:%M:%S')} slow director tick {took:.2f} s", flush=True)
                    if not director.cfg["enabled"]:
                        print("disabled by config; exiting", flush=True)
                        return 0
                    time.sleep(max(0.0, 1 / director.cfg["rate"] - (time.time() - began)))
            except (OSError, RconError) as e:
                print(f"{time.strftime('%H:%M:%S')} rcon lost ({e}); reconnecting", flush=True)
                rcon = None
                time.sleep(1)
            except Exception:
                print(traceback.format_exc(), flush=True)
                time.sleep(1)
    finally:
        try:
            if director is not None and rcon is not None:
                director.camera.remove()
                print(f"{time.strftime('%H:%M:%S')} camera removed; director exiting", flush=True)
        except Exception:
            pass
