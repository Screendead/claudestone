# Lessons from videos

What we learned from the redstone videos Jack has sent, one section per video, and what each lesson means for
this repo. Labels: [S] sourced from the video page or a download; [M] measured by us, by running or scanning the
download; [I] inferred, including anything taken from YouTube's Gemini summary of a video, which has not been
checked against the footage.

## 1. mattbatwings: 3D graphing calculator (2026-03-29)

https://www.youtube.com/watch?v=YJJk0iLJ4Ks, code https://github.com/mattbatwings/3D-Graphing-Calculator, world
download `3d-grapher-by-mattbatwings.zip`. 27:43 long and 1.06M views when read [S]. You type an equation in x, y
and z (up to degree 3) on a keypad. The machine works out the sign of the polynomial over a 64³ grid, and two
flying-machine printers build the surface out of concrete powder dropped into water [S, I].

### What the download does when run [M]

We ran the world on Fabric 1.21.4 with Alternate Current (his setup) and on vanilla 26.3, using `tick sprint`.
Both printed the same blocks, so the build doesn't depend on the mod.

- **Layout.** A plane is one graph z. Each plane is held in two 64×64 lamp memories built from repeater locks at
  x −178..−52. Their columns are graph x and their rows are graph y, with y ≥ 0 at z −48 and y < 0 at z 8.
  The previous plane sits in a second pair at z −4 and 52. Each memory is a shift register: a new column enters
  at x −178 about every 2,000 game ticks, and the printer reads from the east end. So the print runs one plane
  behind the computation.
- **Speed.** About 2,000 gt per column and about 128,000 gt per plane. The flying-machine round trip sets that
  pace. 64 planes come to about 8.2M gt, which is 114 hours at 20 tps. The video's "about 6 hours per graph" [I]
  would then need tick warping or a smaller grid.
- **Checks.** We checked the computation with one-term equations. `y` fills the y < 0 half and `z` fills the
  whole plane at z = −32, as they should. We checked where the input reaches by diffing a cube run against a
  sphere run tick for tick: the differences reach the memories and stop there.
- **Fault 1: it stops after one plane.**
  - Two 6-bit binary counters run the machine, one for columns (x 49..57, z −68..−65) and one for planes
    (x 49..57, z −85..−82). Their LSB is the y −35 row, and Reset sets the plane count to 0.
  - The column clock passes a subtract-mode comparator gate at (5, −41, −53), whose east side is an inhibit.
  - The inhibit turns on when two signals are both off: "columns running", and "planes running" from a dust
    line that starts at z −78.
  - "Planes running" comes from a torch at (55, −36, −81). That torch reads the plane counter's **bit 0** row,
    so it goes off as soon as the count reaches 1. The column counter, built from the same cells, ends on its
    wrap after 64.
  - Replacing the wool at (53, −40, −78) with a redstone block keeps "planes running" on. Plane 2 then starts on
    its own, and the run went on through 5 planes until we stopped it.
  - With that block in place, nothing stops the machine after 64 planes. A real end-of-graph stop isn't built
    or tested yet.
- **Fault 2: the first printed planes are stale.** The saved world still holds his last graph in all four
  memories, and Reset doesn't clear them (it changes 235 blocks, none of them memory). Every equation therefore
  printed the same first plane, a ring cut from his old graph, and the second plane mixes his data with ours.
  With a one-plane print lag, this may be how the design is meant to work [I]. It does mean a fresh world
  needs its memories cleared first.

### Lessons for us

1. **Diff two runs that differ only in their input.** Snapshotting the whole world and diffing an equation-A
   run against an equation-B run at the same tick found the break in a 1.15M-block machine without reading its
   design. Diffing a working state against a stuck one at each step of a Start press found the gate. Both cost
   no model time. Apply: a harness tool that diffs two runs of a build (or two states of one run) by region and
   tick, for big builds like `cpu_fib4` and the doors.
2. **State saved in a world outlives a reset.** His Reset leaves memories and counters as they were. Our
   packaged `place` sets every block fresh, and specs have `reset` tests. Apply: give each stateful build
   (`cpu_fib4`, registers, counters) a test that runs it, resets it and runs it again, checking every memory
   cell rather than just the outputs.
3. **Test the end condition, not only the first steps.** His end-of-run check was tied to the wrong bit and
   stops after one plane. Watching a few planes would never show whether it stops at 64. Apply: counter and
   CPU specs should step past the wrap and check the stop. A `counter/` spec needs a wrap-and-stop test.
4. **Model the maths in code first.** His repo is a Python model of each stage: the parser, the
   finite-difference column generator, the exponent ROM and the sign test. Apply: keep an executable model next
   to every arithmetic build, as `cpu_fib4`'s Fibonacci test does, and diff the model against the build's memory
   contents too, not only its display.
5. **Long builds make debugging slow.** He calls a 6-hour full test "miserable" [I]. Our per-part tick tests and
   `tick sprint` avoid that, and the case is worth making when we present our work.
6. **Presentation.** A long explainer that walks through each subsystem in order, with the helpers credited
   (Sloimay and MythicalPingu built the printer) [I]. Each subsystem is in its own colour of wool, which made
   the world readable when scanned [M].

## 2. mattbatwings: "How To Wire Like a Redstone Pro!" (2024-06-08)

https://www.youtube.com/watch?v=pT-VWjqYli0, world download `wiring-like-a-pro.zip` (Java 1.18.2). 11:56 long and
826k views when read [S]. A wiring tutorial with chapters on single bit, multi-bit, horizontal/vertical
conversion, hex (signal strength), crossing wires and building techniques [S]. It shows no testing.

