import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { createCanvas } from "@napi-rs/canvas";
import { Model, parseModel } from "../src/model";
import { cellTrace, drawLayer, infoTable, Theme } from "../src/render";
import { parseTrace } from "../src/trace";
import { fixture, fixtures, specFiles } from "./lib/paths";

const theme: Theme = { bg: "#000", cell: "#111", grid: "#222", fg: "#ccc", hover: "#fff", select: "#0af" };
type Opts = Partial<Parameters<typeof drawLayer>[2]>;

function render(m: Model, o: Opts = {}, S = 40) {
  const w = m.layers[0].rows[0].length, h = m.layers[0].rows.length;
  const cv = createCanvas(w * S, h * S);
  const ctx = cv.getContext("2d");
  drawLayer(ctx as unknown as CanvasRenderingContext2D, m, { y: m.layers[0].y, S, signals: null, showBelow: true, theme, compass: false, ...o });
  return (x: number, y: number) => [...ctx.getImageData(x, y, 1, 1).data.slice(0, 3)];
}

test("every fixture layer draws, including block-entity data", () => {
  for (const f of specFiles(join(fixtures, "library"))) {
    const m = parseModel(readFileSync(f, "utf8"));
    for (const l of m.layers) {
      const cv = createCanvas(m.layers[0].rows[0].length * 8, m.layers[0].rows.length * 8);
      drawLayer(cv.getContext("2d") as unknown as CanvasRenderingContext2D, m, { y: l.y, S: 8, signals: {}, sparse: true, showBelow: true, theme });
    }
    assert.ok(infoTable(m).size > 0, f);
  }
});

test("a sparse trace records only named cells", () => {
  const m = parseModel(fixture("and_gate"));
  const t = infoTable(m);
  const opts = { signals: { "8,1,1": 12 }, sparse: true, levels: null };
  assert.deepEqual(cellTrace(t.get("o")!, "8,1,1", opts), { level: 12, traced: true });
  assert.deepEqual(cellTrace(t.get("-")!, "4,1,0", opts), { level: 0, traced: false });
  assert.deepEqual(cellTrace(t.get("-")!, "4,1,0", { ...opts, sparse: false }), { level: 0, traced: true });
  assert.deepEqual(cellTrace(t.get("-")!, "4,1,0", { signals: null }), { level: 0, traced: false });
  // Named cells absent from a frame are off: traces drop zero values.
  assert.deepEqual(cellTrace(t.get("o")!, "8,1,1", { signals: {}, sparse: true }), { level: 0, traced: true });
});

test("an unrecorded torch keeps its placed state under a sparse trace; a dense trace turns it off", () => {
  const m: Model = { name: "t", description: "", traits: [], tests: [], palette: [["*", "redstone_torch"], ["o", { output: "out", block: "redstone_torch" }]],
    layers: [{ y: 0, rows: ["*o"] }] };
  const S = 40, head = (px: ReturnType<typeof render>, x: number) => px(x * S + S / 2, S / 2);
  const lit = head(render(m), 0), unlit = head(render(m, { signals: {} }), 0);
  assert.notDeepEqual(lit, unlit);
  const sparse = render(m, { signals: {}, sparse: true });
  assert.deepEqual(head(sparse, 0), lit);     // not recorded: drawn as placed (lit)
  assert.deepEqual(head(sparse, 1), unlit);   // recorded and absent: off
});

test("a plain torch is never recorded, so a dense trace leaves it lit", () => {
  const m: Model = { name: "t", description: "", traits: [], tests: [], palette: [["t", "torch"], ["w", "wall_torch[facing=east]"]],
    layers: [{ y: 0, rows: ["tw"] }] };
  const t = infoTable(m);
  assert.deepEqual(cellTrace(t.get("t")!, "0,0,0", { signals: {}, sparse: false }), { level: 0, traced: false });
  assert.deepEqual(cellTrace(t.get("w")!, "1,0,0", { signals: {}, sparse: false }), { level: 0, traced: false });
  const S = 40, px = (r: ReturnType<typeof render>) => r(S / 2, S / 2);
  assert.deepEqual(px(render(m, { signals: {} })), px(render(m)));
});

test("comparator strengths from a dense trace reach the drawing", () => {
  const tr = parseTrace(readFileSync(join(fixtures, "traces/analog_dac/every code gives its value.json"), "utf8"));
  const fr = tr.frames!.find((f) => f.levels && Object.keys(f.levels).length)!;
  const m = parseModel(fixture("analog_dac"));
  const t = infoTable(m);
  const [key, strength] = Object.entries(fr.levels!)[0];
  const [x, y, z] = key.split(",").map(Number);
  const info = t.get(m.layers.find((l) => l.y === y)!.rows[z][x])!;
  assert.equal(info.id, "comparator");
  assert.equal(cellTrace(info, key, { signals: fr.signals, levels: fr.levels, sparse: tr.sparse }).strength, strength);
  // Zero strengths are left out of the file; only comparators have one.
  assert.equal(cellTrace(info, "0,0,0", { signals: {}, levels: {} }).strength, 0);
  assert.equal(cellTrace(t.get("=")!, "0,0,0", { signals: {}, levels: {} }).strength, undefined);
  assert.equal(cellTrace(info, key, { signals: fr.signals, levels: null }).strength, undefined);
  const withLevels = render(m, { y, signals: fr.signals, levels: fr.levels }, 48);
  const without = render(m, { y, signals: fr.signals }, 48);
  // The strength is written next to the comparator's CMP/SUB tag.
  let differs = false;
  for (let px = 0; px < 48 && !differs; px++) for (let py = 36; py < 48 && !differs; py++)
    differs = JSON.stringify(withLevels(x * 48 + px, z * 48 + py)) !== JSON.stringify(without(x * 48 + px, z * 48 + py));
  assert.ok(differs);
});
