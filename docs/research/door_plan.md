# Seamless piston door plan: 3x3 target, fallbacks, first concept, work order

Written 2026-09-30 from the scratchpad notes only. No server, RCON, pytest or repo edit was used.

Labels:
- [source: file:line] means I read it there. Scratchpad files are cited by bare name.
  - `RULES` = squid_repo/reference/Door_Rules.md (the full Squid Java ruleset).
  - `MECH` = door_mechanics.md (26.3 decompile reading).
  - `HD` = door_harness_design.md.
  - `TECH` = door_techniques.md.
  - `M:` = docs/MECHANICS.md in the repo, meaning proven on a live 26.3 server.
- [inferred] means my reasoning. Each one names the test that would settle it.

## 0. Headline

**The centre block is the whole problem, and my model can't explain the record.**
- The edge ring of a 3x3 opens in 2 gt using only mechanics that are already proven or read from source (section 2.3).
- Under the 26.3 timing model in MECH, the centre block needs at least two piston moves. I can't derive a way for those two moves to finish by 3 gt. My best bound is ≥ 5 gt, and that is optimistic (section 2.4) [inferred].
- Yet the target record opens in 3 gt [source: squid_records.md:5]. The glass-etho 3x3 is logged at 2 gt [source: squid_records.md:6], and a 2x2 glass door is logged as "open instant" [source: squid_records.md:19].
- So one of these must be true:
  - the model is missing a community technique;
  - Squid's timing convention credits moves differently from the game (section 2.5);
  - the logs were summarised wrongly.
- Settling this comes before any 3x3 build. The cheap way is forensics (T0 plus the Space Walker video), not server time.

## 1. Target and beat conditions

### 1.1 The target
"Fastest Seamless 3x3", plain type [source: squid_records.md:5]:
- holders JensundLars and Sirrcacti, 21 Feb 2023;
- close: instant (0 gt);
- open: 0.15 s (3 gt), open-visible 0.3 s (6 gt);
- 3762 blocks.

It is unverified that nothing newer exists. squid_records.md is one page of Discord search results, newest first [source: squid_records.md:1,4]. Re-read the full #record-logs history for plain 3x3 seamless before claiming anything.

The log does not say which seamless tier the record holds. I read the tier table from the screenshot: SUPER, FULL, SEMI, QUART [source: squid_rules.md:53-64]. This also closes gap G1 in HD, which still lists the table as missing [source: HD:436-437].
- We target **FULL**. It needs no circuitry and no entities visible in three static states: the front of the closed door, open, and closed. Opening and closing motion is unconstrained [source: squid_rules.md:57-61].
- SUPER also constrains motion, which only a real client can check [source: MECH:194].
- Whether "Fastest Seamless 3x3" is a FULL category, an any-tier category or a lower-tier one is unknown. Settle in T0.

### 1.2 How a door beats it
Speeds are compared method by method, in rule priority order. Ties on everything go to the earlier date [source: RULES:620, 640-656]. So the ways to win are, in order:
1. Opening time ≤ 2 gt. This wins outright whatever the other times are.
2. Opening time 3 gt with open-visible ≤ 5 gt.
3. Open 3/6 gt with close 0 gt and a smaller close-visible time. The record's close-visible time isn't in the log, so I need it from the source.
4. Then the reset times [source: RULES:652-656].

[inferred from the rule text] A matching time is not enough, because ties go to the earlier record. Closing speed only matters if both opening times tie. For route 1 or 2, a simple 2 gt close is fine, and a 0 gt close can wait.

### 1.3 Fallback targets, in order
1. **Plain 2x2 seamless (FULL), fastest.** Every 2x2 block is a corner with two slots, so each block leaves in one pull. By my model the record floor is reachable [source: TECH:16-18; squid_records.md:29-30], but not yet on proven mechanics:
   - 2 gt open needs one unproven spec, the tick-0 alignment `piston_extends_on_repeater_tick`.
   - 0 gt close needs the unproven in-tick spit. The proven spit (M: piston_one_tick_instant_transport) is a between-ticks 1 gt pulse, which the rule credits as start + 1, not 0 [source: MECH:168; RULES:624].
   - The fight is over close-visible time, the resets and volume, via "smallest fastest".
   - I have not found the current plain (non-glass, non-flush) 2x2 fastest record in squid_records.md. Find it first.
