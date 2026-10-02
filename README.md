# Claudestone

**Vanilla Minecraft redstone, designed by Claude agents, proven tick by tick on a real server, shipped as a data pack.**

<p align="center">
  <a href="https://github.com/Screendead/claudestone/releases/tag/v0.1"><img src="docs/media/showreel.jpg" width="800" alt="A frame from the showreel: the 16x16 piston door standing open, its coloured machinery either side of the doorway"></a>
</p>

<p align="center"><b><a href="https://github.com/Screendead/claudestone/releases/tag/v0.1">Watch the showreel (1:42)</a></b> · <b><a href="https://github.com/Screendead/claudestone/releases/tag/v0.1">Download the world</a></b></p>

> **From a sentence to a tested, paste-able build.** Claude agents design the redstone, a harness steps it one
> game tick at a time on an unmodified Minecraft Java 26.3 server, and only builds that pass ship, as a data pack
> that places exactly the blocks that were tested. Not a mod.

**What this claims, and what it doesn't.** These builds are not better, faster or smaller than what expert redstone
builders make. The claim is that Claude agents, with this repo as their harness, build things a novice couldn't,
on their own: they design, test and fix each build until it passes.

| At a glance (tracked files, 2026-10-02) | |
|---|---|
| **457** specs in **41** folders, every one with its own tests | [`library/INDEX.md`](library/INDEX.md) |
| **85** specs that each prove one 26.3 mechanic | [`docs/MECHANICS.md`](docs/MECHANICS.md) |
| **27** community designs rebuilt as `ref_*` specs, so comparisons are measured, not quoted | `library/*/ref_*` |
| **1** banked win over a community best, **1** tie | [`docs/WINS.md`](docs/WINS.md) |

## Try it in Minecraft

You need Minecraft Java Edition **26.3**.

