// Builds out/harness/index.html: the real webview bundle with a stubbed VS Code API, one library file and its trace.
// Open it in a browser (or headless Chrome --screenshot / --dump-dom) to inspect the UI.
//   npm run build && npm run harness -- and_gate logic 110
import { mkdirSync, readFileSync, writeFileSync, copyFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { bodyMarkup } from "../src/webview/markup";
import { parseModel } from "../src/model";

const root = resolve(__dirname, "../../..");
const ext = resolve(__dirname, "../..");
const [file = "and_gate", testName = "logic", tickArg = "110"] = process.argv.slice(2);
const out = join(ext, "out/harness");
mkdirSync(out, { recursive: true });
copyFileSync(join(ext, "dist/webview.js"), join(out, "webview.js"));
copyFileSync(join(ext, "media/style.css"), join(out, "style.css"));
const model = parseModel(readFileSync(join(root, "library", `${file}.redstone.yaml`), "utf8"));
let frames: unknown = null;
try { frames = JSON.parse(readFileSync(join(root, "traces", file, `${testName}.json`), "utf8")).frames; } catch { /* no trace */ }
const vars = `
:root { --vscode-editor-background:#1e1e1e; --vscode-foreground:#cccccc; --vscode-font-family:sans-serif; --vscode-font-size:13px;
 --vscode-panel-border:#444; --vscode-button-secondaryBackground:#3a3d41; --vscode-button-secondaryForeground:#fff;
 --vscode-button-secondaryHoverBackground:#45494e; --vscode-focusBorder:#007fd4; --vscode-input-background:#3c3c3c; --vscode-input-foreground:#ccc;
 --vscode-editor-font-family:monospace; --vscode-editorHoverWidget-background:#252526; --vscode-editorHoverWidget-border:#454545; }`;
const script = `
window.__posted = [];
window.acquireVsCodeApi = () => ({ postMessage: (m) => window.__posted.push(m), getState: () => null, setState: () => {} });
`;
const drive = `
const model = ${JSON.stringify(model)}, frames = ${JSON.stringify(frames)};
window.addEventListener('load', () => {
  const send = (m) => window.dispatchEvent(new MessageEvent('message', { data: m }));
  send({ type: 'doc', model });
  send({ type: 'trace', test: ${JSON.stringify(testName)}, frames, path: 'x' });
  const slider = document.getElementById('slider');
  slider.value = String(frames ? frames.findIndex((f) => f.tick >= ${Number(tickArg)}) : 0);
  slider.dispatchEvent(new Event('input'));
  // Paint a cell through real mouse events, then report what the webview asked the extension to write.
  const cv = document.getElementById('canvas'), r = cv.getBoundingClientRect(), S = r.width / model.layers[0].rows[0].length;
  const at = (x, z, t, b) => cv.dispatchEvent(new MouseEvent(t, { bubbles: true, clientX: r.left + (x + .5) * S, clientY: r.top + (z + .5) * S, button: b }));
  at(0, 0, 'mousemove', 0);
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'r' }));
  at(1, 0, 'mousedown', 2); window.dispatchEvent(new MouseEvent('mouseup'));
  const edits = window.__posted.filter((m) => m.type === 'edit');
  const el = document.createElement('pre'); el.id = 'report';
  el.textContent = JSON.stringify({ posted: window.__posted.map((m) => m.type), rows: edits.length ? edits[0].model.layers[0].rows : null });
  document.body.appendChild(el);
});`;
const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><link rel="stylesheet" href="style.css"><style>${vars}</style></head>
<body>${bodyMarkup()}<script>${script}</script><script src="webview.js"></script><script>${drive}</script></body></html>`;
writeFileSync(join(out, "index.html"), html);
console.log(join(out, "index.html"));
