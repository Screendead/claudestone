# Handoff — Claudestone

*Updated 2026-11-21. Audience: the next agent, or Jack. This file holds the current task: the plan, where it stands,
open thoughts, and the options set aside. Update it when a step closes or a call is made. Git holds the history;
`CLAUDE.md` holds how the code works, `docs/AUTHORING.md` how to design a variant. The repo is public: personal and
account details go in `HANDOFF.private.md`, which is gitignored.*

## The current task: a record-breaking seamless piston door

North Star (Jack): make a world-record-breakingly fast X-by-X flush piston door in the smallest possible volume, and
actually achieve it, judged under the Redstone Squid Java ruleset. The harness already proves logic builds tick by
tick; doors need it to measure opening and closing times, volume and seamlessness the way Squid does.

### Where things stand

| Item | State |
|---|---|
| Target | The plain "Fastest Seamless 3x3" (JensundLars & Sirrcacti, 2023-02-21: 0.15 s open, instant close, 3762 blocks) has no newer plain entry. Checked in Squid's `#record-logs` (2026-09-30, "fastest 3x3" and "seamless 3x3", two pages each). Nearest: BloxxDev/Kiwii semi-seamless funnel (0.15 s, 2025-10), nanda meow glass (0.1 s open, 2026-04). Which seamless tier the target holds is unconfirmed. Goals (Jack, 2026-09-30): both at once, in parallel: (a) a 3x3 whose seamless time beats 6 gt (a real "Fastest" win if open stays 3 gt), and (b) a smaller build than 3762 blocks matching the plain record's 3 gt open / 6 gt seamless |
| Seamless tiers | From Squid's Door Rules doc. Checked states: front, opened, closed, during opening, during closing. L = no circuitry and no entities visible in the hallway; D = no circuitry visible. SUPER: L in all five. FULL: L front/opened/closed. SEMI: D front/opened. QUART: D front only, and not allowed with GLASS, HIDDEN SAND or HIDDEN LAMP. Only SUPER constrains motion |
| Door mechanics | Researched from the 26.3 source: tick phase order, piston extend lands at E+2 and retract at R+2, sticky piston spits on a pulse of 2 gt or less, no retraction under 2 gt, `redstone_experiments` off (old dust update order), neighbour order W, E, D, U, N, S |
| Timing reading | Settled (Jack, 2026-11-21): Squid is not asked; we assume the strictest reading, R (opening ends when the last piston lands, start + 2), and untiered "Seamless" is not assumed to mean FULL. So front (b) (design B, 3/6 in fewer than 3762 blocks) is dropped: under R it is 5/8. Front (a) stands: the slime schedule (scratchpad `door2/seam_verdict.md`) opens in 3 with seamless 3 (5/5 under R), in-model only, with no server run, closing or wiring. The "seamless ≥ 6" floor (seam_bound, verify_2 R3) still holds without slime. The Feb 2023 record's reset time, version and world stay unknown, and whether a seamless 16x16 can also hold the unrestricted Fastest title stays INFERRED. See `docs/research/door_gap.md` |
| Door progress | Design B / design_c opens in replay (a SUB6 slime schedule) in 1728 blocks against the record's 3762, with no close, reset or input. Door-parts workflow (2026-10-01): lever input `door_lever_sticky_input` and close primitive `door_close_spit_relay` pass; `door_relay_rearm` works only for horizontal relays (five F=up relays must be re-oriented); a button toggle within 8 added blocks was not found; close wave 1 is a dead end in design_c's geometry (no legal feed for P6 or T). A close-layout agent is working out whether that is local or structural (scratchpad `door2/close_layout/REPORT.md`). Four relaxation searches run on the desktop (`door2/remote_{MULTI,SLIME,DROP,OOP}_r7.log`; a result counts only with `memo_full=False depth_cut=0`) |
| Door harness | Wired into the Rig and on master (pushed f5206f2): `door:` section, lever or repeater input, `door_cycle` reporting R/H1/R1/visible times, seamless grade, tier and slab-scan volume, `update_pass: strict`, chunked build functions; the laptop holds a dsat's RCON turn while a test runs in its container. MEASURED: `ref_legden_fastest_10x10` passes on dsat3 and sat3, open 29 (visible 32), close 14, FULL, 13552. Later: `Build.rotated` (T13), an origin sweep, the reset search, and a player press |
| Largest door | Jack (2026-10-01): build a seamless 16x16 (one chunk), as fast as possible, beating at least one record. Squid `#record-logs` (read 2026-10-01): **Fastest 16x16 Piston Door**, NumpadInfinite 2022-02-14, open 180.55 s, close 9.25 s, 58x19x24 = 25,056 blocks (not seamless); **Smallest Fastest 16x16**, NumpadInfinite/Hi30/ytivarG 2022-11-26, 58x23x18 = 24,012, same times. No seamless 16x16 is logged; RMC Team's 2017 sand seamless 16x16 (8800 blocks) comes up in `#logs-discussion` but was never logged, and whether sand counts for NxN is disputed there. Whether a seamless door can also take the unrestricted Fastest title is INFERRED (the rules say only that each restriction combination is its own category); ask Squid. Banking (Jack, 2026-10-01): against Squid's logged numbers, since no Numpad world exists to rebuild. Order: (a) a working, measured seamless 16x16; (b) under 24,012 blocks; (c) speed toward the 12x12 record's 2.1 s. Needs the door harness (T6/T7/T3/T4, in progress) and a one-off `bigdoor` plot. Progress (2026-10-01 night): LegDen's 10x10 can't scale to 16 tall (a closed 16-tall column exceeds the 12-block push limit; COMPUTED); following Numpad's family (INFERRED from frames), door columns are pulled sideways by flying-machine shuttle bands. Tested on laptop satellites: `door16_carrier_segment`, `door16_engine_b` (the first flying machine proven on 26.3), `door16_shuttle_band` (fetches columns and pushes them back) and `door16_band_stack` (mirrored 2-row bands; a middle band stops by overflowing the push limit) `door16_band_kick` (middle bands come home on their own via an observer, note block and observer relay), `door16_band_close` (both halves return their columns in one trip and stop where the queues meet; needs at least 5 columns per half) and `door16_band_open` (a perpendicular store at the slot; open, rebuild and close end where they started). COMPUTED for 8 columns per half: about 28 planes deep, open about 228 s (slower than Numpad), close about 80 gt. Open: stacking the z-bands, the volume budget, open speed, the controller. Notes: scratchpad `bigdoor/` and `bigdoor/16/` (`PROGRESS.md`) |
| Harness | Done 2026-09-30/10-01 and pushed: Docker satellites on the desktop, tests run in the container; `scripts.remote_run`/`remote_keep`, and `scripts.jobs` (detached, resumable desktop jobs) with `scripts.status` (one screen); container test steps `insert`/`expect_items`/`throughput`; tests build in `plot_for`'s plot by default; `scripts.retest`; `REDSTONE_OWNER`; `Rcon.sequence`; the `githooks/pre-commit` lint and index check (`git config core.hooksPath githooks`); showroom places over-long containers in pieces. All non-main plots are 72x72 squares on one grid, `references`, `survival` and `storage` included. Camera: `/trigger watch_off`/`watch_on` in game and `scripts.watch poses`; the orbit swing was reverted (it jittered on the client) and Jack is opted out |
| Library | 400 specs in 38 folders; 84 in `library/mechanics/`, catalogued in `docs/MECHANICS.md`. New: 3 survival builds and 4 storage builds (no storage win: see each spec's description); storage round 2 is running, rebuilding each baseline as a `ref_*` spec first |
| `lightless` trait | Fixed on master (checked 2026-11-20): `redstone/traits.py` defines it as "queues no light checks" with the full block list (daylight detectors, lecterns, sculk shriekers, piston heads, shelves, furnaces, ...), `dust_emits_no_light` proves dust gives light 0 at power 15, and `tests/test_traits.py` passes. The `perf`-counted check is written (2026-11-21): a `light_checks` step (satellites only) and `light_checks_torch_not_dust` (a torch queues checks; a dust line and a repeater line none). Left: its first run on a satellite (Mac), then its `docs/MECHANICS.md` entry |
| Wins | 1 banked in `docs/WINS.md` (2026-10-01): the smallest 2 gt pulse limiter, `t2_a_qc_breaker`, volume 6 against the wiki circuit breaker's 9 (rebuilt as `ref_wiki_circuit_breaker`). Losses and ties: T6 XOR loses to the wiki's Basic Subtraction XOR (24 vs 32 blocks per bit); T4's 0 gt rising edge ties the Dust-cut RED; T3 lost |
| T8 RAM cell | `t8_c_v51` (2026-10-01): a tileable repeater-lock RAM bit at 51 blocks per bit, found by the lattice SAT sweep, verified in game (checkerboard crosstalk test). Not banked: it isn't box-shaped and its lines are diagonal staircases (whether the "cube" challenge allows that is a reading), and the 64 bar has no rebuilt reference. An agent is checking whether 51 is the floor (the sweep gave up on each config after 15 s) and whether a 4x4x3 = 48 box exists |
| Desktop | i9-9900K, Docker Desktop on WSL2 (14 CPUs, ~12.5 GB). Searches hold at most 12 CPUs (`REDSTONE_SEARCH_CPUS`). WSL updates itself and restarts Docker; `remote_keep`/`scripts.jobs` resume. The SSH login and IP stay out of git (`server/docker_host`); check `git log origin/master..HEAD -p` before each push |
| Git | Committed as work finishes. Every branch is pushed before a turn ends (Jack, 2026-11-20); master's new commits go to `wip/<name>`, never to master itself. Merging is Jack's |
| Usage | Jack's local caps (2026-10-01): stop background work at 62% weekly (cap 65%); no 5-hour cap |
| GitHub | Public at https://github.com/Screendead/claudestone (Jack's call, 2026-09-30) |
| Licence | MIT, copyright Jack Lusher 2026 (Jack's call, 2026-09-30): `LICENSE`, `vscode-redstone/LICENSE`, `pyproject.toml`. It can't cover Mojang's material (see "Thoughts") |
| README | Written (2026-10-02): what it is, the showreel still and links, what it claims and doesn't, trying it in Minecraft, what's built |

### The plan

1. Door: settle the close (local fix or a layout searched for open and close together), then reset and input, then
   wire the door harness modules into the Rig and build it in full on a satellite.
2. Largest seamless square door: finish the groundwork, show Jack the target and plan, then build a scalable panel
   module small before scaling N.
3. Keep banking strict wins (T8's floor, storage round 2's measured comparisons).
4. `lightless`: definition and block list fixed, `light_checks` step written; left, its first satellite run and the
   `docs/MECHANICS.md` entry.

## Calls

- **Ask Squid how they time and tier doors** (2026-11-21). Jack's answer, verbatim: "B · Assume the strictest reading".
  Acted on: front (b), the smaller 3x3 at the record's speed, is dropped; front (a), the faster 3x3, goes on, timed under R.

## Queued

- **Showreel.** A 60–90 s hype reel for the README, socials and Discord (Jack, 2026-09-30): original Csound music, no voiceover, captions; Remotion motion graphics, terminal scenes and trace animations from real repo data; Chunky renders (on the desktop) and a Replay Mod session Jack records. **On hold (Jack, 2026-09-30): no changes or work on the video until Jack says.** Draft 1 rendered 2026-09-30 (`showreel/out/draft.mp4`, 76.8 s, gitignored); Chunky and Replay shots are placeholder cards; open items in `showreel/README.md` and the storyboard. Rendered media and Mojang assets stay out of git.
- **CI.** A GitHub Actions workflow for the offline tests: not yet (Jack, 2026-09-30).

## Research

`docs/research/`, written 2026-09-30 by research agents. Each file marks what came from a source and what was inferred.

- `door_mechanics.md`: 26.3 piston and tick-order mechanics, from the decompiled source.
- `door_techniques.md`: how record doors are built, from public sources.
- `door_records.md`, `squid_records.md`, `squid_rules.md`: the Squid ruleset, seamless tiers and current records.
- `door_harness_design.md`: what the harness needs to measure doors (tasks T0–T18).
- `door_plan.md`: the plan from research to a record attempt.
- `door_gap.md`: why records open a 3x3 faster than the model allows, hypotheses H1–H5 and how to settle each.
- `light_updates.md`: every block that queues a light check, the `perf` method to count them, and the `lightless` audit.

## Rules for this repo

- Discord (Squid) is read-only for Claude: no messages, reactions, joins or invites; stop at any verification gate.
- No CAPTCHA bypass; Claude doesn't sign in for Jack.
- Don't commit anything from `server/` (the Minecraft jar, the world, the RCON password).
- Commits carry no attribution lines.

## Thoughts

- **Why MIT.** The point of the project is builds people paste into their worlds, and MIT lets anyone
  reuse the code and designs with only the notice kept. Alternatives: GPL-3.0 (as comtran-compiler) keeps
  derivatives open but is heavier for a data pack someone drops into a world; no licence (as Unstir) keeps rights
  but makes public reuse unlawful, which defeats a public library. MIT can't cover Mojang's material: the server jar
  stays out of git; `redstone/blocks.json` is generated from the jar's data reports (block ids and states), a
  small, factual list that community tools publish routinely. Inferred, not legal advice.
- **The commit email is public.** Every commit carries Jack's personal-domain email. Changing it later means
  rewriting history, so decide before the first push.

## Set aside, with reasons

These are recommendations against, not Jack's calls, unless the entry says so. Keep every entry: if one is picked
back up, note the date and why.

### R1 — Private repo (Jack's call, 2026-09-30)

Jack chose public: "that's the most fun".
