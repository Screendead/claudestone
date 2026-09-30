import re
import socket
import subprocess
import time
from pathlib import Path

from .build import Build, Pos, write_datapack
from .rcon import Rcon

SERVER_DIR = Path(__file__).resolve().parent.parent / "server"
PACK = "redstone_ai"
# Longest scheduled tick a vanilla component can leave behind (wooden button: 30 ticks).
FLUSH_TICKS = 40
BUTTON_TICKS = {"minecraft:stone_button": 20, "minecraft:polished_blackstone_button": 20}
PLAIN_SUPPORTS = ("stone", "cobblestone", "smooth_stone", "stone_bricks", "white_concrete", "white_wool")
OPPOSITE = {"north": (0, 0, 1), "south": (0, 0, -1), "east": (-1, 0, 0), "west": (1, 0, 0)}


def parse_state(state: str) -> tuple[str, dict[str, str]]:
    block, _, rest = state.partition("[")
    props = dict(kv.split("=") for kv in rest.rstrip("]").split(",") if kv)
    return block, props


def format_state(block: str, props: dict[str, str]) -> str:
    return block + ("[" + ",".join(f"{k}={v}" for k, v in props.items()) + "]" if props else "")


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

    def __init__(self, rcon: Rcon, origin: Pos = (128, -63, 128), size: Pos = (64, 32, 64)):
        self.r = rcon
        self.origin = origin
        self.size = size
        self.build = Build()
        self.pending: list[tuple[int, Pos]] = []
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
        # Only step fast: frozen or not, login and connection timeouts count ticks at this
        # rate, so leaving it high kicks players who are joining.
        self.r.cmd("tick rate 1000")
        self.r.cmd(f"tick step {n}")
        while self.gametime() < target:
            time.sleep(0.002)
        self.r.cmd("tick rate 20")

    def run(self, command: str) -> str:
        out = self.r.cmd(command)
        if "Unknown or incomplete" in out or "Incorrect argument" in out or "<--[HERE]" in out:
            raise CommandFailed(f"{command!r}: {out}")
        return out

    def clear(self) -> None:
        # Fill is capped at 32768 blocks per command, so clear in horizontal slabs.
        (ox, oy, oz), (sx, sy, sz) = self.origin, self.size
        layers = max(1, 32768 // (sx * sz))
        for y in range(oy, oy + sy, layers):
            top = min(y + layers, oy + sy) - 1
            # strict: no neighbour updates, so attached torches and levers don't pop off as items.
            self.run(f"fill {ox} {y} {oz} {ox + sx - 1} {top} {oz + sz - 1} air strict")
        self._advance(FLUSH_TICKS)

    def load(self, build: Build) -> None:
        (lo, hi) = build.bounds()
        for a, b, s in zip(lo, hi, self.size):
            if a < 0 or b >= s:
                raise ValueError(f"build bounds {lo}..{hi} exceed rig size {self.size}")
        self.clear()
        self.build = Build(dict(build.blocks))
        self.pending = []
        write_datapack(self.datapacks, PACK, {"build": build.to_mcfunction()})
        self.run("reload")
        if f"file/{PACK}" not in self.run("datapack list enabled"):
            self.run(f'datapack enable "file/{PACK}"')
        out = self.run(f"execute positioned {self.abs((0, 0, 0))} run function {PACK}:build")
        if not out.startswith("Running function"):
            raise CommandFailed(f"build function: {out}")

    def is_(self, pos: Pos, predicate: str) -> bool:
        out = self.run(f"execute if block {self.abs(pos)} {predicate}")
        return out.startswith("Test passed")

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
