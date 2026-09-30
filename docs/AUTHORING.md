# Designing a library variant

Everything you need to add a design to `library/<family>/`. Don't read the harness source
unless a tool here misbehaves. `docs/MECHANICS.md` lists verified niche mechanics worth
exploiting, each with the spec that proves it.

## Loop

```sh
source .venv/bin/activate
python -m scripts.lint [<spec>]        # offline (no args: whole library): unknown block states or
                                       # entities, unsupported dust/torches, bad cells, over-long
                                       # run/log/check commands, bad wave strings. Instant.
python -m scripts.try <spec>           # lint, then every test on a free server: one line each
                                       # (log replies under it), traits check and size. Exit 0 = done.
python -m scripts.try <spec> --test "<test>"   # only that test (repeatable)
python -m scripts.retest <plot> [--failed] [-k word]   # every spec of a plot (main: those with
                                       # no plot), or --spec <name>...; --failed: only tests
                                       # whose last result failed. One line per test.
python -m scripts.try <spec> --trace   # every cell on every tick; on failure prints the table
python -m scripts.look trace <spec> "<test>" [--cells a,out] [--from T --to T] [--levels]
python -m scripts.look world <plot> [--y N]   # the live blocks as layers, after a run
```

`try` builds in your family's plot (it prints `plot: <name>`; folders such as nand or
full_adder share a plot, see `redstone/plots.py`; a `ref_*` rebuild of a community design
builds in `references`; mechanics, builds and input use main). Every
run writes a trace: without `--trace` it holds only the named cells at the ticks the test
read them, which is enough for `look trace` on a truth table. Tests run on satellite servers and
the passing build is copied into your plot in the main world, where the user watches; the
plot's billboard shows what is running. You never need RCON yourself.

Run a spec with `try` (or `retest`), never `pytest -k`: `-k` matches substrings, so `-k xor_`
also runs other families' specs whose names contain it. Specs in `mechanics/`, `builds/` and
`input/` have no plot of their own, so they run in `$REDSTONE_PLOT`, or in main on the main
server when it is unset; set `REDSTONE_PLOT=<plot>` (one the build fits) to run them on a
satellite instead. Set `REDSTONE_OWNER=<your id>` and the plot's status sign, its record and
the showroom entry name you as the one testing.

Run a CPU-heavy offline search (pysat, brute force) on the desktop, not the laptop:
`python -m scripts.remote_run <dir> --jobs N -- python3 script.py`. Its container has python3,
pyyaml and python-sat; anything else goes in a `requirements.txt` in `<dir>`.

## File

`library/<family>/<name>.redstone.yaml`; `name` is unique across the library.

```yaml
name: not_gate
description: An input inverted by a torch on a block.   # one line: what's special about it
traits: [compact, torch_based]         # from redstone/traits.py VOCABULARY
palette:                               # one character -> one cell
  .: air
  '=': smooth_stone
  a: {input: a}                        # air; the harness places/removes a redstone block here
  '>': repeater[facing=west]
  '#': white_concrete
  ): redstone_wall_torch[facing=east]
  o: {output: out, block: redstone_wire}
  L: {name: lamp, block: redstone_lamp}   # named cell: readable by expect, usable by use
  F: {block: redstone_torch, fixture: true}   # test fixture, see below
  _: {reserve: true}                   # air the design needs, see below
layers:                                # keyed by y; rows = z north->south, columns = x west->east
  0: |
    .====
  1: |
    a>#)o
tests:
- name: logic
  truth_table: |                       # inputs | outputs, 1/0; x = don't care (outputs only)
    a | out
    0 | 1
    1 | 0
  delay: 4                             # exact worst-case ticks; or max_delay: N as a bound
  delays: {out: {rise: 4, fall: 2}}    # optional, per output and edge; max_delays: bounds
```

- Every layer has the same width and height; top-left character is the origin.
- Several glyphs with the same `input:` name are one input, driven at every cell in the
  order the layers list them (y, then rows, then columns): a mux select row, a long
  column fed at both ends. In the palette that is one glyph used at each cell.
- `fixture: true` on a block (named or not) marks it as test scaffolding, not design: a
  decay chain, a threshold reader, an analog source. It is placed and tested, but left out
  of the size (`try`, `library/INDEX.md`) and of the checked traits, so a fixture torch
  doesn't break `lightless`.
- `{reserve: true}` is air that belongs to the design (a piston's travel, a frame's
  cell): it counts in the size, and lint fails if a block fills it.
