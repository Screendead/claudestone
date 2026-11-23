# Close layout report (close-layout agent, 2026-10-01; saved by the main session from its hand-back)

Labels: SOURCED (file), MEASURED (sat1, plot mechanics_8), COMPUTED (sim.py), INFERRED.

## Verdict
No structural obstruction. The close runs from one input to the closed door's plane in the simulator [COMPUTED
p9_p8.txt]: stages 0 to 8 are measured in game. Of the returns, the trigger chain's east side goes home from blocks, with
no command after the input [COMPUTED rbt_drives.txt; MEASURED 4/4], after two changes to measured blocks (the bus's
west branch re-laid, K_T made sticky): with added blocks alone it cannot, whatever the box [COMPUTED returns.txt]. The
west side goes home from blocks too, with no measured block changed [COMPUTED west_drives.txt; MEASURED 3/3], but for
G, which ends where the opening puts it: its closed cell is Y12's head, so NP12 is lit again until Y12 is re-armed. Y12's
re-arm is done from blocks with Y12 made sticky, no command after the input [COMPUTED y12_holds.txt; MEASURED 3/3]; the
opening's other six relays are not designed.
- Every close mover (15) has power cells that at its stage reach no piston still to fire/wait [COMPUTED constraints.py].
- Wave-1 dead end had three non-structural causes: coupling treated as fatal regardless of order (a piston whose retract
  event ran is a moving block for the rest of c0 g [SOURCED PistonBaseBlock.java:168-178]); opening wiring on free cells
  (top pocket G12/G12b, DS, Z_T, RB_T, RB_S); and a new wake requirement: dust updates only reach Manhattan distance 2
  [SOURCED DefaultRedstoneWireEvaluator.java:20-37], and a sticky retract updates neither the head cell nor the pulled
  block's new cell (flags 276/324) [SOURCED PistonBaseBlock.java:172,259-261,302,347-349]. So QC feeds at (1,5,1)/(1,6,0)
  power T but never wake it in c0; the dead end's G12b fix is insufficient [MEASURED control].
- P6 and T fixed with no change to opening blocks; volume unchanged 1728 [COMPUTED].
- S's H2 feed: shown in the simulator and on a satellite on 2026-11-21: section "S H2 feed" below.
- Stages 0 and 1 from one input: shown in the simulator on 2026-11-21: section "Trigger chain" below.
- DP's on and off (stage 2): seven blocks, shown in the simulator on 2026-11-21, the command is gone: P11 extends at c3
  and is spat in that phase; P6 is not spat, it extends at c4 on NA. Section "DP, stage 2: the design" below.
- P10 and V (stages 3 and 4): two blocks, shown in the simulator on 2026-11-22, both commands are gone: P10 extends at c8
  on design_c's own repeater and V at c11 on a repeater from NA into NV; neither is spat. Section "P10 and V, stages 3 and
  4" below.
- The S feed's inputs (stage 5): thirteen blocks, shown in the simulator on 2026-11-22, the last commands are gone: the
  close runs through stage 5 from the one falling input. F_S is out from c10 to c15 on a repeater that reads RB_ST and a
  stone that cuts its feed; RB_F goes home by itself and G_S is taken out. Section "The S feed's inputs, stage 5" below.
- P7, P9 and P8 (stages 6 to 8): nine blocks and a stone for one glass, shown in the simulator on 2026-11-22: the door
  plane is the closed door's at c25 j, from the one falling input. P7 needs no block: its fire at c3 is used. P9, which
  no block fed, fires after stage 5 and pushes TM and TR; P8 follows; Q does not fire. Section "P7, P9 and P8, stages 6
  to 8" below.
- The returns, first pass (2026-11-22, simulator): the trigger chain cannot go home with added blocks. RB_ST, RB_T and
  RB12 have no route to their closed cells inside the box, whatever drives them; with the box grown RB12 and RB_ST have
  one, RB_T still none: nothing can be moved into (1,5,-1) without changing a measured block. Every fired
  relay is held by its arm, and the four that face up (and K) also by their own payload at R+2. Z9 is re-armed in
  place by command, without re-orienting it: the up relays have a way home, their drives are not designed. Section
  "The returns, first pass" below.
- RB_T's return from blocks (2026-11-22, simulator): 49 blocks and K_T sticky, box 2160. A sticky piston above RB_T, which
  RB_ST powers from its rest cell, does the kick when RB_ST is pulled away; RB_ST does not go home (its route takes eight
  pistons) but a second and a third redstone block move one place each with it round a loop of five pistons; one pulse,
  read from the S feed's dust and sent down a line of repeaters, times the loop and H_T. The trigger chain's east side
  and the S feed's cut end as loaded. Section "RB_T's return from blocks" below.
- The west side's return from blocks (2026-11-22, simulator): 34 blocks, no measured block changed, box 2520. A sticky
  piston west of RB12, built out and held by a redstone block that a second piston takes away and brings back, pulls RB12
  off K's head and pushes it back; K and M_K retract in between. One piston above G then pushes G and RB12 down together:
  M_K, released two ticks after its push, leaves WK beside K, and RB12 lands on a K that cannot push, G being above it.
  One pulse, read from the east return's line. G ends at (-4,3,2) and NP12 is lit again: G's last cell is the relays'
  step's. Section "The west side's return from blocks" below.

Close order [SOURCED plan_common.txt]: 0 P12 retract | 1 T, P9, P1-P6 | 2 P11 | 3 P10 | 4 V H2 | 5 S H2 | 6 P8 | 7 Q H2 | 8 P7
As built [COMPUTED p9_p8.txt]: 0 P12 retract, 1 T (c0) | 2 P11, and P7 (c3) | P1-P6 (c4) | 3 P10 (c8) | 4 V (c11) | 5 S H2
(c14, c15) | 6 P9 H2 with TM and TR (c20, c22) | 7 P8 (c23, Q home at c25 j). Q does not fire.

## Added blocks (9)
- T feed: FT stone (1,6,0) (QC cell of T and P12); DT dust (1,7,0); CT stone cut (0,7,0) isolating DT from G12 (0,6,0).
- T wake: P_R sticky piston (3,6,-1) facing west, extended, head (2,6,-1); HOLD redstone block (4,6,-1) (stand-in).
  Z_T pushes RB_T onto P_R's head at t3; at close P_R pulls RB_T to (2,6,-1), Z_T retracts, its retract event updates T,
  which fires under the lit feed, all in one phase g.
- P6+P11 feed: FP stone (-3,3,0) (powers P11, QC P6 via P11's cell); DP dust (-3,4,0); CP stone cut (-3,4,-1) off NA.
  DP wakes P11; P11's extension wakes P6. NA does not feed FP [COMPUTED].

## Results
Simulator: open state identical to design_c with all 9 blocks [COMPUTED feeds.txt, puller.txt].
Server: close_feeds_probe.redstone.yaml, 8/8 pass [MEASURED]; mutated copy failed both checks (checks live).
- Opening frame/slots per tick match simulator (21 cells, t-1..t16).
- P6 and P11 fire together after P12's retract. Control with NP12 alive: P11 shoves the top row, Q ends at (4,3).
- T fires when Z_T retracts under lit feed; also with real P_R. Controls: P_R without feed -> T stays; lit feed alone ->
  T fires only at c2 j; feed lit before NP12 kill -> P12 stays out (FT is P12's QC cell, so T feed lights after P12's retract).
- Refuted [COMPUTED]: RB_T pusher at (0,6,-1) east (G12 powers it while open).
- 0 gt close INFERRED only (no spit relays in the probe).

## S H2 feed (2026-11-21; simulator, then server)
Option (a) works; (b) and (c) were not needed. Opening and the nine blocks unchanged: open-state diff none, box still 1728
[COMPUTED s_feed.txt]. Stage 5: V spits S into (1,3,0); S fires there, pushes C to (1,1,0) and is spat itself.
- Blocks: F_S sticky piston (1,5,3) facing north, retracted; RB_F redstone block (1,5,2). For a pull inside the phase:
  G_S sticky piston (3,5,1) facing west, extended, head (2,5,1); HOLD_G redstone block (3,6,1) (stand-in, like HOLD).
- Why there: DS (1,4,1) is S's only clean cell that is no wall, door block or moving piston [COMPUTED constraints.txt].
  A redstone block at DS's other free neighbours powers S waiting at (0,3,0) (from (0,4,1)) or P7 (from (2,4,1)); at
  (1,5,1) only T, by QC. Resting east of, above or north of (1,5,1) it changes the opening; south, at (1,5,2), it does
  not [COMPUTED].
- How: RB_F real at (1,5,1) lights DS; the wall (1,3,1) under DS powers S. S spat onto the lit cell fires in that
  phase; S real first is woken by DS's change (distance 2). Pulling RB_F darkens DS inside the puller's event and wakes
  S again: its retract spits C if the pull comes at most 2 gt after S fired; at 3 gt S pulls C back [COMPUTED].
- Drives [COMPUTED]: A, a 1 gt pulse on F_S spits RB_F, G_S's hold removed pulls it to (2,5,1); spit and pull each act
  inside their own block event. B, spit, then F_S's second pulse pulls RB_F home (F_S lands 2 gt after the spit; with
  pulses set between ticks the pull is 4 gt or more after it). C, F_S held out, RB_F lands 2 gt later, F_S's release
  pulls it home. B and C need only F_S and RB_F. In all three T lands lit and stays in.
- T [COMPUTED]: (1,5,1) is a QC cell of T and DS points into T. RB_F real before T's retract event cancels the retract.
  If DS is lit when T lands (2 gt after that event), S must be in (1,3,0), moving in, extended or retracting, or T fires
  into the empty cell. S landing later on the lit cell queues its extension before T is updated, and T's push fails on
  the extended S: the block need not be gone before T lands, as (a) assumed. S at rest under a landed T when DS lights:
  T fires first in sim.py's dust order, S in the reverse; the game walks a HashSet there [SOURCED sim.py wire_update].
- Couplings [COMPUTED]: DS's changes update T, S, P7, Z_S, Z_T and G_S; a P7 feed lit before stage 8 is woken by them.
  After drive A, RB_F at (2,5,1) QC-powers P7 from 2 gt after the pull: one update then fires P7, and the next opening
  fails (P7 stays out). Return in the closed state: HOLD_G back (G_S pushes RB_F to (1,5,1)), then any pulse on F_S; the
  loaded closed state then equals the standard one and opens the same. RB_F QC-powers Z_S at (1,5,2), as ARM_ZS does,
  and at (2,5,1). G_S's base takes (3,5,1), one of P8's four clean cells; (3,5,-1), (3,6,0) and NV (4,5,0) remain
  [COMPUTED constraints.txt].
- Probe: stages 0-5 driven one event per tick by commands (k1-k6): redstone blocks at (-1,5,1) for P10, (-1,3,1) for V,
  (1,6,3) for F_S; glass set and cleared at (1,5,0) is the update T's depower must deliver (item 3). Controls fail:
  no feed; no pull; pull at 3 gt; RB_F spat before T's retract; T landing lit over an empty (1,3,0).
- Server: `close_s_feed_probe` (A, B, C and three controls; 18 cells and DS's level checked against the simulator at
  the deciding ticks) passes 6/6 on sat1, and `close_feeds_probe` still 8/8 [MEASURED 2026-11-21]. Drive A's pull inside
  one phase matches the simulator at every check, mid-pull moving pistons included; at A's end RB_F is at (2,5,1), G_S
  and F_S are retracted and every down-facing sticky piston is in [MEASURED]. Its steps, read back from the YAML and replayed in the simulator, pass
  6/6; without F_S or RB_F A, B and C fail; without G_S A fails, B and C pass [COMPUTED export_s_feed]. Drive A's use
  inside one phase (the 0 gt close) is INFERRED: commands cannot order events inside a phase.

## Trigger chain, stages 0 and 1 (2026-11-21; simulator; measured on a satellite)
One falling input runs E0, P_R's release, the NP12 kill, T's extension and spit and P12's retract inside one block-event
phase, c0 [COMPUTED trigger.txt]. Not as framed in two ways: the T feed is armed in the open state instead of lit in c0, so
the order is T first, P12 after; and DP (stage 2) is still a command here (its blocks came later: "DP, stage 2: the
design").
- Blocks: 36 (13 dust, 16 glass or stone, 5 pistons, 1 repeater, 1 redstone block; 12 and 17 before the west branch was
  re-laid on 2026-11-22, below), I_A sticky (part 1), HOLD (4,6,-1) gone. Opening: open-state diff none, the door's
  pistons and the door plane the same at every tick; box 12x14x12 = 2016 through the opening and the close since the
  re-lay, 1728 before it [COMPUTED].
- Levels: block events run first in, first out, so an event queued inside an event of level n runs after every event of
  level n. Order that rests on levels does not depend on dust's update order [SOURCED sim.py tick; INFERRED].
- Bus: dust fed by K_in (1,8,-2), lit while the input is on. East (2,8,-2), (3,8,-2), (3,8,-1) on stone (3,7,-1) above
  P_R: P_R's hold. (4,8,-2) on stone (4,7,-2) feeds a 4-tick repeater (4,7,-1) into AP. West from K_in's top, over the
  input repeater (re-laid 2026-11-22, "The bus re-laid" below): (1,9,-2) on K_in, (0,10,-2) on stone (0,9,-2), (0,9,-1),
  (-1,9,-1), (-2,8,-1), (-3,7,-1), (-4,6,-1), (-4,5,0), (-4,5,1) on stone (-4,4,1) above M_K. Stone cut (-3,5,0) over DP.
  Until the re-lay: from K_in's south side, (1,8,-1), (0,8,-1), (-1,7,-1), (-2,7,-1), then as now, with a second cut
  (1,8,0) over DT; that is the bus the probes were measured on. The last dust sits on a stone on M_K and the step before
  it rests on glass: with a stone there the stone QC-holds M_K until its own dust is dark and only the end dust updates
  M_K, so M_K's release would rest on the parity of the levels (held for good at 9 and 8, the levels before the re-lay,
  released at 8 and 7) [COMPUTED trigger.txt, ctl 7].
- T feed: piston AP (4,7,0) facing west pushes redstone block RB_ST from (3,7,0) to (2,7,0), beside DT. It lands at t10 j;
  T's last update of the opening is t8 j (P12's head landing), so T waits powered and not updated, and Z_T's retract
  event wakes it. RB_ST at (3,7,0) QC-holds P_R out in the closed state; from t0 the bus does. Why not lit in c0
  [INFERRED]: a pushed block powers nothing until it lands, so an instant on needs a removed cut or a spat block, and
  the block the depower relay can take away must stand beside DT (below).