What the world contains [M]: 3,791 redstone components in about 60 demo builds. The longest straight dust run
between repeaters is 15 blocks, and there are 55 such runs. Seven demos are 15 repeaters plus 2 comparators each,
which fits the repeater-chain hex line.

What the video says [I]: a repeater every 15 dust; glass towers carry signals up and spirals carry them down;
buses at 2-block pitch, or 1-block when staggered; adjacent spirals alternate clockwise and counter-clockwise;
going from horizontal to vertical reverses the bit order; a hex line made of repeaters carries strength X for
exactly X blocks; crossings by a repeater intersection stackable every 2 blocks, or a messy zero-tick crossover;
bulk `//stack` can drop dust that has no block under it.

### Lessons for us: what the builds taught

We rebuilt the demos from the world as `ref_mattbatwings_*` specs and ran them on 26.3. Every spec below passes
its tests [M]. Sizes are x×y×z. Delays are game ticks (gt) at the output lamp, so each fall includes the lamp's
own 4 gt off delay (`lamp_off_delay_4_ticks`). How each one works is read from the blocks [I] unless it says
otherwise.

1. **Only boosters cost ticks on a climber.** Dust on a wool staircase, on a 2×2 spiral or on a glass zigzag
   adds no delay. One booster partway up restores strength for climbs of 20 to 26 blocks. A repeater costs
   rise 2 / fall 6 gt and a torch pair (two inverters in series) rise 4 / fall 8 gt, whatever the length [M].
   Specs: `vertical_wire/ref_mattbatwings_diag_up_repeater` (1×21×25), `diag_down_repeater` (1×26×27),
   `diag_up_torch_pair` (1×21×24), `spiral_down_repeater` (3×24×3), `spiral_down_torch_pair` (3×26×2),
   `glass_zigzag_up_repeater`, `glass_zigzag_up_torch_pair` and `glass_zigzag_up_torch_pair_flat` (1×26×4).
   No mutant shows the booster is needed [I]. Library: the unboosted shafts were there (`vwire_staircase`,
   `vwire_spiral`, `vwire_glass_zigzag_up`/`_long`); the boosted staircase and spiral variants are new.
   A torch-boosted wire starts lit after placement and goes dark about 6 gt later, so its test must settle
   first [M].
2. **4-bit buses by geometry alone.**
   - `ref_mattbatwings_wool_diagonal_bus4_3wide`: four dust lines on wool staircases, offset 2 in y and 1 in x.
     All 16 patterns pass, rise 0 / fall 4, 2×21×19 [M]. Library had `vwire_staircase_bus`.
   - `ref_mattbatwings_glass_zigzag_torch_refresh_bus4`: four glass zigzags with a torch pair each, 25 blocks of
     height, rise 4 / fall 8, 4×27×7 [M]. Library had `vwire_glass_zigzag_*` and `vwire_torch_tower_bus`
     separately.
   - `wire/ref_mattbatwings_stacked_flat_bus4_repeater`: four 34-block lines at y 1, 3, 5, 7 over wool in a
     1-wide column, one repeater each, rise 2 / fall 6, 1×8×37 [M]. Library had `wire_flat_bus` and
     `wire_spaced_bus`.
3. **Repeater between two wool blocks; target block as a conductor.** A dust line pointing into a wool block
   weakly powers it, and a repeater reading that wool restarts the line at 15
   (`ref_mattbatwings_wire_repeater_between_wool`, 1×2×37). A dust-powered target block feeds a repeater the
   same way (`ref_mattbatwings_wire_target_repeater`, 9×2×17). Both rise 2 / fall 6 [M]. Neither was isolated
   in the library.
4. **Hex line: a decaying ruler re-encoded by parallel repeaters.** A comparator reading a barrel puts strength
   S on a dust line, which is lit for exactly S blocks. A delay-1 repeater beside each of its dust writes 15
   into a second, unconnected line, which then decays back to exactly S at a 15-block end, where a comparator
   reads it [I]. Strengths 0..15 all arrive exactly, with a constant 2 gt to the first comparator plus 4 gt to
   the output at any strength [M]. Specs: `signal_strength/ref_mattbatwings_hex_line_flat` (3×2×19),
   `hex_line_stair_targets` (2×16×22, read through target blocks), `hex_line_vertical_glass` (7×16×2). This
   settles the old lesson that asked for a repeater-chain hex line spec. Library: `wire_analog_comparator`
   carries strength by a different method; the ruler line is new.
5. **A short ruler is an analog offset.** With 11 repeaters the far end reads min(15, b+4) for b > 0 and 0 for
   b = 0, and a subtract comparator then gives max(0, that − a). All 256 (a, b) pairs pass [M]
   (`ref_mattbatwings_line_subtract`, 3×2×15). Our first expected formula was wrong; the table caught it.
6. **Comparator, wool, dust relay.** A comparator into a wool block; the dust beside the wool reads the full
   strength, not one less, and the next comparator reads it again. Four dust cells equal the input for every
   s = 0..15, 2 gt per stage, 3 blocks per stage, 1×2×16 [M] (`ref_mattbatwings_comparator_relay`). Library:
   `wire_analog_comparator` is the comparator-block chain without the dust.
7. **Stacked fan-out.** One comparator into a red wool block feeds the dust above and below it; a dust
   staircase past stained-glass columns carries the signal to two more layers. One input lights four lamps on
   four layers, rise 6 / fall 10 on all four, 19×9×5 [M] (`crossing/ref_mattbatwings_comparator_fanout4`). The
   wool-both-faces and glass links were not isolated [I]. With a 47-block stacked bus behind it and a repeater
   every 16 blocks, each repeater adds exactly 2 gt (far lamps rise 14) [M]
   (`ref_mattbatwings_bus4_56_comparator_fanout`, 58×9×9). Its fan-in end and the 2 gt route to out1 were not
   traced.
