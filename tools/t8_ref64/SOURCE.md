# The community 4x4x4 tileable RAM cell: sources

Found on 2026-11-23 for issue #85. No schematic, litematic or world download exists for either design below. The block layout has not been read from the video yet: see "What is still missing".

## 1. Pepich1851, "Minecraft redstone: 4^3 tileable memory cell" (video)

- URL: https://www.youtube.com/watch?v=Wa6TiN1pm40
- Channel: Pepich1851. Published 2018-05-21. Length 14:54.
- Description, in short: the design was made at a redstoner.com player's request. The layout stands on the author's plot on the Redstoner server ("You can find the layout on my big plot"; commands `/bp`, `/p h Pepich1851`). It gives no schematic link.

What the narration says, paraphrased from the auto-generated transcript (read clearly, not guessed):
- One cell is a 4x4x4 cube, tileable in all three directions. A row of cells along one axis widens the word, one bit per cell. Rows tile sideways and upwards for more words. The demo is a 3x3 tile of 9 words, then words of 2 and 3 bits.
- Two enable lines run through each cell: read enable (cyan wool in the video) and write enable (dark blue wool), on opposite sides. Both are inverted: off means enabled. Each ends in a repeater so that it carries into the next tiled cell, with dust between.
- Storage is a locked repeater: the write-enable line locks the data repeater when it is on.
- Read is a comparator in subtract mode. With read enable on, its output is 15 − 14 = 1 and the bit does not carry on. With read enable off, the stored bit passes to the output line.
- The output line is carried up through a block over the read path ("this kind of weird thing", 6:47), so that it does not cross the other line. The data input line runs in at the cell's input side.
- Two repeaters make the cell tile without a gap (about 4:56–5:26). Without them dust works, but then neighbours need one block of air between them.
- The enable lines need a repeater about every 4 cells (signal 15, 14, 13 ...); the demo uses repeaters everywhere.
- The author calls it "not the most space efficient": there is air above the red line and beside the enable lines (7:55–8:18).
- Block count: 4x4x4 = 64 blocks of space per bit (inferred from the stated cube; the author gives no non-air block count).

Where in the video to read the blocks:
- 0:53–3:10: one cell built from nothing (enable lines, storage repeater, subtract comparator, output riser, data input).
- 3:18–4:40: a second cell along the word.
- 4:47–5:33: the two tiling repeaters.
- 5:41–6:57: tiling sideways.
- 7:48–12:30: tiling upwards; one cell's comparators are set wrong, then fixed, at 12:18.

## 2. Open Redstone Engineers: "A Challenge for Everyone: The 4x4x4 Tileable RAM Cube" (forum thread)

- URL: https://forum.openredstone.org/thread-2034.html (print view: https://forum.openredstone.org/printthread.php?tid=2034)
- Started 2014-01-18 by properinglish, under Projects & Inventions > In Progress.
- The opening post warns that the challenge "is not guaranteed to be possible to complete".
- The rules, paraphrased by the fetch tool (not verbatim; recheck in a browser before relying on them):
  - Solid state only: no pistons, repeater-lock memory.
  - Tileable in all directions.
  - Data in and out lines run parallel; read and write control lines run parallel; the two pairs run perpendicular.
  - No insulation by repeaters, comparators or torches; the only delay allowed between cells is signal extension.
  - Cells may overlap if the whole still tiles at 4x4x4.
- Replies, paraphrased:
  - Darkroom (2014-01-18) claims a solution, on an in-game warp `4x4x4ram` (no web link).
  - redstonewarrior (2014-01-20) claims a 4x4x4 cell and a 4x3x4 variant with one shared read/write bus, with no schematic posted.
  - WrytXander (2014-01-31) describes a 3x4x5 cell, which started with subtract comparators and moved to a two-torch read.
- No attachments, schematics or images. Not checked: later pages, and thread tid=13098, which a search returned.

## 3. Smaller cells, not verified

A search summary names an r/technicalminecraft post, "probably smallest RAM module" (July 2020): a comparator cell holding 4 bits in 4x4x4 (16 per bit). It is not repeater-lock. Reddit refused the fetch, so this is unconfirmed, with no author or schematic. PlanetMinecraft hits not opened: "1-bit stackable memory v1.1", "compact piston-free bit storage", "UTD memory cell".

## What is still missing

- A layer-by-layer listing of one cell. The video is the only source of the blocks, and reading them needs its frames between 0:53 and 3:10 scrubbed step by step. That was not done in this pass.
- The best entry of the ORE challenge: none is posted with a block count or a schematic.
