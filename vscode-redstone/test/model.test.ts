import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parseDocument, isScalar, YAMLMap, Pair, Scalar } from "yaml";
import {
  applyModel, canon, clone, entryAt, entryState, formatState, parseModel, parseState, setCell, rotateState, addLayer, resize,
  removeLayer, renameLabel,
} from "../src/model";
import { fixture, fixtures, findSpec, pyLoad, specFiles } from "./lib/paths";

const files = specFiles(join(fixtures, "library"));
const rel = (p: string) => p.slice(fixtures.length + 1);

/** The text with the palette and layers sections cut out: what an edit must leave byte-identical. */
function outsideGrid(text: string): string {
  const items = (parseDocument(text).contents as YAMLMap).items as Pair<Scalar, YAMLMap>[];
  const spans = items.filter((p) => isScalar(p.key) && (p.key.value === "palette" || p.key.value === "layers"))
    .map((p) => {
      let e = p.value!.range![1];
      while (text[e - 1] === "\n") e--;
      return [p.key!.range![0], e];
    }).sort((a, b) => b[0] - a[0]);
  let out = text;
  for (const [a, b] of spans) out = out.slice(0, a) + "<cut>" + out.slice(b);
  return out;
}

/** Paint one cell that holds a plain block with redstone_lamp. */
function oneCellEdit(m: ReturnType<typeof parseModel>) {
  const m2 = clone(m);
  const at = m2.palette.find(([g, e]) => typeof e === "string" && canon(e) !== "air" && canon(e) !== "redstone_lamp" &&
    m2.layers.some((l) => l.rows.some((r) => r.includes(g))))![0];
  const l = m2.layers.find((l) => l.rows.some((r) => r.includes(at)))!;
  const z = l.rows.findIndex((r) => r.includes(at));
  assert.ok(setCell(m2, l.y, l.rows[z].indexOf(at), z, { state: "redstone_lamp" }));
  return m2;
}

test("fixtures cover the format", () => {
  const all = files.map((p) => readFileSync(p, "utf8")).join("\n");
  assert.ok(files.length >= 12);
  for (const needle of ["{Items:", "- repeat:", "- wave:", "- level:", "finally:", "- log:", "\nentities:", "layers: {", "description: >-"])
    assert.ok(all.includes(needle), needle);
});

