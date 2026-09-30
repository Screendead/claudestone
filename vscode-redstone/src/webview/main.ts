import {
  Model, Test, CellSpec, LabelKind, canon, clone, entryAt, entryFixture, entryLabel, entryState, formatState, height, layerAt,
  parseState, setCell, rotateState, addLayer, removeLayer, resize, renameLabel, width, Edge,
} from "../model";
import { cellTrace, drawLayer, infoTable, Theme } from "../render";
import { Frame, parseFailures } from "../trace";
import { testFlags } from "./text";

declare function acquireVsCodeApi(): { postMessage(m: unknown): void; getState(): any; setState(s: unknown): void };
const vscode = acquireVsCodeApi();

interface Trace { test: string; frames: Frame[] | null; path: string; sparse: boolean; failures: string[] }

const COMMON: string[] = [
  "air", "redstone_wire", "repeater[facing=west]", "comparator[facing=west]", "comparator[facing=west,mode=subtract]",
  "redstone_torch", "redstone_wall_torch[facing=east]", "redstone_lamp", "lever[face=wall,facing=west,powered=false]",
  "stone_button[face=wall,facing=west,powered=false]", "white_concrete", "smooth_stone", "redstone_block",
];

let model: Model | null = null;
let y = 0;
let S = 0; // 0 = fit to window
let showBelow = true;
let tool: "paint" | "select" = "paint";
let brush = "redstone_wire";
let labelKind: "none" | LabelKind = "none";
let labelName = "";
let hover: { x: number; z: number } | null = null;
let selected: { x: number; z: number } | null = null;
let stroke: Model | null = null;
let strokeErase = false;
let selectedTest: string | null = vscode.getState()?.test ?? null;
let trace: Trace | null = null;
let frameIdx = 0;
let playing = false;
let speed = 1;
let running = false;
let timer: ReturnType<typeof setTimeout> | undefined;
let errorText = "";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
function el<K extends keyof HTMLElementTagNameMap>(tag: K, props: Partial<HTMLElementTagNameMap[K]> & { cls?: string } = {},
  ...kids: (Node | string)[]): HTMLElementTagNameMap[K] {
  const { cls, ...rest } = props as any;
  const e = document.createElement(tag);
  Object.assign(e, rest);
  if (cls) e.className = cls;
  for (const k of kids) e.append(k);
  return e;
}

function theme(): Theme {
  const cs = getComputedStyle(document.body);
  const v = (n: string, d: string) => cs.getPropertyValue(n).trim() || d;
  return {
    bg: v("--vscode-editor-background", "#1e1e1e"),
    cell: "rgba(128,128,128,0.10)",
    grid: "rgba(128,128,128,0.35)",
    fg: v("--vscode-foreground", "#ccc"),
    hover: v("--vscode-focusBorder", "#fff"),
    select: "#e5c07b",
  };
}

const frame = (): Frame | null => (trace?.frames && trace.frames.length ? trace.frames[Math.min(frameIdx, trace.frames.length - 1)] : null);
const currentEvent = (): { text: string; tick: number } | null => {
  const fr = trace?.frames;
  if (!fr) return null;
  for (let i = Math.min(frameIdx, fr.length - 1); i >= 0; i--) if (fr[i].event) return { text: fr[i].event + (fr[i].reply ? ` -> ${fr[i].reply}` : ""), tick: fr[i].tick };
  return null;
};
function drivenInputs(): Record<string, boolean> {
  const out: Record<string, boolean> = {};
  const fr = trace?.frames;
  if (!fr) return out;
  for (let i = 0; i <= Math.min(frameIdx, fr.length - 1); i++) {
    const m = /^drive\s+(.*)$/.exec(fr[i].event);
    if (m) for (const kv of m[1].split(/\s+/)) { const [k, v] = kv.split("="); if (k) out[k] = v === "1" || v === "true"; }
  }
  return out;
}

const traceOpts = () => ({ signals: frame()?.signals ?? null, sparse: !!trace?.sparse, levels: frame()?.levels ?? null });

