export const meta = {
  name: 'constitution-audit',
  description: 'Audit Claudestone against CONSTITUTION.md: each owner brings one area into line in its own worktree and commits; nothing is only reported',
  whenToUse: 'Between waves, when no other worker edits the code: every few waves, or when the suite or the code has grown. Start laptop satellites sat1..sat4 first (the owners never start or stop servers). Args: {base: "<branch>", tag: "<short id, e.g. a1>"}.',
  phases: [{ title: 'Audit', detail: 'ten owners, one area each, fixing in their own worktree' }],
}
const base = (args && args.base) || 'master'
const tag = (args && args.tag) || 'a1'
const REPO = '$HOME/development/redstone-ai'
const ROOT = '$HOME/development/redstone-ai-worktrees'
const common = (name, server) => `
You are a senior owner at the studio making Claudestone: vanilla Minecraft 26.3 redstone builds designed in Python, tested tick by tick on headless servers over RCON, shipped as data packs. Read CONSTITUTION.md at the repo root first (if your base lacks it: git show constitution:CONSTITUTION.md). Its test rule, in Jack's words: "The owner's eye is the ultimate test. Do not over-rely on unit/e2e tests for quality. The eye is paramount. Tests bloat the repo, go stale, require maintenance, and rarely get pruned, leading to obscene CI times and choking the pipeline, thus reducing throughput anyway over time. Do not write tests as a crutch. Scrutinise new and existing tests when things change." Here the eye is the build working in the game; a spec's tick-by-tick tests guard what the eye cannot see (the tick an output changes, a 1 gt glitch, crosstalk between tiles, a door's times and volume) and are the build's proof, not a crutch. The global code rule: comments state constraints the code cannot show, and nothing else; an abstraction exists only to remove a repeated idea; notes and analysis stay out of tracked files unless they are a document someone asked for.

Your piece: bring one area into line with the constitution and that rule. You fix what you find and commit it; nothing is only reported. You are not reviewing anyone: you own this area's fitness now.

Set up, with the Bash sandbox disabled for the worktree command: cd ${REPO} && git worktree add -b audit/${name} ${ROOT}/${name} ${base}. Work only in ${ROOT}/${name}. There: ln -s ${REPO}/server server (gitignored servers, locks and showroom are shared; the symlink is excluded, never stage it), and run Python as ${REPO}/.venv/bin/python from the worktree root, so redstone imports from your worktree. Commit as you go with plain messages (no attribution, no model names), staging files by path; the pre-commit hook lints staged specs and checks library/INDEX.md (regenerate with python -m scripts.index --tracked and stage it with spec changes). Do not push. Do not edit CONSTITUTION.md, HANDOFF.md, docs/WINS.md, the two untracked specs in the main folder, or Jack's quoted words. Generated library files change only through scripts/generate.py, then python -m scripts.generate. tests/test_harness.py::test_every_building_block_folder_has_a_plot already fails on the base (archive folders without plots): leave it. Other owners audit other areas at the same time: stay in yours.

Servers: never start, stop or restart a server, satellite or the watch director. For any test that needs a server, set REDSTONE_SERVER=${server} REDSTONE_WATCH=0 REDSTONE_OWNER=${name}; if it is down, say so in the hand-in and prove with offline checks instead. Never touch a Docker satellite (the desktop is off). Trash, never rm.

Behaviour must not change. Prove it the cheapest way that could fail: python -m scripts.lint on specs you touched; the offline tests that touch your area (pytest tests/<file> -q, never the whole of tests/test_generated.py unless you changed a generator); and for harness or build code, a few library specs whose tests exercise the lines you changed (pytest "tests/test_library.py::test_spec[<spec>::<test>]").

Hand-in (at most 150 words): what you removed or changed and why, in numbers (tests, lines, seconds before and after), anything you judged should stay against first appearance and why, commit ids.
`
const testOwner = (files) => `YOUR AREA: these offline test files in tests/: ${files}. Time them first (pytest <files> -q --durations=0; note the count and total seconds). For each test decide: does it guard something the eye cannot see and that would be costly to break unnoticed (a harness rule such as RCON sequencing, the lock order or sprint landing; a trait the library claims; the file format round-trip; a generated file being current; a door measurement)? Keep those, made fast. Delete tests that only prove a piece was done, pin today's numbers, duplicate another test, or are stale; merge near-duplicates; cut the cost of slow ones (check a sample or one generator instead of regenerating everything, a smaller input) without losing what they guard. Helpers and fixtures used only by deleted tests go too. Report the before and after count and seconds of your files.`
const libraryOwner = (folders) => `YOUR AREA: the tests declared in these library folders' specs (library/<folder>/*.redstone.yaml): ${folders}. Time them first, on your server, in one run: pytest -q --durations=0 with the ids test_spec[<spec>::<test>] of your folders' specs (python -m scripts.retest <plot>... runs a plot's specs). Note the count and total seconds. Then, per spec: keep each test that would catch a real break the eye cannot see; delete or merge a test that repeats another's case, shorten waits and settles far longer than the behaviour needs, and drop expectations that pin a number nothing depends on. Constraints: a tile test backs the tileable or stackable trait; a mechanics/ spec backs its entry in docs/MECHANICS.md and keeps the test that proves it; a ref_* spec and any spec named in docs/WINS.md keep the tests behind its numbers; door_cycle bounds are measurements. Never weaken a test to make it pass: a test that fails on the base is reported with its id, not edited. Rerun only the specs you changed. Report the before and after count and seconds of your folders.`
const codeOwner = (area) => `YOUR AREA: ${area}. Read every file. Remove comments that narrate, restate the code, record history ("was", "before", "now", "used to", dates, who asked), or hold analysis; keep and sharpen those stating a constraint the code cannot show (many here do: a vanilla quirk, an RCON or tick-rate limit, a lock order). Remove dead code (unused functions, parameters, flags, constants, branches no caller reaches: prove with a search across redstone/, scripts/, tests/, docs/ and CLAUDE.md, since commands are run by name) and abstractions that wrap one use. Leave formatting alone; do not rename for taste. If CLAUDE.md describes code you change, make it match.`
const parts = {
  [`${tag}-tests-harness`]: [testOwner('test_harness, test_rcon, test_remote, test_docker_sats, test_spec_offline, test_retest, test_showroom, test_watch, test_status, test_jobs, test_remote_run, test_remote_keep, and conftest.py (shared: keep what test_library.py needs)'), 'sat4'],
  [`${tag}-tests-design`]: [testOwner('test_generated, test_lint, test_traits, test_devices, test_circuits, test_door, test_door_probe, test_door_timing, test_door_volume, test_rotate, and test_library.py\'s test_loads'), 'sat4'],
  [`${tag}-lib-logic`]: [libraryOwner('and, nand, nor, not, or, xor, xnor, mux, demux, binary_decoder, encoder, half_adder, full_adder, magnitude_comparator, alu, accumulator, barrel_shifter, bcd, bcd_to_7seg, bin_to_bcd, seven_segment, sqrt, randomiser, sorter'), 'sat1'],
  [`${tag}-lib-seq`]: [libraryOwner('clock, counter, d_flip_flop, d_latch, rs_latch, t_flip_flop, register, shift_register, delay, dual_edge, falling_edge, rising_edge, pulse_extender, pulse_limiter, crossing, wire, vertical_wire, signal_strength, input'), 'sat2'],
  [`${tag}-lib-builds`]: [libraryOwner('mechanics, builds, door, cpu, cpu_parts, storage, survival, dice_roller, doorbell_jingle, hex_combination_lock, reaction_timer'), 'sat3'],
  [`${tag}-core`]: [codeOwner('redstone/build.py, fileformat.py, harness.py, spec.py, library.py, traits.py, plots.py, showroom.py, watch.py'), 'sat4'],
  [`${tag}-servers`]: [codeOwner('redstone/rcon.py, servers.py, docker_sats.py, remote.py, and docker/ (the satellite image)'), 'sat4'],
  [`${tag}-design`]: [codeOwner('redstone/door.py, door_probe.py, door_timing.py, door_volume.py, circuits.py, pla.py, route.py, devices.py, rotate.py, entity_dims.py, out_display.py'), 'sat4'],
  [`${tag}-scripts`]: [codeOwner('scripts/*.py and vscode-redstone/src and vscode-redstone/test (prove the extension with npm run build and npm test there; never commit its out/, dist/ or .vsix)'), 'sat4'],
  [`${tag}-docs`]: [`YOUR AREA: unused scripts, traces and the documents. Delete scripts in scripts/ that nothing runs any more (search redstone/, scripts/, tests/, docs/, CLAUDE.md, githooks/ and docker/ for callers; a one-off search whose result is already in a spec or doc is history, not a caller; a generator that scripts/generate.py imports is a caller). Make the trace writer and docs agree: CLAUDE.md, docs/AUTHORING.md, docs/MECHANICS.md, README.md and vscode-redstone/README.md must match the code and the library (fix or cut what is wrong; every MECHANICS.md entry names a spec that exists). Cut repeated or stale material where git holds the history. Do not rewrite decisions, research notes in docs/research, records, or Jack's quotes.`, 'sat4'],
}
const picks = {
  // Opus: deciding which tests guard real risk is judgement a plausible wrong deletion would hide; medium: one bounded list each.
  [`${tag}-tests-harness`]: ['opus', 'medium'],
  [`${tag}-tests-design`]: ['opus', 'medium'],
  // Opus: pruning a spec's tests can drop the one case that catches a timing break, and nothing would flag it; medium: many specs, each small.
  [`${tag}-lib-logic`]: ['opus', 'medium'],
  [`${tag}-lib-seq`]: ['opus', 'medium'],
  [`${tag}-lib-builds`]: ['opus', 'medium'],
  // Opus: harness and RCON code where a removed line can break lock order or tick landing without an offline test failing; medium: bounded files.
  [`${tag}-core`]: ['opus', 'medium'],
  [`${tag}-servers`]: ['opus', 'medium'],
  // Sonnet: comment and dead-code removal here is checked by the door and generator tests and a search; medium: many files.
  [`${tag}-design`]: ['sonnet', 'medium'],
  [`${tag}-scripts`]: ['sonnet', 'medium'],
  // Sonnet: unused scripts and stale docs are found by searching and checked against the code; medium: broad but shallow.
  [`${tag}-docs`]: ['sonnet', 'medium'],
}
phase('Audit')
const results = await parallel(Object.keys(parts).map(name => () =>
  agent(common(name, parts[name][1]) + parts[name][0], { label: name, phase: 'Audit', model: picks[name][0], effort: picks[name][1] })
    .then(r => ({ name, branch: `audit/${name}`, report: r }))))
return results.filter(Boolean)
