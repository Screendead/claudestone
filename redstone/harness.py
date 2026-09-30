import re
import socket
import subprocess
import time
from pathlib import Path

from .build import Build, Pos, write_datapack
from .rcon import Rcon

SERVER_DIR = Path(__file__).resolve().parent.parent / "server"
PACK = "redstone_ai"
# Covers the longest scheduled tick a component can leave behind and the torch burnout
# memory (RedstoneTorchBlock: 8 toggles within 60 ticks burns a torch out for 160 ticks),
# which is kept per position and would otherwise carry into the next test.
FLUSH_TICKS = 170
BUTTON_TICKS = {"minecraft:stone_button": 20, "minecraft:polished_blackstone_button": 20}
PLAIN_SUPPORTS = ("stone", "cobblestone", "smooth_stone", "stone_bricks", "white_concrete", "white_wool")
OPPOSITE = {"north": (0, 0, 1), "south": (0, 0, -1), "east": (-1, 0, 0), "west": (1, 0, 0)}


def parse_state(state: str) -> tuple[str, dict[str, str]]:
    block, _, rest = state.partition("[")
    props = dict(kv.split("=") for kv in rest.rstrip("]").split(",") if kv)
    return block, props


def format_state(block: str, props: dict[str, str]) -> str:
    return block + ("[" + ",".join(f"{k}={v}" for k, v in props.items()) + "]" if props else "")


def signal_property(state: str) -> str | None:
    """The property that says whether a block is carrying signal, if any."""
    name = parse_state(state)[0].removeprefix("minecraft:")
    if name == "redstone_wire":
        return "power"
    if name in ("redstone_torch", "redstone_wall_torch", "redstone_lamp"):
        return "lit"
    if name in ("repeater", "comparator", "lever", "observer") or name.endswith("_button"):
        return "powered"
    return None


# Minecraft stops a function after 65536 commands (maxCommandChainLength), so probes
# are split into functions of at most this many commands.
PROBE_CHUNK = 60000
WARP_RATE = 10000  # the maximum /tick rate


def probe_functions(build: Build, only: set[Pos] | None = None) -> tuple[list[str], list[Pos]]:
    """Functions that write each probed block's signal level into storage as bN."""
    probed = [p for p in sorted(build.blocks) if signal_property(build.blocks[p]) and (only is None or p in only)]
    lines = []
    for i, (x, y, z) in enumerate(probed):
        block = parse_state(build.blocks[(x, y, z)])[0]
        prop = signal_property(build.blocks[(x, y, z)])
        checks = [(f"power={n}", n) for n in range(1, 16)] if prop == "power" else [(f"{prop}=true", 1)]
        for predicate, value in checks:
            lines.append(f"execute if block ~{x} ~{y} ~{z} {block}[{predicate}] run "
                         f"data modify storage {PACK}:probe s.b{i} set value {value}")
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


def _rcon_up(port=25575) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
        return True
    except OSError:
        return False


