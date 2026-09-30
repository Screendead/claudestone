# Wins ledger

This ledger banks true wins, where one of our designs beats the best known community design. The showreel, the README and posts take their claims from here and from nowhere else.

A result counts as a win only if all four of these hold:

1. **Rebuilt and passing.** The community design has been rebuilt as a spec from its source
   (`library/<block>/ref_<author>_<design>`, crediting the author and linking the source), and it passes on our 26.3 server.
2. **One convention.** Ours and theirs are measured under one stated convention, with the same:
   - function,
   - input and output strength assumptions,
   - edges,
   - tiling rule,
   - way of counting volume, with inputs and outputs included or excluded the same way.
3. **Strictly better.** Our metric strictly beats theirs.
4. **Nothing better known.** A fresh search finds no better community design.

Times are in game ticks (gt). The wiki's "tick" is the redstone tick, which is 2 gt. Every claim is marked SOURCED (read from a source), MEASURED (run on our server) or INFERRED.

## Wins

- **Smallest 2 gt pulse limiter: 6 against the circuit breaker's 9 (win, 2026-10-01).**
  - **Designs.** Ours is `t2_a_qc_breaker` (`library/pulse_limiter/`). It beats the Minecraft Wiki's "Circuit Breaker Pulse Limiter", which the wiki also lists as the "Circuit breaker" rising edge detector. The rebuild is `ref_wiki_circuit_breaker`, with the block-drop check `ref_wiki_circuit_breaker_blockdrop` (both in `library/rising_edge/`). Credit goes to the Minecraft Wiki editors: https://minecraft.wiki/w/Redstone_circuits/Pulse#circuit_breaker , schematic at https://minecraft.wiki/w/Redstone_circuits/Pulse/red . The wiki states 1×3×3 (9), 1-wide, delay 1 tick and output pulse 1 tick (SOURCED).
  - **What changed.** Ours is the circuit breaker without its dust-and-support column. The input line points into the block on the piston, and the piston is powered through quasi-connectivity rather than through the support of a dust (INFERRED from the layouts; the behaviour is MEASURED below).
  - **Metrics.** Both designs have (MEASURED, 2026-10-01, `scripts.try`):
    - delay 2 gt and a 2 gt output under the harness driver, and 4 gt delay with a 2 gt output when fed by a delay-1 repeater,
    - the same full-strength output from a delay-1 repeater,
    - a pulse on every input of 3 gt or longer, and at every gap from 1 to 6 gt,
    - the same failure: an input of 1-2 gt still gives its pulse but drops the block, and the next input is lost,
    - a pulse that makes a sticky piston drop its block.

    The `widths`, `gaps` and `repeater fed` tests of the two specs have identical step lists, compared programmatically (MEASURED). Ours has volume **6** (2×3×1) and theirs has volume **9** (3×3×1) (MEASURED; 9 matches the wiki's figure).
  - **Why it is a win.**
    1. Rebuilt and passing: `ref_wiki_circuit_breaker` and `ref_wiki_circuit_breaker_blockdrop` pass on 26.3 (MEASURED).
    2. One convention. Both specs keep the input dust and the output dust, with their supports, as fixtures outside the counted box. Both are driven the same two ways, a placed block and a delay-1 repeater. Both have a rising edge only, and neither claims tiling (SOURCED from the specs).
       - Our input support is glass, so the quasi-connectivity inside the counted box does the work, not a fixture.
       - Our design also passes with the input dust on smooth stone, like the ref's input fixture (MEASURED, a temporary copy, since removed).
       - The wiki design cannot be counted as 6 in the same way. Its third column is a dust whose support powers the piston, so leaving that column out would hide working blocks in a fixture (INFERRED).
    3. Strictly better: 6 < 9, with identical measured behaviour (MEASURED).
    4. Nothing better known (search on 2026-10-01).
       - **Searched:** the wiki Pulse page, including its Pulse limiter, Pulse generator and RED sections; the pulse_limiter and red schematic galleries; and web and forum searches for compact and quasi-connectivity pulse limiters (SOURCED).
       - **No design under 9 at 2 gt was found.** The candidates that do exist are:
         - Dropper-hopper, 8: delay 3 rt, output 3.5 rt (SOURCED).
         - Moving-block off-pulse limiter, 8: falling edge only (SOURCED).
         - bumbatumbarumba's 2×1×4 monostable, 8, 2013: an inverted RED (SOURCED, minecraftforum.net thread 346756).
       - **The Moved observer RED / Observer pulse generator is smaller (1×1×3, 3) but is not the same function** (SOURCED size; rebuilt as `ref_wiki_moved_observer_red` from the wiki's text, because the wiki gives only an image).
         - It is slower: 5 gt delay under the harness driver and 6 gt fed by a repeater (MEASURED).
         - It gives no output at all for a 3 gt or 4 gt input, and it loses the next input at gaps of 4 and 5 gt (MEASURED, its `widths` and `gaps` tests).
         - So it does not dominate ours. On the volume-delay front the points are observer (3, 5 gt, loses some inputs), ours (6, 2 gt) and the circuit breaker (9, 2 gt), and the circuit breaker is dominated.
  - **Test ids.**
    - `test_spec[t2_a_qc_breaker::widths]`
    - `test_spec[t2_a_qc_breaker::gaps]`
    - `test_spec[t2_a_qc_breaker::repeater fed]`
    - `test_spec[t2_a_qc_breaker::repeater into the block]`
    - `test_spec[t2_a_qc_breaker::drops a block]`
    - `test_spec[ref_wiki_circuit_breaker::widths]`
    - `test_spec[ref_wiki_circuit_breaker::gaps]`
    - `test_spec[ref_wiki_circuit_breaker::repeater fed]`
    - `test_spec[ref_wiki_circuit_breaker_blockdrop::drops a block]`
    - `test_spec[ref_wiki_moved_observer_red::widths]` (for the observer comparison)
    - `test_spec[ref_wiki_moved_observer_red::gaps]` (for the observer comparison)
  - **Caveats.**
    - The win is scoped to a 2 gt delay. It is not "the smallest pulse limiter", because the observer design is smaller at a slower delay and loses some inputs.
    - Ours works on Java only, because it relies on quasi-connectivity. The wiki circuit breaker is captioned for both editions (INFERRED from the wiki's JE/BE notes).
    - The observer rebuild follows the wiki's text, not a schematic. A different faithful layout might not lose 3-4 gt inputs, and that would need a fresh check before this entry is cited against it (INFERRED).
    - This closes only T2's "≤9 at 2 gt" target. The instant (0 gt) limiter with a ≤2 gt output is not claimed.
    - `t2_b_sand_breaker` (also 6) recovers from a dropped block when the next input comes 10 gt or more later. It is not entityless and is not part of this claim.

Also refereed without a win (2026-09-30): the XOR in T6 and the edge detectors in T4.

## Ties and near misses

These are not claims of a win.

- **0 gt rising-edge detector (tie, 2026-09-30).**
  - **Designs.** Ours is `pulse_rising_instant_piston`. It ties the Minecraft Wiki's "Dust-cut rising edge detector (Unrepeated)", rebuilt as `ref_wiki_dust_cut_red`. Credit goes to the Minecraft Wiki editors: https://minecraft.wiki/w/Redstone_circuits/Pulse#dust-cut_rising_edge_detector , schematic at https://minecraft.wiki/w/Redstone_circuits/Pulse/red .
  - **Metrics.** Both designs have (MEASURED):
    - volume 15,
    - delay 0 gt,
    - a 3 gt pulse under the harness driver and 2 gt when fed by a delay-1 repeater,
    - the same failure: an input of 1-2 gt jams the next edge.
  - **Why it is a tie.** It is the same circuit, and only the way the input enters differs (INFERRED). Counting ours as 12 against their 15 would be an artefact of the convention, not a win.
  - **Test ids.**
    - `test_spec[pulse_rising_instant_piston::output rises the same tick and is cut 3 ticks later]`
    - `test_spec[pulse_rising_instant_piston::inputs of 3 ticks and longer, repeatedly]`
    - `test_spec[ref_wiki_dust_cut_red::widths]`
    - `test_spec[ref_wiki_dust_cut_red::gaps]`
    - `test_spec[ref_wiki_dust_cut_red::repeater fed]`
  - **Caveat.** Our figures when fed by a repeater came from a probe copy that is kept outside the library. The library spec for our design has no test fed by a repeater.
