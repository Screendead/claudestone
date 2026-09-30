import { Model, entryLabel, entryState, Label, parseState, layerAt, width, height } from "./model";

export type Signals = Record<string, number>;
export interface Theme { bg: string; cell: string; grid: string; fg: string; hover: string; select: string }
export interface DrawOpts {
  y: number;
  S: number;
  signals: Signals | null;
  /** Driver state inferred from trace events; inputs are air, so the trace has no signal for them. */
  inputs?: Record<string, boolean>;
  showBelow: boolean;
  compass?: boolean;
  theme: Theme;
  hover?: { x: number; z: number } | null;
  selected?: { x: number; z: number } | null;
}
export interface Info {
  glyph: string;
  state: string;
  id: string;
  props: Record<string, string>;
  label?: Label;
}

type Ctx = CanvasRenderingContext2D;
type Dir = "north" | "east" | "south" | "west";
const DIRS: Dir[] = ["north", "east", "south", "west"];
const VEC: Record<Dir, [number, number]> = { north: [0, -1], east: [1, 0], south: [0, 1], west: [-1, 0] };
const OPP: Record<Dir, Dir> = { north: "south", south: "north", east: "west", west: "east" };
const ANGLE: Record<Dir, number> = { north: 0, east: Math.PI / 2, south: Math.PI, west: -Math.PI / 2 };

export function infoTable(model: Model): Map<string, Info> {
  const t = new Map<string, Info>();
  for (const [glyph, e] of model.palette) {
    const state = entryState(e);
    const { id, props } = parseState(state);
    t.set(glyph, { glyph, state, id, props, label: entryLabel(e) });
  }
  return t;
}

export function infoAt(model: Model, table: Map<string, Info>, x: number, y: number, z: number): Info | undefined {
  const g = layerAt(model, y)?.rows[z]?.[x];
  return g === undefined ? undefined : table.get(g);
}

const COLOURS: Record<string, string> = {
  white: "#cfd5d6", orange: "#e06101", magenta: "#a9309f", light_blue: "#2389c7", yellow: "#f1af15",
  lime: "#5ea918", pink: "#d5658f", gray: "#373a3e", light_gray: "#7d7d73", cyan: "#157788",
  purple: "#64209c", blue: "#2c2f8f", brown: "#603c20", green: "#495b24", red: "#8e2121", black: "#080a0f",
};
const SOLIDS: Record<string, string> = {
  stone: "#7d7d7d", smooth_stone: "#a5a5a5", cobblestone: "#6b6b6b", stone_bricks: "#777777",
  andesite: "#888888", granite: "#9a6b58", diorite: "#bfbfbf", deepslate: "#4a4a50", obsidian: "#1b1030",
  dirt: "#866043", oak_planks: "#a2824f", spruce_planks: "#6b5030", iron_block: "#dcdcdc", gold_block: "#f5d33c",
  quartz_block: "#ece6df", sand: "#dbcf9b", netherrack: "#6f3536", bedrock: "#3a3a3a", glass: "#a9d8e8",
  grass_block: "#5b8c3a", sandstone: "#d8cb9a", bricks: "#96574a", coal_block: "#181818", diamond_block: "#5fdcd0",
};

export function solidColour(id: string): string | undefined {
  const m = /^(.*)_(concrete|wool|terracotta|concrete_powder|stained_glass)$/.exec(id);
  if (m && COLOURS[m[1]]) return COLOURS[m[1]];
  return SOLIDS[id];
}

const NON_SOLID = /^(air|redstone_wire|repeater|comparator|redstone_torch|redstone_wall_torch|lever|.*_button|.*_pressure_plate|torch|wall_torch)$/;
const isSolid = (i: Info | undefined) => !!i && !i.label?.kind.startsWith("input") && !NON_SOLID.test(i.id);
const isSource = (i: Info) =>
  /^(redstone_torch|redstone_wall_torch|lever|redstone_block|.*_button|.*_pressure_plate)$/.test(i.id);