// ---------- rendering ----------

function fitScale(): number {
  if (!model) return 32;
  const wrap = $("canvasWrap");
  const w = Math.max(1, width(model)), h = Math.max(1, height(model));
  return Math.max(16, Math.min(80, Math.floor(Math.min((wrap.clientWidth - 24) / w, (wrap.clientHeight - 24) / h))));
}
const scale = () => S || fitScale();

function sizeCanvas(c: HTMLCanvasElement, w: number, h: number): CanvasRenderingContext2D {
  const dpr = window.devicePixelRatio || 1;
  c.width = Math.round(w * dpr);
  c.height = Math.round(h * dpr);
  c.style.width = `${w}px`;
  c.style.height = `${h}px`;
  const ctx = c.getContext("2d")!;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return ctx;
}

function renderMain() {
  if (!model) return;
  const m = stroke ?? model;
  const s = scale();
  const c = $<HTMLCanvasElement>("canvas");
  const ctx = sizeCanvas(c, width(m) * s, height(m) * s);
  drawLayer(ctx, m, {
    y, S: s, ...traceOpts(), inputs: drivenInputs(), showBelow, theme: theme(), hover, selected,
  });
}

function renderMinis() {
  if (!model) return;
  const box = $("minis");
  box.replaceChildren();
  for (const l of [...model.layers].reverse()) {
    const cv = el("canvas", { cls: "mini" + (l.y === y ? " active" : ""), title: `layer y=${l.y}` });
    const ms = 8;
    const ctx = sizeCanvas(cv, width(model) * ms, height(model) * ms);
    drawLayer(ctx, model, { y: l.y, S: ms, ...traceOpts(), inputs: drivenInputs(), showBelow: false, compass: false, theme: theme() });
    cv.onclick = () => { y = l.y; renderAll(); };
    box.append(el("div", { cls: "miniWrap" }, el("span", { textContent: `y=${l.y}` }), cv));
  }
}

function swatch(state: string, label?: { kind: LabelKind; name: string }): HTMLCanvasElement {
  const e = label ? (label.kind === "input" ? { input: label.name } : label.kind === "output" ? { output: label.name, block: state } : { name: label.name, block: state }) : state;
  const mini: Model = { name: "", description: "", traits: [], tests: [], palette: [["p", e]], layers: [{ y: 0, rows: ["p"] }] };
  const cv = el("canvas");
  const ctx = sizeCanvas(cv, 40, 40);
  drawLayer(ctx, mini, { y: 0, S: 40, signals: null, showBelow: false, compass: false, theme: { ...theme(), grid: "transparent" } });
  return cv;
}

function renderPalette() {
  if (!model) return;
  const box = $("palette");
  box.replaceChildren();
  const seen = new Set<string>();
  const add = (state: string, label?: { kind: LabelKind; name: string }, glyph?: string) => {
    const key = canon(state) + (label ? `|${label.kind}:${label.name}` : "");
    if (seen.has(key)) return;
    seen.add(key);
    const isSel = !label && canon(state) === canon(brush);
    const item = el("button", { cls: "swatch" + (isSel ? " sel" : ""), title: label ? `${label.kind} ${label.name}: ${state}` : state },
      swatch(state, label), el("span", { textContent: glyph ? `${glyph}` : "" }));
    item.onclick = () => {
      tool = "paint";
      brush = label?.kind === "input" ? "air" : state;
      labelKind = label ? label.kind : "none";
      labelName = label ? label.name : "";
      renderAll();
    };
    box.append(item);
  };
  for (const [g, e] of model.palette) add(entryState(e), entryLabel(e), g);
  $("paletteCommon").replaceChildren();
  const common = $("paletteCommon");
  for (const st of COMMON) {
    const key = canon(st);
    if (seen.has(key)) continue;
    const item = el("button", { cls: "swatch" + (canon(brush) === key && labelKind === "none" ? " sel" : ""), title: st }, swatch(st));
    item.onclick = () => { tool = "paint"; brush = st; labelKind = "none"; labelName = ""; renderAll(); };
    common.append(item);
  }
  ($("toolPaint") as HTMLButtonElement).classList.toggle("sel", tool === "paint");
  ($("toolSelect") as HTMLButtonElement).classList.toggle("sel", tool === "select");
  ($("labelKind") as HTMLSelectElement).value = labelKind;
  if (document.activeElement !== $("labelName")) ($("labelName") as HTMLInputElement).value = labelName;
  $("brushInfo").textContent = labelKind === "input" ? `input ${labelName || "(name?)"}` : `${labelKind !== "none" ? labelKind + " " + (labelName || "(name?)") + ": " : ""}${brush}`;
}