- DT off: W_T (1,5,0), a piston facing north above T, powered by FT, blocked by Z_T's head. Z_T's retract event queues
  T, then removes its head and queues W_T. W_T's extension updates K_T (2,5,0), a piston facing up under glass (2,6,0)
  and RB_ST: QC-powered by RB_ST and FT and three from DT, so not updated since RB_ST landed. K_T pushes the glass and
  RB_ST up; DT dies inside K_T's event and its change updates W_T, two below FT; W_T's retract event updates T, which
  is spat. That update is the one the S probe's POKE stood in for. Of the cells FT powers, (2,5,0) alone is three from
  DT, and its column can only take a source away from (2,7,0) ((2,6,0) is P7's QC cell) [INFERRED; constraints.txt].
- NP12 kill: K (-4,1,2), a piston facing up under RB12, QC-powered by L (-3,2,2) and armed from the load behind
  design_c's blocker at (-4,3,2). Sticky M_K (-4,3,1) facing down, held by the bus, pulls glass WK (-4,1,1) from beside
  K; K pushes RB12 to (-4,3,2) and G to (-4,4,2). RB12 cannot be pulled inside the box: north is NA's dust, south is z 4,
  above is G's cell, and a sticky piston facing up two below it is QC-powered by RB12 itself [COMPUTED].
- P12: FT is its QC cell, so it stays out while the feed is lit, NP12 dead or not. W_T's retract event updates P12 as
  well as T, so P12 retracts after DT is dark, in the same phase. This replaces "T feed only after P12's retract".
- c0, in order [COMPUTED]: I_A pulls RB_A, P_R pulls RB_T, M_K pulls WK (level 0, any order); Z_T retracts, K pushes
  RB12 (1); T extends, W_T extends (2); K_T pushes RB_ST, DT 0 (3); W_T retracts (4); P12 retracts and pulls SP, K_T
  retracts, T is spat (5). After c0: C real at (1,2,0), (1,3,0) and (0,3,0) air, T and P12 moving.
- Order checks pass: dust's updates in reverse order, I_A's event behind P_R's and M_K's, and both: end-state cells
  the same, each tick's piston events the same set, Z_T to T's spit in the same order. Z_T retracts when the second of
  RB_A and RB_T has left, whichever it is [COMPUTED]. (The cut over DT went with the first west dust, 2026-11-22.)
- Controls fail [COMPUTED]: no W_T (T and P12 get no update); no spacer or no K_T (DT stays lit); no WK (NP12 lives,
  P12 stays out, P11 shoves the top row); I_A not sticky (Z_T stays, T is not woken); DP lit before c0; a 3-tick
  repeater (RB_ST lands at t8 j ahead of P12's head and T fires in the opening); input off fewer than 11 ticks after
  it went on (c0 before t11: feed not armed).
- Through stage 5 with stages 2 to 5 by command (c1 DP on, c2 off, c3 P10, c4 V and F_S, c5 both off, c6 G_S's hold):
  stage 5 done [COMPUTED]. NA relights when RB_A lands (c2 j): P7 is out from c3 over TR at (2,2,0), P1 to P6 from c4,
  P10 from c8. T has landed (c2 j) before stage 5, so RB_F is spat before S lands (drive A, s_feed's ctl 6 otherwise).
- Rest state, return not designed: RB_ST (2,8,0), glass (2,7,0), RB12 (-4,3,2), G (-4,4,2), K out (QC by RB12), M_K out
  again from c3 (RB12 beside it) with WK back beside K, K_T out from c3 (RB_T at (2,6,-1) QC-powers it, NA's relight
  updates it), P_R in, AP in from c8.
- Costs to other items: until the re-lay glass (1,7,-1) under the bus took item 4's down-pusher cell and glass (-1,6,-1)
  one of P10's five clean cells (both free now; a piston at (1,7,-1) fires in the opening all the same, below);
  (-4,4,0) and (-3,5,0), item 5's DP cells, are the bus's support and cut, so the DP stand-in is a redstone block at
  (-3,4,1). In the open state T and K_T are powered and not updated, K since the load: one stray
  update fires them.
- DP, not done in this step. Needed: on after P12's retract event, off after P6's extension, each a block event. P12's retract
  event updates (0,5,-1), P10 and S; P11's base update reaches (-2,4,0) and (-2,3,-1) after P6 is queued. (-2,4,0) is
  beside DP, so DP's own change updates a piston there, and nothing P11's or P6's push frees can block one as Z_T's
  head blocks W_T [INFERRED].
- Probe: `close_trigger_probe` (`export_trigger`): the run above and three controls (glass under RB_ST, W_T or WK
  removed with setblock air strict before the opening), 27 to 47 cells and the levels of DT and DS checked against the
  simulator after c0 and later ticks. Its steps, read back from the YAML and replayed in the simulator, pass 4/4; without
  K_T, W_T, M_K or the dust above P_R the first test fails [COMPUTED]. Server (2026-11-21, sat1): 4/4 [MEASURED];
  `close_feeds_probe` 8/8 and `close_s_feed_probe` 6/6 still pass. Re-exported on the re-laid bus (2026-11-22): replays
  4/4 with the same controls live, lint ok [COMPUTED]; in game 4/4 [MEASURED 2026-11-22, main server on the Mac].

## DP, stage 2: the design (2026-11-21; simulator; measured on a satellite)
Seven blocks light DP after P12's retract and cut it again from the one input: the DP command is gone, the opening is
unchanged and the feed is home again by itself [COMPUTED dp_off.txt; MEASURED 4/4 on sat1, below]. Not as framed in one
way: P11 is spat, P6 is not (below).
- Blocks: RB_D, a redstone block at (-3,4,2), south of DP's source cell (-3,4,1); A_D, a sticky piston at (-3,4,3) facing
  north, behind it; Q_D, a stone at (-3,6,3); R_D, a 1-tick repeater at (-2,6,3) facing east on glass (-2,5,3); TAP, a dust
  at (-1,6,3) on glass (-1,5,3). Opening: open-state diff none, no cell differs outside the seven, the door's pistons and
  the door plane the same at every tick, nothing moves during the load, DP 0 in the closed and the open state, box 1728
  through the opening and the close [COMPUTED].
- Source: A_D out puts RB_D in the source cell, DP 15; pulled, RB_D is a moving block at once, DP 0. At rest RB_D is a
  second QC source of Y12, which ARM_Z11 holds anyway, and powers nothing else [COMPUTED].
- Power: A_D's only power is Q_D, two above it (QC), strongly powered by R_D. R_D reads TAP; TAP reads NP12's dust (0,5,3)
  down the step and its glass passes nothing back: NP12's levels are what they were [COMPUTED]. This is the first pass's
  third way out, power south of DP that outlives K's event: R_D outlives it by one tick.
- Armed: NP12 lights at t6 g; that storm updates A_D, which is not powered yet. R_D turns on at t8 d and updates Q_D's
  neighbours, not A_D: from then A_D is powered and not updated, as T, K_T and K are. One stray update there fires it:
  RB_D lights DP and P11 shoves the top row [COMPUTED].
- On: K's event (c0, level 1) kills NP12. H (-3,3,3), the dust under A_D, dies in it and updates A_D, which R_D powers
  until c2 d: A_D extends at level 2. RB_D lands at c2 j and DP's change updates P11, which extends at c3, level 0:
  three ticks after P12's retract, as a block event, like P_W's on.
- Off: R_D turns off at c2 d, again without an update of A_D. A_D's head lands at c2 j right behind RB_D, and the landing
  updates A_D: unpowered, its retract is queued behind P11's extension. c3, level 0: P11 extends, then A_D pulls RB_D and
  DP is 0 inside that event; DP's change updates P11, which is spat at level 1: S real at (0,3,0). RB_D and A_D are home
  at c5 j and R_D stays off (NP12 is dead): the feed leaves nothing to return.
- What the order rests on [COMPUTED; INFERRED for the game]: a push adds the pushed block's block entity ahead of the
  head's, and phase j runs them in that order (sim.py move_blocks). With the head ticked first, A_D's retract runs ahead
  of P11's extension and P11 never fires (what-if in dp_off.txt). Dust's updates reversed, I_A's event last, both: the
  same piston events in every tick, stage 5 done.
- P6: P11's extension queues P6 (QC through FP) behind A_D's retract; that event finds FP dark and is dropped, in every
  order. P6 extends once, at c4, on NA's repeater with P1 to P5, and stays out, where the closed door has it. It is not
  spat: for that DP must stay lit one event longer. `dp_off_search.py` screens one and two more blocks in the 36 free
  cells of dp_search's region for a design that spits P6 too (rerun 2026-11-22 on the re-laid bus, which freed one
  cell; the counts were 35, 1 of 560, 441 of 152320 and 435, with the same passes): one more, 1 of 576, a dust at
  (-2,4,0) (DP's change reaches it and its own reaches P6, so P6 is queued with P11); built, the opening differs from t1 (RB11 beside it
  lights it and DP in the closed state), lit it points into V, and it stands on P11, whose top the game does not take
  as a support once it extends [INFERRED; the simulator has no rule for support]. Two more: 455 of 161280, 449 of them
  with that dust and 6 without, four ideas: a dust on NA's dust that ties DP to NA, dp_search's row pusher, a redstone
  block beside NA's and NV's dust, and a relay above A_D. Built, each fails: the first three move pistons during the
  load and change the opening, and the relay fires in the opening [COMPUTED dp_off_search.txt, dp_off.txt].
- The relay, the lead for spitting P6 [COMPUTED as set into the open state, not buildable as it is]: N_X, a piston at
  (-3,5,3) facing north above A_D and under Q_D, and D_X, a piston at (-3,5,2) facing down in front of it. K's event
  wakes N_X with A_D, and N_X pushes D_X over the source cell. R_D's turning off at c2 d updates N_X, whose retract
  (c2 g) updates A_D: unpowered with RB_D still moving, A_D spits it, so DP is lit in c2 g and P11 and P6 extend in c2,
  a tick earlier. D_X lands at c2 j beside RB11, which powers it, and pushes RB_D down at c3: both are spat, a tick
  before NA's repeater turns on. RB_D ends at (-3,3,1), beside M_K, and D_X out at (-3,5,1). What stops it: R_D's
  turning on at t8 d updates N_X too, so the built relay runs in the opening and is spent. It needs N_X held in until
  c0.
- Stage 3: P11's head is in (-1,3,0) during c3 and P10 pushes V into that cell, so P10 comes at c4 or later. With stages
  3 to 5 by command one tick later than in the trigger probe (c4 P10; c5 V and F_S; c6 both off; c7 G_S's hold) stage 5
  is done: S real at (1,3,0), C at (1,1,0), and outside the seven blocks the end state is cell for cell that of
  trigger.py's run, where a command lights and cuts DP [COMPUTED].
- Controls fail [COMPUTED]: no RB_D; no A_D; A_D not sticky (DP stays lit, P11 stays out); no R_D; no TAP; no Q_D; R_D at
  2 ticks (still on when the head lands, so A_D is not released, and its turning off at c4 d updates nothing); a dust in
  R_D's place (Q_D is lit by the storm that updates A_D, which fires in the opening); a stone under TAP (NP12's step is
  cut and the opening differs). The input off fewer than 11 ticks after it went on fails as the trigger chain does.
- Costs: A_D armed in the open state (above); RB_D as Y12's second QC source, for whatever returns Y12; the cells
  (-3,4,1) to (-3,4,3), (-3,6,3), (-2,5,3), (-2,6,3), (-1,5,3), (-1,6,3).
- Probe: `close_dp_off_probe` (`export_dp_off`): the run above and three controls (RB_D, the repeater or the tap dust
  removed with setblock air strict before the opening), 52 or 53 cells and the levels of DT, DS, DP and the tap checked
  against the simulator after c0, c2, c3 and later ticks. Its steps, read back from the YAML and replayed in the
  simulator, pass 4/4; without A_D, Q_D, RB_D or R_D the first test fails [COMPUTED]. Server (2026-11-21, sat1): 4/4
  [MEASURED]. The game orders it as the simulator assumes: after c2 RB_D is at (-3,4,1), A_D out, DP 15, R_D off; after
  c3 RB_D and P11 are moving, S real at (0,3,0), DP 0, so P11 extends at c3 and is spat. Trace levels: the tap 10 from
  t32 to t41, 0 from t42 (NP12 killed at c0); DP 15 at t44 (c2), 0 from t45 (c3). The tap dust, R_D and the glass under
  both are in place after the run (read from the world). `close_trigger_probe` 4/4, `close_feeds_probe` 8/8 and
  `close_s_feed_probe` 6/6 still pass.

## P10 and V, stages 3 and 4 (2026-11-22; simulator; measured on a satellite)
Two blocks take the P10 and V commands out of the close: stages 0 to 4 run from the one input, the opening is unchanged
and stage 5 is done with its commands moved to c12, c13 and c15 [COMPUTED p10_v.txt; MEASURED 3/3 on sat1, below]. Not as framed in two ways: P10 needs
no block, and neither P10 nor V is spat (below).
- Blocks: D_V, a dust at (1,4,-4) on the hallway's roof, between NA's dusts (2,4,-4) and (1,4,-3); R_V, a 1-tick repeater
  at (0,4,-4) facing east on the roof beside it, which reads D_V and powers NV's dust (-1,4,-4). Opening: open-state diff
  none, no cell differs outside the two, the door's pistons and the door plane the same at every tick, nothing moves
  during the load, box 1728 through the opening and the close [COMPUTED]. In the closed state R_V is on and six dusts of
  NV's west branch read 12 to 15 where RB_V alone gives 7 to 12; in the open state NV is dark as before. No piston has an
  added cell among its power sources.
- P10 (stage 3), no block: the command hid that design_c's own r_P10 (-1,5,-1), 3 ticks on NA, turns on at c8 d, three
  ticks after NA's relight (RB_A's landing, c2 j). P10 extends once, at c8, level 0, five ticks after P11's spit, pushes V
  into (-1,3,0) and stays out, where the closed door has it, as P6 does at c4. V and P10's head land at c10 j. With r_P10
  taken out of the open state nothing moves at P10 or V.
- V (stage 4): NV is the opening's own feed of V: its last dust (-1,3,-1) points south into (-1,3,0). C_cut cuts it at
  t2 j and it is dark through the open state and the close; R_V feeds it west of the cut. NA relights at c2 j and R_V
  turns on at c4 d: 15 at (-1,4,-4), 12 at (-1,3,-1), which points into air then (S left at c3). V lands on the lit cell
  at c10 j, checks itself and extends at c11, level 0; S lands at (1,3,0) at c13 j. At the end of every tick before that
  nothing powers V waiting at (-1,4,0), nor S at (-1,3,0) or (0,3,0).
- Not spat: the feed is on while NA is lit, so V extends once and stays out, its head in (0,3,0): the closed door has V
  out, there on NV. S is real at (1,3,0) two ticks after V's extension instead of in that phase, which a close by ticks
  can afford. End state against dp_off's run, where commands drive P10 and V: outside the two blocks V is out instead of
  in, its head is in (0,3,0) and NV's dust is lit; every other cell is the same.
- Opening: NA dies at t0 g and R_V turns off at t2 d; C_cut lands at t2 j as before and V retracts at t3. At 2 ticks R_V
  is still on at the cut and the opening differs from t2.
- What the order rests on [COMPUTED; INFERRED for the game]: a tick runs its scheduled ticks before its block entities
  (R_V off at t2 d, the cut at t2 j); a block that lands checks itself, and P10's head, landing above V right after it,
  updates V again (three updates of V at c10 j, each powered); and NA's relight no earlier than c1. Lit one tick early
  (what-if: a redstone block beside (-1,3,-2) before c3), S's event is queued behind P11's extension and finds S moving;
  two ticks early S fires down from (-1,3,0). The feed arms nothing: no piston waits powered and not updated. Dust's
  updates reversed, I_A's event last, both: the same piston events in every tick, the same end state.
- P8: NV's east branch reads the feed through the cut's dust (1,6,-6): 11 there, 1 at (5,5,0) and 0 at (4,5,0), the dust
  that points into P8's QC cell, so P8 stays in. A feed one dust further up NV leaves 1 at (4,5,0).
- Stage 5, still by command: S moves in from c11 g to c13 j, so F_S's pulse and G_S's hold come later than in dp_off's
  run. RB_F spat at c11, c12 or c13 (T's push fails on the moving S), S fires at c14 on landing lit, G_S's hold off at c14
  (behind S's event), c15 or c16: done; at c17 C is pulled back. Spat at c10 or with s_feed's ticks, T fires into the
  empty (1,3,0). The run uses c12, c13 and c15.
- Controls fail [COMPUTED]: no D_V; no R_V; a stone in D_V's place (NA's dusts do not point into it); R_V at 2 ticks; a
  dust in R_V's place (NA and NV one net, the opening differs from t-1); R_V turned round. The input off fewer than 11
  ticks after it went on fails as the trigger chain does.
- Fewer [COMPUTED p10_v_search.txt]: every single block (piston and sticky piston in six facings, redstone block, stone,
  glass, dust, a repeater in four facings at 1 to 4 ticks) built into each of the 180 free cells of x -3..1, y 2..7,
  z -7..2 (175 before the bus's west branch was re-laid; rerun 2026-11-22) and run from the load: 3 of 5760 put S at
  (1,3,0) by c14 with the opening unchanged, and none can be built. Two
  are R_V's idea in one block, a 1-tick repeater facing west at (-2,2,-2) or (-2,2,-1) that reads NA and strongly powers
  the wall block under NV's dust: the first stands on NA's dust (-2,1,-2), the second on r_P4. The third, a 4-tick
  repeater at (-2,4,0) facing west, stretches DP's one tick to c10 d to c18 d above V; it stands on P11, and when it
  turns off V pulls S back. Pairs other than D_V and R_V were not searched.
- Costs: stage 5 ends at c15 instead of c7, since P10 waits for r_P10; NV's levels in the closed state and through the
  close, with (5,5,0) at 1, one short of P8's dust; NA's dusts (2,4,-4) and (1,4,-3) now also point at D_V; the cells
  (1,4,-4) and (0,4,-4). Whatever later moves NA's relight (P7 fires on it at c3, ahead of its stage) moves stages 3 and
  4 with it.
- Probe: `close_p10_v_probe` (`export_p10_v`): the run above and two controls (D_V or R_V removed with setblock air strict
  before the opening), 55 or 56 cells and the levels of DT, DS, DP, the tap, D_V and NV at (-1,4,-4), (-1,3,-1), (5,5,0)
  and (4,5,0) checked against the simulator after c0, c3, c4, c8, c10, c11, c13, c14, c15 and c17 (the controls: c4, c10,
  c11, c14). Its steps, read back from the YAML and replayed in the simulator, pass 3/3; without D_V or R_V the first
  test fails [COMPUTED]. Server (2026-11-22, sat1): 3/3 [MEASURED], every test's failures empty. The game orders it as
  the simulator assumes: after c10 V is in at (-1,3,0), lit, P10 out; after c11 V is out, its head and S moving; after
  c13 S is at (1,3,0). Trace levels (input falls at t40, c0 = t42): NV's dust (-1,4,-4) 0 through c3 and 15 from c4
  (t46) to c17, with (-1,3,-1) 12 and (5,5,0) 1 at c4; D_V's 12 from c3; P8's dust (4,5,0) 0 at every snapshot from c0
  to c17, so P8 stays in. `close_dp_off_probe` 4/4, `close_trigger_probe` 4/4, `close_s_feed_probe` 6/6 and
  `close_feeds_probe` 8/8 still pass.

## The S feed's inputs, stage 5 (2026-11-22; simulator; measured on the main server)
Thirteen blocks take the last three commands out of the close: stages 0 to 5 run from the one falling input with no
command after it, and the opening is unchanged [COMPUTED s_inputs.txt]. Not as framed in two ways: the drive is C, not A,
so nothing is spat and G_S and its hold are taken out; and the feed is cut, not turned off.
- Blocks: R_F, a 4-tick repeater at (2,8,1) facing north on glass (2,7,1); dust D_1 (2,8,2) on glass (2,7,2) and D_2
  (1,8,2) on stone (1,7,2); dust D_F (1,7,3) on stone Q_F (1,6,3), which is above F_S; R_C, a 1-tick repeater at (0,8,2)
  facing east on glass (0,7,2); stone Q_C (-1,8,2); A_C, a sticky piston at (-1,8,3) facing east; stone C_F (0,8,3).
  Eight work and five carry them. Taken out: G_S (3,5,1), its head (2,5,1) and HOLD_G (3,6,1). Opening: open-state diff
  none, no cell differs outside the 13 and G_S's three, the door's pistons and the door plane the same at every tick,
  nothing moves during the load, no added cell changes in the opening, no piston has an added cell among its power
  sources in the closed or the open state, box 1728 through the opening and the close [COMPUTED].
- Drive: C of the S feed, F_S alone. A needs two inputs, a pulse on F_S that ends within 2 gt and a hold that falls at
  c14 to c16, and leaves RB_F parked beside P7. C needs one: F_S out from c9 or c10 and released at c14 (behind S's
  event), c15 or c16; out from c8 or c11, or released at c13 or c17, it fails [COMPUTED by command on SRC_F]. With G_S and
  HOLD_G left in the run is the same, event for event.
- Source: RB_ST, the trigger chain's redstone block. K_T's push in c0 leaves it at (2,8,0), where it lands at c2 j; it
  is at (3,7,0) in the closed state and at (2,7,0) in the open state, so R_F, which reads (2,8,0), is off through both
  and through the opening [COMPUTED]. Why RB_ST [INFERRED]: R_F needs a level that rises in the close and is off in the
  closed and the open state; NA and NV rise north of the door plane, and NP12 and the tap, south of it, fall in c0.
- On: R_F turns on at c10 d: D_1 15, D_2 14, D_F 13, one step down from D_2 (the stone under D_2 passes it; on glass
  D_F stays dark). D_F powers Q_F and its change updates F_S, two below it, as DT does W_T. F_S extends at c10 g and
  stays out; RB_F lands at (1,5,1) at c12 j and DS reads 15. S is moving in from c11 g, so T, which RB_F powers by QC,
  cannot push; S lands on the lit cell at c13 j, checks itself ahead of T's update and extends at c14, and T's event
  fails on the extended S, as in p10_v's run.
- Cut: R_C reads D_2 and turns on at c12 d; Q_C powers A_C, which pushes C_F from (0,8,3) to (1,8,3), the cell above
  D_F and beside D_2. C_F lands at c14 j and cuts the step both ways, as C_cut cuts NV at t2 j: D_F reads 0 in that
  phase and its change updates F_S.
- Off: c15 g, level 0, F_S retracts and pulls RB_F, a moving block at once: DS 0 inside that event, S is updated and
  spat at level 1, one tick after its extension: C real at (1,1,0), (1,2,0) air. W_T retracts with it. RB_F, F_S and S
  are home at c17 j.
- Why a cut [COMPUTED the delays; INFERRED the rest]: a repeater's pulse is at least its delay long, so R_F alone holds
  F_S out to c18 or longer, and R_F is the only delay that turns F_S on at c10 (1 to 3 ticks fail). R_C reads the line
  above the cut, so A_C stays out and D_F stays dark while RB_ST is up. A cut driven from below the cut, or from RB_F's
  arrival, lets go as soon as it has worked, and F_S would fire again.
- After: R_F and R_C stay on and A_C out. With RB_ST taken out of (2,8,0) by command (its return is not designed),
  R_F turns off 8 gt later, R_C 2 gt after it, and A_C pulls C_F back beside a dark D_2, home 12 gt after RB_ST left:
  the 13 blocks are as in the open state. A_C not sticky passes the close and leaves the step cut.
- End state against p10_v's run, where commands drive stage 5: outside the 13 blocks and the cut cell three cells
  differ, RB_F at (1,5,2) instead of (2,5,1) and no G_S at (3,5,1); every dust level is the same. RB_F is where the
  closed door has it, so drive A's return (HOLD_G back, a pulse on F_S) is not needed.
- What the order rests on [COMPUTED; INFERRED for the game]: a redstone block that lands behind a repeater starts its
  delay in that tick (RB_A's landing and r_P10, measured in `close_p10_v_probe`); a conductor that lands above the lower
  dust of a step cuts it in the block-entity phase, and the dust's change updates a piston two away (C_cut and V in the
  opening); a piston that lands checks itself before its neighbours are updated (S ahead of T at c13 j, as in p10_v's
  measured run); and drive C itself (`close_s_feed_probe`). No piston waits powered and not updated: the feed arms
  nothing. Dust's updates reversed, I_A's event last, both: the same piston events in every tick, the same end state.
- Updates: DS's two changes (c12 j, c15 g) update P7, T, W_T, Z_S and Z_T, and S at c15; the changes of D_1, D_2 and
  D_F update F_S alone.
- Controls fail [COMPUTED]: no R_F (F_S never moves, S lands and stays in, C stays at (1,2,0)); R_F at 3 ticks (every
  tick of the feed two early: RB_F is pulled home at c13 g, before S lands); no C_F (F_S and S stay out); R_C at 2
  ticks (released at c17, S pulls C back); glass under D_2; a dust in R_F's place (the feed is lit at c2 j and T fires
  into the empty (1,3,0) at c6); R_C turned round; each of the eight working blocks left out; R_C at 3 or 4 ticks. Q_F
  as glass passes: D_F, two above F_S, is a QC source of F_S by itself. The input off fewer than 11 ticks after it went
  on fails as the trigger chain does.
- Costs: stage 5 is done at c15 and RB_F is home at c17 j. The cells of the 13 and (1,8,3); (2,8,1) was one of RB_ST's
  three free neighbours at (2,8,0), which leaves (3,8,0) and (2,8,-1) to whatever returns it. RB_ST has to stay at
  (2,8,0) through c15, and C_F is home 12 gt after it leaves. Freed: (2,5,1), (3,6,1) and (3,5,1), one of P8's four
  clean cells.
- P7 and the returns, not taken on: P7 fires at c3 as before; RB_F is no longer parked at (2,5,1), so that QC source
  of P7 is gone, and the S feed has nothing left to return. A P7 held in until its stage is updated by DS at c12 j and
  c15 g. South of the door plane the line now has levels that rise at c10 (D_1, D_2) and c12 (Q_C) and stay up, and
  A_C's stroke (c12 g to c14 j), for the stages that follow [INFERRED].
- Probe: `close_s_inputs_probe` (`export_s_inputs`): the run above with no command after the input, and two controls
  (R_F or C_F removed with setblock air strict before the opening), 64 or 65 cells and the levels of DT, DS, DP, the
  tap, D_V, NV's four dusts, D_1, D_2 and D_F checked against the simulator after c0, c3, c4, c8, c10, c11, c12, c13,
  c14, c15, c17 and c20 (the controls: c10, c12, c14, c16; c10, c12, c14, c15, c18). Its steps, read back from the YAML
  and replayed in the simulator, pass 3/3; without R_F, D_F, R_C or C_F the first test fails [COMPUTED]. Server (2026-11-22, main on the Mac): 3/3
  [MEASURED]: F_S out at c10, RB_F at (1,5,1) after c12, S out at c14, the cut after c14, S spat at c15, RB_F home
  after c17; both controls hold; the five earlier close probes still pass.

## P7, P9 and P8, stages 6 to 8 (2026-11-22; simulator; measured on sat1)
Nine blocks and one changed support take the close from stage 5 to the closed door's plane: from the one falling input,
with no command, the door's sixteen pistons and the door plane are at c25 j what the loaded closed state has, and the
opening is unchanged [COMPUTED p9_p8.txt]. Not as framed in three ways: P7 gets no block and is not held, its fire at c3
is used; P9, stage 1 of the plan, had no feed at all and fires after stage 5; Q's H2 is not needed.
- What the close did after stage 5 [COMPUTED s_inputs.txt]: nothing. P8 and Q never fire. P9 never fired in any run: no
  block feeds it (in the closed door RB9 does; Z9 takes it away at t3). TM stays at (3,2,0), Q at (3,3,0), (1,2,0) is
  empty, and P7 is out from c3 with TR at (2,2,0).
- Order: the plan closes the top row as 1 P9 (TM to (2,2,0), spat), 6 P8 (Q down), 7 Q H2 (TM on to (1,2,0)), 8 P7 (TR
  down), so P7 would have to be held in until Q has fired. With P7 on NA at c3 the plan's stage 1 fails: P9 by command
  at c1 and c2 leaves TM at (2,2,0), P7 pushes TR down onto it, TM lands at (2,1,0), R's cell, and P5 stays in [COMPUTED
  what-if]. As built P7 goes first (TR at (2,2,0) at c5 j), P9 pushes TM and TR one cell west after stage 5 and is spat,
  and P8 pushes Q down to (3,2,0). TM and TR end in each other's cells. They are the same block: the closed state loaded
  with the two labels exchanged opens the same at every tick [COMPUTED].
- P7: no block. NA's relight fires it at c3, a tick ahead of P1 to P6. DS's changes update it at c12 j and c15 g: out and
  powered, no event.
- Blocks: R_X, a 2-tick repeater at (2,5,1) facing west on glass G_X (2,4,1), which stands on the hallway's roof beside
  DS; A_9, a sticky piston at (3,4,1) facing east; S_L, a stone at (6,3,1) in place of design_c's glass under LY's dust
  (6,4,1); R_9, a 1-tick repeater at (5,3,0) facing east on glass G_9 (5,2,0); R_8, a 1-tick repeater at (3,5,-1) facing
  north on design_c's stone (3,4,-1); D_8, a dust at (3,5,-2) on glass G_8 (3,4,-2); O_8, an obsidian block at (3,-1,0),
  under the static block (3,0,0). Seven work and three carry them. Opening: open-state diff none but O_8's own cell, no
  cell differs outside the added blocks at any tick, dust levels included, the door's pistons and the door plane the
  same at every tick, nothing moves during the load, box 1728 through the opening and the close [COMPUTED].
- Pulse: R_X reads (1,5,1), where RB_F stands from c12 j to c15 g. It turns on at c16 d and, its input gone, off at
  c20 d: its pulse is its delay long. That gives the S feed's timing to the east side with S's 0-tick already done.
- Shuttle: A_9 is QC-powered by R_X through (3,5,1), the cell above it, and updated by its changes. In front of it is
  RB9, the opening's own redstone block, which Z9 pushed up to (4,4,1) at t3. A_9 extends at c16; RB9 lands at (5,4,1)
  at c18 j, beside LY's dusts (5,4,2) and (6,4,1); A_9 pulls it back at c20 and both are home at c22 j. RB9 stands
  beside LY for 2 gt.
- Wire: LY, the opening's dust from RB_Y to Z_S, dark since t0, runs from RB9's cell to P9. Its dust (6,4,1) stands on a
  glass that passes nothing down to its dust (6,3,0); on S_L it does: 15 and 14 from c18 j to c20 g. In the closed state
  and the opening LY's levels are what they were.
- P9: R_9 reads LY's dust (6,3,0) and points into (4,3,0), the cell above P9. On at c20 d, off at c22 d. P9 extends at
  c20, level 0, and pushes TM and TR; at c22 it is spat: TM real at (2,2,0) in that event, TR lands at (1,2,0) at c22 j,
  P9 is home at c24 j. By command [COMPUTED]: P9 powered before c14 or c15 does nothing (the row is blocked; S's head
  is in (1,2,0) until its spit in c15 g); from c16 and released 1 or 2 gt later it is done; at 3 gt it pulls TM back.
- P8: R_8 reads D_8, which reads NA's dust (2,4,-2) up the step (and DQ's (4,4,-2); the glass passes nothing back), and
  points into (3,5,0), the cell above P8. It is on in the closed state, a second source beside NV's dust, off through
  the open state, and on again from c4 d, two ticks after NA's relight. O_8 makes P8's column immovable while TM is at
  (3,2,0): at c4 d R_8 and r_P5 both turn on, and without O_8 P8 can push Q, TM, R and the static block down if its
  event runs ahead of P5's. With it P8 waits powered and blocked: by O_8, then P5's head, then P9's head.
- Wake: A_9 stands south of P8. Its landing at c22 j updates P8, powered and free since P9's spit in c22 g: P8 extends at
  c23 and stays out; Q lands at (3,2,0) at c25 j. P8's updates before that (c4 d, c16 g, c18 j, c20 g) find it blocked.
- Opening: D_8 and LY die at t0 g, R_8 and R_9 turn off at t2 d, ahead of NV's cut (t2 j) and of P9's 0-tick (t3), as
  R_V does: P8 retracts at t3 and P9 fires at t3 as before. A_9 is updated at t0 g, t3 g and t5 j (RB9 landing in
  front of it) and never powered. In the closed state P9 has R_9 beside RB9 among its sources and P8 has R_8 beside
  NV; in the open state no piston has an added cell among its sources.
- End state [COMPUTED]: the door's pistons and the door plane as the loaded closed state has them, cell for cell, the
  labels of TM and TR exchanged; A_9, RB9, R_X and LY as in the open state; R_8 on. Against s_inputs' end state five
  cells differ, (1,2,0), (2,2,0), (3,2,0), (3,3,0) and (3,4,0), and no dust level. Against the closed state 41 cells
  outside the door plane still differ, all of them the returns: the opening's relays X2, Z_Q, Y1, Z_S, Z9, Z11, Y12 with
  RB_X, C_cut, RB_Q, RB_Y, RB_S, RB9, RB11 and G; the trigger chain's K, M_K, RB12, P_R, RB_T, K_T, SPC and RB_ST; the S
  feed's A_C, C_F, R_F and R_C; and R_9, off while LY is dark. With RB_ST taken out by command the S feed resets as
  before and P8 stays out on R_8.
- What the order rests on [COMPUTED; INFERRED for the game]: a repeater whose input is gone when its delay ends still
  turns on, for its delay (R_X; MEASURED as a rule in docs/MECHANICS.md, repeater_extends_short_pulses: 3 gt in at
  delay 2 gives 4 gt); a sticky piston released 2 gt after it pushed two blocks leaves both (P9; with one block the
  spit is measured at 1 and 2 gt, sticky_piston_short_pulse_drops_block, and S's here); a repeater that points into
  the cell above a piston powers it by QC and updates it (A_9, P9, P8), as dust pointing into that cell does (P8 on NV
  in the opening); a repeater reads the dust behind it whichever way that dust's line runs (R_9 behind LY's (6,3,0));
  a piston base that lands updates its neighbours (A_9 and P8), as a landing head does (P10's and V, measured). No
  order inside a phase is used: R_X's off and R_9's on are both scheduled ticks of c20, A_9's and P9's events both run
  in c20 g in either order, and P8's update at c22 j follows P9's spit at c22 g by phase. Dust's updates reversed,
  I_A's event last, both: the same piston events in every tick, the same end state.
- Controls fail [COMPUTED]: no R_X; R_X at 1 tick (P9's 0-tick still runs, at c18 and c20, but A_9 is home at c19 j,
  when P8 is behind P9's head, and P8 is never updated again); R_X at 3 or 4 ticks (RB9 stands beside LY for 4 gt or
  more, R_9's pulse is as long and P9 pulls TM back); A_9 not sticky (RB9 stays beside LY and P9 stays out); the glass
  left at S_L; R_9 at 2 to 4 ticks (its pulse is 4 gt or more, and the opening differs from t3: it is still on when P9
  fires); a stone under R_X (DS points into it from c12 j and A_9 fires at c13); a stone under D_8 (NA and DQ are one
  net; the opening differs from t0); each of R_X, A_9, S_L, R_9, D_8 and R_8 left out. R_8 at 2 ticks passes the close
  and changes the opening from t3 (it is still on at NV's cut); at 3 or 4 ticks both fail. O_8 left out passes in the
  simulator's order of c4's events and fails with P8's event first. G_9 as stone passes. The input off fewer than 11
  ticks after it went on fails as the trigger chain does.
- Costs: the door closes at c25 j, eight ticks after stage 5's last landing. The cells of the ten and (5,4,1), RB9's
  stroke; (3,5,-1) was one of P8's clean cells, (5,2,0) and (5,3,0) two of P9's. One of design_c's blocks changes: the
  glass under LY's dust (6,4,1) is a stone, and LY passes that step both ways. RB9 is borrowed: it has to stand at
  (4,4,1) until c22 j, so its return comes after that and leaves (3,4,1) and (5,4,1) alone. LY's two changes (c18 j, c20 g) update
  Y1, Z_Q and Z_S, fired and powered, so no event now; a re-arm that resets a fired relay by dust within 2 would be
  hit by them [INFERRED]. P8 waits powered and blocked from c4 d to c22 j. O_8 stands in the door plane's corner
  (3,-1,0), outside the frame and the wall ring.
- Not searched: no screen for fewer blocks was run. One block in every free cell around P9 and P8, as p10_v_search
  does, is about half an hour of CPU here.
- Probe: `close_p9_p8_probe` (`export_p9_p8`): the run above with no command after the input, and two controls (R_9 or
  R_8 removed with setblock air strict before the opening), 77 or 76 cells and the levels of DT, DS, DP, the tap, D_V,
  NV's four dusts, D_1, D_2, D_F, LY at (6,4,1) and (6,3,0) and D_8 checked against the simulator after c0, c4, c10, c12,
  c14, c15, c16, c18, c20, c22, c23, c25 and c30 (the controls: c16, c18, c20, c22, c25; c4, c20, c22, c23, c25). Its
  steps, read back from the YAML and replayed in the simulator, pass 3/3; without R_X, A_9, R_9 or R_8, or with the
  glass left at S_L, the first test fails [COMPUTED]. `python -m scripts.lint close_p9_p8_probe`: ok. MEASURED (sat1) 3/3:
  the door plane closed from the one input as above; with R_9 removed RB9 still shuttles, LY lit after c18 and dark
  after c20, P9 and P8 stay in; with R_8 removed P9 runs and is spat, P8 stays in, Q stays at (3,3,0). Traits ok,
  5x7x4, 10 blocks.

## The returns, first pass (2026-11-22; simulator)
After p9_p8's close 41 cells outside the door plane differ from the loaded closed state [COMPUTED returns.txt]. This pass
asks what each needs and finds the trigger chain blocked inside the box: no block was added to the design. Not as framed
in two ways: the trigger chain's returns, the suggested first group, cannot be built with added blocks, and the up relays
need not be re-oriented.
- Holds [COMPUTED]: after the close every fired relay is held by its arm, a redstone block design_c leaves for good: X2
  by (1,8,-4) (set strict after the load), Z_Q by (6,4,-4), Y1 by (7,4,-4), Z_S by (2,6,2) and RB_F (1,5,2), Z9 by (5,3,1),
  Z11 and Y12 by (-2,4,2), Y12 also by DP's RB_D (-3,4,2). Z_Q, Y1, Z9, Z11 and K are held as well by their own payload,
  which rests at R+2, a QC cell (MEASURED for a sticky up relay: `door_relay_rearm`, test 3). K_T is held by RB_T at
  (2,6,-1), M_K by RB12, A_C by Q_C; P_R is in and in the closed state only RB_ST (3,7,0) powers it. No relay goes home
  unless its arm leaves first and something updates it then.
- Routes [COMPUTED]: breadth first, one cell a step, from each block's cell after the close. A step needs the next cell
  empty and a mover: a piston behind the block, or a sticky piston beyond the next cell, either a piston already there
  facing that way and not held with the block in place (P_R, Z_T, K) or a new one in a free cell (1208: in the box,
  empty in the closed state and in every tick of the opening and of the close to c30, off the door plane and out of the
  hallway), screened: built retracted into the closed state, nothing moves during the load and every other cell is the
  same at every tick of the opening and the close. A stop is screened as well: a redstone block set there after the
  close fires no piston in 12 ticks, a piston moving to its closed state (K_T in, P_R out) apart. Lenient: a stop may
  leave a piston powered and not updated.
- RB_ST (2,8,0) to (3,7,0): no step. West is the stone over DT, south R_F, below SPC, above the box's top (y 8). At (3,8,0)
  a redstone block lights DH and the bus (I_A fires, so the opening starts, with AP, W_T and the door's pistons); at
  (2,8,-1) it lights the bus's (2,8,-2) and (1,8,-1) (AP and W_T fire); at (2,7,0), with SPC gone, it lights DT and W_T
  fires into (1,5,-1), RB_T's closed cell. So the S feed's cut (A_C, C_F, R_F, R_C), which RB_ST's leaving resets, has no
  return either. The way out is up, out of the box [INFERRED: a puller at (2,10,0) or a pusher in SPC's cell].
- RB_T (2,6,-1) to (1,5,-1): reaches (1,6,-1) (P_R's push), (2,7,-1) (a piston at (2,5,-1) facing up) and (2,6,-2) (a
  sticky piston at (2,6,-3)), no further. Into (1,5,-1) from (1,6,-1) only past the bus's glass (1,7,-1) or by Z_T's
  pull, and RB_T at (1,6,-1) holds Z_T by QC. At (2,5,-1) a redstone block fires Z_T, at (2,8,-1) AP; (0,6,-1), (2,5,-2),
  (3,6,-2) and (2,6,-3) have no mover: behind and beyond them stand glass, NA's dust, RB_A or RB_T's own cell, and a
  sticky piston at (4,6,-2) changes the opening at t0.
- RB12 (-4,3,2) to (-4,2,2): no step. K's head is under it (K held by RB12 itself), G above, M_K and Y12's head beside it,
  the box's west edge, and south no mover. G's closed cell (-3,3,2) is Y12's head.
- SPC (2,7,0) to (2,6,0): K_T's head is there. K_T made sticky (what-if) leaves the opening and the close the same, but
  that SPC is real at (2,7,0) from c0 g instead of moving to c2 j, and would pull SPC home when it retracts: once RB_T has
  left (2,6,-1).
- So the trigger chain's returns need a change to measured blocks or to the box, not added blocks [INFERRED]: RB_ST put
  elsewhere by the T feed's off (K_T lifts it onto the top layer), or the box raised; RB_T needs (1,7,-1) free (the bus's
  first west dust (1,8,-1) moved) or a T power in the closed state other than a block at (1,5,-1).
- The box grown (the lead's call, 2026-11-22: only the speed front stands, the box may grow; measured blocks stay)
  [COMPUTED returns.txt, second pass, box grown by 2 on every side, 3516 free cells]: RB12 and RB_ST have routes in the
  screen, RB_T has none. RB12 goes west round the box's edge, (-5,3,2), (-5,2,2), back east into (-4,2,2), movers out to
  x -6. RB_ST goes up and round, (2,9,0), (3,9,0), (3,9,1), (3,8,1), (3,7,1), north into (3,7,0), movers up to y 10 (the
  screen is static: it does not keep movers off the path, and (3,9,1) is on it). Neither is designed.
- RB_T, whatever the box: every way into (1,5,-1), for any block, needs a mover in a measured block's cell or in one of
  three free cells that fail the screen. Moving west: a pusher in R_8's cell or a puller at (0,5,-1), which NA's stone
  (0,5,-2) powers during the load. East: r_P10's cell, or a puller at (2,5,-1), which RB_T at (2,6,-1) powers and which
  fires at c3. Down: the bus's glass (1,7,-1), or Z_T's pull (design_c's, not sticky, and held by a block at (1,6,-1)).
  North: W_T's cell. South: a pusher at (1,5,-3), which NA's dust (0,5,-3) and RB_A power during the load, or W_T's pull
  (not sticky). Up: Z_T's own cell. Every cell named is inside the box, so growing it changes nothing; a chain pushed
  from further off would move R_8, r_P10, W_T or the bus's dust, and from the north it needs a block at (1,5,-2) first,
  which nothing reaches. The trigger chain cannot be returned without changing a measured block: this step stops here,
  with nothing designed. What would open it [INFERRED]: the bus's first west dust off (1,8,-1), so that a piston can
  stand at (1,7,-1) over RB_T; or Z_T and W_T sticky, or T held in the closed state by something other than a block at
  (1,5,-1). Each changes a block of a measured probe (`close_trigger_probe`, `close_feeds_probe`, design_c's).
- Z9 in place, by command [COMPUTED what-if]: the up relays do not need re-orienting. D9, a piston at (4,5,1) facing
  down, added (it passes the mover screen and is unpowered in the closed state). ARM_Z9 taken out before c22 or earlier:
  RB9's departure (c16 g, A_9's push) or P9's spit (c22 g) updates Z9, unpowered, and it retracts. A_9 brings RB9 back
  over it at c22 j, where RB9 QC-powers Z9 without updating it. A redstone block above D9 (stand-in source, set before
  c24 at the latest, taken out before c24 at the earliest) has D9 updated and pushing RB9 down at c23 g; RB9 is moving
  when P9's base lands beside Z9 (c24 j), which with RB9 at rest fires Z9 again, and lands on Z9 at c25 j. ARM_Z9 set back
  from c23 on lands without updating Z9. Back before c25 j, Z9 is powered at P9's landing and RB9's and its push fails,
  on RB9 moving, then on D9's head in (4,4,1), the cell where the load puts an obsidian blocker. End: Z9 in, RB9 at
  (4,3,1), ARM_Z9 at (5,3,1), D9 in, as the closed state has them, the door plane closed at c25 j as in p9_p8's run, and
  an update under Z9 fires it. Three piston events are added to p9_p8's close (Z9 in at c16, D9 out at c23 and in at
  c29), none taken away; dust's updates reversed and I_A's event last change nothing. Controls fail: ARM_Z9 left in
  place (Z9 stays out, D9 cannot push RB9 into its head); no source for D9 (P9's landing fires Z9 at c25); ARM_Z9 back
  before c22 (P9's spit fires Z9 at c22).
- Not designed: D9's source (on by c23, off from c24; LY lit c18 j to c20 g, read by a 2-tick repeater, gives c22 d to
  c24 d, but no cell found reads LY and points into D9 or its QC cells [INFERRED]) and ARM_Z9's mover: it can only be
  pulled aside, to (5,2,1) or (5,3,2) (every other neighbour is S_L, R_9, Z9's head or RB9's stroke), and back, so its
  puller must be powered in the closed and the open state, off from c22 or before until c23 or after.
- Probe: `close_returns_probe` (`export_returns`): the what-if with its two drives stood in for by commands after the
  input (a probe of the mechanism, not a design), the blocker variant (ARM_Z9 back before c23) and the control without
  D9's source; the cells the close moves or must leave alone, Z9's cells and the levels of p9_p8's probe checked after
  c0, c16, c18, c20, c22 to c25, c28 and c32 (by test), then Z9, RB9's cells and D9 four ticks after a glass block is
  set under Z9 and taken out. Its steps, read back from the YAML and replayed in the simulator, pass 3/3; without D9 the
  first test fails [COMPUTED]. `python -m scripts.lint close_returns_probe`: ok. Server (2026-11-22, main on the Mac): 3/3
  [MEASURED]: Z9 in at c16, RB9 over it after c22, D9 pushes at c23 and is in at c29, Z9 fires on the update under it;
  in the blocker test the push stops on RB9 moving and D9's head; in the control RB9 stays over Z9 and P9's landing at
  c24 fires Z9 again. `close_p9_p8_probe` still passes 3/3.

## The bus re-laid, and RB_T's return (2026-11-22; simulator; its six probes measured on the main server)
The lead's fix for RB_T was one measured block changed: the bus's first west dust off (1,8,-1), a down-pusher at (1,7,-1).
The bus is re-laid and every stage holds. The piston cannot stand at (1,7,-1); a column two cells higher does its work,
and with four drives stood in for by commands RB_T goes home. Not as framed in three ways: the piston's cell; the size
of the change (four dusts re-laid, the box 2016); and P_R's push, which the first pass's screen let through, wakes W_T.
- Bus [COMPUTED trigger.txt]: the west branch leaves K_in's top and climbs over the input repeater: (1,9,-2) on K_in,
  (0,10,-2) on stone (0,9,-2) above R_in, (0,9,-1) on glass (0,8,-1), (-1,9,-1) on stone (-1,8,-1), (-2,8,-1) on stone
  (-2,7,-1), then the old run from (-3,7,-1). Gone: dust (1,8,-1), (0,8,-1), (-1,7,-1), (-2,7,-1), glass (1,7,-1),
  (-1,6,-1), (-2,6,-1), stone (0,7,-1), and the cut (1,8,0) over DT, which had only that dust to cut. K_in's other sides
  are R_in, X2's top beside ARM_X2, and I_A, and the column over RB_T has to stay clear to (1,9,-1) (below), so the tap is
  K_in's top. 36 blocks still; box x -4..7, y -3..10, z -8..3 = 12x14x12 = 2016.
- The same [COMPUTED]: nothing moves during the load, and the opening and the close to c30 are the same at every tick in
  every cell outside the changed bus cells. trigger, dp_off, p10_v, s_inputs and p9_p8 give the verdicts and controls
  they gave; their outputs differ in the box, in the order of c0's three level-0 events (P_R, I_A, M_K: any order
  passes, as before) and in the bus's levels (M_K's dust 7, was 8).
- One net [COMPUTED]: (1,9,-2) sits on K_in and reads the east branch's (2,8,-2) down the step. Whatever else lights the
  bus now powers K_in from above, so I_A, P_R and AP see it; before, a lit west branch reached M_K only. Nothing in the
  design lights it. It showed in the screens: rerun under their old rule (output not kept), dp_off_search passed two
  one-block and 31 two-block candidates in which I_A extends again; traced for one, a piston at (-3,5,1) facing north
  that RB11 powers: it pushes the cut off DP, the bus reads DP's pulse, I_A and P_R fire and are spat, and NA's death
  then "spits" P6 at c6. The rule now also wants I_A not to extend again (`dp_search.py`), and with it dp_off_search
  passes what it passed before the re-lay: the dust on P11 and the same six pairs, in 36 cells.
- Searches rerun on the re-laid bus [COMPUTED]: p10_v_search (180 cells: the same three single blocks), dp_off_search
  (36 cells: the same dust and six pairs) and dp_search (41 cells: nothing in the free cells, the same two on the
  south pusher), the last two under the rule with I_A.
- Probes: `close_trigger_probe`, `close_dp_off_probe`, `close_p10_v_probe`, `close_s_inputs_probe` and `close_p9_p8_probe`
  re-exported; each replays in the simulator with its controls live and lints ok [COMPUTED]. Every MEASURED line above
  is for the bus before the re-lay: all five are to be measured again.
- The piston at (1,7,-1) [COMPUTED returns.txt]: plain or sticky, facing down, it changes the opening at t0. K_in (1,8,-2)
  is strongly powered while the input is on and stands beside (1,8,-1), the cell above the piston: QC, whatever is in
  (1,8,-1), so no bus route helps. I_A's extension beside it updates it at t0 g, it extends into the empty (1,6,-1), and
  Z_T's lift of RB_T at t3 never comes (T extends at t3 and stays out to t11). At (1,8,-1) K_in would power it directly.
- The report's other ways [COMPUTED returns.txt; the last INFERRED]: Z_T sticky is held out by RB_T at (1,6,-1), its own
  payload at R+2: updated there it extends and stays, and never pulls RB_T down. W_T sticky would pull a block south
  out of (1,5,-2), RB_A's open cell: every way into that cell is NA's dust or stone, a wall, a piston that moves during
  the load, or I_A's own push, which is the opening. T held otherwise: T fires at t3 g on RB_T alone (DS is dark by
  then) and Z_T's lift takes RB_T away in that phase; another hold is another relay inside the opening's T stage, a
  change to design_c's opening, not tried.
- The column [COMPUTED returns.txt, what-if]: H_T, a piston at (1,9,-1) facing down, where K_in does not reach it, over
  two glass spacers, GA (1,7,-1) and GB (1,6,-1) in the closed state. Z_T lifts RB_T, GB and GA together at t3; in the
  open state and after the close GB is at (1,7,-1) and GA at (1,8,-1), and H_T's push moves GA, GB and RB_T down one
  cell. GB stands in (1,6,-1), a cell of the opening. Nothing moves during the load, the opening and the close are the
  same at every tick outside the column's three cells, and H_T is unpowered in the closed state and after every tick of
  the opening and of the close to c30: the bus dust beside it, (1,9,-2) and (0,9,-1), points past it.
- The trap [COMPUTED returns.txt]: P_R cannot push RB_T straight back to (1,6,-1). K_T, held by RB_T at (2,6,-1),
  retracts in P_R's phase; its base lands in the same phase j as RB_T, behind it, and updates W_T, which RB_T at
  (1,6,-1) powers by QC: W_T's head takes (1,5,-1) and H_T's push stops on it. The first pass's stop screen set a
  redstone block at (1,6,-1) and saw nothing fire: it is lenient about pistons left powered and not updated.
- The kick [COMPUTED]: N_T, a sticky piston at (2,6,-3) facing south (nothing moves during the load with it, the opening
  and the close are the same, and it is unpowered in the closed state and after every tick of both). Out and in, it
  pulls RB_T north to (2,6,-2): K_T retracts and lands with W_T unpowered. Out again, it pushes RB_T back; RB_T's
  landing in front of P_R is the update P_R needs, and K_T, powered again and not updated, stays in.
- RB_T by command [COMPUTED returns.txt, what-if; H_T, GA, GB and N_T added]: after the close, N_T's stand-in source
  (a redstone block at (3,6,-3)) before c32 and out before c34; RB_ST taken out of (2,8,0) and set at (3,7,0) before
  c37; the source again before c38 and out before c43; H_T's stand-in source (1,10,-1) before c45 and out before c48;
  SPC set back at (2,6,0) before c51. N_T out at c32, pulls RB_T at c34, K_T in; N_T out at c38, P_R out at c41, RB_T at
  (1,6,-1) after c43; H_T out at c45, RB_T at (1,5,-1) after c47; A_C pulls C_F back at c46 (RB_ST left R_F). End: RB_T,
  GA, GB, P_R, K_T, SPC, RB_ST, Z_T, W_T, AP and the S feed's thirteen as the closed state has them, T powered by
  RB_T, Z_T not powered, the door plane closed. 28 cells outside the door plane still differ (44 after the close in
  this build): the opening's seven relays with their blocks, and K, M_K, RB12 and G.
- Windows, one command moved at a time [COMPUTED]: the kick's source on before c27 to c33 (all tried) and off before c33
  to c36; RB_ST home before c35 to c40 (earlier, P_R is powered when RB_T is pulled away and extends into the empty
  cell; later, RB_T's landing finds P_R unpowered); the source again before c35 to c39 (N_T must stay out until P_R
  has taken RB_T) and off before c39 to c45 (all tried); H_T's source on before c44 or later (RB_T lands at (1,6,-1) at
  c43 j) and off before c46 to c50 (all tried). Dust's updates reversed and I_A's event last change nothing.
- Controls fail [COMPUTED]: RB_ST home before the kick (RB_T stays at (2,6,-2)); no GB (Z_T lifts RB_T alone, H_T's
  push ends a cell short); no source for H_T; N_T not sticky.
- K_T made sticky [COMPUTED what-if; a measured block]: K_T pulls SPC home when the kick releases it, with no command
  for SPC.
- A lead for H_T's source [COMPUTED the fact; INFERRED the lead]: set in the open state and left on, it moves nothing,
  there (Z_T's head under RB_T stops H_T's push) or through the close (H_T is powered and not updated). A source that
  is on while RB_T is at (1,6,-1) and off in the closed state would need no timing of its own.
- Not designed: N_T's source and its two pulses, H_T's source, RB_ST's return (its landing at (3,7,0) is P_R's hold and
  must fall while RB_T is parked; the screen's route for it has six steps, in the box now that it reaches y 10) and
  SPC's mover (the cell above SPC is RB_ST's rest cell).
- Probe: `close_returns_probe` (`export_returns`) now builds D9, H_T, GA, GB and N_T and has six tests: the three for Z9,
  RB_T home by command, the trap (no kick: W_T takes RB_T's cell) and the control without H_T's source. Its steps,
  read back from the YAML and replayed in the simulator, pass 6/6; without D9 the first test fails, without H_T or N_T
  the fourth [COMPUTED]. `python -m scripts.lint close_returns_probe`: ok. Server (2026-11-22, main on the Mac): 6/6
  [MEASURED], traits ok; the five other re-exported probes pass too (trigger 4/4, dp_off 4/4, p10_v 3/3, s_inputs
  3/3, p9_p8 3/3), so every stage holds in game on the re-laid bus.

## RB_T's return from blocks (2026-11-22; simulator)
From the one falling input, with no command after it, the trigger chain's east side goes home after the close: RB_T
under T, GA and GB under H_T, P_R out, K_T in, SPC at (2,6,0), a redstone block in RB_ST's closed cell, the S feed's cut
reset. 49 blocks added and one measured block made sticky (K_T); box 12x15x12 = 2160. Not as framed in three ways: RB_ST
does not go home (its route takes eight pistons: three redstone blocks move one place each instead); N_T, the what-if's
kicker, is not used (the kick is done from above by U_T, which needs no source); and the drives are not sources with a
timing each but one pulse on a line of repeaters.
- K_T sticky [COMPUTED trigger.txt, returns.txt]: the lead's fix for SPC, which has no other mover. At c0 DT's death
  unpowers K_T inside its own extension; sticky, it is released at once and spits SPC, which is real at (2,7,0) from c0
  g instead of landing at c2 j. RB_ST, the second block of the push, lands at (2,8,0) at c2 j as before; every other
  cell of the opening and of the close is the same at every tick. From c3 its head stands under SPC, and when RB_T is
  lifted off (2,6,-1) it retracts and pulls SPC home. trigger, dp_off, p10_v, s_inputs, p9_p8 and returns give the
  verdicts and controls they gave; trigger.txt and dp_off.txt differ in the text of K_T's c0 event (retract+SPIT),
  returns.txt in its lines about K_T and SPC; dp.txt, p10_v.txt, s_inputs.txt and p9_p8.txt are the same byte for byte.
  The three searches were rerun on it (below).
- RB_ST's own route [COMPUTED rbt_route.txt]: every route of up to eight steps from (2,8,0) to (3,7,0), 120 cells, with
  returns.py's two screens and the two rules they leave out. Out of its rest cell only up passes: a redstone block at
  (1,8,0) lights DT and W_T fires (as at (2,7,0), SPC's cell: returns.txt), at (2,8,-1) or (3,8,0) it lights the bus and
  I_A fires. 22 routes pass the screens, 2 of six steps and 20 of eight. With every mover off the path: 11, the same 2
  and 9 of eight. Both six-step routes take the step (3,8,1) to (3,7,1), down, by a sticky piston at (3,6,1) facing up,
  the only mover for it off the path, and that piston cannot do it: the block two above it is beside the cell above it
  and powers it by QC (set out with the block at (3,8,1): powered by (3,8,1), out after an update and six ticks).
  Without the pullers that face up 2 routes are left, both of eight steps: eight pistons, each with a source and a time
  of its own.
- The loop [COMPUTED rbt_drives.txt]: RB_1 (3,7,1) and RB_2 (3,8,1), two more redstone blocks, stand south of RB_ST's
  closed cell in the closed state (in free cells; nothing moves during the load and the opening and the close are the
  same with them). In a return RB_1 goes north into (3,7,0); RB_ST goes up to (2,9,0), east to (3,9,0), south to
  (3,9,1), and one push down moves it and RB_2 a cell each. The three end in each other's cells: the same block, as TM
  and TR in p9_p8.py. Five pistons, one for each straight piece: P_U (2,10,0), sticky, facing down, pulls RB_ST up; P_E
  (4,9,0), sticky, facing west, pulls it east; P_S (3,9,-1) pushes it south; P_D (3,10,1) pushes the two down; P_N
  (3,7,3), sticky, facing north, pushes glass G_N (3,7,2) and RB_1 north and pulls G_N back (a piston at (3,7,2) is
  QC-powered by RB_2 and extends in the load).
- The kick [COMPUTED]: U_T, a sticky piston at (2,8,-1) facing down, beside RB_ST's rest cell. RB_ST's landing at
  (2,8,0) (c2 j) powers and updates it: out at c3, its head at (2,7,-1) above RB_T, through the rest of the close (its
  two cells are the only added ones that change before c18). When P_U pulls RB_ST up, U_T is released inside that event
  and pulls RB_T up to (2,7,-1); K_T, which RB_T held out, retracts behind it and pulls SPC home. Two ticks later RB_ST
  lands at (2,9,0), beside the cell above U_T, and after it RB_T, in front of U_T: that landing updates U_T, powered by
  QC, and it goes out again and pushes RB_T back down in front of P_R. It needs no source and no pulse.
- P_R and H_T [COMPUTED]: RB_1 lands in (3,7,0) in the tick RB_T lands at (2,7,-1): P_R is powered by QC, as in the
  closed state, and not updated; when RB_T left its front, two ticks before, it was not powered. RB_T's landing in front
  of it is its update: it pushes RB_T to (1,6,-1), under GB and GA. K_T landed three ticks before, so W_T is not woken
  (the trap). P_R's head landing updates U_T's head, and U_T retracts, RB_ST having been pulled on east in that tick.
  H_T pushes GA, GB and RB_T down as in the what-if.
- The timer [COMPUTED]: one pulse. R_0, a 4-tick repeater at (2,6,3) facing west, reads Q_F, the stone under the S
  feed's dust D_F, lit from c10 d to c14 j: on from c18 d to c26 d. R_1 (3,6,3), 4 ticks, into stone Y_0 (4,6,3): c26 d
  to c34 d. Eight dusts on glass climb from beside Y_0, (5,6,3), (6,7,3), (5,8,3), (5,9,2), (4,10,2), (3,10,2),
  (2,10,2), to (2,10,1), which points into P_U (levels 15 to 8). Two repeaters read that line: R_N (4,8,3), 4 ticks,
  into the cell above P_N, and R_E (5,9,1), 4 ticks, into stone Y_E (5,9,0) beside P_E. R_S (4,10,-1), 4 ticks, reads
  two dusts on and beside Y_E and points into stone Y_S (3,10,-1) above P_S; R_H (2,10,-1), 3 ticks, reads Y_S and
  points into the cell above H_T; R_D (3,11,0), 4 ticks, reads a dust on Y_S and points into the cell above P_D. Sixteen
  glass blocks carry the dust and the repeaters. In the closed and the open state and through the opening every repeater
  is off and every dust dark.
- The run [COMPUTED rbt_drives.txt]: c26 P_U out. c34 P_U pulls RB_ST (U_T pulls RB_T, K_T pulls SPC, in that event's
  levels 1 and 2); P_N and P_E out. c36 j RB_1 in (3,7,0), RB_ST at (2,9,0), RB_T at (2,7,-1), SPC home. c37 U_T out
  again, c39 j RB_T in front of P_R, c40 P_R out, c42 j RB_T at (1,6,-1). c42 P_N pulls G_N back, P_E pulls RB_ST east,
  R_S powers P_S, which P_E's head and then the moving block stop; c43 U_T in; c44 j RB_ST at (3,9,0), which updates
  P_S: out at c45, RB_ST at (3,9,1) at c47 j. c48 H_T out, c50 j RB_T at (1,5,-1). c50 P_D out, c52 j RB_2 at (3,7,1)
  and RB_ST at (3,8,1). The S feed's cut resets by itself (A_C pulls C_F back at c44). P_S in at c50, H_T at c56, P_D at
  c58. c34 is the first tick after c30 at which a cell outside the added blocks changes. 19 piston events are added to
  p9_p8's run, none taken away.
- The same [COMPUTED]: every added block but GB stands in a free cell (GB in a cell of the opening, as in the what-if);
  nothing moves during the load; the opening and the close to c30 are the same at every tick in every cell outside the
  added blocks and the cells they move through. Of the added pistons only U_T (from c2) and P_U (from c26) are powered
  at any tick of the opening or of the close to c30.
- End state [COMPUTED]: every cell of the trigger chain's east side (RB_T, GA, GB, H_T, P_R and its head, K_T, SPC,
  RB_ST's three cells, Z_T, W_T, T, AP), of the S feed's thirteen and of the 49 blocks and the cells they move through
  is as loaded, labels apart; their pistons are powered as in the closed state, T by RB_T; the door plane is closed;
  nothing is moving, no tick or block event is pending. 28 cells outside the door plane still differ: the opening's
  seven relays with their blocks, and K, M_K, RB12 and G.
- A second cycle [COMPUTED, sim only]: with those cells (and the dust levels that follow them) set back as loaded
  without updates, a stand-in for the returns not designed, the input goes on again: the second opening is the same as
  the first at every tick in every cell, labels apart, and the second close and return have the same piston events.
- Margins [COMPUTED]: each delay moved alone, 1 to 4 ticks. R_0 and R_1 may be 3 or 4 (shorter, the return is done but
  starts before c30); R_N 3 or 4 (shorter, RB_1 is in (3,7,0) when RB_T is lifted, and P_R, powered, extends into the
  empty cell); R_E, R_S and R_D 2 to 4; R_H 1 to 4. Dust's updates reversed and I_A's event last change nothing. The
  input off 11 ticks or more after it went on: the close and the return are done (8 to 10: the close fails, as in
  p9_p8.txt). With D9, the Z9 what-if's piston, built as well: the same events.
- Controls fail [COMPUTED]: no R_0 (nothing starts); no U_T, or U_T not sticky (RB_T stays in front of P_R, K_T out
  under SPC); K_T not sticky (SPC stays at (2,7,0)); no P_U or no P_E (RB_ST holds U_T out); no P_N, R_N or RB_1 (no
  block in (3,7,0): P_R stays in, RB_T ends at (2,7,-1)); no G_N; P_N not sticky; P_N at (3,7,2) (it extends in the
  load); no R_E, P_S, R_S, P_D, R_D, RB_2, H_T, R_H or GB. Each of the 33 blocks that are not glass under a dust or a
  repeater, left out alone, fails the return. The repeaters that tick together at c34, c42 and c50 run in reverse order:
  the same events.
- Two things the probe is there to measure [COMPUTED the what-ifs; INFERRED that the game agrees]. The order of the
  landings at c36 j: RB_ST lands ahead of U_T's base and of RB_T because its move began first (P_U's event, level 0;
  U_T's, which RB_ST's leaving queued, level 1) and moving blocks tick in the order their moves began; with U_T's base
  ahead of it the return is still done (the base cannot push while RB_T moves, and RB_T's landing is the update that
  counts), with both ahead U_T stays in and RB_T at (2,7,-1). And a piston powered through a stone beside the cell above
  it is not updated: a first design had P_E's work done by a pusher at (1,9,0) fed that way, powered by QC from c40 to
  c48 and never moved, so R_N, R_H and R_D point into the air cell above their piston, whose change updates it (as R_X,
  R_9 and R_8 do, measured), and P_S, powered while it cannot move, is updated by the block it pushes.
- Searches rerun with K_T sticky [COMPUTED]: p10_v_search (180 cells: the same three single blocks), dp_off_search (36
  cells: the same dust and six pairs) and dp_search (41 cells: nothing in the free cells, the same two on the south
  pusher); each output file is the same byte for byte.
- Probes: `close_rbt_drives_probe` (`export_rbt_drives`): the design's 49 blocks on the whole build, four tests with no
  command after the input: the run, checked against the simulator after c0, c3, c5, c18, c26, c34, c36, c37, c39, c40,
  c42, c43, c44, c47, c48, c50, c52, c56, c60 and c62 (137 cells and 22 dust levels each time), and three controls that
  take one block out before the opening: R_0 (nothing starts), U_T (no kick), R_N (no block comes into (3,7,0); U_T,
  updated by H_T's push, lifts RB_T again at c48). Its steps, read back from the YAML and replayed in the simulator,
  pass 4/4; without R_0, U_T, P_U, R_N, P_E, R_S, R_H or R_D the first test fails. `close_trigger_probe`,
  `close_dp_off_probe`, `close_p10_v_probe`, `close_s_inputs_probe`, `close_p9_p8_probe` and `close_returns_probe` are
  re-exported with K_T sticky (the checks of K_T, of its head and of (2,7,0) after c0 differ); each replays in the
  simulator with its controls live. All seven lint ok. Every MEASURED line above is for K_T as a plain piston: the six
  are to be measured again, and the new one for the first time. `close_feeds_probe` and `close_s_feed_probe` are
  unchanged.

## The west side's return from blocks (2026-11-22; simulator)
From the one falling input, with no command after it, the trigger chain's west side goes home after the close: RB12 on K
at (-4,2,2), K in and armed as the load leaves it (powered by L, not updated), M_K in, WK beside K. 34 blocks added and
no measured block changed; box 14x15x12 = 2520 [COMPUTED west_drives.txt]. Not as framed in two ways: RB12 does not take
the route of the first pass's screen, round (-5,2,2) with three pistons, but is pulled one cell west and pushed back, a
kick as RB_T's was, and then pushed down together with G; and the closed state is not all restored, because G cannot be:
it ends at (-4,3,2), its cell in the open state, and the gate over L stays open until Y12 is re-armed.
- After the close [COMPUTED returns.txt]: RB12 at (-4,3,2) on K's head, G above it at (-4,4,2), K out (RB12 is its payload,
  two above it: QC), M_K out (RB12 beside it), WK at (-4,1,1). K retracts only once RB12 has left, and its closed state is
  powered and not updated under RB12, so whatever brings RB12 back onto it has to stop K's push at that landing.
- The screen's route [COMPUTED west_drives.txt, what-if]: with RB12 pulled west to (-5,3,2), K and M_K in and WK at
  (-4,2,1), the route's east pusher at (-6,2,2) is powered by RB12 from where it is parked (QC); RB12 at (-5,2,2) powers
  K by QC, in and free to push; nothing on the route sends M_K out again, so WK stays up; and RB12 set on K with
  (-4,3,2) empty is pushed up again at once (L powers K and updates it). The route's three pistons would need a fourth
  mover for WK and something to stop K as well.
- The kick [COMPUTED]: P_W, a sticky piston at (-6,3,2) facing east, built out, its head at (-5,3,2), held by RB_W, a
  redstone block north of it at (-6,3,1). A_W, a sticky piston at (-6,4,1) facing down, pushes RB_W down to (-6,2,1) and
  pulls it back. RB_W's leaving updates P_W inside A_W's event: it retracts and pulls RB12 west to (-5,3,2); K and M_K,
  updated by RB12's leaving and unpowered, retract in that phase, M_K pulling WK up to (-4,2,1). Parked, RB12 powers no
  piston. RB_W's landing back beside P_W updates it: it pushes RB12 east again and stays out, as loaded. Above P_W a
  redstone block cannot be taken away in one push (every neighbour of that cell is a QC cell of P_W); north, south and
  below it can. P_W is held, not pulsed: released with G at (-4,3,2) it pulls G west (what-if).
- M_K and WK [COMPUTED]: RB12's landing back at (-4,3,2) (c55 j) powers and updates M_K, which pushes WK down at c56.
  RB12 there powers K again, and WK's landing beside K at c58 j would update it: in the control without R_G, K goes out
  again at c59. So RB12 has to leave within two ticks of M_K's push.
- The push down [COMPUTED]: P_G, a sticky piston at (-4,6,2) facing down, over glass SPG (-4,5,2), pushes SPG, G and RB12
  down one cell at c58. RB12's leaving releases M_K two ticks after its push: it leaves WK at (-4,1,1) (a sticky piston
  released within 2 gt of its push leaves the block: measured for P9 and F_S), and WK, real at once, updates K, which
  nothing powers then. RB12 lands on K at c60 j and lights L, whose change updates K with QC power on: its push stops
  on G, moving above RB12, and after that on P_G's head over SPG and G (K's updates while it is in: c58 g not powered,
  c60 j powered and blocked). P_G pulls SPG back at c66. K is left powered and not updated under RB12 and G, as the open
  state has it. P_G stands two above G's cell of after the close because the bus's last dust (-4,5,1) points into
  (-4,5,2): a piston there is out through the open state.
- The timer [COMPUTED]: one pulse, from the east return's line. R_W, a 4-tick repeater at (1,10,2) on glass, reads the
  line's dust (2,10,2), lit from c26 to c34, and a dust joins it to R_M (-1,10,2), 4 ticks, on from c42 d to c50 d.
  Eight dusts run from R_M: (-2,10,2), (-2,10,1) and (-2,10,0) at y 10, then down four stone steps, (-3,9,0), (-4,8,0),
  (-5,7,0), (-6,6,0), beside the bus's west branch (two cells higher and one south) and two cells north of P_G's
  column, to D_A (-6,6,1) on S_A, a stone on A_W: S_A powers A_W and D_A's change updates it, as the bus's last dust
  does M_K from the stone on it (levels 15 to 8).
  R_X (-6,6,2), 4 ticks, reads D_A and powers stone Y_X (-6,6,3); R_G (-5,6,3), 4 ticks, reads Y_X and powers stone
  Y_G (-4,6,3), south of P_G, from c58 d to c66 d. In the closed and the open state and through the opening every
  repeater is off and every dust dark.
- The run [COMPUTED west_drives.txt]: c42 A_W out, P_W pulls RB12 (level 1), K and M_K in (level 2). c44 j RB12 at
  (-5,3,2), WK at (-4,2,1), RB_W at (-6,2,1). c50 A_W pulls RB_W back, c52 j it lands, c53 P_W out, c55 j RB12 at
  (-4,3,2). c56 M_K out. c58 P_G out, M_K released: WK real at (-4,1,1). c60 j RB12 at (-4,2,2), G at (-4,3,2), L 15.
  c66 P_G in, c68 j SPG home. 10 piston events are added to the east return's run, none taken away.
- The same [COMPUTED]: every added block stands in a cell that the build of rbt_drives.py never fills; nothing moves
  during the load; the opening and the close to c30 are the same at every tick in every cell outside the added blocks,
  and no added cell changes before c34. From c31 to c70, against the same build without the 34 blocks, the cells that
  differ are the west column's seven (K, its head cell, (-4,3,2), (-4,4,2), M_K, its head cell, WK's) from c42 and, from
  c60, L, NP12's dust and the DP tap (its repeater from c62): the east side's return is the same at every tick. Of the
  added pistons P_W is powered throughout, by RB_W; A_W and P_G never before their pulse.
