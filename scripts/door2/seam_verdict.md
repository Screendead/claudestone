# Front (a) verdict: seamless under 6 gt at 3 gt open?

Written 2026-09-30, after the laptop restart. Offline only: no server, RCON, pytest or git, and nothing written to the repo.
Labels: SOURCED (file:line), COMPUTED (a script I ran; script and output named), INFERRED (my reasoning; the check is named, if any).
Units: game ticks (gt). "S" = a movement is credited at the tick its event runs (motion start).

## 0. Verdict: SUB6_FOUND, for the opening schedule only, in-model

- **An opening schedule with opening 3 and seamless 3 (S) replays cleanly** in my own port of the 26.3 piston code [COMPUTED `verdict/replay_slime.py` → `verdict/replay_slime.txt`; checks in `verdict/checks_slime.py` → `verdict/checks_slime.txt`].
  - Every movement that touches a visible or interior cell starts at t0 or t3. So seamless is 3 under S, C and R1, and at most 5 under R (pull = start + 2) [INFERRED from the event list plus Door_Rules.md:622-630].
  - The record is 3 open / 6 seamless (0.15 s / 0.3 s) [SOURCED squid_records.md:5]. Opening ties, and seamless is lower under every crediting convention. By the ranking rule that is a Fastest win (Door_Rules.md:620, 640-646).
- **What it does and does not overturn.**
  - B's theorem (seam_bound.md §5) **stands under its own assumptions A1-A7**. A2 (no slime/honey) is an explicit assumption there (seam_bound.md §3). B's §6 says its slime attempts "do not show that it can't", and §8 ranks slime as loophole #1.
  - This schedule is that loophole made concrete. It uses two slime blocks to take away the "+3 to hide the slot piston" charge, and no piston ever pulls C from a slot.
  - verify_2 R3 is scoped the same way: "Beating the plain record on speed is impossible in this mechanic set" (door_3x3_verify_2.md:46), where the set excludes slime ("Slime, honey and entities are still unmodelled", :44; door_3x3_design.md:266). So R3 is not refuted as written. Only an unscoped reading ("seamless 6 is a floor for 26.3 doors") is refuted [SOURCED lines; INFERRED reading].
- **What is NOT shown.** Defaulting to "not shown" on each of these:
  1. **Not run on a server.** The slime steps rest on my port of PistonStructureResolver, and no library spec proves them: `library/mechanics/` has only `piston_glazed_terracotta_slime_barrier` for slime.
  2. **No closing or reset sequence.** A door that cannot close is not a record, so this is the largest gap (§5).
  3. **No wiring.** That covers the ~26 in-phase events and their order, and the power for piston Z, which has to fire (H2) the tick it is spat into slot (-1,0).
  4. **The rules reading.** I read the untiered "Seamless" title as FULL. Wall and floor blocks moving during opening is allowed under FULL but not SUPER (§4).
- So what is shown is a kinematic counterexample to the floor, not a record door. Next steps are in §6.

## 1. The Squid definitions (quoted)

From docs/research/squid_rules.md, the file the brief names [SOURCED]:
- :32-35 Volume: "W*H*D of the circuitry's bounding box, measured CUMULATIVELY across every opening/closing operation and both stable states (the box anything ever occupies). Blocks and entities both count. Excluded: the door frame, the input device, anything inside the hallway except in the open state. Circuitry ignores door/outer-surface/hallway blocks that fit the type. Ties go to the earliest date."
- :38 "1 OPENING TIME: input -> end of the last block movement that makes the hallway match the opened pattern."
- :39 "2 OPENING VISIBLE (SEAMLESS) TIME: input -> last visible block movement inside the hallway (z-fighting counts)."
- :57-62 Tier table. FULL = "L" for the front of the closed door, when opened and when closed, and "-" during opening and closing.

