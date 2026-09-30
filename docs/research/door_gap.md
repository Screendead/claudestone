# Why our model can't reach the logged 3x3 opening times (gap analysis)

Written 2026-09-30. No server, RCON, pytest, scripts.try or repo edit was used.
Planner: `door_planner.py` (assumptions in its docstring). Planner runs: `plan_first.txt`, `plan_all.txt`, and the outputs quoted below.
World download inspected: `worlds/jl2021/` (JensundLars 2021 door), read by `worlds/anvil116.py`.

Labels: [source: ...] = read there. [inferred: ...] = my reasoning, followed by the test that settles it.

## 0. Answer in brief

1. **The 2 gt "glass etho" record isn't a counterexample.** An etho door is a 3x3 with no centre block. The 8-block ring opens in 2 gt using pulls alone, and the planner agrees (§2).
2. **For a full 3x3 the model's minimum is 5 gt under both crediting readings.** This matches the best documented 1.13+ doors: Space Walker (2019) at "0.3 s" in old terms, and JensundLars et al. (2021) at "0.3s (0.25s newest terms)" = 5 gt (§3, §4).
3. **The 2023 record's 3 gt is exactly the tick at which the frame is physically empty.** In the model, the last door block starts leaving the frame at tick 3: its origin turns to air, while it is still a moving_piston in the wall until tick 5. The rule text credits that same pull as ending at start + 2 = 5.
   - So the most likely explanation is that the logged 3 gt counts the hallway as open once the frame cells are air, with blocks still sliding in the walls. The long seamless time (0.3 s = 6 gt) holds the sliding.
   - Both 3 gt 3x3 logs follow this pattern: the plain door at 3/6 gt and the SEMI funnel at 3/9 gt. [inferred; settle with §6.]
4. The other explanations (pre-1.9 mechanics, pistons entering the frame, a summary error) are listed in §5, each with how to settle it.

## 1. Evidence gathered

- **"Etho" = 3x3 with the middle block missing.** [source: r/redstone comments k62t3c0 ("Etho Door -- 3x3 piston door with middle block missing"), ivyl92p ("3x3 iris door (3x3 door without the centre block)"), fomqf8e ("a 3x3 with a hole in the middle is an etho door"), kztbe5h (r/ethoslab: "the 3x3 piston door with the hole in the center"), all via api.pullpush.io]
- **Space Walker + SacredRedstone, 2019, "Fastest Seamless 3x3 Door":** closes instantly, opens in 0.3 s. Seamless 3x3 doors at 0.3 s "have been made before". [source: comment epdhqm5; YouTube Jjd2s6FOBro description: "fastest seamless 3x3 door in the current versions … opening time of 0.3s it's quite unbeatable", 1.13.2+]
- **Space Walker + G4me4u, improved version:** "the fastest it can get in the current versions", 0.3 s open, 864 blocks, 1.5+. [source: YouTube 8ULV27jYUhk description]
- **Space Walker, 2020, "Fastest Possible 3x3 Door":**
  - Open 0.3 s, and seamless at 0.3 s. Earlier 0.3 s doors "always required an extra 0.15s to hide away a piston somewhere".
  - It uses MC-88959 "Jeb / instant double retraction", which was removed in 1.9, so it works in 1.5-1.8 only.
  - [source: comment fjf2qr1]
  - MC-88959: before 15w38 (1.9), a double extender depowered in one tick retracted both pistons at once. [source: Mojira API for MC-88959]
- **JensundLars et al., 2021, "Former Fastest Seamless 3x3 (2 move seamless)":**
  - Description: "Opening and Seamless: 0.3s (0.25s newest terms)", 6336 blocks.
  - This is direct evidence that Squid re-based its timing by 1 gt between the old and new terms. [source: YouTube C2O6Z-U1uJE description; Blolbly comment mh0grjh: "this one is 0.25s seamless (newest terms)"]
- **alugia7, 2020, "Smallest Fastest Possible Seamless 3x3":** Opening .3 s, .45 s seamless. [source: comment g7y5t0m]
- **Squid logs:** plain Fastest Seamless 3x3 (Feb 2023) open 0.15 s / seamless 0.3 s. SEMI-seamless 3x3 funnel (Oct 2025) open 0.15 s / seamless 0.45 s. Glass etho (Apr 2026) open 0.1 s. [source: squid_records.md:5-6, 38-39]
- **Rule text:**
  - A pulled block ends at start + 2 ("Standard retraction"). "Instant retraction" ends at its start. A 0-2 gt pulse extension ends at start + pulse. [source: squid_repo/reference/Door_Rules.md:622-630]
  - Opening time runs to "the end of the last block movement such that the arrangement and composition of blocks inside the hallway matches the 'opened' pattern". [source: Door_Rules.md:642]
  - A build need only work in one Java release. Titles for builds broken in the latest version get "[BROKEN]", and UP-TO-DATE is a separate restriction. [source: Door_Rules.md:29, 321, 524]