- End state [COMPUTED]: K, its head cell with RB12 in it, M_K, its head cell, WK and (-4,4,2) as loaded, K powered by L
  alone as in the closed state, M_K unpowered; the 34 blocks as loaded, P_W held by RB_W, the repeaters off, the line
  dark; the east side as rbt_drives.py leaves it; the door plane closed; nothing moving, no tick or block event pending.
  24 cells outside the door plane still differ (28 before this step): the opening's seven relays with their blocks, G,
  and the DP tap's repeater.
- The open gate [COMPUTED]: from c60 j H reads L up the step that G should cover. NP12 is lit as in the open state (H 14,
  G12 on P12 8, the tap's dust 10), the tap's repeater is on from c62, P12 is powered and its push stops on V's head
  under the spare block, and A_D is powered through the tap's stone and not updated, as it is from t8 in the open
  state. Nothing moves. When NP12 dies again, H's death updates A_D while the tap still powers it, as at c0 (the what-if
  under G). The step that re-arms Y12 starts from this.
- G [COMPUTED the what-ifs; INFERRED the judgement]: G's return is in two steps and only the first is this one's. Down
  to (-4,3,2) it goes here: it is the middle block of P_G's push and, moving above RB12, what stops K. East into
  (-3,3,2) it can go only when Y12 has retracted, and Y12 is held by ARM_Z11 above it and by RB_D beside the cell above
  it (QC): the relays' step. With those two taken out by command after the returns, Y12 as built retracts and leaves G
  at (-4,3,2), which then needs a mover from the west, where P_W's head stands; Y12 made sticky (a measured block of
  design_c) pulls G home by itself: H 0, the tap's repeater off two ticks after G lands, and A_D extends once (RB_D
  being out, it pushes nothing). With Y12 sticky nothing moves during the load and the opening, the close and both
  returns are the same at every tick outside Y12 and its head. Holding RB12 back until G is home was not tried: the
  push down would lose its middle block (P_G reaches one cell past SPG) and K the block that stops it.
