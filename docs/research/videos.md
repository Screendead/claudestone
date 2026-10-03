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

### Lessons for us

1. **Spiral risers.** `library/vertical_wire/vwire_spiral` exists, but MECHANICS.md still says the zero-tick
   diode is "Untested as a spiral". Apply: test a spiral bus with adjacent spirals turning opposite ways, check
   each bit stays separate at 1- and 2-block pitch, and settle the MECHANICS entry.
2. **Repeater-chain hex line.** Apply: add a spec to `library/signal_strength/` that checks the far end at each
   strength 1..15 and measures its delay against a comparator chain.
3. **Bus pitch and crosstalk.** Apply: state the pitch in each `wire/` and `crossing/` bus spec, and add a test
   that drives one bit and expects every other bit unchanged.
4. **Bit order through risers.** Apply: where a CPU bus goes vertical, check the order of the bits, not just
   that they arrive.
5. **Dust needs a block under it.** Apply: a lint warning for dust with nothing solid beneath it in generated
   specs.
6. **Presentation.** A before/after thumbnail and one chapter per problem. The `cpu_fib4` OUT lines (72–74 gt
   routed, then 8–10 gt laid by hand) would make a good before/after.

## 3. mattbatwings: "I Made Building Redstone 100x Faster!"

https://www.youtube.com/watch?v=A2tBeCTA2Dk, no world download. 18:40 long and 91k views when read [S]. A tour of
his public Discord archive of reusable circuits, in 8 categories: arithmetic, combinational, sequential, displays,
hex, conversion, wiring and miscellaneous. Each entry lists delay in ticks, size, vertical or horizontal I/O,
tileability, whether it uses torches, whether outputs are synchronised or rippling, and who built it [I]. He says
one lost divider design comes with "no guarantees that it works properly" [I].

### Lessons for us

1. **Spec sheets.** His entries list the same things our traits and `library/INDEX.md` record, plus I/O
   orientation. Apply: check `redstone/traits.VOCABULARY` for vertical/horizontal I/O and "no torches" (burnout
   proof), and add whatever is missing as checked traits.
2. **Show both sides of a trade-off.** He keeps a fast-but-large and a slow-but-small priority circuit side by
   side. Apply: give both delay and size in each description of `encoder/dec_prio_*` and `crossing/cross_*`, so
   the pairs show.
3. **Categories we don't have.** No magnitude comparator, multiplier, square root, accumulator, hex/FIFO,
   redcoder (hex to one of 16) or randomiser. Apply: the comparator and accumulator (which a CPU needs) and the
   redcoder are the cheapest to add as tested specs.
4. **Carry-cancel adders.** He cites 3-tick and torchless versions [I]. We have
   `full_adder/add_carry_cancel_cell` and `add_carry_cancel_chain_x4`. Apply: measure ours, and put a result in
   WINS.md only after a refereed comparison.
5. **What we offer that his archive doesn't.** His archive has no guarantee that a part works. Every spec in
   ours passes its tests tick by tick. Apply: say so next to the library index in the README.

## Videos recorded elsewhere

- LegDen's fastest 10×10 seamless door (https://youtu.be/bZtwoJV967k): rebuilt and measured in
  `library/door/ref_legden_fastest_10x10`.
- properinglish's 2-wide tileable comparator XOR (https://www.youtube.com/watch?v=yUTDJ6a7qkc): rebuilt in
  `library/xor/ref_properinglish_xor_2wide`.
- Door-record videos found by search, not sent: `docs/research/door_records.md`.