function dirOf(v: string | undefined): Dir | undefined {
  return DIRS.find((d) => d === v);
}

/** Approximate vanilla connection rules for a dust arm from (x,y,z) toward `d`. */
function dustConnects(model: Model, t: Map<string, Info>, x: number, y: number, z: number, d: Dir): boolean {
  const [dx, dz] = VEC[d];
  const n = infoAt(model, t, x + dx, y, z + dz);
  if (n) {
    if (n.id === "redstone_wire" || isSource(n) || n.label?.kind === "input") return true;
    if (n.id === "repeater" || n.id === "comparator" || n.id === "observer") {
      const f = dirOf(n.props.facing);
      if (f && (f === d || f === OPP[d])) return true;
    }
  }
  const up = infoAt(model, t, x + dx, y + 1, z + dz);
  if (up?.id === "redstone_wire" && !isSolid(infoAt(model, t, x, y + 1, z))) return true;
  const down = infoAt(model, t, x + dx, y - 1, z + dz);
  if (down?.id === "redstone_wire" && !isSolid(n)) return true;
  return false;
}

function dustColour(level: number): string {
  const k = Math.max(0, Math.min(15, level)) / 15;
  return `rgb(${Math.round(75 + 180 * k)},${Math.round(8 + 28 * k)},${Math.round(8 + 20 * k)})`;
}

function glow(c: Ctx, cx: number, cy: number, r: number, colour: string) {
  const g = c.createRadialGradient(cx, cy, 0, cx, cy, r);
  g.addColorStop(0, colour);
  g.addColorStop(1, "rgba(255,180,60,0)");
  c.fillStyle = g;
  c.beginPath();
  c.arc(cx, cy, r, 0, Math.PI * 2);
  c.fill();
}

function text(c: Ctx, s: string, x: number, y: number, size: number, fill: string, align: CanvasTextAlign = "center") {
  c.font = `bold ${Math.max(7, Math.round(size))}px sans-serif`;
  c.textAlign = align;
  c.textBaseline = "middle";
  c.fillStyle = fill;
  c.fillText(s, x, y);
}

function torchHead(c: Ctx, cx: number, cy: number, r: number, lit: boolean) {
  if (lit) glow(c, cx, cy, r * 2.6, "rgba(255,70,40,0.55)");
  c.fillStyle = lit ? "#ff3a1c" : "#4a1a14";
  c.beginPath();
  c.arc(cx, cy, r, 0, Math.PI * 2);
  c.fill();
  c.strokeStyle = lit ? "#ffb08a" : "#2a0c08";
  c.lineWidth = 1;
  c.stroke();
}

interface Cell {
  info: Info;
  x: number; y: number; z: number;
  px: number; py: number; S: number;
  level: number;
  traced: boolean;
  driven?: boolean;
}

function drawDust(c: Ctx, k: Cell, model: Model, t: Map<string, Info>) {
  const { S } = k;
  const cx = k.px + S / 2, cy = k.py + S / 2;
  const arms = DIRS.filter((d) => dustConnects(model, t, k.x, k.y, k.z, d));
  const on: Dir[] = [...arms];
  if (arms.length === 0) on.push(...DIRS);
  else if (arms.length === 1) on.push(OPP[arms[0]]);
  const col = k.traced || k.level ? dustColour(k.level) : dustColour(Number(k.info.props.power ?? 0));
  const reach = (d: Dir) => (arms.length === 0 ? 0.22 : arms.includes(d) ? 0.5 : 0.22) * S;
  if (k.level > 0) glow(c, cx, cy, S * 0.55, `rgba(255,50,30,${0.15 + 0.3 * (k.level / 15)})`);
  c.strokeStyle = col;
  c.lineWidth = Math.max(2, S * 0.2);
  c.lineCap = "butt";
  for (const d of on) {
    const [dx, dz] = VEC[d];
    c.beginPath();
    c.moveTo(cx, cy);
    c.lineTo(cx + dx * reach(d), cy + dz * reach(d));
    c.stroke();
  }
  c.fillStyle = col;
  c.beginPath();
  c.arc(cx, cy, S * 0.13, 0, Math.PI * 2);
  c.fill();
  if (k.level > 0 && S >= 36) text(c, String(k.level), cx, cy, S * 0.2, "#fff");
}

