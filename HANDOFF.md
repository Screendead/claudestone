# Handoff — Claudestone

*Updated 2026-09-30. Audience: the next agent, or Jack. This file holds the current task: the plan, where it stands,
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
| Target | The plain "Fastest Seamless 3x3" (JensundLars & Sirrcacti, 2023-02-21: 0.15 s open, instant close, 3762 blocks) has no newer plain entry. Checked in Squid's `#record-logs` (2026-09-30, "fastest 3x3" and "seamless 3x3", two pages each). Nearest: BloxxDev/Kiwii semi-seamless funnel (0.15 s, 2025-10), nanda meow glass (0.1 s open, 2026-04). Which seamless tier the target holds is unconfirmed |
| Seamless tiers | From Squid's Door Rules doc. Checked states: front, opened, closed, during opening, during closing. L = no circuitry and no entities visible in the hallway; D = no circuitry visible. SUPER: L in all five. FULL: L front/opened/closed. SEMI: D front/opened. QUART: D front only, and not allowed with GLASS, HIDDEN SAND or HIDDEN LAMP. Only SUPER constrains motion |
| Door mechanics | Researched from the 26.3 source: tick phase order, piston extend lands at E+2 and retract at R+2, sticky piston spits on a pulse of 2 gt or less, no retraction under 2 gt, `redstone_experiments` off (old dust update order), neighbour order W, E, D, U, N, S |
| Open question | Records log 3x3s opening in 3 gt; the planner (exhaustive search, lower bounds) says 5 gt under either crediting reading. 3 gt is exactly when the frame first holds no door block, the last blocks still moving in the walls. Likeliest (H1, inferred): Squid's opening time ends when the last door block *leaves* the frame, not when it lands; it also explains a 2x2 logged "open instant". Settled from sources: "etho" is a 3x3 without its centre (so the 2 gt glass etho isn't a counterexample), and Squid re-based its times by 1 gt around 2021. Jack to ask the Squid mods: does opening end when the last block leaves the frame or when it lands, and the Feb 2023 entry's version, tier and world link. First spec: `pull_origin_air_at_event`. See `docs/research/door_gap.md` |
| Door harness | Offline modules done 2026-09-30, reviewed, 111 tests pass: `redstone/door_timing.py` (open/close times, stable-state detection, seamless tier), `door_volume.py`, `entity_dims.py` (+ `scripts/entity_dims.py`), `rotate.py`, `door_probe.py`. Opening time currently ends when the last block *lands*, per the rule text; it must also offer "leaves the frame" until the Squid mods answer (see Open question). Next: integration with the Rig, mechanics specs from `docs/research/door_gap.md`, a shakedown door (R9), 2x2 fallbacks |
| Harness fixes | Six batches from the wave 1 journal: batches 1–3 done (`ripple_adder_2bit` moved to `library/builds/`, a `SIGNALS` table replaced `signal_property`, a failing `run` now fails its test); 4–6 (truth-table vocabulary, spec shape, AUTHORING) running, then the full suite and `python -m scripts.index` |
| Library | 328 specs in 36 folders; 75 verified 26.3 mechanics in `library/mechanics/`, catalogued in `docs/MECHANICS.md` |
| `lightless` trait | Wrong, per Jack (2026-09-30). It should mean "queues no light checks", and its block list misses daylight detectors, lecterns, sculk shriekers, piston heads, shelves, furnaces and more. `inverted_daylight_detector_constant` violates it; `analog_const_lectern` does in real use. Dust does not: measured light 0 at power 15 on 26.3, and its states queue no checks. Fix queued after the harness fixes, with a `dust_emits_no_light` spec and a `perf`-counted light-update spec |
| Satellites | Six on the laptop today. Moving to Docker on Jack's Windows desktop (WSL2, reached over SSH, RCON through SSH tunnels, containers bound to localhost), laptop as fallback. Image `redstone-satellite:26.3` built and measured 2026-09-30 (`docker/satellite/README.md`): about 5.9 s from `docker run` to working RCON, 0.7–0.8 GiB each under load, 6 at once is safe on the desktop's 12.5 GB VM. Harness backend not written: it needs an RCON-login readiness check (an open tunnel answers even with the container down), `docker cp` + `reload` for the data pack, and SSH connection reuse (each `docker --context desktop` call costs 1–1.5 s of handshake) |
| Git | 16 commits (2026-09-30 morning); about 100 changes since, uncommitted, waiting for the running work to finish green |
| GitHub | Public at https://github.com/Screendead/claudestone (Jack's call, 2026-09-30). Created empty; `origin` set; nothing pushed |
| Licence | MIT, copyright Jack Lusher 2026 (Jack's call, 2026-09-30): `LICENSE`, `vscode-redstone/LICENSE`, `pyproject.toml`. It can't cover Mojang's material (see "Thoughts") |
| README | Not written. Jack wants one; it can come after the first push (see "Queued") |

### The plan

1. Let the harness fixes finish green, then commit the backlog in logical chunks and push `master`.
2. Per-wave git worktrees sharing one `server/`; on-demand laptop satellites with idle stop and a template-world
   reset; the desktop Docker backend, preferred when reachable.
3. Fix `lightless` (definition, block list, measured check).
4. Door harness: integrate the offline modules, prove the door mechanics as specs, build the shakedown door.
5. Close the 3x3 opening-time gap, then design the door.

## Queued

- **README.** What it is (a sentence to a tested, paste-able build), a sample `.redstone.yaml`, the loop from
  `docs/AUTHORING.md`, packaging as a data pack, the VS Code extension, the seamless door goal, and the licence.
  Screenshots from the showroom would help; keep images small (WebP) or out of git.

- **Showreel.** A 60–90 s hype reel for the README, socials and Discord (Jack, 2026-09-30): original Csound music, no voiceover, captions; Remotion motion graphics, terminal scenes and trace animations from real repo data; Chunky renders (on the desktop) and a Replay Mod session Jack records. Draft being built in `showreel/`; rendered media and Mojang assets stay out of git.
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
