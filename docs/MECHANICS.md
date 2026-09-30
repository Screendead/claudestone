# Verified redstone mechanics (Minecraft Java 26.3)

Every entry below is proven by a passing spec in `library/mechanics/<spec>.redstone.yaml`, run tick by tick on a real 26.3 server. Re-prove one with `python -m scripts.try <spec>`. Each entry carries a verdict: **confirmed** (the claim held), **differs** (the claim was partly wrong; the entry states what really happens) or **refuted** (the claim was wrong; the entry states what really happens).

Conventions: `gt` is a game tick; `+N` means N gt after the stimulus. "Strong" power is hard power from a block driven by a repeater, torch, etc.; "weak" power is what dust or a comparator gives a block it points into. Statements marked "inferred" or "not tested" in an entry were not proven; treat them as leads only. Unless an entry says otherwise, measurements were made by command-placed blocks, so player-only interactions (right-click, shearing, page turns) are usually not covered.

Contents: 1 Dust shape and connection; 2 Power delivery and through-block reads; 3 Comparators; 4 Repeaters, locking, tick priority; 5 Torches and lamps; 6 Observers; 7 Pistons; 8 Quasi-connectivity, crafter, copper bulb; 9 Hoppers and containers; 10 Comparator-readable blocks and analog sources; 11 Sculk and vibrations; 12 Entity inputs and projectiles; 13 Tripwire and falling blocks; 14 Rails and minecarts; 15 Environmental and 26.x; then Build ideas.

---

## 1. Dust shape and connection

### dust_transparent_step_one_way
**Verdict:** confirmed
**Behaviour:** On a two-level dust step, a stone step block passes power both ways. With a transparent step block (glass, glowstone, top smooth-stone slab, upside-down stairs, hopper facing down) power only goes up. Driving from below: lead 15 -> low dust 14 -> upper dust 13 -> tail 12. Driving the upper end: tail 15, upper 14, low 0, lead 0, although low still shows east=up and upper still shows west=side, so it looks connected. Stone control: upper 14, low 13, lead 12. Truth table passes with delay 0.
**Use:** A zero-tick, dust-only diode: one transparent step in a line stops backflow at the cost of 1 strength and 1 block of height. A spiral of these gives an upward-only vertical line.

### dust_diagonal_cut_needs_conductor
**Verdict:** confirmed
**Behaviour:** The cell above the lower dust, under the upper dust (the "corner"): air passes power both ways (low 14, upper 13; from the top upper 14, low 13). A solid conductor (stone) in the corner cuts it both ways: from the bottom, low 14 with east=side and upper/tail 0; from the top, upper 14 with west=side and low/lead 0. Glass, bottom smooth-stone slab, glowstone and persistent oak leaves in the corner do not cut (low east=up, upper 13). A sticky piston pushing stone into the corner: at +1 and +2 the corner is moving_piston and the step still conducts; at +3 the stone lands and low drops to 0; after the piston is unpowered, low is back to 13 by +1 and the stone is home by +4. A pushed glass block leaves the step conducting. Neither dust block breaks.
**Use:** Only a solid cap isolates two lines on adjacent diagonals (glass, slab, glowstone, leaves do not, a common compact-bus bug). A sticky piston pushing a conductor into the corner is a non-destructive wire switch: cuts 3 gt after activation, reconnects within 1 gt of release.

### dust_diagonal_step_powers_step_block
**Verdict:** confirmed
**Behaviour:** With a stone step block, a lamp beside the step block (touching no dust) lights when the line is driven (low 14, upper 13). It still lights with the upper dust removed, when the low dust straightens (east=side) and points into the step block. The cause is ordinary weak power from dust pointing into or sitting on a solid block; the UP connection shape cannot be separated from it. With a glass step the line still carries but the lamp stays unlit after 4 gt.
**Use:** A riser's solid step block is weakly powered, so a lamp, piston or dispenser beside it fires (a free indicator, or a gotcha). Use a glass or top-slab step to avoid firing things next to a riser.

### redstone_block_corner_feeds_diagonal
**Verdict:** confirmed
**Behaviour:** An unpowered step starts at low 0 east=up. A redstone block placed in the corner (above the low dust) gives low 15 (east=up and west=side, step still connected), upper 15, lead 14, tail 14. Control: stone in the corner gives low 0 east=side and upper 0 (cut).
**Use:** A redstone block moved into a diagonal's corner injects 15 into both levels at once without cutting the step. Harness drivers placed in such a corner do not isolate the levels.

### dust_redirect_by_signal_sources
**Verdict:** differs
**Behaviour:** Claim: a list of sources beside a line's last dust bend it sideways. Reality: everything on the list did except the crafter. Setup: 3-dust line ending at a lamp; control end 13, east=side, lamp lit. These bend the end (east=none, west=side, south=side) so the lamp goes unlit after 2 gt: `lightning_rod[facing=up]` (itself powered=false), redstone block (end becomes 15), unpowered floor lever, unpowered stone button, trapped chest, inverted daylight detector (in daytime), target block, lit redstone torch, tripwire hook, observer whose output face points at the dust, repeater facing into the dust (its axis end). These do NOT bend it (end stays east=side, lamp lit): repeater side (unpowered, unlocked), observer side face, observer front face, and crafter (dust does not connect to a crafter in 26.3). Comparator side: dust passing a subtract comparator's side bends into it (west/north none, east/south side). With side at 15, the side reaches 15 at +2 gt, the comparator turns off at +4 and its output lamp is dark by +10; in compare mode the comparator stays on.
**Use:** An unpowered lightning rod (or lever, target, trapped chest...) beside a line end turns the last dust sideways so it stops powering the block ahead, without itself becoming powered: the cleanest end-of-line redirect. A bus can run flush against repeater sides and observer side or front faces. Dust passing a comparator's side is a hidden side input that silently corrupts analog logic.

### dust_dot_vs_cross_isolated
**Verdict:** confirmed
**Behaviour:** A dot dust (all sides none) placed by the harness keeps its dot state through the setblock+clone pass and through a neighbour change and an off/on cycle. Powered to 15 from a strongly powered block above, it lights the lamp below and none of its 4 side lamps. A cross (all sides side) lights all 4 side lamps and the lamp below. Once a dust is placed beside the dot (on a support), the dot becomes a line along that axis (the east lamp lights, north/south stay dark; the new dust reads 14).
**Use:** A dot is a 1-block tap that powers only the block beneath it (lamp, hopper lock, note block) in a dense grid, leaving side blocks off. A cross feeds four side blocks plus the one below. The shape is lost as soon as a neighbour connects.

---

## 2. Power delivery and through-block reads

### torch_hard_powers_block_above
**Verdict:** confirmed
**Behaviour:** A lit standing torch hard-powers the block above it: a repeater reading that block is powered, dust beside it reads 15, the repeater's output dust is on. A repeater beside the torch, facing away, is powered. The block beside the torch at the same height gives nothing (repeater off, dust 0), and neither does the block the torch stands on. Removing the torch turns everything off within 4 gt. Only the standing torch was tested; the wall torch's attached block was not.
**Use:** Vertical 1-wide towers (torch, block, torch, ...) and powering through a ceiling with no dust. Torches can sit beside conductor blocks in dense layouts without feeding them.

### dust_powers_block_below
**Verdict:** confirmed
**Behaviour:** A straight, powered dust line (east=side, west=side, power 14) powers the block directly under it. Hopper goes enabled=false, dropper and dispenser go triggered=true, a lamp under the line lights. At the far end (power 7) the line still fires the dispenser. Dust on glass or on a top smooth-stone slab carries power 14 but does not light a lamp beside the support; the same line on stone does. After the input is removed (wait 4) the hopper is enabled=true again. The hopper test checks the enabled property, not item movement.
**Use:** Lay a dust line directly on a row of hoppers to lock them all (a hopper-lock bus) with no side wiring; the line can also fire droppers or dispensers under it. To run a line past a lamp or piston without switching it, put the dust on glass or a top slab.

### weak_powered_block_skips_dust
**Verdict:** confirmed
**Behaviour:** Dust at 15 pointing into stone: the stone drives a lamp beside it (lit), a repeater leading away (powered, its output dust on) and a torch on top (unlit), but a dust dot on the stone's far face stays at 0. Control: a repeater powers the same stone and the dot reads 15, with the same lamp, repeater and torch reaction. Both return to off 6 ticks after the input is removed. Pistons, comparators and dispensers on the block were not tested.
**Use:** Signal crossing or fan-out: dust into a block drives lamps, repeaters and torches on its other faces while a perpendicular dust line touching the same block stays separate. To carry the signal on in dust past the block, feed it with a repeater instead.

### comparator_through_block_keeps_dust_level
**Verdict:** confirmed
**Behaviour:** Dust at power 7 (end of a 9-dust line) pointing into stone: a comparator (compare mode, no side input) reading that stone outputs 7. A 4-dust line (12 into the stone) gives 12. A repeater in the same position outputs 15. All outputs are 0 again 8 ticks after the input is removed.
**Use:** Carries an analog strength through a one-block wall unchanged, for strength buses and encoders. A repeater there would replace the value with 15.

### comparator_container_masks_weak_block_power
**Verdict:** confirmed
**Behaviour:** Dust at exactly 10 points into stone; a comparator (facing north) reads that stone with a chest behind it. The chest's reading replaces the stone's power even when lower: empty chest gives 0 (before and after powering), 1 stick gives 1, no chest gives 10. With a repeater hard-powering the stone to 15 and 1 item in the chest, output is 15; dust at 15 into the stone with an empty chest also gives 15, so the chest is ignored at 15 from either source.
**Use:** A container sensor can share its block with a signal line at 1-14 and still read correctly, no isolating gap needed. Power the block to 15 to override. Warning: a weak line into a sensor block is hidden whenever a container sits behind it.

---

## 3. Comparators

### comparator_side_input_sources
**Verdict:** differs
**Behaviour:** Setup: subtract comparator, redstone block behind it (rear 15), output dust. Side empty: output 15. Side sources that count (output drops to 0): redstone block, dust at 15, a powered repeater facing into the side. Side sources that leave the output at 15, i.e. the side reads 0: stone hard-powered by a repeater, a lit standing torch, a lit wall torch on a block beyond, a floor lever with powered=true, a floor stone button with powered=true, a daylight detector with nonzero power, a target block at power 15. Rear control: a standing torch in the rear cell drives the comparator to 15. What differs is the observer: it does count as a side source, but its 2 gt pulse (on at +2 after the seen change, off at +4) is swallowed when the comparator output feeds plain dust (comparator stays powered +1..+8, dust stays 15). When the output faces a repeater, the comparator dips exactly +4 and +5 and is back on at +6. (The swallowing explanation is from reading game code, not tested.) A target block placed fresh by setblock resets to power 0.
**Use:** Torches, levers, buttons, daylight detectors, target blocks and hard-powered blocks can sit against a comparator's side without subtracting. For an intended side input use dust, a redstone block or a diode. A torch-inverted subtract input silently does nothing. An observer pulse into a comparator side shows only if the output faces a diode.