function renderSelected() {
  const box = $("selInfo");
  box.replaceChildren();
  if (!model || !selected) { box.textContent = "Select tool: click a cell."; return; }
  const at = entryAt(model, y, selected.x, selected.z);
  box.append(el("div", { textContent: `x=${selected.x} y=${y} z=${selected.z}` }));
  if (!at) return;
  box.append(el("div", { textContent: `'${at.glyph}'  ${entryState(at.entry)}` }));
  const lab = entryLabel(at.entry);
  if (lab) {
    const inp = el("input", { value: lab.name, type: "text" });
    const sel = el("select", {}, ...(["input", "output", "name"] as const).map((k) => el("option", { value: k, textContent: k, selected: k === lab.kind })));
    const apply = () => {
      const next = clone(model!);
      if (renameLabel(next, y, selected!.x, selected!.z, inp.value.trim(), sel.value as LabelKind)) commit(next);
    };
    inp.onkeydown = (e) => { if (e.key === "Enter") apply(); e.stopPropagation(); };
    sel.onchange = apply;
    box.append(el("div", { cls: "row" }, sel, inp, el("button", { textContent: "Rename", onclick: apply })));
  }
}

function parseTable(text: string): { head: string[]; ins: number; rows: string[][] } | null {
  const lines = text.trim().split("\n").filter((l) => l.trim());
  if (lines.length < 2) return null;
  const [l, r] = lines[0].split("|").map((p) => p.trim().split(/\s+/).filter(Boolean));
  const rows = lines.slice(1).map((ln) => ln.split("|").flatMap((p) => p.trim().split(/\s+/).filter(Boolean)));
  return { head: [...l, ...(r ?? [])], ins: l.length, rows };
}

function renderSpec() {
  const box = $("specInfo");
  box.replaceChildren();
  if (!model) return;
  box.append(el("div", { cls: "specName", textContent: model.name }));
  if (model.traits.length) box.append(el("div", { cls: "traits" }, ...model.traits.map((t) => el("span", { cls: "trait", textContent: t }))));
  if (model.description) box.append(el("div", { cls: "dim desc", textContent: model.description }));
}

function renderTests() {
  const box = $("tests");
  box.replaceChildren();
  if (!model) return;
  if (!model.tests.length) box.textContent = "No tests in this file.";
  const driven = drivenInputs();
  for (const t of model.tests as Test[]) {
    const active = t.name === selectedTest;
    const runBtn = el("button", { cls: "run", textContent: running && active ? "Running..." : "Run test", disabled: running,
      title: "Run pytest with REDSTONE_TRACE=1" });
    runBtn.onclick = (e) => { e.stopPropagation(); selectedTest = t.name; running = true; vscode.postMessage({ type: "run", test: t.name }); renderTests(); };
    const head = el("div", { cls: "testHead" }, el("b", { textContent: t.name }),
      (t.delay ?? t.max_delay) !== undefined ? el("span", { cls: "dim", textContent: ` delay ${t.delay ?? t.max_delay}t` }) : "",
      testFlags(t) ? el("span", { cls: "dim", textContent: ` ${testFlags(t)}` }) : "",
      active && trace?.failures.length ? el("span", { cls: "failTag", textContent: "failed" }) : "", runBtn);
    const card = el("div", { cls: "test" + (active ? " active" : "") }, head);
    card.onclick = () => selectTest(t.name);
    if (t.truth_table) {
      const tb = parseTable(t.truth_table);
      if (tb) {
        const table = el("table", { cls: "tt" });
        table.append(el("tr", {}, ...tb.head.map((h, i) => el("th", { textContent: h, cls: i < tb.ins ? "in" : "out" }))));
        tb.rows.forEach((r) => {
          const hit = active && trace?.frames && tb.head.slice(0, tb.ins).every((n, i) => driven[n] === (r[i] === "1")) &&
            Object.keys(driven).length > 0;
          table.append(el("tr", { cls: hit ? "hit" : "" }, ...r.map((v, i) => el("td", { textContent: v, cls: i < tb.ins ? "in" : "out" }))));
        });
        card.append(table);
      }
    }
    if (t.steps) card.append(stepList(t.steps));
    if (t.finally?.length) card.append(stepList(t.finally.map((c) => ({ finally: c }))));
    box.append(card);
  }
}