- `initial: {a: 1}` on a test places that input's redstone block with the build, before
  the harness's update pass, so the build starts with the input already on; later
  `drive` steps move it as usual.
- Sequential tests use `steps:` instead: `drive: {a: 1}`, `use: lever` (click a named lever
  or button; buttons release by themselves), `wait: N` ticks, `expect: {q: 1}`,
  `level: {q: 7}` (below). `settle: N` sets ticks after loading (default 20 or delay+4).
- `wave: {out: '0011110000', q: 'xx11'}` checks each cell once per tick: character i
  (`1` on, `0` off, `x` don't care) at i ticks after the step starts, and the step advances
  as many ticks as the longest string. It fails at the first mismatch, naming the tick and
  cell. Use it for hold-for-N-ticks, clock periods, pulse widths and hazard windows; with
  `settle: 0` a wave straight after loading checks that the build stays quiet while it
  settles. Quote the strings (`0011` unquoted is a number).
- `repeat: {times: N, steps: [...]}` runs the steps N times (it nests); the trace marks
  each iteration (`repeat 2/3`) and failures inside name it.
- Containers (`cell` is a named cell or `[x, y, z]` from the origin; item ids may drop
  `minecraft:`):
  - `insert: {cell: feed, item: cobblestone, count: 10}`, or
    `items: [{id: cobblestone, count: 64}, {id: dirt}]`: stack i goes in slot `slot` + i
    (`slot` defaults to 0), replacing what was there; other slots keep their items.
    `clear: true` empties the container first (alone, it only empties it). It writes with
    `data modify block`, which updates comparators.
  - `expect_items: {cell: out, item: cobblestone, count: 30}`: the total count over the
    container's slots, of `item` (default: any) in `slot` (default: all), must equal
    `count`, or lie within `min`/`max`; `empty: true` is `count: 0` of anything. A failure
    lists what the container held, and the trace frame keeps it under `items`.
  - `throughput: {from: feed, to: out, item: cobblestone, ticks: 800, min: 90}`: counts
    `item` (default: any) in `to` and/or `from`, waits `ticks`, counts again. What arrived
    in `to` (else what left `from`) must be within `min`/`max`; the measurement
    (`arrived`, `left`, `per_hour` at 20 ticks a second) goes in the trace frame and the
    test result, and `try` prints it: `PASS flow (throughput out 100 in 800 ticks (9000/h))`.
    Start it once the flow is steady: items already in transit count when they arrive.
- A failing `expect`, `level`, `wave`, `check`, `run`, `insert`, `expect_items` or
  `throughput` doesn't stop the test: the steps run to the end, so the trace is complete,
  and the test fails with the first failure and `(and N more)`.
- Anything else: `run: <command>` runs any command and `check: <if/unless chain>` fails the
  test unless `execute <chain>` passes; `~` is the build origin. A `run` fails when its
  command fails, quoting the server's reply, except when it only did nothing: a reply that
  is empty or starts `Test failed` (a conditional `execute if ... run` whose condition
  failed), `No entity was found`, `Nothing changed`, `Could not set the block` (setblock to
  the state already there), `An objective already exists by that name`, or says a clock
  `is already at time marker` or a game rule `is already set to` the value. An objective outlives the test with its scores, so pair
  `scoreboard objectives add X dummy` with `finally: [scoreboard objectives remove X]`.
  `log: <command>` runs a command the same way and records its reply in the trace; `try`
  prints each one under the test's result line (use it to read contents, NBT or strengths).
  A test's `finally: [<command>, ...]` runs after its steps even when they fail, e.g. to
  restore a gamerule or the time. A test whose `run`/`log` steps set a gamerule must restore
  it in `finally` (lint enforces it): a failed step or killed server otherwise leaves it set,
  and the world saves it. E.g.
  `run: 'data merge block ~2 ~1 ~0 {Items:[{Slot:0b,id:"minecraft:stick",count:1}]}'`,
  `check: if block ~3 ~1 ~0 comparator[powered=true]`,
  `check: positioned ~2 ~1.5 ~0 if entity @e[type=item_frame,distance=..1,nbt={ItemRotation:3b}]`.
  `library/builds/steps_probe` and `probe_cells` are working examples.
- In `run`/`check`, `~` on x and z is the centre of the origin block (Minecraft centres the
  integer origin), so `~2 ~1 ~0` is the middle of cell (2,1,0) and `~2.5` is its edge. A
  minecart summoned on an edge is off its rail. Selectors can't take `x=~`; use
  `positioned ... dx=`/`distance=`. The clear kills entities in the plot box, 2 blocks
  around it and up to the build height; kill anything that flies further yourself.
- Set container contents with `insert` or `data merge block` (or put them in the state):
  `item replace` into a hopper or decorated pot doesn't update a comparator reading it.
- Keep each `run`/`log` under ~1 KB (RCON drops a command over 1400 bytes; lint checks this); summon empty and fill with
  `item replace entity`.
- Inputs in one `drive` apply in the order listed, which decides same-tick scheduling races,
  so a race between two inputs is tested one order at a time (one test per order). Two
  `drive` steps with no `wait` between them happen in the same tick: a 0-tick pulse.
- Drivers are always strength-15 redstone blocks. For another strength, build the source
  as a fixture (a hopper or composter read by a comparator, marked `fixture: true`) and set
  it with `run: data merge block ...` or `run: setblock ...`. A redstone block also powers
  comparator sides and lamps beside it, which a hard-powered block in the same place would
  not; where the interface matters, put the real feed block between the driver and the
  design.
- Entities summoned by `run` don't count for the `uses_entities` trait; list them in
  `entities:` to claim it.
- What a named cell reads (`expect`, truth tables, traces): 1 when the property below is
  true, and analog blocks their 0-15 `power` (any value above 0 counts as 1 in `expect`).
  Waxed and oxidised copper variants and every wood of door/trapdoor/gate are included.

  | Blocks | Reads |
  |---|---|
  | redstone_wire, daylight_detector, target, sculk_sensor, calibrated_sculk_sensor, light/heavy weighted pressure plates | `power` 0-15 |
  | redstone_torch, redstone_wall_torch, redstone_lamp, copper_bulb | `lit` |
  | repeater, comparator, observer, lever, buttons, other pressure plates, powered_rail, activator_rail, detector_rail, note_block, lectern, lightning_rod, tripwire, tripwire_hook | `powered` |
  | piston, sticky_piston | `extended` (a retracting base is a moving_piston and reads 0) |
  | trapdoors, doors, fence gates | `open` |
  | dispenser, dropper, crafter | `triggered` |
  | hopper | 1 when locked: reads `enabled=false` |

  Anything else (and a cell that starts as air) needs a `check:` step.
- `level: {cmp: 7}` fails unless each cell's exact strength (0-15) matches, and reports the
  measured values. It reads a comparator's output (its `OutputSignal`, not just `powered`),
  or the `power` of dust and the analog blocks above; lint rejects it on any other cell.
  `try --trace` also records comparator outputs, and `look trace <spec> "<test>" --levels`
  shows them.
- Entities: `entities: [{type: minecart, pos: [2.0, 1.0, 0.0], nbt: '{...}'}]`. `pos` is
  relative to the centre of the origin cell, because the build runs under
  `execute positioned <int>`, which centres x and z: `[2.0, 1.0, 0.0]` is the middle of
  cell (2,1,0). Hanging entities (item frames) need integer x and z; `.5` lands in the next
  cell. Block-entity NBT goes in the state:
  `'hopper[facing=down]{Items:[{id:"minecraft:redstone",count:1}]}'`.

## How a truth table is measured

Rows run in order and end by repeating the first (so the design must reset); `reset: false`
skips that replay, e.g. for a toggle sequence of odd length. For each row the inputs change
together, and the delay is the ticks until every output matches; the test's `delay` is the
worst row. Then it holds for the settle time and checks the outputs again. A redstone tick
is 2 game ticks; delays here are game ticks.

- Each output's edge in a row is `rise` or `fall` from the value it ended the previous row
  on (for the first row, its value after loading); an output that doesn't change has no
  edge. Its delay is the tick it first matches. `delays: {cout: 2, sum: {rise: 4, fall: 2}}`
  asserts the exact worst case per edge (a plain number: over both edges), `max_delays`
  bounds them, and either fails if the table never makes that edge. `try` prints the
  measured worst cases on PASS: `PASS logic (delay 4; sum rise 4 fall 2, cout rise 2 fall 2)`.
- `x` in an output column: that output isn't checked in that row. It has no edge there, and
  the next row's edge is from whatever it held.
- `glitch_free: true` reads every tick of the settle and hold: an output that leaves its
  expected value after first matching fails, and so does one the row doesn't change that
  moves at all. Without it only the end of the hold is checked.
- The `instant` trait needs a test with `delay: 0`; zeros in `delays` don't count.
- `tile: [dx, dy, dz]` on a truth-table test builds a second copy at that offset (lint
  fails if the copies put different blocks in one cell or a copy's input cell is not air)
  and drives it one row ahead: copy A gets row i while copy B gets row i+1 (wrapping), and
  both copies' outputs are checked on every row. B's cells appear as `B.<name>` in traces
  and failures; delays are the worst over both copies. Add it as a separate test so the
  single-copy delay stays measured on its own. `library/and/and_torch_1wide` has one.

## Traits

Checked ones must be true of the blocks or `try` fails: silent, lightless, pistonless,
entityless, uses_entities, flat, one_wide, instant, tileable (a `tile` test with dy 0) and
stackable (a `tile` test with dy not 0). Variants that claimed tiling before tile tests
existed are listed in `redstone/traits.UNTILED` until they gain one; add no new names
there. The rest are your claim; only claim
ultracompact/ultrafast if nothing in the family beats it (`library/INDEX.md`).

`lightless` means the design queues no light checks: no block in it changes light emission
or dampening, or is shape-occluding (daylight detectors, lecterns, sculk, pistons), when it
changes state. Dust, repeaters and comparators are fine; see `redstone/traits.LIGHT`.
`silent` is about normal operation; the fizz of a torch burning out doesn't count. Sizes
and `one_wide` leave out driver cells, so they assume inputs arrive from outside the
footprint; when an input cell sits inside it, say so in the description.

## Traps

- Repeater/comparator/observer `facing=F`: input from side F, output on the opposite side.
  Wall torch `facing=F`: hangs on the block on the opposite side of F.
- Input cells must stay air, with their neighbours what the redstone block should power.
- Torches burn out after 8 toggles in 60 ticks; long truth tables on one torch can hit it.
- A block powered only by dust (weakly) turns off torches and drives repeaters and lamps
  beside it, but not dust. Hard power (a repeater into it, a torch under it) drives dust too.
- The harness gives every block an update after placing, so a design can't rely on being
  placed in a stale state.
- Placement order is visible to some blocks: the build `setblock`s every block in (y, x, z)
  order, then clones each onto itself. An observer fires once on placement (place it as
  `observer[powered=true]` if that pulse matters); copper bulbs and hoppers react to the
  order (give a bulb its settled `lit` state; give a hopper that must not move items while
  loading `{TransferCooldown:20}`). A player building by hand may need another order; say
  so in the description.
- A bare `redstone_wire` placed by setblock is the dot state and powers no neighbour. Give
  isolated dust its connections: `redstone_wire[north=side,south=side,east=side,west=side]`.
- Changing an item frame's rotation with `data merge entity` doesn't update a comparator
  reading it; follow it with a `run: setblock` of a block beside that comparator.
- `composter[level=7]` ripens to 8 on its own; use level 6 or lower for a constant strength.
- Not possible with commands: player vibrations (use entities), a player's click on a
  repeater, comparator, door and the like (use `run: setblock` with the full new state;
  `use` covers levers and buttons), and container contents as a named cell in `expect` or a
  truth table (read them with `expect_items`, `log` or `check`).
- Gamerules in 26.3 are snake_case (`advance_time`).
- Inline predicates in 26.3 dispatch on `type:`, not `condition:`:
  `check: positioned ~2 ~1 ~1 unless predicate {type:"location_check",predicate:{light:{light:{min:1}}}}`.
  `condition:` fails to parse ("No key type").
- To assert that a command is refused (a `run` fails on the error reply), fork it and store
  its success: `run: execute as @e[type=X,distance=..1,limit=1] store success score r obj run damage @s ...`
  then `check: if score r obj matches 0`. A forked command's error is silent and stores 0; if
  nothing matched, the score stays unset and the check fails. `library/mechanics/sulfur_cube_tnt_priming`.
- YAML: quote anything starting with `#` (block tags, `#fake` score holders) or it becomes a
  comment, and don't name cells `on`/`off`/`yes`/`no` (they load as booleans).
- A bad block id in the palette fails as `Unknown function redstone_ai:build`; check ids
  (e.g. `waxed_copper_block`).
- A named cell reads only the blocks in the table above; anything else, and cells that
  start as air, need `check: if block ... [prop=value]`.
