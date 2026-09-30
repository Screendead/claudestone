import * as vscode from "vscode";
import * as fs from "node:fs";
import { randomBytes } from "node:crypto";
import * as path from "node:path";
import { bodyMarkup } from "./webview/markup";
import { applyModel, Model, parseModel } from "./model";

const VIEW_TYPE = "redstone.viewer";

/** Workspace root that holds traces/ and .venv: the workspace folder, else the nearest ancestor that looks like the repo. */
function repoRoot(doc: vscode.TextDocument): string {
  const wf = vscode.workspace.getWorkspaceFolder(doc.uri);
  if (wf) return wf.uri.fsPath;
  let dir = path.dirname(doc.uri.fsPath);
  for (let i = 0; i < 6; i++) {
    if (fs.existsSync(path.join(dir, "traces")) || fs.existsSync(path.join(dir, ".venv"))) return dir;
    dir = path.dirname(dir);
  }
  return path.dirname(doc.uri.fsPath);
}

function tracePath(root: string, spec: string, test: string): string {
  return path.join(root, "traces", spec, `${test}.json`);
}

class Panel {
  test: string | null = null;
  constructor(readonly doc: vscode.TextDocument, readonly web: vscode.Webview) {}
  get root() { return repoRoot(this.doc); }
  post(m: unknown) { void this.web.postMessage(m); }

  sendDoc() {
    try {
      this.post({ type: "doc", model: parseModel(this.doc.getText()) });
    } catch (e) {
      this.post({ type: "doc", error: `Cannot parse ${path.basename(this.doc.fileName)}: ${(e as Error).message}` });
    }
  }

  sendTrace() {
    if (!this.test) return;
    let specName = "";
    try { specName = parseModel(this.doc.getText()).name; } catch { return; }
    const p = tracePath(this.root, specName, this.test);
    let frames: unknown = null;
    try { frames = JSON.parse(fs.readFileSync(p, "utf8")).frames; } catch { /* no trace yet */ }
    this.post({ type: "trace", test: this.test, frames, path: p });
  }

  async edit(model: Model) {
    const text = this.doc.getText();
    let next: string;
    try { next = applyModel(text, model); } catch (e) {
      void vscode.window.showErrorMessage(`Redstone: cannot apply edit: ${(e as Error).message}`);
      return;
    }
    if (next === text) return;
    let a = 0;
    const max = Math.min(text.length, next.length);
    while (a < max && text[a] === next[a]) a++;
    let b = 0;
    while (b < max - a && text[text.length - 1 - b] === next[next.length - 1 - b]) b++;
    const we = new vscode.WorkspaceEdit();
    we.replace(this.doc.uri, new vscode.Range(this.doc.positionAt(a), this.doc.positionAt(text.length - b)), next.slice(a, next.length - b));
    await vscode.workspace.applyEdit(we);
  }

  async run(test: string) {
    let spec = "";
    try { spec = parseModel(this.doc.getText()).name; } catch { return; }
    // An exact node id: a -k expression breaks on test names containing and/or/not.
    const nodeId = `tests/test_library.py::test_spec[${spec}::${test}]`;
    const root = this.root;
    const python = fs.existsSync(path.join(root, ".venv/bin/python")) ? ".venv/bin/python" : "python3";
    const task = new vscode.Task(
      { type: "redstone-test" }, vscode.workspace.getWorkspaceFolder(this.doc.uri) ?? vscode.TaskScope.Workspace,
      `redstone: ${spec} / ${test}`, "redstone",
      new vscode.ShellExecution(python, ["-m", "pytest", "-q", nodeId], { cwd: root, env: { REDSTONE_TRACE: "1" } }),
    );
    task.presentationOptions = { reveal: vscode.TaskRevealKind.Always, clear: true };
    this.post({ type: "runState", running: true });
    const done = vscode.tasks.onDidEndTask((e) => {
      if (e.execution.task !== task && e.execution.task.name !== task.name) return;
      done.dispose();
      this.post({ type: "runState", running: false });
      this.sendTrace();
    });
    try { await vscode.tasks.executeTask(task); } catch (e) {
      done.dispose();
      this.post({ type: "runState", running: false });
      void vscode.window.showErrorMessage(`Redstone: could not start test: ${(e as Error).message}`);
    }
  }
}

class Provider implements vscode.CustomTextEditorProvider {
  private panels = new Set<Panel>();
  private watchers = new Map<string, vscode.FileSystemWatcher>();
  constructor(private ctx: vscode.ExtensionContext) {}

  async resolveCustomTextEditor(doc: vscode.TextDocument, wp: vscode.WebviewPanel): Promise<void> {
    const media = vscode.Uri.joinPath(this.ctx.extensionUri, "media");
    const dist = vscode.Uri.joinPath(this.ctx.extensionUri, "dist");
    wp.webview.options = { enableScripts: true, localResourceRoots: [media, dist] };
    wp.webview.html = html(wp.webview, media, dist);
    const panel = new Panel(doc, wp.webview);
    this.panels.add(panel);
    this.watch(panel.root);

    const sub = vscode.workspace.onDidChangeTextDocument((e) => {
      if (e.document.uri.toString() === doc.uri.toString()) panel.sendDoc();
    });
    wp.webview.onDidReceiveMessage((m) => {
      switch (m.type) {
        case "ready": panel.sendDoc(); break;
        case "edit": void panel.edit(m.model); break;
        case "loadTrace": panel.test = m.test; panel.sendTrace(); break;
        case "run": panel.test = m.test; void panel.run(m.test); break;
      }
    });
    wp.onDidDispose(() => { sub.dispose(); this.panels.delete(panel); });
  }

  private watch(root: string) {
    if (this.watchers.has(root)) return;
    const w = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(root, "traces/**/*.json"));
    let t: ReturnType<typeof setTimeout> | undefined;
    const reload = () => {
      if (t) clearTimeout(t);
      t = setTimeout(() => { for (const p of this.panels) if (p.root === root) p.sendTrace(); }, 150);
    };
    w.onDidChange(reload); w.onDidCreate(reload); w.onDidDelete(reload);
    this.watchers.set(root, w);
    this.ctx.subscriptions.push(w);
  }
}

function html(web: vscode.Webview, media: vscode.Uri, dist: vscode.Uri): string {
  const nonce = randomBytes(16).toString("hex");
  const css = web.asWebviewUri(vscode.Uri.joinPath(media, "style.css"));
  const js = web.asWebviewUri(vscode.Uri.joinPath(dist, "webview.js"));
return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${web.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; img-src ${web.cspSource} data:;">
<link rel="stylesheet" href="${css}"><title>Redstone</title></head><body>
${bodyMarkup()}
<script nonce="${nonce}" src="${js}"></script></body></html>`;
}

export function activate(ctx: vscode.ExtensionContext) {
  ctx.subscriptions.push(
    vscode.window.registerCustomEditorProvider(VIEW_TYPE, new Provider(ctx), { webviewOptions: { retainContextWhenHidden: false } }),
    vscode.commands.registerCommand("redstone.openViewer", (uri?: vscode.Uri) => {
      const u = uri ?? vscode.window.activeTextEditor?.document.uri;
      if (u) void vscode.commands.executeCommand("vscode.openWith", u, VIEW_TYPE);
    }),
  );
}
export function deactivate() {}
