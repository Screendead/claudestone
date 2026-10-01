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
REDSTONE_PLOT=main pytest tests/test_library.py   # every test in main instead of each spec's plot
python -m scripts.retest <plot>... [--spec NAME]... [--failed] [-k EXPR]   # a plot's (main: no-plot) or named specs, each in its plot; --failed: last result failed
pytest tests/test_generated.py tests/test_devices.py tests/test_traits.py  # no server needed
python -m scripts.generate               # rewrite generated library files
python -m scripts.package two_digit_adder   # dist/<name>/ + .zip data pack
python -m scripts.plots                  # redraw plot borders and labels in the world
python -m scripts.lint [<spec>]          # offline checks, whole library by default
python -m scripts.try <spec> [--test NAME]... [--trace]   # lint + run on a satellite
python -m scripts.servers {start,stop,status} [laptop|docker|all]   # satellites
python -m redstone.docker_sats {start,stop,status} [dsatN]...   # Docker satellites only
python -m scripts.satellite_image        # rebuild the Docker satellite image on the desktop
python -m scripts.remote_run <dir> [--jobs N] -- <cmd> [args]...   # a CPU-heavy search, on the desktop
python -m scripts.remote_keep -- <cmd> [args]...   # rerun a resumable desktop job after each desktop drop
python -m scripts.jobs start <name> <dir> [--jobs N] [--resume CMD] -- <cmd>...   # a detached desktop job
python -m scripts.jobs {status [<name>],stop <name>,log <name> [-n N]}
python -m scripts.status                 # jobs, search CPUs, servers, plots, RAM and plan usage on one screen
python -m scripts.blockdata              # regenerate redstone/blocks.json after a server upgrade
python -m scripts.watch {start,stop,status}   # the camera director on main (starts by itself)
python -m scripts.watch {off,on} [player]...  # opt players out of / back into being watched (in game: /trigger watch_off, /trigger watch_on)
python -m scripts.watch poses [--seconds N]   # read-only: each watch camera's steps, reversals, jerk
git config core.hooksPath githooks       # once per clone: pre-commit lints staged library specs and checks library/INDEX.md
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
`library/mechanics/`. `docs/WINS.md` banks true wins, where we beat the community best against rebuilt `ref_<author>_<design>` specs.
`githooks/pre-commit` (enabled by `git config core.hooksPath githooks`) runs `scripts.lint` on
staged library specs and fails if regenerating `library/INDEX.md` (`python -m scripts.index --tracked`, committed and staged specs only)
changes it, so stage the regenerated index with the spec.

## Plots

The world is a redstone-preset superflat (surface y=56), daylight, weather and mob spawning
off. `redstone/plots.py` divides it into a 192x24x192 `main` plot and, north of it, a grid
of 72x32x72 plots (five a row, pitch 80, each forceloading exactly 5 x 5 chunks): one per
building block, eight mechanics workbenches, a black-ringed `references` plot,
`survival` and `storage`, each with a coloured concrete ring, glass corner posts and a floating name
drawn two blocks outside it. One plot sits off the grid: `bigdoor` (112x64x112 at 370,56,210,
gray ring, 8x8 chunks), for piston doors up to 16x16 with their mechanism; `library/door/` maps
to it via `FOLDER_PLOT`. `plot_for(path)` maps a `ref_*` file (a rebuilt
community design, see `docs/WINS.md`) to `references` and any other library file by folder
to its plot (`FOLDER_PLOT` for folders sharing one; mechanics, builds and input have none).
Unset, a library test builds in `plot_for`'s plot, or in main when its folder has none
(mechanics, builds, input); `REDSTONE_PLOT=<name>` makes every test build there, `main`
included. `scripts.try` sets it from `plot_for`. Ticks
are global per server, so each test takes one server's `rig.lock`: the `main` plot runs on
the main server; any other plot runs on the first idle satellite, Docker ones first (main if none is up), so
runs in different plots proceed at once. A per-plot lock (`server/plots/<plot>.lock`)
serialises runs of the same plot. Satellites keep plot coordinates; the plot's status sign
on main is updated whichever server runs. `server/plots/<plot>.json` records which server
last ran the plot and, when `REDSTONE_OWNER` is set (a workflow id, say), who; the showroom
entry keeps that owner and the plot's status sign shows it after the test name. After a test the `main` plot keeps its last tested build (mirrored from a
satellite if one ran it). Every other plot on main is a showroom (`redstone/showroom.py`,
called from conftest teardown with plain commands, no main lock): each variant ever tested
there stands in its own slot under a `text_display` label (tags `showroom`, `<plot>`,
`sr_<spec>`; green/red/yellow for passed/failed/not fully run). `ref_*` specs stand only in
`references`, labelled `<folder>: <spec>`, and nothing else does; a redraw drops misplaced
entries and those whose file is gone. Slots, sizes and results
are in `server/showroom/<plot>.json`, errors in `server/showroom.log`;
`python -m scripts.showroom rebuild [<plot>]` redraws from those files and the library.

