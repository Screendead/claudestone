# Main server watchdog crashes, 2026-09-30 16:50:54 and 17:08:08

Source paths are relative to scratchpad/mc-src/net/minecraft/server/. The decompiled line numbers are a few lines off from the crash-stack numbers.

## Root cause: two linked mechanisms

- **(a) Crash 1.** `copper_oxidation_fires_observers` legitimately sets `random_tick_speed` 4096 for a 300-tick `wait`, and it runs on main (mechanics specs have no plot). Every stepped tick then does 4096 random rolls in every ticking chunk: 785 forceloaded, plus about 4225 more within the player's simulation distance of 32. The loop fell 60 s behind schedule, which is what the watchdog measures.
- **(b) Crash 2.** The crash in (a) killed the server before the spec's `gamerule random_tick_speed 3`. The shutdown save wrote 4096 to `game_rules.dat`. After the restart every stepped tick on main was about 1365x dearer, and 67 s after Screendead joined the watchdog fired again during ordinary `and_*` tests.

Resetting the gamerule fixes only (b). The next run of the copper spec on main, with a player within 32 chunks, would crash again unless (a) is also addressed.

- Both crash reports have "Performance stats: Random tick rate: 4096" [source: crash-2026-09-30_16.50.55 line 368, crash-2026-09-30_17.08.08 line 438].
- `library/mechanics/copper_oxidation_fires_observers.redstone.yaml` runs `gamerule random_tick_speed 4096`, then `wait: 300`, then `gamerule random_tick_speed 3`. It has no `finally` [source: yaml lines 38-40]. `sculk_detects_ice_melt` does the same with `wait: 20`. Mechanics specs have no plot (`plots.py` comment line 46), so they run in main.
- Its trace `traces/copper_oxidation_fires_observers/oxidation step ....json` was written at 16:50:56, 1-2 s after the watchdog fired at 16:50:54. It was the test running during crash 1 [source: file mtimes].
- `server/testworld/data/minecraft/game_rules.dat` was written at 16:50:55, during the watchdog's `System.exit` shutdown save. It holds `random_tick_speed` = `00 00 10 00` = 4096 [source: raw NBT bytes]. It has not been rewritten since, so the current main server (started 17:14:48) loaded 4096 [inferred: SavedData is only rewritten when dirty].
- The tests run between the 17:04 restart and crash 2 were `and_comparator_*`, `and_gate` and `and_piston_gate` [source: trace mtimes]. None of them set the gamerule; only the two mechanics files do [source: grep]. So crash 2 ran on the leaked 4096.

### Why 4096 makes each stepped tick expensive
- Chunks tick only when `runsNormally()` is true [source: level/ServerChunkCache.java:338]. That means unfrozen, or inside a `tick step`: `runGameElements = !isFrozen || frozenTicksToRun > 0` [source: world/TickRateManager.java:57]. The harness steps every tick it advances, so every stepped tick visits every block-ticking chunk [source: level/ServerChunkCache.java:395].
- Per chunk, `tickChunk` loops `tickSpeed` times over `random.nextInt(48)` and calls `tickPrecipitation` on a hit. That call does a heightmap lookup and a `getBiome` [source: level/ServerLevel.java:507-511, tickPrecipitation ~l.590]. Randomly-ticking sections add a further `tickSpeed` rolls each [source: l.525]. On this world (desert biome, sandstone layers, no features) almost no section is randomly ticking [inferred from generator-settings], so the precipitation loop is the cost. Both watchdog stacks stop inside that path: `tickPrecipitation -> getBiome -> getNoiseBiome`, `ZeroBitStorage` meaning a single-biome palette [source: crash stacks].
- Chunks that tick: every entity-ticking chunk in the simulation tracker [source: DistanceManager.java ~l.175-183]. That includes forceloaded chunks (`FORCED_TICKET_LEVEL` = ENTITY_TICKING, ChunkMap.java:128) and chunks within the player's `simulation-distance` of 32.
  - Main has 785 forceloaded chunks ("Loading 785 persistent chunks", log -7).
  - The crash reports do not give the ticking-chunk count directly. `W: 8281` (crash 1, = 91²) and `W: 4798` (crash 2) are loaded chunks. The `E: ...,4761,...` field is the entity manager's `chunkLoadStatuses` [source: PersistentEntitySectionManager.java:347-360]. A player at simulation distance 32 adds up to 65² = 4225 ticking chunks [inferred from the ticket radius].
  - Going from speed 3 to 4096 is about 1365x more rolls per chunk. Going from 785 chunks to about 5000 is about 6x more [calculation].