function stepList(steps: Record<string, unknown>[]): HTMLElement {
  const ol = el("ol", { cls: "steps" });
  for (const st of steps) {
    const [k, v] = Object.entries(st)[0] ?? ["?", ""];
    if (k === "repeat" && typeof v === "object" && v !== null) {
      const r = v as { times?: number; steps?: Record<string, unknown>[] };
      ol.append(el("li", {}, el("span", { cls: "kw " + k, textContent: k }), ` x${r.times ?? "?"}`, stepList(r.steps ?? [])));
      continue;
    }
    const body = typeof v === "object" && v !== null
      ? Object.entries(v as Record<string, unknown>).map(([a, b]) => `${a}=${b}`).join(" ") : String(v);
    ol.append(el("li", {}, el("span", { cls: "kw " + k, textContent: k }), " ", body));
  }
  return ol;
}

function renderPlayback() {
  const has = !!trace?.frames?.length;
  $("playbackEmpty").style.display = has ? "none" : "block";
  $("playbackBody").style.display = has ? "block" : "none";
  $("playbackEmpty").textContent = selectedTest
    ? (trace && trace.frames === null ? `No trace for "${selectedTest}" yet. Press Run test.` : "Loading trace...")
    : "Select a test to load its trace.";
  if (!has) return;
  const fr = trace!.frames!;
  $("traceNote").textContent = trace!.sparse ? "Sparse trace: only named cells were recorded; other cells show their placed state." : "";
  const fails = $("failures");
  if (fails.dataset.for !== trace!.path + trace!.failures.join("\n")) {
    fails.dataset.for = trace!.path + trace!.failures.join("\n");
    fails.replaceChildren(...parseFailures(trace!.failures, fr).map((f) => el("button", {
      cls: "fail", title: "Go to this tick", onclick: () => { stopPlay(); frameIdx = f.frame; renderFrame(); },
      textContent: `Test failed${f.tick === null ? "" : ` at tick ${f.tick}`}: ${f.message}`,
    })));
  }
  const slider = $<HTMLInputElement>("slider");
  slider.max = String(fr.length - 1);
  slider.value = String(frameIdx);
  const ev = currentEvent();
  $("eventLabel").textContent = ev ? ev.text : "";
  $("tickLabel").textContent = `tick ${fr[frameIdx].tick}   frame ${frameIdx + 1}/${fr.length}`;
  $("playBtn").textContent = playing ? "Pause" : "Play";
  const chips = $("eventChips");
  if (chips.dataset.for !== `${trace!.path}:${fr.length}`) {
    chips.replaceChildren();
    chips.dataset.for = `${trace!.path}:${fr.length}`;
    fr.forEach((f, i) => {
      if (!f.event) return;
      chips.append(el("button", { cls: "chip", textContent: `${f.tick}: ${f.event}`, title: f.reply ?? "", onclick: () => { frameIdx = i; renderAll(); } }));
    });
  }
}

