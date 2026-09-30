import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parseModel } from "../src/model";
import { testFlags } from "../src/webview/text";
import { ext, fixture } from "./lib/paths";

test("README describes the test command the extension runs", () => {
  const readme = readFileSync(join(ext, "README.md"), "utf8");
  const src = readFileSync(join(ext, "src/extension.ts"), "utf8");
  assert.ok(src.includes("tests/test_library.py::test_spec[${spec}::${test}]"));
  assert.ok(readme.includes("tests/test_library.py::test_spec[<spec>::<test>]"));
  assert.ok(readme.includes("REDSTONE_TRACE=1"));
  assert.ok(readme.includes("REDSTONE_PLOT"));
  assert.ok(!readme.includes("-k \""));
});

test("test flags show settle", () => {
  const t = parseModel(fixture("rs_hopper_pair")).tests.find((t) => t.settle !== undefined)!;
  assert.match(testFlags(t), /settle 30t/);
  assert.equal(testFlags({ name: "x" }), "");
});
