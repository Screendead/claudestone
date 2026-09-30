# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Vanilla Minecraft Java (26.3) redstone builds, designed in Python, tested tick by tick
on a real headless server over RCON, and shipped as a data pack that places the exact
tested blocks. It is not a mod. The goal is to turn a sentence like "two numbers on levers,
a button, the sum on a 7-segment display" into a proven, paste-able build.

## Commands

```sh
source .venv/bin/activate
pytest                                   # everything; starts the server if RCON is down
pytest "tests/test_library.py::test_spec[latch::holds a 1 when locked]"   # one spec test
REDSTONE_PLOT=xor pytest tests/test_library.py -k xor_   # build in the xor plot, not main
pytest tests/test_generated.py tests/test_devices.py tests/test_traits.py  # no server needed
python -m scripts.generate               # rewrite generated library files
python -m scripts.package two_digit_adder   # dist/<name>/ + .zip data pack
python -m scripts.plots                  # redraw plot borders and labels in the world
python -m scripts.lint [<spec>]          # offline checks, whole library by default
python -m scripts.try <spec> [--test NAME]... [--trace]   # lint + run on a satellite
python -m scripts.blockdata              # regenerate redstone/blocks.json after a server upgrade
```

Test ids for the library are `test_spec[<spec name>::<test name>]`; spec names are unique
across the whole library. Every test run writes `traces/<spec>/<test>.json`: with
`REDSTONE_TRACE=1` (`try --trace`) every signal cell on every tick, otherwise `"sparse": true`
with only the named cells at the snapshots the test took anyway.

VS Code extension (`vscode-redstone/`): `npm run build`, `npm test`, `npm run package`
(produces the `.vsix`). It opens `*.redstone.yaml` as a layer-by-layer visual editor,
plays traces, and runs a single test by the pytest id above.

## Library layout

`library/<building block>/<variant>.redstone.yaml`: one folder per reusable building block
(not, xor, d_latch, clock, ...) holding many designs of it; `library/builds/` holds whole
builds and harness checks. `redstone/library.py` finds a spec by name. A spec's `traits`
come from `redstone/traits.VOCABULARY`; the factual ones (silent, lightless, pistonless,
entityless, flat, one_wide, instant, tileable/stackable from `tile` tests, ...) are checked
against the blocks, fixtures excluded, by `tests/test_traits.py`; the rest are the
designer's claim. `docs/AUTHORING.md` is the
self-contained brief for designing a variant; keep it in step with the format and tools.
`docs/MECHANICS.md` catalogues verified 26.3 mechanics, each proven by a spec in
`library/mechanics/`.

## Plots

The world is a redstone-preset superflat (surface y=56), daylight, weather and mob spawning
off. `redstone/plots.py` divides it into a 192x24x192 `main` plot and 48x32x48 plots, one
per building block, each with a coloured concrete ring, glass corner posts and a floating
name drawn two blocks outside it. `plot_for(path)` maps a library folder to its plot
(`FOLDER_PLOT` for folders sharing one; mechanics, builds and input have none).
`REDSTONE_PLOT=<name>` makes tests build there; unset, tests build in main unless the build
does not fit it, then in `plot_for`'s plot. `scripts.try` sets it from `plot_for`. Ticks
are global per server, so each test takes one server's `rig.lock`: the `main` plot runs on
the main server; any other plot runs on the first idle satellite (main if none is up), so
runs in different plots proceed at once. A per-plot lock (`server/plots/<plot>.lock`)
serialises runs of the same plot. Satellites keep plot coordinates; the plot's status sign
on main is updated whichever server runs. `server/plots/<plot>.json` records which server
last ran the plot. After a test the `main` plot keeps its last tested build (mirrored from a
satellite if one ran it). Every other plot on main is a showroom (`redstone/showroom.py`,
called from conftest teardown with plain commands, no main lock): each variant ever tested
there stands in its own slot under a `text_display` label (tags `showroom`, `<plot>`,
`sr_<spec>`; green/red/yellow for passed/failed/not fully run). Slots, sizes and results
are in `server/showroom/<plot>.json`, errors in `server/showroom.log`;
`python -m scripts.showroom rebuild [<plot>]` redraws from those files and the library.

## Server

`server/` is gitignored and holds `server.jar`, `server.properties` (RCON password read
from here), `harness.log`, and `rig.lock`. `ensure_server()` launches it with Java 25+.
Settings that must stay: `pause-when-empty-seconds=-1` (otherwise the game clock stops
with no players), RCON enabled, and `broadcast-rcon-to-ops=false` and `broadcast-console-to-ops=false` (test commands
stay out of chat). Changing properties
needs a restart, which kicks any player watching. After each test the world is unfrozen
for players.