2. **Flush 2x2 seamless categories.** These records are very active in 2026: Valle0t V2 on 16 Aug 2026 has open 2 gt, close 0 gt, 5 gt visible both ways and 440 blocks [source: squid_records.md:14-18].
   - [inferred] Flush makes the frame-slice slot cells part of the outer surface, visible from the front. The hidden-slot trick in 2.3 then fails, which may explain their 5 gt visible times.
   - Settle by checking the slot visibility in a flush layout with the hallway probe (HD T3).
3. **A restriction niche.** Every combination of restrictions is its own category [source: squid_rules.md:9], for example "no slime // honey", "no observers" or "no entities" [source: RULES:283, 291, 297; TECH:172].
   - [inferred] The ring design in 2.3 uses no slime, observers or entities, so it may qualify for several such categories at once.
   - Settle by searching #record-logs for each combination before building.

Smallest-only categories are not a target. They rely on fragile entity tricks: NaN-motion carts, copied UUIDs, non-ticking entities [source: squid_records.md:20-24,31; TECH:179].

## 2. First design concept: "R9", an edge-pull ring plus a centre module

### 2.1 Frame of reference
- The hallway runs along z. The door faces north: the player stands at z < 0 looking south (repo convention, CLAUDE.md).
- The frame is the plane z = 0, cells x ∈ {0,1,2}, y ∈ {0,1,2}.
- The walls are at x = -1 and x = 3, the floor at y = -1 and the ceiling at y = 3. Walls, floor and ceiling are all smooth quartz, for every z.
- The hallway (the cells at x 0..2, y 0..2) runs on both sides of the frame. A door hallway is "continuable" [source: RULES:37,363].
- **Slot** = a wall, floor or ceiling cell at z = 0 that touches a frame edge cell.

### 2.2 Front view of the z = 0 plane
x runs -2..4 left to right (as drawn, not as the player sees it); y runs top to bottom.

```
y= 4   .  .  Pv Pv Pv .  .      Pv/P^/P>/P< = sticky_piston facing down/up/east/west (base)
y= 3   .  Q  hv hv hv Q  .      hv etc = its piston_head, extended into the slot (closed state)
y= 2   .  Q  D  D  D  Q  .      D = door block (smooth quartz); Q = quartz wall
y= 1   P> h> D  C  D  <h P<     C = centre door block (module in 2.4)
y= 0   .  Q  D  D  D  Q  .
y=-1   .  Q  h^ h^ h^ Q  .
y=-2   .  .  P^ P^ P^ .  .
```

The planes z = ±1 are the plain hallway: quartz ring, air inside. Wiring sits at depth ≥ 2 from the hallway (|x−1| ≥ 3 or y ∉ -1..3) and runs in the z = ±1 and z = ±2 planes behind the walls.

### 2.3 The ring: 8 edge blocks

**Parts list:**
- 8 sticky pistons: 3 above, facing down; 3 below, facing up; 1 each side, facing inward.
- 8 door blocks, 9 with the centre.
- A dust network from the input block. It branches both ways around the ring, because 24 perimeter cells exceed dust's 15-block reach [inferred]. Settle with the harness trace of dust power at the far pistons.
- A lever on the front outer wall.
- **Quasi-connectivity hazard.** Every piston must be directly neighboured by the powered net. A piston powered only through the cell above it will not retract when that power drops, because nothing sends it a neighbour update (proven, M: piston_quasi_connectivity_bud) [source: MECH:239]. The QC cells are (x,5,0) for the top pistons and (-2,2,0)/(4,2,0) for the side pistons. The T3 trace must show all 8 slot cells turn to moving_piston at 0 g. A stuck edge block is a silent failure that the 2 gt timeline would hide.

**Polarity:**
- Closed = pistons powered and extended, heads in the slots, sticky-attached to the door blocks.
- Open = pistons unpowered and retracted, door blocks sitting in the slots.
- Lever on = closed.
- [inferred] The rules don't fix lever polarity. They only require "one interaction → one change of stable state" [source: RULES:700]. Add this to the T0 questions.

**Open timeline.** Tick 0 is the tick the input fixture repeater's output falls. That falls in the scheduled-tick phase (d), at VERY_HIGH priority [source: HD:69-79; MECH:249].

