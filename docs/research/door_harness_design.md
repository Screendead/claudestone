# Door test harness: design (not implemented)

Scope: timing, seamless, volume and robustness checks for Squid-ruleset piston doors on the existing
tick-stepped RCON harness. Nothing here has been run. Labels: [S: file:line] = read in that source,
[W: url] = read on the web, [I] = inferred, followed by the test that would settle it.

Paths used below:
- `RULES` = squid_repo/reference/Door_Rules.md (the full Squid rules text; it supersedes the
  distilled squid_rules.md, and its seamless tier table lost its check marks, lines 131-136).
- `MC` = mc-src/net/minecraft (Vineflower decompile of 26.3, see findings-inputs.md:2).
- `H` = redstone/harness.py, `SP` = redstone/spec.py, `FF` = redstone/fileformat.py, `B` = redstone/build.py.
- `TODO` = harness_todo.md (items are cited as TODO#n, n = line number).

## 0. Facts everything below rests on

Tick phases in one server tick, in order:
1. Queued player packets run first (`packetProcessor.processQueuedPackets()`), then `tickServer`
   [S: MC/server/MinecraftServer.java:985-991].
2. `tickChildren` runs command functions, then `level.tick` [S: MinecraftServer.java:1067-1094].
3. Inside `ServerLevel.tick`, the order is: `tickTime()` (gametime += 1), then blockTicks (scheduled ticks:
   repeaters, torches, observers, button releases), fluidTicks, raids, chunkSource (random ticks), then
   blockEvents (piston starts), then entities, then blockEntities (moving_piston progress)
   [S: MC/server/level/ServerLevel.java:386-445]. When the tick is frozen, `runs` is false and every one of
   these phases except chunkSource is skipped [S: ServerLevel.java:364,386,391,408].
4. RCON commands run as main-thread tasks inside `waitUntilNextTick`, after `tickServer` returns
   [S: MinecraftServer.java:745,838-839; MC/server/dedicated/DedicatedServer.java:714-717].

Consequence [I, from 1-4]: a player's click and an RCON command both execute between ticks, while
gametime still holds the value of the tick that just ended. Nothing in the world runs between those two
points, so for the world they are the same phase. Settled by task T1.

MC-172213 is titled "Redstone components lose 1 tick of delay when (de-)activated by a player input". Per
the report, player packets are handled before world time is incremented, so ticks scheduled by player
actions skip one tick of delay. The report lists command execution among those player actions. Open,
affects 1.15.2-1.20.6 [W: https://mojira.dev/MC-172213]. This matches the source: `createTick` schedules
at `getGameTime() + delay` [S: MC/world/level/LevelAccessor.java:31-37], and `blockEvent` only queues. The
queue runs in the next tick's blockEvents phase [S: ServerLevel.java:1260-1270].

Piston motion lifecycle [S: MC/world/level/block/piston/PistonMovingBlockEntity.java:291-324,338-344;
MC/world/level/Level.java:523-544]:
- In tick s's blockEvents phase a `moving_piston` block is created. Its ticker is added directly to the
  ticking list (it was not created during a block-entity tick), so it ticks in tick s's blockEntities
  phase: progressO = 0, progress = 0.5.
- Tick s+1: progressO = 0.5, progress = 1.0.
- Tick s+2: progressO >= 1, so the moved block is placed in place of the moving_piston.
- The saved NBT `progress` is **progressO**, not progress. The other keys are `blockState` (the moved
  state), `facing`, `extending` and `source`.
- A retraction event that meets a still-moving block calls finalTick and places the block in the same
  tick. This is the 0-tick "drop" (`finalTick`, PistonMovingBlockEntity.java:259-284).

This gives observed end ticks of s+2 for a standard move, s+p for a p-tick pulse and s for an instant
retraction. These are exactly Squid's end-time formulas [S: RULES:622-630]. [I] Settled by task T2.

Block events are broadcast to clients [S: ServerLevel.java:1270-1281], so a client may animate a piston
event that the server started and finished inside one tick. A between-ticks observer never sees such an
event (see 2.4).

---
## 1. Tick zero

**Which input the harness produces now.** `drive()` places or removes a redstone block over RCON
[S: H:270-277]. `use()` does setblock plus a clone of the support block [S: H:302-332]. Both are
player-phase inputs (section 0). None of the existing tests has repeater input in Squid's sense.

**Squid's definition.** Speeds are timed with repeater input [S: RULES:622]. Repeater input means the
input block is powered "from the position of the input device" [S: RULES:484]. Time runs from the input
to the end of the last movement [S: RULES:642-650].

**Design.** Build a repeater-input fixture (T7):
- Put a real `repeater[delay=1]` in the device cell, facing so that its output enters the input block.
  For a floor or ceiling device, which a repeater cannot occupy, use a spec-declared horizontal repeater
  cell that points into the input block.
- Put a harness `drive` cell behind the repeater, outside the build.
- Drive at gametime G. The repeater's tick is scheduled for G+2 and fires in blockTicks of the tick whose
  gametime is G+2. That repeater output change is the input.
- **Tick 0 = the tick in which the fixture repeater's output changes.** The harness detects it and never
  computes it: step one tick at a time, probe the repeater's `powered`, and take the first end-of-tick
  observation where it has flipped as the observation of tick 0.
- Every later observation O(t) is the world after tick t's blockEntities phase.

**Check against Squid's examples.**
- "0 gt close": the fixture repeater powers a piston in tick 0's blockTicks, and its block event runs in
  tick 0's blockEvents phase. With a 0-tick drop, O(0) already shows the closed pattern. Close time is 0.
- "2 gt open": a standard move starting in tick 0 is observed finished at O(2) (section 0). Open time is 2.

**For player input.** Tick 0 is the first tick after the command (`use`). That is when its piston block
events run. Scheduled delays counted from that tick are one tick shorter, which is MC-172213. Player-input
runs are pass/fail robustness checks only and never produce the claimed times.

**Can the harness read the world in the input tick?**
- Yes, at the end of it. After `step(1)` returns, gametime has advanced once and nothing runs until the
  next step [S: H:199-205; findings-inputs.md:47-48].
- It can never read between phases of one tick, for example after blockTicks but before blockEvents.
- No change is needed for Squid timing, because Squid times are whole ticks computed from movement start
  ticks, and those are observable (section 0).
- What is lost is whatever exists only inside a tick (see 2.4).
- The one required change: the door runner must step and probe every tick through the whole operation.
  `Recorder.wait` already steps one tick at a time when tracing [S: SP:28-37]. TODO#15 ("trace records
  every tick") covers the trace side.

## 2. Hallway observation per tick

**2.1 What the current probe reads.** `probe_functions` covers only build cells whose block has a signal
property: dust power, lit, or powered [S: H:34-43,52-64]. It writes one integer per cell. It has no block
ids, no air cells, nothing for pistons (`signal_property` returns None for piston, sticky_piston,
moving_piston and piston_head), no NBT and no entities. `parse_state` drops NBT [S: H:23-27].

Related doc gap: AUTHORING.md:77-78 says a piston cell reads 1 when powered. That is not true of the code
[S: H:41]. Fix the doc in T18.

**2.2 New hallway probe (T3).**
- Region V = hallway cells ∪ visible surface cells. Default: the hallway plus each 6-neighbour cell of a
  hallway cell that is not itself hallway. Glass types override this with a spec-declared `visible` list.
- One generated function, the same chunking as `PROBE_CHUNK`. For each cell i in V, the first matching
  line wins and writes `h.c{i}`:
  - `if block <p> #minecraft:air` → 0 (air)
  - `if block <p> #redstone_ai:door_material` → 1 (door block; the spec's door blocks as a generated tag)
  - `if block <p> #redstone_ai:surface_material` → 2 (hallway composition: walls, floor, ceiling)
  - `if block <p> minecraft:moving_piston run data modify storage redstone_ai:probe m.c{i} set from block <p>`
    → 3, plus the NBT: `blockState`, `progress` (= progressO), `extending`, `source`, `facing`
  - `if block <p> minecraft:piston_head` → 4
  - otherwise → 9 (other, which is circuitry)
- Generate the two tags into the data pack from the spec (`write_datapack` already writes the pack
  [S: B:72-84]; it needs a `tags/block` directory).
- Whether `#minecraft:air` covers air, cave_air and void_air is [I]. Settle with a one-line check in T3.

**2.3 Classification per cell per tick.**
- Door block present: code 1, or code 3 whose `blockState` is door material.
- Air: code 0.
- Visible movement at tick t: any cell of V has code 3 or 4, or any cell's code or NBT differs between
  O(t-1) and O(t). The last of these differences is the finalize step s+2, which also covers z-fighting
  swaps.
- Circuitry visible: any cell of V has code 9, code 4, or code 3 whose `blockState` is not door or surface
  material, or that has `source: true` (a piston head or base in motion).

Entities in V:
- Use `execute if entity @e[type=!player,tag=!rig_dummy,x=..,dx=..]` per hallway box, and
  `data modify storage ... append from entity @s {id, Pos, Invisible}` for detail.
- A selector volume `dx` matching when the entity hitbox intersects the volume is [I]. Settle by summoning
  a minecart half a block outside a 1-cell box in T3.
- Invisible entities are reported but are not counted as "visible" without a ruling [I]. SUPER needs "no
  entities visible" [S: RULES:128].

**2.4 Gap: intra-tick states.** A block that exists only inside one tick, such as a head extended and
retracted by two block events in the same tick, is never observed. The client does receive both block
event packets [S: ServerLevel.java:1270-1281].
- Whether that is visible (renders or z-fights) is [I].
- The only settle is a real client: the user watches the showroom with `tick rate 1`. Add it as a manual
  checklist item.
- For volume, count such positions conservatively: add every piston's head cell to the occupancy set if
  that piston ever fires an event. Detect this as: the base's `extended` changed, or a moving_piston with
  `source: true` was seen at the base or head.

## 3. The four timings and reset times

Inputs: the observation series O(0..W) for one operation, where W = the operation's quiescence tick
(below), plus O(-1), the stable state before the input.

- **Pattern.** OpenPattern: every hallway cell is air (or the type's open composition), and surfaces are
  unchanged. ClosedPattern: every frame cell has code 1 and the other hallway cells are air
  [S: RULES:99,692].
- **Quiescence.** W = the first tick after which the full probe is either static for Q = 40 ticks, or
  periodic with period ≤ 64 for 3 periods (a stable state may "return at regular intervals"
  [S: RULES:696]). If there is none by 600 ticks, fail: the time is unbounded [S: RULES:503].

Observed times (from repeater-input runs only):
1. OPENING TIME: the smallest t such that O(t') matches OpenPattern for every t' in [t, W]
   [S: RULES:642].
2. OPENING VISIBLE TIME: the largest t ≤ W at which visible movement occurs (2.3).
   - With a permanent clock, use the tick the stable state is reached [S: RULES:644-646].
   - A door whose clock moves something visible forever therefore has visible time = W.
3. CLOSING TIME: the largest t at which a hallway cell changes to or from door material, including
   moving_piston cells carrying door material [S: RULES:648]. Cross-check that ClosedPattern holds for
   every t' in [that t, W].
4. CLOSING VISIBLE TIME: as in 2, for the closing operation.

Formula cross-check (T9):
- For every hallway motion, record the start tick s (the first sighting of the moving_piston with
  progress 0.0; for an instant change with no moving_piston seen, s = t). Compute end = s + 2 (standard),
  s + pulse (cut short), or s (instant) [S: RULES:624-630].
- The times from these formula ends must equal the observed ones.
- Any mismatch fails the run as "timing model disagreement". It is not averaged away.
- A range of speeds takes the slowest [S: RULES:632-634]. So the claimed time is the maximum over every
  run in the test matrix (origins, rotations, cycles), per Notes 7.3 [S: RULES:768-769].

**Reset times (T11).** Opening reset R_o = k* − T_open_visible [S: RULES:652-654], where k* is the
smallest input offset k (ticks after the opening input's tick 0) such that **every** k' in [k, K_max]
passes. The rule says "at any time thereafter" [S: RULES:652].

A trial at offset k:
- Fresh `load` (clear, flush, build), stable closed state.
- Repeater-input open at tick 0, repeater-input close at tick k.
- Pass when all of these hold:
  - The close meets the claimed close and close-visible times, measured from its own tick 0.
  - Seamless holds throughout.
  - The door reaches ClosedPattern and quiescence.
  - One further nominal open→close cycle meets every claim.

Search bounds:
- Scan k from K_min up to K_max = W_open + Q. From K_max on, the door is in its stable state and every
  offset is the same trial.
- K_min = 2 for a lever with a delay-1 repeater fixture: a repeater stretches shorter pulses to its
  delay [I]; settle in T1.
- For a button, K_min = the button's press length, because the device can't be pressed again until
  release (stone 20, wooden 30 [S: H:18; findings-inputs.md:21]).
- Scan linearly; do not bisect. Pass/fail is not known to be monotonic [I].
- Record the whole pass/fail vector.

A negative R is allowed [S: RULES:654]. Closing reset is the mirror image. Cost: about (K_max − K_min)
fresh loads per direction, each costing FLUSH_TICKS = 170 ticks at warp [S: H:17,229-233].

Button doors [I]: timing with repeater input probably means a repeater pulse the length of the button's
press. The rules don't say. Ask Squid (T0).

## 4. Cumulative bounding box (volume)

Rule [S: RULES:571-583]: W×H×D of the circuitry, "cumulatively measured across every closing/opening
operation and opened/closed state", counting both blocks and entities. Exclusions:
- (1) door, outer-surface and hallway blocks that fit the type's composition, the door frame, and the
  input device;
- (2) blocks or entities inside the hallway except in the open state;
- (3) entities not required to extend outside the wiring;
- (4) entity hitbox parts that only occupy a block at a float position.

Circuitry ignores door, outer-surface and hallway blocks that fit the type [S: RULES:708].

Computation (T4, T5, T12). The union is kept in storage, so it costs no RCON reads until the end.
- Region D = the build's bbox ∪ the hallway boxes, dilated by m = 2 and clamped to the plot. Cells are
  classified statically:
  - E_static: frame cells and the input device cell;
  - Hall: hallway cells;
  - Surf: spec-declared hallway surface and outer-surface cells;
  - Shell: D's outermost layer.
- Each tick, one generated function writes flags with `data modify storage redstone_ai:occ <key>.c{i} set value 1b`.
  For each cell not in E_static:
  - Non-hallway cells: `execute unless block <p> #minecraft:air` writes `any.c{i}`, and additionally
    `unless block <p> #redstone_ai:door_material unless block <p> #redstone_ai:surface_material` writes
    `circ.c{i}`.
  - Hallway cells get the same two lines, but only in the open-state window (the runner calls a second
    function `occ_hall` only then).
- Entities each tick: `execute as @e[type=!player,tag=!rig_dummy,<D box>] run data modify storage
  redstone_ai:occ e append value {...}`, collecting id, Pos and scale where available. Hitbox size comes
  from a table generated from `EntityType` `sized(w, h)` in MC (T5), plus the baby flag.
  - Exception (4): round a hitbox that sits at a float position inward.
  - Exception (3) is the designer's claim: the spec lists entities `volume: exempt`, and the report names
    them.
- Also add the conservative piston-head cells from 2.4.
- Volume = (max − min + 1) per axis over the flagged cells and entity boxes.
  - Report V_any (all flags) and V_circ (circ flags); the claim is compared against V_circ.
  - Whether a door block retracted into the wall is excluded (the "fits the type" wording) is not clear
    from RULES:577 [I]. Show both numbers, and settle by recomputing a published record's volume (T12).
- Guard: if any Shell cell is ever flagged, fail with "grow margin". Without that, blocks could leave D
  unseen. [I] A block moved several cells by several events inside one tick could jump the shell. Margin
  2 plus the head rule makes this unlikely; the settle is T12's check against a known record.
- Which operations count: every nominal open and close run and both stable windows, with both input
  kinds. Reset trials are not included. Whether faster re-toggles must also stay inside the claimed box
  is [I]; ask Squid.

## 5. Player input vs repeater input (MC-172213)

**What differs** [W: mojira.dev/MC-172213; S: section 0]. Player input runs before the tick's gametime
increment. Repeater input runs in blockTicks after it.
- Anything the input schedules (repeater, torch, observer, comparator, dropper) fires one tick "earlier"
  relative to the tick in which the input's immediate piston block events run.
- A door can work with one input kind and fail with the other; Squid requires both [S: RULES:475-482].

**Does `use()` reproduce a player click?**
- Phase: yes [I, section 0]. An RCON setblock plus clone runs in the same between-ticks slot as a click
  packet. The bug report itself lists command execution as a player action.
- Code path: no. A real lever click is `LeverBlock.useWithoutItem → pull(state, level, pos, null)`
  [S: MC/world/level/block/LeverBlock.java:56-66]. A real button press is `press()`: setBlockAndUpdate,
  updateNeighbours, scheduleTick(ticksToStayPressed), sound, BLOCK_ACTIVATE game event
  [S: MC/world/level/block/ButtonBlock.java:70-98].
- Emulation differences are listed in findings-inputs.md:34:
  - different neighbour-update order;
  - the support block is re-set, which gives it onPlace and shape updates;
  - no sound and no game event, so sculk won't hear the click;
  - no scheduled release.

**Button release in the harness.**
- The harness releases at the player-phase slot before tick `due` [S: H:188-197].
- The real release runs in tick `due`'s blockTicks, which is repeater phase. Squid calls button
  deactivation "repeater input" [S: RULES:478].
- Emulating before `due` fires scheduled effects one tick early. Emulating after `due` starts piston
  events one tick late. Neither is exact [I, section 0].

**Exact release, proposed (T8).** `clone` copies pending scheduled ticks with their absolute trigger
time [S: MC/world/ticks/LevelTicks.java:258-271; MC/server/commands/CloneCommands.java:322]. Procedure:
1. Keep a stash button of the same block type and orientation on a plain support in an isolated stash
   cell outside the door's volume. `tickBlock` only runs a tick if the block matches its type
   [S: ServerLevel.java:823-827].
2. Press the stash button with a wind charge. That is the real `press()`, which schedules the release at
   P+20 (verified 20 gt for stone in findings-inputs.md:21). Step until the stash button reads powered at
   the end of tick P.
3. Between ticks P and P+1, run `clone S S D replace` (the door device becomes a pressed button and takes
   the pending tick at P+20), then `clone A A A replace force` (the missing update at the support block).
   This is the press, in player phase at gametime P.
4. At P+20 the real `ButtonBlock.tick` releases the door button in blockTicks: repeater phase, real code
   path.

[I] Settle with a mechanics spec: one door button pressed by (a) this method and (b) a wind charge
directly. Compare the release tick and the downstream traces. Expect the press to differ by the phase
only and the release to be identical.

**Closest honest check overall.**
- Timing and claims: repeater fixture.
- Player input, lever: `use()` for both toggles. Also a wind-charge run (exact code path, but entity
  phase). Pass requires both.
- Player input, button: the stash method.
- Wind charge caveats: it toggles anything triggerable within about 1.2 blocks, and it knocks entities
  (findings-inputs.md:20-21).
- The user clicks it in the showroom as a last manual step. A real player can't be scripted over
  commands (TODO#10).
- Sculk-dependent doors must rely on the wind-charge run, since `use()` emits no game event.

## 6. Robustness checks

- **Origins.** "NOT LOCATIONAL: functions in any given location" [S: RULES:317]. Notes 7.3 require the
  claimed speed everywhere [S: RULES:768-769].
  - Run the timing suite at origin offsets covering x mod 16 and z mod 16 ∈ {0, 5, 10, 15} (16
    combinations, so chunk borders fall at different places), plus y offsets across a section boundary.
  - Where location dependence comes from is [I]: block-entity ticker order is list-insertion order
    [S: Level.java:523-544], so it depends on the order chunks load. Sampling is evidence, not proof;
    report it as "tested at N offsets".
  - The plot is 48×32×48 [CLAUDE.md]; a big door uses the main plot.
- **Rotations.** Add `Build.rotated(quarter_turns)`: positions plus state properties (facing, axis,
  rotation 0-15, north/east/south/west connections, rail shape, stairs facing), entity Pos and Rotation.
  [I] Verify each rotation against the game's own `BlockState.rotate`:
  1. Save the placed build to a structure (structure block, SAVE).
  2. `place template redstone_ai:<spec> <pos> clockwise_90 none 1.0 0 strict` beside the
     Python-rotated build. `strict` skips the update pass (findings-inputs.md:41-43).
  3. Compare with `execute if blocks … all`.
  Squid's DIRECTIONAL covers the 4 cardinal facings [S: RULES:317]; mirroring is not required.
- **Player in hallway.** Rule 3.8: player movement in a stable state must not break it
  [S: RULES:526-528].
  - Use a `mannequin`. It extends Avatar, which extends LivingEntity, and it has a player-shaped body and
    an `immovable` flag [S: MC/world/entity/decoration/Mannequin.java:28,93,150; MC/world/entity/Avatar.java:13].
  - Stone pressure plates detect LivingEntity [S: MC/world/level/block/PressurePlateBlock.java:35-36].
  - Test: in each stable state, place the mannequin at every standing position in the hallway for 40
    ticks. Then `tp` it one cell per tick along the hallway. The stable state must hold and O must not
    change.
  - Not covered: `instanceof Player` checks, step vibrations (tp emits a teleport game event, not steps),
    and block interaction. That is a gap, closed only by the user walking through.
- **Reload.** "Wiring that breaks upon reloading the chunks" [S: RULES:498].
  - On the satellite, in each stable state: `forceload remove` the plot, poll `execute if loaded` until
    false, `forceload add`, then `wait_loaded` [S: H:113-120]. Then run a full nominal cycle and require
    identical timings.
  - [I] Chunks unload while ticks are frozen: the chunkSource tick is not gated on `runs`
    (ServerLevel.java:405). Settle in T16; if they don't, step ticks while waiting.
  - Also once per candidate: `save-all flush`, then a satellite restart. Only on a satellite the run holds
    the lock for (CLAUDE.md Servers).
- **Reliability.**
  - 100 nominal cycles, plus 20 cycles at the minimum reset offset, all with timing and seamless
    asserted every cycle. This catches torch burnout, whose memory is kept per position [S: H:14-17], and
    drift.
  - Repeat one cycle at `time set` 0, 6000, 13000 and 18000 (no time-of-day dependence
    [S: RULES:494]). Restore the gamerule and time in a teardown (TODO#14).
  - Random ticks run during steps (findings-inputs.md:46).

## 7. File format addition (T6)

A `door:` section beside `tests:`. Boxes are inclusive [[x,y,z],[x,y,z]] pairs in build coordinates.
`load` fills `Spec.door`, `dump` writes it back unchanged (the round-trip rule, CLAUDE.md), and the lint
checks it offline.

The example below only illustrates the format. It is not a working door: it has no wiring.

```yaml
name: door_format_example
description: Illustrates the door section only; not a working door.
palette:
  .: air
  Q: smooth_quartz
  D: smooth_quartz
  P: sticky_piston[facing=west]
  i: {name: input_block, block: smooth_quartz}
  l: {name: lever, block: 'lever[face=floor,facing=north]'}
layers:
  0: |
    QQQQQ
    QQQQQ
    QQQQQ
    QQQQQ
    QQQQQ
  1: |
    .Q.Q.
    .Q.Q.
    .Q.DP
    .Q.Qi
    .Q.Q.
  2: |
    .Q.Q.
    .Q.Q.
    .Q.DP
    .Q.Ql
    .Q.Q.
  3: |
    QQQQQ
    QQQQQ
    QQQQQ
    QQQQQ
    QQQQQ
door:
  hallway: [[[2, 1, 0], [2, 2, 4]]]      # cells the player walks through
  frame:   [[[2, 1, 2], [2, 2, 2]]]      # holds door blocks when closed
  front: north                           # the side "front side of closed door blocks" faces
  door_material: [smooth_quartz]         # becomes #redstone_ai:door_material
  surface_material: [smooth_quartz]      # hallway composition; #redstone_ai:surface_material
  outer_surface: [[[0, 0, 0], [4, 3, 0]]]
  visible: auto                          # hallway + 6-neighbour surfaces; or a list of boxes
  open: air                              # hallway contents when open
  closed: {frame: door}                  # frame = door material, rest of hallway air
  initial: open                          # state the build is placed in
  input:
    device: lever                        # named lever/button cell
    block: input_block                   # named input block
    repeater: {at: [4, 1, 4], facing: south}   # fixture: floor device, so a side repeater into i
  claims:                                # checked, not trusted; times in game ticks
    open: 2
    open_visible: 4
    close: 0
    close_visible: 4
    open_reset: -1
    close_reset: 0
    seamless: {front: true, opened: true, closed: true, opening: true, closing: true, entities: true}
    volume: 60
    locational: false
    directional: false
tests:
  - name: door
    door: [timing, player_input, reset, origins, rotations, mannequin, reload, cycles, daytime]
```

## Gaps needing a person or outside source

- G1: the seamless tier table's check marks are missing [S: RULES:131-136]. Read them from a screenshot
  of the Google Doc before mapping the five observed columns to SUPER/FULL/SEMI/QUART.
- G2: the rules don't say whether repeater input for a button door is a pulse of the button's length.
- G3: whether faster re-toggles count toward volume.
- G4: whether door blocks outside the hallway are excluded from volume.
- G5: intra-tick client-visible motion (2.4).
- G6: a real player in the hallway and a real click. These are manual showroom steps.

## Implementation tasks (for sonnet agents; start only after the live runs end, as with TODO)

Each task names its files and its acceptance check.
- **Offline-testable:** T3-T6, T9 (pure functions), T12 (compute part), T13 (Python part).
- **Needs a satellite:** T1, T2, T7, T8, T10, T11, T13 (verification), T14-T17.

- **T0** (person/browser): read the tier table (G1); ask Squid G2-G4. Output: a short note in the
  scratchpad.
- **T1** mechanics spec `library/mechanics/<phase>.redstone.yaml`: one piston+repeater chain driven
  (a) by `drive` and (b) through an upstream repeater. Compare tick 0 (piston start) and the downstream
  repeater tick. Expect the MC-172213 one-tick offset. Also check the repeater pulse-stretch minimum used
  for K_min.
- **T2** mechanics spec for the moving_piston lifecycle: read `progress` over three ticks for a standard
  extend and retract, a 1-gt cut extension and a 0-tick drop, using `data get block`. Expect
  0.0 → 0.5 → placed, and the finalize ticks from section 0.
- **T3** `H`: a `hallway_probe_functions(spec)` generator (section 2.2) plus tag writing in
  `write_datapack`. Unit tests on the generated text. Include the `#minecraft:air` and selector-`dx`
  checks as mechanics specs.
- **T4** `H`: occupancy functions (`occ`, `occ_hall`) with storage union and the shell guard
  (section 4). Unit tests on the generated text.
- **T5** `scripts/`: generate `redstone/entity_dims.py` from `EntityType.java sized(...)` in the
  decompile. A test that it parses at least minecart, armor_stand and mannequin.
- **T6** `FF`: load and dump the `door:` section, validate boxes against layers, and extend lint.
  Round-trip test in tests/test_generated.py style.
- **T7** `redstone/door.py` (new): the repeater fixture variant of a spec, the drive schedule and tick-0
  detection from the fixture repeater's `powered`.
- **T8** stash-clone button press/release (section 5) plus its mechanics spec against a direct wind
  charge.
- **T9** `redstone/door.py`: per-tick runner producing O(t). Pure functions for pattern, quiescence,
  the four times and the formula cross-check. Unit tests on synthetic series: instant, 1-gt pulse,
  standard, and a visible clock.
- **T10** seamless column booleans (front, opened, closed, opening, closing, entities). Map them to a
  tier only after T0.
- **T11** reset search: a linear scan with suffix-all-pass; report the vector and R for both directions.
- **T12** volume from occupancy and entities: V_any and V_circ, entity exemptions, the head-cell rule.
  Check against one published record rebuilt by hand, for example a small 2x2 seamless from
  squid_records.md, if a schematic can be had.
- **T13** `B`: `Build.rotated`. Offline tests for property tables. A satellite check against
  `place template … strict` with `execute if blocks`.
- **T14** origins sweep (16 xz offsets plus a y section offset); the reported time is the maximum.
- **T15** mannequin stable-state and walk-through test.
- **T16** chunk-reload test (verify unload happens while frozen) and a satellite restart variant.
- **T17** reliability cycles and the daytime sweep, with the gamerule/time teardown (TODO#14).
- **T18** `scripts.try` door report (one line per check with the times, the reset vectors and
  V_any/V_circ); a door section in docs/AUTHORING.md; fix the piston "powered" wording
  (AUTHORING.md:77-78).

TODO items to land first, not re-planned here:
- TODO#13 (steps fail on command errors);
- TODO#4 and TODO#12 (gametime/RCON races; #12 is DONE);
- TODO#6 (entities leaving the plot, stale entities: needed for entity volume);
- TODO#7 (wait_loaded before place: needed for reload and origins);
- TODO#15 (trace every tick plus moved blocks);
- TODO#2 (the `-k` filter);
- TODO#10 (`use` limits: document).