Satellites `sat1..sat6` (`redstone/servers.py`) live in `server/satellites/<name>/` on
ports 25566+/RCON 25576+, `-Xmx1G`, sharing main's jar, `libraries/` and `versions/` by
symlink and its properties (view/simulation distance 2, max-players 1). A satellite
force-loads only the plot under test. `python -m scripts.servers {start,stop,status}`
creates/starts (idempotent) or stops them; pytest never starts one. `REDSTONE_SERVER=main`
(or `sat3`, ...) pins every test to that server.

## Architecture

Data flows: generator or hand-written YAML → `Spec` → `Rig` on the server → pass/fail and
trace → `package` data pack.

- `redstone/build.py`: `Build` is a dict of positions to block states (which may carry
  block-entity NBT) plus entities to summon. `to_commands()`
  emits two passes: `setblock` everything, then `clone` each block onto itself so every
  block gets a neighbour update (placement alone leaves stale state). The packaged `place`
  function is this exact text.
- `redstone/fileformat.py`: the `.redstone.yaml` format (spec in its docstring): layers
  keyed by y, a glyph palette, inputs (one name may span several cells)/outputs/named
  cells, `fixture` blocks (outside the design's size and traits) and `reserve`d air, and
  tests (`truth_table` with `x` don't-care outputs, `tile` for two copies, `delay`/`max_delay`, per-output-edge `delays`/`max_delays`,
  `glitch_free`, `reset`, `settle`, `initial` drivers, `steps` of drive/use/wait/expect/level/wave/run/log/check/repeat, `finally`
  commands). `dump` must round-trip
  what `load` reads; `tests/test_generated.py` fails if a generated file is stale.
- `redstone/harness.py`: `Rig` owns one plot. It clears with `fill … air strict` (no
  item drops), kills non-player entities in it, 2 blocks around it and up to the build
  height, waits `FLUSH_TICKS` so burnt-out torches recover, kills again (entity sections
  load after their chunk), loads a build, and steps with `tick freeze`/`tick step`, polling game time.
  `fast()` is a reentrant context that raises the tick rate while stepping. Inputs are
  redstone blocks placed/removed at driver cells; levers and buttons are toggled with
  `setblock` then a `clone` of the block they hang on (setblock alone doesn't update it),
  and the harness schedules button release itself. Reads use a generated probe function
  (≤60,000 commands per chunk, because of the 65,536 command-chain limit) that copies
  block states into storage.
- `redstone/spec.py`: runs one test of a `Spec` on a `Rig`, shows the test name as a
  title to players, and records traces. Step failures (expect, level, wave, check, a `run`
  or `log` whose command fails) are collected and the steps run to the end; the test then
  fails with the first. `tests/test_spec_offline.py` checks step semantics on a fake Rig.
- `scripts/lint.py`: offline checks, including block states and entity types against
  `redstone/blocks.json` (generated by `scripts/blockdata.py` from the server jar's data
  reports; don't hand-edit it), build bounds against the spec's plot, non-string cell names
  (YAML reads unquoted on/off/yes/no as booleans), wave strings, `repeat` bodies, and `run`/`log`/`check`/`finally` length for RCON.
- `redstone/pla.py`: generators for sum-of-products logic as two NOR planes of torches
  (`pla`), an OR-only plane (`or_plane`), and a Quine–McCluskey `minimise`. Each emits its
  own truth-table test and a computed `max_delay` bound.
- `redstone/devices.py`: player-facing parts: 7-segment digits (lamps hard-powered from
  behind by repeaters so the power bleeds into neighbouring lamps of the same segment, with
  frame blocks between segments) and lever/button switches.
- `redstone/route.py`: `Circuit` places parts at hand-chosen offsets and routes nets
  between named pins as dust on support blocks, with keep-out spacing, pin/start
  reservation, repeater insertion, and rip-up-and-retry. `build()` returns a `Spec` with
  prefixed named cells and a delay bound.
- `scripts/generate.py`: every generated library entry, including the full
  `two_digit_adder`. Edit generators here, then regenerate; don't hand-edit generated YAML.
  Hand-written specs (e.g. `latch`, basic gates) live only in `library/`.

## Orientation traps

- Repeater `facing=F`: input on side F, output on the opposite side.
  Wall torch `facing=F`: attached to the block on the opposite side.
- Player-facing builds face north; the player stands north looking south, so +x is on the
  player's left. `tests/test_devices.py` checks the digit faces as the viewer sees them.
- Soft vs hard power matters for lamps: a repeater or dust pointing into a lamp lights
  its lamp neighbours too; a torch beside it, or a repeater into the block behind it,
  does not.

## Environment

`rm` is blocked by a hook; use `trash <paths>`.