### comparator_compare_is_ge
**Verdict:** confirmed
**Behaviour:** Rear dust at 7. Compare mode: side 0 gives 7, side 6 gives 7, side 7 (tie) gives 7, side 8 gives 0. Subtract mode, rear 7: side 3 gives 4, side 6 gives 1, side 7 gives 0, side 9 gives 0. Values read as the exact power of the output dust.
**Use:** One comparator gives A >= B on analog values, ties pass. Subtract gives max(A-B, 0); side >= rear inhibits it. Two comparators make a band decoder.

---

## 4. Repeaters, locking, tick priority

### repeater_lock_only_by_diodes
**Verdict:** confirmed
**Behaviour:** Only a powered diode (repeater or comparator) facing into a repeater's side locks it. A delay-1 repeater locked (locked=true) held a 1 for 8 gt after its data dropped and held a 0 for 8 gt after data rose, then followed its input again. Five controls beside it left it locked=false and following data within 4 gt: power-15 dust, a redstone block, stone hard-powered by a repeater, a lit standing torch, an observer checked on the tick it was powered.
**Use:** Two-repeater torchless latch (lightless, cannot burn out). Dust buses, redstone blocks, powered blocks, observers and torches can sit beside a repeater latch's side without locking it by accident.

### repeater_lock_discards_pending_tick
**Verdict:** confirmed
**Behaviour:** A delay-4 repeater (8 gt) got rising data at t0 and a delay-1 lock repeater was powered at a chosen tick. Lock landing at t0+2, 4, 6, 7 or 8 gt: the output never turned on (locked=true, powered=false, still so 60 gt later); at t0+8, the same tick as the output, the lock wins. Landing at t0+9, 10 or 12: the repeater turned on and held. The dropped change is not replayed; the repeater re-evaluates only on unlock and then takes a full new delay (output rose 8 gt after locked went false, 10 gt after the lock input was released).
**Use:** Sample window: the latch ignores data arriving less than 2*delay gt before the lock (the lock's own tick included). Cheap rejection of late signals or glitches in latches and clocked registers.

### diode_side_input_tick_priority
**Verdict:** differs
**Behaviour:** Claim: diode locks get tick priority. True for repeaters only. A delay-1 repeater lock scheduled 2 gt after a delay-2 data repeater's change still ticks first when both land on the same game tick (rising data stays 0, falling data holds 1, both locked). Comparators get no such priority: a comparator lock scheduled after the data change loses the same-tick race (rising: data latches 1; falling: data latches 0). If both are scheduled in the same tick against a delay-1 repeater, a rising race goes to whichever was scheduled first (they share one priority level). Against a falling output the comparator lock loses even when scheduled first. A comparator lock landing 1 gt before the output tick locks in time.
**Use:** A repeater-locked latch needs no padding on its lock path: a lock landing on the data repeater's output tick still wins. A comparator-driven lock needs at least 1 gt of margin or it races by schedule order (rising) and loses (falling). A lock and data arriving together at the data repeater's input always hold the old value (see repeater_lock_discards_pending_tick).

### repeater_extends_short_pulses
**Verdict:** differs
**Behaviour:** Repeater half confirmed as an exact rule: output width = max(input width, 2*delay) gt, starting 2*delay after the input rises. Measured for inputs of 1, 2, 3, 5 gt against delays 1-4: 1 gt at delay 1 gives 2 gt; 2 gt gives 2/4/6/8; 3 gt gives 3 at delay 1, 4 at delay 2; 5 gt gives 5/5/6/8. A real 2 gt observer pulse through a delay-4 repeater lasts 8 gt (on +10 to +17). Comparator half differs: it passes pulses of 2 gt or more unchanged, 2 gt later (2, 3, 5 gt stay 2, 3, 5), but a 1 gt pulse gives no output at all.
**Use:** A one-block pulse extender up to 8 gt with no loop, for example to give pistons long enough pulses. A comparator is not a transparent pulse relay: it removes 1 gt pulses, so it is a 1 gt pulse filter.

### dust_update_order_locational
**Verdict:** confirmed
**Behaviour:** `redstone_experiments` is disabled on the main world and all satellites, so the legacy locational update order applies. A symmetric dust fork feeds two normal pistons pushing blocks into a shared cell; only the first block event succeeds. At the plot's z+0 row the right-hand piston (seen from the input) wins in all 4 rotations; an identical copy at z+12, x+0 picks the left-hand piston. Deterministic across ~15 runs, so the winner depends on position, not design. Rotation did not change the winner here. Control: a delay-1 repeater on one branch and delay-2 on the other makes the 1-tick side win at 0 and 180 degrees. "Dust updates blocks it cannot power" was not tested.
**Use:** Library rule: no shipped build may depend on which of two same-tick dust-fed components acts first, because the winner changes when the build is moved. Break ties with repeaters of different delays. The spec also guards the default: if Mojang makes the experimental order default, it fails.

---

## 5. Torches and lamps

### torch_burnout_one_shot
**Verdict:** differs
**Behaviour:** Torch on stone hard-powered by a delay-1 repeater. Input 3 gt on / 3 gt off toggles it every 6 gt. It burns out on its 8th turn-off within 60 gt (t=46) and stays unlit; 7 turn-offs leave it working; a 20 gt clock never burns it over 12 cycles. Differs from the claim in recovery: it relights by itself exactly 160 gt after the burnout turn-off (lit=false at +159, lit=true at +160) with no update needed. Updates meanwhile are ignored, including input pulses 54 and 104 gt after burnout. If the input is still on at +160 it stays off and relights 2 gt after release. Direct 2 gt pulses via a redstone block do not toggle it (redstone blocks do not power solid blocks); 2 gt pulses via a repeater were not measured.
**Use:** Self-limiting burst: a fast clock (period under 7.5 gt) through a torch gives exactly 8 low pulses, then the torch stays off for a fixed 160 gt, ignoring input, and resets itself. A timed fuse or one-shot, not a latch needing an update to re-arm. Torch logic cannot follow fast clocks.

### lamp_off_delay_4_ticks
**Verdict:** confirmed
**Behaviour:** A lamp lights in the same tick a redstone block is placed beside it. After removing the input the adjacent dust goes to 0 at once, but the lamp stays lit +0..+3 and goes dark at exactly +4; a 20 gt pulse gives the same 4 gt tail. A repeater reading the lamp block stays off throughout. Hard-powered control (a repeater into the lamp): the feeding repeater turns off at +2 and the reader repeater at +4 while the lamp is still lit at +4 and +5; the lamp goes dark at +6, 4 gt after its own power ended. A lit but unpowered lamp is not a signal source.
**Use:** Decode glitches shorter than 4 gt never flash a 7-segment digit; the lamp is a free pulse stretcher. Timing tests on lamp outputs must allow the 4 gt tail. A lamp cannot be memory or a pulse-extender source, because its lit tail powers nothing.

### dust_emits_no_light
**Verdict:** confirmed
**Behaviour:** Dust driven by a redstone block to 15 (and the next dust at 14), sealed in a stone box, leaves light level 0 at both dust cells (`execute unless predicate {type:"location_check",predicate:{light:{light:{min:1}}}}` passes). Control: a lit redstone torch sealed the same way reads exactly 7 at its own cell. From the 26.3 source (not measured): a block state change queues a light check only when emission or dampening differs, or either state uses its shape for light occlusion (`LightEngine.hasDifferentLightProperties`); dust, repeaters and comparators never do, while torches, lamps, copper bulbs, daylight detectors, lecterns, sculk sensors and pistons do. Light checks were not counted directly (`perf` profiling would be needed).
**Use:** The `lightless` trait means no light checks: dust, repeaters and comparators carry signals without light work; a torch costs one light check per toggle.

---

## 6. Observers

### observer_dual_edge_powered_state
**Verdict:** confirmed
**Behaviour:** Watching a trapdoor (open=true, powered=true) or note block (powered=true), the observer is on at +2..+3 on the rising edge and again at +2..+3 on the falling edge, 2 gt each. Watching a lamp: it lights at +0 and its observer pulses at +2..+3; on power off the lamp stays lit until +3, goes dark at +4, and its observer pulses at +6..+7, exactly 4 gt later than the trapdoor or note block pulse. Stone control: no pulse. Doors, fence gates and repeaters were not tested.
**Use:** Two-block dual-edge pulse generator: input -> trapdoor or note block -> observer gives a 2 gt pulse on each edge (for example lever to T flip-flop). A lamp as the watched block delays the falling-edge pulse by 4 gt with no repeater.

### observer_dust_level_vs_block_entity
**Verdict:** differs
**Behaviour:** Partly holds. (1) Hopper (64 stone) -> comparator -> dust at 3. Appending 64 more stone via `data modify` makes dust 6 at +2 gt; the observer is off +1..+3, on +4..+5, off +6. Adding 1 more item leaves dust at 6 and the observer silent. Removing the stack (6 -> 3) gives the same pulse. (2) A dot dust: `setblock stone` beside it leaves the dot, no pulse. `setblock waxed_lightning_rod` beside it changes the dust to east=side (power 0) and the observer pulses at +2..+3. (3) Chest contents changed by `item replace` or `data modify`: no pulse. (4) Refutes the claim that repeater lock changes are silent: locking a repeater sets locked=true at +2 and the observer pulses at +4..+5; unlocking is the same. `locked` is block state, so observers see it. (5) Command quirk: `item replace ... container.1` on a hopper never updates the comparator (dust stayed 3 for 8+ gt); `data modify` updates it in 2 gt. Composter/cauldron levels, furnace lit and chest opening were not tested.
**Use:** Observer on comparator-fed dust is an analog change detector: pulses when a container's fill level changes, quiet when the count changes within a level. It also detects a connecting block at a dust end (a shape change with no power change). Contents must be read through a comparator. Repeater lock/unlock is not silent: an observer beside a repeater pulses 2 gt after each lock change, a lock-change detector and an accidental glitch source.

### moved_observer_pulses
**Verdict:** confirmed
**Behaviour:** Sticky piston pushing an observer (facing north, output into dust): moving_piston at +1..+2, landed powered=false at +3..+4, powered=true at +5..+6 (dust behind it 15), off at +7. The pulse starts 2 gt after landing and lasts 2 gt, in both directions. If moved again while lit (retract at +5), dust drops to 0 at +6, so the pulse is 1 gt, and it lands unpowered and stays dark 10+ gt. If moved again before its pending pulse (retract at +4, landed at +3, not yet powered), no pulse happens at either position for 10+ gt: the pulse is lost. A retract on the tick the pulse would end anyway (+6) counts as idle and pulses again at home.
**Use:** A piston-moved observer gives its own "arrived" signal: a 2 gt strength-15 pulse 2 gt after landing, in both directions. Core of flying machines and clockless step sequencers. Moving it within 2 gt of landing loses the pulse, a hazard for fast piston engines.

### copper_oxidation_fires_observers
**Verdict:** confirmed
**Behaviour:** With random_tick_speed 4096 for 300 gt, `weathered_copper_bulb[lit=true,powered=false]` became `oxidized_copper_bulb[lit=true,powered=false]` (properties carried over) and `weathered_lightning_rod[facing=up]` became `oxidized_lightning_rod[facing=up,powered=false]`. Each watching observer fired once. Waxed variants were unchanged and their observers stayed quiet. Passed 3 of 3 runs. Tested only for weathered -> oxidized on bulbs and lightning rods; other stages, doors, trapdoors, chests and golem statues not tested. The gamerule was reset to 3, assumed vanilla.
**Use:** Build hygiene: ship waxed copper. An unwaxed bulb or lightning rod next to an observer fires it at a random later time, and an oxidising bulb keeps its lit state. Supports a factual "stable" trait: no unwaxed weathering copper.

### note_block_trumpet_copper_oxidation
**Verdict:** confirmed
**Behaviour:** A note block on `waxed_copper_block` loads with instrument=trumpet. Changing the block below re-tunes it on the same tick: waxed_exposed_copper -> trumpet_exposed, waxed_weathered_copper -> trumpet_weathered, oxidized_copper -> trumpet_oxidized, copper_block -> trumpet. Each change fires the watching observer (off +0..+1, on +2..+3, off +4). Control: stone -> cobblestone under a note block keeps basedrum and gives no pulse. Waxed and unwaxed behave the same. Driven by setblock, not real random-tick oxidation. The id is `waxed_copper_block`, not `waxed_copper`.
**Use:** A note block on copper reads the copper's oxidation stage with no redstone: an observer on it pulses when the stage below changes (oxidation or scraping; waxing does not change the id). Adds four trumpet timbres to note-block ROMs, selected by the block below.

---

## 7. Pistons

### sticky_piston_short_pulse_drops_block
**Verdict:** confirmed
**Behaviour:** Sticky piston facing east, stone in front, driven N gt. With N=1 or 2 the stone is left at +2, +1 is air, base ends retracted (N=2: t+1 base extended and +1/+2 moving_piston; one tick after power off the stone is already a real block at +2, the retract finalised instantly; base is moving_piston 2 gt, retracted 3 gt after unpowering). With N=3 or 4 the stone is pulled back (t+3 piston_head at +1, stone at +2; then moving_piston, stone at +1 2 gt later). Threshold is exactly between 2 and 3 gt. Correction to the claim: the next 2 gt pulse does retrieve the block (from +2 back to +1), and a third pushes it out again.
**Use:** A pulse-length discriminator from one sticky piston (<= 2 gt leaves the block out, >= 3 gt brings it back). Also a one-piston T flip-flop or block toggler: each 1-2 gt pulse moves the block between +1 and +2, so its position is the stored bit (for example a redstone block powering one of two lines).

### piston_same_tick_pulse_ignored
**Verdict:** confirmed
**Behaviour:** A redstone block placed then removed at a sticky piston's back with no tick step between does nothing, for two consecutive harness drives and for two setblock commands in one run: after 1 and 8 gt the piston is still extended=false, stone unmoved. Controls: a lone setblock of the block extends it by the next tick; a 1 gt pulse (drive, wait 1, undrive) extends it (extended=true, +1 moving_piston at t+1) and drops the stone at +2. The queued extend event re-checks power when block events run and cancels.
**Use:** Command-driven or instant-update 0-tick pulses cannot fire pistons: power must still be present when block events run (at least 1 gt). Pistons filter glitches shorter than 1 tick. Harness pulse drivers need wait >= 1 between on and off.

### piston_one_tick_instant_transport
**Verdict:** differs
**Behaviour:** Redstone block pushed toward destination dust, source dust beside the origin. Normal piston, 1 gt pulse: motion starts at t+1 (source dust 15 -> 0); at t+2 the head spot is air but the pushed block is still moving_piston and destination dust 0; it lands at t+3, the same as a held pulse. So for a normal piston a short pulse only cuts the head. Sticky piston, 1 gt pulse: the redstone block is a real block at +2 by t+2 (destination 15), 1 gt earlier than held (t+3): the spitting finalTick. For both types the origin stops emitting the tick motion starts, because moving_piston emits nothing, so the two ends are never powered together.
**Use:** A sticky piston fed a 1 gt pulse carries a redstone block to its destination in 2 gt instead of 3 and leaves it there (lightless carrier). A normal piston gains nothing. In both cases the origin goes dark the tick motion starts, leaving a 1-2 gt gap with neither end powered.

### piston_redstone_block_chain_instant_off
**Verdict:** confirmed
**Behaviour:** Three sticky pistons in a zigzag, each extended one holding a redstone block that powers the next piston, output dust after the last. Falling edge: 1 gt after the input block is removed all three pulled blocks are in motion (old positions air, retracted positions moving_piston) and output dust is 0 at t+1; by t+3 all three blocks rest retracted with pistons extended=false. Rising edge: 3 gt per stage (first block lands t+3, second t+6, third t+9, output 15 at t+9).
**Use:** A falling-edge wire whose delay does not depend on length: any number of stages turns off in 1 gt (vs 2 gt per repeater), for fast doors and synchronised retraction. Rising edge costs 3 gt per stage, so it is instant in one direction only.

### piston_ignores_power_from_face
**Verdict:** confirmed
**Behaviour:** `piston[facing=east]` with a redstone block directly in front stays extended=false through settle and a neighbour update. A redstone block behind, to the north side, above or below extends it within 4 gt (placed behind, it pushes the front redstone block 2 blocks away). A redstone block diagonally above the face (pos+up+east) with the front block removed leaves the piston retracted until a neighbour update, then it extends within 4 gt: quasi-connectivity counts the front-above diagonal.
**Use:** A sticky piston can park a redstone block against its own face without powering itself, so a redstone-block carrier shuttles between the face and an output 2 blocks away with no spacer. Keep the front-above diagonal clear of power or it activates the piston on the next update.

### piston_push_limit_breakable_tail
**Verdict:** confirmed
**Behaviour:** Piston facing east with 12 stone then air: extended=true within 6 gt, head at +1, stone at +2..+13. With 13 stone: extended=false at 6 gt and nothing moved. With 12 stone then redstone dust: extended, stone moved, dust destroyed and a redstone item spawns, so the dust does not count toward the 12-block limit. That 13 blocks give no animation is inferred from the end state.
**Use:** An actuator that fires only if the line holds 12 blocks or fewer, so a 13th block disables it (a piston AND with no redstone between). A line ending in dust or a torch is a one-shot fuse or reset keeping the full 12-block capacity. Not silent (breaking dust makes a sound).

### piston_block_entity_stoppers
**Verdict:** confirmed
**Behaviour:** With the piston pushing stone into each of these, the piston stays extended=false and both blocks are unmoved: hopper, chest, furnace, dispenser, dropper, jukebox, beacon, ender chest, crafter, oak shelf, barrel, spawner, enchanting table, obsidian, crying obsidian, bedrock, reinforced deepslate, end portal frame, and an extended piston (head in place). Control: stone with air behind moves. A retracted `piston[facing=north]` is pushed from +2 to +3 and stays retracted. An iron door (both halves) is destroyed and drops an item. An open iron trapdoor moves to +2, keeps open=true, no drop. A lone piston_head was not tested.
**Use:** A working component (hopper, dropper, crafter, shelf, barrel) doubles as the piston stop, so no obsidian or extra column is needed. Pushing retracted pistons is how extenders work. In flying doors, doors break but trapdoors survive and keep their open state.

### piston_glazed_terracotta_slime_barrier
**Verdict:** differs
**Behaviour:** Glazed terracotta beside a slime block stays put while the slime moves +1; a stone control moves with the slime. Honey beside slime also stays put. A sticky piston pushes glazed terracotta to +2 and leaves it on retraction; stone is pulled back. Heavy core does NOT behave this way (claimed push-only): a sticky piston pulls it back to +1 and a slime block carries it along (moved to +2 beside the slime).
**Use:** Glazed terracotta, or a honey/slime boundary, separates two slime/honey structures, or a structure and a fixed wall, with no air gap, saving a block in flying machines, doors and sequencers. Heavy core cannot be used for this.

### pull_origin_air_at_event
**Verdict:** confirmed
**Behaviour:** A sticky piston facing east is held extended by a delay-1 repeater, with a stone on its face. The input is removed at t:
- at +1 the repeater is still on and nothing has moved;
- at +2 the repeater is off, and in that same tick the stone's cell is air while the head cell and the base are moving_piston. `data get` reads progress 0.0 at +2 and 0.5 at +3, because the saved value lags one tick;
- at +4 the stone is real in the head cell and the piston is retracted.

So the retract event R is the repeater's own off tick: the origin is air at R and the block is real at R+2. A second variant uses a retracted sticky piston with a stone 2 cells ahead and a 1 gt direct pulse. The piston extends at +1 and the stone is untouched. At +2 the retract event empties the stone's cell and pulls the stone into the head cell, where it is moving_piston at +2 and +3 and real at +4.
**Use:** A block pulled out of a door frame leaves its frame cell empty in the event tick, 2 gt before it lands in the wall. A timer that scores "frame cell empty" reads R; one that scores "block landed" reads R+2. A repeater-driven piston acts in the repeater's own tick.

### piston_zero_tick_chain_same_tick
**Verdict:** confirmed
**Behaviour:** The layout:
- Sticky piston Q (east) is powered only through stone B, which a delay-1 repeater hard-powers.
- Stone K sits 2 cells in front of Q.
- Piston Z faces B and is powered by a comparator on the same input.
- Piston Y (north) has K and then obsidian in its line and is powered by a redstone block, so it is blocked.

Both inputs are driven at t. Nothing has moved at +1. At +2:
- Z is extended, with its arm in B's old cell and B moving;
- Q's base is moving_piston and K is moving into Q's head cell;
- K's old cell holds Y's moving arm, and Y is extended.

At +4 K is real in Q's head cell, Q is retracted and Y's head is in K's old cell. Control: with the repeater alone, Q is extended at +2, K has not moved and Y is still.

The mechanism, read from source and consistent with the result:
- The repeater turning on (HIGH) queues Q's extension in the scheduled-tick phase, before the comparator (NORMAL) queues Z's.
- In the block-event phase Q extends, then Z pushes B. B's vacated cell updates Q, which is now unpowered.
- Q's retract event runs in the same phase and pulls K. It is event 1 because the cell 2 ahead holds a real block.
- K's vacated cell updates Y, and Y's extension also runs in that phase.
**Use:** A 0-tick pull: both of the piston's edges fall in one tick, and a block 2 cells away is moved that tick. A chain of piston events can run inside one tick, ordered by when each event was queued. The depower must be queued after the victim's extension; if it runs first, the extension re-checks its power and is dropped (piston_same_tick_pulse_ignored). Scheduled-tick priority (repeater before comparator) is one way to get that order.

### spat_piston_fires_same_tick
**Verdict:** confirmed
**Behaviour:** A sticky piston pushes a retracted piston W (facing north) toward a cell beside a redstone block.
- With a 1 gt pulse (on at t, off at t+1), W is moving at +1. At +2 the sticky piston's base is moving_piston and its head cell is air, and W is real at the far cell, `extended=true`, with its own arm moving_piston. W was spat and extended in the same tick.
- With an in-tick 0-tick (the piston_zero_tick_chain_same_tick arrangement), W is already extended at the far cell in the event tick E, and the sticky piston's head cell is air.
- Control: without the depower, W is still moving_piston at E.
**Use:** A spat piston acts in the spit tick, so a carrier that 0-ticks costs 0 gt per extender stage, against 3 gt when the moved piston lands (piston_landed_powered_extends_next_tick). This allows 0-2 gt door closings by spit chains. Hazard: any piston spat onto a powered cell fires at once.

### piston_landed_powered_extends_next_tick
**Verdict:** confirmed
**Behaviour:** A sticky piston pushes a retracted piston onto a cell beside a redstone block, with an event at +1. The moved piston is moving_piston at +1 and +2, real and unextended at +3 (event + 2), and extended with its arm moving_piston at +4 (event + 3). The same holds when it is pulled back onto a powered cell: it lands unextended at R+2 and extends at R+3. One landed on an unpowered cell stays retracted for the next 10 gt.
**Use:** An extender stage costs 3 gt from event to event when the moved piston lands. Every piston a door moves must land unpowered, or it fires 1 gt after landing.

### piston_moved_source_zero_tick_depower
**Verdict:** confirmed
**Behaviour:** In both cases a piston X is depowered in the same block-event phase in which it extends. It then 0-tick pulls a stone from 2 cells ahead. The second mover Z is a BUD piston armed by a redstone block set two cells above it; no update reaches Z when that block is placed.
- **Lit observer.** X (sticky, east) is powered through stone F by an observer's output. Z sits behind X, facing the observer. The observer is triggered at t. At +2, its on tick:
  - Z is extended and the observer is moving;
  - X's base is moving_piston and the stone is moving into X's head cell.

  At +4 the stone is real and X is retracted. Control without arming: X is extended at +2 and holds for the observer's 2 gt pulse.
- **Redstone block.** X is powered by a redstone block beside it, but its line (stone, stone, obsidian) is blocked. Sticky piston A pulls the first stone out sideways at +1 (input removed at t). In that tick:
  - X extends into the gap;
  - Z, armed beside the gap and facing the redstone block, pushes the redstone block away;
  - X retracts and pulls the second stone into the gap.

  Everything is real by +3. Control without arming: X extends and holds.

Mechanism, read from source; the results agree:
- Observer case: Z is woken by X's own extension (the base's neighbour update), so the order is causal. A lit observer with a pending tick that is moved updates its output side as if off, which reaches X through F.
- Redstone-block case: X and Z are both woken by the vacated gap cell, whose neighbours update in order W, E, D, U, N, S. X is west of the gap and Z north, so X is queued first. That order is directional. [inferred; the build was not tested rotated]
- Both cases passed in two plots (mechanics_3 and mechanics_6).
**Use:** Depowers a door's slot pistons within the same phase. A QC-armed BUD piston beside a piston's base is a relay that always runs after that piston. An observer is the reusable power source for a piston whose only free input is below a floor block.