function drawDiode(c: Ctx, k: Cell) {
  const { S, info } = k;
  const facing = dirOf(info.props.facing) ?? "north";
  const flow = OPP[facing];
  const cmp = info.id === "comparator";
  c.save();
  c.translate(k.px + S / 2, k.py + S / 2);
  c.rotate(ANGLE[flow]);
  c.translate(-S / 2, -S / 2);
  // Canonical orientation: signal flows up, input at the bottom.
  c.fillStyle = "#9a9a9a";
  c.fillRect(S * 0.06, S * 0.06, S * 0.88, S * 0.88);
  c.strokeStyle = "#5c5c5c";
  c.lineWidth = 1.5;
  c.strokeRect(S * 0.06, S * 0.06, S * 0.88, S * 0.88);
  c.fillStyle = "#b4b4b4";
  c.fillRect(S * 0.12, S * 0.12, S * 0.76, S * 0.76);
  const lit = k.level > 0;
  const r = S * 0.075;
  if (cmp) {
    const sub = info.props.mode === "subtract";
    torchHead(c, S * 0.5, S * 0.22, r * 1.15, sub || lit);
    torchHead(c, S * 0.3, S * 0.74, r, false);
    torchHead(c, S * 0.7, S * 0.74, r, false);
  } else {
    const delay = Math.max(1, Math.min(4, Number(info.props.delay ?? 1)));
    torchHead(c, S * 0.5, S * 0.22, r, lit);
    torchHead(c, S * 0.5, S * (0.8 - 0.13 * (delay - 1)), r, false);
  }
  // Flow arrow between the two torches.
  c.fillStyle = "rgba(20,20,20,0.75)";
  c.beginPath();
  c.moveTo(S * 0.5, S * 0.36);
  c.lineTo(S * 0.65, S * 0.5);
  c.lineTo(S * 0.55, S * 0.5);
  c.lineTo(S * 0.55, S * 0.6);
  c.lineTo(S * 0.45, S * 0.6);
  c.lineTo(S * 0.45, S * 0.5);
  c.lineTo(S * 0.35, S * 0.5);
  c.closePath();
  c.fill();
  c.restore();
  const tag = cmp ? (info.props.mode === "subtract" ? "SUB" : "CMP") : `${info.props.delay ?? 1}t`;
  text(c, tag, k.px + S * 0.9, k.py + S * 0.9, S * 0.2, "#111", "right");
}

function drawTorch(c: Ctx, k: Cell) {
  const { S, info } = k;
  const lit = k.traced ? k.level > 0 : info.props.lit !== "false";
  const cx = k.px + S / 2, cy = k.py + S / 2;
  const wall = info.id === "redstone_wall_torch" || info.id === "wall_torch";
  const facing = dirOf(info.props.facing);
  if (wall && facing) {
    const [ax, az] = VEC[OPP[facing]];
    const hx = cx + ax * S * 0.2, hy = cy + az * S * 0.2;
    c.strokeStyle = "#6b4a25";
    c.lineWidth = Math.max(2, S * 0.1);
    c.lineCap = "round";
    c.beginPath();
    c.moveTo(cx + ax * S * 0.48, cy + az * S * 0.48);
    c.lineTo(hx, hy);
    c.stroke();
    c.lineCap = "butt";
    torchHead(c, hx, hy, S * 0.14, lit);
  } else {
    c.fillStyle = "#6b4a25";
    c.beginPath();
    c.arc(cx, cy, S * 0.11, 0, Math.PI * 2);
    c.fill();
    torchHead(c, cx, cy, S * 0.15, lit);
  }
}

