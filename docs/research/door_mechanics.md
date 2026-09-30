# Piston and door mechanics from the 26.3 source

Scope: exact piston, tick-phase and redstone-component behaviour relevant to record seamless piston doors (Redstone Squid Java ruleset), read from decompiled game code. No server, RCON or pytest was touched.

Path prefixes used in citations:
- `S:` = `mc-src/net/minecraft/` (Vineflower decompile of `jarx`, the unpacked 26.3 server classes)
- `C:` = `cl/src/net/minecraft/` (Vineflower decompile of 4 classes from the 26.3 client jar, `cl/client.jar`)
- `M:` = `docs/MECHANICS.md` in the repo (claims already proven on a live 26.3 server by a mechanics spec)

Every claim is tagged **[source: ...]** or **[inferred]**. An inferred claim names the test that would settle it.

---

## 0. Version check: the source is 26.3

- `server/server.jar` contains `version.json` with `"id": "26.3"`, `world_version 5023`, `protocol_version 777`, `build_time 2026-09-15T11:20:48+00:00`, `stable: true` [source: `unzip -p server/server.jar version.json`].
- The `server.jar` sha1 is `33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c`, which equals `downloads.server.sha1` in `v26_3.json` (`id 26.3`, `releaseTime 2026-09-15T11:23:02+00:00`) [source: shasum + v26_3.json].
- The bundler's `META-INF/versions.list` names `26.3/server-26.3.jar`. The class bytes in `jarx` match that inner jar exactly for `PistonBaseBlock.class` (e70e210a278d…), `SharedConstants.class` (54389cb4f633…) and `RedstoneWireBlock.class` (b7060731b3cd…) [source: shasum of the classes unzipped from `META-INF/versions/26.3/server-26.3.jar` compared with `jarx/`].
- The client jar downloaded for the renderer has sha1 `e877b6a07acd633fb3bb475002175cec036e7b87`, which equals `downloads.client.sha1` in v26_3.json [source: shasum].
- The 26.3 jars are not obfuscated (Mojang names such as `PistonMovingBlockEntity`, `ownSignal`), so the names below are real names, not mappings [source: the decompiled files].

**Verdict: source = Minecraft Java 26.3 release. No version risk.** One caveat: decompiled Java can differ cosmetically from the original (for example the odd `this.extending != 1.0F - this.progress < 0.25F` at `S:world/level/block/piston/PistonMovingBlockEntity.java:365`), but the control flow is the shipped bytecode.

**World feature flags:** the test world has `redstone_experiments` **disabled**. Its `level.dat` `DataPacks.Disabled` = [minecart_improvements, redstone_experiments, trade_rebalance] and `Enabled` = [vanilla, file/redstone_ai]; `server.properties` has `initial-enabled-packs=vanilla` [source: level.dat NBT bytes; server.properties]. So every `ExperimentalRedstoneUtils.initialOrientation` returns `null` [source: `S:world/level/redstone/ExperimentalRedstoneUtils.java:9-24`] and dust uses the legacy evaluator (§9). Also `max-chained-neighbor-updates=1000000` [source: server.properties].

---

## 1. Order of work inside one server tick

### 1.1 Server loop
1. `processPacketsAndTick`: **player packets are processed first** (`packetProcessor.processQueuedPackets()`), then `tickServer` [source: `S:server/MinecraftServer.java:984-994`].
2. `tickServer`: `tickCount++`, `tickRateManager.tick()`, then `tickChildren` [source: `S:server/MinecraftServer.java:959-961`]. `tickRateManager.tick()` sets `runGameElements = !frozen || frozenTicksToRun > 0` [source: `S:world/TickRateManager.java:56-61`].
3. `tickChildren`: command functions (`getFunctions().tick()`, i.e. `#minecraft:tick` data-pack functions), then each level's `tick`, then connections and the player list [source: `S:server/MinecraftServer.java:1067-1112`].
4. After the tick, `waitUntilNextTick` → `runAllTasks()`. **RCON commands run here** because `DedicatedServer.runCommand` uses `executeBlocking` [source: `S:server/MinecraftServer.java:738-745, 838-847`; `S:server/dedicated/DedicatedServer.java:714-717`].

So both a harness `setblock` and a player's click land **between** tick T and tick T+1, while `getGameTime()` still returns T. [inferred for the player path: the packet-queue claim is from source, but whether a lever-use packet runs in `processQueuedPackets` or as a queued task was not traced. Either way it is before the level tick. Settle with the MC-172213 player-input spec already listed in squid_rules.md.]

### 1.2 `ServerLevel.tick`, in order [source: `S:server/level/ServerLevel.java:359-474`]
| # | Phase | Line | Notes |
|---|---|---|---|
| a | `handlingTick = true` | 361 | |
| b | world border, weather | 366-370 | only if `runsNormally` |
| c | `tickTime()` → **gameTime + 1** | 388, 481-485 | |
| d | **scheduled block ticks** (`blockTicks.tick`), then fluid ticks | 395-397 | cap 65,536 per tick |
| e | raids | 403 | |
| f | `chunkSource.tick` (random ticks, spawning) | 407 | |
| g | **block events** (`runBlockEvents`) | 410, 1264-1289 | piston moves happen here |
| h | `handlingTick = false` | 413 | |
| i | **entities** | 432-454 | frozen non-player entities skipped |
| j | **block entities** (`tickBlockEntities`) | 456 | moving_piston progress; landing |

Phases i and j only run while `emptyTime < 300`. `emptyTime` is reset whenever the level has active chunk tickets [source: `S:server/level/ServerLevel.java:415-424`]. [inferred: the force-loaded plot keeps `hasActiveTickets` true, so a player-less satellite still ticks block entities. Evidence: the existing piston specs pass on satellites.]

`tickBlockEntities` skips every ticker when `!runsNormally()`, i.e. while frozen and not stepping [source: `S:world/level/Level.java:527-547`]. A frozen server does not advance moving_piston progress; `tick step` does.

