"""Every variant tested in a building-block plot stands side by side in that plot on main,
each under a floating label with its name, size, delay and traits.

State per plot is server/showroom/<plot>.json: {"specs": {name: entry}}, where an entry
holds its slot (x, z inside the plot), size (w, h, d of the build bounds), box (the w, d
reserved on the floor: the build, widened to fit its label's name), per-test results,
traits, the time it was last tested and, if that test had one ($REDSTONE_OWNER), its owner.
Callers hold server/plots/<plot>.lock.
"""

import hashlib
import json
import math
import time
import traceback

from . import fileformat, library
from .build import Build
from .harness import checked, clear_commands, wait_loaded
from .plots import PLOTS, REFERENCES
from .rcon import Rcon
from .servers import ROOT

STATE = ROOT / "showroom"
LOG = ROOT / "showroom.log"
GAP = 2
# Rows further apart, so a label is not straight behind the one on the row in front.
GAP_Z = 4
SCALE = 1.25
PX = 0.025  # blocks per text pixel at scale 1
TAG = "showroom"
# RCON drops a request over about 1446 bytes; a data pack function (how tests load builds)
# has no such limit, so a container full of items fits a test but not a showroom slot.
RCON_MAX = 1400


def _log(msg: str) -> None:
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def load_state(plot: str) -> dict:
    path = STATE / f"{plot}.json"
    return json.loads(path.read_text()) if path.exists() else {"specs": {}}


def save_state(plot: str, state: dict) -> None:
    STATE.mkdir(exist_ok=True)
    tmp = STATE / f".{plot}.json.tmp"
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True))
    tmp.replace(STATE / f"{plot}.json")


def normalised(build: Build) -> Build:
    """The build moved so its x and z bounds start at 0; y is kept as tested."""
    (lx, _, lz), _ = build.bounds()
    return build.shifted((-lx, 0, -lz))


def size_of(build: Build) -> list[int]:
    (lx, _, lz), (hx, hy, hz) = build.bounds()
    return [hx - lx + 1, hy + 1, hz - lz + 1]


def box_of(name: str, size: list[int], plot_size) -> list[int]:
    name_blocks = (7 * len(name) + 2) * PX * SCALE  # bold glyphs are about 7 px wide
    return [min(max(size[0], math.ceil(name_blocks)), plot_size[0]), size[2]]


def _overlaps(a, b) -> bool:
    (ax, az, aw, ad), (bx, bz, bw, bd) = a, b
    return ax < bx + bw + GAP and bx < ax + aw + GAP and az < bz + bd + GAP_Z and bz < az + ad + GAP_Z


def _fits(slot, box, others, plot_size) -> bool:
    x, z = slot
    if x < 0 or z < 0 or x + box[0] > plot_size[0] or z + box[1] > plot_size[2]:
        return False
    return not any(_overlaps((x, z, *box), o) for o in others)


def find_slot(box, others, plot_size) -> list[int] | None:
    """First free position scanning rows north to south, each west to east."""
    for z in range(plot_size[2] - box[1] + 1):
        for x in range(plot_size[0] - box[0] + 1):
            if _fits((x, z), box, others, plot_size):
                return [x, z]
    return None


def _rects(specs: dict, skip: str | None = None) -> list:
    return [(*e["slot"], *e["box"]) for n, e in specs.items() if n != skip and e.get("slot")]


def status(entry: dict, test_names: list[str] | None) -> str:
    results = entry.get("results", {})
    names = test_names if test_names is not None else list(results)
    if any(results.get(t, {}).get("result") == "fail" for t in names):
        return "fail"
    if names and all(results.get(t, {}).get("result") == "pass" for t in names):
        return "pass"
    return "untested"


def _misplaced(plot: str, name: str) -> bool:
    """Reference rebuilds stand only in the references plot, and nothing else does."""
    return name.startswith("ref_") != (plot == REFERENCES.name)


def title(plot: str, name: str, path=None) -> str:
    """The name a slot's label shows: in the references plot, prefixed by the spec's
    building block (its library folder)."""
    if plot != REFERENCES.name:
        return name
    try:
        return f"{(path or library.path_of(name)).parent.name}: {name}"
    except LookupError:
        return name


def label_text(name: str, entry: dict, test_names: list[str] | None) -> dict:
    colour = {"pass": "green", "fail": "red", "untested": "yellow"}[status(entry, test_names)]
    w, h, d = entry["size"]
    delays = [r["delay"] for t, r in entry.get("results", {}).items()
              if r.get("delay") is not None and (test_names is None or t in test_names)]
    line = f"{w}x{h}x{d}" + (f" · {max(delays)} ticks" if delays else "")
    extra = [{"text": name, "bold": True, "color": colour}, {"text": "\n" + line, "color": "#DDDDDD"}]
    if entry.get("traits"):
        extra.append({"text": "\n" + ", ".join(entry["traits"]), "color": "#DDDDDD"})
    return {"text": "", "extra": extra}


