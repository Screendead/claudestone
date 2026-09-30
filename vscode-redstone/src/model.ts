import { isMap, isScalar, parseDocument, Scalar, YAMLMap, Pair } from "yaml";

export type Entry = string | { input: string } | { output: string; block: string } | { name: string; block: string };
export interface Layer { y: number; rows: string[] }
export interface Model {
  name: string;
  description: string;
  palette: [string, Entry][];
  layers: Layer[];
  tests: Test[];
}
export interface Test {
  name: string;
  truth_table?: string;
  delay?: number;
  max_delay?: number;
  steps?: Record<string, unknown>[];
}
export type LabelKind = "input" | "output" | "name";
export interface Label { kind: LabelKind; name: string }
/** What to put in a cell: a block state plus an optional name. Inputs ignore the state (air). */
export interface CellSpec { state: string; label?: Label }

// Preferred glyphs; mirrors GLYPHS in redstone/fileformat.py.
export const GLYPHS: Record<string, string> = {
  "minecraft:air": ".",
  "minecraft:smooth_stone": "=",
  "minecraft:white_concrete": "#",
  "minecraft:stone": "S",
  "minecraft:redstone_wire": "-",
  "minecraft:repeater[facing=west]": ">",
  "minecraft:repeater[facing=east]": "<",
  "minecraft:repeater[facing=north]": "v",
  "minecraft:repeater[facing=south]": "^",
  "minecraft:redstone_torch": "*",
  "minecraft:redstone_wall_torch[facing=east]": ")",
  "minecraft:redstone_wall_torch[facing=west]": "(",
  "minecraft:redstone_wall_torch[facing=south]": "u",
  "minecraft:redstone_wall_torch[facing=north]": "n",
  "minecraft:redstone_lamp": "L",
  "minecraft:redstone_block": "R",
};
const FREE = "ABCDEFGHIJKMNOPQSTUVWXYZbcdefghijklmpqrstwxyz0123456789";

