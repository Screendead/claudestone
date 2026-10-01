import re
import socket
import subprocess
import time

from .build import Build, Pos, write_datapack
from . import servers
from .plots import MAIN
from .rcon import Rcon
from .servers import Server

SERVER_DIR = servers.MAIN.dir
PACK = "redstone_ai"
# Between `execute positioned <origin>` and a command, so that Rig.command can tell
# whether it succeeded.
RUN_WRAP = f"store success storage {PACK}:probe ok int 1 run "
# Covers the longest scheduled tick a component can leave behind and the torch burnout
# memory (RedstoneTorchBlock: 8 toggles within 60 ticks burns a torch out for 160 ticks),
# which is kept per position and would otherwise carry into the next test.
FLUSH_TICKS = 170
BUTTON_TICKS = {"minecraft:stone_button": 20, "minecraft:polished_blackstone_button": 20}
PLAIN_SUPPORTS = ("stone", "cobblestone", "smooth_stone", "stone_bricks", "white_concrete", "white_wool")
BUILD_TOP = 319  # the overworld's highest block
KILL_MARGIN = 2
OPPOSITE = {"north": (0, 0, 1), "south": (0, 0, -1), "east": (-1, 0, 0), "west": (1, 0, 0)}


def parse_state(state: str) -> tuple[str, dict[str, str]]:
    """Block id and properties; any block-entity NBT after them is dropped."""
    block, _, rest = state.split("{")[0].partition("[")
    props = dict(kv.split("=") for kv in rest.rstrip("]").split(",") if kv)
    return block, props


def format_state(block: str, props: dict[str, str]) -> str:
    return block + ("[" + ",".join(f"{k}={v}" for k, v in props.items()) + "]" if props else "")


BOOL, INVERTED, ANALOG = "bool", "inverted", "analog"
# block -> (property, kind). BOOL reads 1 when the property is true, ANALOG reads its
# 0-15 value. A hopper's `enabled` is the inverse of power, so INVERTED reads 1 when
# it is false, i.e. when the hopper is locked.
SIGNALS = {
    "redstone_wire": ("power", ANALOG),
    **dict.fromkeys(("redstone_torch", "redstone_wall_torch", "redstone_lamp"), ("lit", BOOL)),
    **dict.fromkeys(("repeater", "comparator", "lever", "observer", "powered_rail", "activator_rail",
                     "detector_rail", "note_block", "lectern", "lightning_rod", "tripwire", "tripwire_hook"),
                    ("powered", BOOL)),
    **dict.fromkeys(("piston", "sticky_piston"), ("extended", BOOL)),
    **dict.fromkeys(("dispenser", "dropper", "crafter"), ("triggered", BOOL)),
    **dict.fromkeys(("daylight_detector", "target", "sculk_sensor", "calibrated_sculk_sensor",
                     "light_weighted_pressure_plate", "heavy_weighted_pressure_plate"), ("power", ANALOG)),
    "hopper": ("enabled", INVERTED),
}
SUFFIX_SIGNALS = (("copper_bulb", ("lit", BOOL)), ("_trapdoor", ("open", BOOL)), ("_door", ("open", BOOL)),
                  ("_fence_gate", ("open", BOOL)), ("_button", ("powered", BOOL)),
                  ("_pressure_plate", ("powered", BOOL)))


def signal(state: str) -> tuple[str, str] | None:
    """(property, kind) of the property that says whether a block carries signal, if any."""
    name = parse_state(state)[0].removeprefix("minecraft:")
    if name in SIGNALS:
        return SIGNALS[name]
    return next((v for suffix, v in SUFFIX_SIGNALS if name.endswith(suffix)), None)


def has_level(state: str) -> bool:
    """Whether a `level` step can read an exact 0-15 strength here."""
    sig = signal(state)
    return parse_state(state)[0] == "minecraft:comparator" or (sig is not None and sig[1] == ANALOG)


def _checks(prop: str, kind: str) -> list[tuple[str, int]]:
    if kind == ANALOG:
        return [(f"{prop}={n}", n) for n in range(1, 16)]
    return [(f"{prop}={'false' if kind == INVERTED else 'true'}", 1)]