function renderBar() {
  if (!model) return;
  const idx = model.layers.findIndex((l) => l.y === y);
  $("layerLabel").textContent = `y = ${y}  (${idx + 1}/${model.layers.length})`;
  $<HTMLInputElement>("belowChk").checked = showBelow;
  $("dims").textContent = `${width(model)} x ${height(model)}`;
}

function renderAll() {
  const banner = $("error");
  banner.style.display = errorText ? "block" : "none";
  banner.textContent = errorText;
  if (!model) return;
  if (!layerAt(model, y)) y = model.layers[0]?.y ?? 0;
  renderBar();
  renderSpec();
  renderMain();
  renderMinis();
  renderPalette();
  renderSelected();
  renderTests();
  renderPlayback();
  vscode.setState({ test: selectedTest });
}

/** Cheap refresh for playback ticks: no palette or test-list rebuild except the highlighted truth-table row. */
function renderFrame() {
  renderMain();
  renderMinis();
  renderPlayback();
  renderTests();
}

// ---------- editing ----------

function commit(next: Model) {
  model = next;
  vscode.postMessage({ type: "edit", model: next });
  renderAll();
}
function brushSpec(): CellSpec | null {
  if (labelKind === "none") return { state: brush };
  if (!labelName) return null;
  return { state: labelKind === "input" ? "air" : brush, label: { kind: labelKind, name: labelName } };
}
function paintAt(m: Model, x: number, z: number, erase: boolean, dragging: boolean): boolean {
  if (erase) return setCell(m, y, x, z, { state: "air" });
  const spec = brushSpec();
  if (!spec || (spec.label && dragging)) return false;
  return setCell(m, y, x, z, spec);
}
function cellFromEvent(e: MouseEvent): { x: number; z: number } | null {
  if (!model) return null;
  const r = $("canvas").getBoundingClientRect();
  const s = scale();
  const x = Math.floor((e.clientX - r.left) / s), z = Math.floor((e.clientY - r.top) / s);
  return x >= 0 && z >= 0 && x < width(model) && z < height(model) ? { x, z } : null;
}

function tip(e: MouseEvent, c: { x: number; z: number } | null) {
  const t = $("tip");
  if (!c || !model) { t.style.display = "none"; return; }
  const at = entryAt(model, y, c.x, c.z);
  const info = at && infoTable(model).get(at.glyph);
  const ct = frame() && info ? cellTrace(info, `${c.x},${y},${c.z}`, traceOpts()) : null;
  const lab = at && entryLabel(at.entry);
  t.replaceChildren(
    el("div", { textContent: `x=${c.x} y=${y} z=${c.z}` }),
    el("div", { textContent: at ? `minecraft:${entryState(at.entry).replace(/^minecraft:/, "")}` : "?" }),
    el("div", { cls: "dim", textContent: `glyph '${at?.glyph ?? ""}'${lab ? `   ${lab.kind}: ${lab.name}` : ""}` }),
    el("div", { textContent: !ct ? "no trace" : !ct.traced ? `not recorded${trace?.sparse ? " (sparse trace)" : ""}`
      : `trace level ${ct.level}${ct.strength !== undefined ? `, output strength ${ct.strength}` : ""}` }),
  );
  t.style.display = "block";
  t.style.left = `${Math.min(e.clientX + 14, window.innerWidth - 240)}px`;
  t.style.top = `${e.clientY + 14}px`;
}

