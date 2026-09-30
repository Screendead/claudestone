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

None yet (2026-09-30). Two claims were refereed: the XOR in T6 and the edge detectors in T4. Neither met the bar.

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