# Minecraft stops a function after 65536 commands (maxCommandChainLength), so probes
# are split into functions of at most this many commands.
PROBE_CHUNK = 60000
WARP_RATE = 10000  # the maximum /tick rate
# The rate between step batches on main, where players log in: logging in times out after
# 600 ticks at the current rate (30 s here). The first tick of each batch waits out the idle
# tick period (50 ms here), so satellites, which no one joins, stay at WARP_RATE for a test.
IDLE_RATE = 20
# Gamerules library tests change (and restore in `finally`), at their vanilla values.
BASELINE_GAMERULES = {"random_tick_speed": 3, "tnt_explodes": "true"}


def probe_functions(build: Build, only: set[Pos] | None = None) -> tuple[list[str], list[Pos]]:
    """Functions that write each probed block's signal level into storage as bN, and a
    comparator's output strength as cN."""
    probed = [p for p in sorted(build.blocks) if signal(build.blocks[p]) and (only is None or p in only)]
    lines = []
    for i, (x, y, z) in enumerate(probed):
        block = parse_state(build.blocks[(x, y, z)])[0]
        for predicate, value in _checks(*signal(build.blocks[(x, y, z)])):
            lines.append(f"execute if block ~{x} ~{y} ~{z} {block}[{predicate}] run "
                         f"data modify storage {PACK}:probe s.b{i} set value {value}")
        if block == "minecraft:comparator":
            lines.append(f"execute store result storage {PACK}:probe s.c{i} int 1 run "
                         f"data get block ~{x} ~{y} ~{z} OutputSignal")
    chunks = [lines[i:i + PROBE_CHUNK] for i in range(0, len(lines), PROBE_CHUNK)] or [[]]
    return ["\n".join(c) + "\n" for c in chunks], probed


def attached_to(pos: Pos, props: dict[str, str]) -> Pos:
    x, y, z = pos
    face = props.get("face", "wall")
    if face == "floor":
        return (x, y - 1, z)
    if face == "ceiling":
        return (x, y + 1, z)
    dx, dy, dz = OPPOSITE[props["facing"]]
    return (x + dx, y + dy, z + dz)


def _rcon_up(port: int = servers.MAIN.rcon_port) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
        return True
    except OSError:
        return False


