# Close layout report (close-layout agent, 2026-10-01; saved by the main session from its hand-back)

Labels: SOURCED (file), MEASURED (sat1, plot mechanics_8), COMPUTED (sim.py), INFERRED.

## Verdict
No structural obstruction. The close runs from one input to the closed door's plane in the simulator [COMPUTED
p9_p8.txt]: stages 0 to 8 are measured in game; the returns are not designed, and the trigger chain's cannot be built
from added blocks, whatever the box [COMPUTED returns.txt].
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
  4/4 with the same controls live, lint ok [COMPUTED]; not measured again yet.

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

## The bus re-laid, and RB_T's return (2026-11-22; simulator; nothing here measured yet)
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
  the fourth [COMPUTED]. `python -m scripts.lint close_returns_probe`: ok. Not measured with these blocks.

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
   The trigger chain's east side goes home by command [COMPUTED returns.txt, what-if]: RB_T down a column (H_T at
   (1,9,-1) over glass GA and GB, which Z_T lifts with RB_T) after a kick by N_T (2,6,-3), P_R out on RB_ST's return,
   K_T in at the kick, SPC by command (K_T made sticky would do it); the S feed's cut resets when RB_ST leaves; 28 cells
   then still differ. The fix first chosen, a piston at (1,7,-1), fires in the opening (K_in powers it by QC), and Z_T
   sticky, W_T sticky or another hold for T do not open it either. Not designed: N_T's source and its two pulses, H_T's
   source, RB_ST's return (a route in the screen, up over y 9 and round by (3,7,1); its landing is P_R's hold and must
   fall while RB_T is parked at (2,6,-2)), SPC's mover, and the west side: RB12 (a route west round x -5 if the box
   grows there), K, M_K and G.
   The opening's relays, which every close leaves fired (X2, Z_Q, Y1, Z_S, Z9, Z11, Y12 with RB_X, C_cut, RB_Q, RB_Y,
   RB_S, RB9, RB11): each is held by its arm, the four that face up also by their payload at R+2. They need no
   re-orienting: Z9 is re-armed in place by command, its arm taken out before c22, D9 (4,5,1) pushing RB9 down at c23
   and the arm back from c23 on [COMPUTED returns.txt; MEASURED `close_returns_probe` 3/3]. Not designed: D9's
   source (on by c23, off from c24) and ARM_Z9's puller (from (5,2,1) or (5,3,2); powered in the closed and the open
   state, off from c22 or before until c23 or after). RB_Y's return relights LY and R_9 then powers P9 behind Q, as RB9
   does, and LY's relight updates Y1, so Y1 needs the blocker, a head in (7,5,-3) [INFERRED]. P8 is held by R_8 on NA, so C_cut's
   return has no deadline.
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
the rest of the trigger chain's east side (returns.txt; `close_returns_probe` 6/6 in the simulator). Next: measure the six
re-exported probes in game (`close_trigger_probe`, `close_dp_off_probe`, `close_p10_v_probe`, `close_s_inputs_probe`,
`close_p9_p8_probe`, `close_returns_probe`; `close_feeds_probe` and `close_s_feed_probe` are unchanged); then the drives
of RB_T's return (N_T's two pulses, H_T's pulse, RB_ST's route home timed into RB_T's park, SPC's mover) and the west
side (RB12, K, M_K, G); then D9's source and ARM_Z9's puller, and the same in-place re-arm for Z11, Z_Q and Y1 (Y1
with the blocker). If P6 must be
spat, the relay above A_D is the lead: find what holds N_X in through the opening. A close inside one phase would need
DP's on in c0 after P12's retract, five levels past K's event at x <= -2 (dp.txt).

The scripts are in `scripts/door2/close_layout/` (constraints.py/.txt, constraints_P6stage2.txt, feeds.py/.txt,
puller.py/.txt, export_feeds.py, s_feed.py/.txt, export_s_feed.py, trigger.py/.txt, export_trigger.py, dp.py/.txt,
dp_search.py/.txt, dp_off.py/.txt, dp_off_search.py/.txt, export_dp_off.py, p10_v.py/.txt, p10_v_search.py/.txt,
export_p10_v.py, s_inputs.py/.txt, export_s_inputs.py, p9_p8.py/.txt, export_p9_p8.py, returns.py/.txt,
export_returns.py), run from the repo root as `python -m scripts.door2.close_layout.<module>`; the simulator is `scripts/door2/sim.py`. The specs are in the library:
`library/builds/compactB_open_c.redstone.yaml` (design_c's opening), `library/mechanics/close_feeds_probe.redstone.yaml`,
`library/mechanics/close_s_feed_probe.redstone.yaml` (written by `export_s_feed`),
`library/mechanics/close_trigger_probe.redstone.yaml` (written by `export_trigger`),
`library/mechanics/close_dp_off_probe.redstone.yaml` (written by `export_dp_off`; 4/4 on sat1),
`library/mechanics/close_p10_v_probe.redstone.yaml` (written by `export_p10_v`; 3/3 on sat1),
`library/mechanics/close_s_inputs_probe.redstone.yaml` (written by `export_s_inputs`; 3/3 on the main server),
`library/mechanics/close_p9_p8_probe.redstone.yaml` (written by `export_p9_p8`; 3/3 on sat1) and
`library/mechanics/close_returns_probe.redstone.yaml` (written by `export_returns`; 3/3 on the main server).
The six from `close_trigger_probe` on were written again on 2026-11-22 for the re-laid bus (`close_returns_probe` with
three more tests); the results in brackets are from before it.
Re-run: `python -m scripts.try close_feeds_probe`; `python -m scripts.try close_s_feed_probe`;
`python -m scripts.try close_trigger_probe`; `python -m scripts.try close_dp_off_probe`;
`python -m scripts.try close_p10_v_probe`; `python -m scripts.try close_s_inputs_probe`;
`python -m scripts.try close_p9_p8_probe`; `python -m scripts.try close_returns_probe`;
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
`python -m scripts.door2.close_layout.export_returns`
