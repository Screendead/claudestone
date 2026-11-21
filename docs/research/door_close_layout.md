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
- Open knot: S's H2 feed.

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

## Still needed (all local)
1. S H2 feed. Options [INFERRED]: (a) spit a redstone block into (1,5,1) after V's extension, removed before T lands at
   c2 j; (b) move RB_S's landing off (0,4,2) so dust at (0,4,1) relights DS; (c) free Z_T's cell for wall dust (1,3,-1).
2. Trigger order: E0, NP12 kill, then T feed, P_R release, DP, each a later FIFO event.
3. Depowers: spit relay after T's extension (DT off); one after P6's extension (DP off).
4. Z_T/RB_T reset: P_R re-extends, a down-pusher at (1,7,-1) pushes RB_T to (1,5,-1). Clashes with w1 probe: X_C at
   (1,7,-1) powered by RB_T; P_R's base is w1's L0 dust cell.
5. Routing: DT trunk over the top ((1,7,±1), (2,7,0) free); DP from west/top ((-4,4,0), (-3,5,0) free). Box has 2.18x headroom.
Fired relays under the re-arm design are BUD-armed from f+3 g: close dust within 2 of one resets it [SOURCED door_relay_rearm.md].

## Next
Workflow part "S H2 feed in the top pocket", option (a) first; starter part adopts the trigger order above and takes
FT/DT/CT, P_R, FP/DP/CP as fixed inputs.

The scripts are in `scripts/door2/close_layout/` (constraints.py/.txt, constraints_P6stage2.txt, feeds.py/.txt,
puller.py/.txt, export_feeds.py), run from the repo root as `python -m scripts.door2.close_layout.<module>`; the
simulator is `scripts/door2/sim.py`. The specs are in the library:
`library/builds/compactB_open_c.redstone.yaml` (design_c's opening) and `library/mechanics/close_feeds_probe.redstone.yaml`.
Re-run: `python -m scripts.try close_feeds_probe`