export function parseState(state: string): { id: string; props: Record<string, string> } {
  const m = /^([^[]*)(?:\[(.*)\])?$/.exec(state.trim())!;
  const id = m[1].replace(/^minecraft:/, "");
  const props: Record<string, string> = {};
  if (m[2]) for (const kv of m[2].split(",")) {
    const [k, v] = kv.split("=");
    if (k) props[k.trim()] = (v ?? "").trim();
  }
  return { id, props };
}

export function formatState(id: string, props: Record<string, string>): string {
  const keys = Object.keys(props);
  return keys.length ? `${id}[${keys.map((k) => `${k}=${props[k]}`).join(",")}]` : id;
}

/** Canonical form for equality: no namespace, properties sorted. */
export function canon(state: string): string {
  const { id, props } = parseState(state);
  const sorted: Record<string, string> = {};
  for (const k of Object.keys(props).sort()) sorted[k] = props[k];
  return formatState(id, sorted);
}

export function entryState(e: Entry): string {
  if (typeof e === "string") return e;
  return "block" in e ? e.block : "air";
}
export function entryLabel(e: Entry): Label | undefined {
  if (typeof e === "string") return undefined;
  if ("input" in e) return { kind: "input", name: e.input };
  if ("output" in e) return { kind: "output", name: e.output };
  return { kind: "name", name: e.name };
}
export function makeEntry(spec: CellSpec): Entry {
  const l = spec.label;
  if (!l) return spec.state;
  if (l.kind === "input") return { input: l.name };
  if (l.kind === "output") return { output: l.name, block: spec.state };
  return { name: l.name, block: spec.state };
}

export function parseModel(text: string): Model {
  const doc = parseDocument(text);
  if (doc.errors.length) throw new Error(doc.errors[0].message);
  const js = doc.toJS() as Record<string, any>;
  if (!js || typeof js !== "object") throw new Error("not a mapping");
  const pal = doc.get("palette", true);
  if (!isMap(pal)) throw new Error("missing palette");
  const palette: [string, Entry][] = [];
  for (const p of pal.items) {
    const k = String(isScalar(p.key) ? p.key.value : p.key);
    const v = p.value && (p.value as any).toJSON ? (p.value as any).toJSON() : p.value;
    palette.push([k, v as Entry]);
  }
  const lay = doc.get("layers", true);
  if (!isMap(lay)) throw new Error("missing layers");
  const layers: Layer[] = [];
  for (const p of lay.items) {
    const y = Number(isScalar(p.key) ? p.key.value : p.key);
    const txt = String(isScalar(p.value) ? p.value.value : "");
    layers.push({ y, rows: txt.replace(/\n+$/, "").split("\n") });
  }
  layers.sort((a, b) => a.y - b.y);
  const w = layers[0]?.rows[0]?.length ?? 0;
  const h = layers[0]?.rows.length ?? 0;
  for (const l of layers) {
    if (l.rows.length !== h || l.rows.some((r) => r.length !== w))
      throw new Error(`layer ${l.y} is not ${h} rows of ${w}`);
  }
  return {
    name: String(js.name ?? ""),
    description: String(js.description ?? ""),
    palette,
    layers,
    tests: Array.isArray(js.tests) ? js.tests : [],
  };
}

const STRINGIFY = { lineWidth: 0, flowCollectionPadding: false, indentSeq: false } as const;

function scalarFor(s: string, isKey: boolean): Scalar {
  const sc = new Scalar(s);
  // PyYAML reads a bare "=" as a special tag and "<<" as a merge key; quote every symbol glyph.
  if (isKey && !/^[A-Za-z.]$/.test(s)) sc.type = "QUOTE_SINGLE";
  return sc;
}
function entryNode(e: Entry): unknown {
  if (typeof e === "string") return scalarFor(e, false);
  const m = new YAMLMap();
  m.flow = true;
  for (const [k, v] of Object.entries(e)) m.add(new Pair(new Scalar(k), scalarFor(v as string, false)));
  return m;
}

/** Write palette and layers into the original text, leaving every other node alone. */
export function applyModel(text: string, model: Model): string {
  const doc = parseDocument(text);
  if (doc.errors.length) throw new Error(doc.errors[0].message);
  const before = parseModel(text);
  let changed = false;

  if (JSON.stringify(before.palette) !== JSON.stringify(model.palette)) {
    changed = true;
    const pal = doc.get("palette", true) as YAMLMap;
    const want = new Map(model.palette);
    pal.items = pal.items.filter((p) => want.has(String(isScalar(p.key) ? p.key.value : p.key)));
    const have = new Map<string, Pair>();
    for (const p of pal.items) have.set(String(isScalar(p.key) ? p.key.value : p.key), p as Pair);
    for (const [g, e] of model.palette) {
      const old = have.get(g);
      if (!old) pal.items.push(new Pair(scalarFor(g, true), entryNode(e)));
      else if (JSON.stringify((old.value as any)?.toJSON?.() ?? old.value) !== JSON.stringify(e)) old.value = entryNode(e);
    }
  }

  const layerText = (l: Layer) => l.rows.join("\n") + "\n";
  const lay = doc.get("layers", true) as YAMLMap;
  const beforeL = new Map(before.layers.map((l) => [l.y, layerText(l)]));
  const keyOf = (p: Pair) => Number(isScalar(p.key) ? p.key.value : p.key);
  if (beforeL.size !== model.layers.length || model.layers.some((l) => beforeL.get(l.y) !== layerText(l))) {
    changed = true;
    const want = new Map(model.layers.map((l) => [l.y, l]));
    lay.items = lay.items.filter((p) => want.has(keyOf(p as Pair)));
    const have = new Map(lay.items.map((p) => [keyOf(p as Pair), p as Pair]));
    for (const l of model.layers) {
      const old = have.get(l.y);
      if (old && isScalar(old.value)) {
        if (String(old.value.value) !== layerText(l)) old.value.value = layerText(l);
      } else {
        const sc = new Scalar(layerText(l));
        sc.type = "BLOCK_LITERAL";
        if (old) old.value = sc;
        else lay.items.push(new Pair(new Scalar(l.y), sc));
      }
    }
    lay.items.sort((a, b) => keyOf(a as Pair) - keyOf(b as Pair));
  }
  return changed ? doc.toString(STRINGIFY) : text;
}

// ---- editing operations (mutate the model in place) ----

export function clone(m: Model): Model { return JSON.parse(JSON.stringify(m)); }

export function width(m: Model): number { return m.layers[0]?.rows[0]?.length ?? 0; }
export function height(m: Model): number { return m.layers[0]?.rows.length ?? 0; }
export function layerAt(m: Model, y: number): Layer | undefined { return m.layers.find((l) => l.y === y); }
export function entryAt(m: Model, y: number, x: number, z: number): { glyph: string; entry: Entry } | undefined {
  const g = layerAt(m, y)?.rows[z]?.[x];
  if (g === undefined) return undefined;
  const e = m.palette.find(([k]) => k === g)?.[1];
  return e === undefined ? undefined : { glyph: g, entry: e };
}

function sameEntry(a: Entry, b: Entry): boolean {
  if (typeof a === "string" || typeof b === "string") {
    return typeof a === "string" && typeof b === "string" && canon(a) === canon(b);
  }
  if ("input" in a || "input" in b) return "input" in a && "input" in b && a.input === b.input;
  return entryLabel(a)!.kind === entryLabel(b)!.kind && entryLabel(a)!.name === entryLabel(b)!.name &&
    canon(entryState(a)) === canon(entryState(b));
}

function usedGlyphs(m: Model): Set<string> {
  const s = new Set<string>();
  for (const l of m.layers) for (const r of l.rows) for (const c of r) s.add(c);
  return s;
}

/** Find or create the glyph for a cell spec, adding a palette entry when needed. */
export function glyphFor(m: Model, spec: CellSpec): string {
  const entry = makeEntry(spec);
  const isAir = !spec.label && canon(spec.state) === "air";
  const found = m.palette.find(([, e]) => sameEntry(e, entry));
  if (found) return found[0];
  const taken = new Set(m.palette.map(([k]) => k));
  const reserved = new Set(Object.values(GLYPHS));
  let g: string | undefined;
  if (!spec.label) {
    const pref = GLYPHS[canonNs(spec.state)];
    if (pref && !taken.has(pref)) g = pref;
  } else {
    const c = spec.label.name[0];
    if (c && /[A-Za-z0-9]/.test(c) && !taken.has(c) && !reserved.has(c)) g = c;
  }
  if (!g && isAir && !taken.has(".")) g = ".";
  if (!g) g = [...FREE].find((c) => !taken.has(c) && !reserved.has(c));
  if (!g) throw new Error("palette is full");
  m.palette.push([g, entry]);
  return g;
}
function canonNs(state: string): string {
  const c = canon(state);
  return "minecraft:" + c;
}

export function setCell(m: Model, y: number, x: number, z: number, spec: CellSpec): boolean {
  const layer = layerAt(m, y);
  if (!layer || z < 0 || z >= layer.rows.length || x < 0 || x >= layer.rows[0].length) return false;
  if (spec.label) clearName(m, spec.label.name, y, x, z);
  const g = glyphFor(m, spec);
  const row = layer.rows[z];
  if (row[x] === g) return false;
  layer.rows[z] = row.slice(0, x) + g + row.slice(x + 1);
  pruneLabels(m);
  return true;
}

/** Names are unique across the build: placing one elsewhere moves it. */
function clearName(m: Model, name: string, ky: number, kx: number, kz: number) {
  for (const l of m.layers) l.rows.forEach((row, z) => {
    for (let x = 0; x < row.length; x++) {
      if (l.y === ky && x === kx && z === kz) continue;
      const e = m.palette.find(([k]) => k === row[x])?.[1];
      if (e && entryLabel(e)?.name === name) {
        const air = glyphFor(m, { state: "air" });
        l.rows[z] = l.rows[z].slice(0, x) + air + l.rows[z].slice(x + 1);
      }
    }
  });
}

/** Drop label entries no cell uses any more; plain block entries stay so they remain in the palette. */
export function pruneLabels(m: Model) {
  const used = usedGlyphs(m);
  m.palette = m.palette.filter(([g, e]) => used.has(g) || !entryLabel(e));
}

export function renameLabel(m: Model, y: number, x: number, z: number, name: string, kind?: LabelKind): boolean {
  const at = entryAt(m, y, x, z);
  const lab = at && entryLabel(at.entry);
  if (!at || !lab || !name) return false;
  return setCell(m, y, x, z, { state: entryState(at.entry), label: { kind: kind ?? lab.kind, name } });
}

const ROT: Record<string, string[]> = { facing: ["north", "east", "south", "west"] };
/** Rotate the facing of a directional block clockwise (viewed from above); undefined if it has none. */
export function rotateState(state: string): string | undefined {
  const { id, props } = parseState(state);
  const f = props.facing;
  if (!f) return undefined;
  const order = ROT.facing;
  const i = order.indexOf(f);
  if (i < 0) return undefined;
  return formatState(id, { ...props, facing: order[(i + 1) % 4] });
}

export function addLayer(m: Model, where: "above" | "below"): number {
  const w = width(m), h = height(m);
  const y = where === "above" ? Math.max(...m.layers.map((l) => l.y)) + 1 : Math.min(...m.layers.map((l) => l.y)) - 1;
  const air = glyphFor(m, { state: "air" });
  m.layers.push({ y, rows: Array.from({ length: h }, () => air.repeat(w)) });
  m.layers.sort((a, b) => a.y - b.y);
  return y;
}
export function removeLayer(m: Model, y: number): boolean {
  if (m.layers.length <= 1) return false;
  m.layers = m.layers.filter((l) => l.y !== y);
  pruneLabels(m);
  return true;
}
export type Edge = "north" | "south" | "west" | "east";
/** delta +1 adds a row/column of air at that edge, -1 removes the outermost one. */
export function resize(m: Model, edge: Edge, delta: 1 | -1): boolean {
  const w = width(m), h = height(m);
  if (delta < 0 && ((edge === "north" || edge === "south") ? h : w) <= 1) return false;
  const air = glyphFor(m, { state: "air" });
  for (const l of m.layers) {
    if (edge === "north") l.rows = delta > 0 ? [air.repeat(w), ...l.rows] : l.rows.slice(1);
    else if (edge === "south") l.rows = delta > 0 ? [...l.rows, air.repeat(w)] : l.rows.slice(0, -1);
    else if (edge === "west") l.rows = l.rows.map((r) => (delta > 0 ? air + r : r.slice(1)));
    else l.rows = l.rows.map((r) => (delta > 0 ? r + air : r.slice(0, -1)));
  }
  pruneLabels(m);
  return true;
}