8. **Dead structure in a cut-out.** Three of the fan-out's subtract taps read 0: a repeater feeds both the
   comparator's rear and the dust at its side, so 15 − 15 = 0 [M] (`fanout4` test `taps`). Level reads per
   cell found them; reading the layout did not.
9. **Not built.** W34, W47 and W56 climb 37 to 44 blocks, over the 32-block `references` plot height [M].
   W29, W48, W57, W70 and W78 repeat a built cluster or a library spec; W84 has no output; W25, W36, W43, W52
   and W62 were not attempted.

Left from the first reading of the video: settle MECHANICS' "untested as a spiral" (spiral risers pass, but
no spec checks one-way flow), check bit order where a CPU bus goes vertical, and the lint warning for dust
with nothing under it.

## 3. mattbatwings: "I Made Building Redstone 100x Faster!"

https://www.youtube.com/watch?v=A2tBeCTA2Dk, no world download. 18:40 long and 91k views when read [S]. A tour of
his public Discord archive of reusable circuits, in 8 categories: arithmetic, combinational, sequential, displays,
hex, conversion, wiring and miscellaneous. Each entry lists delay in ticks, size, vertical or horizontal I/O,
tileability, whether it uses torches, whether outputs are synchronised or rippling, and who built it [I]. He says
one lost divider design comes with "no guarantees that it works properly" [I].

### Lessons for us: what the builds taught

We rebuilt archive entries as `ref_<author>_<design>` specs and ran them on 26.3. Every spec in items 1-21
passes its tests [M]; in the second batch (after item 21) a spec marked *partial* passes only the tests that
pin what it really does, and the README claim it misses is named. Sizes are x×y×z; delays are game ticks (gt). Archive "ticks" are redstone ticks (2 gt) on the
combinational parts we checked: classic crosswire "1" is 2 gt, the carry-cancel adder's "6" is 12 gt, the
encoder's "1t" pulse is 2 gt [M]. Three figures did not match in either unit: `ref_antekcookie_cmp8` (8 rt,
worst measured delay 18 gt), `ref_indy_serial_8b` (2RT, shortest working pulse 12 gt) and
`ref_librok_shift_2t_4function` (2t, shortest working press period 8 gt) [M]. How each design works is read
from blocks and traces [I] unless it says otherwise. Two categories the first reading found missing,
magnitude comparator and redcoder, now have ref specs.

**Analog strength as logic.**

1. **Dust decay as carry lookahead.** `full_adder/ref_llucas_inc8_2t` (8-bit incrementer, 4×17×7, all 256
   inputs): each bit's barrel source sits 2 levels lower than the one before, and the dust staircase between
   bits loses exactly 2 per bit, so every lower bit's 0 arrives at bit k at bit k's own level. Two subtract
   comparators then tell "a lower bit is 0" from "only my bit is 0" [I]. Every output rises at 4 gt and falls
   at 8 whatever the carry length [M]. Not in the library.
2. **Decay-offset XOR and a constant-time carry bus.** `full_adder/ref_sloimay_cca_8bit_5hz` (8-bit adder,
   11×17×5): operands enter the two ends of a short dust line and two subtract comparators cancel equal levels,
   giving a ⊕ b; generate and kill levels spread up a dust staircase bus with a 2-level drop per layer [I].
   Delay is 12 gt for a 1-bit and a 7-bit carry alike, on 30 + 128 chosen sums and 448 adversarial patterns,
   with a 5,000-row random check passing outside the file [M]. Removing any of three bus dusts fails the sums
   tests [M]. The 5 Hz pipelining claim was not measured. Library: carry-cancel adders exist
   (`add_carry_cancel_cell`), with a per-bit carry; the bus and the decay XOR are new.
3. **15 against 14 per bit.** `magnitude_comparator/ref_mattbatwings_cmp8_eq` (4×18×6): an input gives 15 to
   one dust and 14 to the next, so of two subtract comparators per bit only the one for A > B or A < B outputs
   anything; equal bits cancel [M, in a probe run not kept as a spec]. Stage b outputs gt/eq of bits
   b..0; 51 vectors on 16 outputs pass with rise 6 / fall 10 at every stage [M].
   `ref_antekcookie_cmp8` (5×16×10) gives one-hot eq/lt/gt, worst 18 gt, and shows eq and lt lit together for
   about 2 gt on returning to equal [M]. Neither existed in the library.
4. **Two offset thermometers give one-hot.** `signal_strength/ref_unknown_redcoder_3wide` (18×3×4): one strength
   drives two dust lines one block apart; an output is lit iff the first line reaches its column and the
   second doesn't, so it lights only at s = k. Every s = 0..15 lights one line, 6 gt [M]. Library:
   `analog_decoder` does the same job with one subtract comparator per line. A one-item barrel
   on a subtract side trims exactly 1 where the last column lacks a decay step: with it empty, s = 1 lights
   nothing [M].
5. **Torch restart chain.** `signal_strength/ref_mattbatwings_redcoder_vertical` (2×17×6): the first level the
   dust doesn't reach lights its output and a side torch; that torch powers the next target block, which
   reseeds the dust at 15, so every level above stays powered and only one output lights. The trace shows
   15, 14, 13 … above the first dark level [M]. Rise 4 or 6 gt for any pair of strengths [M]. Target blocks
   used as conductors were not in the library; `analog_decoder` is the nearest decoder.
6. **Equality as NOR of two one-sided differences.** `signal_strength/ref_lmt_hex_equality_check` (4×2×5):
   s − r and r − s on two subtract comparators turn off one wall torch; all 256 pairs pass, 6 gt [M]. Library
   had `analog_compare_ge` and `analog_abs_diff`, not equality.
