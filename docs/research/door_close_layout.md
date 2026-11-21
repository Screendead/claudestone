# Close layout report (close-layout agent, 2026-10-01; saved by the main session from its hand-back)

Labels: SOURCED (file), MEASURED (sat1, plot mechanics_8), COMPUTED (sim.py), INFERRED.

## Verdict
No structural obstruction; full close not yet shown end to end.
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
- DP's on and off (stage 2): no design found on 2026-11-21, the command stays: section "DP, stage 2" below.

Close order [SOURCED plan_common.txt]: 0 P12 retract | 1 T, P9, P1-P6 | 2 P11 | 3 P10 | 4 V H2 | 5 S H2 | 6 P8 | 7 Q H2 | 8 P7

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

## Trigger chain, stages 0 and 1 (2026-11-21; simulator; the server probe is written, not yet run)
One falling input runs E0, P_R's release, the NP12 kill, T's extension and spit and P12's retract inside one block-event
phase, c0 [COMPUTED trigger.txt]. Not as framed in two ways: the T feed is armed in the open state instead of lit in c0, so
the order is T first, P12 after; and DP (stage 2) is still a command, its on and off are not designed.
- Blocks: 36 (12 dust, 17 glass or stone, 5 pistons, 1 repeater, 1 redstone block), I_A sticky (part 1), HOLD (4,6,-1)
  gone. Opening: open-state diff none, the door's pistons and the door plane the same at every tick, box 1728 through the
  opening and the close [COMPUTED].
- Levels: block events run first in, first out, so an event queued inside an event of level n runs after every event of
  level n. Order that rests on levels does not depend on dust's update order [SOURCED sim.py tick; INFERRED].
- Bus: dust fed by K_in (1,8,-2), lit while the input is on. East (2,8,-2), (3,8,-2), (3,8,-1) on stone (3,7,-1) above
  P_R: P_R's hold. (4,8,-2) on stone (4,7,-2) feeds a 4-tick repeater (4,7,-1) into AP. West from K_in's south side
  (1,8,-1), (0,8,-1), (-1,7,-1), (-2,7,-1), (-3,7,-1), (-4,6,-1), (-4,5,0), (-4,5,1) on stone (-4,4,1) above M_K. Stone
  cuts (1,8,0) over DT and (-3,5,0) over DP. The last dust sits on a stone on M_K and the step before it rests on glass:
  with a stone there M_K is QC-held one update longer than its own dust and is never updated again [COMPUTED].
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
  RB_A and RB_T has left, whichever it is. Without the cut over DT the west branch dies with DT, in K_T's event, and the
  close still passes [COMPUTED].
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
- Costs to other items: glass (1,7,-1) under the bus takes item 4's down-pusher cell; glass (-1,6,-1) is one of P10's
  five clean cells; (-4,4,0) and (-3,5,0), item 5's DP cells, are the bus's support and cut, so the DP stand-in is a
  redstone block at (-3,4,1). In the open state T and K_T are powered and not updated, K since the load: one stray
  update fires them.
- DP, not done. Needed: on after P12's retract event, off after P6's extension, each a block event. P12's retract
  event updates (0,5,-1), P10 and S; P11's base update reaches (-2,4,0) and (-2,3,-1) after P6 is queued. (-2,4,0) is
  beside DP, so DP's own change updates a piston there, and nothing P11's or P6's push frees can block one as Z_T's
  head blocks W_T [INFERRED].
- Probe: `close_trigger_probe` (`export_trigger`): the run above and three controls (glass under RB_ST, W_T or WK
  removed with setblock air strict before the opening), 27 to 47 cells and the levels of DT and DS checked against the
  simulator after c0 and later ticks. Its steps, read back from the YAML and replayed in the simulator, pass 4/4; without
  K_T, W_T, M_K or the dust above P_R the first test fails [COMPUTED]. Server (2026-11-21, sat1): 4/4 [MEASURED];
  `close_feeds_probe` 8/8 and `close_s_feed_probe` 6/6 still pass.

## DP, stage 2 (2026-11-21; simulator; no design found, the command stays)
No set of real blocks was found that lights DP and cuts it again, so there is no probe. `dp.py` computes what the on and
the off need and what the free cells allow; `dp_search.py` screens every one and two added blocks in the 40 free cells of
x -4..-2, y 2..6, z -1..3, and the same on top of the pusher south of DP's source cell: nothing that passes can be
built [COMPUTED dp.txt, dp_search.txt]. The on alone has a one-block answer through NA; the off has none. The what-ifs
below set or clear SRC_P between two block events of one phase: they show which orders work, not how to get them.
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
  down, and at x < 0 its extension updates r_P10, its glass (-1,4,-1) and the bus's glass (-1,6,-1): nothing carries the
  event west. At x <= -2 the block events of c0 are M_K's (level 0) and K's (level 1); the next are M_K's at c3 (RB12
  landing beside it) and NA's P4 and P6 at c4. An on inside c0 after P12's retract needs an event of level 6 there,
  five levels past K's.