- Rough cost [inferred, not measured]: about 4096 × a few ns + 85 × about 0.5 µs per chunk, so about 60 µs per chunk. That is about 0.3 s per stepped tick for 4761 chunks, and about 50 ms for 785. The 300-tick `wait` then needs about 90 s of server-thread time.
- Timing check for crash 1. The last lag reset was at 16:49:54 ("10338 ticks behind"). The previous test's trace was written at 16:49:53. The watchdog fired at exactly 16:50:54. So the lag grew about 1:1 with wall time for the whole minute: the server thread did nothing but stepped ticks. The test needs about 300+ stepped ticks and had not finished, so it averaged at least about 0.2 s per stepped tick [inferred]. Crash 2 has the same shape: a reset at 17:07:01 as the player joined, and the watchdog 67 s later.
- The no-player evidence fits this. After the restart, with 4096 leaked and no player online, main logged "24929ms or 498 ticks behind" (17:05:27) and "23627ms or 472 ticks behind" (17:06:34), both at 20 tps (about 50 ms per tick). No such lag appears in the 12:34-15:45 session [source: logs].

### What "A single server tick took 60 s" actually measures
- The watchdog compares `Util.getNanos() - server.getNextTickTime()` with `max-tick-time` [source: dedicated/ServerWatchdog.java:42-43]. That is how far the loop runs behind its schedule, not how long one tick took.
- `runServer` adds `nanosecondsPerTick` to `nextTickTimeNanos` on every loop [source: MinecraftServer.java:736]. It skips the schedule forward only through the "Can't keep up" branch. That branch needs the lag to exceed 1 s + 20 ticks, and needs `nextTickTime` to have advanced at least 10 s + 100 ticks of scheduled time since the last skip [source: MinecraftServer.java:718-726].
- The watchdog fires when the lag passes 60 s before a skip becomes possible. After a skip, N ticks of real cost d at period p give a lag of N(d - p). A skip is allowed once N·p >= 10 s + 100p [calculation from the above]. So the watchdog wins if the average tick cost is more than p + 60p/(10 s + 100p):
  - at 20 tps (p = 50 ms): more than about 250 ms per tick, sustained for about 300 ticks
  - at `tick rate 10000` (p = 0.1 ms, the harness `WARP_RATE`, harness.py:83): more than about 0.7 ms per tick, sustained for about 60 s
- `spec.run` wraps the whole test, including the 300-tick wait, in `rig.fast()` [source: spec.py:100]. The watchdog message "should be max 0.00" means the rate was 10000 at the crash [source: ServerWatchdog.java message = millisecondsPerTick 0.1, rounded].
- The high rate therefore makes the watchdog about 350x easier to trip. It is a multiplier, not the cause. At 20 tps the crash would need more than 250 ms per tick. The measured lower bound is only about 200 ms, so whether it would crash at 20 tps too is open [inferred].
- What the harness change did: the scratchpad snapshots from 12:45 (`harness.new.py`, `spec.new.py`) already have `WARP_RATE = 10000`, `fast()`, and `spec.run` wrapping the whole test in `rig.fast()`. `diff` against the current files shows no change to any fast/tick/step line. So the 10000-tps stepping was in place during the morning session with the player online, and is not what changed [source: diff].
- Normally frozen idle loops cost about 0.11 ms (warnings about every 11 s, "1002ms or 10020 ticks behind"), so the lag keeps resetting harmlessly. That was true all day, player online or not.