function setupCanvas() {
  const cv = $("canvas");
  cv.addEventListener("contextmenu", (e) => e.preventDefault());
  cv.addEventListener("mousedown", (e) => {
    const c = cellFromEvent(e);
    if (!c || !model) return;
    if (tool === "select" && e.button === 0) { selected = c; renderAll(); return; }
    if (e.button !== 0 && e.button !== 2) return;
    strokeErase = e.button === 2;
    stroke = clone(model);
    paintAt(stroke, c.x, c.z, strokeErase, false);
    renderMain();
  });
  window.addEventListener("mousemove", (e) => {
    const c = e.target === cv ? cellFromEvent(e) : null;
    if (JSON.stringify(c) !== JSON.stringify(hover)) { hover = c; if (!stroke) renderMain(); }
    tip(e, c);
    if (stroke && c && paintAt(stroke, c.x, c.z, strokeErase, true)) renderMain();
  });
  cv.addEventListener("mouseleave", () => { hover = null; $("tip").style.display = "none"; if (!stroke) renderMain(); });
  window.addEventListener("mouseup", () => {
    if (!stroke || !model) return;
    const done = stroke;
    stroke = null;
    if (JSON.stringify(done) !== JSON.stringify(model)) commit(done); else renderAll();
  });
}

function mutate(fn: (m: Model) => boolean | void) {
  if (!model) return;
  const next = clone(model);
  if (fn(next) === false) return;
  commit(next);
}

function rotateHovered() {
  if (!model) return;
  const at = hover && entryAt(model, y, hover.x, hover.z);
  if (hover && at) {
    const rot = rotateState(entryState(at.entry));
    if (rot) { mutate((m) => setCell(m, y, hover!.x, hover!.z, { state: rot, label: entryLabel(at.entry), fixture: entryFixture(at.entry) })); return; }
  }
  const b = rotateState(brush);
  if (b) { brush = b; renderPalette(); }
}
function cycleDelay() {
  if (!model || !hover) return;
  const at = entryAt(model, y, hover.x, hover.z);
  if (!at) return;
  const { id, props, nbt } = parseState(entryState(at.entry));
  if (id !== "repeater") return;
  const d = (Number(props.delay ?? 1) % 4) + 1;
  const st = formatState(id, { ...props, delay: String(d) }, nbt);
  mutate((m) => setCell(m, y, hover!.x, hover!.z, { state: st, label: entryLabel(at.entry), fixture: entryFixture(at.entry) }));
}
function pick() {
  if (!model || !hover) return;
  const at = entryAt(model, y, hover.x, hover.z);
  if (!at) return;
  const lab = entryLabel(at.entry);
  brush = lab?.kind === "input" ? "air" : entryState(at.entry);
  labelKind = lab ? lab.kind : "none";
  labelName = lab ? lab.name : "";
  tool = "paint";
  renderAll();
}

function moveLayer(d: number) {
  if (!model) return;
  const ys = model.layers.map((l) => l.y);
  const i = ys.indexOf(y) + d;
  if (i >= 0 && i < ys.length) { y = ys[i]; renderAll(); }
}

// ---------- traces ----------

function selectTest(name: string) {
  selectedTest = name;
  trace = null;
  frameIdx = 0;
  stopPlay();
  vscode.postMessage({ type: "loadTrace", test: name });
  renderAll();
}
function stopPlay() { playing = false; if (timer) clearTimeout(timer); }
function tickPlay() {
  if (!playing || !trace?.frames) return;
  if (frameIdx >= trace.frames.length - 1) { stopPlay(); renderFrame(); return; }
  frameIdx++;
  renderFrame();
  timer = setTimeout(tickPlay, 50 / speed);
}
function togglePlay() {
  if (!trace?.frames) return;
  if (playing) { stopPlay(); renderPlayback(); return; }
  if (frameIdx >= trace.frames.length - 1) frameIdx = 0;
  playing = true;
  tickPlay();
}
function step(d: number) {
  if (!trace?.frames) return;
  stopPlay();
  frameIdx = Math.max(0, Math.min(trace.frames.length - 1, frameIdx + d));
  renderFrame();
}

// ---------- wiring ----------

