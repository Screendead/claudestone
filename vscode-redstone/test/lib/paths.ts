import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { parseModel } from "../../src/model";

// Bundled to out/test/*.cjs, so paths are relative to that directory.
export const ext = resolve(__dirname, "../..");
export const repo = resolve(ext, "..");
export const fixtures = join(ext, "test/fixtures");

/** Every *.redstone.yaml under dir, at any depth. */
export function specFiles(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? specFiles(p) : p.endsWith(".redstone.yaml") ? [p] : [];
  }).sort();
}

/** A spec file by its `name:`, searched in each library root in order. */
export function findSpec(name: string, roots = [join(fixtures, "library")]): string {
  for (const root of roots) for (const p of specFiles(root)) {
    if (p.endsWith(`/${name}.redstone.yaml`) && parseModel(readFileSync(p, "utf8")).name === name) return p;
  }
  for (const root of roots) for (const p of specFiles(root)) {
    if (parseModel(readFileSync(p, "utf8")).name === name) return p;
  }
  throw new Error(`no spec named ${name} under ${roots.join(", ")}`);
}

export const fixture = (name: string) => readFileSync(findSpec(name), "utf8");

/** Loads a spec with the repo's Python loader (offline: no server involved). */
export const pyLoad = (path: string) => JSON.parse(execFileSync(join(repo, ".venv/bin/python"), ["-c", `
import json, sys
from redstone.fileformat import load
s = load(sys.argv[1])
print(json.dumps({"blocks": {",".join(map(str, p)): b.removeprefix("minecraft:") for p, b in s.build.blocks.items()},
  "inputs": {k: list(v) for k, v in s.inputs.items()}, "named": {k: list(v) for k, v in s.named.items()}, "outputs": list(s.outputs),
  "cells": [list(p) for p in s.input_cells("s")] if "s" in s.inputs else [],
  "fixtures": sorted(map(list, s.fixtures)), "reserved": sorted(map(list, s.reserved))}))
`, path], { cwd: repo, encoding: "utf8" }));