The full text these paraphrase [SOURCED scratchpad/squid_repo/reference/Door_Rules.md]:
- :642 "OPENING TIME: time from input interaction to the end of the last block movement such that the arrangement and composition of blocks inside the hallway matches the “opened” pattern specified by the build’s **\<type\>**."
- :644-646 "OPENING VISIBLE TIME (OPENING SEAMLESS TIME): time from input interaction to the last visible block movement from inside the hallway, or if the build does not have a final visible block movement due to continuously running clocks, to when the build reaches its stable open state. NOTE: “visible block movement” includes z-fighting block movements."
- :622-630, the ending time of a movement: "0 to 2gt pulse extension: Starting time of block or piston movement + Pulse length received / Standard extension: … + 2gt / Instant retraction: Starting time of block or piston movement / Standard retraction: … + 2gt".
- :573-579 Volume: "**Volume = width * height * depth** of the circuitrywiring of the build … Each dimension is cumulatively measured across every closing/opening operation and opened/closed state." Exceptions: "Exclude any door, outer surface, hallway blocks if not required to be the block that fits the \<type\>’s hallway composition in the open state, the door frame and the input device" and "Exclude blocks or entities inside the hallway except in the open state."
- :125 "seamless doors must match the \<type\>’s hallway composition i.e. no circuitry is visible inside the hallway."
- :708 "CIRCUITRY: as WIRING, but ignores any door, outer surface, hallway blocks that fit the \<type\>’s hallway composition."
- :722 "QUARTZ-LIKE BLOCKS: blocks that keep the build functional before and after replacing them with quartz blocks."
- :289 "ONLY WIRING SLIME // HONEY // GRAVITY BLOCKS: These blocks do not appear inside the hallway." This is an optional component restriction, so by default slime may pass through the hallway [INFERRED from its placement under the restrictions list].

## 2. The checker: an independent port, validated on design B

`verdict/pistonsim.py` is written directly from the 26.3 source. It shares no code with relax*.py, door_planner.py or seam_bound.py.

What it ports [SOURCED mc-src/net/minecraft/world/level/block/piston/]:
- `PistonStructureResolver.java:25-191`, line by line:
  - the push limit of 12;
  - back-drag (99-113);
  - collision reorder (124-138, 164-175);
  - branching over `Direction.values()` minus the push axis (177-191);
  - no sticking between slime and honey (68-74);
  - skipping non-pushable neighbours (82-83);
  - the piston's own cell (86, 106, 145).
- `PistonBaseBlock.java`:
  - triggerEvent 139-211: the extend path; on retract, finalTick at +1, the base turns to moving_piston, the spit check at +2 (184-188), then a pull or a removal (190-203);
  - moveBlocks 257-330: the head cell is set to air before resolving a pull (259-260);
  - isPushable 213-255: an extended piston or a block entity is not pushable.
- `PistonMovingBlockEntity`:
  - a forced finalTick sets a source piston to air and places everything else (259-280);
  - a natural landing places movedState (291-313);
  - landing happens at the end of start + 2, and the block can move again at start + 3.

What it enforces:
- A piston can fire again no sooner than 3 ticks after its last event.
- Only real (non-moving) blocks can act or be pulled.
- Events run in the listed order inside phase g.

**Validation** [COMPUTED `verdict/replay_designB.py` → `replay_designB.txt`]:
- Design B's 16-piston schedule (door_3x3_design.md §3.2) replays with every event legal.
- The open state is clean, with opening(S) = 3 and seamless(S) = 6. That matches door_3x3_design.md:199-215 and A's replayB3.

Bugs found while building it (both fixed before the results above): a tuple-unpack error, and landing a retracting base through finalTick, which wrongly deleted it.

**Slime paths** [COMPUTED `verdict/t_resolver.py` → `t_resolver.txt`]. Design B uses no slime, so these were unit-checked separately against expectations taken from the source lines, not from other code. 9/9 pass:
- back-drag stops at the first non-sticky block (99-113);
- a branch takes a retracted piston but skips an extended one and a moving one (82-83, 184);
- slime and honey do not stick; slime and slime do (68-74);
- 12 blocks including branches are allowed and 13 refused (95, 110, 154);
- a branch whose front cell is obsidian fails the whole move (145-146);
- obsidian beside slime is skipped (82-83);
- a dragged slime line-pushes a retracted piston (122-161);
- back-drag stops at the pusher's own cell (106).

One case failed first. That was my test's fault: the quartz was not touching any slime. I rebuilt the case and it passes.

## 3. The counter-schedule ("slime carrier")

