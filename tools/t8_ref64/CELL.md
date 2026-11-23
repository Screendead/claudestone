# Pepich1851's 4x4x4 tileable RAM cell: one cell, block by block

Read on 2026-11-23 from the video in `SOURCE.md` (https://www.youtube.com/watch?v=Wa6TiN1pm40), at 1080p,
frame by frame, with the auto-generated transcript alongside. Timestamps are m:ss in the video. This is the
final, working state; it includes nothing placed only for the demo (levers, lamps, the test blocks that stick
out past the cell).

## Axes

- **z: along the word.** Both enable lines run along z, and cells side by side along z are the bits of one
  word (3:18–4:40 builds the second bit this way). The enable signal travels toward **-z**: each line enters
  a cell at z=3 and leaves at z=0 through a repeater into the next cell's z=3.
- **x: words sideways.** The data input and data output lines run along x, so cells side by side along x
  hold the same bit of different words (5:41–6:57).
- **y: up.** Words also tile upward (7:48–12:30).
- Local (0,0,0) is the bottom corner with the write-enable (dark blue) line at x=0 and the enable
  repeaters at z=0. Read enable (cyan) is at x=3. x, y and z each run 0..3. Positions in the text are
  written (x, y, z).

## Layers

Each grid has rows z=0..3 (top row z=0, where the enable repeaters are) and columns x=0..3. Repeater and
comparator entries name the side the input is on and the direction of the output.

### y=0: read clearly (1:00–1:30)

| z \ x | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 0 | blue wool | orange wool | air | cyan wool |
| 1 | blue wool | air | yellow wool | cyan wool |
| 2 | blue wool | yellow wool | yellow wool | cyan wool |
| 3 | air | air | air | air |

- At 1:07 the narration says the two z=3 blocks of the enable lines are "punched out": each line is built
  as an L and its bottom block at z=3 removed, leaving the z=3 block one level up (y=1 below). The demo
  hangs a lever in that hole, under the y=1 block (1:44, 2:58); the lever is not part of the cell.
- All three yellow blocks: (2,0,1) carries the comparator, (2,0,2) the storage repeater and (1,0,2) the lock
  repeater. The one at (2,·,2) is easy to miss once the repeater is on it; it is plain at 1:29–1:30.
- The orange block at (1,0,0) holds up the dust at (1,1,0) (y=1). Its colour is read at 2:33; that it sits
  at y=0 is **guessed**: it is inferred from its apparent height next to the y=1 orange beside it (2:40) and
  from the circuit, which needs that dust at y=1 to be powered by the comparator's output block.

### y=1: read clearly (1:24–2:20; repeater directions from the close-ups at 1:39 and 2:18)

| z \ x | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 0 | repeater, input +z, out -z, delay 1 | dust | orange wool | repeater, input +z, out -z, delay 1 |
| 1 | dust | orange wool | comparator, rear +z, out -z, **subtract** | dust |
| 2 | dust | repeater, input -x, out +x, delay 1 (lock) | repeater, input +z, out -z, delay 1 (storage) | dust |
| 3 | blue wool | air | red wool | cyan wool |

- The storage repeater (2,1,2) is locked from its side by the lock repeater (1,1,2), which takes the
  write-enable dust at (0,1,2) (narration 1:32–1:40; the lock bar shows at 2:18).
- The comparator (2,1,1) reads the storage repeater from behind and the read-enable dust (3,1,1) from its
  side, and outputs into the orange block (2,1,0). Front torch lit at 2:18: subtract mode. One cell in the
  stacked demo is first placed in compare mode and fixed to subtract at 12:18; subtract is the working state.
- Torch positions: the enable repeaters' torches sit together at their -z end (1:39 close-up), so they
  output to -z. The storage repeater's front torch is at its -z end with the lock bar just behind it (2:18).
  The lock repeater's torches are at its x=2 end (1:39). Delay 1 for all four: the delay torch, or the bar,
  sits next to the front torch.
- (1,1,1) and (2,1,0) orange: placed at 2:28–2:33. Read at 2:30 and 2:40. That they are at y=1 is
  **guessed** in the same way as (1,0,0) above.
- (2,1,3) red: at 2:58 an orange block stands there with a lever on it as a test input. At 3:01 it is broken
  (the orange drop shows at 3:02) and replaced by red wool. Read clearly at 3:02–3:07.

### y=2: read at 2:50–3:07; heights of the orange blocks guessed

| z \ x | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 0 | air | air | air | air |
| 1 | orange wool | dust | orange wool | orange wool |
| 2 | air | air | air | air |
| 3 | red wool | red wool | dust | red wool |

- Data output (orange). (0,2,1), (2,2,1) and (3,2,1) are one level higher than (1,1,1) (2:40, 2:58). The
  two over x=2..3 sit above the comparator and the read-enable dust (narration 6:40–6:47: the output is
  taken "upwards" so that it does not cross the red line).
- Data input (red). The line dips at x=2: red wool at (2,1,3) with dust on it at (2,2,3), and red wool one
  level higher at x=0, 1 and 3 (3:02–3:07, seen square-on from +z at 3:07).

### y=3: read at 2:58–3:10

| z \ x | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 0 | air | air | air | air |
| 1 | dust | air | dust | dust |
| 2 | air | air | air | air |
| 3 | dust | dust | air | dust |

- The narration (7:55–8:18) calls the cell "not the most space efficient", with air above the red line and
  beside the enable lines, which matches this layer.

## Lines and levels

- **Write enable**: dark blue, x=0. Enters at z=3: the next cell's repeater (along +z) powers the y=1 wool
  at (0,1,3), which powers the dust at (0,1,2) (15) and (0,1,1) (14). It leaves through the repeater at
  (0,1,0) into the y=1 wool at z=3 of the next cell along -z. The dust at (0,1,2) also feeds the lock
  repeater.
- **Read enable**: cyan, x=3, the same shape. The dust beside the comparator, at (3,1,1), carries 14, the
  narration's "15 minus 14" (2:12–2:21).
- **Both enables are inverted: off means enabled** (1:40). Write enable on locks the storage repeater; off
  lets it follow the data input. Read enable on: the comparator gives 15 - 14 = 1, which reaches the dust at
  (1,1,0) as 1 and dies before the output line. Off: the comparator passes the stored bit (15 or 0).
- **Data input**: red, along x at z=3: dust at y=3 on the red at y=2, dipping at x=2 to dust at y=2 on the red
  wool (2,1,3), which feeds the storage repeater from behind. It enters and leaves through the x=0 and x=3
  faces at (0,3,3) and (3,3,3).
- **Data output**: orange, along x at z=1. The comparator strongly powers the orange (2,1,0). That powers the
  dust at (1,1,0) (on the orange at (1,0,0)), which climbs to the dust at (1,2,1) (on the orange at (1,1,1)).
  That is where the cell's output joins the line, which runs at y=3 on the orange at (0,2,1) and on (2,2,1)
  and (3,2,1). It enters and leaves at (0,3,1) and (3,3,1).
- The repeaters needed on long data lines are not part of the cell. The narration (3:49–3:58) says to add
  them "eventually", depending on how far the line goes.

## The tiling repeaters (4:47–5:33)

- The two repeaters forgotten on the second cell and added at 4:56–5:26 are the enable lines' repeaters at
  z=0. With dust there instead, the cell still works, but cells along the word then need one block of air
  between them, or neighbours interfere (5:03–5:18).

## Not read

- The exact y of the orange blocks (1,0,0), (1,1,1), (2,1,0), (0,2,1), (2,2,1) and (3,2,1) is not read
  directly. No frame shows them square-on from the side. The levels given are the only ones consistent with
  their apparent sizes at 2:40 and 2:58 and with a working output path (comparator → block → dust up two
  steps onto the output line). A server test of the read path settles it.
- The video never says which way along x the data lines are driven. They are plain dust and work either
  way.