function drawLamp(c: Ctx, k: Cell) {
  const { S } = k;
  const lit = k.traced ? k.level > 0 : k.info.props.lit === "true";
  if (lit) glow(c, k.px + S / 2, k.py + S / 2, S * 0.85, "rgba(255,220,90,0.6)");
  c.fillStyle = lit ? "#ffd75a" : "#5a3d24";
  c.fillRect(k.px + S * 0.06, k.py + S * 0.06, S * 0.88, S * 0.88);
  c.strokeStyle = lit ? "#fff2b0" : "#8b6a45";
  c.lineWidth = 1.5;
  c.strokeRect(k.px + S * 0.14, k.py + S * 0.14, S * 0.72, S * 0.72);
  c.beginPath();
  c.moveTo(k.px + S * 0.5, k.py + S * 0.14);
  c.lineTo(k.px + S * 0.5, k.py + S * 0.86);
  c.moveTo(k.px + S * 0.14, k.py + S * 0.5);
  c.lineTo(k.px + S * 0.86, k.py + S * 0.5);
  c.stroke();
}

function attached(info: Info): { wall: boolean; toward: Dir; face: string } {
  const face = info.props.face ?? "wall";
  const facing = dirOf(info.props.facing) ?? "north";
  return { wall: face === "wall", toward: OPP[facing], face };
}

function drawSwitch(c: Ctx, k: Cell) {
  const { S, info } = k;
  const powered = k.traced ? k.level > 0 : info.props.powered === "true";
  const { wall, toward, face } = attached(info);
  const cx = k.px + S / 2, cy = k.py + S / 2;
  const lever = info.id === "lever";
  const accent = powered ? "#ff3a1c" : "#8a8a8a";
  if (powered) glow(c, cx, cy, S * 0.6, "rgba(255,60,30,0.35)");
  if (wall) {
    const [ax, az] = VEC[toward];
    const depth = lever ? 0.16 : 0.1;
    const bx = cx + ax * S * (0.5 - depth / 2), by = cy + az * S * (0.5 - depth / 2);
    const w = ax === 0 ? S * (lever ? 0.4 : 0.34) : S * depth, h = az === 0 ? S * (lever ? 0.4 : 0.34) : S * depth;
    c.fillStyle = lever ? "#6f6f6f" : "#9d9d9d";
    c.fillRect(bx - w / 2, by - h / 2, w, h);
    if (lever) {
      const len = S * (powered ? 0.36 : 0.22);
      c.strokeStyle = powered ? "#c8a06a" : "#8a6a3a";
      c.lineWidth = Math.max(2, S * 0.09);
      c.beginPath();
      c.moveTo(bx, by);
      c.lineTo(bx - ax * len, by - az * len);
      c.stroke();
      c.fillStyle = accent;
      c.beginPath();
      c.arc(bx - ax * len, by - az * len, S * 0.06, 0, Math.PI * 2);
      c.fill();
    } else {
      const th = S * (powered ? 0.07 : 0.14);
      const ex = cx + ax * S * (0.5 - depth) , ey = cy + az * S * (0.5 - depth);
      c.fillStyle = powered ? "#c9c9c9" : "#b5b5b5";
      const ww = ax === 0 ? S * 0.22 : th, hh = az === 0 ? S * 0.22 : th;
      c.fillRect(ex - ax * th / 2 - ww / 2, ey - az * th / 2 - hh / 2, ww, hh);
      if (powered) { c.strokeStyle = "#ff3a1c"; c.lineWidth = 1.5; c.strokeRect(ex - ax * th / 2 - ww / 2, ey - az * th / 2 - hh / 2, ww, hh); }
    }
  } else {
    const ceil = face === "ceiling";
    c.fillStyle = lever ? "#6f6f6f" : "#b5b5b5";
    const s = S * (lever ? 0.4 : 0.32);
    c.fillRect(cx - s / 2, cy - s / 2, s, s);
    if (lever) {
      const sg = powered ? 1 : -1;
      c.strokeStyle = "#8a6a3a";
      c.lineWidth = Math.max(2, S * 0.09);
      c.beginPath();
      c.moveTo(cx, cy);
      c.lineTo(cx + sg * S * 0.2, cy + sg * S * 0.2);
      c.stroke();
      c.fillStyle = accent;
      c.beginPath();
      c.arc(cx + sg * S * 0.2, cy + sg * S * 0.2, S * 0.06, 0, Math.PI * 2);
      c.fill();
    } else if (powered) {
      c.strokeStyle = "#ff3a1c";
      c.strokeRect(cx - s / 2, cy - s / 2, s, s);
    }
    if (ceil) text(c, "^", cx, cy - s, S * 0.16, "#ccc");
  }
  text(c, lever ? "L" : "B", k.px + S * 0.5, k.py + S * 0.5, S * 0.16, "rgba(255,255,255,0.6)");
}

