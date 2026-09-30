# Light updates in 26.3: which redstone activity queues light work

Source: decompiled 26.3 in `mc-src`. "Source" = read in code; "inferred" = reasoned, not run.

## 1. The rule (source)

`LevelChunk.setBlockState` (chunk/LevelChunk.java:296-302):

```java
if (LightEngine.hasDifferentLightProperties(oldState, state)) {
   profiler.push("updateSkyLightSources"); this.skyLightSources.update(...);
   profiler.popPush("queueCheckLight");    lightEngine.checkBlock(pos);
```

`LightEngine.hasDifferentLightProperties` (lighting/LightEngine.java:41-48): true iff
`new != old` AND (`dampening differs` OR `emission differs` OR `new.useShapeForLightOcclusion()` OR `old.useShapeForLightOcclusion()`).
(LevelChunk returns early when old == new, so setting the identical state never gets here.)

Dampening is cached per state (BlockBehaviour.java:294-299, 396-398, 515-530):
- 15 if `solidRender` = `canOcclude` and occlusion shape (default = outline `getShape`) is a full cube;
- else 0 if `propagatesSkylightDown` = outline shape not a full cube AND fluid state empty;
- else 1. Overrides only in TintedGlass, Leaves (getLightDampening) and a handful of propagatesSkylightDown overrides (glass, vegetation, walls/panes/fences (CrossCollision), liquids, barrier, light, shulker box...), none redstone-driven.

So a state change (or a block swap) queues a light check only if: emission changes, OR the shape toggles between full and not-full (or waterlogged toggles), OR the block uses shape for light occlusion.

Only other light-queueing paths outside `lighting/`: `LevelChunk:292 updateSectionStatus` (a whole 16^3 section becoming all-air / not all-air, not redstone-relevant), `ProtoChunk:137/142` (worldgen), chunk load/save. Nothing in redstone code calls the light engine directly.

## 2. Blocks whose changes queue a light check

(a) Emission depends on state (Blocks.java `litBlockEmission` at 5587, and lambdas):
redstone_torch / redstone_wall_torch (LIT: 7/0, 2048/2053), redstone_lamp (15/0, 2707), redstone_ore / deepslate_redstone_ore (9/0, 2037),
copper_bulb (all oxidation/waxed variants, 15/12/8/4 vs 0, 5166), furnace/smoker/blast_furnace (13), campfire (15) / soul_campfire (10),
candles and candle_cake (3*candles), respawn_anchor (charges), sea_pickle, trial_spawner, vault, light (level), glow_lichen, cave_vines (berries).
Sculk sensors have constant `lightLevel(state -> 1)` (5032): emission does NOT change, but see (b).

(b) `useShapeForLightOcclusion` true, so EVERY state change queues a check:
daylight_detector (POWER, INVERTED), lectern (POWERED, HAS_BOOK), sculk_sensor + calibrated_sculk_sensor (PHASE, POWER),
sculk_shrieker (SHRIEKING), piston/sticky_piston when EXTENDED=true (so extend and retract both qualify), piston_head (always),
*_shelf (POWERED, SIDE_CHAIN_PART; 26.x shelves are redstone-readable), stairs (SHAPE), non-double slabs, farmland (MOISTURE), dirt_path, snow (LAYERS),
end_portal_frame, enchanting_table, stonecutter. Static stairs/slabs cost nothing; they only matter if their state changes.

(c) Dampening varies between states: checked every redstone component; none of the doors, trapdoors, fence gates, rails, plates, buttons,
levers, tripwire, cake, composter (level 8 reuses the level-7 shape, not full; ComposterBlock:54-59) ever reaches a full outline shape,
and none change fluid state during redstone activity. Only piston base (full when retracted, `PistonBaseBlock:59-61`) varies, already in (b).
Waterlogged toggles (bucket/dispenser) would change 0 <-> 1.