7. **Barrel thresholds as a lookup table.** `signal_strength/ref_aminotreal_hex_halfer` (18×3×4): a cake (14)
   minus the input feeds a decaying thermometer, and five subtract comparators read barrels at 3, 6, 9, 12, 15
   against it; out = ⌊n/2⌋ for all 16 inputs, 6 gt [M]. Reprogramming means changing item counts [I].
   Library: `analog_const_container` for the constants, no lookup-table function.
8. **Two-comparator neutral memory.** `signal_strength/ref_unknown_hex_incdec` (5×3×6): two subtract
   comparators read strength-14 barrels through wool in a loop, F = 14 − E and E = 14 − F, so every value holds.
   A 4 gt pulse of 15 on one wool overrides its barrel (as in `comparator_container_masks_weak_block_power`)
   and moves the value by exactly 1: up 0..14 saturating, down to 0, inc 4 gt, dec 6 gt [M]. Library had
   comparator-ring memories (`analog_peak_hold`), not an up/down analog counter.
9. **Comparator loops hold a whole 0..15 value.** `rs_latch/ref_unknown_lra_hex_rs_horizontal` (3×3×5) holds
   3, 6 and 8 with no decay, a larger value overwrites, a smaller one is ignored, and a side input drains it
   in 4 to 6 gt [M]. `d_latch/ref_unknown_lra_hex_d_latch` (3×3×5) computes clk − (15 − data) into the same
   kind of loop and re-latches 8, then 3, then 0 on clicks [M]. Library: `rs_comparator_ring` (binary),
   `analog_peak_hold`, `dl_subtract_lock`.
10. **Containers as constants.** Barrels and hoppers packed with items give fixed strengths with no torch:
    `binary_decoder/ref_llucas_torchless_a` (3×11×18, 3-to-8 active-low, release 2 gt, select 6 gt) and
    `ref_llucas_dec005` (6×8×17, new output at +4, old off at +8) [M]. Both were dead until the barrel
    contents were read from the .schem block entities; the parsed block list drops them [M]. Library:
    `analog_const_container`.

**Locks, pulses and counters.**

11. **Lock-race T flip-flop.** One signal drives both a repeater's data input and its lock. When it drops,
    an ON repeater turns off and an OFF repeater still turns on 2 gt later, before the lock returns [M for the
    behaviour, I for the scheduled-tick cause]. `t_flip_flop/ref_unknown_lra_tff_repeater_lock` (9×2×3)
    toggles 6 of 6 presses. The library's lock flip-flops (`tff_torch_repeater`, `tff_lightless_lock`) are
    master-slave; this single-repeater toggle is new.
12. **Synchronous counter from a torch-refreshed dust ladder.** `counter/ref_mattbatwings_counter_8bit_3x3`
    (3×18×4): one 4 gt pulse drops a dust ladder; each bit's torch (lit while the bit is
    0) re-powers the ladder at its level, so ladder stage k stays low only if bits 0..k−1 are all 1, and every
    bit's lock-race toggle (item 11) fires together [I]. Every bit changes at +8 gt for 0→1, 127→128 and
    255→0 alike; 257 presses wrap 0..255 [M]. `ref_mattbatwings_counter_8bit_load` (8×20×4) adds a load: set
    every bit through a bus, then a comparator per bit clears the zero bits (all lamps on at +6, zero bits dark
    at +16) [M]. Library: synchronous counters existed (`count_bulb_sync`); the ladder and the loadable counter
    are new.
13. **Rising-edge pulse: rear minus delayed side.** A subtract comparator with the signal on its rear and the
    same signal through a repeater on its side gives one 2d gt pulse per rise. Measured d = 2 → 4 gt, 3 → 6,
    4 → 8; d = 1 gives no pulse [M] (`clock/ref_unknown_config_clock`, 10×2×2, which also shows a self-gated
    comparator loop whose period is 4 + 4d: 20 gt at d = 4, 12 at d = 2). Used in
    `d_latch/ref_unknown_lra_dlatch` (8×2×5: pulse turns a torch off, which opens a lock; q at +8),
    `ref_indy_serial_8b` and the counters. Library: `pulse_rising_comparator`, `clock_comparator_repeater`.
14. **Cross-coupled torch SR latch.** `rs_latch/ref_unknown_lra_srlatch` (3×3×7): set wins a same-tick press
    from either state and either order [M].
    Library: the `rs_latch` family.

**Wiring and conversion.**

15. **Crossings.** `crossing/ref_mattbatwings_classic_crosswire` (5×11×5, 5 bits each way): a repeater drives a
    wool block at each crossing and the wool's strong power bridges the gap; 41 patterns, 2 gt [M].
    `ref_kuggo_instant_crosswire_a` (7×18×9) and `_b` (7×18×7), 8 bits each way: dust only, staircasing over
    wool, 70 patterns, 0 gt [M]. Library: `cross_instant_*`, `cross_underpass`, `cross_diode_grid`.
16. **Multi-bit risers.** `vertical_wire/ref_mattbatwings_updiag_1wide` (1×22×18, 4 lines on glass steps,
    16 patterns, rise 4) and `ref_mattbatwings_spirals_updown` (3×16×24, 4 bits up and 4 down, 64 patterns,
    rise 0) [M]. Why the interleaved lines in updiag don't merge was not traced. Library had single spirals
    (`vwire_spiral`); offset multi-bit spirals are new.
17. **Hex lines.** `wire/ref_mattbatwings_hex_flat` (3×2×19), `vertical_wire/ref_mattbatwings_hex_up` (7×16×2) and
    `hex_down` (9×17×3): the ruler line of section 2 item 4, strengths 0..15 exact, 4 gt [M].