Players on main watch hands-off: a single director process (`redstone/watch.py`,
`python -m scripts.watch run`) puts every online player in spectator (tag `watch`; the old
gamemode is kept in `server/watch/state.json` and restored by `scripts.watch off` or by `/trigger watch_off` in game (`watch_on` opts back in):
the director polls the two trigger objectives over RCON and enables them again after each poll,
with no data-pack tick function; the opt-out list is matched without case and kept in
`state.json`, so it holds across director and server restarts) and cuts
between shots, each held at least `dwell` seconds: a test building on main (the main plot, or
any plot a test runs in on the main server), the main plot's result, a showroom slot placed;
failures first, then new variants, then the newest; when nothing happens it tours recent
builds. Each shot frames the build's box in a 70° field of view from the north, about 35° up,
clear of posts, labels and other slots, and slides slowly sideways (`motion: "dolly"`; an
`orbit` swing turns in visible 1.4° steps, since entity rotation is sent in 1/256 turns). Each
watcher spectates its own invisible `item_display` (tags `watch_cam`, `watch_cam_<name>`),
summoned where the player is and attached once; after that only these entities move, gliding
by `teleport_duration` and snapping (duration 0) on a cut, because a switch between the
player's view and an entity's eases the eye height by 1.62 blocks. While main is frozen or
warping the client can't move them, so the camera holds still; a camera cleared away with a
plot is summoned again; `camera: "tp"` in the config teleports the players instead (steps).
The status line is an actionbar. Events come from
`server/watch/events.jsonl` and `status/<plot>.json` (written by `spec.py`), the showroom
files and, for a pytest older than those, new traces. `spec.run` and `scripts.servers start`
start the director if none holds `server/watch/director.lock`; it outlives pytest, and
`scripts.watch stop` keeps it off until `start`; `REDSTONE_WATCH=0` stops one process from
starting it. Settings (`orbit`, `dwell`, `camera`, ...) are in `server/watch/config.json`,
set by `scripts.watch start --no-orbit` etc. and reread live; its log is `director.log`. It
uses plain RCON commands on main, never a rig lock, and nothing goes to chat.
`scripts.watch poses` samples each camera entity's server-side pose (the teleport targets, not
the client's interpolation) and prints per-axis steps, reversals and jerk, flagging a camera
shaking in place.

## Server

`server/` is gitignored and holds `server.jar`, `server.properties` (RCON password read
from here), `harness.log`, and `rig.lock`. `ensure_server()` launches it with Java 25+.
Settings that must stay: `pause-when-empty-seconds=-1` (otherwise the game clock stops
with no players), RCON enabled, and `broadcast-rcon-to-ops=false` and `broadcast-console-to-ops=false` (test commands
stay out of chat). `simulation-distance=8` with `view-distance=32`: every plot is
forceloaded and ticks anyway, so a player's simulation distance only adds empty chunks to
every stepped tick (at 32, about 4000, which with a raised `random_tick_speed` crashed main).
`max-tick-time=300000`: the watchdog measures how far the loop runs behind its schedule, not
one tick, and stepping at `WARP_RATE` makes 60 s of lag easy to reach. Changing properties
needs a restart, which kicks any player watching. After each test the world is unfrozen
for players.