### piston_qc_shared_side_input
**Verdict:** confirmed
**Behaviour:** The layout:
- Sticky pistons S and T face up, with T directly under S.
- Stone F beside S is hard-powered by a repeater.
- S's line is a stone and then a gate piston's head.

With F on, the gate is removed without updating either piston, and both stay retracted. Then:
- An update to T alone, from a neighbouring piston retracting, makes T extend at +1 and push S and the stone up. S lands unpowered 2 gt later.
- Control, F off: the same update leaves T still.
- Updating S first (a block set beside it) makes S fire. T, updated by S's base, finds an extended piston in its line and stays retracted, even after its own update.
**Use:** In a stacked column of two pistons, T's quasi-connectivity reads every side input of S. Once their shared line clears, whichever is updated first fires. A door that powers the upper piston from the side must make sure the lower one is not updated first, or it shoves the upper piston and its line.

---

## 8. Quasi-connectivity, crafter, copper bulb

### piston_quasi_connectivity_bud
**Verdict:** confirmed
**Behaviour:** Sticky piston facing east with a redstone block placed by setblock 2 above (air between): still extended=false after 6 gt. A stone setblock beside it makes it extended=true 1 gt later, sticky head in front by 4 gt. With no power the same update does nothing. With the block removed it stays extended 6+ gt, and the next neighbour update retracts it within 4 gt. A redstone block directly above extends it within 1 gt with no update. A dropper behaves the same: power 2 above leaves triggered=false and the item unfired after 8 gt; a neighbour update makes it fire within 8 gt. Dispensers and normal pistons not tested separately.
**Use:** An observer-free BUD, and 1-bit memory held in the piston's state. A power line along the top of a row can drive pistons or droppers two below it. Avoid accidental QC, and do not rely on QC power being noticed until some neighbour update happens.