- The relight and the east side [COMPUTED]: NP12's relight updates W_T, and RB_T powers W_T by QC while it stands at
  (1,6,-1), c42 j to c47 (the trap of the bus section). Built, RB12 lands at c60 j, ten ticks after RB_T is home. With
  the line 14 ticks early (R_M a dust, R_W at 1 tick) it lands at c46 j: W_T extends at c47 and its head takes RB_T's
  closed cell. With two repeaters on the line the earliest landing is c48 j, when H_T has pushed RB_T on.
- Margins [COMPUTED]: each delay moved alone, 1 to 4 ticks. R_W and R_M: all done, and all 16 pairs (the kick at c30 to
  c42). R_X and R_G: 3 or 4, not both 3: P_G's push has to fall in c56 to c58, after M_K's extension and before WK
  lands (at 2, R_G is on while RB12 is still moving into (-4,3,2), the push fails and nothing updates P_G; at 1, P_G
  pushes G into the empty cell at c52). With one of them at 3, P_G's event runs in c56 behind M_K's extension, queued
  in c55 j (first in, first out), and M_K is released inside that phase; with the two events exchanged (what-if) M_K's
  is dropped and WK stays up. Built at 4 and 4 nothing rests on that order. Dust's updates reversed, I_A's event last,
  the scheduled ticks of each tick reversed from c30 and the moving blocks west of x -3 in reverse order from c40
  change nothing, nor do 60 seeded runs with both in a random order. The input off 11 ticks or more after it went on: the close and both returns are done.