### 1.3 Scheduled ticks (phase d)
- A tick fires at `gameTime_at_schedule + delay` [source: `S:world/level/LevelAccessor.java:31-37`]. A tick scheduled with delay 2 in phase d of T fires in phase d of T+2.
- Order within a game tick: **priority first** (EXTREMELY_HIGH −3 … EXTREMELY_LOW +3), **then `subTickOrder`**, a level-global counter in scheduling order [source: `S:world/ticks/ScheduledTick.java:9-20`; `S:world/ticks/TickPriority.java:5-12`; `S:world/level/Level.java:1090`]. Chunks are merged by the same comparator (`CONTAINER_DRAIN_ORDER`) [source: `S:world/ticks/LevelTicks.java:32-36, 153-172`], so **position does not affect scheduled-tick order**.
- All ticks due this game tick are **collected before any runs** (`collectTicks` then `runCollectedTicks`) [source: `S:world/ticks/LevelTicks.java:81-91`]. A tick scheduled while phase d runs can therefore never fire in the same game tick.
- Dedupe: only one pending tick per (pos, block) while queued (`ticksPerPosition`, `UNIQUE_TICK_HASH`) [source: `S:world/ticks/LevelChunkTicks.java:21, 53-57`]. A tick is removed from that set when it is *collected* [source: same file, 43-50]. Diodes, torches and comparators guard with `willTickThisTick` (in the collected set); the observer guards with `hasScheduledTick` [source: DiodeBlock:88, RedstoneTorchBlock:86, ComparatorBlock:141, ObserverBlock:75].

### 1.4 Block events (phase g)
- `blockEvent()` adds a `BlockEventData(pos, block, a, b)` record to an `ObjectLinkedOpenHashSet`. The queue is **FIFO** and **identical events collapse** (record equality) [source: `S:server/level/ServerLevel.java:216, 1259-1262`; `S:world/level/BlockEventData.java:6`].
- `runBlockEvents` drains until empty, so **events queued while events run execute in the same game tick** [source: ServerLevel.java:1264-1289]. This makes piston-chain 0-ticks possible.
- An event only runs if the block at pos is still the same `Block`. The piston then re-checks power inside `triggerEvent` [source: ServerLevel.java:1291-1294; PistonBaseBlock.java:139-152].
- Where an event lands depending on when it was queued [source: phase list 1.2]:
  - queued in d, f or g of tick T: runs in g of **T**;
  - queued in i or j of T, or between ticks (commands, players): runs in g of **T+1**.
- A successful event is broadcast to clients within 64 blocks as `ClientboundBlockEventPacket` [source: ServerLevel.java:1270-1281]. The client then runs the same `triggerEvent` itself [source: `C:client/multiplayer/ClientPacketListener.java:1497-1500`].

### 1.5 Neighbour updates and shape updates
- Neighbour and shape updates are **synchronous**, run depth-first through `CollectingNeighborUpdater`. Updates caused while one update runs are pushed on a stack and run before the parent's remaining directions [source: `S:world/level/redstone/CollectingNeighborUpdater.java:68-112`]. They are never deferred to a later phase. The chain cap is `max-chained-neighbor-updates` [source: same file 70-80].
- `updateNeighborsAt` order: **W, E, D, U, N, S** (`NeighborUpdater.UPDATE_ORDER`) [source: `S:world/level/redstone/NeighborUpdater.java:18`; `CollectingNeighborUpdater.java:128-169`]. This order is fixed in world axes, so it is **directional** (rotating a build changes which neighbour hears first).
- `Direction.values()` order (used by many loops, e.g. torch `notifyNeighbors`, wire `toUpdate`, `getBestNeighborSignal`) is D, U, N, S, W, E [source: `S:core/Direction.java:33-38`].
- `setBlock` flag bits: 1 neighbours, 2 clients, 4 invisible, 16 skip shape updates, 64 moved-by-piston, 256 skip BE side-effects, 512 skip onPlace [source: `S:world/level/block/Block.java:90-103`]. `onPlace` runs on **every state change** unless 512 is set, not only on block changes [source: `S:world/level/chunk/LevelChunk.java:305-329`]. So a diode's `setBlock(..., 2)` still updates the block in front through `DiodeBlock.onPlace` [source: `S:world/level/block/DiodeBlock.java:164-167`].
- Shape updates (`updateNeighbourShapes`) fire unless flag 16 is set [source: `S:world/level/Level.java:251-256`]. Observers listen to shape updates (§7.3).

### 1.6 Block entities (phase j)
- Tickers run in list order (insertion order). A ticker added while phase j runs goes to `pendingBlockEntityTickers` and first runs next tick. One added outside phase j (e.g. in phase g) goes straight into the list and **ticks in the same game tick** [source: `S:world/level/Level.java:523-547`].
- If a position already has a ticker wrapper, it is **rebound in place** and keeps its old list slot [source: `S:world/level/chunk/LevelChunk.java:709-729`].
- [inferred] Order of moving_piston ticking and landing: `moveBlocks` creates the moved cells from the far end of `toPush` back toward the piston, and the arm last [source: PistonBaseBlock.java:297-318]. For a fresh position the farthest cell therefore ticks and lands first. A position that already held a ticker keeps its old list slot. Settle with `piston_landing_order_far_first` (§12).

---

## 2. Piston extension timeline

### 2.1 Trigger
`neighborChanged`, `onPlace` (only when the block type changes and there is no BE) and `setPlacedBy` call `checkIfExtend` [source: `S:world/level/block/piston/PistonBaseBlock.java:63-86`]. If the piston is powered, not extended and `PistonStructureResolver.resolve()` succeeds, it queues **block event 0** (extend) with `b1 = facing` [source: PistonBaseBlock.java:93-99]. `PistonBaseBlock` has no `tick()` or `updateShape`. The piston never uses scheduled ticks and **never reacts to shape updates, only to neighbour updates and its own placement** [source: whole file].