- Source [COMPUTED]: a redstone block lights DP from (-3,4,1) or (-2,4,0). At (-2,4,0) it powers V directly and S by QC.
  At (-3,4,1) it QC-powers M_K (and Z11), so it cannot stand there before c0 [INFERRED]. Beside that cell it can rest only
  to the
  south, (-3,4,2): at (-3,5,1) it holds the bus's last dust at 15 and at (-3,3,1) it holds M_K; either way the NP12 kill
  never comes. The pusher's cell (-3,4,3) is updated by K's event, which would start it at level 2, but nothing powers
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
  at every tick, box 1728, DP 0. Close: P_W pulls CP into the cut at c0 (level 0), CP lands at c2 j, P_W pushes it out at
  c3 (level 0) and DP reads NA: P11 extends at level 1 and P6 at level 2, three ticks after P12's retract, as block
  events; the same with dust's updates reversed and I_A's event last. If NA relights before CP lands, the P11 and P6
  events queued then find no power at c3 and are dropped. DP then stays lit: CP's cell takes a block at once only from
  two cells away (a spit) [INFERRED], and those are r_P10's glass (-1,4,-1), the bus's stone (-3,6,-1), NA's stone and a
  cell outside the box. Not adopted: it replaces the stand-in's on with an on no command can cut.
- Search [COMPUTED dp_search.txt]: blocks set without updates into the open state (a piston may stand powered and not
  extended), then the close from the input with no DP command; a pass needs stages 0 and 1 done, P11 out after P12's
  retract and spat, P6 out and spat, S at (0,3,0), no dust lost, by c6. In the 40 free cells of x -4..-2, y 2..6,
  z -1..3, with 16 blocks (piston and sticky piston in six facings, redstone block, stone, glass, dust): one block, 0
  of 640; two blocks, 0 of 199680. On top of the south pusher (sticky (-3,4,3) facing north, redstone block
  (-3,4,2)), which fails alone: one more, 0 of 608; two more, 2 of 179968. The two are one idea: a redstone block at
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
1. S H2 feed: done in sim and on the server [MEASURED]. Still to wire, its inputs: F_S on and off (the spit after T's retract
   event) and G_S's hold off after S's extension (drive A), or F_S alone (drives B, C); after drive A, the return.
2. Trigger order: E0, P_R release, NP12 kill, T and P12's retract run from the input in c0 [MEASURED: `close_trigger_probe`
   4/4 on sat1]. Left: DP on. It may come at any level from 2 of c0 to c2, not only after P12's retract; one piston
   through NA gives it at c3 [COMPUTED dp.txt].
3. Depowers: T's done (W_T, K_T) [COMPUTED]. Left: DP off after P6's extension: no piston that can take DP's source
   away is reached from P11's or P6's extension, and no free cell closes CP's cell at once [COMPUTED dp.txt].
4. Z_T/RB_T reset: P_R re-extends, a down-pusher pushes RB_T to (1,5,-1); (1,7,-1) is now the bus's support. Also the
   return of RB_ST and its glass, RB12 and G, K, K_T.
5. Routing: the bus is laid (east to P_R and AP, west to M_K). DP's trunk: (-3,4,1) free; (-4,4,0), (-3,5,0) taken. The
   bus's last dust (-4,5,1) keeps a source from resting above (-3,4,1).
Fired relays under the re-arm design are BUD-armed from f+3 g: close dust within 2 of one resets it [SOURCED door_relay_rearm.md].

## Next
DP's off (stage 2) is the open item: decide between moving the bus's west end to free (-3,5,1), freeing (-1,4,-1) or
(-3,6,-1) for P_W's route, and a different feed for P11 and P6 whose source P6's extension can reach (section "DP,
stage 2"). The probes drive P10 and V (stages 3 and 4) by command: their close feeds are not designed here.

The scripts are in `scripts/door2/close_layout/` (constraints.py/.txt, constraints_P6stage2.txt, feeds.py/.txt,
puller.py/.txt, export_feeds.py, s_feed.py/.txt, export_s_feed.py, trigger.py/.txt, export_trigger.py, dp.py/.txt,
dp_search.py/.txt), run from the repo root as `python -m scripts.door2.close_layout.<module>`; the simulator is `scripts/door2/sim.py`. The specs are in the library:
`library/builds/compactB_open_c.redstone.yaml` (design_c's opening), `library/mechanics/close_feeds_probe.redstone.yaml`,
`library/mechanics/close_s_feed_probe.redstone.yaml` (written by `export_s_feed`) and
`library/mechanics/close_trigger_probe.redstone.yaml` (written by `export_trigger`).
Re-run: `python -m scripts.try close_feeds_probe`; `python -m scripts.try close_s_feed_probe`;
`python -m scripts.try close_trigger_probe`;
`python -m scripts.door2.close_layout.s_feed > scripts/door2/close_layout/s_feed.txt`;
`python -m scripts.door2.close_layout.export_s_feed`;
`python -m scripts.door2.close_layout.trigger > scripts/door2/close_layout/trigger.txt`;
`python -m scripts.door2.close_layout.export_trigger`;
`python -m scripts.door2.close_layout.dp > scripts/door2/close_layout/dp.txt`;
`python -m scripts.door2.close_layout.dp_search > scripts/door2/close_layout/dp_search.txt` (about an hour)