### dropper_qc_crafter_no_qc
**Verdict:** confirmed
**Behaviour:** Dropper (west into a barrel, 2 sticks) with a redstone block at y+2 (air at y+1): after 10 ticks unfired (triggered=false, comparator 1). A neighbour setblock sets triggered=true in the same tick and the item leaves exactly 4 gt after the update (not after the power). Comparator dust drops 2 gt after that (1 at +5, 0 at +6). A second update while still quasi-powered does not fire again (triggered stays true, 1 stick left). Control: the same update with no power above leaves it unfired. A crafter (one oak_log, orientation=west_up) in the same layout stays triggered=false and uncrafted after both a side update and a block placed on top. Powered directly by a redstone block, it sets triggered=true at once, the log is consumed at exactly +4 gt, 4 oak_planks go into the barrel, comparator falls at +6. Dispensers not tested (inferred same, shared DispenserBlock).
**Use:** Crafters can sit under power lines or in dense stacked autocrafter arrays without phantom triggers. A quasi-connected dropper takes an input powered diagonally from above and acts as a BUD firing 4 gt after any update while its above-cell is powered.

### copper_bulb_instant_toggle
**Verdict:** confirmed
**Behaviour:** A waxed copper bulb goes lit=true, powered=true in the same tick the driver is placed. On the falling edge it goes powered=false at once and stays lit. A comparator reading it drives a second bulb, which toggles exactly 2 gt later (dust after the second comparator 15 at 4 gt). Four 2 gt pulses give A lit 1,0,1,0 and B lit 1,1,0,0, so BA runs 11 -> 10 -> 01 -> 00 (counts down). A long pulse toggles once. A second source added while powered, first removed, second removed: no toggle; powered follows the sources. A waxed oxidized bulb reads 15 when lit. A repeater hard-powering a bulb does not power dust on the far side, but does once the bulb is stone, so the bulb does not conduct. Placement (setblock + clone): a bulb listed lit=false,powered=false beside a redstone block comes up lit=true,powered=true (comparator 15); listed powered=true it comes up lit=false,powered=true (comparator 0).
**Use:** Smallest T flip-flop: bulb + comparator, 2 gt latency. Chained: a 2-blocks-per-bit ripple down-counter or frequency divider, with the lit bulbs as display. Rule: a bulb that is powered at rest must be listed powered=true, or it toggles on placement and starts lit.

---

## 9. Hoppers and containers

### hopper_chain_first_hop_cooldown
**Verdict:** differs
**Behaviour:** Two 4-hopper chains (E->W and W->E), checked every tick. A lone item in an idle first hopper leaves it 1 gt later, then moves one hop every 7 gt (reaches hoppers 2, 3, 4 at +1, +8, +15), not 8. Both directions give identical timings, so there is no direction-tied first-hop offset. A first hopper holding 3 items sends them 8 gt apart (end hopper count 1, 2, 3 at +15, +23, +31). The 8 gt figure is the per-item rate out of a hopper that keeps items; a single item crossing empty hoppers takes 7 gt per hop.
**Use:** Silent, exact item delay lines: a lone item takes 7 gt per hop (plus 1 gt out of an idle source); a stream leaves 8 gt apart. A design assuming 8 gt per hop for a single item gains 1 gt per hop.

### hopper_lock_instant_accepts_input
**Verdict:** confirmed
**Behaviour:** Placing a redstone block beside a hopper makes it enabled=false in the same tick, removing it enabled=true in the same tick. With the gate hopper locked, the hopper feeding it still inserted all 5 stone and the gate kept them; the hopper after it stayed empty and it did not pull 4 dirt from the barrel above. After unlocking, all 5 stone and 4 dirt reached the next hopper within 100 gt. The gate is not quasi-powered: with a redstone block beside the space above both gate and a piston, a lock/unlock cycle leaves the piston extended but the gate enabled=true. Not tested: collecting item entities while locked, insertion by droppers or hopper minecarts.
**Use:** A zero-delay item gate for item-count registers, hopper clocks and sorters. A locked hopper does not block its feeding line: it keeps accepting items until full.

### comparator_nonstackable_item_steps
**Verdict:** confirmed
**Behaviour:** Hopper with 1-5 wooden swords: 3, 6, 9, 12, 15. Dropper with 1-9 swords: 2, 4, 5, 7, 8, 10, 11, 13, 15. Control: hopper with 1-5 single stone in separate slots: 1 each time. 16-stack items count 4x: 16 snowballs = 3 = 64 stone; 16 stone = 1. At the rounding boundary 5 snowballs = 20 stone = 22 stone = 1 and 6 snowballs = 23 = 24 stone = 2. `/item replace` into a hopper sets the slot but does not update the comparator (dust stays 0 until a neighbour update); a dropper updates normally. Use `data merge` for hopper contents.
**Use:** Item-count memories with widely spaced levels (5-state hopper memory with swords) and fixed signal strengths from a few unstackable items.

### decorated_pot_single_slot_fullness
**Verdict:** confirmed
**Behaviour:** Pot with 1, 5, 10, 32, 64 stone gives dust 1, 2, 3, 8, 15. A hopper with the same counts gives 1, 1, 1, 2, 3. A hopper above moved its 3 stone in; a hopper below pulled all 5 out of a second pot. The pot NBT stores the item under `item`, not `Items`. `/item replace` into a pot does not update the comparator (dust 0 until a neighbour update, then 15); `data merge` does. Dropper insertion not tested.
**Use:** A one-block analog store with about 4.6 items per level, filled and drained by hoppers, for precise constants.