- Controls fail [COMPUTED]: no R_W or no A_W (nothing starts in the west); A_W not sticky (RB_W stays down, P_W in, RB12
  at (-5,3,2)); no RB_W (P_W retracts in the load); P_W not sticky; no P_G, R_X, Y_X, R_G or Y_G (K out again at c59);
  no SPG; P_G not sticky (SPG left at (-4,4,2)); R_X and R_G both at 3 ticks; the line 14 ticks early. Each of the 24
  blocks that are not glass or S_A under a dust or a repeater, left out alone, fails the return.
- A second cycle [COMPUTED, sim only]: with the 72 cells that still differ, labels apart, set back as loaded without
  updates (the relays, G, and the dust and the tap that the open gate lights), the second opening is the same as the
  first at every tick in every cell, and the second close and returns have the same piston events. With D9 built as
  well: the same events.
- What the probe is there to measure [COMPUTED here; INFERRED that the game agrees]: A_W out at c42 on D_A; P_W's pull
  inside A_W's event and K's and M_K's retracts behind it; P_W out again at c53 on RB_W's landing; M_K leaving WK at
  c58, two ticks after its push; K in after c60, with L at 15, RB12 on it and G above; NP12 lit from c60 with P12 and
  A_D in; and, in the control, K out at c59 on WK's landing.