function drawRedstoneBlock(c: Ctx, k: Cell) {
  const { S } = k;
  glow(c, k.px + S / 2, k.py + S / 2, S * 0.8, "rgba(255,40,20,0.35)");
  c.fillStyle = "#b31212";
  c.fillRect(k.px + S * 0.06, k.py + S * 0.06, S * 0.88, S * 0.88);
  c.strokeStyle = "#e84a3a";
  c.lineWidth = 2;
  c.strokeRect(k.px + S * 0.06, k.py + S * 0.06, S * 0.88, S * 0.88);
  c.strokeStyle = "#6e0808";
  c.lineWidth = 1.5;
  c.beginPath();
  c.moveTo(k.px + S * 0.2, k.py + S * 0.5);
  c.lineTo(k.px + S * 0.8, k.py + S * 0.5);
  c.moveTo(k.px + S * 0.5, k.py + S * 0.2);
  c.lineTo(k.px + S * 0.5, k.py + S * 0.8);
  c.stroke();
}

function drawSolid(c: Ctx, k: Cell, colour: string) {
  const { S } = k;
  c.fillStyle = colour;
  c.fillRect(k.px + S * 0.04, k.py + S * 0.04, S * 0.92, S * 0.92);
  c.strokeStyle = "rgba(0,0,0,0.35)";
  c.lineWidth = 1;
  c.strokeRect(k.px + S * 0.04 + 0.5, k.py + S * 0.04 + 0.5, S * 0.92 - 1, S * 0.92 - 1);
}

function drawUnknown(c: Ctx, k: Cell) {
  drawSolid(c, k, "#6a6a6a");
  text(c, k.info.glyph, k.px + k.S / 2, k.py + k.S / 2, k.S * 0.45, "#eee");
}

function drawBlock(c: Ctx, k: Cell, model: Model, t: Map<string, Info>) {
  const id = k.info.id;
  if (k.info.label?.kind === "input") {
    const on = k.level > 0 || !!k.driven;
    c.setLineDash([4, 3]);
    c.strokeStyle = on ? "#ff3a1c" : "#5d8fd6";
    c.lineWidth = 1.5;
    c.strokeRect(k.px + k.S * 0.12, k.py + k.S * 0.12, k.S * 0.76, k.S * 0.76);
    c.setLineDash([]);
    if (on) { c.fillStyle = "rgba(255,58,28,0.35)"; c.fillRect(k.px + k.S * 0.12, k.py + k.S * 0.12, k.S * 0.76, k.S * 0.76); }
    text(c, "IN", k.px + k.S / 2, k.py + k.S / 2, k.S * 0.24, on ? "#ff8a70" : "#7aa6e6");
    return;
  }
  if (id === "air") return;
  if (id === "redstone_wire") return drawDust(c, k, model, t);
  if (id === "repeater" || id === "comparator") return drawDiode(c, k);
  if (id === "redstone_torch" || id === "redstone_wall_torch" || id === "torch" || id === "wall_torch") return drawTorch(c, k);
  if (id === "redstone_lamp") return drawLamp(c, k);
  if (id === "lever" || id.endsWith("_button")) return drawSwitch(c, k);
  if (id === "redstone_block") return drawRedstoneBlock(c, k);
  const col = solidColour(id);
  if (col) return drawSolid(c, k, col);
  drawUnknown(c, k);
}