def _abs(plot, slot, y=0):
    (ox, oy, oz) = PLOTS[plot].origin
    return ox + slot[0], oy + y, oz + slot[1]


def _clear_box(rcon: Rcon, plot: str, name: str, entry: dict) -> None:
    rcon.cmd(f"kill @e[type=text_display,tag={TAG},tag=sr_{name}]")
    if entry.get("slot"):
        (x, y, z), sy = _abs(plot, entry["slot"]), PLOTS[plot].size[1]
        for c in clear_commands((x, y, z), (entry["box"][0], sy, entry["box"][1])):
            checked(rcon, c)


def _split_list(text: str) -> list[str]:
    """The top-level elements of an SNBT list body."""
    parts, depth, start, quote = [], 0, 0, None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote and text[i - 1] != "\\":
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    return parts + [text[start:]] if text[start:].strip() else parts


def _cut_list(text: str, key: str) -> tuple[str, list[str]] | None:
    """`text` with the list after `key` emptied, and that list's elements; None without one."""
    at = text.find(key)
    if at < 0:
        return None
    start = end = at + len(key)
    depth = 1
    while depth:
        depth += {"[": 1, "]": -1}.get(text[end], 0)
        end += 1
    return text[:start] + text[end - 1:], _split_list(text[start:end - 1])


def fit_rcon(command: str) -> list[str]:
    """`command`, or for an over-long setblock of a container, the setblock with its Items
    emptied and one `data modify ... append` per item (and per stack inside a shulker box)."""
    head = "setblock "
    cut = _cut_list(command, "Items:[") if command.startswith(head) else None
    if len(command) <= RCON_MAX or cut is None:
        return [command]
    placed, items = cut
    pos = " ".join(command[len(head):].split(" ", 3)[:3])
    out = [placed]
    for item in items:
        inner = _cut_list(item, '"minecraft:container":[')
        if len(item) + 80 <= RCON_MAX or inner is None:
            out.append(f"data modify block {pos} Items append value {item}")
            continue
        out.append(f"data modify block {pos} Items append value {inner[0]}")
        out += [f'data modify block {pos} Items[-1].components."minecraft:container" append value {e}'
                for e in inner[1]]
    return out


def _place(rcon: Rcon, plot: str, name: str, entry: dict, build: Build | None, test_names,
           update: str = "all") -> None:
    x, y, z = _abs(plot, entry["slot"])
    w, h, _ = entry["size"]
    bx = x + (entry["box"][0] - w) // 2
    if build is not None:
        for c in normalised(build).to_commands(update):
            for part in fit_rcon(c):
                checked(rcon, f"execute positioned {bx} {y} {z} run {part}")
    text = json.dumps(label_text(title(plot, name), entry, test_names), ensure_ascii=False)
    width = int(entry["box"][0] / (PX * SCALE))
    tags = json.dumps([TAG, plot, f"sr_{name}"])
    checked(rcon, f"summon text_display {x + entry['box'][0] / 2} {y + h + 1} {z} "
                  f"{{Tags:{tags},billboard:\"center\",line_width:{width},text:{text},"
                  f"transformation:{{scale:[{SCALE}f,{SCALE}f,{SCALE}f],translation:[0f,0f,0f],"
                  f"left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]}}}}")


def _forceload(rcon: Rcon, plot: str) -> None:
    p = PLOTS[plot]
    (ox, _, oz), (sx, _, sz) = p.origin, p.size
    rcon.cmd(f"forceload add {ox} {oz} {ox + sx - 1} {oz + sz - 1}")
    wait_loaded(rcon, p.origin, p.size)


def _library_spec(name: str):
    """The spec's current library file, None if it is gone, or the load error."""
    try:
        return fileformat.load(library.path_of(name))
    except LookupError:
        return None
    except Exception as e:  # being edited: keep the entry as it stands
        return e


def _pack(plot: str, state: dict, keep: str | None) -> None:
    """Give every entry a slot afresh, in name order; drop the oldest failing entries (then
    the oldest) until they all fit. `keep` is never dropped."""
    size = PLOTS[plot].size
    specs = state["specs"]
    while True:
        placed = {}
        for name in sorted(specs):
            slot = find_slot(specs[name]["box"], _rects(placed), size)
            if slot is None:
                break
            placed[name] = dict(specs[name], slot=slot)
        else:
            state["specs"] = placed
            return
        candidates = [n for n in specs if n != keep]
        if not candidates:
            raise ValueError(f"{keep} alone does not fit in {plot}")
        failing = [n for n in candidates if status(specs[n], None) == "fail"]
        victim = min(failing or candidates, key=lambda n: specs[n].get("tested", 0))
        _log(f"{plot}: dropped {victim} ({status(specs[victim], None)}) to make room")
        del specs[victim]