- Earlier scripts and searches [COMPUTED]: this step adds files and changes none. feeds, puller, trigger, dp, dp_off,
  p10_v, s_feed, s_inputs, p9_p8, returns, rbt_route and rbt_drives, rerun, give their .txt files byte for byte; the
  seven exporters from `export_trigger` to `export_rbt_drives`, rerun, write the same YAML. The three searches, rerun
  (p10_v_search 180 cells, dp_off_search 36, dp_search 41 and 39), give their files byte for byte: they screen the
  builds of their own steps, which hold none of the 34 blocks; three of these stand in cells of the two DP screens
  (P_G, SPG and Y_G, at (-4,6,2), (-4,5,2) and (-4,6,3)).
- Probe: `close_west_drives_probe` (`export_west_drives`): the 34 blocks on the whole build, three tests with no
  command after the input: the run, checked against the simulator after c0, c3, c34, c42, c44, c50, c52, c53, c55, c56,
  c58, c60, c62, c66, c68 and c70 (54 cells of the west side and 29 dust levels each time, 174 cells after c70), and two
  controls that take one block out before the opening: R_M (the line stays dark, nothing moves in the west) and R_G
  (the kick and RB12's way back as in the run, P_G stays in, K out again at c59). Its steps, read back from the YAML
  and replayed in the simulator, pass 3/3; without R_W, R_M, A_W, RB_W, P_W, R_X, Y_X, R_G, Y_G, P_G or SPG the first
  test fails. `python -m scripts.lint close_west_drives_probe`: ok. MEASURED 3/3 on the main server (2026-11-22).

## Y12's re-arm, first pass (2026-11-22; simulator)
Not done from blocks: Y12 ends re-armed with Y12 made a sticky piston, 8 added blocks and two sources stood in for by
four commands after the input [COMPUTED y12.txt; MEASURED 3/3 after the D_X fix]. Box still 14x15x12 = 2520; the opening is the same at
every tick and the close the same to c30 outside the added cells, Y12 and its head's cell; the returns are the same
until c61.
- Sticky [COMPUTED y12.txt, control]: a plain Y12 retracts at c61 and leaves G at (-4,3,2). A block leaves that cell
  eastward only by a piston in (-5,3,2), where P_W's head stands, or by Y12's pull.
- Holds [COMPUTED y12.txt, what-if]: a redstone block in any of the five cells one step from ARM_Z11's powers Y12, so
  ARM_Z11 is not taken away. ARM_Z11 and RB_D are each lifted one cell and put back; a moving block powers nothing and
  Y12 retracts while both move.
- When [COMPUTED y12.txt, what-if]: the DP tap powers both of RB_D's movers while NP12 is lit: A_D through its stone,
  and a piston over RB_D by standing beside that stone. A_D fired with the tap on stays out and parks RB_D in DP's
  source cell, where it powers M_K by QC; G's leaving then fires M_K. So the lift is at c61 g, after G's landing in
  (-4,3,2) at c60 j and before the tap's repeater turns on at c62 d.
- W_Y (-3,6,2), a sticky piston facing down over RB_D, in at rest. S_W (-3,7,3), a stone on the tap's stone, powers it
  without an update from c52 to c60: R_F (-4,7,3), a 1-tick repeater on Y_G, reads S_F (-5,7,3), a stone on R_G, which
  D_X (-6,7,3), a dust on Y_X, powers. P_G's extension beside W_Y at c58 updates it and it goes out; its head lands on
  RB_D at c60 j and updates it, unpowered: at c61 it pulls RB_D up. RB_D lands in front of it at c63 j with the tap on
  and W_Y pushes it down at c64; the tap's repeater turns off at c65 d, updates W_Y, and W_Y leaves RB_D and retracts.
  R_F at 2 to 4 ticks fails. In the open state the tap holds W_Y out; it retracts at c2 over A_D's head and pulls nothing.
- U_Y (-2,6,2), a sticky piston facing down over ARM_Z11, built out. STAND-IN: its hold is a redstone block at
  (-2,8,2), taken out before c60 and set back before c63 without updates (out before c59 to c61, back before c62 to
  c65). NP12's relight at c60 j updates U_Y: it pulls ARM_Z11 up at c61 and pushes it back at c64.
- B_Y (-4,3,3), a piston facing north. STAND-IN: a redstone block at (-5,3,3), set before c62 and cleared before c70
  with updates (set before c62 or c63; cleared before c67 or later). Its head is in (-4,3,2) from c62: G's landing at
  c63 j and ARM_Z11's at c66 j update Y12, powered, and its push fails. The head also keeps K in.
- A_D: G's landing puts NP12 out with the tap still on and updates A_D. Its push, queued behind W_Y's, fails at c64 on
  RB_D moving into the cell in front of it. With G landing ahead of RB_D (sim only) A_D's head takes that cell and
  RB_D stays up [COMPUTED y12.txt, order]: it rests on moving blocks ticking in the order their moves began [MEASURED
  `close_rbt_drives_probe`]. A_D never moves and DP is never lit.
- End state [COMPUTED y12.txt]: Y12 in, powered by ARM_Z11 and RB_D and not updated; G at (-3,3,2); NP12 and the tap
  dark; 20 cells outside the door plane still differ (the other six relays with their blocks, and R_9). A second cycle
  is the same.
- Left [INFERRED from the cells, not searched]: U_Y's hold from blocks needs a source that goes dark without updating
  U_Y. The cells that power U_Y silently are (-1,7,2), (-2,7,3) and (-2,8,2); a redstone block there has no second
  powering cell one step away but (-2,7,2), whose leaving updates U_Y; the cells that would feed them hold the glass
  under R_C (0,7,2) or under the west line (-2,9,2), the tap's repeater (-2,6,3), lie at z 4, or are two above P_G or
  P10. (-2,6,1) and the cells that power it are left free for the down-pusher over RB11 that Z11's return needs. B_Y's
  source needs an edge 2 ticks after R_G from a cell that does not update A_D at c62 (the cell above B_Y is beside A_D).
- Probe: `close_y12_probe` (`export_y12`): three tests with the stand-in commands, replayed in the simulator 3/3; the
  first test fails with Y12 plain or without U_Y, W_Y, B_Y, S_W, R_F, S_F or D_X. `python -m scripts.lint
  close_y12_probe`: ok. MEASURED on the main server, 2026-11-22: 0/3, R_F still off at c54 (control 1 first off at c62,
  control 2 on the same R_F check at c60).
- The cause [INFERRED from the export and MEASURED mechanics, the trace not yet read]: D_X (-6,7,3) has no dust beside
  it. The simulator treats a lone dust as a cross, pointing east into S_F; the export set it as bare `redstone_wire`,
  and a bare dust set by command is a dot that powers no neighbour [MEASURED dust_dot_vs_cross_isolated; AUTHORING.md],
  so S_F, R_F and S_W stay dark and W_Y never fires. Fix: D_X is a cross in the build and the export writes
  `redstone_wire[east=side,north=side,south=side,west=side]` for it (`state_str` writes a dust's four sides only when the
  build marks it a cross), and the probe now checks that shape. y12.txt is unchanged; close_y12_probe re-exported (3/3
  replayed, the same controls live, lint ok); the other exporters write the same YAML. The two older lone dusts, (1,7,0)
  and (-3,4,0), are dots in game; with them as dots the simulator gives the same runs of west_drives.py and y12.py at
  every tick, which fits their probes passing. MEASURED again on the main server, 2026-11-23, with D_X a cross: 3/3 (the
  run and both controls): lift at c61, G home after c63, RB_D left at c65, ARM_Z11 back after c66, Y12 in and armed,
  A_D never out.

## Y12's holds from blocks (2026-11-22; simulator)
Y12's re-arm needs no command after the input [COMPUTED y12_holds.txt; MEASURED 3/3]: y12.py's two stand-in sources are
made of blocks, 14 on y12.py's 8, Y12 sticky (the lead's call) and no other measured block changed. From the one falling
input Y12 goes in and is armed again, G lands at (-3,3,2), NP12 and the tap end dark and A_D never moves. Box 14x15x14 =
2940: z 4 for U_Y's hold (the lead's call) and z 5 for B_Y's source, which the lead accepted (2026-11-22).
- Why a hold alone cannot do it [COMPUTED y12_holds_search.txt]: U_Y is updated at W_Y's extension (c58 g, it must be
  powered) and at NP12's relight (c60 j, it must be dark, or W_Y's retract at c61 g). The cells that power U_Y without
  an update are (-3,7,2) (it also powers P_G and W_Y), (-2,7,1) (kept free), (-2,7,3), (-2,8,2) and (-1,7,2). A block a
  sticky piston moves out of one and back is gone 5 gt at least; the only usable moves (piston and away cells free, the
  block there powering nothing that stands) are out of (-2,8,2) to (-2,8,1), out of (-1,7,2) to (-1,7,1) (pushed or
  pulled) and out of (-2,7,3) to (-2,7,4) (pulled from z 5); no neighbour update reaches any of those pistons from W_Y's
  extension to the end of c59, and no tick is scheduled in c59. So the hold leaves before c58 and U_Y needs a second
  source for c58.
- S_U [COMPUTED]: a stone at (-2,7,3) under dust D_U (-2,8,3), which dust D_S on S_W (-3,8,3) lights while S_W is (c52 d
  to c60 d): U_Y is lit by QC, D_U three cells from U_Y and D_S three from W_Y. D_U is beside A_C: D_Z, a dust at
  (-2,8,4) on glass G_Z (-2,7,4), turns it north-south; without D_Z A_C pushes C_F out at c52 and back at c60.
