"""Offline check for builds that are certainly broken: block states and entity types the
game does not have (from redstone/blocks.json; regenerate it with scripts.blockdata after a
server upgrade), blocks that pop off for lack of support, commands too long for RCON, and
cells or test references the harness cannot use. No style advice.

    python -m scripts.lint <spec name | path>...     (no arguments: the whole library)
"""

import json
import re
import sys
from pathlib import Path

from redstone import door, fileformat, library, spec as spec_module
from redstone.build import UPDATE_PASSES
from redstone.fileformat import Spec
from redstone.harness import PLAIN_SUPPORTS, RUN_WRAP, has_level, parse_state, signal
from redstone.plots import MAIN, plot_for
from scripts.blockdata import OUT as BLOCKDATA

KNOWN = json.loads(BLOCKDATA.read_text())
# Vanilla RCON drops a longer request packet without replying.
RCON_MAX = 1400

# y=0 needs no block below: the harness plots stand on the world's ground.
NEEDS_FLOOR = {"redstone_wire", "repeater", "comparator", "redstone_torch", "rail", "powered_rail",
               "detector_rail", "activator_rail"}
FLOOR_SUFFIXES = ("_pressure_plate", "_carpet")
BEHIND = {"north": (0, 0, 1), "south": (0, 0, -1), "east": (-1, 0, 0), "west": (1, 0, 0)}
WALL_ONLY = {"redstone_wall_torch", "wall_torch", "soul_wall_torch", "copper_wall_torch", "ladder", "tripwire_hook"}


def _support(pos, name, props):
    """Where a block hangs, or None if it is free-standing."""
    x, y, z = pos
    if name in WALL_ONLY or name == "lever" or name.endswith("_button"):
        face = props.get("face", "wall") if name == "lever" or name.endswith("_button") else "wall"
        if face == "floor":
            return x, y - 1, z
        if face == "ceiling":
            return x, y + 1, z
        dx, dy, dz = BEHIND[props.get("facing", "north")]
        return x + dx, y + dy, z + dz
    return None


def _state_problems(state: str) -> list[str]:
    block, props = parse_state(state)
    name = block.removeprefix("minecraft:")
    known = KNOWN["blocks"].get(name)
    if known is None:
        return [f"unknown block {name!r} in {state}"]
    out = []
    for k, v in props.items():
        if k not in known:
            out.append(f"{name} has no property {k!r} ({', '.join(known) or 'none'}) in {state}")
        elif v not in known[k]:
            out.append(f"{name} {k}={v} is not one of {', '.join(known[k])} in {state}")
    return out


