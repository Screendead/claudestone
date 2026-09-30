// Renders library files + traces to PNGs so the drawing code can be inspected without a UI.
// Usage: npm run render [outDir]   (default: out/render)
import { createCanvas } from "@napi-rs/canvas";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { parseModel } from "../src/model";
import { drawLayer, Theme } from "../src/render";
import { parseTrace } from "../src/trace";
import { findSpec, fixtures, repo as root } from "./lib/paths";

const outDir = process.argv[2] ?? resolve(__dirname, "../render");
mkdirSync(outDir, { recursive: true });
const theme: Theme = { bg: "#1e1e1e", cell: "#262626", grid: "#3a3a3a", fg: "#ccc", hover: "#fff", select: "#0af" };

interface Job { file: string; test: string; frameTick: number | null; y: number; below: boolean; tag: string }
const jobs: Job[] = [
  { file: "and_gate", test: "logic", frameTick: 79, y: 1, below: true, tag: "and_gate_00_rest" },
  { file: "and_gate", test: "logic", frameTick: 139, y: 1, below: true, tag: "and_gate_11" },
  { file: "and_gate", test: "logic", frameTick: null, y: 1, below: true, tag: "and_gate_notrace" },
  { file: "xor_gate", test: "logic", frameTick: 109, y: 1, below: true, tag: "xor_y1_a1b0" },
  { file: "xor_gate", test: "logic", frameTick: 109, y: 2, below: true, tag: "xor_y2_a1b0" },
  { file: "lever_lamp", test: "lever toggles lamp", frameTick: 25, y: 1, below: true, tag: "lever_lamp_on" },
  { file: "lever_lamp", test: "lever toggles lamp", frameTick: 22, y: 1, below: true, tag: "lever_lamp_pulled" },
  { file: "button_lamp", test: "button pulse", frameTick: 30, y: 1, below: true, tag: "button_lamp" },
  { file: "latch", test: "x", frameTick: null, y: 1, below: true, tag: "latch_notrace" },
  { file: "full_adder", test: "x", frameTick: null, y: 1, below: true, tag: "full_adder_notrace" },
  { file: "or_gate", test: "logic", frameTick: 100, y: 1, below: true, tag: "or_gate" },
  { file: "rs_hopper_pair", test: "x", frameTick: null, y: 1, below: true, tag: "rs_hopper_pair_nbt" },
  { file: "analog_dac", test: "every code gives its value", frameTick: 40, y: 1, below: true, tag: "analog_dac_levels" },
];
for (const j of jobs) {
  // Fixtures first: the live traces/ are rewritten, dense or sparse, by every test run.
  const model = parseModel(readFileSync(findSpec(j.file, [join(fixtures, "library"), join(root, "library")]), "utf8"));
  const tp = [fixtures, root].map((d) => join(d, "traces", j.file, `${j.test}.json`)).find(existsSync);
  const tr = parseTrace(j.frameTick !== null && tp ? readFileSync(tp, "utf8") : null);
  const fr = tr.frames && (tr.frames.filter((f) => f.tick <= j.frameTick!).pop() ?? tr.frames[0]);
  const S = 64, w = model.layers[0].rows[0].length, h = model.layers[0].rows.length;
  const cv = createCanvas(w * S, h * S);
  drawLayer(cv.getContext("2d") as unknown as CanvasRenderingContext2D, model,
    { y: j.y, S, signals: fr?.signals ?? null, sparse: tr.sparse, levels: fr?.levels ?? null, showBelow: j.below, theme });
  writeFileSync(join(outDir, `${j.tag}.png`), cv.toBuffer("image/png"));
  console.log("wrote", j.tag);
}