Coordinates are (x, y, z):
- frame: x, y ∈ 0..2 at z = 0;
- hallway: x, y ∈ 0..2 at 1 ≤ |z| ≤ 3, with quartz walls, floor and ceiling;
- M = (1,0,0), E = (1,-1,0), E2 = (1,-2,0), E3 = (1,-3,0).

All pistons are sticky. "held" means extended in the closed state, with its head at +1.

**Closed state:**
- 9 quartz door blocks in the frame.
- Slime N in slot (-1,0,0), slime S2 in slot (2,-1,0), and static quartz in slots (-1,2,0) and (3,2,0).
- Spares X (-2,-2,0), spX (-2,-1,1), spY (-1,-1,1), spR1 (3,-1,1), spL2 (-1,-1,-1), spR2 (3,-1,-1).
- Everything non-quartz sits in hidden cells or in slots, which are covered while closed.
- `check_closed`: no problems. There is no non-quartz block in a visible wall cell [COMPUTED].

| piston | base | facing | role |
|---|---|---|---|
| P_TL, P_TM, P_TR | (0..2,4,0) | down, held | t0: TL, TM, TR into the top slots |
| P_L / P_R | (-2,1,0) / (4,1,0) | E / W, held | t0: L → (-1,1), R → (3,1) |
| P_BR | (4,0,0) | W, held | t0: BR → (3,0) |
| P_BL | (0,-2,0) | up, held | t0: BL → (0,-1) |
| A | (-2,0,0) | E | t0: spits N (-1,0) → corner (0,0,0). N drags walls (-1,0,±1) into the hallway (0,0,±1) |
| K0 | (-3,-1,0) | E | t0: spits piston Z (-2,-1) → corner (-1,-1). t3: spits X into the corner and pushes spX into (0,-1) |
| Y | (-1,-2,0) | up | t0: spits Z from the corner into slot (-1,0). t3: spits X into (-1,0) |
| Z | (-2,-1,0) | E | t0, on arrival in (-1,0), fires at once (H2): pushes N (0,0) → M (spat) and BM M → (2,0) |
| P2 | (1,-2,0) = E2 | up | t0: 0-tick; head into E, pulls N M → E and drags C centre → M |
| XP | (-2,-3,0) | up | t0: spits X (-2,-2) → (-2,-1) |
| T3 | (2,-3,0) | up | t3: 0-tick pull of S2 (2,-1) → (2,-2). The structure is 11 blocks (see below) |
| Wp / Wm | (-2,0,±1) | E | t3: pull the walls back from (0,0,±1) to (-1,0,±1) |
| PLX, AX, ZP | (-4,1,0), (-2,2,0), (-3,0,0) | E, down, E | t3: P_L → (-3,1), A → (-2,1), Z → (-2,0). This clears Z out of the slot |
| FL1, FR1, FL2, FR2 | (-3,-1,1), (4,-1,1), (-2,-1,-1), (4,-1,-1) | E/W | t3: refill the four dragged floor cells from hidden spares |
| CF | (-1,-1,2) | -z | t3: spits spX from (-1,-1,1) into corner (-1,-1,0) |

**T3's structure at t3**, all moving one cell down [COMPUTED; the sizes are in `checks_slime.txt`]:
- S2 (2,-1) → (2,-2);
- back-dragged BM (2,0) → (2,-1);
- the branch into N: N E → E2, with C back-dragged M → E;
- P2, pushed as a line: E2 → E3;
- floors (1,-1,±1) and (2,-1,±1);
- BL (0,-1) → (0,-2), which pushes P_BL down to (0,-3).

**Event order** [COMPUTED as listed in `replay_slime.py` SCHED]:
- t0: P_TL, P_TM, P_TR, P_L, P_R, P_BR, P_BL (held retracts), then A, K0, Y, Z, P2, XP (0-ticks).
- t3: Wp, Wm, PLX, AX, ZP, T3, FL1, FR1, FL2, FR2, CF, K0, Y (0-ticks).

**Result** [COMPUTED replay_slime.txt, checks_slime.txt]:
- Every event is legal. Visible or interior movement happens only at ticks {0, 3}.
- The frame and hallway are empty after phase g of t3, so opening(S) = 3 and seamless(S) = 3.
- The strict open-state check finds nothing wrong: every frame and hallway cell is air, and every cell sharing a face with them (the 12 slots plus the walls, floor and ceiling for |z| ≤ 3) holds quartz.
- Final slots:
  - top: TL, TM, TR;
  - left: static quartz, L, X;
  - right: static quartz, R, BR;
  - bottom: spX, C, BM.