| tick/phase | what happens | basis |
|---|---|---|
| 0 d | Dust drops to 0 at once. Each extended, unpowered piston queues event 1 (a pull), because +2 is a real block, not a moving one. | MECH:134-139, 293; dust is 0 gt [source: MECH:293] |
| 0 g | 8 pull events run. The frame edge cells turn to air at once. Slots and bases become moving_piston. | MECH:141-147 |
| 0 j, 1 j | progress 0.5, then 1.0 | MECH:103-109, 149-150 |
| 2 j | The door blocks land as real blocks in the slots; the bases land retracted. | MECH:150; proven harness-relative in M: sticky_piston_short_pulse_drops_block [source: MECH:152] |

Ring opening time = 2 gt, the standard retraction end of start + 2 [source: RULES:630]. Ring visible time = 2 gt, if the landing tick counts as the end [inferred; the rule text is open, MECH:357].

**Close, simple version:**
- Lever on. Tick 0 is the fixture repeater rising in phase d at HIGH priority.
- The dust powers all 8 pistons, and extend events run at 0 g.
- Each door block is pushed from its slot back into the frame. Each head stays in its slot, still attached.
- Everything lands at 2 j. Close = 2 gt and close-visible = 2 gt [source: MECH:90-109].

**Close, 0 gt version.** This only matters on a full tie (1.2).
1. Power must drop during 0 g, after the 8 extend events have run. Then each piston queues event 2, and it runs in the same phase g. The door block is finalTicked into the frame at tick 0 and the arm becomes air [source: MECH:141-147, 168]. The in-tick variant is unproven.
2. Power must be back before the bases land at 2 j. Each base then re-extends at 3 g, and the heads land in the slots at 5 j [inferred from MECH:127, 155-157].
3. The re-attach motion stays behind the door blocks, so close-visible = 0 [inferred].
4. Close reset ≥ 5 gt. Settle with piston_retract_deaf_until_landed.

The generator for the in-tick cut is the hard part. Driving pistons straight off one dust update orders their events by the dust's HashSet walk, which is locational (proven, M: dust_update_order_locational) [source: MECH:286, 301]. Prefer a cut whose order comes from tick priority: repeater (HIGH) before comparator (NORMAL) in the same tick [source: MECH:278-286]. That only works if both parts are fed from the tick-0 edge without an extra 2 gt diode stage, and I don't have such a circuit. This is open.

**Why the ring is seamless (FULL)** [inferred from geometry; settle with the HD T3 hallway probe for the static states]:
- **Closed.** Each slot cell touches the hallway through one face only, and that face is covered by its frame door block. Its other faces touch wall or ceiling mass or other slots. So the heads in the slots can't be seen from either side. Everything else visible is quartz.
- **Front of the closed door.** It shows 9 quartz door blocks.
- **Open.** The slots hold the quartz door blocks, so every hallway surface is quartz. The piston faces touch the door blocks from behind.
- **Motion.** FULL doesn't constrain it [source: squid_rules.md:60].
- **Risk: rendering.** The client renders a retracting base and head [source: MECH:181-185], but in the ring those sit behind the door blocks. SUPER would still need a client check (MECH §12, last row).

### 2.4 The centre block, and why no fast module exists in my model
Facts behind the argument:
- (a) C's four frame neighbours are edge door blocks. Its other two neighbours are hallway cells (±z).
- (b) Under FULL, nothing but quartz may be in view in the closed state [source: squid_rules.md:60].
- (c) So in the closed state no piston base or head touches C. C's first move can't be a pull, and it can't be a first-block push.
- (d) The only other first move is as a non-first block of a line push from an edge-middle slot, for example the middle row pushed from the left slot.
  - A pulsed push spits only the first block. The others keep moving and land at s + 2 [source: MECH:146, 168; TECH:49].
  - So C is a moving_piston, which is immovable, until 2 j [source: MECH:126].
- (e) C's second move can't be queued before 3 g, because a landing in phase j queues work for the next tick [source: MECH:66-68, 127].
  - If the second move is a pull, C clears at ≥ 5 gt.
  - If it is a 0-tick first-block spit, C clears at 3 gt. But the pusher must stand on C's hallway side, in the hallway. Its retracting base stays there as a moving_piston until ≥ 5 j [source: MECH:149-150], and then it still has to leave. The "opened" pattern needs an air hallway [source: RULES:99,642].