(d) Block swaps (checked per swap with old/new block's properties):
- piston push/pull: moved block -> moving_piston (dampening 0: `MovingPistonBlock.getShape` = empty, emission 0) -> block again.
  Any opaque block (15), lit lamp, slime/honey (1) etc. queues a check both ways; air <-> moving_piston or glass <-> moving_piston does NOT
  (both 0/0, no useShape). piston_head placement always queues (useShape).
- dispenser placing blocks (water/lava/powder snow buckets, shulker box, carved pumpkin, skulls, fire via flint and steel/fire charge, bone-meal growth);
  TNT ignition (tnt 15 -> air 0); falling blocks (sand/gravel/concrete_powder/anvil... 15 -> air); explosions; any block break/place.
- dropper, hopper item moves, dispensing entities (arrows, TNT entity) do not change blocks, so no check.

### Named components, explicit

| block | queues light check on state change? | why (source) |
|---|---|---|
| redstone_wire | **NO** | no lightLevel (Blocks:1337), no useShape override, shape (RedStoneWireBlock:86-103) = dot 10x10x1 plus floor arms (y 0-1) plus UP walls 1 px thick at a face; the point (8,8,8) is outside every piece, so never a full cube in any of its 1296 states; no fluid; so dampening 0 for all states, emission 0 |
| redstone_torch / wall_torch | **YES** | LIT changes emission 7 <-> 0 |
| repeater | **NO** | DiodeBlock shape 16x2x16 slab (DiodeBlock:28), no lightLevel (Blocks:2239): dampening 0, emission 0 in all states (POWERED, LOCKED, DELAY) |
| comparator | **NO** | same DiodeBlock shape, no lightLevel (Blocks:2958) |
| observer | NO | full cube all states: dampening 15 constant, emission 0 |
| target | NO | full cube, emission 0 |
| hopper | NO | noOcclusion, non-full shape (facing only): dampening 0 constant |
| dropper / dispenser (TRIGGERED) | NO for the state change; YES if the dispenser places or removes a block (d) | full cube constant |
| note_block | NO | full cube constant |
| lever, buttons, pressure plates, tripwire, tripwire_hook, rails (all kinds) | NO | shapes all small boxes (LeverBlock:46, ButtonBlock:54-56, BasePressurePlateBlock:25-26, TripWireBlock:36-37, TripWireHookBlock:40, BaseRailBlock:28-29 flat 2 px / slope 8 px), emission 0; rails' WATERLOGGED is not touched by redstone |
| doors, trapdoors, fence gates | NO | Door/TrapDoor SHAPES = boxZ(16,13,16), 3 px thick (DoorBlock:47, TrapDoorBlock:43); FenceGate SHAPES = cube(16,16,4) (FenceGateBlock:42); never full |
| lectern | **YES** | useShape = true (LecternBlock:69); a player page turn (LecternBlockEntity.setPage) sets POWERED true then false 2 gt later (LecternBlock:148-166); `data merge {Page:n}` does not (section 4) |
| daylight_detector | **YES** | useShape = true (DaylightDetectorBlock:43); POWER written when it changes (line 60-61) |
| sculk_sensor / calibrated | **YES** | useShape = true (SculkSensorBlock:277) (emission is a constant 1) |
| sculk_shrieker | YES | useShape = true |
| copper_bulb (all variants) | **YES** on LIT change; NO when only POWERED changes | litBlockEmission; full cube |
| crafter | NO | full cube, no emission |
| redstone_lamp | **YES** | LIT 15 <-> 0 |
| piston / sticky_piston / piston_head / moving_piston | **YES** | useShape when extended, head always, moved blocks swap with moving_piston (d) |
| shelf | YES | useShape = true (ShelfBlock:75), POWERED |

The user's claim that dust queues light updates is contradicted by the 26.3 source; torches do queue them.
Only an empirical count (section 3) can settle it beyond the source reading.

## 3. Verifying on the server

`debug start/stop` is NOT usable: in 26.3 it is `MinecraftServer.TimeProfiler` (MinecraftServer:2232-2257), whose results return an empty `getTimes` and `saveResults` = false; the command only prints seconds, ticks and TPS (DebugCommand:71-97). No sections, no file (source).

Use `perf start` / `perf stop` (PerfCommand, dedicated server only):
- The recorder's `ActiveProfiler` wraps every server-loop iteration (MinecraftServer:738 `Profiler.use(createProfiler())`), including the command-execution wait (`nextTickWait`), frozen or not. That `tick step` ticks are captured is inferred from the loop structure, not run.
- Hard limit: 10 s of wall time (`ActiveMetricsRecorder.PROFILING_MAX_DURATION_SECONDS = 10`); `perf stop` ends it early. Longer tests need several windows.
- Output: `server/debug/profiling/<name>.zip` containing `profiling.txt` (MetricsPersister:29, 86). Lines look like `[depth] |   name(count/countPerTick) - pct%/pct%`. `queueCheckLight(N/..)` = N light checks on that path. It always has a sibling `updateSkyLightSources` with the same count, so its parent is always printed (the dump only descends into nodes with 2+ entries, FilledProfileResults:231-262). The zip is written async (ioPool): poll for it.
- Count ALL paths, not only level-tick paths. RCON commands run through `executeBlocking` (DedicatedServer:714-717) and their synchronous neighbour-update chains run inside the command: a lamp turned on by a driver lights immediately (`RedstoneLampBlock.neighborChanged` sets LIT on at once, only OFF is scheduled, lines 29-41); a copper bulb flips LIT on the spot. A tick-only filter would miss exactly those.
- Harness noise to subtract: each driver change `setblock redstone_block` <-> `air` is one light check (redstone_block full cube, dampening 15 vs 0). Lever/button toggles add none (thin shapes; the self-`clone` of the support block hits `oldState == state` and returns early). `run:` steps that setblock/fill count too. Clean way: run the identical step sequence twice, once on the design and once with the design blocks removed (drivers only), and assert equal counts; or subtract the known number of driver changes.

Harness check (proposal): for a spec claiming lightless, after load and settle, `perf start`, run the test steps (fast, under 10 s wall), `perf stop`, poll for the zip, sum every `queueCheckLight(N/` in `profiling.txt`, subtract the control, assert 0. The profile is server-wide, so the server must be otherwise idle (satellites, one plot each, suit this).
Sanity spec for `library/mechanics/`: lever -> torch must give a count > 0; lever -> 15 dust, and lever -> repeater line, must give 0. That spec also settles the "dust queues light updates" question empirically.
JFR (`jfr start`) has no light-engine event and its method sampling cannot count calls exactly, so it is not a substitute.

A likely source of the belief that dust causes light updates: any visible state change (dust power level) makes the client re-mesh the chunk section and sends a block update packet; that is render/network work, not a light check (inferred, not traced in the source).

Static checker alternative (no server): flag a lightless spec if its design contains a block from section 2 (a) or (b) that can change state, or pistons. Dispensers are a designer's claim (depends on contents). Static stairs/slabs are harmless.

## 4. Library audit

181 specs claim `lightless` (loaded with redstone.library + fileformat.load, block names from `traits.block_names`, audit script run then deleted). All pass the current checker.
Blocks used in them: activator/detector/powered rail, rail, barrel, cake, chest, chiseled_bookshelf, comparator, composter, black/white concrete, daylight_detector, decorated_pot, dispenser, dropper, glass, heavy/light weighted pressure plates, hopper, iron_trapdoor, lectern, note_block, oak/stone buttons, observer, redstone_block, redstone_wire, repeater, smooth_stone, stone, target, tripwire(+hook), water_cauldron, waxed_copper_block.

Specs containing a block from the section 2 list:
- `library/mechanics/inverted_daylight_detector_constant` - daylight_detector. VIOLATES: its POWER changes during the tests (noon/midnight, a test sets power=7 and it recomputes at game time %20, the unroofed control drops to 0). Each change queues a check (useShape).
- `library/mechanics/lectern_page_signal_and_pulse` and `library/signal_strength/analog_const_lectern` - lectern. NOT violated by the tests as written: they turn pages with `data merge block ... {Page:n}`, which goes BlockDataAccessor.setData (lines 47-55) -> `loadAdditional` sets `this.page` directly (LecternBlockEntity:196-200) and never calls `signalPageChange`, so the block state never changes. A survival player turning pages goes through `setPage` (LecternBlockEntity:159-164) -> `signalPageChange` -> POWERED true, then false 2 gt later: two light checks per page turn. analog_const_lectern is marketed as survival page-turning, so in real use it is not lightless.
- `library/mechanics/arrow_holds_wooden_button` - dispenser. Not a violation: it fires arrows (entities), places no block; TRIGGERED is on a full cube.
All other 177 contain only blocks that never queue light checks on their own state changes.

Descriptions mentioning "lightless": every spec with the trait whose description uses the word is consistent. Those explicitly saying "no light update(s)": and_comparator_lightless, seg_dec_decimal, seg_floor_dust, tff_lightless_lock: correct per source.
Specs without the trait whose description says "lightless" (all read, all consistent: they either point to a lightless alternative or disclaim it): and_torch_3input, and_torch_flat, clock_hopper_piston, clock_torch_repeater, latch, delay_torch_tower, add_full_piston_instant(+_x2) ("not lightless (a piston moves)"), or_nor_torch_compact, or_nor_wide_torch, rs_torch_nor, tff_copper_bulb ("neither silent nor lightless"), tff_torch_repeater, vwire_observer_bulb_down ("the shaft itself is lightless"), and powered_rail_chain_limit_isolation ("a lightless 1-wide bus"; correct: rails queue no light checks; it lacks the trait).

## Proposed checker set (for traits.py, not applied)

LIGHT = torches, lamp, redstone ores, sculk_sensor, calibrated_sculk_sensor, sculk_shrieker, daylight_detector, lectern, piston, sticky_piston, piston_head, moving_piston; suffixes copper_bulb, _shelf.
Definition text: "no light updates while it runs: no block changes state in a way the light engine re-checks (torches, lamps, bulbs, daylight detectors, lecterns, sculk, pistons, moving blocks)". Dispensers are a designer's claim (depends on contents).