### 2.2 Block event 0 (phase g of tick E)
1. Server-side re-check: if power has gone, `return false` and nothing happens [source: PistonBaseBlock.java:142-152]. This is why a pulse that begins and ends before phase g does nothing (proven on a server: M: `piston_same_tick_pulse_ignored`).
2. `moveBlocks(extending=true)` [source: PistonBaseBlock.java:257-357]:
   - resolve again; a failed resolve returns false (no move, no extended state);
   - "destroy" blocks (POPPED) drop items and become air (flag 18) [283-295];
   - each pushed block's **destination** becomes `moving_piston[facing]` (flag 324 = 256|64|4: no neighbour update, **no client packet**, shape updates yes). Its BE has `movedState` = the block, `extending=true`, `source=false`, progress 0 [297-306];
   - the arm cell becomes `moving_piston[facing,type]` with BE `movedState=piston_head`, `extending=true`, `source=true` [308-318];
   - vacated origin cells become air (flag 82 = 64|16|2) [320-324], followed by shape updates around them [326-332];
   - neighbour updates at every destroyed cell, every **origin** cell of a pushed block and the arm cell [337-354];
3. The base is set to `extended=true` (flag 67 = 64|2|1) [source: PistonBaseBlock.java:160]. The sound and game event follow.

Result: during phase g of E, a redstone block that has been pushed **stops powering at once**. Its origin is air, and the destination `moving_piston` is not a signal source and not a conductor [source: Blocks.java:891-905; MovingPistonBlock has no signal methods]. This is proven on a server: M: `piston_one_tick_instant_transport` ("origin stops emitting the tick motion starts").

### 2.3 moving_piston progress, per game tick [source: `S:world/level/block/piston/PistonMovingBlockEntity.java:291-324`]
| Game tick, phase | progressO | progress | Cell |
|---|---|---|---|
| E, g (created) | 0 | 0 | moving_piston |
| E, j (1st BE tick) | 0 | 0.5 | moving_piston |
| E+1, j | 0.5 | 1.0 | moving_piston |
| E+2, j | 1.0 → **lands** | — | real block |

Landing (E+2, phase j): the BE is removed. `movedState` is corrected by `Block.updateFromNeighbourShapes` and set with flag 67 (neighbour updates, client packet, moved-by-piston). Then `level.neighborChanged(pos, …)` is called on the cell itself [source: PistonMovingBlockEntity.java:294-313]. If the shape-corrected state is air (e.g. dust with no support), the original is placed with flag 340 and then `updateOrDestroy` runs [303-304]. A waterlogged block lands un-waterlogged [306-308]. The arm cell lands as `piston_head` because its movedState is the head.

`TICKS_TO_EXTEND = 2` and `TICK_MOVEMENT = 0.51` are declared but the tick code uses `+0.5F` [source: PistonMovingBlockEntity.java:31-33, 316].

