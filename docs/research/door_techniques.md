# Fast seamless piston doors: technique survey (2x2, 3x3, flush)

Written 2026-09-30 from public web sources plus the files already in this scratchpad. No servers, RCON or repo files were touched.

Labels:
- [source: X] means I read it in X. Web pages were read through WebFetch/WebSearch, which return an LLM summary, not the page text. Quotes from them may be paraphrased.
- [inferred] means my own reasoning. Each one names the test that would settle it.

Local paths below were in the research scratchpad and are not in the repo (the decompile is Mojang's code):
- `mc/src/`, `mc-src/`: the Vineflower decompile of 26.3 [source: findings-inputs.md:2]
- `wiki/`: cached minecraft.wiki pages
- `squid_repo/reference/Door_Rules.md`: the Squid Java ruleset

## 0. Headline

The records work at the floor that the engine allows [source: squid_records.md:5-19,29-30]:
- close in 0 gt
- open in 2 gt (0.1 s)

Both floors come straight out of the 26.3 piston code (sections 1 and 2). What separates record doors is the rest of the build:
- visible (seamless) time
- reset time
- volume
- category tricks: glass, carpet or TNT door blocks, and entities

No public page I could reach explains how a specific record door (JensundLars, nanda meow, Valle0t and others) is wired. The web part of this survey gives you mechanism and vocabulary, not blueprints.

## 1. How 0-tick (instant) closing works: block dropping

### Mechanism, from the 26.3 source

1. **Extension starts.** A powered piston queues block event 0 [source: mc/src/PistonBaseBlock.java:94-96]. When the event runs, `moveBlocks` replaces each pushed block with a `moving_piston` at its destination. Each one holds a `PistonMovingBlockEntity` with progress 0 [source: PistonBaseBlock.java:151-153, 294-306].
2. **Retraction starts.** If the piston loses power while `EXTENDED=true`, `checkIfExtend` looks at pos+2. That is the first pushed block's destination. The code picks event 2 instead of 1 when all of the following hold [source: PistonBaseBlock.java:98-110]:
   - pos+2 holds a `moving_piston` that is still extending in the same direction
   - and one of these is true: `progress < 0.5`, or it is the same game tick as that block entity's last tick, or `ServerLevel.isHandlingTick()`
3. **The block lands.** `triggerEvent` with event 1 or 2:
   - It calls `finalTick()` on the moving block directly in front of the piston [source: PistonBaseBlock.java:160-163].
   - For a sticky piston it also calls `finalTick()` on an extending moving block at pos+2 [source: PistonBaseBlock.java:175-184].
   - `finalTick()` sets progress to 1 and immediately runs `setBlockAndUpdate(movedState)` [source: mc-src/.../piston/PistonMovingBlockEntity.java:259-280].
   - Result: the pushed door block is placed in its final cell in the same tick, and the sticky piston does not pull it back. It only removes its head (`removeBlock`), because `b0 != 1` [source: PistonBaseBlock.java:187-191].
4. **When `isHandlingTick` is true.** It is set to true at the start of `ServerLevel.tick` and back to false right after `runBlockEvents()` [source: ServerLevel.java:361, 407-413]. So it covers scheduled block ticks, fluid ticks, random ticks and block events. It does not cover entities or block entities.

[inferred] Together these mean a depower that comes from redstone (repeater, comparator, observer or piston during those phases) always drops the block. A depower from a player action may not drop it once the block has been ticked once. Settle with a test: 1 gt and 2 gt pulses on a sticky piston pushing one block, driven by a repeater vs by a `setblock` lever toggle, logging the block state every tick.

### Public sources for the same behaviour

- The minecraft.wiki Sticky Piston page, "Block dropping" section, says [source: https://minecraft.wiki/w/Sticky_Piston]:
  - "A sticky piston finishes extending early and starts retracting if it loses power before the extension process is over."
  - "the first block ends up in its final position immediately and all the other blocks continue moving".
  - It is called "block dropping" or "block spitting", and it is Java-only.
  - History: added 1.7.3, removed in 17w49a, restored in 17w49b.
- The Zero-ticking tutorial says 0-tick pulses make sticky pistons "instantly drop their block and start retracting". Regular pistons "do not instantly teleport blocks". It exploits MC-8328, which "may be fixed at any time" [source: https://minecraft.wiki/w/Tutorial:Zero-ticking].
- r/redstone user VIBaJ: "Pistons take 2 gt to extend (unless block dropping for 1gt or 0 gt) and retract." [source: https://www.reddit.com/r/redstone/comments/1epku2k/can_anyone_explain/lhurih4/ via api.pullpush.io]

### The ruleset scores this as 0 gt

The timing section defines when a movement ends [source: squid_repo/reference/Door_Rules.md:622-630]:
- "0 to 2gt pulse extension: Starting time ... + Pulse length received"
- "Standard extension: ... + 2gt"
- "Instant retraction: Starting time"
- "Standard retraction: ... + 2gt"

So a door block placed by a 0-tick pulse counts as ending at its start time. That is why the logs show "Close 0 s" / "instant" [source: squid_records.md:5-19].

### Is the block already in place, or dropped?

Neither the public sources nor the logs say which one record doors use.

[inferred] Block dropping explains the whole 0 s closing time: the door block goes from air to solid in the input tick. The "closing visible time" of 0.25-0.4 s in the logs then comes from other visible movement after that tick, for example hallway, floor or wall blocks being restored, or hardware retracting behind glass [source for the numbers: squid_records.md:6,10,14-17].

Settle it by logging every hallway cell per tick in the harness while replicating a 2x2 flush door that uses dropped closing.

### Generating the 0-tick pulse

Two generator types are documented [source: https://minecraft.wiki/w/Tutorial:Zero-ticking]:
- **Tile-tick priority.** Comparators are processed after repeaters in the same tick. A repeater powers the line, and a comparator-driven piston removes the power source in the same tick.
- **Budded pistons.** A budded piston only retracts when it is updated, so update order depowers the line in the same tick. The example is "a redstone line that directly powers a sticky piston and bud-powers two other sticky pistons".

Community names for the circuits:
- **ABBA** circuits fire A then B on the rising edge and B then A on the falling edge [source: DearHRS, https://www.reddit.com/r/redstone/comments/1w1ofd6/design_help_wanted/p6rh9co/; bryan3737, /r/redstone/comments/1rs4e4r/help_with_block_switcher/oa5cuh2/; Griffoen0, /r/redstone/comments/1wilrb2/alternate_pistons/pabfnc8/, all via pullpush].
- **ABCCBA 0-tick generator**: named only, not explained [source: WiktorKw comment, pullpush search "0 tick seamless door"].

### Instant repeaters and wire

The wiki's instant repeater design [source: https://minecraft.wiki/w/Tutorial:Instant_repeaters]:
- A sticky piston holds a redstone block, above a powered block, with a second sticky piston diagonal to it.
- "This 0-ticks the top piston, effectively teleporting the redstone block". It emits two-redstone-tick pulses and can be chained.
- Listed use: "Zero-tick doors" to restore signal strength.

[inferred] Why a dropped redstone block can drive the next piston in the same tick: a dropped block is placed during the block-event phase (step 3 above), and a piston updated during the block-event phase starts in the same tick (section 2). So a chain of 0-ticked pistons can carry a signal with 0 gt per stage. A normally pushed block arrives in the block-entity phase, which adds 1 gt per stage, and the wiki says chains of those run 3 gt apart [source: wiki/p_Piston.txt:95]. Settle with a harness test of a 3-stage chain of 0-ticked redstone blocks, reading the game time at each piston's event.

## 2. How 2 gt opening works

**Start delay.** A Java piston's start delay is 0 or 1 gt [source: wiki/p_Piston.txt:85-95]:
- 0 if it is powered and updated during the scheduled-tick, random-tick or block-event phase
- 1 if it is powered during the entity or block-entity phase, or by player input

**Stroke length.** Extension and retraction each take 2 gt [source: wiki/p_Piston.txt:50,52]. In code, a moving block gains +0.5 progress per block-entity tick and is placed on the tick after it reaches 1.0 [source: PistonMovingBlockEntity.java:291-325].

**Result.** Repeater input → dust → sticky piston pulling the door block gives a standard retraction, start+2 gt = 0.1 s. That matches the 0.1 s openings in the logs:
- nanda meow 3x3 glass etho
- the Valle0t / Flattergaming / JensundLars 2x2 V2
- the Oct 2025 2x2
[source: squid_records.md:6,14,18]

Openings of 0.15 s (JensundLars/Sirrcacti plain 3x3) and 0.25 s mean at least one door block needs a second, chained move [inferred from the arithmetic above].

**Input bug.** The start-delay rule is what the community calls the "input bug" (MC-172213). A player-pressed button or lever acts outside the tick phases, so pistons it powers start 1 gt later [source: squid_rules.md:13-14; VIBaJ: "The 'input bug' doesn't make repeaters lose a tick, it makes pistons gain a tick", /r/redstone/comments/1epku2k/can_anyone_explain/lhmfhm5/; shutara_11, /r/redstone/comments/1rhvc7j/where_is_my_damn_2_gt_delay/o8ch2y5/; DearHRS, /r/redstone/comments/1u325tp/.../or1xjfx/, all via pullpush]. Records are timed with repeater input [source: Door_Rules.md:622]. The logs tag builds "input bug" or "no input bug" (ChemCN vs Valle0t) [source: squid_records.md:7,15].

[inferred] "No input bug" means the door has the same timing, or at least still works, under player input. Settle it by running every door test twice: repeater-driven input, and the harness's `setblock` lever toggle.

## 3. Fast input-to-piston lines

- **Dust.** Updates are instant within the phase that powers it [inferred, standard redstone behaviour]. A repeater input driving dust directly into the pistons gives 0 gt start delay. For the fastest opening, this is the only line that needs no extra tick.
- **Observers are not 0-delay in Java.** On an observed change the observer schedules a tick 2 gt later. At that tick it turns on and schedules its own turn-off 2 gt after that. So it has 2 gt latency and a 2 gt pulse [source: mc/src/ObserverBlock.java:42-50, 63-75; wiki/p_Observer.txt:49 "for 2 game ticks"]. An observer therefore cannot sit on the critical path of a 2 gt opening. The "observers only on even ticks" claim in a search summary is Bedrock behaviour [source: wiki/p_Observer.txt:51].
- **Observer 1-tick pulses and block dropping.** Short observer pulses are commonly used to make sticky pistons drop blocks [source: search-result snippet only, r/redstone; unverified].
- **Instant wire.** The old minecraft.wiki "Instant wire" page is a Beta-era glitch that is "now outdated" [source: https://minecraft.wiki/w/Tutorial:Instant_wire]. Modern instant lines are chains of 0-ticked pistons with redstone blocks (the instant repeaters in section 1).
- **Quasi-connectivity (QC).** Java pistons can be powered from the block above and can be left "budded" [source: wiki/p_Piston.txt:99-108; https://minecraft.wiki/w/Tutorial:Quasi-connectivity]. Budded pistons are one of the two documented 0-tick generator types (section 1). DardS8Br advises "learn how to better utilize observers, block dropping, and quasi" to compact doors [source: /r/redstone/comments/1dh832r/.../l8wiv38/ via pullpush].

## 4. How seamless is defined and judged

**Rule text:**
- Seamless means "no circuitry is visible inside the hallway". The tier depends on which of five states or operations obey that: front of the closed door, opened, closed, during opening, during closing. The top tier also forbids visible entities [source: Door_Rules.md:125-138].
- The tier check marks did not survive the export, so read them from the tier-table image before claiming a tier [source: squid_rules.md:23-24].
- "Visible block movement" includes z-fighting [source: Door_Rules.md:644-646].
- Opening visible time runs to "the last visible block movement from inside the hallway" [source: Door_Rules.md:644].
- The CLEAN restriction ignores "block teleportation" when counting motions [source: Door_Rules.md:248].

**What block dropping gives you for free.** [inferred] A dropped block shows no motion: it appears in its final cell (section 1). So dropped closing is automatically seamless during closing, as long as nothing else moves in view. That fits the near-universal "instant close" in fast seamless records.

**Glass, carpet and TNT categories.** These change the hallway composition [source: Door_Rules.md:89-109]:
- Glass door blocks are see-through, so hardware seen through them presumably counts as visible circuitry. That would explain why glass categories are separate [inferred; the rule text on see-through visibility was not found].
- Carpet requires a carpet on the floor, and TNT requires TNT door blocks and frame. So these are separate records, not techniques you can borrow for plain doors [source: Door_Rules.md:105-109].

**Not found:** any public explanation of how a specific record door hides its pistons during motion. The only example links are to Twitter (super seamless) and YouTube (1S5Lk-fAu9M at 633 s, quart seamless) [source: Door_Rules.md:133,136]. Neither could be read.

## 5. Typical 3x3 layouts

Only tutorial-tier material could be read.
- **SyntaxMine (26.2):** a 3x3 "is a two-stage machine". Stage 1 is slime-block double extenders ("a slime block behind a row of door blocks lets one piston push that whole row"). Stage 2 pushes the slime-and-block mass into a cavity, with a repeater delay of 2 ticks or more between stages [source: https://syntaxmine.com/articles/piston-doors-minecraft-1-21-4]. **Low trust:** the same page says an extension takes "0.15 second", which contradicts the wiki's 2 gt [wiki/p_Piston.txt:50].
- **minecraft.wiki piston uses page:** lists flush "Jeb doors" (full and half), a "Flush Seamless piston door" ("fully hidden, no pistons or redstone visible"), and "Smallest 3x3" by SacredRedstone at 56 blocks. Its "larger piston doors" section is marked missing [source: https://minecraft.wiki/w/Tutorial:Piston_uses].
- **"Etho" 3x3 layout:** a record category ("3x3 glass seamless etho") [source: squid_records.md:6,10]. **Not found:** any public description of which block goes where.
- **The centre-block problem.** [inferred] In a 3x3 door one block deep, the centre block has no neighbouring cell outside the hallway. It needs either two moves, or a push of the whole row (centre plus edge) into the wall. A single 2 gt opening therefore suggests something else:
  - the centre is removed by a piston behind the door plane that pulls it along the hallway axis into the wall (only possible if the door is set into a recess), or
  - a slime or honey carrier or a chained drop moves it.

  To settle, build a 3x3 in which each door block has its own sticky piston behind the door plane pulling it back, and check whether the hallway matches the opened pattern at 2 gt.

**Community lead:** Griffoen0 posted "0t 3x3 vault door (now seamless!!)", "Instant 3x3/4x4 vault door", "0t 5x5 instant vault" ("triple extender closing") and "Instant cave door 0t" [source: pullpush submissions: /r/redstone/comments/1udflyh, 1q5oy9c, 1q5uxn7, 1umv098, 1tssdi5]. The post dates from the pullpush summary are unreliable; the summariser converted the timestamps. The ABBA circuit is repeatedly recommended for sequencing double extenders without update conflicts (section 1).

## 6. Reset tricks

**Not found** in public sources.

What the logs show: reset times of 0.05 s (nanda meow), 6 gt (Oct 2025 2x2) and 0.25 s (Valle0t V2) [source: squid_records.md:6,14,18]. The rules allow negative reset times [source: squid_rules.md:42].

[inferred] Short resets need these to be idle again quickly:
- 0-tick generators (for example ABBA circuits that return to rest on the falling edge)
- any spent redstone blocks

Spam-proofing is an open community question: "How to make 0-tick piston door spam-proof?" [source: /r/redstone/comments/1w1gmvv via pullpush]. Settle with the harness reset sweep described in squid_rules.md:51.

## 7. "Smallest" doors with entities

What the logs show [source: squid_records.md:11,20-26]:
- Door_Maker and Kawediloru: 21 blocks with 9 mixed entities; 24 blocks with 7 entities and "NaN-motion carts"; 36 blocks with "copied-UUID chickens, non-ticking baby zombified piglins", locational at a chunk border.
- Valle0t V2 uses 3 boats.
- Pix: "crafter tech" with 2 entities.

Rules that shape these builds:
- Entities count toward volume, except hitbox parts at a floating position where a block could still be placed by hand [source: Door_Rules.md:571,579-583].
- NO ENTITIES is its own restriction [source: Door_Rules.md:297].
- Entities must be isolated from the hallway and the outside [source: Door_Rules.md:728-731].

Public explanations: **not found** for any of NaN motion, copied UUIDs, chunk-border non-ticking entities or crafter tech. Web searches for them return spam. Related oddities:
- A strider riding a strider in a minecart can power a pressure plate 2 blocks higher than an armor stand can [source: search snippet of r/redstone "it_took_5_whole_years", lr.ggtyler.dev mirror; not fetched].
- The minecart physics rework is still behind the Minecart Improvements experiment [source: wiki/je_1.21.2.txt:102].

[inferred] Entity doors lean on non-standard entity state, like NaN motion or not ticking. That kind of state is fragile across versions and hard to reproduce with plain `summon`, so it is a poor first target for this harness.

## 8. Version sensitivity

- **Redstone Experiments.** 24w33a added the wire update-order and performance rework as the opt-in "Redstone Experiments" data pack, not as default behaviour [source: wiki/s24w33a.txt:74,354-357; wiki/redexp.txt:1-30]. It shipped the same way in 1.21.2 [source: wiki/je_1.21.2.txt:102,384-392]. 24w34a made wire updates "left-first", no longer random [source: wiki/redexp.txt:32].
  - My grep of the 1.21.3 to 26.3 changelogs in `wiki/` found no promotion to default. That is absence of a hit, not a confirmation. The 26.3 piston code still calls `ExperimentalRedstoneUtils` [source: PistonMovingBlockEntity.java:22,276,311].
  - [inferred] Default worlds keep the old wire order, so doors from 2023-2026 keep working. Settle by running `datapack list` on the test world, which is for an agent allowed to use RCON.
- **door_records.md:71 is wrong.** It says 24w33a's change shipped as a default 1.21.2 change. It was experiment-only.
- **Block dropping** was removed in 17w49a and restored in 17w49b. Non-sticky pistons dropped blocks briefly in the 1.13 prereleases, and 18w30b ended that [source: https://minecraft.wiki/w/Sticky_Piston; wiki/p_Piston.txt:265-266].
- **MC-8328** (0-tick pulses) was unfixed as of the wiki pages read [source: https://minecraft.wiki/w/Tutorial:Zero-ticking; door_records.md:68].
- **Bedrock** has a fixed 2 gt piston start delay, no block dropping, no 0-tick and no QC, so none of these designs port [source: wiki/p_Piston.txt:97; DardS8Br, /r/redstone/comments/1d4p1sl/.../l9j7k42/].
- **Version tags on records:** Pix's door is 1.21+ with crafters; Valle0t V1 is 1.21.11 [source: squid_records.md:11,15]. The Space Walker tutorial is tagged "MC 1.13.2+" (see leads).

## 9. Leads (titles only; descriptions were unreadable because YouTube pages and invidious return no body)

- **Jjd2s6FOBro:** "[Tutorial] Fastest Seamless 3x3 Door | 0.3s Opening, Instant Closing | MC 1.13.2+", Space Walker [source: youtube oembed]. This is the one public tutorial of a fast seamless 3x3 with instant close. Best first thing to watch.
- **cqiAzko6b_U:** "[Quick RS] ZERO ticks to close 2x2 flush door", redinator2000 [source: youtube oembed].
- **M-psnTsrtqY:** "0-Tick Piston Doors Are Insane!", avogaado [source: youtube oembed].
- **bH0lCFUbPoU:** "(World Record) Fastest 3x3 Flush Piston Door!", 0k4a [source: youtube oembed]. door_records.md:50 quotes a snippet for it: 0.3 s open, instant close.
- **ECanDo, "2x2 Flush Seamless Piston Door":** 80 blocks, 6x3x7, opens in 10 ticks and closes in 9 [source: https://schemat.io/schematics/9CJe8w]. A slow baseline, and downloadable as .schem.
- **Reddit (via https://api.pullpush.io):** "3x3 0-tick flush piston door" (ALPHANono2008, /r/redstone/comments/1vzd7uf); "WR: Smallest seamless 3x3 checker door (112 blocks)" (no-liver, /comments/1u22l0i); Griffoen0's 0t vault series (section 5). The pullpush comment search is rate-limited (HTTP 429), so alugia7's comments are not retrieved. alugia7 is a former fastest-seamless record holder (door_records.md:43) and mentions "reuse of 0-tick gens" and "3-gt clocks".
- **Could not reach:** YouTube descriptions or search, reddit.com, old.reddit, redlib mirrors, the technical-minecraft fandom wiki (HTTP 402), and the minecraft.wiki pages Tutorial:Piston_door(s) and Tutorial:Double_piston_extender (404). Web search returns no results about the named record holders.