### Why the morning session with the player did not crash
- From 12:34 to 15:45 `random_tick_speed` was 3. The sculk spec (4096 for 20 ticks) ran at 16:09, while Screendead was offline (15:45-16:23), and it restored 3 [source: trace mtimes, logs].
- Crash 1 was the first run of the 300-tick copper spec with the player online [inferred: traces are overwritten per run; a morning run with the player would have crashed the same way]. Crash 2 ran on the leaked 4096 with the player online.
- The recent harness changes (fast() at 10000 tps around the whole test) lowered the tolerance, but did not create the load.

## Confidence
High that the leaked `random_tick_speed=4096`, plus many ticking chunks, is the root cause: the crash stats, the saved `game_rules.dat` value, the trace timing and the stack location all agree. Medium on the exact per-tick cost figures, which were estimated, not measured.

## The server running now
Main is still at 4096 [inferred from disk]. Every stepped tick on main is about 1365x more expensive in its 785 forceloaded chunks. Any randomly-ticking block in a main build (copper, ice, crops, leaves, and so on) now changes state far more often, which can fail tests spuriously. If Screendead joins while a long `wait` is stepping, main will crash again.

## Fix

Two fixes are needed: fix 2 for (b) and one of the fix 4 options for (a). Fixes 1 and 3 are cleanup.


1. **Data, now.** Put the gamerule back on main. Either run `gamerule random_tick_speed 3` over RCON (one harmless command, but it is a command to the server, so run it only when allowed), or edit `game_rules.dat` while main is stopped.
2. **Harness: reset to a known baseline at every rig start.** This also covers a server killed mid-test, where `finally` cannot run. In `redstone/harness.py`, `Rig.__init__`:
   ```python
           ox, _, oz = origin
           sx, _, sz = size
           # A test that died mid-run can leave this raised, and the world saves it.
           self.r.cmd("gamerule random_tick_speed 3")
           if server == servers.MAIN:
   ```
3. **Specs: restore in `finally`.** Add this to each test that raises the gamerule (copper_oxidation_fires_observers' one test, and the three sculk_detects_ice_melt tests):
   ```yaml
     finally:
     - gamerule random_tick_speed 3
   ```
   This covers a failed step or exception while the server lives. Fix 2 covers crashes.
4. **For (a), pick one or combine (the properties options need a main restart):**
   - **`simulation-distance=8`** in `server/server.properties`, keeping `view-distance=32` so the player still sees everything. All plots are forceloaded and tick anyway, so a simulation distance of 32 only adds about 4000 empty desert chunks to every stepped tick. At 8 that is about 289. Margin is limited, though: 785 forceloaded chunks at 4096 already produced about 25 s of lag at 20 tps with no player (17:05:27). A future 4096 spec with a longer wait could still crash an empty main.
   - **`max-tick-time=300000`.** With the harness at 10000 tps, the watchdog measures accumulated schedule lag, not one hung tick. This removes the 60 s cliff and still catches a real hang within 5 minutes. The cost is that a stall shows up later.
   - **Run random-tick specs on a satellite, not main.** A satellite force-loads only its plot and uses simulation distance 2, for example by giving `library/mechanics` a plot through `plot_for`, or by running those two specs with `REDSTONE_SERVER=sat1`. This is the most robust, but it is a bigger change.

## Verifying safely (without disturbing the running suite)
- **Offline, now:** re-read the `random_tick_speed` bytes in `server/testworld/data/minecraft/game_rules.dat` after fix 1 and a save. They should read `00 00 00 03`.
- **After the suite finishes:**
  1. On main, with no player, run the copper spec alone: `pytest "tests/test_library.py::test_spec[copper_oxidation_fires_observers::oxidation step pulses the observer, waxed does not]"`. Check that `gamerule random_tick_speed` reads 3 afterwards.
  2. Tail `logs/latest.log`. "Can't keep up" should show the lag growing during the 300-tick wait while staying well under 60 s, with 785 chunks and no player.
  3. Repeat with a player online. Confirm no crash with fix 4 applied, and optionally reproduce the crash risk only with simulation-distance 32 on a satellite, never on main.
- **Crash-path test:** kill a satellite mid-copper-test, restart it, run any other spec, and check that the gamerule reads 3. That exercises fix 2.