function wire() {
  setupCanvas();
  $("layerDown").onclick = () => moveLayer(-1);
  $("layerUp").onclick = () => moveLayer(1);
  $("belowChk").onchange = (e) => { showBelow = (e.target as HTMLInputElement).checked; renderMain(); };
  $("zoomIn").onclick = () => { S = Math.min(96, scale() + 6); renderAll(); };
  $("zoomOut").onclick = () => { S = Math.max(12, scale() - 6); renderAll(); };
  $("zoomFit").onclick = () => { S = 0; renderAll(); };
  $("addAbove").onclick = () => mutate((m) => { y = addLayer(m, "above"); });
  $("addBelow").onclick = () => mutate((m) => { y = addLayer(m, "below"); });
  $("delLayer").onclick = () => mutate((m) => removeLayer(m, y));
  for (const e of ["north", "south", "west", "east"] as Edge[]) {
    $(`add_${e}`).onclick = () => mutate((m) => resize(m, e, 1));
    $(`del_${e}`).onclick = () => mutate((m) => resize(m, e, -1));
  }
  $("toolPaint").onclick = () => { tool = "paint"; renderPalette(); };
  $("toolSelect").onclick = () => { tool = "select"; renderPalette(); };
  $("labelKind").onchange = (e) => { labelKind = (e.target as HTMLSelectElement).value as typeof labelKind; renderPalette(); };
  $("labelName").oninput = (e) => { labelName = (e.target as HTMLInputElement).value.trim(); renderPalette(); };
  $("playBtn").onclick = togglePlay;
  $("stepBack").onclick = () => step(-1);
  $("stepFwd").onclick = () => step(1);
  $("toStart").onclick = () => step(-1e9);
  $("toEnd").onclick = () => step(1e9);
  $<HTMLInputElement>("slider").oninput = (e) => { stopPlay(); frameIdx = Number((e.target as HTMLInputElement).value); renderFrame(); };
  $<HTMLSelectElement>("speed").onchange = (e) => { speed = Number((e.target as HTMLSelectElement).value); };
  $("reloadTrace").onclick = () => selectedTest && vscode.postMessage({ type: "loadTrace", test: selectedTest });
  window.addEventListener("resize", () => renderMain());
  new MutationObserver(() => renderAll()).observe(document.body, { attributes: true, attributeFilter: ["class"] });
  window.addEventListener("keydown", (e) => {
    const t = e.target as HTMLElement;
    if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) && !(t.id === "slider")) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    switch (e.key) {
      case "[": case "PageDown": moveLayer(-1); break;
      case "]": case "PageUp": moveLayer(1); break;
      case "r": case "R": rotateHovered(); break;
      case "d": case "D": cycleDelay(); break;
      case "i": case "I": pick(); break;
      case " ": togglePlay(); break;
      case "ArrowLeft": step(-1); break;
      case "ArrowRight": step(1); break;
      default: return;
    }
    e.preventDefault();
  });
  window.addEventListener("message", (ev) => {
    const msg = ev.data;
    if (msg.type === "doc") {
      stroke = null;
      errorText = msg.error ?? "";
      if (msg.model) {
        const first = !model;
        model = msg.model as Model;
        // Open on the layer holding the named cells, which is where the circuit is.
        if (first) y = model.layers.find((l) => l.rows.some((r) => [...r].some((g) => {
          const e = model!.palette.find(([k]) => k === g)?.[1];
          return e && entryLabel(e);
        })))?.y ?? model.layers[model.layers.length - 1]?.y ?? 0;
      }
      if (model && (!selectedTest || !model.tests.some((t) => t.name === selectedTest))) {
        selectedTest = model.tests[0]?.name ?? null;
        if (selectedTest) vscode.postMessage({ type: "loadTrace", test: selectedTest });
      }
      renderAll();
    } else if (msg.type === "trace") {
      if (msg.test !== selectedTest) return;
      const had = trace?.frames?.length ?? 0;
      trace = { test: msg.test, frames: msg.frames, path: msg.path, sparse: !!msg.sparse, failures: msg.failures ?? [] };
      if (!msg.frames || frameIdx >= msg.frames.length || !had) frameIdx = 0;
      $("eventChips").dataset.for = "";
      renderAll();
    } else if (msg.type === "runState") {
      running = !!msg.running;
      renderTests();
    }
  });
  vscode.postMessage({ type: "ready" });
}

wire();