def lint(spec: Spec) -> list[str]:
    bad, blocks = [], spec.build.blocks
    for state in sorted(set(blocks.values())):
        bad += _state_problems(state)
    for entity in sorted({e for _, e, _ in spec.build.entities}):
        if entity.removeprefix("minecraft:") not in KNOWN["entities"]:
            bad.append(f"unknown entity type {entity!r}")
    for kind, cells in (("input", spec.inputs), ("output", spec.outputs), ("name", spec.named)):
        bad += [f"{kind} {n!r} is a {type(n).__name__}, not a name; quote it in the YAML"
                for n in cells if not isinstance(n, str)]
    for pos, state in sorted(blocks.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        block, props = parse_state(state)
        name = block.removeprefix("minecraft:")
        if (name in NEEDS_FLOOR or name.endswith(FLOOR_SUFFIXES)) and pos[1] > 0 and (pos[0], pos[1] - 1, pos[2]) not in blocks:
            bad.append(f"{name} at {pos} has nothing below")
        held = _support(pos, name, props)
        if held and held[1] >= 0 and held not in blocks:
            bad.append(f"{name} at {pos} hangs on {held}, which is air")
    plot = (plot_for(spec.path) if spec.path else None) or MAIN
    bad += _placement_problems(spec, plot)
    if spec.update_pass not in UPDATE_PASSES:
        bad.append(f"update_pass {spec.update_pass!r} is not one of {', '.join(UPDATE_PASSES)}")
    if spec.door is not None:
        bad += [f"door: {m}" for m in door.problems(spec, plot.size)]
    for n, pos in spec.named.items():
        if pos not in blocks:
            bad.append(f"cell {n} at {pos} is air")
    for t in spec.tests:
        bad += [f"test {t['name']!r}: {m}" for m in _test_problems(spec, t, plot)]
    return bad


def _placement_problems(spec, plot):
    bad, blocks = [], spec.build.blocks
    lo, hi = spec.build.bounds() if blocks else ((0, 0, 0), (-1, -1, -1))
    for a, b, s in zip(lo, hi, plot.size):
        if a < 0 or b >= s:
            bad.append(f"build bounds {lo}..{hi} exceed the {plot.size} {plot.name} plot")
            break
    for n in spec.inputs:
        for pos in spec.input_cells(n):
            if pos in blocks:
                bad.append(f"input {n} at {pos} is inside the build ({blocks[pos]}); the driver cell must be air")
            if any(p < 0 or p >= s for p, s in zip(pos, plot.size)):
                bad.append(f"input {n} at {pos} is outside the rig")
    for pos in sorted(spec.reserved & blocks.keys()):
        bad.append(f"reserved cell {pos} holds {blocks[pos]}")
    return bad


def _readable(spec, name):
    if name not in spec.named:
        return f"unknown cell {name!r}"
    if not signal(spec.build.blocks.get(spec.named[name], "")):
        return f"cell {name!r} ({spec.build.blocks.get(spec.named[name], 'air')}) carries no signal the harness can read"


def _test_problems(spec, test, plot):
    out = []
    at = "execute positioned " + " ".join(map(str, plot.origin))
    if "truth_table" in test:
        try:
            ins, outs, _ = fileformat.parse_truth_table(test["truth_table"])
        except Exception as e:
            return [f"truth_table does not parse: {e}"]
        out += [f"unknown input {n!r}" for n in ins if n not in spec.inputs]
        out += filter(None, (_readable(spec, n) for n in outs))
        out += _table_option_problems(test, outs)
    else:
        out += [f"{k} needs a truth_table" for k in TABLE_OPTIONS if k in test]
    initial = test.get("initial", {})
    if not isinstance(initial, dict):
        out.append(f"initial {initial!r} is not a map of input to 1 or 0")
    else:
        out += [f"initial: unknown input {n!r}" for n in initial if n not in spec.inputs]
        out += [f"initial {n!r}: {v!r} is not 1 or 0" for n, v in initial.items() if v not in (0, 1)]
    if "tile" in test:
        out += _tile_problems(spec, test["tile"], plot)
    if "door_cycle" in test:
        out += door.cycle_problems(spec, test["door_cycle"])
        out += ["door_cycle and tile can't be combined"] if "tile" in test else []
    out += _step_problems(spec, test.get("steps", []), at)
    for command in test.get("finally", []):
        out += _command_problems("finally", command, at)
    restored = {m.group(1) for c in test.get("finally", []) if isinstance(c, str) for m in GAMERULE_SET.finditer(c)}
    out += [f"run changes gamerule {r} but finally does not restore it (a failed or killed test leaves it, "
            "and the world saves it)" for r in sorted(_gamerules(test.get("steps", [])) - restored)]
    return out


GAMERULE_SET = re.compile(r"\bgamerule\s+(?:minecraft:)?(\w+)\s+\S")


def _gamerules(steps) -> set[str]:
    """Gamerules the `run`/`log` steps set, repeat bodies included."""
    rules = set()
    for step in steps:
        if not isinstance(step, dict) or len(step) != 1:
            continue
        (kind, arg), = step.items()
        if kind in ("run", "log") and isinstance(arg, str):
            rules |= {m.group(1) for m in GAMERULE_SET.finditer(arg)}
        elif kind == "repeat" and isinstance(arg, dict) and isinstance(arg.get("steps"), list):
            rules |= _gamerules(arg["steps"])
    return rules


TABLE_OPTIONS = ("delays", "max_delays", "glitch_free", "reset", "tile")


def _tile_problems(spec, tile, plot):
    if (not isinstance(tile, list) or len(tile) != 3 or not any(tile)
            or not all(isinstance(v, int) and not isinstance(v, bool) for v in tile)):
        return [f"tile {tile!r} is not a nonzero offset [dx, dy, dz]"]
    try:
        both = spec_module.tiled(spec, tuple(tile))
    except ValueError as e:
        return [f"tile {tile}: the copies {e}"]
    return [f"tile {tile}: {m}" for m in _placement_problems(both, plot)]


def _ticks(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _table_option_problems(test, outs):
    out = [f"{k} {test[k]!r} is not true or false" for k in ("glitch_free", "reset")
           if k in test and not isinstance(test[k], bool)]
    for key in ("delays", "max_delays"):
        if key not in test:
            continue
        if not isinstance(test[key], dict):
            out.append(f"{key} {test[key]!r} is not a map of output to ticks or {{rise: N, fall: N}}")
            continue
        for n, v in test[key].items():
            if n not in outs:
                out.append(f"{key} {n!r} is not an output column of the truth table")
            elif isinstance(v, dict):
                out += [f"{key} {n!r}: {e!r} must be rise or fall" for e in v if e not in ("rise", "fall")]
                out += [f"{key} {n!r} {e}: {w!r} is not a number of ticks" for e, w in v.items() if not _ticks(w)]
                if not v:
                    out.append(f"{key} {n!r} is empty")
            elif not _ticks(v):
                out.append(f"{key} {n!r}: {v!r} is not a number of ticks")
    return out


def _command_problems(kind, command, at):
    if not isinstance(command, str):
        return [f"{kind} {command!r} is not a command"]
    prefix = {"check": "", "run": RUN_WRAP, "log": RUN_WRAP, "finally": RUN_WRAP}[kind]
    n = len(f"{at} {prefix}{command}".encode())
    if n > RCON_MAX:
        return [f"{kind} command is {n} bytes; RCON drops requests over {RCON_MAX}: {command[:60]}..."]
    return []


def _step_problems(spec, steps, at):
    out = []
    for step in steps:
        if not isinstance(step, dict) or len(step) != 1:
            out.append(f"step {step!r} is not one kind: argument")
            continue
        (kind, arg), = step.items()
        if kind == "drive":
            out += [f"unknown input {n!r}" for n in arg if n not in spec.inputs]
        elif kind == "expect":
            out += filter(None, (_readable(spec, n) for n in arg))
        elif kind == "level":
            for n, v in arg.items():
                if n not in spec.named:
                    out.append(f"unknown cell {n!r}")
                elif not has_level(spec.build.blocks.get(spec.named[n], "")):
                    out.append(f"level {n!r}: {spec.build.blocks.get(spec.named[n], 'air')} has no signal strength "
                               "to read (dust, comparators and analog-power blocks do)")
                elif not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 15:
                    out.append(f"level {n!r}: {v!r} is not a strength 0-15")
        elif kind == "wave":
            if not isinstance(arg, dict) or not arg:
                out.append(f"wave {arg!r} is not a map of cell to string")
                continue
            for n, w in arg.items():
                if not isinstance(w, str):
                    out.append(f"wave {n!r}: {w!r} is a {type(w).__name__}; quote it in the YAML")
                elif not w or set(w) - set("01x"):
                    out.append(f"wave {n!r}: {w!r} must be one or more of 0, 1 and x")
                out += filter(None, [_readable(spec, n)])
        elif kind == "repeat":
            times, inner = (arg.get("times"), arg.get("steps")) if isinstance(arg, dict) else (None, None)
            if not isinstance(times, int) or isinstance(times, bool) or times < 1 or not isinstance(inner, list):
                out.append(f"repeat needs {{times: <positive int>, steps: [...]}}, not {arg!r}")
                continue
            out += _step_problems(spec, inner, at)
        elif kind == "use":
            if arg not in spec.named:
                out.append(f"unknown cell {arg!r}")
                continue
            block, props = parse_state(spec.build.blocks[spec.named[arg]])
            if block != "minecraft:lever" and not block.endswith("_button"):
                out.append(f"use {arg!r}: {block} is not a lever or button")
                continue
            held = _support(spec.named[arg], block.removeprefix("minecraft:"), props)
            below = spec.build.blocks.get(held, "")
            if parse_state(below)[0].removeprefix("minecraft:") not in PLAIN_SUPPORTS:
                out.append(f"use {arg!r}: attached to {below or 'air'}; the harness only emulates plain full blocks")
        elif kind in ("insert", "expect_items", "throughput"):
            out += [f"{kind}: {m}" for m in _item_problems(spec, kind, arg, at)]
        elif kind in ("run", "log", "check"):
            out += _command_problems(kind, arg, at)
        elif kind == "wait":
            if not isinstance(arg, int) or isinstance(arg, bool) or arg < 0:
                out.append(f"wait {arg!r} is not a number of ticks")
        else:
            out.append(f"unknown step {kind!r}")
    return out


# Blocks whose block entity keeps an `Items` list, which the item steps read and write.
CONTAINERS = {"chest", "trapped_chest", "barrel", "hopper", "dropper", "dispenser", "crafter", "furnace",
              "blast_furnace", "smoker", "brewing_stand", "chiseled_bookshelf", "campfire", "soul_campfire"}
CONTAINER_SUFFIXES = ("copper_chest", "shulker_box", "_shelf")
ITEM_KEYS = {"insert": {"cell", "items", "item", "count", "slot", "clear"},
             "expect_items": {"cell", "item", "slot", "count", "min", "max", "empty"},
             "throughput": {"from", "to", "item", "ticks", "min", "max"}}


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _count(v, least=0):
    return _int(v) and v >= least


def _container_problems(spec, where):
    if isinstance(where, str):
        if where not in spec.named:
            return [f"unknown cell {where!r}"]
        pos = spec.named[where]
    elif isinstance(where, list) and len(where) == 3 and all(map(_int, where)):
        pos = tuple(where)
    else:
        return [f"{where!r} is not a cell name or [x, y, z]"]
    # A position that is air in the build may get its container from a `run` step.
    name = parse_state(spec.build.blocks.get(pos, "air"))[0].removeprefix("minecraft:")
    if name != "air" and name not in CONTAINERS and not name.endswith(CONTAINER_SUFFIXES):
        return [f"{where!r} is {name}, which holds no Items"]
    return []


def _item_problems(spec, kind, arg, at):
    if not isinstance(arg, dict):
        return [f"{arg!r} is not a map"]
    out = [f"unknown key {k!r}" for k in arg if k not in ITEM_KEYS[kind]]
    for k in ("cell",) if kind != "throughput" else [k for k in ("from", "to") if k in arg]:
        if k not in arg:
            return out + [f"needs {k}"]
        out += _container_problems(spec, arg[k])
    if "item" in arg and not isinstance(arg["item"], str):
        out.append(f"item {arg['item']!r} is not an item id")
    out += [f"{k} {arg[k]!r} is not a count" for k in ("count", "min", "max", "slot") if k in arg and not _count(arg[k])]
    if kind == "insert":
        items = arg.get("items", [])
        if not isinstance(items, list) or not all(isinstance(i, dict) and isinstance(i.get("id"), str)
                                                  and _count(i.get("count", 1), 1) and set(i) <= {"id", "count"}
                                                  for i in items):
            return out + [f"items {items!r} is not a list of {{id, count}}"]
        if "items" in arg and ("item" in arg or "count" in arg):
            out.append("give items, or item and count, not both")
        if not ("items" in arg or "item" in arg or arg.get("clear")):
            out.append("needs items, item or clear: true")
        if not out:
            out += [m for c in spec_module.insert_commands(spec, arg) for m in _command_problems("run", c, at)]
    elif kind == "expect_items":
        if not any(k in arg for k in ("count", "min", "max", "empty")):
            out.append("needs count, min, max or empty: true")
        if "empty" in arg and (arg["empty"] is not True or {"count", "min", "max"} & set(arg)):
            out.append("empty is true, alone, or left out")
    else:
        if not ("from" in arg or "to" in arg):
            out.append("needs from or to")
        if not _count(arg.get("ticks"), 1):
            out.append(f"ticks {arg.get('ticks')!r} is not a positive number of ticks")
    return out


def _load(arg: str) -> Spec:
    return fileformat.load(arg if Path(arg).is_file() else library.path_of(arg))


def main(args: list[str]) -> int:
    targets = args or [str(p) for p in library.paths()]
    problems = 0
    for arg in targets:
        try:
            found = lint(_load(arg))
        except Exception as e:
            found = [f"does not load: {e}"]
        for m in found:
            print(f"{Path(arg).name.removesuffix(library.SUFFIX)}: {m}")
        problems += len(found)
    if not problems:
        print("lint ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
