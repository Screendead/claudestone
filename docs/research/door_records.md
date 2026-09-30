# Piston door records research (seamless-first)

Legend: [R] = read from the cited page (via WebFetch/WebSearch summary, which is an LLM summary, not verbatim); [I] = my inference, not read. 
GAP WARNING: I could NOT reach the canonical modern record list. The Scribd "Minecraft Piston Door Regulations" doc (https://www.scribd.com/document/820662283/Rule) failed to load; YouTube and forums.redstoner.com (DNS failure) were unfetchable; Discord servers are not searchable. Most concrete records below are 2016-2018 Redstoner-era or recent unverified community posts. Treat as leads, not a current leaderboard.

## 1. Definitions and how records are kept

Terms (all from search-result snippets, not from a rulebook I could read):
- Flush: door is flat with the surrounding wall. Seamless: when open, no redstone components (pistons, torches) are visible. [R] https://www.minecraftforum.net/forums/minecraft-java-edition/redstone-discussion-and/340566-2x2-seamless-flush-piston-door-tutorial and https://www.planetminecraft.com/project/2x3-flush-seamless-piston-door/ (search snippet)
- Seamless, stricter wording: "no circuitry visible inside the hallway in the opened state". [R, snippet] via Scribd rules doc search result https://www.scribd.com/document/820662283/Rule (content itself not read; exact text unverified)
- Full flush: "door block retracted to any side other than the floor" [R, snippet; same Scribd source, unverified]. So: flush = door face level with wall; full-flush = door blocks can retract to a side (not only down), per that snippet.
- Category names seen in r/redstone-related results: "Smallest 4x4 Non-Seamless Cave Door", "Smallest 4x4 Flush Non-Seamless Cave Door", "Smallest 4x4 Full-Flush Non-Seamless Cave Door". [R, snippet] search result (reddit mirrors, no URL fetched); treat as unverified.
- Redstoner "World Record Door Plot" (Nov 2017): shelves = smallest seamless / fastest (bottom), smallest nonseamless / fastest (second), smallest "concept" doors (top: cave, funnel, nether portal); separate shelves for flush and hipster doors; double-category doors excluded except fastest/smallest + seamless. [R] https://redstoner.com/forums/threads/5260/
- 0-tick 3x3 challenge required doors "seamless from BOTH sides when closed"; scored by block count and cycle time. [R] https://redstoner.com/forums/threads/2953/
- The Redstoner records plot thread gave NO explicit definitions of seamless/flush and no measurement protocol. [R] https://redstoner.com/forums/threads/5260/
- 5x5 record post noted bottom half is "location-dependent and directional" and contains a contained slime block; the community discussion had terminology disputes about records. Implies locational/directional builds were posted as records but may be contested. [R] https://redstoner.com/forums/threads/5063/

NOT FOUND (do not assume): the timing unit and start/end events for open/close time; whether volume is bounding box (all posts quote dimensions like 9x4x15=540, which is consistent with bounding box [I]); input rules; the Discord/spreadsheet that maintains current records. r/redstone Discord invite exists (https://discord.com/invite/Qq2ubaZ) but I could not read it. Times in posts are quoted in seconds (0.6 s, 0.85 s) or ticks (3-tick cycle) [R].

## 2. Records found (seamless first)

Volume = blocks in bounding box as quoted by poster [I on definition]. Older records likely beaten; no current list retrieved.

Smallest seamless:
| Size | Volume | Holder | Date | Version | Source |
|---|---|---|---|---|---|
| 3x3 (0-tick, seamless both sides) | 297 (3-tick cycle) | HitzCritz | May 2016 | unknown | https://redstoner.com/forums/threads/2953/ |
| 3x3 | 56 | SacredRedstone | unknown | unknown | https://www.planetminecraft.com/project/minecraft-redstone-2x2-flush-and-seamless-piston-door/ area search snippet only; unverified, could not find primary |
| 4x4 | 117 | Wilux | 2017-12-06 | unknown | https://forums.redstoner.com/threads/5437/ (listed at https://redstoner.com/forums/2/) |
| 4x4 vault door | 105 (beat 159/160 by abh 37) | unknown | unknown | unknown | search snippet only, no URL fetched; unverified |
| 5x5 (no observers) | 540 (9x4x15) | BrubriRedstone + Jonny__ | 2017-08-03 | unknown | https://redstoner.com/forums/threads/5063/ |
| 6x6 | 460 / 480 / 520 | SacredRedstone+Roudone+Wilux / same / error0x00000000 | Nov 2017 | unknown | https://redstoner.com/forums/threads/5260/ |
| 7x7 | 550 / 756 | SacredRedstone group / SacredRedstone | Nov 2017 | unknown | same |
| 8x8 | 648 / 672 / 870 | SacredRedstone group / group / SacredRedstone | Nov 2017 | unknown | same |
| 9x9 | 754 / 780 / 930 | SacredRedstone group / BrubriRedstone+Burgerlover1 / Brubri+Ralp+Burgerlover1 | Nov 2017 | unknown | same |
| 9x9 observerless | listed as "smallest" | Essentuan | 2018-01-05 | unknown | https://forums.redstoner.com/threads/5507/ (title only, via listing) |
| 11x8 | "worlds smallest" tiny seamless | BPhineas | 2018-02-03 | unknown | https://forums.redstoner.com/threads/5551/ (title only) |
(The multiple values per size in the Nov 2017 table are separate shelf entries, presumably per sub-category; meaning of each not stated [I].)

Fastest seamless:
| Size | Time | Holder | Date | Source |
|---|---|---|---|---|
| 5x5 "Thunderbolt" | opens in 0.6 s | Alugia7 | 2018-03-19 | https://forums.redstoner.com/threads/5612/ (title via https://redstoner.com/forums/2/) |
| 7x7 | "Fastest Seamless 7x7" (time not retrieved) | Alugia7 | 2018-05-20 | https://forums.redstoner.com/threads/5687/ (title only) |
| 5x5, 715 blocks | 0.85 s | unknown | unknown | https://www.youtube.com/watch?v=eVy2hLuMiSg (title only) |
| 5x5 slimeless, 540 blocks | 1 s | unknown | unknown | https://www.youtube.com/watch?v=qKYv33Rt71s (title only) |
No 2x2 seamless record numbers found. No 2020s fastest-seamless numbers found.

Flush / other context (brief):
- 3x3 flush "fastest" claim: 0.3 s opening, instant close (search snippet of https://www.youtube.com/watch?v=bH0lCFUbPoU; video not readable, holder/date/version unknown).
- Non-seamless fastest 3x3, 0-tick: 192 blocks, EatPineaplePizza and Jonny, April 2016. [R] https://redstoner.com/forums/threads/2953/
- 4x4 glass door smallest: DaichiCZ 2018-09-16 (https://forums.redstoner.com/threads/5825/, title only).
- Smallest 5x5 funnel: 330 blocks, VoodooCraft & Brubri, 2017-10-15 (https://forums.redstoner.com/threads/5288/, title only). 12x12 full-flush hidden nether portal, BPhineas 2017-10-04 (https://forums.redstoner.com/threads/5264/, title only).
- Recent unverified claims: 32-volume 3x3 door by TheredstonegamerYT, 2025-11-07, poster himself unsure of rules and unclear if seamless/flush https://www.minenest.com/590071/ ; 49-block "flush" 3x3, 1x8x7, Java 1.21.11, MineSchematic, 2026-01-27 (uses observers and sticky pistons; "one of the smallest" claim) https://mineschematic.com/s/tiny-3x3-piston-door-f5336481 . Neither is an accepted record [I].

Adjacent (not door-record) Guinness records exist for build speed of a two-block piston door (7.86 s, Seungbin Kim, 2022-02-02): https://www.guinnessworldrecords.com/world-records/379914-%E2%80%8Bfastest-time-to-build-a-two-block-piston-door . Irrelevant to design records.

## 3. Techniques (seamless-relevant)

0-tick pulse / block dropping. A signal that turns on and off within the same game tick. Sticky piston receiving a 1- or 2-tick pulse starts extending and then, on the depower, drops its block and retracts; with a 0-tick pulse the sticky piston "instantly drops its block and starts retracting". This is what leaves the moved block in the extended position with the head gone, i.e. the mechanism for hiding the pulling hardware behind a seamless door. [R] https://minecraft.wiki/w/Tutorial:Zero-ticking and https://technical-minecraft.fandom.com/wiki/0-tick_pulses?oldid=4974 (snippet; page returned 402 on fetch). Wiki wording: sticky pistons drop block, non-sticky don't "teleport" blocks.
Generating one: (a) tile-tick priority: comparators update after repeaters within a tick; power a line via repeater and cut it with a comparator-driven piston, so the pulse ends in the same tick. (b) budded pistons: when input depowers, the directly-powered piston retracts first and its update depowers the next piston in the chain, ending the pulse the same tick. [R] https://minecraft.wiki/w/Tutorial:Zero-ticking
Ordering claim: block updates are processed one at a time in a fixed order even inside one game tick; repeaters and comparators react late, comparators after repeaters. [R] search snippet summarising the technical-minecraft wiki page above. Detailed ordering rules for pistons (block events vs. scheduled ticks) were not retrieved [gap].

Observer chains / instant wire / double-triple extenders / self-closing / BUD / locational tricks: I did not find a source explaining how the seamless records use these. Mentions only: observers appear in flush 3x3 49-block build (mineschematic link above); "no observers" is called out as a notable feature of the 540-block 5x5 (https://redstoner.com/forums/threads/5063/); 4x4 vault and 5x5 designs use minecart-with-chest (4 carts) for signalling in the 540 block 5x5 [R] same. Quasi-connectivity (pistons powered from the block above the piston) is Java-only [R] https://minecraft.wiki/w/Tutorial:Quasi-connectivity (snippet). Everything else in the request under this heading: NOT SOURCED. [I] Seamless door hiding likely relies on pistons pulling door blocks flush into a wall and the drop leaving no exposed head, but this is inference.

## 4. Version sensitivity

- 0-tick mechanism itself: bug MC-8328, "remains unfixed in current Java Edition" per wiki. Zero-tick plant farming was patched (accidentally in 18w06a, officially in 20w12a before 1.16) but that does not affect piston 0-tick pulses. [R] https://minecraft.wiki/w/Tutorial:Zero-ticking . (MC-8328's own bug page not checked; date of the wiki content unknown, so "current" may lag 26.x [I].)
- Java start delay of pistons is 0-1 ticks; Bedrock has fixed 2-tick delay (so Java 0-tick designs do not port). [R] https://minecraft.wiki/w/Piston . Bedrock has no quasi-connectivity/0-tick parity request: https://feedback.minecraft.net/hc/en-us/community/posts/360048276432--Java-Parity-Zero-Tick-Pistons (title only).
- Piston hardness 0.5 -> 1.5 in 1.16 (not relevant to timing). [R] https://minecraft.wiki/w/Piston
- Redstone wire update-order changes: snapshot 24w33a made wire only update blocks that can receive power from it, which broke some quasi-connectivity-dependent piston activation; controversial, 1.21.2 shipped a performance rework of redstone wire that changed update order around wires. [R, snippet] https://feedback.minecraft.net/hc/en-us/community/posts/28929729298317-Let-s-talk-about-Redstone-Java-Snapshot-24w33a and https://minecraft.fandom.com/wiki/Java_Edition_1.21 . Doors that used wire + quasi-connectivity or that relied on wire update order pre-1.21.2 may need re-verification [I]. I did not confirm whether 24w33a's change was kept in 1.21.2 in the same form; I did not find any 26.x piston-specific change [gap].
- Old (2016-2018) records predate all of this; whether they still function on current versions is untested here [I].

## Suggested next steps to close the gaps
- Get the Scribd rules text by browser (mcp claude-in-chrome) and the Discord/records sheet; try r/redstone wiki and YouTube descriptions of channels that post door records.
- Fetch minecraft.wiki Tutorial:Quasi-connectivity, Java Edition 1.21.2 and 24w33a changelogs directly to confirm redstone-wire update-order change.

---
# Ruleset (primary source: Scribd doc 820662283)
Bedrock community ruleset, stated to be adapted from **Redstone Squid's Records Catalogue** (the Java piston-door ruleset; a Discord server, records not public on the web). Chinese sections translated by me.

Door: on (de)activation either seals the entire hallway with door blocks, or removes all door blocks from it. Hallway horizontal or vertical.

Record eligibility:
- Input: exactly one input device, lever OR button; outside the door volume, mounted on a fixed block inside the volume. Seamless: input device may not sit on frame blocks.
- Stable at all times: works at any game time; works after reload (chunk/world reload).
- Finite run time; unlimited uses. Wireless (sculk etc.) only if the player can walk through and nothing outside the volume affects it; must work in latest version.
- No reliance on "malicious features" (exploits; term untranslated).
- Closed: no circuitry exposed in the hallway or door face.

Titles: Smallest (volume; earliest to reach wins ties) and Fastest.
- Volume = W*L*H of circuitry incl. layout, plus any outside blocks required to be air/quartz-like/immovable. Circuitry ignores door, outer-surface and hallway blocks that fit the type. (Reddit snippet: button/lever not counted; showcase input lines not counted.)
- Speed priority order: opening time, closing time, opening reset, closing reset, opening input delay, closing input delay.
  - Opening time: from closed, input activation -> last visual block movement inside the hallway.
  - Closing time: from opened, input activation -> last visual block movement inside the hallway.
  - Reset time: end of open/close time -> stable opened/closed state.
  - Input delay: activation -> start of open/close time.

Restrictions:
- Seamless: no circuitry visible inside the hallway in opened state.
- Semi flush: outer door layer flush with outer surface, circuitry behind surface or on/below floor. Full flush: all circuitry behind outer surface. Regular-type flush doors need a door block retracted to a side other than the floor.
- Wiring restrictions (separate record categories): observerless, observer-only, entityless, sticky-pistonless, gravity-blockless, RBO, TDO, etc.
- Stable state: remains in, or returns to at regular intervals, indefinitely until input. One interaction = one change of stable state.

Prior art: github.com/jogobeny/Minecraft-Piston-Door-... evolves 3x2 piston doors with an evolutionary algorithm (not read).