- The hold [COMPUTED]: RB_U, a redstone block at (-1,7,2), beside the cell above U_Y, in place of the stand-in at
  (-2,8,2). H_U, a sticky piston at (-1,7,3) facing north, under A_C, pushes it to (-1,7,1) and pulls it back. S_U
  powers H_U (beside it; D_U's changes update it): out at c52 g, back at c60 g, RB_U home at c62 j. Q_C, which powers
  A_C's cell from c12 to c44, powers H_U too (QC): A_C's extension at c12 updates it and RB_U is away from c12 to c46 j;
  no update reaches U_Y from c5 to c58.
- The run [COMPUTED]: U_Y lit c46 to c59 (RB_U, then S_U), dark after c60 d to c62 j: NP12's relight at c60 j finds it
  dark and it pulls ARM_Z11 at c61 g with W_Y's pull of RB_D, as the stand-in had it (out before c60, back before c62);
  ARM_Z11's landing at c63 j finds it lit, it pushes at c64 g and stays out on RB_U.
- B_Y's source [COMPUTED]: R_B, a 3-tick repeater at (-4,6,4) facing north on glass G_B, reads Y_G and powers stone S_B
  (-4,6,5) from c64 d to c72 d; dust D_B under S_B on stone S_B2 (-4,4,5) steps down north to dust D_Y (-4,4,4) on glass
  G_Y (-4,3,4), pointing north into the cell above B_Y. B_Y goes out at c64 g into (-4,3,2), empty since G left at c61
  g; ARM_Z11's landing at c66 j finds its head there; in at c72 g. D_Y updates A_D at c64 d, when A_D's push is already
  queued (G's landing, c63 j, behind W_Y's), and at c72 d, with the tap off. Y_G alone (a dot under it) is one tick
  short: B_Y goes in at c66 g and Y12 out at c67 (what-if). A repeater reads Y_G only from (-4,6,4), facing north, so its
  output is at z 5 [COMPUTED y12_holds_search.txt: the cells from which a repeater reads Y_G, S_W, S_F, Y_X or the tap's
  stone]. No single block near B_Y re-arms Y12 [y12_holds_search.txt].
- Against y12.py's run [COMPUTED]: the opening, the close and the returns are the same at every tick outside the added
  cells and B_Y's head cell (out c64 to c72, two ticks after the stand-in source's c62 to c70); against west_drives.py's
  run the cells that differ are y12.py's. 20 cells outside the door plane still differ from the closed state, as after
  y12.py.
- Margins [COMPUTED]: R_B 1 to 4 ticks re-arm Y12. At 1 tick B_Y is powered at G's landing in (-4,3,2) at c60 j and its
  push stops only because M_K's base lands after G (the landings reversed: fails); at 2 ticks D_Y updates A_D in c62 d
  beside the tap's turning on (the scheduled ticks reversed: fails); at 3 (built) and 4 neither. Order: dust's updates
  reversed, I_A's event last, the scheduled ticks reversed, and the landings of c14, c46, c54, c60, c62, c64, c66 and c72
  each reversed among themselves change nothing; 60 runs with the scheduled ticks of every tick in a random order (and
  dust's updates reversed in half) re-arm Y12 every time. As in y12.py, A_D's push ahead of W_Y's at c64 and the c63 j
  landings reversed fail: they rest on moving blocks ticking in the order their moves began [MEASURED
  `close_rbt_drives_probe`].
- Controls fail [COMPUTED]: no RB_U (U_Y retracts in the load), no H_U, no S_U, D_U or D_S (U_Y and Y12 stay out), H_U
  not sticky (RB_U left at (-1,7,1): U_Y never pushes ARM_Z11 back and Y12 goes out at c64), no D_Z (A_C moves C_F out
  and back, c52 to c61), no R_B, S_B, D_B, S_B2 or D_Y (Y12 out again at c67); each of y12.py's 7 blocks left out and Y12
  plain still fail. A second cycle [COMPUTED, sim only] is the same: second opening identical at every tick, second close
  and returns re-arm Y12 with the same piston events.
- Cost [INFERRED]: RB_U at (-1,7,1), from c14 j to c44 g and from c54 j to c60 g, is one step from (-2,7,1): it would
  power a piston at (-2,6,1), the cell kept free for Z11's down-pusher, by QC. Z11's design has to allow for it.
- Probe: `close_y12_holds_probe` (`export_y12_holds`): three tests with no command after the input (the run; H_U taken
  out: U_Y and Y12 stay out; R_B taken out: Y12 out again at c67), replayed in the simulator 3/3; the first test fails
  with Y12 plain or without RB_U, H_U, S_U, D_U, D_S, D_Z, R_B, S_B, D_B, S_B2, D_Y, U_Y or W_Y. `python -m scripts.lint
  close_y12_holds_probe`: ok. MEASURED on the main server, 2026-11-23: 3/3; in the run RB_U out c12 to c46 and c52 to
  c62, U_Y lit by S_U at c58, the lift at c61, G home after c63, B_Y out c64 to c72. Earlier scripts, searches and exporters: unchanged, their outputs
  byte for byte. After close_y12_probe's 0/3 (above: D_X exported as a dot) the probe is re-exported with D_X a cross;
  only D_X's glyph and checks change, y12_holds.txt and y12_holds_search.txt are the same byte for byte, the replay is
  still 3/3 with the same controls live, lint ok. Its other dusts all have a neighbour to point at, so none is a lone
  dot; the two older lone dusts, (1,7,0) and (-3,4,0), are as in west_drives.

## Z11's return, first pass (2026-11-23; simulator)
Not done from blocks: Z11 goes home, in and armed as loaded, with 3 added blocks and one drive stood in for by two
commands after the input [COMPUTED z11.txt; not measured]. No measured block changed; box still 14x15x14 = 2940. The
opening is the same at every tick, and the close and the returns are y12_holds.py's at every tick outside the 3 blocks,
the stand-in's cell, Z11's column and RB11's park: (-2,5,1) and (-1,5,1) from c3 (RB11 spat east), Z11 and (-2,4,1) from
c61. The last drive needs a measured block moved, the west timer's line: the lead's call (HANDOFF, Calls).
- Holds [COMPUTED]: after the close Z11 (-2,3,1) is held by ARM_Z11 (-2,4,2) and by its own payload RB11 at (-2,5,1), two
  above it (QC). ARM_Z11 is away only in Y12's window (U_Y lifts it at c61 g, it lands back at c66 j), so RB11 has to be
  off (-2,5,1) then and back in (-2,4,1) by the end. The only way into (-2,4,1) is down from (-2,5,1), pushed from
  (-2,6,1) [z11_search.txt, 1].
- The way out [COMPUTED]: H11, a sticky piston at (-3,5,1) facing east, beside RB11, fired by DP's pulse: RB_D lands in
  DP's source cell (-3,4,1), under H11, at c2 j and A_D pulls it back at c3 g, the pulse that spits P11. H11 pushes RB11
  east at c3 g and is spat in the same phase: RB11 rests at (-1,5,1) from c3, beside P10, which it powers until c60.
  P11's head is moving through (-1,3,0) then, in P10's way, so P10's push fails and it goes out at c8 as before. That
  rests on order: H11's spit is queued ahead of P11's (A_D's pull updates H11, above RB_D's old cell, before DP's dust,
  which reaches P11). With P11's first (sim only), or H11 a plain piston (RB11 lands only at c5 j), P10 goes out early and
  the door plane fails (P8, Q, S). Of the twelve one-step moves of RB11 out of (-2,5,1) it is the only one whose piston
  cell is free and whose block lands where it powers nothing that waits [z11_search.txt, 1]. Z11, held by ARM_Z11 alone,
  retracts at c61 g when U_Y's lift updates its head: inside Y12's window, with Y12 retracting and P11 unpowered. With H11
  alone y12_holds.py's verdict holds, and only H11's cell, RB11's two cells (from c3) and Z11's (from c61) differ
  [what-if].
- The way back [COMPUTED, with a STAND-IN]: H11 pulls RB11 back into (-2,5,1) and D11, a piston at (-2,6,1) facing down,
  pushes it into (-2,4,1). R11, a 4-tick repeater at (-2,7,2) on U_Y facing south, reads S_U and points into (-2,7,1), the
  cell above D11: D11 is powered c60 d to c68 d. STAND-IN for H11's second drive: a redstone block at (-3,6,0), beside the
  cell above H11 (it powers no other piston), set before c56 and taken out before c61, both with setblock strict. W_Y's
  extension at c58 g updates H11, which goes out into the empty (-2,5,1); its head lands at c60 j beside U_Y's head,
  which NP12's relight updates then anyway. Z11's retract at c61 g updates H11, unpowered, and it pulls RB11 back, after
  Z11's event, so RB11 lands at c63 j after Z11's base. RB11's landing updates D11: it pushes RB11 down at c64 g while
  ARM_Z11 moves; ARM_Z11 lands at c66 j, RB11 right after it, and Z11, powered again, cannot push RB11 into D11's head.
  D11 goes in at c68 g. End: Z11 in, powered by ARM_Z11 and not updated; RB11 at (-2,4,1); (-2,5,1) and (-1,5,1) empty;
  17 cells outside the door plane still differ from the closed state (20 after y12_holds.py): the other five relays and
  their blocks, and R_9.
- Margins [COMPUTED]: the stand-in works set before c4 to c58 (before c59 it misses W_Y's update) and taken out before
  c59, c60 or c61 (before c58 or c62 it fails). R11 works only at 4 ticks: at 1 to 3 it comes on before H11's head is in
  (-2,5,1) and D11 pushes into the empty cell. RB_U in its park (-1,7,1) powers D11 too (QC) from c14 to c44 and c54 to c60,
  while (-2,5,1) is empty until c58 (the lead's warning): nothing updates D11 then. Order: dust's updates reversed, I_A's
  event last, the scheduled ticks reversed, RB11 landing ahead of Z11's base at c63 j, and the landings of c60 and c66
  reversed among themselves change nothing; 60 runs with the scheduled ticks shuffled return Z11 every time; P11's spit
  ahead of H11's at c3 fails (above). A second cycle is the same.
- Controls fail [COMPUTED]: no H11 (RB11 holds Z11 out); H11 plain (P10 out at c6); no D11 or no R11 (RB11 back on
  (-2,5,1), (-2,4,1) empty); no stand-in (R11 comes on at c60 with (-2,5,1) empty, D11's head arrives beside U_Y's and U_Y
  retracts a tick early: Y12's re-arm fails); stand-in taken out before c62 (H11 pulls only at c64 and Z11 pushes RB11 up
  again at c70).
- The drive [COMPUTED z11_search.txt and what-if; INFERRED where marked]: H11 must be powered at W_Y's extension (c58 g)
  and not from Z11's retract (c61 g) on, without updating W_Y (in and powered c52 to c58), U_Y (out and dark c60 d to
  c61 g) or D11 (dark beside the empty (-2,5,1) before c58). Every cell that powers H11 is the bus's last dust (-4,5,1),
  DP's source cell, CUT_DP, W_Y's head cell or W_Y, D11's cell, a cell where a block also powers W_Y and D11 ((-3,6,1),
  (-3,7,1)) or P_G ((-4,6,1)), or (-3,6,0), whose own neighbours are the bus's dust and stone and P10's QC cell; a dust in
  any free one of them is within two steps of W_Y. No single block in the 249 free cells up to six steps away (6963 runs) returns Z11
  with Y12's re-arm intact (z11_search.txt, 3). The S feed's own time would: a redstone block at (-3,7,1) set before c52
  and taken out before c60, in place of the stand-in, returns Z11 (W_Y, QC from it, is powered then by S_W anyway). A
  stone there under a dust at (-3,8,1), lit from D_S through a dust at (-3,9,2) on glass at (-3,8,2), would carry that
  [INFERRED, 4 blocks], but both dusts join the west timer's line ((-3,8,1) beside its step stone (-3,8,0) under (-3,9,0);
  (-3,9,2) up the glass (-2,9,2) to (-2,10,2)). The line, measured in `close_west_drives_probe`, would have to be re-laid
  off x -3 to -2 there: the call.
- Probe: `close_z11_probe` (`export_z11`): four tests (the stand-in run; no command after the input; H11 taken out; R11
  taken out; the last three controls), replayed in the simulator 4/4; the first test fails with H11 a plain piston or
  without H11, D11 or R11. `python -m scripts.lint close_z11_probe`: ok. To be measured, with the stand-in commands: H11
  out and spat at c3 with RB11 at (-1,5,1) after it and P10 in until c8; H11 out at c58; Z11 in at c61 and RB11 back in
  (-2,5,1) after c63; D11 out at c64 and RB11 in (-2,4,1) after c66; D11 in after c68; Y12's re-arm as in
  `close_y12_holds_probe`. The controls: with no command, D11 out at c60 and Y12 left out; without H11, Z11 out at the
  end; without R11, RB11 left on (-2,5,1).

## DP, stage 2: what the on and the off need (2026-11-21; simulator; the first pass, which found no design)
This pass found no set of real blocks that lights DP and cuts it again. What it computed still holds, and the design
above is the last of its three ways out. `dp.py` computes what the on and the off need and what the free cells allow;
`dp_search.py` screens every one and two added blocks in the free cells of x -4..-2, y 2..6, z -1..3 (40; 41 since the
bus was re-laid, rerun 2026-11-22 with the same result), and the same on
top of the pusher south of DP's source cell: nothing that passes can be built [COMPUTED dp.txt, dp_search.txt]. Through
NA the on alone has a one-block answer and the off has none. The what-ifs below set or clear SRC_P between two block
events of one phase: they show which orders work, not how to get them.
- On [COMPUTED]: lit before T's extension event is queued, P11 shoves the top row (ctl 6). Lit after that and before
  P12's retract event, T's head in (1,3,0) stops the push and P11 waits powered; nothing updates P11 or P6 through c1, and
  NA's relight (RB_A landing, c2 j) updates both: they extend at c3. Lit after P12's retract event they extend in c0. T's
  event is queued at level 1 and runs at level 2, so an on inside an event of level 2 or more is safe in every order;
  inside K's event (level 1) it depends on whether Z_T's ran first. "After P12's retract" is therefore not needed as
  such: any on from level 2 of c0 to c2 gives P11 after P12.
- Off [COMPUTED]: cleared between P11's and P6's extension events, P11 is spat and P6's event is dropped (NA extends P6
  at c4, which is enough for a close by ticks, not for one phase). Cleared after P6's, in that phase or one or two ticks
  later, both are spat; three ticks later both pull their blocks back.
- Who can time it [COMPUTED]: P12's retract event updates one free cell, (0,5,-1). A piston there can face only up or
  down, and at x < 0 its extension updates r_P10, its glass (-1,4,-1) and (-1,6,-1), the bus's glass until the re-lay: nothing carries the
  event west. At x <= -2 the block events of c0 are M_K's (level 0) and K's (level 1); the next are M_K's at c3 (RB12
  landing beside it) and NA's P4 and P6 at c4. An on inside c0 after P12's retract needs an event of level 6 there,
  five levels past K's.
- Source [COMPUTED]: a redstone block lights DP from (-3,4,1) or (-2,4,0). At (-2,4,0) it powers V directly and S by QC.
  At (-3,4,1) it QC-powers M_K (and Z11), so it cannot stand there before c0 [INFERRED]. Beside that cell it can rest only to the
  south, (-3,4,2): at (-3,5,1) it holds the bus's last dust at 15 (and, the bus being one net since the re-lay, K_in and
  I_A with it) and at (-3,3,1) it holds M_K; either way the NP12 kill never comes. The pusher's cell (-3,4,3) is updated by K's event, which would start it at level 2, but nothing powers
  it there, and a stone at (-2,4,3) beside it cuts NP12. The signals in reach are NP12, which dies in that event, and
  blocks that never change [INFERRED].
- Taking it out [COMPUTED]: a piston under the block, (-3,3,1) facing up, is powered by FP and updated by DP's change,
  so it fires with P11 and ahead of P6 (P11 spat, P6 dropped), and its block lands at (-3,5,1), where it relights the
  bus. The other two are the south pusher pulling the block back and a pusher at (-3,6,1) above a spacer [INFERRED]. P11's
  extension event updates the free cells (-2,4,0) and (-2,3,-1) after P6 is queued, P6's updates (-2,2,-1) and (-2,2,1);
  of the pistons that could stand there only (-2,2,1) facing west updates one of the three, the piston under the block,
  and nothing powers it there ((-2,4,0) is QC-powered by RB11 through the open state).
- NA route [COMPUTED]: a sticky piston P_W at (-4,4,-1) facing east has the bus's stone above it and NA's dust north of
  it, so it is powered except from c0 to c2 j. In the closed state it holds CP at (-2,4,-1) and DP reads NA at 8; P11
  does not move (V is in front [INFERRED]). Opening: open-state diff none, the door's pistons and the door plane the same
  at every tick, box 1728 (2016 since the re-lay), DP 0. Close: P_W pulls CP into the cut at c0 (level 0), CP lands at c2 j, P_W pushes it out at
  c3 (level 0) and DP reads NA: P11 extends at level 1 and P6 at level 2, three ticks after P12's retract, as block
  events; the same with dust's updates reversed and I_A's event last. If NA relights before CP lands, the P11 and P6
  events queued then find no power at c3 and are dropped. DP then stays lit: CP's cell takes a block at once only from
  two cells away (a spit) [INFERRED], and those are r_P10's glass (-1,4,-1), the bus's stone (-3,6,-1), NA's stone and a
  cell outside the box. Not adopted: it replaces the stand-in's on with an on no command can cut.