Satellites `sat1..sat6` (`redstone/servers.py`) live in `server/satellites/<name>/` on
ports 25566+/RCON 25576+, `-Xmx1G`, sharing main's jar, `libraries/` and `versions/` by
symlink and its properties (view/simulation distance 2, max-players 1). A satellite
force-loads only the plot under test. `python -m scripts.servers {start,stop,status}`
creates/starts (idempotent) or stops them (`laptop` by default; status shows both kinds);
pytest never starts a laptop satellite. `REDSTONE_SERVER=main` (or `sat3`, `dsat2`, ...)
pins every test to that server; a pinned dsat that is down fails the test.

Docker satellites `dsat1..dsat6` (`redstone/docker_sats.py`, which adds them to `SERVERS`
when imported) are containers of image `redstone-satellite:26.3` (`docker/satellite/`,
rebuilt by `scripts.satellite_image`) on the desktop, reached as `docker -H ssh://<host>`,
the host from `REDSTONE_DOCKER_HOST` or the gitignored `server/docker_host` (never write it
into a tracked file); the desktop's shell is cmd.exe. RCON is published on the desktop's
loopback at 25676..25681 and forwarded to the same port here through the shared SSH
ControlMaster (`ssh -O forward`), so the per-port RCON lock keeps them apart from laptop
satellites. A forward accepts TCP with the container down, so "up" means an RCON login plus
a command (`is_up()`), never a port check. `rig.lock`, `harness.log` (the container's
`docker logs`) and `crash-reports/`, saved when it is removed, live in
`server/satellites/dsatN/`; the data pack Rig writes there is pushed into the container
(`push_datapack`, ~0.4 s a test). For a non-main plot pytest takes, in order: an idle
running dsat, an idle laptop satellite, a dsat it starts for the test (~6 s; only when
every running satellite is busy), the first busy satellite to come free; main only if no
satellite is up or startable. A dsat is listed from one `docker ps` and asked `is_up()`
only once its lock is won. With no host configured nothing is tried; a desktop that fails
to answer (or no `docker`/`ssh` on PATH) is written to `server/satellites/dsat_unreachable`
and skipped by every process, so tests fall back to the laptop satellites; every 2 minutes
one background thread (one process at a time) probes it again and clears or renews the
mark, so only the first failure costs a test (up to ~10 s). A detached reaper stops dsats
whose `rig.lock` is free and untouched for 8 minutes; winning the lock of a dsat that turns
out to be down does not count as use. After a hung or dropped SSH/docker
call the master is probed and closed (`ssh -O exit`, dropping every forward) only if it
no longer answers; the call is then retried once.

A test on a dsat runs in its container, next to the server (`redstone/remote.py`): over
the forward every RCON command is a ~6 ms round trip, and a test sends hundreds. The rig
fixture yields a `RemoteRig`, and `spec.run` hands it the test: one
`ssh <host> docker exec -i dsatN python3 -c <BOOT>` whose first stdin line carries
`redstone/*.py` and the pickled Spec and test. In the container `serve` runs `spec._run` on
a `Rig` over local RCON and streams back status-sign commands (replayed on main), watch
events (replayed here), a heartbeat, and at the end the result or exception, the loaded
build and the trace text, which is written here; traces and failure messages are the ones
a forwarded run gives. Locks, plot records, showroom and mirroring stay on the laptop. A dsat
listed by `docker ps` is taken without an RCON check (the container waits for a server still
starting). 45 s without a line probes the desktop: gone, it is marked down and the test
fails; answering, the wait goes on up to 5 minutes. A container of an image without
python3 runs the test through the forward as before; `REDSTONE_REMOTE=0` forces that.
The image carries python3, pyyaml, pip and python-sat.