function badge(c: Ctx, k: Cell) {
  const l = k.info.label;
  if (!l) return;
  const size = Math.max(8, k.S * 0.22);
  c.font = `bold ${Math.round(size)}px sans-serif`;
  let s = l.name;
  while (s.length > 1 && c.measureText(s).width > k.S - 4) s = s.slice(0, -1);
  const w = c.measureText(s).width + 4, h = size + 3;
  c.fillStyle = l.kind === "input" ? "#2f6fbf" : l.kind === "output" ? "#2a9a4a" : "#9a5fc0";
  c.fillRect(k.px + 1, k.py + 1, w, h);
  text(c, s, k.px + 3, k.py + 1 + h / 2, size, "#fff", "left");
}

export function drawLayer(c: Ctx, model: Model, o: DrawOpts): void {
  const w = width(model), h = height(model), S = o.S;
  const t = infoTable(model);
  c.clearRect(0, 0, w * S, h * S);
  c.fillStyle = o.theme.bg;
  c.fillRect(0, 0, w * S, h * S);
  const pass = (y: number, alpha: number, labels: boolean) => {
    c.save();
    c.globalAlpha = alpha;
    for (let z = 0; z < h; z++) for (let x = 0; x < w; x++) {
      const info = infoAt(model, t, x, y, z);
      if (!info) continue;
      const key = `${x},${y},${z}`;
      const level = o.signals?.[key] ?? 0;
      const k: Cell = { info, x, y, z, px: x * S, py: z * S, S, level, traced: !!o.signals,
        driven: info.label?.kind === "input" && !!o.inputs?.[info.label.name] };
      drawBlock(c, k, model, t);
    }
    c.restore();
    if (labels) for (let z = 0; z < h; z++) for (let x = 0; x < w; x++) {
      const info = infoAt(model, t, x, y, z);
      if (info?.label) badge(c, { info, x, y, z, px: x * S, py: z * S, S, level: 0, traced: false });
    }
  };
  // Cell backgrounds and grid.
  c.strokeStyle = o.theme.grid;
  c.lineWidth = 1;
  for (let z = 0; z < h; z++) for (let x = 0; x < w; x++) {
    c.fillStyle = o.theme.cell;
    c.fillRect(x * S + 1, z * S + 1, S - 2, S - 2);
  }
  if (o.showBelow && layerAt(model, o.y - 1)) pass(o.y - 1, 0.3, false);
  pass(o.y, 1, true);
  c.strokeStyle = o.theme.grid;
  for (let x = 0; x <= w; x++) { c.beginPath(); c.moveTo(x * S + 0.5, 0); c.lineTo(x * S + 0.5, h * S); c.stroke(); }
  for (let z = 0; z <= h; z++) { c.beginPath(); c.moveTo(0, z * S + 0.5); c.lineTo(w * S, z * S + 0.5); c.stroke(); }
  // North marker.
  if (o.compass !== false) text(c, "N", w * S - 8, 8, 10, o.theme.fg, "center");
  const box = (p: { x: number; z: number } | null | undefined, colour: string) => {
    if (!p) return;
    c.strokeStyle = colour;
    c.lineWidth = 2;
    c.strokeRect(p.x * S + 1, p.z * S + 1, S - 2, S - 2);
  };
  box(o.selected, o.theme.select);
  box(o.hover, o.theme.hover);
}