- Search [COMPUTED dp_search.txt]: blocks set without updates into the open state (a piston may stand powered and not
  extended), then the close from the input with no DP command; a pass needs stages 0 and 1 done, P11 out after P12's
  retract and spat, P6 out and spat, S at (0,3,0), no dust lost, by c6 (and, since 2026-11-22, I_A not extending
  again). In the 41 free cells of x -4..-2, y 2..6, z -1..3, with 16 blocks (piston and sticky piston in six facings,
  redstone block, stone, glass, dust): one block, 0 of 656; two blocks, 0 of 209920. On top of the south pusher (sticky
  (-3,4,3) facing north, redstone block (-3,4,2)), which fails alone: one more, 0 of 624; two more, 2 of 189696 (rerun
  on the re-laid bus, which freed (-2,6,-1); before it 40 cells, 0 of 640, 0 of 199680, 0 of 608 and the same 2 of
  179968). The two are one idea: a redstone block at
  (-4,4,3) powers the pusher, K's event starts it, its block lands at c2 j, and a piston at (-4,4,-1) facing south,
  which NA powers at c3, pushes the row (-4,4,0)..(-4,4,3) south, so the pusher loses power after P6's extension and
  pulls its block back. Built, it fails: the pusher and the piston move during the load, DP is lit in the closed state,
  the opening differs from t1, and the row is the bus's glass and stone under its last two dusts and ends outside the
  box [COMPUTED dp.txt]. What it shows is a path from NA's relight to the pusher's power; three and more free blocks
  were not searched.
- What would open it [INFERRED]: the bus's last dust off (-4,5,1), so that a block can rest at (-3,5,1) and a piston at
  (-3,6,1), beside the bus, push it in and pull it back; or a free cell at (-1,4,-1) or (-3,6,-1), to close CP's cell at
  once after P_W's on; or power south of DP that outlives K's event, for the pusher at (-3,4,3).

## Still needed (all local)
1. S H2 feed: done in sim and on the server [MEASURED]. Its inputs: drive C from 13 blocks, F_S out at c10 on a 4-tick
   repeater that reads RB_ST at (2,8,0) and released at c15 by a stone pushed onto its feed's step; RB_F is home at c17 j
   and G_S is taken out [COMPUTED s_inputs.txt; MEASURED: `close_s_inputs_probe` 3/3 on the main server].
2. Trigger order: E0, P_R release, NP12 kill, T and P12's retract run from the input in c0 [MEASURED: `close_trigger_probe`
   4/4 on sat1]. DP on: RB_D's landing at c2 j, P11 out at c3 [MEASURED: `close_dp_off_probe` 4/4 on sat1].
   P10 at c8 on r_P10, V at c11 on R_V, both on NA's relight [MEASURED: `close_p10_v_probe` 3/3 on sat1].
3. Depowers: T's done (W_T, K_T) [COMPUTED]. DP's done for P11: A_D's own head landing releases it and it pulls RB_D
   right behind P11's extension [MEASURED: `close_dp_off_probe` 4/4 on sat1]. P6 is not spat (it extends at c4 on NA): no piston that can take
   DP's source away is reached from P6's extension [COMPUTED dp.txt, dp_off_search.txt].
   P10 and V need none: they extend once and stay out, as the closed door has them [COMPUTED p10_v.txt].
   S's: F_S's feed is cut at c14 j and F_S pulls RB_F home at c15 [COMPUTED s_inputs.txt].
   P9's: R_9's pulse is 2 gt, c20 d to c22 d. P7 and P8 need none: they stay out [COMPUTED p9_p8.txt].
4. The returns: 41 cells outside the door plane differ from the closed state after the close [COMPUTED p9_p8.txt].
   The trigger chain's east side goes home from blocks, with no command [COMPUTED rbt_drives.txt]: RB_T down a column
   (H_T at (1,9,-1) over glass GA and GB, which Z_T lifts with RB_T) after a kick from above by U_T (2,8,-1), which
   RB_ST itself powers; P_R out on a redstone block that P_N pushes into RB_ST's closed cell, RB_ST and a third block
   moving one place on round a loop of five pistons; K_T, sticky now, in at the kick and SPC home with it; the S feed's
   cut resets when RB_ST leaves; one pulse from the S feed's dust times it; 28 cells then still differ. MEASURED
   (2026-11-22, main server): `close_rbt_drives_probe` 4/4, and the six probes re-exported for K_T 23/23. The fix first chosen for RB_T, a piston at (1,7,-1),
   fires in the opening (K_in powers it by QC), and Z_T sticky, W_T sticky or another hold for T do not open it either;
   RB_ST's own route takes eight pistons (rbt_route.txt). The west side goes home from blocks as well [COMPUTED
   west_drives.txt; MEASURED (2026-11-22, main server): `close_west_drives_probe` 3/3]: RB12 kicked west and back by P_W (-6,3,2), which RB_W
   holds and A_W releases, K and M_K in at the kick, then G and RB12 pushed down together by P_G (-4,6,2), WK left
   beside K by M_K's release, K stopped by G above RB12; one pulse from the east return's line; 34 blocks, no measured
   block changed, box 2520; 24 cells then still differ. G ends at (-4,3,2), not at (-3,3,2), which is Y12's head: its
   last cell is the relays' step's, and until then NP12 is lit again (P12 powered, stopped by V's head; A_D powered and
   not updated).
   The opening's relays, which every close leaves fired (X2, Z_Q, Y1, Z_S, Z9, Z11, Y12 with RB_X, C_cut, RB_Q, RB_Y,
   RB_S, RB9, RB11): each is held by its arm, the four that face up also by their payload at R+2. They need no
   re-orienting: Z9 is re-armed in place by command, its arm taken out before c22, D9 (4,5,1) pushing RB9 down at c23
   and the arm back from c23 on [COMPUTED returns.txt; MEASURED `close_returns_probe` 3/3]. Not designed: D9's
   source (on by c23, off from c24) and ARM_Z9's puller (from (5,2,1) or (5,3,2); powered in the closed and the open
   state, off from c22 or before until c23 or after). RB_Y's return relights LY and R_9 then powers P9 behind Q, as RB9
   does, and LY's relight updates Y1, so Y1 needs the blocker, a head in (7,5,-3) [INFERRED]. P8 is held by R_8 on NA, so C_cut's
   return has no deadline. Y12 is held by ARM_Z11, which Z11 shares, and by RB_D; when it retracts G has to go from
   (-4,3,2) into (-3,3,2): Y12 made sticky pulls it there by itself (a measured block of design_c; what-if in
   west_drives.txt), as built it needs a mover from the west, where P_W's head stands. NP12 then dies and A_D, armed
   since RB12 came home, fires once as at c0. First pass [COMPUTED y12.txt]: done with Y12 sticky, three pistons and two
   stand-in sources, inside the west return (c58 to c70); A_D does not fire. From blocks [COMPUTED y12_holds.txt]: 14 more
   blocks, no command after the input, box 2940 (z 5 for B_Y's source, accepted by the lead). Z11, first pass [COMPUTED
   z11.txt]: home with 3 blocks (H11, D11, R11) and one stand-in drive (H11's pull), which needs the west timer's line
   re-laid (the call). Left: D9's source, ARM_Z9's puller and the other up relays.
5. Routing: the bus is laid (east to P_R and AP, west over the input repeater to M_K; re-laid 2026-11-22, box 2016). DP needs no trunk: its tap reads NP12 at (0,5,3).
6. Stages 6 to 8: P7 on NA at c3, P9's 0-tick with TM and TR at c20 and c22, P8 at c23, the door plane closed at c25 j
   [COMPUTED p9_p8.txt]. MEASURED: `close_p9_p8_probe` 3/3 on sat1.
Fired relays under the re-arm design are BUD-armed from f+3 g: close dust within 2 of one resets it [SOURCED door_relay_rearm.md].

## Next
DP's design is MEASURED (`close_dp_off_probe` 4/4 on sat1: RB_D lands ahead of A_D's head and P11 is spat). P10 and V
(stages 3 and 4) are MEASURED from two blocks (`close_p10_v_probe` 3/3 on sat1: V out at c11, S at (1,3,0) after c13). The
S feed's inputs (stage 5) are MEASURED from thirteen blocks: the close runs through stage 5 from the one input with no
command (`close_s_inputs_probe` 3/3 on the main server: F_S out at c10, S spat at c15, RB_F home after c17). The last
stages are MEASURED from nine blocks and a stone: the door plane closes from the one input with no command
(`close_p9_p8_probe` 3/3 on sat1: R_X on at c16, RB9 at (5,4,1) after c18 with LY lit, P9 out at c20, TM at (2,2,0) and
TR at (1,2,0) after c22, P8 out at c23, Q at (3,2,0) after c25; with R_9 removed P9 and P8 stay in, with R_8 removed P8
stays in and Q at (3,3,0)). The returns' first pass (item 4) finds the trigger chain blocked with added blocks, inside the
box or out of it (RB_T: returns.txt), and Z9 re-armed in place by command (`close_returns_probe` 3/3 in game). The bus's
west branch is re-laid over the input repeater (box 2016) and RB_T goes home by command, down a column after a kick, with
the rest of the trigger chain's east side (returns.txt; `close_returns_probe` 6/6 in the simulator and in game). The six
re-exported probes pass in game on the re-laid bus (23/23 on the main server, 2026-11-22). RB_T's return is designed from
blocks and MEASURED (rbt_drives.txt: 49 blocks, K_T sticky, box 2160; `close_rbt_drives_probe` 4/4 and the six probes
re-exported for K_T 23/23 on the main server, 2026-11-22, traits ok): the trigger chain's east side ends as loaded from the
one input with no command. The west side's return is designed from blocks (west_drives.txt: 34 blocks, no measured block
changed, box 2520; MEASURED: `close_west_drives_probe` 3/3 and `close_rbt_drives_probe` still 4/4 on the main server,
2026-11-22, traits ok): RB12, K, M_K and WK end as loaded, G at (-4,3,2), and NP12 is lit again from c60. Y12 is
re-armed from blocks with no command after the input (y12.txt, then y12_holds.txt: Y12 sticky, 22 blocks, box 2940; G
home at (-3,3,2), NP12 and the tap dark, A_D never moves; COMPUTED; `close_y12_probe` measured 0/3 on an export fault,
D_X placed as a dot, now fixed in both probes, both since MEASURED 3/3). Z11's return, first pass (z11.txt; COMPUTED):
Z11 home with 3 blocks (H11 spits RB11 east on DP's pulse at c3, so Z11 retracts in Y12's window; H11 pulls RB11 back and
D11, on R11, pushes it home) and one stand-in drive, H11's pull, which only a re-laid west timer's line lets blocks carry
(the call; `close_z11_probe` to be measured). Next: D9's source and ARM_Z9's puller, then the
same in-place re-arm for Z_Q and Y1 (Y1 with the blocker). If P6 must be
spat, the relay above A_D is the lead: find what holds N_X in through the opening. A close inside one phase would need
DP's on in c0 after P12's retract, five levels past K's event at x <= -2 (dp.txt).

The scripts are in `scripts/door2/close_layout/` (constraints.py/.txt, constraints_P6stage2.txt, feeds.py/.txt,
puller.py/.txt, export_feeds.py, s_feed.py/.txt, export_s_feed.py, trigger.py/.txt, export_trigger.py, dp.py/.txt,
dp_search.py/.txt, dp_off.py/.txt, dp_off_search.py/.txt, export_dp_off.py, p10_v.py/.txt, p10_v_search.py/.txt,
export_p10_v.py, s_inputs.py/.txt, export_s_inputs.py, p9_p8.py/.txt, export_p9_p8.py, returns.py/.txt,
export_returns.py, rbt_route.py/.txt, rbt_drives.py/.txt, export_rbt_drives.py, west_drives.py/.txt,
export_west_drives.py, y12.py/.txt, export_y12.py, y12_holds.py/.txt, y12_holds_search.py/.txt, export_y12_holds.py, z11.py/.txt, z11_search.py/.txt, export_z11.py), run from the repo root as `python -m scripts.door2.close_layout.<module>`; the simulator is `scripts/door2/sim.py`. The specs are in the library:
`library/builds/compactB_open_c.redstone.yaml` (design_c's opening), `library/mechanics/close_feeds_probe.redstone.yaml`,
`library/mechanics/close_s_feed_probe.redstone.yaml` (written by `export_s_feed`),
`library/mechanics/close_trigger_probe.redstone.yaml` (written by `export_trigger`),
`library/mechanics/close_dp_off_probe.redstone.yaml` (written by `export_dp_off`; 4/4 on sat1),
`library/mechanics/close_p10_v_probe.redstone.yaml` (written by `export_p10_v`; 3/3 on sat1),
`library/mechanics/close_s_inputs_probe.redstone.yaml` (written by `export_s_inputs`; 3/3 on the main server),
`library/mechanics/close_p9_p8_probe.redstone.yaml` (written by `export_p9_p8`; 3/3 on sat1),
`library/mechanics/close_returns_probe.redstone.yaml` (written by `export_returns`; 3/3 on the main server),
`library/mechanics/close_rbt_drives_probe.redstone.yaml` (written by `export_rbt_drives`; 4/4 on the main server) and
`library/mechanics/close_west_drives_probe.redstone.yaml` (written by `export_west_drives`; 3/3 on the main server),
`library/mechanics/close_y12_probe.redstone.yaml` (written by `export_y12`; 0/3 on main before the D_X fix, 3/3 after) and
`library/mechanics/close_y12_holds_probe.redstone.yaml` (written by `export_y12_holds`; 3/3 on the main server),
`library/mechanics/close_z11_probe.redstone.yaml` (written by `export_z11`; with the stand-in, not yet run on a server).
On 2026-11-23, with the Y12 holds merged, `close_west_drives_probe` 3/3 and `close_rbt_drives_probe` 4/4 still pass.
The six from `close_trigger_probe` on were written again on 2026-11-22 for the re-laid bus (`close_returns_probe` with
three more tests); the results in brackets are from before it. On the re-laid bus all six pass on the main server
(2026-11-22): 4/4, 4/4, 3/3, 3/3, 3/3 and 6/6. They were written a third time on 2026-11-22 with K_T sticky
(rbt_drives.py) and pass again on the main server, 23/23, with `close_rbt_drives_probe` 4/4. west_drives.py changes none
of them.
Re-run: `python -m scripts.try close_feeds_probe`; `python -m scripts.try close_s_feed_probe`;
`python -m scripts.try close_trigger_probe`; `python -m scripts.try close_dp_off_probe`;
`python -m scripts.try close_p10_v_probe`; `python -m scripts.try close_s_inputs_probe`;
`python -m scripts.try close_p9_p8_probe`; `python -m scripts.try close_returns_probe`;
`python -m scripts.try close_rbt_drives_probe`; `python -m scripts.try close_west_drives_probe`;
`python -m scripts.try close_y12_probe`; `python -m scripts.try close_y12_holds_probe`;
`python -m scripts.try close_z11_probe`;
`python -m scripts.door2.close_layout.s_feed > scripts/door2/close_layout/s_feed.txt`;
`python -m scripts.door2.close_layout.export_s_feed`;
`python -m scripts.door2.close_layout.trigger > scripts/door2/close_layout/trigger.txt`;
`python -m scripts.door2.close_layout.export_trigger`;
`python -m scripts.door2.close_layout.dp > scripts/door2/close_layout/dp.txt`;
`python -m scripts.door2.close_layout.dp_search > scripts/door2/close_layout/dp_search.txt` (about an hour);
`python -m scripts.door2.close_layout.dp_off > scripts/door2/close_layout/dp_off.txt`;
`python -m scripts.door2.close_layout.export_dp_off`;
`python -m scripts.door2.close_layout.dp_off_search > scripts/door2/close_layout/dp_off_search.txt` (about 25 minutes);
`python -m scripts.door2.close_layout.p10_v > scripts/door2/close_layout/p10_v.txt`;
`python -m scripts.door2.close_layout.export_p10_v`;
`python -m scripts.door2.close_layout.p10_v_search > scripts/door2/close_layout/p10_v_search.txt` (about 4 minutes);
`python -m scripts.door2.close_layout.s_inputs > scripts/door2/close_layout/s_inputs.txt`;
`python -m scripts.door2.close_layout.export_s_inputs`;
`python -m scripts.door2.close_layout.p9_p8 > scripts/door2/close_layout/p9_p8.txt` (about 20 s);
`python -m scripts.door2.close_layout.export_p9_p8`;
`python -m scripts.door2.close_layout.returns > scripts/door2/close_layout/returns.txt` (about 2 minutes);
`python -m scripts.door2.close_layout.export_returns`;
`python -m scripts.door2.close_layout.rbt_route > scripts/door2/close_layout/rbt_route.txt` (about a minute);
`python -m scripts.door2.close_layout.rbt_drives > scripts/door2/close_layout/rbt_drives.txt` (about 30 s);
`python -m scripts.door2.close_layout.export_rbt_drives`;
`python -m scripts.door2.close_layout.west_drives > scripts/door2/close_layout/west_drives.txt` (under a minute);
`python -m scripts.door2.close_layout.export_west_drives`;
`python -m scripts.door2.close_layout.y12 > scripts/door2/close_layout/y12.txt`;
`python -m scripts.door2.close_layout.export_y12`;
`python -m scripts.door2.close_layout.y12_holds > scripts/door2/close_layout/y12_holds.txt` (about a minute);
`python -m scripts.door2.close_layout.y12_holds_search > scripts/door2/close_layout/y12_holds_search.txt` (about 5 minutes);
`python -m scripts.door2.close_layout.export_y12_holds`;
`python -m scripts.door2.close_layout.z11 > scripts/door2/close_layout/z11.txt` (about 20 s);
`python -m scripts.door2.close_layout.z11_search > scripts/door2/close_layout/z11_search.txt` (about 30 minutes on one core; it uses every core);
`python -m scripts.door2.close_layout.export_z11`