for (const f of files) {
  test(`round-trips unedited: ${rel(f)}`, () => {
    const text = readFileSync(f, "utf8");
    assert.equal(applyModel(text, parseModel(text)), text);
  });
  test(`a one-cell edit leaves everything outside palette and layers byte-identical: ${rel(f)}`, () => {
    const text = readFileSync(f, "utf8");
    const edited = applyModel(text, oneCellEdit(parseModel(text)));
    assert.notEqual(edited, text);
    assert.equal(outsideGrid(edited), outsideGrid(text));
    assert.deepEqual(parseModel(edited).tests, parseModel(text).tests);
  });
  test(`edit then undo restores the text: ${rel(f)}`, (t) => {
    const text = readFileSync(f, "utf8");
    const m = parseModel(text);
    const edited = applyModel(text, oneCellEdit(m));
    // An edited flow-mapping layers section comes back in block form, so undoing by model cannot restore its bytes.
    if (/^layers: \{/m.test(text)) return t.skip("flow-mapping layers");
    assert.equal(applyModel(edited, m), text);
  });
}

test("a flow-mapping layers section is rewritten loadably and the rest is untouched", () => {
  const p = findSpec("shift_pulse_lock");
  const text = readFileSync(p, "utf8");
  const m = oneCellEdit(parseModel(text));
  const out = applyModel(text, m);
  assert.equal(outsideGrid(out), outsideGrid(text));
  assert.deepEqual(parseModel(out).layers, m.layers);
  const w = join(mkdtempSync(join(tmpdir(), "rs-")), "f.redstone.yaml");
  writeFileSync(w, out);
  const want = pyLoad(p).blocks;
  const got = pyLoad(w).blocks;
  const changed = Object.keys({ ...want, ...got }).filter((k) => want[k] !== got[k]);
  assert.equal(changed.length, 1);
  assert.equal(got[changed[0]], "redstone_lamp");
});

test("edit keeps name, description, tests and comments", () => {
  const text = "# top comment\n" + fixture("and_gate").replace("tests:", "# tests below\ntests:");
  const m = parseModel(text);
  setCell(m, 0, 0, 0, { state: "redstone_block" });
  const out = applyModel(text, m);
  assert.ok(out.startsWith("# top comment\nname: and_gate\ndescription: >-\n"));
  assert.ok(out.includes("# tests below\ntests:\n- name: logic\n  truth_table: |"));
  const before = new Set(text.split("\n"));
  const changed = out.split("\n").filter((l) => !before.has(l));
  assert.deepEqual(changed, ["  R: redstone_block", "    R====...."]);
});

test("paint edit is accepted by the Python loader and reflected in blocks", () => {
  const text = fixture("xor_gate");
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
  const text = fixture("and_gate");
  const base = pyLoad(findSpec("and_gate"));
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
  const text = fixture("or_gate");
  const m = parseModel(text);
  for (const s of ["redstone_wall_torch[facing=north]", "redstone_wall_torch[facing=south]", "redstone_wall_torch[facing=west]",
    "repeater[facing=east]", "redstone_torch", "smooth_stone", "stone", "white_concrete"]) setCell(m, 0, 0, 0, { state: s }), setCell(m, 0, 0, 1, { state: s });
  const out = applyModel(text, m);
  const p = join(mkdtempSync(join(tmpdir(), "rs-")), "g.redstone.yaml");
  writeFileSync(p, out);
  pyLoad(p);
});

test("fixtures, reserved air and multi-cell inputs survive edits and load in Python", () => {
  const text = [
    "name: t", "palette:", "  .: air", "  '=': stone", "  s: {input: s}", "  F: {block: 'repeater[facing=west]', fixture: true}",
    "  _: {reserve: true}", "  o: {output: out, block: redstone_wire}", "layers:", "  0: |", "    s=o_F.s", "",
  ].join("\n");
  const m = parseModel(text);
  assert.equal(entryAt(m, 0, 4, 0)!.entry && (entryAt(m, 0, 3, 0)!.entry as { reserve: true }).reserve, true);
  setCell(m, 0, 6, 0, { state: "air", label: { kind: "input", name: "s" } });
  setCell(m, 0, 4, 0, { state: rotateState("repeater[facing=west]")!, fixture: true });
  const p = join(mkdtempSync(join(tmpdir(), "rs-")), "t.redstone.yaml");
  writeFileSync(p, applyModel(text, m));
  const s = pyLoad(p);
  assert.deepEqual(s.inputs, { s: [0, 0, 0] });
  assert.deepEqual(s.cells, [[0, 0, 0], [6, 0, 0]]);
  assert.deepEqual(s.fixtures, [[4, 0, 0]]);
  assert.deepEqual(s.reserved, [[3, 0, 0]]);
  assert.equal(s.blocks["4,0,0"], "repeater[facing=north]");
});

const HOPPER = 'hopper[facing=east,enabled=false]{Items:[{Slot:0b,id:"minecraft:redstone",count:1}]}';

test("block-entity data parses, formats and stays distinct", () => {
  assert.deepEqual(parseState(HOPPER), { id: "hopper", props: { facing: "east", enabled: "false" },
    nbt: '{Items:[{Slot:0b,id:"minecraft:redstone",count:1}]}' });
  assert.deepEqual(parseState("minecraft:chest{Items:[]}"), { id: "chest", props: {}, nbt: "{Items:[]}" });
  assert.deepEqual(parseState("repeater[facing=west]"), { id: "repeater", props: { facing: "west" } });
  const { id, props, nbt } = parseState(HOPPER);
  assert.equal(formatState(id, props, nbt), HOPPER);
  assert.equal(canon("hopper[facing=east,enabled=false]{Items:[]}"), "hopper[enabled=false,facing=east]{Items:[]}");
  assert.notEqual(canon(HOPPER), canon("hopper[facing=east,enabled=false]{Items:[]}"));
  assert.notEqual(canon(HOPPER), canon("hopper[facing=east,enabled=false]"));
  assert.equal(rotateState(HOPPER), HOPPER.replace("facing=east", "facing=south"));
});

test("specs with block-entity data parse, edit and load in Python", () => {
  for (const name of ["rs_hopper_pair", "probe_cells"]) {
    const text = fixture(name);
    const m = parseModel(text);
    const nbtGlyphs = m.palette.filter(([, e]) => entryState(e).includes("{")).map(([g]) => g);
    assert.ok(nbtGlyphs.length > 0, name);
    const at = m.layers.flatMap((l) => l.rows.flatMap((r, z) => [...r].map((g, x) => ({ g, x, y: l.y, z })))).find((c) => c.g === nbtGlyphs[0])!;
    // Two hoppers with different contents need two glyphs; the same contents reuse one.
    const other = HOPPER.replace("count:1", "count:5");
    setCell(m, at.y, at.x, at.z, { state: other });
    const g1 = entryAt(m, at.y, at.x, at.z)!.glyph;
    assert.notEqual(g1, nbtGlyphs[0]);
    const out = applyModel(text, m);
    assert.equal(outsideGrid(out), outsideGrid(text));
    const p = join(mkdtempSync(join(tmpdir(), "rs-")), "n.redstone.yaml");
    writeFileSync(p, out);
    assert.equal(pyLoad(p).blocks[`${at.x},${at.y},${at.z}`], other);
    // Fixture and named entries hold the state inside a flow map.
    const m2 = parseModel(out);
    setCell(m2, at.y, at.x, at.z, { state: other, label: { kind: "name", name: "box" }, fixture: true });
    writeFileSync(p, applyModel(out, m2));
    const s = pyLoad(p);
    assert.equal(s.blocks[`${at.x},${at.y},${at.z}`], other);
    assert.deepEqual(s.named.box, [at.x, at.y, at.z]);
  }
});

test("traits and settle are read", () => {
  const m = parseModel(fixture("rs_hopper_pair"));
  assert.ok(m.traits.length > 0);
  assert.ok(m.tests.some((t) => t.settle === 30));
  assert.deepEqual(parseModel("name: a\npalette: {.: air}\nlayers:\n  0: |\n    .\n").traits, []);
});

test("an entry pruned by an edit and restored by undo keeps its palette position", () => {
  const text = ["name: t", "palette:", "  .: air", "  a: {name: a, block: 'observer[facing=south]'}", "  b: {output: out, block: redstone_wire}", "layers:", "  0: |", "    ab", ""].join("\n");
  const m = parseModel(text);
  const m2 = clone(m);
  setCell(m2, 0, 0, 0, { state: "redstone_lamp" });
  const edited = applyModel(text, m2);
  assert.ok(!edited.includes("{name: a"));
  assert.equal(applyModel(edited, m), text);
});

test("a layers-only edit leaves a hand-indented palette byte-identical", () => {
  const text = ["name: t", "palette:", "    .: air", "    '#': stone   # support", "layers:", "  0: |", "    .#", ""].join("\n");
  const m = parseModel(text);
  setCell(m, 0, 0, 0, { state: "stone" });
  assert.equal(applyModel(text, m), text.replace("    .#", "    ##"));
});