- Every piston and slime ends in a hidden cell.

**Order constraints inside phase g** [COMPUTED `verdict/order_t0.py` → `order_t0.txt`; adjacent swaps plus targeted moves]:
- t0:
  - P_BL and P_BR run before A (P_L is optional: N skips P_L's head);
  - then A → K0 → Y → Z → P2;
  - K0 runs before XP;
  - the top ring's order doesn't matter.
- t3:
  - PLX → AX → ZP;
  - ZP runs before Y;
  - T3 runs before the four floor refills;
  - FL1 → CF → K0 → Y.
- This is the requirement list for whoever builds the relays, the analogue of design B's `requirements()`.

**Controls** [COMPUTED checks_slime.txt]:
- Dropping T3, Z, P2 or Y makes the replay fail.
- Dropping Wp or AX leaves problems in the open state, with opening 13; dropping CF leaves one unfilled slot.
- Order matters: Y before ZP fails. T3 first is fine.

**Where the proof breaks** [INFERRED; the checker confirms the schedule]:
- seam_bound.md §5 case (α) assumes C's first mover is a piston S whose base sits in the slot E (F4 under A2). Here C is moved at t0 and t3 only as a back-dragged neighbour of slime N.
- The t3 move uses no piston in E. S2's pull reaches N through a slime-slime branch (PistonStructureResolver.java:184), and it pushes P2 out of E2 as part of N's line (130-160). So E2 does not need to be empty beforehand, which was the conflict that forced the slot-piston shape (seam_bound.md §5 "With opening = 3").
- B's §6 attempt "slime spat into M at t0 … the pull back needs the spitter's base (E2), which is still locked" assumed the slime enters M from E. Here it enters through the corner (0,0), spat by Z, which Y and K0 carry into (-1,0). That leaves E2 free for P2.
- seam_wild.md §3.6 (a) and (b) did not combine a second slime with the line push of P2.

## 4. Rules and tier checks

- **Tier.** The record title is plain "Fastest Seamless 3x3" [SOURCED squid_records.md:5]. I judge against FULL, which needs clean states with no requirement during opening [SOURCED squid_rules.md:57-62]:
  - Closed: the frame is quartz, the hallway is air, and walls, floor and ceiling are quartz. Slime and pistons in slots are covered by the door blocks and walls [COMPUTED check_closed; INFERRED geometry].
  - Open: clean [COMPUTED strict check].
  - During opening: slime and pistons pass through the frame, slots and hallway, and wall blocks move. FULL allows this; SUPER would not [INFERRED].
  - Design B also shows a piston in slot (0,-1) during t3-t6, so the record-shaped design isn't SUPER either [SOURCED door_3x3_design.md:153, 207-211].
- **Covered slots (inherited assumption).** Slots may hold pistons or slime while closed, because the door blocks and walls cover them. That is design B's reading (door_3x3_design.md §2.1 "Closed state"), and the record's hidden-slot technique depends on it too. I did not re-derive it from Door_Rules.md:99 ("Composition of the hallway: when both closed/open").
- **Hallway composition.** The walls and floor end as quartz in their original cells: the dragged ones are replaced by quartz spares, pushed in from hidden cells [COMPUTED]. No non-quartz wall block is needed, so the reading of Door_Rules.md:99/111 on wall composition does not matter here.
- **Crediting.**
  - S, C and R1: opening 3, seamless 3.
  - R: the 0-tick pulls at t3 are credited 5, so 5/5. That equals the logged JensundLars 2021 slime door ("0.25s newest terms" = 5 gt; door_gap.md:28-29) [INFERRED].
  - The record's own 3 gt opening implies Squid does not use R for it (design B is 5/8 under R) [SOURCED door_3x3_design.md:21-45].
- **Volume.** Not relevant to front (a). Not measured.

## 5. Gaps and risks, ranked

1. **Closing and reset (blocking for a record).** The open state is not the closed state reversed:
   - floors shifted by one cell;
   - 5 spares consumed;
   - N, S2, P2, BL, P_BL and Z displaced.
   The door still has to close to the same closed state and reopen, with unlimited uses (Door_Rules.md:509-518). Not attempted.
2. **Slime mechanics on the server** [INFERRED from source; not proven by spec]:
   - the 11-block T3 structure: the slime-slime branch, the back-drag of BM and C, and P2 pushed inside the line;
   - A's spit dragging the walls into the hallway;
   - N being spat (real) while the dragged walls stay moving.
   Suggested spec: `slime_carrier_bottom_row`, the t0 and t3 core on a bare frame.
3. **In-phase order and wiring.**
   - The primitives are proven on sat1: ordered 0-tick chains (spec `piston_zero_tick_chain_same_tick`), H2 (`spat_piston_fires_same_tick`), and mid-tick depower (`piston_moved_source_zero_tick_depower`) [SOURCED door2/mechanics.md].
   - The schedule needs about 13 ordered events per tick, and none of the relays exist.
   - Z is the hardest relay [INFERRED from H2, door2/mechanics.md §3; unbuilt]. Its power has to follow these steps:
     - It must be **unpowered** at (-2,-1) and in the corner (-1,-1), because a spat piston that lands powered fires at once (H2).
     - It must be **powered** the moment it lands in (-1,0).
     - It must be **depowered** inside the same phase g, so that its push is a 0-tick spit.
     - All of this happens while its neighbours are moving (L into (-1,1), the walls away). One possible source is QC through the static quartz at (-1,2).
   - P2 is pushed to E3 and must land unpowered there, or it re-extends at +3 [SOURCED door2/mechanics.md §4].
4. **Directionality.** The update order (WENDUS) may force some events into a different order when the door is rotated [SOURCED door2/mechanics.md "What surprised me" 2]. Not checked.
5. **Model limits.** No entities, no client rendering, no chunk or locational effects.

## 6. Recovery status and next steps

**State after the restart**, checked 22:06 and again at 22:41 [COMPUTED `ps`, `docker ps` on the desktop, log tails]:
- **Still running on the desktop under relax7** (wrappers from 21:40 and 21:55):
  - MULTI at 3.0M nodes, still in t=3 branches (2,930 s);
  - OOP at 2.0M nodes (2,257 s);
  - SLIME and DROP: no progress line yet.
- **ALL was never launched.** None of the four runs has a result.
- **Stopped:** the laptop local6 jobs, with no result (see local6/HANDOFF_from_copy.md).
- **Launched by me:** nothing.
- **How the runs relate to this result** [INFERRED]:
  - This schedule needs z moves: the wall drag and restore, the floor refills, and CF.
  - So a SLIME "none" (in-plane) would not contradict it, while an ALL (OOP + SLIME) "none" would. That points to a model bug in one of the two.
  - The B0 "none" (no slime) stands: seamless ≥ 6 without sticky blocks, now backed by B's proof and A's exhaustive run.

**Next steps, in order:**
1. **Server-test the bottom-row core.** A spec that runs t0 and t3 with only C, BM, BL, N, S2, P2, A, K0, Y, Z, T3 and P_BL, with `run: setblock` power (as the mechanics specs do), and expects:
   - C at E at t5;
   - N at E2 and P2 at E3;
   - BM at (2,-1);
   - frame air from phase g of t3.

   This one test turns "in-model" into "proven kinematics".
2. **Design the closing.** The reversed spits need H2 chains through the same corner, and the floor and spare bookkeeping has to reverse. This decides whether it is a door at all.
3. **Only after 1 and 2:** wiring and volume, and the tier question to Squid (T0).

## 7. Files
- scripts/door2/seam_verdict.md (this file)
- scripts/door2/verdict/pistonsim.py: the independent 26.3 port
- scripts/door2/verdict/replay_designB.py and .txt: the validation run
- scripts/door2/verdict/replay_slime.py and .txt: the counter-schedule and its replay
- scripts/door2/verdict/checks_slime.py and .txt: the strict open check, structure sizes, controls and order variants
- scripts/door2/verdict/t_resolver.py and .txt: unit checks of the slime paths in the resolver port
- scripts/door2/verdict/order_t0.py and .txt: the in-phase order constraints