18. **Serial lines.** `ref_indy_serial_8b` (10×2×47): load, then 8 presses shift out, at 12 gt per pulse or
    slower; every faster rhythm tried failed [M], against a README figure of "2RT".
    `encoder/ref_librok_observer_encoder_serial` (9×5×12): an observer encoder stores its code as single items
    in dropper pairs, and a torch-driven repeater chain unmasks four subtract comparators one per 4 gt, sending
    start, b0, b1, b2; each read returns its item, so the memory clears itself [M]. The placement pass fires
    the droppers, so its tests insert items after placing [M]. Library: no serial-out or dropper-latch spec.
19. **Observer-on-lamp edge detector.** `encoder/ref_librok_observer_encoder_7to3` (5×5×5): an observer facing
    a lamp pulses on both edges; seven of them OR into a 3-bit code, 4 gt after on and 8 after off (the lamp
    delay) [M]. Library: observer pulse specs in `mechanics/`, no lamp edge detector.
20. **Priority encoders.** `encoder/ref_mattbatwings_fast_priority` (10×3×7): subtract comparators cancel lower
    rows, every output rises at 4 gt [M]. `ref_mattbatwings_small_priority` (7×2×10): a torch chain where each
    winner disables the next row, ripple worst 12 gt [M]. Both need a real lever on its block: a redstone-block
    driver beside the block does not power it, so the torch on it stays lit [M, in a probe run not kept as a
    spec]. Library: `dec_prio_4to2`, `dec_prio_8to3`.
21. **Bidirectional shift register.** `shift_register/ref_librok_shift_2t_4function` (10×18×15): up, down,
    load, reset on 8 vertical slices, 14 gt to a rising lamp, one shift per press however long it is held [M].
    Presses need at least 3 gt high and an 8 gt period with repeater drivers; the "2t" claim was not
    reproduced [M]. Library had only serial-in shift registers.

### Second batch: the rest of the archive

104 more entries were rebuilt: 92 pass, 11 are partial, 1 failed (REDCODE001, removed). 49 more were
read without running ("analysed" table at the end). Delays are measured from the input change [M] and
include any fixture repeater (2 gt) a rebuild needed; "net" removes it. Mechanisms are [I] unless marked.
A lamp output adds 4 gt to every fall (`lamp_off_delay_4_ticks` in `docs/MECHANICS.md`). Several archive
schematics are blank templates (every tap placed); for those the [M] result is of a code the rebuilder
chose, not one the archive shipped.

**Analog arithmetic and conversion.**

| Technique | How | Proving spec, size, delay | Library before |
|---|---|---|---|
| One-way dust staircase as a carry/OR bus | Dust stepping up over a transparent step reads only the dust below, so stage k sees the OR of lower stages; a repeater per stage restores 15 | `full_adder/ref_aminotreal_incrementor_4bit` 4×10×8, rise 6 every bit; `_decrementor_4bit` 6×9×4, rise 4; `_negator` 4×10×7, 4 gt; `encoder/ref_librok_vertical_priority_15` 4×16×4, rise 4, 15 levels end at strength 1 [M] | mechanic `dust_transparent_step_one_way`; not used as a bus |
| XOR from two subtract comparators on one OR rear | rear = a OR b, sides a and b, outputs merged on one dust | incrementor, negator [M, levels read from trace] | comparator XORs in `xor/`; not this form |
| Constant-1 barrel rear makes a comparator a NOR of its sides | rear 1 minus max(sides) | `seven_segment/ref_nano_passthrough_display`; emptying one such barrel fails a sweep [M] | `nor/or_nor_comparator` (different) |
| Side held at 14 as a 15-only valve | subtract comparator passes 1 only when its rear is 15; joins two ports one-way | same spec, trace T=1, V=14 [M] | no |
| Popcount by saturating subtract chains | one chain subtracts from 15 down to 8, a second counts up from 0, a final subtract joins them | `signal_strength/ref_mattbatwings_unary_counter_15` 32×2×10, 14 gt net; `_8` 7×2×17, 8 gt for every pattern [M] | no |
| Dust-only signum | nonzero = wired OR of dust staircases; sign = fan-out | `full_adder/ref_walvischris_signum_5bit` 11×10×3, `magnitude_comparator/ref_mattbatwings_signum_8bit` 5×16×5, both 0 gt to the dust [M] | no |
| Absolute value | sign-gated invert enable carried as a decaying dust ladder (15..1); or barrel constants | `full_adder/ref_walvischris_abs8` 13×19×7, settles 12 gt with a 10 gt out7 glitch on 0x40→0xC0; `ref_llucas_abs8_3t` 9×18×9, 8/12 gt [M] | no |
| Accumulator, sum latched on one pulse | carry settles before the latch, all bits change together | `accumulator/ref_mattbatwings_accumulator_8bit` 11×18×9, rise +8 / fall +12 on every bit, 255+1 included [M] | no |
| Hex digit as a strength, decoded by decay windows | repeater pairs k apart on one decaying line feed a subtract comparator: on for k input values; bit j uses windows of 2^j | `signal_strength/ref_mattbatwings_hex_to_bin` 5×9×17, 6 gt (*partial*: stale dust on dsat1-3) [M]; `ref_aminotreal_hex_to_binary` 9×4×18, 6 gt, ORs detectors by joining dusts [M] | `analog_decoder` (one-hot only) |
| Remainder pass, one bit per stage | compare against barrel constants 8, 4, 2; a repeater-driven 15 side blocks the subtract path | `signal_strength/ref_librok_stackable_vertical_hex_to_binary` 6×9×5, +4 gt per stage, worst 34 [M] | no |
| Binary to strength | 15 torches as a thermometer on one dust line; or gated barrel constants plus one subtract | `ref_mattbatwings_bin_to_hex_targets` 13×7×16, 4 gt (`_stack` 7×11×17 *partial*: one dsat process); `ref_powsi_small_bin_to_hex` 5×6×6, 6 gt; `ref_librok_vertical_binary_to_hex` 4×9×5, ≤12 gt [M] | `analog_dac` |
| Decimal digits as strengths | strength per digit, halved or doubled per bit stage with barrel constants | `bcd/ref_xoliks_bin_to_dec_8bit` 7×18×15, ≤42 gt; `ref_xoliks_dectobin_converter` 25×18×14, ≤46 gt; fractional versions round the last place up on 16 and 248 inputs [M] | no |
| Double dabble | unclocked add-3 network, or one add-3 stage reused 8 times with levers read 6 gt apart | `bcd/ref_mattbatwings_comb_bin_to_bcd8` 19×19×48, ≤38 gt; `bin_to_bcd/ref_mattbatwings_seq_bin_to_bcd8` 34×12×33, 60 gt for every input [M] | no |
| Counting sort | per threshold k, count inputs ≥ k; output j = number of k whose count > j | `sorter/ref_oscar91_counting_sorter` 50×30×24, rise 20 / fall 24 for any vector [M] | no |
| Tristate input by strength | 15 = 1, 14 = don't care, 0 = 0 on one dust line | `binary_decoder/ref_llucas_tristate_decoder_2t` 7×8×20, rise 4 / fall 8 [M] | no |
| Gray-coded windows to 16 segments | each segment is a union of strength intervals, so a step of 1 flips one segment | `seven_segment/ref_mixel_16seg_display` 14×10×11, 18-24 gt from insert [M] | no |
| Comparator diode bus | dust, wool, compare comparator, wool repeated: strength unchanged, 2 gt per hop, one-way | `register/ref_zebronic_register_file_7x32_dual_read` [M, trace] | no |