- (f) The line push in (d) also shifts an edge block into the hallway. Every edge-middle cell has one slot, and the ring uses it. So each route through an edge cell needs that edge block to go two deep as well.
  - A slot can't hold slime or honey, because those drag the visible wall cells at z = ±1 [inferred from MECH:216; the branch rule for immovable neighbours is not re-read].

**Result** [inferred]: under FULL with quartz door blocks, the opening time is ≥ 5 gt. Every concrete centre sequence I tried was much slower. A classic DPE-style pull 2 deep is about 11 gt by the stage costs in MECH:222-226.

Settle, offline and with no server:
- Write a scratchpad brute-force planner. An abstract 3x3 plus slots and depth-2 cells; moves are push, pull and spit with the MECH timing (standard land at s + 2, re-trigger at +3, first-block-only spit, a deaf retracting base); FULL visibility enforced in the closed and open states.
- Ask it for the minimum opening time.
- If it finds < 5, the argument above has a hole. If it doesn't, the record uses something outside the model (2.5).

**Centre module candidates, to try once 2.5 is answered:**

| id | idea | open by model | status |
|---|---|---|---|
| M-a | Row push from the left slot (C lands t2 in (2,1)), then spit C into the right slot, which R vacated 2 deep. The pusher leaves the hallway afterwards. | ≥ 5 gt, likely 7+ | [inferred], needs the planner |
| M-b | Vertical double-pull: BM 2 deep into the floor, then C pulled down twice. | ~11 gt | [inferred] from MECH:222-226 |
| M-c | Whatever the record uses | 3 gt | unknown; forensics first (2.5) |

**Honest status:** R9 with M-a or M-b doesn't beat the record. It is still worth building as the harness shakedown door, because the ring is the hardest-working part of any seamless 3x3 and of the 2x2 fallback. The 2x2 version (four corner pulls, 2 gt open) is the first door to run end to end.

### 2.5 The question that decides the 3x3
RULES:624 says "0 to 2gt pulse extension: Starting time … + Pulse length received", applied to "any block or piston movement" [source: RULES:622-626]. The game spits only the first block of a pulsed push, and the rest land at s + 2 [source: MECH:146, 168].
- If Squid credits every block in a pulsed line at start + pulse, a 0-tick row push "ends" C's first move at tick 0 for scoring. Then a 3 gt opening needs only a second move by 3 gt, which is closer to explicable [inferred].
- If Squid credits per block as the game behaves, the record uses a technique missing from MECH.
- HD's formula cross-check (T9: "s + pulse (cut short)") has the same ambiguity [source: HD:178-182]. The cross-check must know which convention applies.

Settle three ways:
1. Add the question to T0.
2. Watch the record video and the Space Walker "Fastest Seamless 3x3 | 0.3s Opening, Instant Closing" tutorial (youtube Jjd2s6FOBro) for how C leaves [source: TECH:194].
3. Write the spec `line_push_zero_tick_second_block` (3.1). It records what the game does, whatever the rule credits.

Also ask T0 which tier the target record holds, and what "etho" means. It isn't in the RULES type list [source: RULES:72-76; grep of squid_repo finds no "etho"]. If etho has no centre block, the glass-etho 2 gt log is no counterexample.

### 2.6 Mechanics R9 depends on, and their status

| mechanic | used for | status on 26.3 |
|---|---|---|
| Sticky pull: event at R, base and block land R + 2 | ring open | proven harness-relative (M: sticky_piston_short_pulse_drops_block) [source: MECH:152] |
| A repeater edge in phase d → piston event in the same tick | tick 0 = the event tick | **unproven** (piston_extends_on_repeater_tick) [source: MECH:123] |
| Dust is 0 gt; dust order is locational | input fan-out | proven (M: dust_update_order_locational) [source: MECH:301] |
| A 1 gt spit places the block early | 0 gt close | proven between ticks (M: piston_one_tick_instant_transport) [source: MECH:168] |
| In-tick 0-tick spit via block events | 0 gt close; M-a | **unproven** (zero_tick_teleport_via_block_events) |
| A retracting base is deaf until R + 2 j; re-extend at R + 3 | close reset, M-a | **unproven** (piston_retract_deaf_until_landed) [source: MECH:157] |
| A landed powered piston extends the next tick | M-a/M-b stage cost | **unproven** (piston_landed_powered_extends_next_tick) [source: MECH:127] |
| Non-first blocks of a pulsed push land at s + 2 | lower bound (d) | code-read only [source: MECH:168]; **unproven** on a server |
| Slot cells can't be seen when closed | seamless claim | geometric [inferred]; probe check (HD T3) |
| Retract motion behind a door block can't be seen | visible time | client-only [source: MECH:194] |