def ensure_server(server: Server = servers.MAIN, timeout=180) -> None:
    if _rcon_up(server.rcon_port):
        return
    log = open(server.dir / "harness.log", "w")
    subprocess.Popen(
        ["java", f"-Xmx{server.memory}", "-jar", "server.jar", "nogui"],
        cwd=server.dir, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _rcon_up(server.rcon_port):
            return
        time.sleep(0.5)
    raise TimeoutError(f"{server.name} did not open RCON")


def clear_commands(origin: Pos, size: Pos) -> list[str]:
    """Empty a box without drops and remove the entities in it."""
    (ox, oy, oz), (sx, sy, sz) = origin, size
    # Fill is capped at 32768 blocks per command (max_block_modifications), so clear in
    # 32 x 32 x 32 pieces; strict: no neighbour updates, so attached torches and levers
    # don't pop off as items.
    fills = [f"fill {x} {y} {z} {min(x + 31, ox + sx - 1)} {min(y + 31, oy + sy - 1)} {min(z + 31, oz + sz - 1)} air strict"
             for x in range(ox, ox + sx, 32) for z in range(oz, oz + sz, 32) for y in range(oy, oy + sy, 32)]
    return fills + [kill_command(origin, size)]


def kill_command(origin: Pos, size: Pos) -> str:
    """Remove the entities of a plot, with those that have left it sideways or upwards
    (projectiles, minecarts), but not the plot's own labels and status sign, nor the watch
    director's camera (redstone.watch), which players on main spectate."""
    (ox, oy, oz), (sx, _, sz) = origin, size
    m = KILL_MARGIN
    return (f"kill @e[type=!player,tag=!plot_label,tag=!plot_status,tag=!watch_cam,x={ox - m},y={oy},z={oz - m},"
            f"dx={sx - 1 + 2 * m},dy={BUILD_TOP - oy},dz={sz - 1 + 2 * m}]")


def wait_loaded(rcon: Rcon, origin: Pos, size: Pos, timeout=60) -> None:
    (ox, oy, oz), (sx, _, sz) = origin, size
    corners = [(x, oy, z) for x in (ox, ox + sx - 1) for z in (oz, oz + sz - 1)]
    deadline = time.time() + timeout
    while not all(rcon.cmd(f"execute if loaded {x} {y} {z}").startswith("Test passed") for x, y, z in corners):
        if time.time() > deadline:
            raise TimeoutError(f"area at {origin} did not load")
        time.sleep(0.05)


def mirror(rcon: Rcon, origin: Pos, size: Pos, build: Build) -> None:
    """Place a build in a plot of another server with plain commands: no tick control,
    data pack or reload, so it is safe while that server runs a test elsewhere."""
    (ox, oy, oz), (sx, _, sz) = origin, size
    rcon.cmd(f"forceload add {ox} {oz} {ox + sx - 1} {oz + sz - 1}")
    wait_loaded(rcon, origin, size)
    for command in clear_commands(origin, size) + [f"execute positioned {ox} {oy} {oz} run {c}"
                                                   for c in build.to_commands()]:
        checked(rcon, command)


class CommandFailed(Exception):
    pass


def checked(rcon: Rcon, command: str) -> str:
    out = rcon.cmd(command)
    if ("Unknown or incomplete" in out or "Incorrect argument" in out or "<--[HERE]" in out
            or "not loaded" in out):
        raise CommandFailed(f"{command!r}: {out}")
    return out


class Rig:
    """Places a build in a tick-frozen world and advances it tick by tick."""

    def __init__(self, rcon: Rcon, origin: Pos = MAIN.origin, size: Pos = MAIN.size, plot: str = MAIN.name,
                 server: Server = servers.MAIN, display: Rcon | None = None):
        self.r = rcon
        # Where players watch: the plot status signs live in the main world.
        self.display = display or rcon
        self.server = server
        self.plot = plot
        self.heading: list[dict] = []
        self.owner: str | None = None
        self.origin = origin
        self.size = size
        self.build = Build()
        self.loaded = Build()  # as placed by load(), less its drivers, before any use()
        self.pending: list[tuple[int, Pos]] = []
        self.probed: list[Pos] = []
        self.levels: dict[Pos, int] = {}
        self.probe_count = 0
        self.datapacks = server.dir / server.level_name() / "datapacks"
        ox, _, oz = origin
        sx, _, sz = size
        # A test that died mid-run can leave these changed, and the world saves them.
        self.r.cmd(f"tick rate {IDLE_RATE}")
        self.rate = IDLE_RATE
        self.idle_rate = IDLE_RATE if server == servers.MAIN else WARP_RATE
        for rule, value in BASELINE_GAMERULES.items():
            self.r.cmd(f"gamerule {rule} {value}")
        if server == servers.MAIN:
            self.r.cmd("tick freeze")
            self.r.cmd(f"forceload add {ox} {oz} {ox + sx - 1} {oz + sz - 1}")
        else:
            # A satellite keeps only the plot under test loaded.
            self.r.cmd("forceload remove all")
            self.r.cmd(f"forceload add {ox} {oz} {ox + sx - 1} {oz + sz - 1}")
            wait_loaded(self.r, origin, size)
            self.r.cmd("tick freeze")

    @staticmethod
    def level_name() -> str:
        props = (SERVER_DIR / "server.properties").read_text()
        return re.search(r"^level-name=(.*)$", props, re.M).group(1)

    def abs(self, pos: Pos) -> str:
        return " ".join(str(o + p) for o, p in zip(self.origin, pos))

    def gametime(self) -> int:
        return int(re.search(r"(\d+)", self.r.cmd("time query gametime")).group(1))

    def step(self, n: int = 1) -> None:
        target = self.gametime() + n
        # A real button release fires in the scheduled-tick phase of its tick; applying it
        # between ticks instead moves it just before that tick starts.
        for due, pos in sorted(self.pending):
            if due <= target:
                self._advance(due - 1 - self.gametime())
                self._set_powered(pos, False)
                self.pending.remove((due, pos))
        self._advance(target - self.gametime())

    def _advance(self, n: int) -> None:
        """Step n ticks as fast as the server can compute them. On main the login timeout
        counts ticks at the current rate, so the rate is raised only for the batch: left
        high between steps, it kicks joining players."""
        if n <= 0:
            return
        target = self.gametime() + n
        self._rate(WARP_RATE)
        try:
            self.r.cmd(f"tick step {n}")
            while self.gametime() < target:
                time.sleep(0.002)
        finally:
            self._rate(self.idle_rate)

    def _rate(self, rate: int) -> None:
        if self.rate != rate:
            # Set first: if the command fails, the next call sends it again.
            self.rate = None
            self.r.cmd(f"tick rate {rate}")
            self.rate = rate

    def release(self) -> None:
        """Let the world run again at the normal rate, for anyone watching; an unfrozen
        satellite left at WARP_RATE would spin a core."""
        self._rate(IDLE_RATE)
        self.r.cmd("tick unfreeze")

    def run(self, command: str) -> str:
        return checked(self.r, command)

    def command(self, command: str) -> tuple[bool, str]:
        """Run a command with `~` at the build origin: whether it succeeded, and the
        server's reply. A failed command still replies, often with its reason."""
        with self.r.sequence():
            reply = self.run(f"execute positioned {self.abs((0, 0, 0))} {RUN_WRAP}{command}")
            return int(re.findall(r"(-?\d+)", self.run(f"data get storage {PACK}:probe ok"))[-1]) == 1, reply

    def clear(self) -> None:
        for command in clear_commands(self.origin, self.size):
            self.run(command)
        self._advance(FLUSH_TICKS)
        # A chunk's entities load after its blocks, so the first kill can miss them.
        self.run(kill_command(self.origin, self.size))

    def load(self, build: Build, probe: set[Pos] | None = None, drivers: set[Pos] = frozenset(),
             update: str = "all", functions: dict[str, str] | None = None,
             tags: dict[str, str] | None = None) -> None:
        """Place a build. `probe` limits snapshots to those cells (default: every
        signal-carrying block). `drivers` are input cells the build places a redstone
        block in; drive() may move them later. `update` is the spec's update pass
        (Build.to_commands). `functions` and `tags` go into the data pack beside the build
        and probe functions, for call()."""
        (lo, hi) = build.bounds()
        for a, b, s in zip(lo, hi, self.size):
            if a < 0 or b >= s:
                raise ValueError(f"build bounds {lo}..{hi} exceed rig size {self.size}")
        wait_loaded(self.r, self.origin, self.size)
        self.clear()
        design = {p: b for p, b in build.blocks.items() if p not in drivers}
        self.loaded = Build(design, list(build.entities))
        self.build = Build(dict(design))
        self.pending = []
        probes, self.probed = probe_functions(self.build, probe)
        self.probe_count = len(probes)
        parts = build.to_functions(PROBE_CHUNK, update)
        root = write_datapack(self.datapacks, PACK, {**{f"build{i}": body for i, body in enumerate(parts)},
                                                     **{f"probe{i}": body for i, body in enumerate(probes)},
                                                     **(functions or {})}, tags)
        if hasattr(self.server, "push_datapack"):
            # A Docker satellite's world is in its container; this folder is only staging.
            self.server.push_datapack(root, reload=False)
        self.run("reload")
        if f"file/{PACK}" not in self.run("datapack list enabled"):
            self.run(f'datapack enable "file/{PACK}"')
        # In order, every setblock before any clone; each part is its own command chain.
        for i in range(len(parts)):
            out = self.run(f"execute positioned {self.abs((0, 0, 0))} run function {PACK}:build{i}")
            if not out.startswith("Running function"):
                raise CommandFailed(f"build function {i + 1}/{len(parts)}: {out}")

    def call(self, functions: list[str], read: str | None = None) -> str:
        """Run data pack functions at the build origin, then `data get storage <read>` if
        given, with no other client's command in between; that reply, or ""."""
        with self.r.sequence():
            for f in functions:
                out = self.run(f"execute positioned {self.abs((0, 0, 0))} run function {PACK}:{f}")
                if not out.startswith("Running function"):
                    raise CommandFailed(f"function {f}: {out}")
            return self.run(f"data get storage {read}") if read else ""

    def snapshot(self) -> dict[Pos, int]:
        """Signal level of every probed block: analog power 0-15, otherwise 1 or 0. Sets
        `levels` to the output strength of each probed comparator."""
        with self.r.sequence():
            self.run(f"data modify storage {PACK}:probe s set value {{}}")
            for i in range(self.probe_count):
                self.run(f"execute positioned {self.abs((0, 0, 0))} run function {PACK}:probe{i}")
            out = self.run(f"data get storage {PACK}:probe s")
        found = {int(i): int(v) for i, v in re.findall(r"\bb(\d+): (\d+)", out)}
        self.levels = {self.probed[int(i)]: int(v) for i, v in re.findall(r"\bc(\d+): (\d+)", out)}
        return {pos: found.get(i, 0) for i, pos in enumerate(self.probed)}

    def level(self, pos: Pos) -> int:
        """Exact 0-15 strength: a comparator's output, or an analog block's power."""
        state = self.build.blocks.get(pos, "")
        if not has_level(state):
            raise ValueError(f"{pos} ({state or 'air'}) has no signal strength to read")
        block = parse_state(state)[0]
        if block == "minecraft:comparator":
            with self.r.sequence():
                self.run(f"execute store result storage {PACK}:probe l int 1 run data get block {self.abs(pos)} OutputSignal")
                return int(re.findall(r"(-?\d+)", self.run(f"data get storage {PACK}:probe l"))[-1])
        prop = signal(state)[0]
        return next((n for n in range(16) if self.is_(pos, f"{block}[{prop}={n}]")), 0)

    def is_(self, pos: Pos, predicate: str) -> bool:
        out = self.run(f"execute if block {self.abs(pos)} {predicate}")
        return out.startswith("Test passed")

    def drive(self, pos: Pos, on: bool) -> None:
        """Place or remove a redstone block. Unlike a lever, a redstone block powers its
        neighbours directly, so setblock's update of those neighbours is the whole effect."""
        if any(p < 0 or p >= s for p, s in zip(pos, self.size)):
            raise ValueError(f"driver {pos} outside rig")
        if pos in self.build.blocks:
            raise ValueError(f"driver {pos} overlaps the build")
        self.run(f"setblock {self.abs(pos)} {'redstone_block' if on else 'air'}")

    def powered(self, pos: Pos) -> bool:
        if not self.is_(pos, "redstone_wire"):
            raise ValueError(f"{pos} is not redstone dust")
        return not self.is_(pos, "redstone_wire[power=0]")

    def describe(self, pos: Pos) -> str:
        """The live value of whatever property carries signal at pos, for failure reports."""
        state = self.build.blocks.get(pos, "minecraft:air")
        block = parse_state(state)[0]
        name = block.removeprefix("minecraft:")
        sig = signal(state)
        if not sig:
            return name
        prop, kind = sig
        if kind == ANALOG:
            return f"{name} {prop}={self.level(pos)}"
        live = "true" if self.is_(pos, f"{block}[{prop}=true]") else "false"
        return f"{name} {prop}={live}" + (" (locked)" if kind == INVERTED and live == "false" else "")

    def dump(self) -> str:
        interesting = [p for p, s in sorted(self.build.blocks.items()) if signal(s) or "redstone_block" in s]
        return "\n".join(f"  {p}: {self.describe(p)}" for p in interesting)

    def use(self, pos: Pos) -> None:
        """Flip a lever or press a button the way a player's click does.

        A plain setblock only updates the lever's own neighbours; LeverBlock.pull also
        updates the neighbours of the block it is attached to. Cloning that block onto
        itself supplies the missing update.
        """
        state = self.build.blocks[pos]
        block, props = parse_state(state)
        if block != "minecraft:lever" and not block.endswith("_button"):
            raise ValueError(f"{pos} is {state}, not a lever or button")
        powered = props.get("powered") == "true"
        if block.endswith("_button"):
            if powered:
                return  # a pressed button ignores clicks
            release = BUTTON_TICKS.get(block, 30)
            self.pending.append((self.gametime() + release, pos))
        self._set_powered(pos, not powered)

    def _set_powered(self, pos: Pos, on: bool) -> None:
        block, props = parse_state(self.build.blocks[pos])
        props["powered"] = "true" if on else "false"
        state = format_state(block, props)
        self.build.blocks[pos] = state
        attached = attached_to(pos, props)
        support = self.build.blocks.get(attached, "")
        if parse_state(support)[0].removeprefix("minecraft:") not in PLAIN_SUPPORTS:
            raise ValueError(f"{pos} is attached to {support or 'nothing'}; only plain full blocks are emulated faithfully")
        self.run(f"setblock {self.abs(pos)} {state}")
        a = self.abs(attached)
        self.run(f"clone {a} {a} {a} replace force")