`scripts.remote_run` runs CPU-heavy offline jobs (pysat searches, brute force; no Minecraft)
in throwaway containers of the same image: the dir is uploaded once per content hash into a
Docker volume (`rr-src-*`, older snapshots of the same dir dropped), a `requirements.txt`
there is pip-installed once per content (`rr-pip-*`), output streams back live, the exit
code is the command's, and new or changed files are copied back into the dir. `--jobs N`
gives the container N CPUs and N GB; all runs together hold at most `REDSTONE_SEARCH_CPUS`
(default 12) of the desktop VM's 14 CPUs, via slot locks in `server/remote_run/`. Ctrl-C,
SIGTERM or a killed process stops the container (its stdin closes); an unreachable desktop
is an error, never a local run.
`scripts.remote_keep` runs a local command (usually a script that rebuilds its resume state from
the log it streamed, then calls remote_run) and runs it again whenever it exits 255, remote_run's
code for a lost desktop, once the desktop's Docker answers again. Any other exit ends it (a
`before` hook may add arguments to each start). A long search is started with `scripts.jobs
start`, never by hand-made wrappers: it detaches a runner in its own session (it outlives the
shell and any task time limit) that runs `remote_run <dir> --jobs N -- <cmd>` under remote_keep's
loop. Output goes to `server/jobs/<name>/log`; pid, cmd, dir, started, restarts and exit to
`server/jobs/<name>/job.json`. A dropped container copies nothing back, so the log is the
checkpoint: `--resume CMD` runs through the shell in `<dir>` before every start with `$JOB_NAME`,
`$JOB_DIR`, `$JOB_LOG` and `$JOB_RESTARTS` set; the words it prints are appended to `<cmd>`, the
files it writes into `<dir>` are uploaded, a nonzero exit ends the job, and it must not call
remote_run itself. `jobs status` reports running, stopped, finished, failed, or dead (a stale pid).
`scripts.status` is read-only and takes a few seconds: it probes locks without waiting, asks the
desktop one `docker ps` (none while `dsat_unreachable` is set), and reads plan usage only from
`~/.claude/usage-cache.json`.

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
  `glitch_free`, `reset`, `settle`, `initial` drivers, `steps` of drive/use/wait/expect/level/wave/run/log/check/repeat and the container steps
  insert/expect_items/throughput (a named cell or [x, y, z]; throughput records items moved and
  a rate per hour in the trace and result), `finally`
  commands), a top-level `update_pass` (all, none, unobserved: observers are set last and the
  blocks they face are not cloned, or strict: every block set with `setblock ... strict` and no
  pass, which observer-heavy builds such as LegDen's 10x10 need; the packaged `place` and the
  showroom use the same pass), a `door:` section (doorway origin/width/height/facing, depth,
  door and surface material, input plus fixture `repeater[delay=1]` or a `lever` flipped like a
  click, tier) and the `door_cycle` test kind. `dump` must round-trip
  what `load` reads; `tests/test_generated.py` fails if a generated file is stale.