- **The world.** Download `claudestone-world-26.3.zip` from the [release](https://github.com/Screendead/claudestone/releases/tag/v0.1),
  unzip it into your `saves` folder and open **Claudestone** in Singleplayer. It is the harness's own test world:
  you start beside the CPU, in creative with cheats on. Every plot north of you is a showroom of one building
  block, each variant under a green (passed) or red (failed) label.
  - **The CPU:** you spawn at its controls. Flip the east lever (START) and watch the display on the far
    (north-east) corner count 1, 1, 2, 3, 5, 8, 13.
  - **The door:** `/tp @s 418 70 255 180 0` puts you in front of it, and the lever is at `417 59 210`.
    It opens over about 7.7 minutes (9,234 game ticks), so `/tick rate 200` helps.
- **One build in your own world.** The release also has a data pack for each of `two_digit_adder`, `cpu_fib4`
  and `door16_quart_compact`. Put the zip in your world's `datapacks` folder, `/reload`, stand where the front
  should go, run `/function <name>:prepare`, wait a second, then `/function <name>:build`. It builds to your south.

## What's built

- **A 16x16 piston door** (`door16_quart_compact`, 96x30x45, 7,705 blocks). One lever opens it in 9,234 game ticks
  and closes it in 448. Slime-block flying machines carry the door's quartz out into stacks and bring it back.
  From the front no circuitry shows in the doorway (the Redstone Squid "QUART" grade). Its `door_cycle` test
  reads the hallway every tick of the cycle and times both moves.
- **A 4-bit CPU running Fibonacci** (`cpu_fib4`, 185x8x85, 16,210 blocks). A two-phase clock, a program counter,
  a 16-word lever ROM, a control decoder, an ALU, registers and a decimal display, each a tested library part.
  Its test runs the program and checks the display shows 1, 1, 2, 3, 5, 8, 13 before it halts.
- **A two-digit adder** from one sentence, below.

Still in progress: a 16x16 door that hides its circuitry in every state, and a 3x3 door with a full reset.

## A sentence, built and checked

<img src="docs/media/adder-sums.gif" width="400" align="right" alt="The two-digit adder's 7-segment lamps at each check of its test, from 0 to 18">

The sentence *"two numbers on levers, a button, the sum on a 7-segment display"*, built: `two_digit_adder`,
151x10x156, 14,893 blocks. `scripts/generate.py` places library parts (lever switches, encoders, a half adder and three full adders, latches, a decoder, two 7-segment
digits) and `redstone/route.py` routes the wires between them.

Its test flicks a lever in each row, presses the button and checks every lamp of the display, for every sum
from 0 + 0 to 9 + 9. The animation on the right is that test's trace: the lamps the server reported lit at each
of the 20 checks, one check per frame (stop-motion, not every tick).

<br clear="right">

## How it works

```
 sentence ──► generator (Python)  ──┐
              or hand-written YAML ─┴─► Spec ──► Rig on a headless 26.3 server ──► pass/fail + trace ──► data pack
                                       (.redstone.yaml)  setblock + clone,           every cell,          (dist/<name>.zip)
                                                         tick freeze / tick step     every tick
```

- **Spec** (`redstone/fileformat.py`). Layers keyed by y, a glyph palette, named inputs, outputs and cells,
  fixtures and reserved air, and tests: truth tables with exact delays, `glitch_free`, waves, `tile` tests for
  two copies, step lists (drive, use, wait, expect, wave, ...), container steps, and a `door_cycle` test that
  times a piston door the way the Redstone Squid rules do.
- **Rig** (`redstone/harness.py`). It clears a plot, places the build in two passes (`setblock`, then a `clone`
  of every block onto itself, because placement alone leaves stale states), freezes the tick and steps it. It
  reads block states through a generated probe function in one RCON round trip.
- **Servers.** One main world that players can watch, plus satellite servers (laptop processes and Docker
  containers) that run tests in parallel, one plot each. Every passing build is mirrored into a showroom on
  main, labelled green or red.
- **Traces.** Every run writes `traces/<spec>/<test>.json`; with `REDSTONE_TRACE=1` that is every signal
  cell on every tick:

![Timing diagram of the CPU's two-phase clock: COM and CAP pins, 10 gt pulses, 200 gt period, CAP 150 gt after COM](docs/media/cpu-clock.png)

<sub>The four output pins of `cpu_clock`, the first clock built for the 4-bit CPU (`library/cpu_parts/`), from a
full trace. A two-phase clock is what lets the CPU's master/slave registers work: on CAP every master captures its
next value, on COM every slave commits it, so no register reads a value that is still changing.</sub>

## The rule: measured, or it isn't claimed

The wins ledger (`docs/WINS.md`) counts a result as a win only if the community design has been **rebuilt and
passes on our server**, both are measured **under one convention**, ours is **strictly better**, and a fresh
search finds **nothing better**. Every figure is marked SOURCED, MEASURED or INFERRED.

| | Ours | Theirs | Result |
|---|---|---|---|
| 2 gt pulse limiter | `t2_a_qc_breaker`, volume **6** | Minecraft Wiki circuit breaker, volume 9 (`ref_wiki_circuit_breaker`) | **Win** (2026-10-01): same measured behaviour, 6 < 9. Scoped to a 2 gt delay; Java only (quasi-connectivity) |
| 0 gt rising-edge detector | `pulse_rising_instant_piston`, 15 | Wiki dust-cut RED, 15 (`ref_wiki_dust_cut_red`) | **Tie**: the same circuit |
| XOR, edge detectors, T3 | | | Refereed, **no win** |

## From the agents' logs

Real lines from the Claude agents' session transcripts, quoted verbatim:

> "The datapack route works. The lamp is dark because of the ordering trap I expected: the lamp was placed after
> the torch, so it never got an update."
>
> — a Claude agent, on the first build (this is why every build is placed in two passes)

> "Everything passing first time makes me suspicious, so I'll run mutation checks: break each key mechanism and
> confirm the test catches it."
>
> — a Claude agent, writing mechanics specs

> "LegDen's door works on 26.3, but only when every block is placed strictly."
>
> — a Claude agent, which led to `update_pass: strict`

> "Found it: the Squid record log has a plain **Fastest 16x16 Piston Door** record (Numpad, 2022: 180.55 s to open,
> 9.25 s to close) and no seamless 16x16 record at all."
>
> — a Claude agent, picking the next target

> "The T2 check came back as a win: all four ledger criteria are met, as long as the claim is limited to a 2 gt
> delay."
>
> — a Claude agent, banking the pulse limiter

## Quick start

You need Python 3.12+, Java 25+ and a Minecraft Java 26.3 `server.jar` in `server/` (not included). RCON is
configured from `server/server.properties`.

```sh
python3 -m venv .venv && source .venv/bin/activate && pip install pyyaml pytest
git config core.hooksPath githooks       # pre-commit: lint staged specs, check library/INDEX.md

python -m scripts.lint                   # offline checks of the whole library
pytest tests/test_generated.py tests/test_devices.py tests/test_traits.py   # no server needed
python -m scripts.try t2_a_qc_breaker    # lint, then every test of one spec on a server
pytest                                   # everything; starts the server if RCON is down
python -m scripts.package two_digit_adder   # dist/two_digit_adder/ and a .zip data pack
```

Offline checks, as they run today:

```
$ python -m scripts.lint
lint ok
$ pytest tests/test_devices.py tests/test_traits.py tests/test_spec_offline.py -q
499 passed in 12.17s
```

To add a design, start with [`docs/AUTHORING.md`](docs/AUTHORING.md). `CLAUDE.md` describes the whole
system in detail.

## Repo layout

| Path | What's there |
|---|---|
| `library/<block>/<variant>.redstone.yaml` | The library: one folder per building block (`xor`, `d_latch`, `clock`, `door`, ...), many designs in each. `library/INDEX.md` lists them all with size, delay and traits |
| `library/mechanics/` | Specs that prove 26.3 mechanics, catalogued in `docs/MECHANICS.md` |
| `library/builds/` | Whole builds, such as `two_digit_adder` |
| `redstone/` | The harness: file format, `Rig`, RCON, servers and satellites, door timing, PLA and router generators, devices |
| `scripts/` | Command-line tools: `lint`, `try`, `retest`, `generate`, `package`, `plots`, `status`, `watch`, ... |
| `tests/` | pytest: one test id per spec test (`test_spec[<spec>::<test>]`), plus offline tests |
| `vscode-redstone/` | A VS Code extension that opens `*.redstone.yaml` as a layer-by-layer editor and plays traces |
| `docs/` | `AUTHORING.md`, `MECHANICS.md`, `WINS.md`, and `research/` on door mechanics and records |
| `docker/` | The satellite server image |

## Licence

MIT (see `LICENSE`). That covers this repo's code and designs, not Mojang's material: the server jar is not
included.