- **Source check: a 0-ticked sticky piston pulls the block 2 cells away.** If it extends into air and loses power in the same tick, `checkIfExtend` queues event 1, because +2 is not a moving_piston. `triggerEvent(b0 = 1)` then finalTicks the arm and runs `moveBlocks(extending = false)` on the +2 block. The pull still lands at R+2. [source: mc-src/.../piston/PistonBaseBlock.java:100-113, 154-201] The planner uses this as its PULL move.
- **JensundLars 2021 world (1.16.5), saved in the open state:**
  - Frame plane x=253, hallway y 230-232, z 586-588, running along x.
  - 11 of the 12 slot cells hold quartz. The 12th, top-left (y 233, z 586), is a barrier, which the world uses to mark hallway walls.
  - Behind the slots are rows of sticky pistons (z 584 facing +z, y 228 facing up, z 590-591 facing -z with one slime block at (253,231,590), y 234 facing down with obsidian at z 586).
  - 205 sticky pistons, 9 slime, 9 honey.
  - The world has a `redstonetweaks/` folder (Space Walker's mod), so check its settings before replaying the world.
  - [source: worlds/anvil116.py dump] I did not reconstruct the motion; that needs a simulator or server (§6).

## 2. Planner results (door_planner.py)

Model:
- One plane.
- Piston bases anywhere outside the 3x3, conjured freely. Their bodies never block anything; this is a relaxation, so every result is a lower bound.
- PULL: 0-tick or held, credited R+2, re-movable at R+3.
- PUSH: 0-tick sticky. The first block is spat, real in the same tick and re-movable in the same tick. The rest land at t+2 and can move again at t+3. The push limit is 12. moving_piston cells are immovable.
- No move may carry a block from the wall back into the frame.

| door | metric | reading | minimum |
|---|---|---|---|
| etho (8 blocks) | rule credit | FIRST and ALL | **2 gt**: 8 pulls at t=0 |
| 3x3 | rule credit | FIRST | **5 gt** (plan_first.txt; bounds 0-4 searched exhaustively) |
| 3x3 | rule credit | ALL | **≥ 4** by exhaustive search to bound 3 (9 min run); a bounds 4-5 run writes plan_all.txt (still running at writing); 5 by the argument below |
| 3x3 | physical frame-empty tick | – | **3 gt**, with or without same-tick re-moves of spat blocks |

**5 gt schedule (FIRST)**, exactly as printed in plan_first.txt; cells are (x,y) with (1,1) = C:
- t=0:
  - 0-tick push of the bottom row east. BR goes into the wall, BM goes to (2,0), and BL is spat to (1,0).
  - The same for the top row: TR goes out, TM goes to (2,2), and TL is spat to (1,2).
  - BL and TL are pulled back west to (0,0) and (0,2). L is pulled west (out) and R east (out).
  - C is pulled down into the vacated bottom-middle cell (1,0).
- t=3:
  - C is pulled down from (1,0) into the floor slot, and BM is pulled down from (2,0).
  - BL is pulled west from (0,0) (out).
  - TL is pushed east again to (1,2) and pulled up (out) in the same tick. TM is pulled up from (2,2).
- The last pulls land at 5.
- The idea is a row shift: shift a row sideways to empty an edge-middle cell, then pull the centre through it twice. Both stages are ordinary pulls.

**Physical 3 gt schedule (no same-tick chaining needed):**
- t=0:
  - Push the bottom row east.
  - Pull L, TL, TM and TR out. Pull R up into TR's cell.
  - Pull C east into R's cell.
- t=1: pull the spat BL down.
- t=3: pull C east (out), R up (out) and BM down (out).
- From tick 3 every frame cell is air. The last three blocks are moving_piston in the wall until they land at 5.

**2x2 check** (FRAME set to 2x2): rule credit 2 gt under FIRST and ALL, physical frame-empty **0 gt**. The schedule is two 0-tick row pushes plus two pulls, all at t=0.

**The schedules are not buildable as printed.** Piston bodies are relaxed away. In the 5 gt schedule, C's second pull needs its head at (1,-1), which is where the first puller's body sits. The physical-3 schedule has the same clash at (3,1).
- The minima are still valid lower bounds.
- Whether 5 survives once bodies are tracked is unverified. If it doesn't, the in-model minimum only goes up, which widens the gap.
- A buildable centre mechanism must add an explicit step. For example, at t=3 0-tick-push the spent piston sideways out of the slot, then 0-tick-pull C with a piston one cell deeper. That piston's head extends into the vacated slot and pulls C at +2 in the same phase g.

**Why the rule-credit minimum is 5 under both readings** [inferred from the model; the solver agrees for FIRST, and for ALL up to bound 4]:
- (a) The first block of any push whose base is outside the frame always lands inside the frame. The line starts at a cell next to the base and moves away from it.
- (b) So every schedule's last departure from the frame is a pull, credited at start + 2.
- (c) C needs two moves. Its first move can't be a spit, because a spit needs a base next to C, inside the frame. So C can't move again before t+3.
- (d) C's second move is either a pull (ends at 5) or a push (credited 3 under ALL). A push leaves its first block in the frame, and pulling that block out ends at ≥ 5.

The ALL reading doesn't help because of (a).

## 3. What each record means under the model

| log | open | seamless | fits the model? |
|---|---|---|---|
| glass etho, nanda meow 2026 | 2 gt | 5 gt | **yes**: ring pulls at t=0 (§2). The only question left is how it closes in 0 gt |
| JensundLars 2021 | 5 gt (new terms) | 5 gt | **yes**: exactly the rule-credit minimum |
| Space Walker 2019/2020 | 6 gt old terms = 5 new | same or +3 | **yes** once converted to new terms |
| plain 3x3, JensundLars/Sirrcacti, Feb 2023 | 3 gt | 6 gt | **only** under the physical frame-empty metric (§2), or outside the model (§5) |
| SEMI funnel 3x3, BloxxDev/Kiwii 2025 | 3 gt | 9 gt | same as above; funnel blocks also have depth [source: Door_Rules.md:48-50], so its geometry differs |

A pattern to verify, not a law: in several logs, seamless = open + 3 gt.
- 2x2 glass (viktorpresents, 2025) is 0/3 gt, "open instant".
- The glass etho, the 2x2 flush V2 and the Oct 2025 2x2 are 2/5 gt.
- The plain 3x3 (2023) is 3/6 gt.
- It fails for TNT 3x3 (5/6) and the SEMI funnel (3/9) [source: squid_records.md:6, 8, 14, 18, 19, 38].

The "open instant" 2x2 fits only the frame-empty metric: in-model its rule credit is ≥ 2, and its physical frame-empty time is 0 (above).
- So the same convention (H1) explains two anomalies: 2x2 at 0 and 3x3 at 3.
- The "+3" would be: the last pull starts at the logged open time, lands 2 gt later, and visible motion is counted to the landing tick + 1.
- Counter-evidence: the 2x2 V2 at 2 gt open is not "instant", so under H1 its last block must leave the frame at tick 2. That is possible (a second stage), but unverified.

The two 3 gt logs are the only 3x3 ones whose seamless time is far above their opening time. The model's physical-3 schedule predicts exactly that: blocks are still sliding in the walls for ≥ 2 gt, and other hidden pistons are still moving after the frame is empty. [inferred]

## 4. The "newest terms" shift

- JensundLars's own description converts 0.3 s (old) to 0.25 s (new) for the same door [source: C2O6Z-U1uJE].
- So the old convention counted one extra tick, most likely the landing or render tick, or an input tick that the new one drops [inferred].
- It explains the 2019-2021 "0.3 s" figures, but only 1 gt of the 2023 gap (5 → 3 needs 2).
- Settle it by reading the Door Rules revision history, or by asking a Squid mod what "newest terms" changed (a T0 question).

## 5. Hypotheses, ranked, and how to settle each

**H1. Squid times "open" as the tick the frame cells stop holding real door blocks, not the pull's end at start + 2.**
- [inferred] It is supported by:
  - the model's physical minimum being exactly 3;
  - both 3 gt logs having seamless times ≥ 2× their opening time;
  - the 2021 5 gt door being called the "former" fastest in its own title (C2O6Z-U1uJE).
- A possible rule basis: moving_piston is invisible server-side and is not a block that fits the "opened pattern". The client, though, still draws the sliding block [source: door_mechanics.md §4].
- A second anomaly fits the same convention: viktorpresents' 2x2 glass "open instant" is 0 gt, the model's physical frame-empty time, while the rule credit is ≥ 2 (§3).
- Settle it in three ways:
  - (i) Watch the 2023 record video or world, if one is linked in the log, frame by frame at the tick where the log says "open".
  - (ii) Ask Squid (T0): "Does opening time end when the last door block *leaves* the frame, or when it lands?"
  - (iii) Game side: write the spec `pull_origin_air_at_event` (below).

**H2. Pistons enter the frame or the z = ±1 hallway during opening, and "Instant retraction: starting time" credits their removal at its start.**
- [inferred] The planner does not model pistons as objects.
- A piston spat into the frame is placed in phase g, so if powered it can fire in the same tick (door_mechanics.md §1.4, §2.5). Its base is then a retracting moving_piston for 2 gt.
- By the argument in §2 (a)-(d), such a piston must still leave the frame at ≥ t+3 by a pull, ending ≥ t+5. The only exception is if the rule counts its retraction as "instant", credited at start. That again comes down to how moving_piston is counted, so H2 collapses into H1 unless there is a mechanic outside the model.
- Settle it by extending the planner with retracted sticky pistons as pushable objects that fire in the same tick when spat. Also write the spec `spat_piston_fires_same_tick`.

**H3. The 2023 door is version-specific (pre-1.9 instant double retraction, MC-88959) or uses behaviour since removed.**
- Records need only work in one release [source: Door_Rules.md:524]. With MC-88959 a double extender pulls the centre two cells in one stage.
- It is weakened by Space Walker's 1.5-1.8 door using exactly this and still logging 0.3 s old terms (= 5 new) [source: fjf2qr1].
- Settle it by reading the version field of the Feb 2023 #record-logs entry, and whether the title carries "[BROKEN]".

**H4. The log line was summarised wrongly**, for example 0.15 s is a reset or z-fighting figure, or belongs to a typed category.
- Settle it by re-reading the full Feb 2023 embed, including type, tier, version, video and world link. squid_records.md:5 records only "open 0.15 s, 0.3 s seamless".

**H5. Different geometry.**
- The door blocks may start or end outside the 1-deep frame plane (funnel depth), or the hallway walls in the frame plane may not need to be quartz when open. For a non-FULL tier the composition condition is optional [source: Door_Rules.md:101].
- It doesn't change the centre bound, because the planner already leaves the walls free. It could matter for the SEMI funnel.
- Settle it from the tier in the log and the funnel type image (imgur m41EKUE).

Rejected:
- "Squid's clock starts later (repeater input offset)". A later zero would shorten times, but the 2 gt records (etho, 2x2 V2) match a t=0 pull credited at start + 2 under the written rule. So Squid's zero and ours coincide, and a 2 gt offset would make those doors "instant". The only documented offset is the 1 gt "newest terms" rebase (§4).
- "0-tick pulls within one tick". A pull always lands at R+2, and a pulled block can't be moved until R+3 [source: door_mechanics.md §3.3, §3.6].

## 6. Specs to write (when servers are free), in order

1. **`pull_origin_air_at_event`**
   - A sticky piston pulls a stone out of a 1x1 "frame" cell, driven by a repeater.
   - Probe every tick: the frame cell (expect air at the event tick R), the destination (moving_piston at R..R+1, stone at R+2 after phase j) and the base.
   - This is the game side of H1: it fixes the tick an "air-frame" timer would report against the rule's R+2.
2. **`line_push_zero_tick_second_block`** (already planned): the first block real at s, the second a moving_piston until s+2. This is lemma (a)/(c) of §2.
3. **`row_shift_centre_drop`** (only after a layout with real piston bodies exists; see the §2 caveat)
   - The planner's 5 gt mechanism on a bare 3x1 row plus centre, plus the explicit step that clears the spent puller.
   - t0: 0-tick row push east plus a pull of the centre into the vacated edge cell.
   - t3: the second pull.
   - Expect the frame air from t3 and everything landed at t5. This single spec yields both the physical 3 and the credited 5 figures.
4. **`spat_block_moved_again_same_tick`** (already planned): the 5 gt schedule uses it, though the physical-3 schedule doesn't need it.
5. **`spat_piston_fires_same_tick`**: a retracted, powered sticky piston spat into place fires in the same phase g. It tests H2.
6. **`piston_extends_on_repeater_tick`** (already planned): it anchors tick 0 for all of the above.

Offline, before any server time:
- The H1/H3/H4 log questions for T0.
- Scrape the Feb 2023 entry's world link. If it exists, dump its frame plane with `worlds/anvil116.py`; that reader is 1.16-format, and newer chunks need the `sections/block_states` layout.