## 3. Work order

### 3.1 Mechanics specs to write first, in dependency order
None of these may start until the servers are free (the task's hard rules).
1. `piston_extends_on_repeater_tick`: every claimed time is counted from this tick 0 [source: MECH:339].
2. `line_push_zero_tick_second_block` (new): a sticky piston pushing a 2-block line on a 0-tick and on a 1 gt pulse.
   - Expect block 1 real at s (or s + 1) and block 2 moving_piston until s + 2.
   - It settles lower-bound step (d) and the game side of 2.5.
3. `zero_tick_teleport_via_block_events`: the in-tick spit [source: MECH:344].
4. `spat_block_moved_again_same_tick` (new): a block spat in phase g is pulled by a second sticky piston that was depowered later in the same phase g.
   - Expect the pull event to see a real block and start at the same tick.
   - [inferred from MECH:64, 146] This is the only way inside the model for a block to take 2 moves inside 3 gt. The planner needs it as a rule.
5. `piston_retract_deaf_until_landed` [source: MECH:340].
6. `piston_landed_powered_extends_next_tick` [source: MECH:342].
7. `double_extender_min_stage_gap`, only if the centre module uses an extender [source: MECH:343].

Harness mechanics T1 and T2 [source: HD:452-458] run alongside 1.

### 3.2 Harness work order (from HD's task list)
- **Now (no servers, no repo edits):**
  - T0 by the user or a browser. Carry over G2-G4 [source: HD:436-442] and add:
    - (i) the pulse-extension crediting question (2.5);
    - (ii) the target record's tier and centre mechanism;
    - (iii) "etho";
    - (iv) lever polarity;
    - (v) whether the landing tick counts as motion.
  - Also:
    - the record forensics;
    - the offline planner (a scratchpad script);
    - a full re-read of #record-logs for the plain 2x2 and 3x3 categories.
- **Offline code, once repo edits are allowed:** T6 (the `door:` file section), T3 (hallway probe), T9 (per-tick runner and timing functions, with the convention flag from 2.5), T4 and T12 (occupancy and volume), T13 (rotation) [source: HD:447].
- **Satellite, once free:** T1, T2, T7 (repeater fixture and tick-0 detection), then the specs in 3.1. Then build the 2x2 corner-pull door, then the R9 ring.
- **Last:** T8 (button), T10 (seamless columns), T11 (reset scan), T14-T17 (origins, mannequin, reload, reliability) [source: HD:448].

### 3.3 Risks
- **The model is incomplete.** Three logged records beat my derived bounds (section 0). Until 2.5 is settled, any 3x3 timeline from me is a floor, not a promise.
- **Rule readings.**
  - Target tier (1.1), crediting (2.5), landing tick (MECH:357), polarity: all open.
  - Ties lose to the earlier date, so matching a record isn't enough [source: RULES:620].
- **Stale records.** One Discord results page only [source: squid_records.md:1].
- **Both input kinds must work.** Player input is before-tick. Pistons start 1 gt later and scheduled parts fire one tick earlier relative to them [source: HD:259-265].
  - A 0-tick generator built for repeater input may turn into a plain pull under a lever click, or the other way round.
  - A real click can't be scripted, so `use()` plus a wind charge plus a manual showroom click stand in for it [source: HD:305-313].
- **Locational and directional behaviour.**
  - Dust order is locational (proven) and neighbour-update order is W, E, D, U, N, S [source: MECH:301-305].
  - A "not locational/directional" claim needs the origins and rotation sweeps (HD T13, T14). The claimed speed must hold everywhere [source: RULES:768-769 via HD:318-319].
- **Seamless during motion can't be tested headless** (client ghosts from spits) [source: MECH:194]. FULL avoids this. SUPER can't be claimed without a client recording.
- **Shared servers.** All server work waits for the other agents. Nothing in this plan touches RCON.