def redraw(rcon: Rcon, plot: str, state: dict, current: tuple[str, Build] | None = None,
           repack: bool = False) -> None:
    """Clear the whole plot and draw every entry, rereading builds from the library (the
    current spec's build is the one just tested). Entries whose file is gone are dropped;
    entries whose size changed keep their slot if it still fits, else everything repacks."""
    size = PLOTS[plot].size
    builds, tests, updates = {}, {}, {}
    for name in list(state["specs"]):
        entry = state["specs"][name]
        s = _library_spec(name)
        if s is None:
            _log(f"{plot}: {name} has no library file; removed")
            del state["specs"][name]
            continue
        if _misplaced(plot, name):
            _log(f"{plot}: {name} belongs {'in' if name.startswith('ref_') else 'outside'} "
                 f"{REFERENCES.name}; removed")
            del state["specs"][name]
            continue
        if isinstance(s, Exception):
            _log(f"{plot}: {name} did not load ({s}); keeping its slot empty")
            builds[name] = None
            continue
        tests[name] = [t["name"] for t in s.tests]
        builds[name] = s.build
        updates[name] = s.update_pass
        entry["traits"] = list(s.traits)
    if current:
        builds[current[0]] = current[1]
    for name, b in builds.items():
        if b is not None and b.blocks:
            entry = state["specs"][name]
            entry["size"] = size_of(b)
            entry["box"] = box_of(title(plot, name), entry["size"], size)
            entry["blocks"] = _digest(b)
    specs = state["specs"]
    if repack or not all(e.get("slot") and _fits(e["slot"], e["box"], _rects(specs, n), size)
                         for n, e in specs.items()):
        _pack(plot, state, current[0] if current else None)
    p = PLOTS[plot]
    _forceload(rcon, plot)
    rcon.cmd(f"kill @e[type=text_display,tag={TAG},tag={plot}]")
    for c in clear_commands(p.origin, p.size):
        checked(rcon, c)
    for name, entry in sorted(state["specs"].items()):
        _place(rcon, plot, name, entry, builds.get(name), tests.get(name), updates.get(name, "all"))


def _record(state: dict, spec, result: dict) -> dict:
    entry = state["specs"].setdefault(spec.name, {"results": {}})
    r = {"result": "pass" if result.get("passed") else "fail"}
    if result.get("delay") is not None:
        r["delay"] = result["delay"]
    entry.setdefault("results", {})[result["test"]] = r
    entry["results"] = {t: v for t, v in entry["results"].items() if t in {x["name"] for x in spec.tests}}
    entry["traits"] = list(spec.traits)
    entry["tested"] = time.time()
    if result.get("owner"):
        entry["owner"] = result["owner"]
    else:
        entry.pop("owner", None)
    return entry


def show(rcon: Rcon, plot: str, spec, build: Build, result: dict, full: bool = False) -> None:
    """Record one test's outcome ({test, passed, delay}) and stand `build` in its slot in
    `plot` on main. `full`: the plot on main was overwritten (the test ran there), so
    redraw every entry. Never raises; failures go to server/showroom.log."""
    try:
        _show(rcon, plot, spec, build, result, full)
    except Exception:
        _log(f"{plot}: show {getattr(spec, 'name', spec)} failed\n{traceback.format_exc()}")


def _show(rcon, plot, spec, build, result, full):
    if _misplaced(plot, spec.name):
        return
    size = PLOTS[plot].size
    path = STATE / f"{plot}.json"
    first = not path.exists()
    state = load_state(plot)
    old = dict(state["specs"].get(spec.name, {}))
    entry = _record(state, spec, result)
    tests = [t["name"] for t in spec.tests]
    if first or full:
        # First time: the plot still holds the last whole-plot mirror, so start clean.
        redraw(rcon, plot, state, (spec.name, build))
        save_state(plot, state)
        return
    entry["size"] = size_of(build)
    entry["box"] = box_of(title(plot, spec.name, spec.path), entry["size"], size)
    same = (old.get("slot") and old.get("size") == entry["size"] and old.get("box") == entry["box"]
            and old.get("blocks") == _digest(build))
    entry["blocks"] = _digest(build)
    others = _rects(state["specs"], spec.name)
    if old.get("slot") and _fits(old["slot"], entry["box"], others, size):
        entry["slot"] = old["slot"]
    else:
        entry["slot"] = find_slot(entry["box"], others, size)
    if entry["slot"] is None:
        redraw(rcon, plot, state, (spec.name, build), repack=True)
        save_state(plot, state)
        return
    _forceload(rcon, plot)
    if same:
        text = json.dumps(label_text(title(plot, spec.name, spec.path), entry, tests), ensure_ascii=False)
        out = rcon.cmd(f"data merge entity @e[type=text_display,tag={TAG},tag=sr_{spec.name},limit=1] "
                       f"{{text:{text}}}")
        if "No entity" not in out and "<--[HERE]" not in out:
            save_state(plot, state)
            return
    if old.get("slot"):
        _clear_box(rcon, plot, spec.name, old)
    _clear_box(rcon, plot, spec.name, entry)
    _place(rcon, plot, spec.name, entry, build, tests, spec.update_pass)
    save_state(plot, state)


def _digest(build: Build) -> str:
    b = normalised(build)
    return hashlib.sha1(repr((sorted(b.blocks.items()), b.entities)).encode()).hexdigest()