**Adders, ALUs, shifters, square roots.**

| Technique | Proving spec, size, delay | Library before |
|---|---|---|
| Stacked carry-cancel adders (2 layers per bit, staircase bus, container constants) | `full_adder/ref_fearless_z_cca_8bit_3t` 8×18×6, sum rise 6 (mutants: one barrel or the cake removed fail); `ref_don_cca_8bit_3t` 8×19×6, 6; `ref_fearless_z_cca_8bit_3t5hz` 8×19×9, 6; `ref_mixel_cca_10bit_3t` 9×24×8, 6; `ref_mattbatwings_cca_8bit_add007` 15×19×4, 10 at the dust [M] | item 2 above |
| Carry look-everywhere | `ref_mixel_cle_adder_8bit_3t` 20×19×8, rise 6; `ref_kuggo_cle_adder_8bit` 11×21×20, sums 14, cout 6 [M] | no |
| Piston-pulled corner block as carry skip | `ref_q2ck_ica_8bit` 13×7×20, rise 8 any carry length; removing bit 3's piston fails all tests [M] | `add_full_piston_instant` |
| Hex-digit carry-cancel | `ref_louparmi_hex_cca_5t` 9×18×8, 10 gt (*partial*: upper nibbles give A+B+1, the schematic's own saved state too); `ref_louparmi_hex_cca_16nibbles` (*partial*: second operand not found) [M] | no |
| Plain ripple full adder | `ref_mattbatwings_rca_dust_torch` 12×4×6, worst 10 [M] | `full_adder/` |
| ALU from one adder plus control rows (an OR-plane of op levers; no op selected = ADD) | `alu/ref_mattbatwings_alu_cca_8bit` 33×21×22, 11 ops, operand ≤22 gt, op change ≤32 gt; `ref_flyingdean_alu_8bit_4rt` 10×18×9, sum 8 gt net, Cout 10 (add) and 16 (subtract) net [M] | `cpu_alu`, `cpu_alu_compact` |
| Barrel shifter, same latency for every shift | `barrel_shifter/ref_llucas_dorito_rsh8`, `_lsh8` 6×24×17, value 4 gt net, shift 6 gt net [M] | no |
| Square root: flat PLA | `sqrt/ref_mixel_sqrt8_4t` 19×28×11, 8 gt; `ref_mattbatwings_sqrt8_2t` 29×18×17, 4 gt net [M] | no |
| Square root: sequential | `sqrt/ref_mattbatwings_sqrt8_sequential` 15×20×36, 144 gt for every input, levers read 2 at a time 20 gt apart; `ref_safetyiwisher_sqrt8_seq_71rt` 22×23×15, 136 gt, start pulse ≥16 gt [M] | no |

**Memory, registers, counters.**

| Technique | How | Proving spec, size, delay | Library before |
|---|---|---|---|
| Shared lock line over per-bit locked repeaters | one idle-high line climbs the stack; a short drop (item 13 pulse) unlocks every bit for one copy | `register/ref_mattbatwings_register8_lock` 6×18×7, read 8 gt; `ref_odmen_register16` 6×18×12, write 14, read 16 net; `shift_register/ref_mattbatwings_shift_reg_up`/`_down` 5×19×6, 8 gt; `ref_mattbatwings_shift_regs_vertical_load` 8×20×25, 12 gt; `register/ref_mattbatwings_call_stack_16x10` 54×24×18, 24 gt; `randomiser/ref_llucas_lfsr_8bit` 11×17×50 [M] | `shift_pulse_lock`, `shift_reg4_lock`, `dl_lock_stack` |
| Two copies per bit for a second read port | each copy has its own read gate; no mux | `register/ref_librok_register8_dual_read` 7×19×14, read 12 gt rise [M] | no |
| Barrel-calibrated thresholds on one decaying tower | barrel signal per bit equals the tower's level there, so one tower opens every lock | `register/ref_mattbatwings_tristate_register` 8×18×4, read 4 gt, write pulse ≥2 gt [M] | no |
| Pistons lift the non-copying chain | two opposite repeater chains share cells; pistons lift one chain's cells so it clears | `shift_register/ref_mattbatwings_bidir_shift_pistons` 13×11×23, 12 gt; mutants holding a piston column smear 11111111 [M] | no |
| Analog FIFO, move not copy | comparator rings hold 1..15; the transfer output also cuts the source ring | `signal_strength/ref_samosthesage_hex_fifo` 21×2×33, 2 gt per hop; `_vertical` 40×17×22, falls 4 gt per stage, pops 14 per stage, a 15 is stored twice [M] | item 9 (single loop) |
| Register file | `register/ref_mattbatwings_register_file_8x8` 20×29×10, read 10 gt, address taken by +3, data until +25 [M]; `ref_zebronic_register_file_7x32_dual_read` 31×26×20, analog nibbles, read 14-28 gt by distance [M] | `cpu_regs_*` |
| Up/down counter with load | `counter/ref_mattbatwings_counter_updown_load` 19×18×4, 10 gt (the "8-bit" schematic is 6 bits); `ref_tlamp_updown_load_counter` *partial*: carry into bit 6 lost [M] | item 12 |
| Position-coded decimal counter | count is a strength; a V-shaped dust gradient, abs(z−(9−d)) at row z, plus torches gives one-hot; a one-item dropper/hopper/barrel loop shapes the pulse and limits counts to one per 17 gt; digits stack observer to observer | `seven_segment/ref_maizumagames_stackable_7seg_counter` 4×9×14, lamps by +48; `_x2` carries 00..25 and 99→00 [M] | no |
| Arbiters and priority | `encoder/ref_rcs33_choose_n_arbiter` 22×6×32, +4 gt per layer, barrels of shovels as thresholds; `ref_rcs33_banking_arbiter` 21×6×31, rise 4, a dust line of length rear−1 as a threshold; `ref_rcs33_cancellable_priority_encoder` 6×6×31, ≤14 gt, two decaying lines race; `ref_mixel_priority_8bit` *partial* (one pattern of 256, one dust short) [M] | item 20 |
| 32-bit magnitude compare | `magnitude_comparator/ref_antekcookie_hex_cmp32` 5×16×14, ≤24 gt for any digit, eq and lt lit together 16-24 gt [M] | `ref_antekcookie_cmp8` |

**Programmable templates and displays.**

| Technique | Proving spec, size, delay | Library before |
|---|---|---|
| Code as present/absent taps: a repeater (encode/decode) or torch per crossing | `encoder/ref_mattbatwings_encode_v2v` 6×10×13, 4 gt; `_v2h` 6×9×11, 2 gt; `_h2h` 10×4×10; `_h2v` 4×9×9, 2 gt; `binary_decoder/ref_mattbatwings_decode_v2v`, `_v2h`, `_h2h_2wide`/`_3wide`, `_h2v`, all rise 4 / fall 8; reprogram tests swap blocks with setblock [M] | fixed decoders only |
| ROM bit as target vs wool | `seven_segment/ref_rt_rom_display` 15×20×18, 12-16 gt net, image changes as targets are swapped [M] | no |
| One dust per segment; lamp bleed fills it | `seven_segment/ref_mattbatwings_big_7seg_module` 5×10×2, 0/4 gt; `ref_mattbatwings_small_7seg_module` 5×6×4 [M] | `seg_lamp_3x5` |
| Dust into a target block lights the lamp behind; torch-on-wool stack for 3-lamp verticals | `ref_mattbatwings_big_7seg_lamps` 5×10×6, 0-8 gt rise [M] | no |
| One-hot decode then an OR plane per segment, equal depth | `bcd_to_7seg/ref_mattbatwings_fast_bcd_to_7seg` 29×23×5, 14-18 rise; `seven_segment/ref_mattbatwings_fast_hex_to_7seg` 40×23×5, glitch-free [M] | `seg_dec_bcd` |
| Unsynced decode (segments settle 12-38 gt) | `bcd_to_7seg/ref_mattbatwings_classic_hex_to_7seg`; `_classic_bcd_to_7seg` *partial* [M] | |
| Lever row on a dust line as a one-hot to strength encoder (highest lever wins) | `seven_segment/ref_aminotreal_hlp_hex_display` 28 gt, `_bcd_display` 22 gt, `_ubcd_display` 12 gt (*partial*, dsat2/3) [M] | no |
| Pixel matrices | `ref_mattbatwings_basic_pixel_display_8x8` 8×17×16, 6/10 gt, a repeater equalises a pixel's two branches; `ref_mattbatwings_4function_display` 20×25×24, write on button release (30 gt), address as a strength ramp; `ref_nano_passthrough_display` 22×25×24, two ports, no ghosts; `ref_mattbatwings_pixel_module_3x5` 5×10×11 [M] | no |
| Binary to signed decimal display | `seven_segment/ref_penscii_8bit_to_7seg_2s_comp` 17×8×34, final within 46 gt [M] | no |
| Animated icon | `seven_segment/ref_sloimay_loading_icon` 11×10×4, period 46 gt while held [M] | no |

**Inputs, randomness, wiring.**

| Technique | Proving spec, size, delay | Library before |
|---|---|---|
| Dropper `triggered` flag as a row's memory; one dust line as a block-update broadcast | `input/ref_craftymasterman_selector_panel` 3×4×5, old row off at +6 [M] | no |
| Shared clear bus between latch columns | `input/ref_mattbatwings_classic_selector_panel` 7×4×9, new lamp +6, old off +10 [M] | no |
| Key as dust-decay distance on two analog outputs | `input/ref_mattbatwings_banner_keyboard` 13×9×7, 26 keys, 2-4 gt [M] | no |
| Torch per key on its own block | `input/ref_mattbatwings_button_keypad` 5×8×5, 2 gt, key 0 masks key 8 [M] | no |
| Dropper's random slot, hopper locked by the powered dropper holds the result | `randomiser/ref_mattbatwings_two_way_randomizer` 3×3×5, `_three_way` 3×3×6 (53/40/57 of 150), `_9_way` 3×4×15 with shulker boxes as values, press period ≥25 gt [M] | no |
| Dummy button caps a dust end to stop a leak | `mux/ref_mattbatwings_flipper_8bit` 8×16×9, 4 gt; without the button in2 also lights out4 [M] | dust_redirect_by_signal_sources |
| Stale cross-shaped dust kept by `update_pass: strict` | `mux/ref_sloimay_swapper_8bit` 3×17×5, 4 gt; fails under the default pass [M] | no |

**Analysed, not run.** Read from the README [S] and the parsed blocks [I]; none is tested.

| Entry | Technique | Label |
|---|---|---|
| MULTIPY001-003, 006, 008 (combinational multipliers) | partial-product array reduced by subtract comparators and barrel constants; 8x8 at 12-52 ticks | [S] speeds, [I] structure |
| MULTIPY004, 005, 007, 010, 011 (sequential multipliers) | one bit-sliced adder (CCA or carry-save) reused per bit; radix-4 Booth halves the iterations | [S] |
| DIVIDE001-010 | restoring and non-restoring dividers, unrolled (one stage per quotient bit) or looped; 4-11 gt per bit | [S] speeds, [I] structure |
| SQRT003, 006, 007 | 256-entry lookup ROM (9 ticks); digit-by-digit 18 and 11 gt per bit | [S] |
| ROM001, ROM003, RWM001, RWM002, REGISTERFILE001 | repeater-or-wool ROM bits; word lines as dust/glass ladders; Ketari-style locked-repeater RAM at about 31 blocks per bit; 1-line cache | [S] sizes, [I] cells |
| OTHERARITH001-003, 009 | sine/cosine/tangent lookup tables (target block + torch one-hot decode); 32-bit cube root | [S] |
| OTHERCOMB010-012, IOPORT002 | CAM and read/write port crossbars with barrel constants | [I] |
| ALU002, OTHERCPU001, OTHERSEQ002, ADD001, ADD009, BINTOBCD005, BCDTOBIN004 | 16-bit ALU, multi-function math unit, 16-bit accumulator, hex and 16-bit CCAs, double dabble, sequential BCD | [S] |
| SORT002 | odd-even transposition network of analog compare-exchange cells, 17 ticks | [S] speed, [I] network |
| PIXDISPLAY005, CHARDISPLAY002, CHARDISPLAY003, OTHERDISPLAY001, OTHERDISPLAY003 | colour and sprite displays, word processor, XY matrix decoders (row/column coincidence, one torch per pixel) | [I] |

**Not built:** DECODE007 Torchless B (no input levers), Tristate A and B (input encoding not read), LFF002
(same loop as LFF001), LFF004 (no stored items in the schematic), LFF005 upper (floating dust). REDCODE001
1-wide pulse redcoder: rebuilt, but it loaded to a different start state on each run and never decoded
correctly, so the spec was removed.

**Mechanic candidates.** These are proven only inside the builds above, so none is in `docs/MECHANICS.md`
yet; each needs an isolating spec in `library/mechanics/`: the lock-race toggle (item 11); a comparator into
a block giving the dust beside it the full strength (section 2 item 6); the two-comparator neutral memory
(item 8); the rear-minus-delayed-side pulse giving nothing at delay 1 (item 13); a target block carrying
torch power on to dust at 15 (item 5); a lever on a block powering a torch's support where a redstone block
beside it does not (item 20).

Second-batch candidates, each measured inside a passing build only: a redstone block beside a lamp lights it
but leaves a torch on the lamp lit, where a lever or a repeater into it turns the torch off
(`ref_mixel_cle_adder_8bit_3t`, `ref_llucas_dorito_rsh8`, `ref_xoliks_fractional_bin_to_dec8`); a
compare-mode side of 15 cannot clear a stored 15, the tie case of `comparator_compare_is_ge`
(`ref_samosthesage_hex_fifo_vertical`); a subtract comparator with a one-item barrel behind it as a NOR of
its sides (`ref_nano_passthrough_display`); a stale cross-shaped dust kept by `update_pass: strict` powering
all four side blocks (`ref_sloimay_swapper_8bit`); a powered dropper locking the hopper above it
(`ref_mattbatwings_two_way_randomizer`); a dropper's `triggered` flag cleared by a neighbouring dust's
strength change (`ref_craftymasterman_selector_panel`); hopper fill as strength 1 + floor(14·items/320) for
redstone (`ref_louparmi_hex_cca_5t`, `ref_zebronic_register_file_7x32_dual_read`); a setblock of a lectern
with `has_book=false` reading 0 at once (`ref_aminotreal_hex_to_binary`); a note block's observer firing only
when the note actually changes (`ref_samosthesage_hex_fifo`).

## Videos recorded elsewhere

- LegDen's fastest 10×10 seamless door (https://youtu.be/bZtwoJV967k): rebuilt and measured in
  `library/door/ref_legden_fastest_10x10`.
- properinglish's 2-wide tileable comparator XOR (https://www.youtube.com/watch?v=yUTDJ6a7qkc): rebuilt in
  `library/xor/ref_properinglish_xor_2wide`.
- Door-record videos found by search, not sent: `docs/research/door_records.md`.