- `redstone/harness.py`: `Rig` owns one plot. It clears with `fill … air strict` (no
  item drops), kills non-player entities in it (but not the watch camera), 2 blocks around
  it and up to the build height, waits `FLUSH_TICKS` so burnt-out torches recover, kills again (entity sections
  load after their chunk), loads a build, and steps with `tick freeze`/`tick step`, polling game time.
  On main each step batch raises the tick rate to `WARP_RATE` and drops it back to
  `IDLE_RATE` (20) right after, even on an error: the login timeout counts 600 ticks at the
  current rate, so a rate left high kicks joining players. The cost is up to one idle tick
  period (~40 ms) per batch, so satellites (no one joins them) stay at `WARP_RATE` for the
  whole test; `Rig.release()` (conftest teardown) sets 20 again before `tick unfreeze`.
  `Rig()` also resets the tick rate and `BASELINE_GAMERULES`. Inputs are
  redstone blocks placed/removed at driver cells; levers and buttons are toggled with
  `setblock` then a `clone` of the block they hang on (setblock alone doesn't update it),
  and the harness schedules button release itself. Reads use a generated probe function
  (≤60,000 commands per chunk, because of the 65,536 command-chain limit) that copies
  block states into storage. `load` runs the build as `build0..N` (≤60,000 commands each, one
  RCON call per part) and takes extra functions and block tags; `call(functions, read)` runs
  functions, then `data get storage`, in one `rcon.sequence()`. Clears fill 32x32x32 pieces.
- `redstone/spec.py`: runs one test of a `Spec` on a `Rig`, reports it to the watch
  director (events and a status line; other plots' status signs as before), and records traces. Step failures (expect, level, wave, check, insert,
  expect_items, throughput, a `run` or `log` whose command fails) are collected and the steps run to the end; the test then
  fails with the first; a failure that stops the test (a truth table, a harness error) is
  written into the trace's `failures` too. `tests/test_spec_offline.py` checks step semantics on a fake Rig.
- `scripts/lint.py`: offline checks, including block states and entity types against
  `redstone/blocks.json` (generated by `scripts/blockdata.py` from the server jar's data
  reports; don't hand-edit it), build bounds against the spec's plot, non-string cell names
  (YAML reads unquoted on/off/yes/no as booleans), wave strings, `repeat` bodies, and `run`/`log`/`check`/`finally` length for RCON, and the container steps' cells, keys and
  generated command length.
- `redstone/door.py`: `plan(spec)` turns a `door:` section into probe and occupancy functions
  and tags; `cycle()` runs `door_cycle`. Tick 0 is the tick the fixture repeater's output changes.
  Each tick it reads only the hallway (doorway ± depth) and the cells beside it (960 for 16x16;
  a pulled block shows as moving in the wall cell beside the doorway) into `door_timing.Run`
  until static for 40 ticks, and reports open/close times under R (landing, start + 2), H1
  (hallway holds its final real blocks) and R1 (0-tick pulls instant), plus visible times,
  seamless grades and the tier. Volume (`door_volume`) comes from the region's outermost occupied
  cells at rest (found over RCON by comparing slabs with the air 128 blocks above, since a
  function over every cell is too big for a 1 GB satellite to parse), occupancy flags on each
  piston's line every tick, fired pistons' head cells, and entities. With a `lever` input tick
  0 is the first tick after the click. A move starting in the tick another lands in the same
  cell shows as progress 0, 0.5, 0, 0.5 and counts as two movements. A moving
  piston's `blockState` is a bare id when the block is in its default state, else
  `{Name, Properties}`. Broken bounds are collected failures; per-tick changes go under `door`
  in the trace.
- `redstone/remote.py`: runs a spec test in a Docker satellite's container (`serve`) and
  drives it from the laptop (`RemoteRig`); see the Docker satellite paragraphs above.
- `redstone/rcon.py`: the server writes every RCON client's output into one shared buffer
  (`DedicatedServer.runCommand`), so two clients' commands at once get each other's replies.
  `Rcon.cmd` takes `server/rcon.<port>.lock` for each command, across processes. Anything
  that sets state with one command and reads it with the next (a probe function, then
  `data get storage`) wraps them in `with rcon.sequence():`, which holds that lock across the
  whole sequence (reentrant); `Rig.snapshot`, `Rig.command` and `Rig.level` do.
- `redstone/docker_sats.py`: `DockerSatellite`, a `Server` whose world is a container on the
  desktop; `servers.take_idle`/`take` choose and lock a server for conftest.
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

Run CPU-heavy offline searches (pysat, long brute-force scripts) on the desktop with
`python -m scripts.remote_run <dir> --jobs N -- python3 script.py ...`, not on the laptop.
