import * as esbuild from "esbuild";
import { readdirSync } from "node:fs";

const watch = process.argv.includes("--watch");
const tests = process.argv.includes("--tests");

if (tests) {
  const entries = readdirSync("test").filter((f) => f.endsWith(".ts")).map((f) => `test/${f}`);
  await esbuild.build({
    entryPoints: entries, bundle: true, platform: "node", format: "cjs", outdir: "out/test",
    outExtension: { ".js": ".cjs" }, external: ["@napi-rs/canvas"], logLevel: "warning",
  });
} else {
  const common = { bundle: true, sourcemap: true, logLevel: "info", minify: false };
  const ext = { ...common, entryPoints: ["src/extension.ts"], outfile: "dist/extension.js",
    platform: "node", format: "cjs", external: ["vscode"] };
  const web = { ...common, entryPoints: ["src/webview/main.ts"], outfile: "dist/webview.js",
    platform: "browser", format: "iife", target: "es2022" };
  if (watch) {
    for (const o of [ext, web]) await (await esbuild.context(o)).watch();
  } else {
    await Promise.all([esbuild.build(ext), esbuild.build(web)]);
  }
}
