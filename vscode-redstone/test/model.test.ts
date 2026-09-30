import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { applyModel, clone, entryAt, parseModel, setCell, rotateState, addLayer, resize, removeLayer, renameLabel } from "../src/model";

const repo = resolve(__dirname, "../../..");
const lib = join(repo, "library");
const files = readdirSync(lib).filter((f) => f.endsWith(".redstone.yaml"));

const pyLoad = (path: string) => JSON.parse(execFileSync(join(repo, ".venv/bin/python"), ["-c", `
import json, sys
from redstone.fileformat import load
s = load(sys.argv[1])
print(json.dumps({"blocks": {",".join(map(str, p)): b.removeprefix("minecraft:") for p, b in s.build.blocks.items()},
  "inputs": {k: list(v) for k, v in s.inputs.items()}, "named": {k: list(v) for k, v in s.named.items()}, "outputs": list(s.outputs)}))
`, path], { cwd: repo, encoding: "utf8" }));

test("library has files", () => assert.ok(files.length >= 6));

for (const f of files) {
  test(`round-trips unedited: ${f}`, () => {
    const text = readFileSync(join(lib, f), "utf8");
    assert.equal(applyModel(text, parseModel(text)), text);
  });
  test(`re-serialising forced through the yaml document keeps text: ${f}`, () => {
    // An edit followed by its undo must leave no residue in untouched parts.
    const text = readFileSync(join(lib, f), "utf8");
    const m = parseModel(text);
    const m2 = clone(m);
    const at = m2.palette.find(([, e]) => typeof e === "string" && e !== "air" && e !== "redstone_lamp")![0];
    const l = m2.layers.find((l) => l.rows.some((r) => r.includes(at)))!;
    const z = l.rows.findIndex((r) => r.includes(at));
    setCell(m2, l.y, l.rows[z].indexOf(at), z, { state: "redstone_lamp" });
    const edited = applyModel(text, m2);
    assert.notEqual(edited, text);
    assert.equal(applyModel(edited, m), text);
  });
}

test("edit keeps name, description, tests and comments", () => {
  const text = "# top comment\n" + readFileSync(join(lib, "and_gate.redstone.yaml"), "utf8")
    .replace("tests:", "# tests below\ntests:");
  const m = parseModel(text);
  setCell(m, 0, 0, 0, { state: "redstone_block" });
  const out = applyModel(text, m);
  assert.ok(out.startsWith("# top comment\nname: and_gate\n"));
  assert.ok(out.includes("# tests below\ntests:\n- name: logic\n  truth_table: |"));
  const before = new Set(text.split("\n"));
  const changed = out.split("\n").filter((l) => !before.has(l));
  assert.deepEqual(changed, ["  R: redstone_block", "    R====...."]);
});

test("paint edit is accepted by the Python loader and reflected in blocks", () => {
  const text = readFileSync(join(lib, "xor_gate.redstone.yaml"), "utf8");
  const m = parseModel(text);
  setCell(m, 0, 0, 0, { state: "redstone_lamp" });                       // preferred glyph L
  setCell(m, 0, 1, 0, { state: "lever[face=wall,facing=west,powered=false]" }); // new free glyph
  setCell(m, 0, 2, 0, { state: "comparator[mode=compare,facing=north]" });
  setCell(m, 1, 9, 0, { state: "redstone_wire", label: { kind: "output", name: "second" } });
  setCell(m, 1, 8, 0, { state: "air", label: { kind: "input", name: "c" } });
  const out = applyModel(text, m);
  const dir = mkdtempSync(join(tmpdir(), "rs-"));
  const p = join(dir, "edit.redstone.yaml");
  writeFileSync(p, out);
  const loaded = pyLoad(p);
  assert.equal(loaded.blocks["0,0,0"], "redstone_lamp");
  assert.match(loaded.blocks["1,0,0"], /^lever\[/);
  assert.match(loaded.blocks["2,0,0"], /^comparator\[/);
  assert.deepEqual(loaded.named.second, [9, 1, 0]);
  assert.deepEqual(loaded.inputs.c, [8, 1, 0]);
  assert.deepEqual(loaded.outputs.sort(), ["out", "second"]);
  assert.deepEqual(loaded.inputs.a, [0, 1, 0]);
  assert.equal(loaded.blocks["0,0,0"] !== undefined, true);
  // glyph consistency: lamp uses the preferred glyph
  assert.equal(entryAt(parseModel(out), 0, 0, 0)?.glyph, "L");
});

test("structure edits (layers, rows, columns, rotate, rename) load in Python", () => {
  const text = readFileSync(join(lib, "and_gate.redstone.yaml"), "utf8");
  const base = pyLoad(join(lib, "and_gate.redstone.yaml"));
  const m = parseModel(text);
  const top = addLayer(m, "above");
  const bottom = addLayer(m, "below");
  assert.equal(top, 2);
  assert.equal(bottom, -1);
  setCell(m, top, 0, 0, { state: "stone" });
  resize(m, "west", 1);
  resize(m, "north", 1);
  resize(m, "east", 1);
  resize(m, "south", 1);
  assert.ok(renameLabel(m, 1, 1, 1, "renamed"));
  const out = applyModel(text, m);
  const p = join(mkdtempSync(join(tmpdir(), "rs-")), "s.redstone.yaml");
  writeFileSync(p, out);
  const l = pyLoad(p);
  // every original cell shifted by (+1, +1) in x/z
  for (const [k, v] of Object.entries<string>(base.blocks)) {
    const [x, y, z] = k.split(",").map(Number);
    assert.equal(l.blocks[`${x + 1},${y},${z + 1}`], v, k);
  }
  assert.equal(l.blocks["1,2,1"], "stone");
  assert.deepEqual(l.inputs.renamed, [1, 1, 1]);
  assert.ok(!removeLayer(parseModel("name: a\npalette: {.: air}\nlayers:\n  0: |\n    .\n"), 0));
  // removing edges and layers again
  const m2 = parseModel(out);
  resize(m2, "west", -1); resize(m2, "north", -1); resize(m2, "east", -1); resize(m2, "south", -1);
  removeLayer(m2, 2); removeLayer(m2, -1);
  assert.ok(renameLabel(m2, 1, 0, 0, "a"));
  const back = applyModel(text, m2);
  writeFileSync(p, back);
  assert.deepEqual(pyLoad(p), base);
});

test("rotate cycles facing clockwise", () => {
  assert.equal(rotateState("repeater[facing=west]"), "repeater[facing=north]");
  assert.equal(rotateState("redstone_wire"), undefined);
});

test("y/n/symbol glyphs stay loadable", () => {
  const text = readFileSync(join(lib, "or_gate.redstone.yaml"), "utf8");
  const m = parseModel(text);
  for (const s of ["redstone_wall_torch[facing=north]", "redstone_wall_torch[facing=south]", "redstone_wall_torch[facing=west]",
    "repeater[facing=east]", "redstone_torch", "smooth_stone", "stone", "white_concrete"]) setCell(m, 0, 0, 0, { state: s }), setCell(m, 0, 0, 1, { state: s });
  const out = applyModel(text, m);
  const p = join(mkdtempSync(join(tmpdir(), "rs-")), "g.redstone.yaml");
  writeFileSync(p, out);
  pyLoad(p);
});
