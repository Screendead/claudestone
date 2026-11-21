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
- Open knot: S's H2 feed. Shown in the simulator on 2026-11-21: section "S H2 feed" below.

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

## S H2 feed (2026-11-21; simulator only, server run pending)
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
  the deciding ticks), lint clean, not run yet. Its steps, read back from the YAML and replayed in the simulator, pass
  6/6; without F_S or RB_F A, B and C fail; without G_S A fails, B and C pass [COMPUTED export_s_feed]. Drive A's use
  inside one phase (the 0 gt close) is INFERRED: commands cannot order events inside a phase.

## Still needed (all local)
1. S H2 feed: the server run of `close_s_feed_probe`. Then its inputs: F_S on and off (the spit after T's retract
   event) and G_S's hold off after S's extension (drive A), or F_S alone (drives B, C); after drive A, the return.
2. Trigger order: E0, NP12 kill, then T feed, P_R release, DP, each a later FIFO event.
3. Depowers: spit relay after T's extension (DT off); one after P6's extension (DP off).
4. Z_T/RB_T reset: P_R re-extends, a down-pusher at (1,7,-1) pushes RB_T to (1,5,-1). Clashes with w1 probe: X_C at
   (1,7,-1) powered by RB_T; P_R's base is w1's L0 dust cell.
5. Routing: DT trunk over the top ((1,7,±1), (2,7,0) free); DP from west/top ((-4,4,0), (-3,5,0) free). Box has 2.18x headroom.
Fired relays under the re-arm design are BUD-armed from f+3 g: close dust within 2 of one resets it [SOURCED door_relay_rearm.md].

## Next
Server run: `python -m scripts.try close_s_feed_probe`. Then the starter part, which adopts the trigger order above and
takes FT/DT/CT, P_R, FP/DP/CP and F_S/RB_F (G_S/HOLD_G for drive A) as fixed inputs. The S probe drives P10 and V
(stages 3 and 4) by command: their close feeds are not designed here.

The scripts are in `scripts/door2/close_layout/` (constraints.py/.txt, constraints_P6stage2.txt, feeds.py/.txt,
puller.py/.txt, export_feeds.py, s_feed.py/.txt, export_s_feed.py), run from the repo root as
`python -m scripts.door2.close_layout.<module>`; the simulator is `scripts/door2/sim.py`. The specs are in the library:
`library/builds/compactB_open_c.redstone.yaml` (design_c's opening), `library/mechanics/close_feeds_probe.redstone.yaml`
and `library/mechanics/close_s_feed_probe.redstone.yaml` (written by `export_s_feed`).
Re-run: `python -m scripts.try close_feeds_probe`; `python -m scripts.try close_s_feed_probe`;
`python -m scripts.door2.close_layout.s_feed > scripts/door2/close_layout/s_feed.txt`;
`python -m scripts.door2.close_layout.export_s_feed`
