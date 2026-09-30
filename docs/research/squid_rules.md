# Squid Records door rules (the Java ruleset), distilled
Source: "Door Rules" Google Doc, https://docs.google.com/document/d/1kDNXIvQ8uAMU5qRFXIk6nLxbVliIjcMu1MjHjLJrRH4/edit
(linked in r/redstone #docs, 19 Jun 2025). Read 2026-09-30. Records live in #record-logs of Redstone Squid's
Discord (guild 433618741528625152), which the user has not joined. The Bedrock Scribd doc is a translation of an older version.

## Naming
Title: <wiring placement restrictions> <animated restrictions> <size> <type> <orientation>
Subtitle: <component restrictions> <misc restrictions>. E.g. "flush seamless full-sync 5x5 iris funnel trapdoor / No slimes, honey, observers, directional".
Record title = <FIRST|FASTEST|SMALLEST|FASTEST SMALLEST|SMALLEST FASTEST> <category>. Every combination of restrictions is its own category.

## Eligibility (section 3)
- Piston door/entrance records REQUIRE at least one SEAMLESS tier.
- Input: stone button, wooden button or lever, on the contraption's surface, with block support inside the volume. Must work with BOTH
  direct (player) input and repeater input (MC-172213: player vs repeater input differ). Button: player on activation, repeater on deactivation.
- Reliable: no flaky glitches, no time-of-day dependence, no permanent clocks that normal play can break; bounded open/close time (no RNG);
  unlimited uses; not save-state dependent; vanilla, no cheats; works in >=1 Java release; overworld; players in the hallway in a stable
  state can't break it; non-isolated components (sculk, pufferfish) must not be able to break it.
- Normal conditions assumed: no lag, no unloaded chunks, no weather, no world border, no mobs outside.

## Seamless tiers (section 2.1.4)
"Can't tell it's there from inside the hallway": no circuitry (and for the top tier no entities) visible in the hallway. The tier is
decided by which of these states/operations obey it: front side of closed door blocks; opened; closed; during opening; during closing.
1 SUPER, 2 FULL, 3 SEMI, 4 QUART. (The tier table's check marks didn't survive text extraction; SUPER is presumably all five, including
motion. Read the tier table from a screenshot before claiming a tier.)
DENTLESS / MINOR DENTS ONLY: extra restrictions on protrusions and recessions in the hallway. Flush: door face level with the outer
surface and all circuitry behind it.

## Misc restrictions
NOT LOCATIONAL // DIRECTIONAL (works at any location / facing), LOCATIONAL WITH FIXES, UP-TO-DATE. A speed claimed as not-locational must hold
everywhere (section 7).

## Volume (4.2)
W*H*D of the circuitry's bounding box, measured CUMULATIVELY across every opening/closing operation and both stable states (the box
anything ever occupies). Blocks and entities both count. Excluded: the door frame, the input device, anything inside the hallway except in
the open state. Circuitry ignores door/outer-surface/hallway blocks that fit the type. Ties go to the earliest date.

## Speed (4.3.1), measured in game ticks with REPEATER input, in priority order
1 OPENING TIME: input -> end of the last block movement that makes the hallway match the opened pattern.
2 OPENING VISIBLE (SEAMLESS) TIME: input -> last visible block movement inside the hallway (z-fighting counts).
3 CLOSING TIME: input -> last door-block movement.
4 CLOSING VISIBLE TIME.
5/6 OPENING/CLOSING RESET TIME: end of visible time -> earliest moment it can properly be toggled again (negative allowed).
BLOCK MOTION: a game tick in which at least one door block moves inside the hallway.

## Harness implications
- Per-tick hallway observation, including moving_piston: gives times 1-4 and checks seamless-during-motion.
- Input: a lever/button device with a real repeater-driven input test, plus a player-input check (a player can't be scripted in vanilla;
  find out how MC-172213 differs and whether a command can emulate it).
- Cumulative bounding box of every non-air change during the tests, minus frame, input and hallway.
- Location tests at several plot origins or chunk offsets, and rotation to all 4 facings, to back a "not locational/directional" claim.
- Reset time: toggle again at increasing offsets after opening and find the earliest that still works.

## Seamless tier table (from user's screenshot of Door Rules doc, 2026-09-30)
Seamless = matches the <type>'s hallway composition: no circuitry visible inside the hallway.
Cell legend: L = no circuitry AND no entities visible in hallway; D = no circuitry visible; - = no requirement.

| tier  | front side of closed door blocks | when opened | when closed | during opening | during closing |
|-------|---|---|---|---|---|
| SUPER | L | L | L | L | L |
| FULL  | L | L | L | - | - |
| SEMI  | D | D | - | - | - |
| QUART | D | - | - | - | - |
Note: some tiers incompatible with some types (e.g. QUART with GLASS / HIDDEN SAND / HIDDEN LAMP).
Harness implication: FULL needs per-state checks of the static open/closed hallways plus the front face; only SUPER constrains motion (moving_piston / entities visible mid-transition).