### composter_pie_counter_ready_delay
**Verdict:** confirmed
**Behaviour:** Pumpkin pies from a hopper (7 placed at tick 20) raise the level 1 per pie, 8 gt apart: level 1 at +1, 2 at +9, ..., 7 at +49; comparator dust follows 2 gt later. Level 7 becomes 8 exactly 20 gt later (dust 8 two gt after). A hopper below a level-8 composter resets it to 0 on the next game tick and takes exactly 1 bone meal; dust 0 two gt later. Setblock level 5 holds (dust 5, 40+ gt). Setblock level 7 ripens to 8 after exactly 20 gt (placement schedules the tick). Control: the first wheat seed on an empty composter always gives level 1; 7 seeds ended below 7 (reaching 7 has ~0.07% probability).
**Use:** A deterministic 7-item counter (100% items, 8 gt apart hopper-fed) with a free exact 20 gt delay from 7 to 8. A hopper below auto-resets it to 0 with one bone meal. setblock levels 0..6 (and 8) give stable constants; 7 is not stable.

### chiseled_bookshelf_last_slot_counter
**Verdict:** differs
**Behaviour:** Output is last-interacted slot + 1, not a book count. Books fed one at a time by a hopper above step the reading 1..6; a chest with 6 books reads 1. A hopper inserts into the first empty slot: books in slots 0 and 2 (reading 3), the next book goes to slot 1 and reading becomes 2. Differs: (1) removing books does NOT step back. A hopper below drains slot 0 first, then 1, ..., one per 8 gt, and the reading climbs 1..6 while the shelf empties; an empty shelf keeps reading 6. (2) The claim that a hopper below which cannot take a book still interacts is refuted: shelf with books in slots 0 and 3, last_interacted_slot 0 (reading 1), under a hopper full of stone still reads 1 after 30 gt and both books stay.
**Use:** A 6-state item-driven step counter that advances exactly 1 per book inserted by a hopper. Draining with a hopper below also advances it 1..6 at 8 gt per book, so it is not an up/down counter. State persists in the block entity and can be preset with last_interacted_slot NBT.

---

## 10. Comparator-readable blocks and analog sources

### comparator_block_state_constants
**Verdict:** differs
**Behaviour:** Read from block state alone, directly and through a stone block: cake[bites=k] 14-2k (14..2); end_portal_frame eye=false 0, eye=true 15; beehive and bee_nest honey_level k gives k (0..5); composter level k gives k (0..7); cauldron 0; water_cauldron and powder_snow_cauldron level 1/2/3 give 1/2/3; lava_cauldron 3; respawn_anchor charges 0..4 give 0/3/7/11/15; stone 0. Subtract comparator, rear 15, side comparator reading cake bites=3 gives 7; bites=0 gives 1; stone on the side gives 15. Differs: (1) the chiseled bookshelf is not a state constant: slot_N_occupied states without block-entity data read 0; it reads last_interacted_slot+1 from NBT (slot 1 gives 2; slot 4 gives 5 though empty), from the back face (facing=north) as well as the front. (2) A bare crafter reads 0; `crafter{disabled_slots:[I;0,1,2]}` reads 3 (disabled slots count, held in NBT). (3) `creaking_heart[creaking_heart_state=awake]` with no logs becomes uprooted at once and reads 0; its creaking-distance output was not tested.
**Use:** Item-free, entity-free constants 0-15 placed exactly by setblock state: cake (even 14..2), end portal frame (0/15), beehive (0..5), composter (0..7; 8 valid, but 7 ripens to 8), cauldrons (1..3), respawn anchor (0/3/7/11/15). Cake bites=3 on a subtract side turns 15 into 7. Chiseled bookshelf (1..6) and crafter (0..9) constants need block-entity NBT in the placed state, which the build format supports.

### respawn_anchor_dispenser_charge
**Verdict:** differs
**Behaviour:** Each dispenser pulse with glowstone adds 1 charge in the Overworld: charges 1, 2, 3, 4, comparator dust 3, 7, 11, 15 (setblock charges=2 gives 7). Nothing exploded. Differs on the fifth pulse into a full anchor: the dispense fails, the anchor stays at 4 and dust 15, the glowstone stays in the dispenser (1 left of 5) and no glowstone drops. Control: a dispenser holding stone ejects it as an item; anchor stays charges=0, dust 0.
**Use:** A 4-count saturating pulse counter. Extra pulses are harmless and use no glowstone, so no overflow guard is needed. Steps of 3-4 levels decode easily.

### lectern_page_signal_and_pulse
**Verdict:** differs
**Behaviour:** Formula confirmed: output = floor(14*page/(pages-1)) + 1. A 15-page writable book, pages 0..14 set by /data, gives dust exactly 1..15. A 10-page book gives 8 at page 5, 2 at page 1, 13 at page 8. A 1-page book gives 15; an empty lectern gives 0. A lectern set to powered=true strongly powers the block below (dust beside that stone 15; 0 when powered=false again). Differs: changing Page with /data merge sends no pulse: powered stays false at +0, +1, +2 and the dust under it stays 0, although the comparator updates. The 2 gt page-turn pulse itself was not measured (only a player fires it).
**Use:** A 15-state selector (signal = page+1, exact with a 15-page book) set by command or by a player. The strong power below needs a real player page turn to act as a value-changed strobe; a command-set selector needs its own latch trigger.