**NBT trap:** `saveAdditional` writes `progress` = **progressO** (the value before this tick's step) [source: PistonMovingBlockEntity.java:342]. A `data get block` probe reads 0, 0.5, 1.0 at E, E+1, E+2. Loading sets `progressO = progress` [331-332].

### 2.4 Calibration against the harness (+N means N gt after the drive command)
The drive runs between ticks t and t+1 (§1.1). The piston's `neighborChanged` runs at that moment and queues the event, which runs in phase g of **t+1** = E.
- +1 (after tick t+1): destination and arm are moving_piston, base `extended=true`
- +2: still moving_piston (progress 1.0)
- +3: real block and piston_head

This matches the server-proven M: `moved_observer_pulses` ("moving_piston at +1..+2, landed … at +3") and M: `piston_one_tick_instant_transport` ("lands at t+3") [source: M:143-146, 172-175]. **In redstone terms (event at E): movement starts at E, and the block is real at E+2.** A piston powered by a repeater that turns on in phase d of tick R has E = R (same tick), because phase d precedes phase g [inferred from 1.2 + 1.4. Settle with `piston_extends_on_repeater_tick` (§12)].

### 2.5 Pistons moved by pistons (extenders)
- A **retracted** piston (normal or sticky) is pushable and pullable. An **extended** one is immovable, even though the piston's `pushReaction` property is IMMOVEABLE [source: PistonBaseBlock.java:237-254 special-cases pistons; Blocks.java:5661-5667]. piston_head and moving_piston are IMMOVEABLE [source: Blocks.java:869-873, 891-905]. Any other block with a block entity is immovable unless its push reaction is `PUSH` [source: PistonBaseBlock.java:242-254] (M: `piston_block_entity_stoppers`).
- A moved piston lands through `setBlock(…, 67)` in phase j of E+2. Its BE was already removed [source: PistonMovingBlockEntity.java:298-310], so `onPlace` sees `getBlockEntity == null`, the block type changed, and `checkIfExtend` runs [source: PistonBaseBlock.java:80-86]. **A landed piston that is powered queues its extend during phase j, so the event runs in phase g of E+3.** [inferred from source. Settle with `piston_landed_powered_extends_next_tick` (§12).] Every piston relayed through an extender therefore costs 3 gt from event to event.

---

## 3. Piston retraction timeline

### 3.1 Trigger
`checkIfExtend` with power gone while `extended=true` queues event **1**, or event **2** when the +2 cell is a `moving_piston` with the same facing whose BE is still extending, and one of these holds:
- `getProgress(0) < 0.5`, i.e. progressO < 0.5, or
- `gameTime == BE.lastTicked`, or
- `isHandlingTick()` (phases a–g)

[source: PistonBaseBlock.java:100-113; `getProgress(0)` = `lerp(0, progressO, progress)` = progressO, PistonMovingBlockEntity.java:84-90; `lastTicked` set at 292; `isHandlingTick` ServerLevel.java:361, 413, 648-650].

### 3.2 Block event 1 or 2 (phase g of tick R)
1. If the piston is powered again by now: `setBlock(extended=true, 2)` and return. **The retraction is cancelled with no motion** [source: PistonBaseBlock.java:142-147].
2. If the arm cell is still an extending moving_piston BE, `finalTick()` it: as a source it becomes **air** [source: PistonBaseBlock.java:164-166; PistonMovingBlockEntity.java:259-280]. `finalTick` acts only if `progressO < 1.0` [260].
3. The **base becomes `moving_piston`** (flag 276 = 256|16|4) with BE `movedState = piston/sticky_piston[facing, extended=false]`, `extending=false`, `source=true` [source: PistonBaseBlock.java:168-179]. Neighbour updates at the base follow [178].
4. Normal piston: `removeBlock(arm)` [203].
5. Sticky piston: if the +2 cell is an extending moving_piston in the same direction, `finalTick()` it. The pushed block is placed **now, as a real block at +2**, and nothing is pulled: this is **block spitting** [source: 180-190; `finalTick` places `updateFromNeighbourShapes(movedState)` with `setBlockAndUpdate` + `neighborChanged`, 265-277].
6. Otherwise, with event 1 and a pullable block at +2 (not air; `isPushable`; push reaction `PUSH_PULL`, or a piston), it runs `moveBlocks(extending=false)`. The arm is set to air first [259-261]; the pulled block becomes moving_piston at +1 (extending=false). With event 2, or anything not pullable, it just removes the arm [192-201].

### 3.3 Progress
The base BE and the pulled block BE follow the same 0 → 0.5 → 1.0 → land sequence as §2.3 (R, R+1, R+2) [source: PistonMovingBlockEntity.java:291-324]. At R+2 phase j the base lands as the retracted piston and the pulled block lands at +1.

Harness calibration: undrive at t, R = t+1, base real at t+3. This matches M: `sticky_piston_short_pulse_drops_block` ("base is moving_piston 2 gt, retracted 3 gt after unpowering") [source: M:162-165].

### 3.4 The base cannot react while it retracts
While the base is `moving_piston`, `MovingPistonBlock` has no `neighborChanged` [source: `S:world/level/block/piston/MovingPistonBlock.java` whole file], so re-powering the piston during R+0..R+2 is not seen. At landing (R+2, phase j) `onPlace` runs `checkIfExtend` [source: PistonBaseBlock.java:80-86 with the BE removed at PistonMovingBlockEntity.java:298]. The PistonMovingBlockEntity also calls `neighborChanged` on the landed cell [311].

**Consequence:** extension can be interrupted (a retract event finalTicks the moving arm); retraction cannot. The earliest re-extend after event R is phase g of **R+3**. This is the hard floor on a sticky-piston door's reset time. [inferred from source; nothing in M covers it. Settle with `piston_retract_deaf_until_landed` (§12).]

### 3.5 When the sticky piston spits: the threshold
Let E be the extend event tick. The pushed block's moving_piston exists from E phase g until E+2 phase j.
- Retraction triggered by redstone in phase d/f/g of E, E+1 or E+2 (`isHandlingTick` = true): event 2, and the +2 cell is still moving at event time, so the block is **spat**.
- Triggered between ticks (commands, players) after tick E or E+1: `lastTicked == gameTime`, so event 2 and the block is **spat**. After tick E+2 the block has landed, so event 1 and the block is **pulled**.
- Harness form: a pulse of N gt spits for N ≤ 2 and pulls for N ≥ 3. **Proven** on a server: M: `sticky_piston_short_pulse_drops_block` ("threshold is exactly between 2 and 3 gt").
- Even if event 1 is queued, the +2 check in 3.2 step 5 does not depend on the event number. A block still moving when the event *runs* is always spat [source: PistonBaseBlock.java:180-201]. Event 2 only matters when the block has landed between queueing and running: then the piston does *not* pull it back. [inferred: a trigger in phase j of E+2 before the pushed BE ticks gives event 1 (progressO = 0.5, lastTicked = E+1, not handling tick). Settle with `piston_spit_vs_pull_phase_j` (§12); low priority for doors.]

### 3.6 "0-tick" and "1-tick" pulses at a piston
- **Both edges before phase g of the same tick** (e.g. on and off inside phase d, or by two commands): the extend event is queued, the unpower finds `extended=false` and queues nothing, and event 0 then re-checks and returns. **Nothing moves** [source: PistonBaseBlock.java:93-114, 149-151]. Proven: M: `piston_same_tick_pulse_ignored`.
- **On before phase g, off during phase g of the same tick, after the extend event has run** (piston-driven 0-tick, e.g. a pushed redstone block unpowering the piston in phase g): `extended=true`, so event 2 (handling tick) is queued and runs **in the same phase g** (§1.4). A sticky piston: the arm is finalTicked to air, the pushed block is finalTicked into a real block at +2 in the same tick, and the base starts retracting. **The block teleports 1 cell in 0 gt.** A normal piston: the arm vanishes and the pushed block keeps moving and lands at E+2 [source: PistonBaseBlock.java:139-211; the non-sticky branch at 202-204 never touches +2]. [inferred for the in-tick variant. The between-ticks 1 gt variant is proven in M: `piston_one_tick_instant_transport` (sticky real at +2 by t+2 vs t+3 when held; normal gains nothing). Settle with `zero_tick_teleport_via_block_events` (§12).]
- **"Instant retraction" in 26.3:** there is no path that makes a retracting base or a pulled block land faster than R+2. `finalTick` is only called on *extending* BEs (the arm and the +2 cell) from `triggerEvent`, or from `preRemoveSideEffects`. The latter only clears the BE because the cell has already changed by then [source: PistonBaseBlock.java:164-166, 184-189; PistonMovingBlockEntity.java:259-285; LevelChunk.java:308-316]. What players call instant retraction or a 0-tick is the arm vanishing plus the spat block placed at once. [source: `grep -rn finalTick mc-src/` lists only PistonBaseBlock.java:165, 188 and PistonMovingBlockEntity.java:259 (definition), 284 (preRemoveSideEffects), plus an unrelated local variable in MetricsPersister. That no *other* mechanism shortens a retraction is still [inferred]. Settle with `piston_retract_duration_fixed` (§12).]

---

## 4. How moving_piston looks and collides (seamless timing)

### 4.1 Server-side block properties
`moving_piston`: `RenderShape.INVISIBLE`, outline shape empty (it cannot be targeted), `noOcclusion`, `isRedstoneConductor(never)`, `isSuffocating(never)`, `forceSolidOn`, `dynamicShape`, `strength(-1)`, `pushReaction IMMOVEABLE`, no loot table [source: `S:world/level/block/Blocks.java:891-905`; `MovingPistonBlock.java:95-112`]. No `lightLevel`: a moving glowstone or redstone lamp emits nothing while moving [inferred from the missing property and the moved block not being the cell state. Settle with `moving_piston_dark_nonconductor` (§12)].

### 4.2 What the client draws
The client builds its own moving_piston and BE from the block-event packet, running `triggerEvent` client-side. The server-side power check is skipped because of `!isClientSide` at PistonBaseBlock.java:142 [source: ClientPacketListener.java:1497-1500]. Moving cells are placed on the server with flag 324 (no bit 2), so **no block-update packet** is sent for them. The client's own simulation is what the player sees [source: PistonBaseBlock.java:303, 316; Level.java:238-242].

`PistonHeadRenderer` draws `movedState` translated by `getXOff/YOff/ZOff(partialTicks)` = `direction · (progress − 1)` when extending, `direction · (1 − progress)` when retracting. Progress is `lerp(partialTick, progressO, progress)` [source: `C:client/renderer/blockentity/PistonHeadRenderer.java:28-75`; PistonMovingBlockEntity.java:84-106].
- Extending cell at progress 0: drawn exactly on the **origin** cell. At 0.5 it is halfway. At 1.0 it is on the destination.
- Retracting source (piston base): draws the piston base as `extended=true` fixed in place, plus a head sliding back. The head is `short` once progress ≥ 0.5 [source: PistonHeadRenderer.java:48-56].
- Arm cell while extending: the head is drawn `short` while progress ≤ 0.5 [45-47].
- The client keeps a finished BE for 5 extra client ticks (`deathTicks`) before removing it, so the drawn block stays at progress 1.0 until the server's real-block update arrives [source: PistonMovingBlockEntity.java:294-297].

So, by game tick, for an extend event at E:
- **E:** the cell is created at progress 0 and ticks to 0.5 in phase j. Frames rendered between the E and E+1 client ticks interpolate 0 → 0.5.
- **E+1:** 0.5 → 1.0.
- **E+2:** static at 1.0; the cell becomes a real block.

**Visible motion occupies the two tick intervals starting at E and E+1. The block rests visually at E+2.** Under the Squid definitions (squid_rules.md:38-43): "opening visible time" should end at E+2 (the start of the rest frame). "Opening time", the end of the last movement that makes the hallway match, is also E+2, when the cell is a real block. [inferred mapping from rule text to ticks. The rules do not say whether the tick of landing counts as motion. Read the rule's worked example, or ask the Squid mods, before claiming a record time.]

**Client divergence risk:** the client runs pistons from packets on its own clock. It skips the power re-check, and the client-side `isHandlingTick`, `lastTicked` and ordering are not the server's. [inferred: a 0-tick sequence may show a one-frame ghost (a head or block drawn briefly) on the client even when the server's end state is clean. squid_rules.md:39 says "z-fighting counts", so this matters for SUPER/FULL seamless tiers. **Cannot be settled headless.** It needs a real client recording (`/tick rate 1` + frame capture) of each door's opening and closing.]

### 4.3 Collision (entities, players)
`getCollisionShape` = the moved block's collision shape shifted by the extended progress. A retracting source piston adds the extended-base shape. When the query comes from the piston push itself (NOCLIP set to the movement direction) and progress < 1, only the base part is solid [source: PistonMovingBlockEntity.java:347-375; MovingPistonBlock.java:99-103]. Players collide with a moving door block at its interpolated server position. [inferred: a player in the hallway is pushed by an extending door block (`moveCollidedEntities` 118-174). Relevant only to entity-free "SUPER" tiers.]

---

## 5. Structure resolution: push limit, slime, honey

[source for all bullets: `S:world/level/block/piston/PistonStructureResolver.java` and PistonBaseBlock.java:213-255]
- `isPushable`:
  - false outside the world border or build height, or at a height boundary in the push direction;
  - air counts as pushable;
  - pistons: pushable iff not extended;
  - otherwise false if hardness is −1 (bedrock etc.);
  - `IMMOVEABLE` → false; `POPPED` → allowed only where destruction is allowed; `PUSH` → true only when `direction == connectionDirection`;
  - `PUSH_PULL` falls through to `!hasBlockEntity()`.

  [PistonBaseBlock.java:213-255]
- `PUSH` (push-only) blocks: `glazed_terracotta` (all colours) and `shulker_box` [source: Blocks.java:3771-3780 and the SHULKER_BOX hit of the awk scan]. Because the check is `direction == connectionDirection`, glazed terracotta is pushed from the front, **not pulled** by a sticky piston (the pull check needs PUSH_PULL, PistonBaseBlock.java:196), and **not dragged sideways** by slime or honey. Proven: M: `piston_glazed_terracotta_slime_barrier`.
- **Push limit 12** counts only moved blocks. The checks are at resolver lines 94-97 (the first block), 110-111 (the back-chain of sticky blocks) and 154-156 (the forward line). POPPED blocks go to `toDestroy` and do not count [149-152]. Proven: M: `piston_push_limit_breakable_tail`.
- A line ending in a POPPED block destroys it. A blocked line (an immovable block, or the piston itself) makes the whole resolve fail [140-156].
- Slime and honey: `isSticky` = slime or honey [64-66]. Slime–honey faces do **not** stick; anything else sticks to a sticky block if either side is sticky [68-74]. Every sticky block in `toPush` adds its perpendicular neighbours as new lines (`addBranchingBlocks`) [53-58, 177-191]. The back-chain behind a sticky block is also pulled along (`while (isSticky…)`) [99-113]. A sticky back-chain or branch stops at the piston's own cell [86, 106]. But a *forward* push line that reaches the piston itself makes `addBlockLine` return **false**, so the whole move is aborted and the piston does not fire [145-147]. A slime loop that pushes back into its own piston jams it.
- Entities: an extending slime sets an entity's velocity along the push axis to ±1, a bounce [source: PistonMovingBlockEntity.java:127-148]. Honey moving **horizontally** drags entities standing on top (`isStickyForEntities`, `moveStuckEntities`) [185-208].
- The sticky piston pulls: any `PUSH_PULL` block without a BE, and retracted pistons. It does not pull glazed terracotta, shulker boxes, POPPED blocks or immovables [source: PistonBaseBlock.java:192-200].

### 5.1 Double and triple extenders [inferred, assembled from §2–3]
- Only retracted pistons move, so an extender's inner piston must be retracted when it is pushed or pulled. The outer piston cannot pull an inner piston that is still a `moving_piston` (IMMOVEABLE).
- Event-to-event costs:
  - extend landing: 2 gt (E → E+2);
  - a moved piston re-triggers at E+3 (§2.5);
  - retraction: R → R+2, re-trigger at R+3 (§3.4).
- A double extender opening (push the inner piston out, then fire it) therefore needs ≥ 3 gt between the stage events. Retracting in the reverse order needs ≥ 3 gt per stage unless spitting is used.

Settle with `double_extender_min_stage_gap` (§12). No extender cycle time is proven yet.

---

## 6. Quasi-connectivity and BUD

- `getNeighborSignal` [source: PistonBaseBlock.java:116-136]:
  1. any neighbour except the face provides a signal (`hasSignal(pos.relative(d), d)`) → powered;
  2. `hasSignal(pos, DOWN)` is evaluated on the piston's own cell. The piston is not a conductor and is not a signal source, so this is always 0 [inferred: piston properties at Blocks.java:5661-5667 give `isRedstoneConductor(never)` and the block has no signal methods. Harmless];
  3. **quasi-connectivity**: every neighbour of the cell *above*, except below it (the piston itself), is checked, **including the cell diagonally above the face**. Proven: M: `piston_ignores_power_from_face`.
- Pistons are **not redstone conductors** in 26.3, so power into a piston does not pass through it [source: Blocks.java:5665].
- **BUD:** the piston only re-evaluates on a neighbour update to itself or its head (the head forwards updates to the base, PistonHeadBlock.java:104-113), or on `onPlace`. Power arriving at the QC cells does not update the piston, because those cells are 2 away [source: PistonBaseBlock.java:70-86; NeighborUpdater order]. Shape updates are ignored. Proven: M: `piston_quasi_connectivity_bud`.
- [inferred] An **extended** piston can also be budded through its head: `PistonHeadBlock.neighborChanged` relays any update the head receives to the base [source: PistonHeadBlock.java:104-113]. So an update next to the *head* can retract a QC-depowered extended piston. Settle with `piston_head_relays_bud` (§12).

---

## 7. Component scheduling and priorities

| Component | Delay | Priority | Source |
|---|---|---|---|
| Repeater turning on | 2 × delay (2/4/6/8) | HIGH (−1) | RepeaterBlock.java:47-48; DiodeBlock.java:84-99 |
| Repeater turning off | 2 × delay | VERY_HIGH (−2) | DiodeBlock.java:92-94 |
| Repeater (on or off) whose output faces a diode that is not pointing back into it | 2 × delay | EXTREMELY_HIGH (−3) | DiodeBlock.java:90-91, 196-200 |
| Repeater re-tick after a pulse shorter than the delay (stays on for a full delay) | 2 × delay | VERY_HIGH | DiodeBlock.java:56-60 |
| Comparator | 2 | NORMAL, or HIGH when prioritised (same front-diode rule) | ComparatorBlock.java:39-41, 140-149 |
| Observer | 2 on, then 2 off | NORMAL (default) | ObserverBlock.java:45-54, 74-78 |
| Redstone torch | 2 | NORMAL | RedstoneTorchBlock.java:82-89 |
| Stone button / wooden button | 20 / 30 | NORMAL | Blocks.java:2055, 2837 |
| Piston | none (block event, phase g) | after **all** scheduled ticks of the tick | §1.2 |

### 7.1 Repeater
- On `tick`: if locked, nothing. If on and the input is gone, turn off. If off, turn on, and if the input is already gone, schedule another tick with VERY_HIGH [source: DiodeBlock.java:49-63]. Pulse width = max(input width, 2·delay). Proven: M: `repeater_extends_short_pulses`.
- Lock: only diodes (repeaters, comparators) on the sides, via `getControlInputSignal(..., onlyDiodes=true)`. It is updated in `updateShape`, so the lock changes **instantly** on a shape update, not on a tick [source: RepeaterBlock.java:57-90; SignalGetter.java:48-59]. Proven: M: `repeater_lock_only_by_diodes`, `repeater_lock_discards_pending_tick`.
- Input: the signal from the back cell. If the back is dust, `max(signal, dust POWER)` is used, so dust behind a repeater always counts regardless of its shape [source: DiodeBlock.java:109-119].
- Output: strong (direct) power 15 out of the front only [source: DiodeBlock.java:137-150, 188-190]. `updateNeighborsInFront` updates the front cell, then that cell's neighbours except back toward the repeater [176-182].

### 7.2 Comparator
- `checkTickOnNeighbor` schedules a tick if the output value or the powered state would change and no tick is collected this tick [source: ComparatorBlock.java:140-149]. On its tick it refreshes the output and updates the front [151-176]. A 1 gt pulse is filtered out. Proven: M: `repeater_extends_short_pulses` (comparator half) and `diode_side_input_tick_priority`.

### 7.3 Observer
- It fires when the **observed cell sends it a shape update** (`updateShape` with `directionToNeighbour == FACING`, while unpowered) and no tick is pending (`hasScheduledTick`) [source: ObserverBlock.java:56-78].
- Tick: off → on, and schedule off in 2. On → off. Both call `updateNeighborsInFront` (back cell, then its neighbours) [45-54, 80-86]. Output: 15 strong power out of the back [98-111].
- A piston creating `moving_piston` in front of an observer (flag 324, shape updates on) is a state change of the observed cell, so it fires it. A vacated origin (flag 82 skips the automatic shape update) still gets explicit `updateNeighbourShapes`, so an observer watching the origin fires too [source: PistonBaseBlock.java:303, 316, 322-332]. The landing (flag 67) also shape-updates, but `updateShape` ignores it while the observer is powered [source: ObserverBlock.java:67]. [inferred: an observer watching a push destination is on E+2..E+3 from the moving_piston created at E. The landing in phase j of E+2 arrives while it is powered, so it is **missed**: one pulse, not two. Settle with `observer_sees_piston_start_and_land` (§12).]
- Observer placed already powered (e.g. moved while on) with no pending tick: it resets to off at once and updates its front [source: ObserverBlock.java:113-122]. Removed while on with a pending tick: its front is updated as if off [124-129]. Proven in part: M: `moved_observer_pulses`.

### 7.4 Redstone torch
- It schedules a 2 gt tick when its lit state disagrees with its input and no tick is collected [source: RedstoneTorchBlock.java:82-89]. On tick it toggles with `setBlockAndUpdate` (flag 3).
- **Burnout:** 8 toggles within 60 gt → it stays off and schedules a 160 gt re-check [source: 25-29, 60-80, 126-143]. The RECENT_TOGGLES list is per-level and global, and is pruned only in `tick` [65-67]. Proven: M: `torch_burnout_one_shot`.
- Power: weak power to all sides except up, strong power up (`getDirectSignal` DOWN direction = the block above) [source: 91-109]. Its input is only the block it hangs on (`hasSignal(below)`; the wall torch overrides this).

### 7.5 Same-tick ordering recipe for doors [inferred from 1.3 + table]
Within one game tick:
1. all EXTREMELY_HIGH diode ticks;
2. VERY_HIGH (repeaters turning off);
3. HIGH (repeaters turning on, prioritised comparators);
4. NORMAL (comparators, observers, torches, buttons, in scheduling order);
5. **then** all piston block events, FIFO by queue time.

A piston's event order is therefore the order in which its power changed during phases d–g. Two pistons powered by one dust update are ordered by the dust's HashSet walk, which depends on location (§9). Settle any door-critical ordering with a spec of that exact sub-circuit at two plot offsets.

---

## 8. Things that are *not* block events or ticks
- Levers act immediately (`setBlockAndUpdate` + `updateNeighbours`) [source: `S:world/level/block/LeverBlock.java:84-85, 133`].
- The Button scheduled release is 20/30 gt (§7).
- Dust changes are instant (0 gt, neighbour-update driven) (§9).
- A redstone block moved by a piston: loses power at E phase g; gives power at E+2 phase j (§2).

---

## 9. Redstone wire (dust) in 26.3 on this world

- **Evaluator:** `DefaultRedstoneWireEvaluator` unless the `redstone_experiments` flag is on. It is off in the test world (§0) [source: RedstoneWireBlock.java:64, 264-276, 351-353]. The experimental orientation order (`ExperimentalRedstoneWireEvaluator`, `Orientation`) is present in the jar but inactive.
- Default update: compute the target power. If it changed, set it (flag 2), then call `updateNeighborsAt` for **a `HashSet<BlockPos>` of the wire and its 6 neighbours, iterated in hash order** [source: `S:world/level/redstone/DefaultRedstoneWireEvaluator.java:17-38`]. BlockPos hash order depends on coordinates, so **dust update order is locational**. Proven: M: `dust_update_order_locational` (the winning piston flips between z+0 and z+12).
- Squid "NOT LOCATIONAL/DIRECTIONAL" claims (squid_rules.md:29-30) must therefore avoid same-tick races resolved by dust. Order dependence outside dust:
  - `UPDATE_ORDER` W,E,D,U,N,S: **directional** [source: NeighborUpdater.java:18];
  - block-event FIFO: neither locational nor directional [source: ServerLevel.java:216];
  - `moveBlocks` sets vacated origins to air and shape-updates them by iterating `deleteAfterMove`, a `HashMap<BlockPos,…>`: **locational**. Two observers watching two vacated cells of one push fire in a position-dependent order [source: PistonBaseBlock.java:268, 322-332]. The neighbour updates that follow run in fixed far-to-near order [337-354].
- **Weak vs strong power:**
  - While a wire computes its own input, `getBlockSignal` sets `shouldSignal = false`, so every wire reports 0 [source: RedstoneWireBlock.java:278-283, 356-375].
  - A block powered only by dust has non-zero `getDirectSignalTo`, so it powers pistons, lamps and repeaters, but contributes 0 to other dust. This is the entire weak-power rule [source: SignalGetter.java:17-46, 65-69].
  - Dust gives power downward (`getDirectSignal`, direction ≠ DOWN), and sideways only in the directions it connects [RedstoneWireBlock.java:361-375].
  - Proven: M: `weak_powered_block_skips_dust`, `dust_powers_block_below`.
- **Dust vs hard-powered lines for fast doors** [inferred from above]:
  - Dust is 0 gt, but its update storm is large (up to ~42 `updateNeighborsAt` calls per changed wire; `checkCornerChangeAt` adds more on place/remove) and locationally ordered.
  - A repeater/torch → solid block → piston link costs 2 gt per hop but has deterministic, directional order.
  - Redstone-block-carrier chains turn off in 1 gt at any length (proven M: `piston_redstone_block_chain_instant_off`) but cost 3 gt per stage to turn on.
- Dust cannot be pushed intact: it is POPPED (a non-full, support-requiring block).

  [inferred: `piston_push_limit_breakable_tail` shows dust destroyed by a push. Not re-checked in Blocks.java.]

---

## 10. Other fast-door mechanics in source
- **Block-event dedupe:** two identical piston events queued before they run (same pos, block, event type and facing) collapse to one [source: ServerLevel.java:216; BlockEventData.java:6 is a record]. Different events (1 then 0) both run, in FIFO order, and each re-checks power and `extended` when it runs (§2.2, §3.2). [inferred consequence: a second update in the same tick cannot double-fire a piston. Settle with `piston_block_event_dedupe` (§12).]
- **Retract then re-power within the same phase:** the retract event re-checks power and becomes a no-op state set (§3.2 step 1). **A glitch-off that recovers before the event runs is filtered.** This is the dual of the extend check.
- **Pushed-block landing updates:** landing uses flag 67 and an extra `neighborChanged` on the cell itself. An arriving redstone block powers its neighbours in phase j of E+2. Pistons reacting to it queue for E+3; repeaters schedule for E+2+2·delay [source: PistonMovingBlockEntity.java:310-311; §1.4].
- **Chunk borders:** block events and block ticks at positions whose chunk is not block-ticking are postponed (`shouldTickBlocksAt`) [source: ServerLevel.java:1269, 1283-1288; LevelTicks.java:117]. A door spanning a force-loaded/non-loaded boundary is unsafe. Satellites force-load only the plot.
- **Updates from a moved block's origin:** after `moveBlocks`, `updateNeighborsAt` runs at every *origin* position (not the destination). Components beside a door block's old position hear the change in phase g of E; components beside its new position hear it only at E+2 [source: PistonBaseBlock.java:337-354; PistonMovingBlockEntity.java:310-311].

---

## 11. Already proven on a 26.3 server (from docs/MECHANICS.md; no new spec needed)
`sticky_piston_short_pulse_drops_block`, `piston_same_tick_pulse_ignored`, `piston_one_tick_instant_transport`, `piston_redstone_block_chain_instant_off`, `piston_ignores_power_from_face`, `piston_push_limit_breakable_tail`, `piston_block_entity_stoppers`, `piston_glazed_terracotta_slime_barrier`, `piston_quasi_connectivity_bud`, `moved_observer_pulses`, `repeater_extends_short_pulses`, `diode_side_input_tick_priority`, `repeater_lock_only_by_diodes`, `repeater_lock_discards_pending_tick`, `dust_update_order_locational`, `torch_burnout_one_shot`, `observer_dual_edge_powered_state`, `weak_powered_block_skips_dust`, `dust_powers_block_below` [source: `library/mechanics/` listing and M:88-215].

---

## 12. New mechanics specs to write when servers are free

| Spec | Settles | One-line test sketch |
|---|---|---|
| `piston_extends_on_repeater_tick` | §2.4 (E = the repeater's tick) | Delay-1 repeater → block → piston + stone. Drive the repeater input at t. Expect the repeater powered at +2 and the +1 cell already `moving_piston` at +2 (not +3); stone real at +4. |
| `piston_retract_deaf_until_landed` | §3.4 reset floor | Sticky piston held on, then off at t, then on again at t+1 and t+2 (separate runs). Expect `moving_piston` base at +1..+2, retracted at +3, and extension (moving_piston at +1 cell) no earlier than +4 in all runs. Control: on again at t+3 gives the same +4. |
| `piston_retract_cancel_same_tick` | §3.2 step 1 | Piston driven by a redstone block; remove it and put it back between two block-event phases via a torch/repeater 0-tick (or two commands with no step). Expect `extended=true` throughout and no moving_piston at any tick. |
| `piston_landed_powered_extends_next_tick` | §2.5 extender cost | Sticky piston A pushes retracted piston B onto a redstone block (B lands powered). Expect B `extended=false` on the landing tick and B's front cell `moving_piston` exactly 1 gt later. |
| `double_extender_min_stage_gap` | §5.1 | Double piston extender driven by two repeaters with an adjustable gap g = 1..4 gt. Record the smallest g that fully extends and fully retracts, and the total cycle. Test at 2 plot offsets and 4 rotations. |
| `zero_tick_teleport_via_block_events` | §3.6 in-tick 0-tick | Sticky piston P1 is powered by a redstone block that piston P2 pushes away. **P1's extend event must be queued first** (P1 powered by a repeater turning on, HIGH), and P2's push after it (P2 powered by a comparator, NORMAL, same tick). If P2 runs first, P1's re-check fails and nothing moves. Expect P1's stone real at P1's +2 cell in the same tick as P1's event, the arm air and the base moving_piston. |
| `piston_retract_duration_fixed` | §3.6 no instant retraction | Retract sticky pistons in every known 0-tick arrangement (spit, chain, budded). Expect the base `moving_piston` for exactly 2 ticks after its event every time. |
| `piston_block_event_dedupe` | §10 | Two updates to one powered piston in the same tick (dust + neighbour setblock via observer). Expect a single extension, no error or double motion. |
| `piston_spit_vs_pull_phase_j` | §3.5 edge | Retraction triggered by a moving block landing in phase j of E+2 (block entity order: create the trigger block's BE first). Expect event 1: the block landed at +2 is **pulled back**. Low priority. |
| `piston_landing_order_far_first` | §1.6 | Piston pushes 3 observers in a line, each watching into dust. Record which dust lights first at landing. Expect farthest first. Repeat with a pre-existing ticker at a destination. |
| `observer_sees_piston_start_and_land` | §7.3 | Observer watching the destination cell of a pushed stone (event at E). Expect exactly one pulse, powered E+2..E+3, and no second pulse from the landing at E+2. Control: an observer watching the origin also pulses at E+2. |
| `piston_head_relays_bud` | §6 | Extended sticky piston QC-powered, then the QC power removed silently. An update only next to the head (not the base) retracts it within 1 gt. |
| `moving_piston_dark_nonconductor` | §4.1 | A redstone block pushed toward a cell with dust beside the destination; dust also beside a stone placed at the destination's other side. Expect destination-side dust 0 and the stone not powering a lamp at +1..+2, and both 15/lit only at +3. Light emission while moving (glowstone) needs a client or a light-reading block; treat it as client-only. |
| `door_visible_motion_frames` (client) | §4.2 | **Needs a real client.** `/tick rate 1`, record each opening/closing of a candidate door and count frames with any drawn movement or ghost block in the hallway. Compare with the server trace. Required before claiming SUPER/FULL seamless or a visible time. |

---

## 13. Open questions (not answerable from source)
- Whether Squid counts the landing tick (E+2) as a "block motion" tick (squid_rules.md:43). Rule text, not code.
- The exact client frame behaviour of 0-tick spits (ghost heads, z-fighting). Needs a client (§12 last row).
- The player-input path timing (MC-172213) versus a repeater-driven input (squid_rules.md:47).