def ensure_server(server_dir: Path = SERVER_DIR, timeout=120) -> None:
    if _rcon_up():
        return
    log = open(server_dir / "harness.log", "w")
    subprocess.Popen(
        ["java", "-Xmx2G", "-jar", "server.jar", "nogui"],
        cwd=server_dir, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _rcon_up():
            return
        time.sleep(0.5)
    raise TimeoutError("server did not open RCON")


class CommandFailed(Exception):
    pass


class Rig:
    """Places a build in a tick-frozen world and advances it tick by tick."""

    def __init__(self, rcon: Rcon, origin: Pos = (128, -63, 128), size: Pos = (192, 24, 192)):
        self.r = rcon
        self.origin = origin
        self.size = size
        self.build = Build()
        self.pending: list[tuple[int, Pos]] = []
        self.probed: list[Pos] = []
        self.probe_count = 0
        self.fast_depth = 0
        self.datapacks = SERVER_DIR / self.level_name() / "datapacks"
        self.r.cmd("tick freeze")
        ox, _, oz = origin
        sx, _, sz = size
        self.r.cmd(f"forceload add {ox} {oz} {ox + sx - 1} {oz + sz - 1}")

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
        if n <= 0:
            return
        target = self.gametime() + n
        self.r.cmd(f"tick step {n}")
        while self.gametime() < target:
            time.sleep(0.002)

    def fast(self):
        """Run stepped ticks as fast as the server can compute them for the duration of
        a with-block. Nests: only the outermost block restores the normal rate. Login and
        connection timeouts count ticks at this rate, so it must go back to normal after:
        left high, it kicks players who are joining."""
        rig = self

        class _Fast:
            def __enter__(self):
                if rig.fast_depth == 0:
                    rig.r.cmd(f"tick rate {WARP_RATE}")
                rig.fast_depth += 1

            def __exit__(self, *exc):
                rig.fast_depth -= 1
                if rig.fast_depth == 0:
                    rig.r.cmd("tick rate 20")
        return _Fast()

    def run(self, command: str) -> str:
        out = self.r.cmd(command)
        if "Unknown or incomplete" in out or "Incorrect argument" in out or "<--[HERE]" in out:
            raise CommandFailed(f"{command!r}: {out}")
        return out

    def clear(self) -> None:
        # Fill is capped at 32768 blocks per command, so clear in 32 x 32 columns.
        (ox, oy, oz), (sx, sy, sz) = self.origin, self.size
        for x in range(ox, ox + sx, 32):
            for z in range(oz, oz + sz, 32):
                # strict: no neighbour updates, so attached torches and levers don't
                # pop off as items.
                self.run(f"fill {x} {oy} {z} {min(x + 31, ox + sx - 1)} {oy + sy - 1} "
                         f"{min(z + 31, oz + sz - 1)} air strict")
        with self.fast():
            self._advance(FLUSH_TICKS)

    def load(self, build: Build, probe: set[Pos] | None = None) -> None:
        """Place a build. `probe` limits snapshots to those cells (default: every
        signal-carrying block)."""
        (lo, hi) = build.bounds()
        for a, b, s in zip(lo, hi, self.size):
            if a < 0 or b >= s:
                raise ValueError(f"build bounds {lo}..{hi} exceed rig size {self.size}")
        self.clear()
        self.build = Build(dict(build.blocks))
        self.pending = []
        probes, self.probed = probe_functions(self.build, probe)
        self.probe_count = len(probes)
        write_datapack(self.datapacks, PACK, {"build": build.to_mcfunction(),
                                              **{f"probe{i}": body for i, body in enumerate(probes)}})
        self.run("reload")
        if f"file/{PACK}" not in self.run("datapack list enabled"):
            self.run(f'datapack enable "file/{PACK}"')
        out = self.run(f"execute positioned {self.abs((0, 0, 0))} run function {PACK}:build")
        if not out.startswith("Running function"):
            raise CommandFailed(f"build function: {out}")

    def snapshot(self) -> dict[Pos, int]:
        """Signal level of every probed block: dust power 0-15, otherwise 1 or 0."""
        self.run(f"data modify storage {PACK}:probe s set value {{}}")
        for i in range(self.probe_count):
            self.run(f"execute positioned {self.abs((0, 0, 0))} run function {PACK}:probe{i}")
        out = self.run(f"data get storage {PACK}:probe s")
        found = {int(i): int(v) for i, v in re.findall(r"b(\d+): (\d+)", out)}
        return {pos: found.get(i, 0) for i, pos in enumerate(self.probed)}

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
        block = parse_state(self.build.blocks.get(pos, "minecraft:air"))[0]
        name = block.removeprefix("minecraft:")
        if name == "redstone_wire":
            level = next(p for p in range(16) if self.is_(pos, f"redstone_wire[power={p}]"))
            return f"{name} power={level}"
        prop = signal_property(block)
        if prop:
            on = self.is_(pos, f"{block}[{prop}=true]")
            return f"{name} {prop if on else 'un' + prop}"
        return name

    def dump(self) -> str:
        interesting = [p for p, s in sorted(self.build.blocks.items()) if any(
            k in s for k in ("redstone", "repeater", "comparator", "lever", "button", "lamp", "observer", "piston"))]
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