### jukebox_disc_timer_and_id
**Verdict:** confirmed
**Behaviour:** music_disc_11 inserted by a hopper above at tick 21 makes adjacent dust read 15 from tick 21 to 1461 (1441 gt: the song's 1420 gt plus about 20); 0 at 1462. While it plays, the hopper below is enabled=false (locked). It pulls the disc right after the song ends: by tick 1465 has_record=false, comparator 0, disc in the lower hopper. Comparator by disc: 11 gives 11, 13 gives 1, 5 gives 15. Controls: no disc gives dust 0 and hopper enabled=true. A disc set straight into the jukebox with /data RecordItem does not play (dust 0), and the unlocked hopper pulls it within 10 gt.
**Use:** A clockless one-shot timer that resets itself (disc 11: 1441 gt of 15, then the disc is ejected) and a 1-slot ROM keyed by disc type. Insert the disc by hopper or dispenser; a disc placed by /data will not start.

### item_frame_rotation_through_block
**Verdict:** differs
**Behaviour:** A north-facing item frame on the far (north) face of the stone behind a north-facing comparator reads ItemRotation+1: rotations 0..7 give dust 1..8, empty frame 0. A frame sharing a cell with a chest (4 stacks, reads 3) gives the max: rotation 0 (1) gives 3, rotation 6 (7) gives 7, rotation 1 (2) gives 3. Controls reading 0: a frame on a side (east) face of the stone; a frame on glass instead of stone; a frame directly in the comparator's input cell (no block between). That last case refutes "directly behind it": frames are read only through a solid block. Also differs: changing ItemRotation or removing the item by data merge/remove does NOT update the comparator (stale 3 for 20 gt after setting rotation 6; showed 7 only after a block update beside the comparator). A real player rotation could not be tested. NBT keys ItemRotation (byte) and Facing (2b north, 5b east) unchanged.
**Use:** An 8-position player dial or constant 1-8 (0 when empty) on a solid wall block with the comparator hidden behind it. Can share a cell with a container and take the max. Command/NBT-set rotation needs a neighbouring block update before the comparator shows it. Uses an entity (not entityless).

### copper_golem_statue_pose_selector
**Verdict:** confirmed
**Behaviour:** `waxed_copper_golem_statue` placed by setblock keeps its copper_golem_pose. A comparator reads standing 1, sitting 2, running 3, star 4, directly and through a stone block. Facing does not matter (star facing east 4, sitting facing south 2). Replacing it with stone gives 0. A piston pushing it destroys it: the head takes the cell, dust goes to 0 and a `waxed_copper_golem_statue` item drops. Not tested: cycling the pose by player use, slime/honey non-stickiness.
**Use:** An entityless 4-state constant or selector (1-4) placed exactly by setblock state, independent of facing. A piston push is a one-shot destructive reset that drops the statue item. Use the waxed variant so oxidation cannot change it.

### shelf_slot_bitmask_comparator
**Verdict:** confirmed
**Behaviour:** `oak_shelf[facing=north]`. A comparator behind it (south side, facing=north) reads container.0 as 1, container.1 as 2, container.2 as 4; all 8 subsets give exact 0-7. 64 items in a slot count the same as 1. Comparators at the front and side read 0 while the back reads 7. A piston cannot push it (stays unextended; extends once the shelf is replaced by stone). A hopper above fills slot 0 to 64 before slot 1: after 64 items the reading is 1, the 65th makes it 3; from 64+63, the next item finishes slot 1 and the one after goes to slot 2, so the 129th item gives 7. A hopper below takes container.0 first. Not verified: which slot index is visually left, middle or right. Dropper insertion not tested.
**Use:** A one-block 3-bit constant or ROM cell, item shown on the front, readout hidden behind the wall. Hopper-fed it is a stack-count threshold: 1-64 items read 1, 65-128 read 3, 129+ read 7.

### crafter_slot_count_comparator
**Verdict:** confirmed
**Behaviour:** The comparator counts slots that are filled or disabled. `disabled_slots [I;0,1,2]` (via data merge) reads 3; `[I;1..8]` reads 8, and one stick in slot 0 makes it 9. One stack of 64 sticks reads 1 (a dropper with 64 reads 2). A hopper above holding 5 sticks fills slots 0..4 in reading order, one per 8 gt: item k arrives at tick 1+8(k-1) after placing, dust shows k 2 gt later. With 11 items all 9 slots fill, then slots 0 and 1 are topped up to 2 (smallest stack, reading order), still reading 9. A hopper below pulls one item per 8 gt: 3 -> 2 -> 1 -> 0. Control: a dropper fed 5 sticks reads 1.
**Use:** An exact 0-9 up/down counter in one block (up from a hopper above, down from one below; 8 gt per step plus 2 gt comparator). With disabled_slots it is a 1-9 constant source with no items. In a self-triggering autocrafter with unused slots disabled, the comparator reaches 9 when the recipe is complete.

### inverted_daylight_detector_constant
**Verdict:** differs
**Behaviour:** Refuted: a roof (one opaque block above) is not enough. The detector reads sky light at its own cell and open sides still give 14. Roofed inverted: noon 1, midnight 12. Roofed normal: noon 14, midnight 0. Unroofed inverted at noon: 0. Only a detector enclosed on all four sides plus the top outputs a constant 15 when inverted, day and night. Timing claim confirmed: a detector set to power=7 by setblock (enclosed, non-inverted, computed value 0) holds 7 every tick until the first tick whose game time is a multiple of 20, then drops to 0 (checked tick by tick against gametime mod 20). Right-click toggling not tested.
**Use:** A slab-height constant-15 source only when fully enclosed and inverted. A roofed-only detector is a day/night sensor. It recomputes on game time mod 20, giving a 20 gt divider aligned to game time; a power written by setblock lasts until that boundary.

---

## 11. Sculk and vibrations

### wool_occludes_and_dampens_vibrations
**Verdict:** confirmed
**Behaviour:** A white_wool block on the line between a note block and a sculk sensor 4 blocks away blocks the vibration (sensor inactive, last_vibration_frequency 0). Stone there: sensor active at power 8 four ticks later, frequency 10 (note_block_play). Carpet on the line does NOT block it (power 8, frequency 10); white_carpet is not in `#occludes_vibration_signals` (that tag is only `#wool`), while `#dampens_vibrations` is `#wool`, `#wool_carpets`, `#wool_slabs`, `#wool_stairs`. Breaking wool or carpet with `setblock ... destroy` 3 blocks away makes no vibration; breaking stone is block_destroy, frequency 12, active within 3 ticks.
**Use:** Full wool blocks isolate neighbouring sculk transmitter/receiver pairs. Carpet, wool slabs and stairs do not isolate; they only silence events that happen to them (placing, breaking, stepping), so carpet walkways hide footsteps.

### sculk_note_block_frequency_link
**Verdict:** confirmed
**Behaviour:** Plain sculk sensor, note block 5 blocks away (redstone-block driven): active exactly 5 ticks after the drive (inactive at +4), power 6, comparator 10 two ticks later (+7). Active for 30 ticks (+5..+34), cooldown exactly 10 ticks (+35..+44), inactive at +45. Re-playing the note block while active (+10) or in cooldown (+38, arriving +43): both vibrations dropped, no retrigger. An oak trapdoor 4 away opening fires it at +4, power 8, comparator 10; closing (after cooldown) fires at +4, comparator 9. A note block at 8 blocks is heard at +8 with power 1; at 9 blocks it is not heard in 30 ticks. Lever/button activation frequencies (10/9 claimed) and hand-clicking a note block were not tested.
**Use:** Wireless link through walls up to 8 blocks at 1 tick per block. The receiver's comparator gives 10 on open and 9 on close, so it detects both edges. A plain sensor handles at most one edge per 40 ticks (30 active + 10 cooldown); vibrations arriving in that time are lost. A calibrated sensor allows one per 20 ticks.

### calibrated_sculk_frequency_filter
**Verdict:** confirmed
**Behaviour:** The calibrated sensor is tuned by dust on its back (side opposite facing). Tuning 0 (untuned) hears everything: note block 5 away at +5 (power 11, comparator 10), trapdoor 3 away opening (power 13, comparator 10) and closing (comparator 9). Active exactly 10 ticks, then cooldown exactly 10 ticks. The tuning dust stays 0 while the sensor outputs 11 on another side, so the input side gets no output. Tuned to 10: hears note block and trapdoor opening, ignores closing. Tuned to 9: ignores note block and opening (inactive after 30 ticks each), hears closing (comparator 9). Range: note block 16 away heard at +16 with power 1; 17 away not heard.
**Use:** Frequency-addressed wireless channels: note block, lever or door = 10, closing = 9; other frequencies such as footsteps are ignored. The input side emits nothing, so the tuning line needs no diode.

### sculk_output_strength_by_distance
**Verdict:** confirmed
**Behaviour:** Plain sensor, note blocks at axis distances 1, 4, 7 give power 14, 8, 2, each arriving exactly d ticks after the drive. Matches max(1, 15 - floor(15d/8)). Also measured 6 at d=5, 8 at d=4 (trapdoor), 1 at d=8. Dust beside the sensor reads the full strength. The stone under the sensor is strongly powered: dust next to that stone reads the same strength and a repeater facing away turns on. A stone beside the sensor gets no power (dust on its far side 0, repeater behind stays off). Calibrated formula 15 - floor(15d/16), min 1: 13 at d=3, 11 at d=5, 3 at d=13, 1 at d=16. In the amethyst spec the calibrated sensor reads 3 at 13 blocks from the amethyst (sensor is 14 away), placing the relayed vibration's source at the amethyst block.
**Use:** Wireless rangefinder or near/far selector: one receiver plus a comparator threshold on its direct output. A sensor on a block drives a repeater or dust beside that block with no dust of its own; it does not power a block placed beside the sensor.

### amethyst_resonance_relay
**Verdict:** confirmed
**Behaviour:** A note block 4 blocks from plain sensor A, which has an amethyst block beside it. Calibrated sensor B (tuned 10) sits 13 blocks past the amethyst, 18 from the note block (cannot hear it directly). A fires at +4; B fires exactly 13 ticks later (+17, inactive at +16) with power 3 and comparator 10. B tuned to 9 ignores the relay. Trapdoor close near A (frequency 9): A fires at +3, B (tuned 9) fires 13 ticks later with comparator 9, so the frequency is preserved. Control: stone replacing the amethyst (setblock) leaves A firing but B inactive, comparator 0.
**Use:** Multi-hop wireless beyond 8/16 blocks that keeps the frequency: one sensor plus one amethyst per hop, no redstone between hops. 1 tick per block, no extra delay per hop (the amethyst re-emits in the same tick the sensor activates).

### sculk_detects_ice_melt
**Verdict:** confirmed
**Behaviour:** Ice with a glowstone beside it (block light 14) and random_tick_speed 4096 for 20 ticks becomes a water source (water[level=0]); a sensor 4 blocks away records frequency 12 (block_destroy). Controls: ice in daylight with no block light never melts (only the BLOCK light layer counts); packed ice beside glowstone never melts; in both the sensor stays 0, which also shows that placing the glowstone by command makes no vibration. Melt time is random and was not measured. That melting was silent before 26.3 cannot be tested here.
**Use:** Mainly a hazard: ice or snow within 8 blocks of a sensor and next to a light above 11 can trigger it with frequency 12 (same as block breaking). Daylight alone is safe. Could serve as a slow random block-light detector.

---

## 12. Entity inputs and projectiles

### weighted_plate_entity_count
**Verdict:** confirmed
**Behaviour:** Gold plate: 1 non-merging item gives 1, 5 give 5, 15 give 15, 20 still 15 (dust beside reads N, next dust N-1). A 64-stack in one item entity counts as 1. Iron plate: 1 item gives 1, 10 give 1, 11 give 2, 21 give 3 (ceil(N/10)). The plate presses the tick the first entity lands (tick 21), then recounts every 10 gt (31, 41, 51...). Entities added between rechecks are not counted until the next (1 -> 5 showed at +11 gt). Killing items turns the plate off at the next recheck: after 1 gt if killed 1 gt before, after exactly 10 gt if just after. Five identical items with default PickupDelay read 5, then 1 after 62 gt once merged into one count-5 stack; with PickupDelay 32767 they still read 5 after 62 gt.
**Use:** An analog entity counter with no comparator: gold reads N up to 15, iron reads ceil(N/10) up to 150. Reads in 10 gt steps, so input settles up to 10 gt late and release takes 1-10 gt. Items count separately only if they cannot merge (different items or PickupDelay 32767).

### arrow_holds_wooden_button
**Verdict:** confirmed
**Behaviour:** Dispensers facing down one block above floor buttons. The oak button presses 5 gt after the dispenser input (4 gt dispenser delay plus arrow fall), dust beside it 15, still pressed 300 gt later with the arrow stuck (inGround). The stone button, with its own arrow confirmed stuck in its cell, never pressed (dust 0). After the arrow is killed, the oak button releases at its next 30 gt recheck counted from the press (press tick 25, rechecks 55, 85...; killed at 30, released exactly at 55). A control click with no arrow releases after 30 gt. Tridents, wooden plates and the 1200 gt arrow despawn not tested.
**Use:** A projectile-set hold input in one block: stays on while the arrow exists, releases 1-30 gt after it is removed. Only wooden buttons respond; stone buttons ignore projectiles.

### target_block_accuracy_strength
**Verdict:** confirmed
**Behaviour:** Projectiles falling onto the target's top face. Strength = max(1, ceil(15*(0.5-d)/0.5)) with d the offset from face centre: d=0 gives 15, 0.15 gives 11, 0.25 gives 8, 0.3 gives 6, 0.4 gives 3, 0.45 gives 2, 0.49 gives 1 (d=0.1 not 12, a float-rounding boundary, left out of the spec). A snowball powers the target from the tick after landing for exactly 8 gt. An arrow powers it exactly 20 gt then turns it off though the arrow stays stuck 40+ gt more. Adjacent dust reads the same strength and connects into the target (west=side, east=side); beside plain stone it stays a dot. A snowball on stone gives dust 0. A dispenser shooting down from one block up hits 14 or 15 from run to run (random spread).
**Use:** A wireless analog pulse input. Strength is set by where the projectile lands: a fixed summon position gives an exact value, a dispenser 14-15 at centre. The ammo sets pulse length: 8 gt for snowballs and other projectiles, 20 gt for arrows. Unlike a wooden button, it does not hold while an arrow stays stuck.

### armor_stand_presses_stone_plate
**Verdict:** confirmed
**Behaviour:** A summoned armor stand presses a stone plate within 1 gt (adjacent dust 15). A Marker:1b stand leaves it at 0. An item leaves a stone plate at 0 but powers an oak plate to 15. The stone plate rechecks every 20 gt from the press (press at 21, rechecks 41, 61): killing the stand 1 gt before a recheck turns it off after 1 gt; just after one, it stays on 19 gt and goes off at 20. A piston at y+1 pushing its head through the stand's upper body moves the stand one full block, to the next cell's centre (within 0.3); the plate releases at the next recheck, 21 gt after the piston input in this phase.
**Use:** A summonable, killable, piston-pushable weight for stone or oak plates: a harness driver or remote plate actuator. Release takes 1-20 gt. Marker stands are ignored; items work only on wooden plates.

### lightning_rod_strike_pulse
**Verdict:** confirmed
**Behaviour:** A lightning_bolt summoned at the top of `lightning_rod[facing=up]` (strike position inside the rod) powers the rod from the next tick for exactly 8 gt, off at +9. The stone under the rod is hard-powered: dust beside it 15, a repeater reading the stone turns on 2 gt later, and the dust after the repeater goes 15 -> 0 two ticks after the rod turns off. A control bolt on bare stone powered nothing. A plain (non-waxed) rod worked. Fire and gamerules not changed or tested.
**Use:** A wireless trigger from lightning, natural or channeling trident: a tick-exact 8 gt pulse that hard-powers the block it sits on, driving dust or a repeater directly with no comparator or observer.

### wind_charge_toggles_unpowered_only
**Verdict:** confirmed
**Behaviour:** A wind_charge falling onto the floor beside a floor lever flips it on (dust 15); a second flips it off (dust 0). One burst centred between four trapdoors (each one block away): the closed unpowered oak trapdoor opened; the open unpowered oak trapdoor closed; the open oak trapdoor held by an adjacent redstone block (powered=true) stayed open; the iron trapdoor stayed closed. The charge is gone after the hit. Buttons, doors, fence gates, bells, candles, dispenser-fired charges and mob griefing not tested.
**Use:** A wireless one-shot toggle: each burst flips a lever, so a charge source makes a T flip-flop, and one burst can flip several blocks nearby. Trapdoors held by a redstone signal and iron trapdoors ignore it, so powered trapdoors work as wind-proof latches.

---

## 13. Tripwire and falling blocks

### tripwire_shears_disarm_silent
**Verdict:** confirmed
**Behaviour:** Hooks 41 blocks apart (40 strings) attach at build; hooks 42 apart (41 strings) stay attached=false. An item summoned on string 28 of the 40 powers both hooks on the next tick and dust beside the east hook's attachment block reads 15 (strongly powered). Removing a middle string with setblock air (not disarmed) powers both hooks (dust 15) for exactly 10 gt, then both are attached=false and powered=false. Setting that string to disarmed=true first (hooks stay attached and unpowered), then setblock air, detaches both hooks at once with no pulse (dust 0 for the next 12 ticks). Disarm was done by setblock, testing the block-state path, not playerWillDestroy. The checker rejected the "silent" trait (hooks make sounds).
**Use:** A 1-wide entity sensor up to 40 strings long whose hooks strongly power their blocks (drive dust directly). Breaking a string without disarming gives one 10 gt pulse, then the line is dead; a disarmed string can be removed with no signal, so a build can tell broken from sheared.

### tripwire_fast_entity_path_trigger
**Verdict:** confirmed
**Behaviour:** Floating string at y+9, an item summoned at y+15 with Motion [0,-3.5,0]. End of tick 1: item between y+10 and y+14, hook unpowered. End of tick 2: between y+7 and y+8, so no tick ended inside the string, yet the hook is powered and dust on its attachment block reads 15. It stays powered through tick 11 and is off at tick 12 (10 gt pulse). Control: the same fast item one block beside the line never trips it and lands. Control: a slow item dropped from y+9.5 powers the hook at tick 4, the first tick ending inside the string. Pressure plate under a fast arrow not tested.
**Use:** One floating string detects items or entities passing at several blocks per tick (for example at the bottom of a tall drop chute). It trips on the tick of the crossing and gives a 10 gt pulse with no slowdown blocks.

### tripwire_retrigger_and_chunk_order
**Verdict:** differs
**Behaviour:** Timing on 26.3, all exact. (1) An item present one tick then killed gives exactly 10 gt: hook on from the tick after the summon for 10 ticks, dust 15 then 0. (2) The tripwire re-checks every 10 gt from the press, so an item staying 15 ticks gives a 20 gt pulse. (3) An item summoned right after the off tick powers the string the next tick: minimum off gap 1 gt. (4) Repower guard: an item entering the string during the depower tick (summoned 0.3 above with Motion -0.3, checked inside the string at the end of that tick) does not repower it that tick; the hook stays off one tick and repowers the next. Control: same entry on an idle string powers on the same tick. So the 1-tick repower guard from the 26.2 change exists in 26.3. The cross-chunk scheduled-tick order part (MC-310372) was not tested; the piston race across a chunk border was not built.
**Use:** Exact tripwire timing: pulses are 10 gt, extended in 10 gt steps while an entity stays; minimum off gap 1 gt; an entity arriving on the off tick is deferred one tick. Not known whether string must sit in its own chunk.

### tripwire_blocks_fluid_flow
**Verdict:** refuted
**Behaviour:** Myth: string stops fluid flow. Reality: it does not. Water beside a string on stone: string still tripwire at tick 4; at tick 5 (water's first flow tick) the cell is water[level=1] and a string item has dropped; water reaches level=2 by tick 10. Lava replaces the string on its first flow tick (tripwire at tick 25, lava[level=2] at tick 30, lava[level=4] one cell on by tick 60). Control lanes without string flow at the same pace, so string causes no delay.
**Use:** None as a fluid stopper: flowing water or lava destroys string (water drops it as an item). Keep string out of flush or item-stream channels. Inferred, not tested: water destroying an attached string might give a hook pulse and so detect arriving water.

### falling_block_update_and_break
**Verdict:** differs
**Behaviour:** A plain `setblock sand` over air does not float: still sand 1 tick later, air at 2 gt with a falling_block entity, and it lands as a sand block with no sand item nearby. Only `setblock ... strict` leaves sand floating (still there after 40 gt). A 1-block `clone ... replace force` onto itself makes it fall 2 gt later (sand at +1, air at +2), and so does a setblock of stone beside it. Clone onto itself without `force` is rejected (overlap). Sand falling onto a standing torch leaves the torch, puts no block above it and drops one sand item; same on a bottom smooth-stone slab (the air control lane gets a sand block). Rail not tested. Harness caveat: a gravity block in `layers` over air falls during load and is gone by the end of settle; a sand item was also present at tick 0.
**Use:** Sand falls on any placement or neighbour update, 2 gt later, so floating sand is a power-free BUD, but only if placed without an update (setblock strict, or naturally generated). A torch or bottom slab under a sand column turns falling blocks into items to feed a hopper line. Library builds cannot contain unsupported gravity blocks because the harness load makes them fall.

---

## 14. Rails and minecarts

### powered_rail_chain_limit_isolation
**Verdict:** confirmed
**Behaviour:** 11 `powered_rail[shape=east_west]` on stone, a redstone block west of rail 0. Rails 0-8 read powered=true in the same tick the source is placed (no wait, zero delay); rails 9 and 10 stay false. A parallel powered-rail row directly south stays all false. A dust beside rail 1 reads 0 and a lamp beside rail 2 stays unlit: powered rails give nothing to dust or blocks. Turning rail 3 into an activator rail leaves it powered=false though the powered rail beside it is powered, and rails 4-10 stay unpowered: the two types do not pass power to each other. An observer facing rail 5 gives a 2 gt pulse starting 2 gt after the source is placed. Removing the source turns every rail off at once. The clone pass kept explicit rail shapes. Slopes not tested.
**Use:** A 1-wide wire that lights 9 rails with zero delay and powers nothing beside it, so lines can run side by side with no spacing. Read it with an observer (2 gt pulse 2 gt after a change). An activator rail breaks the line into separate segments.

### detector_rail_reads_cart_container
**Verdict:** confirmed
**Behaviour:** Detector rail on stone, comparator[facing=west] behind it driving dust. A chest_minecart with 27x64 stone gives 15 (rail powers 1 gt after summon, comparator 15 two gt later); with 1 item gives 1. A hopper_minecart with one stack of 64 gives 3 (container formula over 5 slots). A command_block_minecart with SuccessCount:7 gives 7. A plain minecart powers the rail (powered=true; the support block is strongly powered, dust beside it 15) but the comparator reads 0. An armor stand never triggers the rail. After the cart is killed the rail stays powered and switches off exactly 20 gt after it first powered (on at 18 gt after the kill, off at 19).
**Use:** A chest minecart is a movable 0-15 memory: store the value as an item count and read it anywhere with one comparator behind a detector rail. A command block cart supplies SuccessCount directly. The rail's 20 gt re-check holds the signal after the cart leaves, usable as a slow timer.

### hopper_minecart_through_floor_and_lock
**Verdict:** confirmed
**Behaviour:** A hopper_minecart on a rail with stone directly above collected a 10-stone item entity lying on that stone within 5 gt; a hopper block under the same stone collected nothing in 45 gt. Under a chest of 20 stone, the cart took 5 items by 5 gt, 6 by 6 gt, all 20 by 40 gt (1 item per gt); a hopper under an identical chest took 5 in 40 gt (1 per 8 gt). An item entity is taken as a whole stack in one pickup. A cart on a powered activator rail reads Enabled:0b and takes nothing from the chest above. Teleported onto a plain rail under another chest it stays Enabled:0b and takes nothing for 20 gt. Brought back with the activator rail now unpowered, it reads Enabled:1b within 2 gt and empties the chest within 20 gt.
**Use:** Hidden item pickup under a solid floor that can still carry dust. Unloads 8x faster than a hopper, suiting fast item-count timers and counters. An activator rail locks it, and the lock persists until the cart crosses an unpowered activator rail.

### powered_rail_park_and_launch
**Verdict:** confirmed
**Behaviour:** Stone wall at x0, powered rail at x1, plain rails x2..x11. A minecart summoned on the unpowered powered rail stays exactly at the x1 centre for 20 gt. After the rail is powered (redstone block beside it), 20 gt later the cart is at x = 5.35-5.39 (block-0 centre + 4.85-4.89), moving away from the wall. With the wall removed, powering the rail leaves the cart where it was. A cart rolling west at 0.4 b/t stops inside the cell of an unpowered powered rail at x3; on plain rail it rolls on to the wall end at x1.
**Use:** A cart station: an unpowered powered rail catches and holds a cart and its cargo. Powering it sends the cart off away from the solid block at the rail's end, with no dispenser or player. Without that block, powering does nothing.

---

## 15. Environmental and 26.x

### potent_sulfur_geyser_clock
**Verdict:** differs
**Behaviour:** State property `potent_sulfur_state` (dry, wet, dormant, erupting, continuous). With 4 water sources above magma: eruption lasts 80-100 gt (4-5 s); dormant countdown reads 44..59 one ticker run after the eruption ends, so 900-1200 gt (45-60 s) between eruptions. The same value returns after a second forced cycle, so timing repeats per block. With 1 water source: eruptions 20-40 gt, dormant countdown 12..29 (about 300-600 gt). A sensor 3 blocks away: frequency 10 (block_activate) at the start, 9 (block_deactivate) at the end. Magma replaced by stone gives state wet: never erupts in 1300 gt, sensor 0. Lava below gives state continuous, one activate (frequency 10), and an item above the column rises past +3 blocks within 20 gt; a dormant geyser leaves it below. From bytecode (not measured): the ticker runs only when gametime % 20 == 0; dormant lasts (10(w-1)+r1)*20 gt, erupting ((w-1)+r2)*20 gt, r1 in 15..30, r2 in 1..2, from seed ^ salt at the block position (repeatable per position and world seed); needs air above the top water block, 5 or more water blocks stops it; the push zone reaches up to 6 blocks per water block (claim said about 7; push height not measured). Differs: the claimed ~50 s / 4-5 s is only the 4-water case; period and eruption length scale with water depth.
**Use:** A redstone-free slow clock: a plain sculk sensor gets frequency 10 at each start and 9 at each end. Period is set by water depth (about 15-30 s for 1 water up to 45-60 s for 4), fixed per block and seed, phase quantised to 20 gt. The lava version is a continuous item/entity elevator.

### tnt_explodes_false_vanishes
**Verdict:** refuted
**Behaviour:** Myth: with the `tnt_explodes` gamerule false, powered TNT vanishes. Reality: it stays `tnt[unstable=false]`, with no tnt entity and no prime_fuse vibration (sensor 0), because prime() returns false and removeBlock is skipped (bytecode). Control with the rule true: one tick after driving the block is air, a TNT entity has fuse 79, sensor reads 10. TNT primed with the rule true and then switched to false counts down and vanishes at exactly 80 ticks without exploding (floor intact, sensor never records 15). TNT minecart on a powered activator rail: rule false leaves fuse -1; rule true gives fuse 78 two ticks later. A burning minecart (in_fire damage) still gets a 0..38 tick fuse under rule false (destroy() sets it) and disappears without exploding.
**Use:** Harness technique: fire with the rule true and check for air plus a TNT entity at fuse 79, then flip the rule false (or kill) before 80 ticks; or check the TNT block is still there with the rule false. Flipping the rule false after priming lets real primed TNT and minecarts run out harmlessly. Rails cannot light minecarts under the false rule; fire still starts the countdown.

### sulfur_cube_tnt_priming
**Verdict:** differs
**Behaviour:** A cube summoned with body-equipment TNT has fuse -1 unprimed. A redstone block beside the block containing its feet primes it with fuse 118..120, counting down 1 per tick. A redstone block one block further away does nothing. A Size 3 cube primes from a redstone block under its feet. A small cube on a comparator that outputs (reading a cake) primes; the same comparator with no output does not. A TNT cube on a stone pressure plate primes itself from the plate its own weight presses. A cube holding stone keeps the plate powered for 200 ticks and does not move. Damage: 100 player_attack is applied (the damage command succeeds) but leaves Health unchanged (kills a cube with no block); fire damage primes at exactly 120 while the damage command fails ("Target is invulnerable": hurt returns false); explosion damage primes at 15..44. With `tnt_explodes` false, redstone cannot prime it. Bytecode: the check is getBestOwnOrNeighbourSignal(BlockPos.containing(position())), the feet block; the comparator case is deliberate code. A Size 3 cube's top sits between 2.8 and 2.99 blocks up, so its centre is in the feet block while resting; centre and feet differ only for a falling or bouncing cube. Priming is the same for Size 0 and 3. Differs from the claim in the feet-block detail (feet, not hitbox centre).
**Use:** A movable, blast-proof charge. Push it so its feet block is next to a signal or onto an outputting component and it fires with a fixed 120 tick fuse (blasts give a random 15-44). It cannot rest on a stone plate as a weight while holding TNT (it primes itself); a cube holding a non-explosive block such as stone is a permanent plate weight.

---

## Build ideas

Combinations below are assembled from the entries above. An idea marked "untested" has not been run as a whole; only its parts are proven.

1. **End-of-line redirect with a lightning rod.** An unpowered lightning rod beside a dust line's last dust turns it sideways so it no longer powers the block ahead, without becoming powered. Relies on: dust_redirect_by_signal_sources. Untested as a shipped component.
2. **Zero-tick vertical diode.** A glass, top-slab or upside-down-stairs step in a rising dust line blocks backflow at 1 strength loss; a spiral gives an upward-only riser. Relies on: dust_transparent_step_one_way, dust_diagonal_step_powers_step_block (transparent step also avoids firing neighbours). Untested as a spiral.
3. **Piston-driven diagonal wire switch.** A sticky piston pushes a stone into a diagonal's corner to cut it (3 gt on, reconnects within 1 gt on release); non-destructive and needs no repeater. Relies on: dust_diagonal_cut_needs_conductor, redstone_block_corner_feeds_diagonal (keep drivers out of the corner).
4. **Two-repeater torchless latch, no lock-path padding.** Two repeaters locking each other; nothing else beside them can lock them, and a repeater-driven lock landing on the data repeater's output tick still wins. Relies on: repeater_lock_only_by_diodes, diode_side_input_tick_priority, repeater_lock_discards_pending_tick (data arriving within 2*delay before the lock is ignored; size the sample window accordingly). Untested as a full latch.
5. **Glitch-rejecting sampled register.** Use the lock's discard-pending behaviour as a sample window, and a comparator (which drops 1 gt pulses) or lamp stage (4 gt tail) as extra glitch filters. Relies on: repeater_lock_discards_pending_tick, repeater_extends_short_pulses, lamp_off_delay_4_ticks. Untested.
6. **Smallest T flip-flop and ripple counter.** Copper bulb + comparator per bit, 2 gt latency, lit bulbs as display; list powered-at-rest bulbs powered=true. Relies on: copper_bulb_instant_toggle, observer_dual_edge_powered_state (dual-edge input from a lever via trapdoor + observer). The observer front end is untested with the bulb.
7. **One-piston T flip-flop with a position bit.** Sticky piston with 1-2 gt pulses toggling a redstone block between +1 and +2, the block's position selecting one of two lines; pulse extender ahead of it via a repeater's 2*delay rule, and a 3 gt+ pulse acts differently (discriminator). Relies on: sticky_piston_short_pulse_drops_block, repeater_extends_short_pulses, piston_ignores_power_from_face (park the block against the face). Untested as a toggle chain.
8. **Fast falling-edge bus.** A zigzag of sticky pistons with redstone blocks turns off in 1 gt regardless of length (rising 3 gt per stage), then a 1 gt pulse to a sticky piston moves the block in 2 gt for the fast rising edge of a single hop. Relies on: piston_redstone_block_chain_instant_off, piston_one_tick_instant_transport. Combining the two into a low-latency asymmetric line is untested.
9. **Clockless piston sequencer.** Each stage is a piston-moved observer whose "arrived" pulse (2 gt, 2 gt after landing) fires the next piston; a repeater or the 2 gt minimum pulse keeps the pistons above the 1 gt filter, and moves faster than 2 gt after landing lose the pulse. Relies on: moved_observer_pulses, piston_same_tick_pulse_ignored, piston_one_tick_instant_transport. Untested as a multi-stage sequencer.
10. **Compact bus with slime/honey partition.** Glazed terracotta or honey between two slime structures avoids an air gap in flying doors and sequencers; a working component (hopper, barrel, crafter) serves as the piston stop. Relies on: piston_glazed_terracotta_slime_barrier, piston_block_entity_stoppers. Untested as a door.
11. **Analog strength bus through walls with an override.** Pass 1-14 strength through a block with a comparator, keep a container behind it as a reading source, and force 15 with a repeater when wanted; a hidden dust-past-comparator-side input must be avoided. Relies on: comparator_through_block_keeps_dust_level, comparator_container_masks_weak_block_power, dust_redirect_by_signal_sources, comparator_compare_is_ge. Untested as a bus.
12. **Item-fed 0-9 up/down counter with hardware delay.** A crafter with disabled slots as preset, hopper above to count up, hopper below to count down, both gated by hoppers that accept input while locked; comparator gives the value 2 gt later. For a delay line use single items at 7 gt per hop. Relies on: crafter_slot_count_comparator, hopper_lock_instant_accepts_input, hopper_chain_first_hop_cooldown. Untested as a locked up/down pair.
13. **Self-resetting one-shot timers.** Jukebox with disc 11 (1441 gt of 15), composter fed by hopper (20 gt free delay from 7 to 8, hopper below resets it), or a torch on a fast clock (8 pulses then 160 gt lockout). Relies on: jukebox_disc_timer_and_id, composter_pie_counter_ready_delay, torch_burnout_one_shot.
14. **Constant-source library without redstone blocks.** Exact 0-15 constants as setblock states: cake, end portal frame, beehive, composter, cauldron, respawn anchor, waxed golem statue, shelf bitmask, item frame, crafter disabled slots, decorated pot. Feed a subtract comparator side with cake for fixed offsets. Relies on: comparator_block_state_constants, copper_golem_statue_pose_selector, shelf_slot_bitmask_comparator, item_frame_rotation_through_block, decorated_pot_single_slot_fullness, comparator_compare_is_ge.
15. **Wireless channelled link with amethyst hops.** Calibrated sensor tuned by dust (10 for open/note block, 9 for close) with an amethyst relay per 13-16 blocks, wool blocks to isolate neighbouring links, a wax-and-stone environment for stable operation, plain sensors only when 40-tick dead time is acceptable. Relies on: calibrated_sculk_frequency_filter, amethyst_resonance_relay, wool_occludes_and_dampens_vibrations, sculk_note_block_frequency_link, sculk_output_strength_by_distance (rangefinder threshold). Untested as a multi-link network.
16. **Wireless projectile / lightning inputs.** Target block for analog pulses (8 gt snowball, 20 gt arrow, strength by hit offset), lightning rod for an 8 gt pulse that hard-powers the block beneath, wooden button as an arrow-held input, wind charge as a lever toggle. Relies on: target_block_accuracy_strength, lightning_rod_strike_pulse, arrow_holds_wooden_button, wind_charge_toggles_unpowered_only. Untested as a combined input panel.
17. **Movable memory cell.** A chest minecart holding N items read through a detector rail by a comparator (0-15), with an activator rail to lock a hopper minecart that unloads 1 item per gt under a floor; a powered rail station parks and launches the cart. Relies on: detector_rail_reads_cart_container, hopper_minecart_through_floor_and_lock, powered_rail_park_and_launch. Untested as a shuttle.
18. **Item-count threshold detector.** Oak shelf (1-64 -> 1, 65-128 -> 3, 129+ -> 7) or decorated pot (about 4.6 items per level) behind a hidden comparator, filled by hopper. Relies on: shelf_slot_bitmask_comparator, decorated_pot_single_slot_fullness, comparator_nonstackable_item_steps (swords for widely spaced levels).
19. **Power-free BUD and phantom-safe autocrafter arrays.** Floating sand (placed with setblock strict) falls 2 gt after any update; a quasi-connected dropper fires 4 gt after any update; crafters in the same array ignore QC, so they can sit under power lines. Relies on: falling_block_update_and_break, dropper_qc_crafter_no_qc, piston_quasi_connectivity_bud. Untested as a mixed array.
20. **Dust-only hopper-lock and tap rows.** A dust line laid on a row of hoppers locks all of them; dot dust taps one block below; glass or top slabs under the dust keep neighbouring lamps and pistons off. Relies on: dust_powers_block_below, dust_dot_vs_cross_isolated, hopper_lock_instant_accepts_input. Untested as a bus.
21. **In-tick slot-piston chain for fast doors.** A held pull clears a slot cell; the blocked slot piston behind it, already powered, extends in the same tick. A BUD piston woken by it then moves its observer or redstone block, so it 0-tick pulls the next block 2 cells in. That block's vacated cell wakes the next slot piston, all in one tick. Closing uses spits, and spat pistons fire in the same tick. Relies on: pull_origin_air_at_event, piston_zero_tick_chain_same_tick, piston_moved_source_zero_tick_depower, spat_piston_fires_same_tick, piston_landed_powered_extends_next_tick (moved pistons must land unpowered), piston_qc_shared_side_input (update order in stacked columns). Untested as a door.
