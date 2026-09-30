import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parseFailures, parseTrace } from "../src/trace";
import { fixtures } from "./lib/paths";

const read = (p: string) => parseTrace(readFileSync(join(fixtures, "traces", p), "utf8"));

test("trace files carry sparse, failures and levels through", () => {
  const sparse = read("and_gate/logic.json");
  assert.equal(sparse.sparse, true);
  assert.deepEqual(sparse.failures, []);
  const dense = read("analog_dac/every code gives its value.json");
  assert.equal(dense.sparse, false);
  assert.deepEqual(dense.failures, []);   // older files have no failures key
  assert.ok(dense.frames!.some((f) => f.levels && Object.keys(f.levels).length));
  const failed = read("sulfur_cube_tnt_priming/with the block it ignores a 100 damage player attack, fire primes it at 120, a blast at 15-44.json");
  assert.equal(failed.failures.length, 1);
  assert.deepEqual(parseTrace(null), { frames: null, sparse: false, failures: [] });
  assert.deepEqual(parseTrace("{"), { frames: null, sparse: false, failures: [] });
});

test("failures point at the first frame at their tick", () => {
  const frames = [0, 5, 5, 9, 12].map((tick) => ({ tick, event: "", signals: {} }));
  assert.deepEqual(parseFailures(["tick 5: expected out=1", "tick 10 (repeat 2/3): got 0", "odd", "tick 99: late"], frames), [
    { tick: 5, message: "expected out=1", frame: 1 },
    { tick: 10, message: "(repeat 2/3) got 0", frame: 4 },
    { tick: null, message: "odd", frame: 4 },
    { tick: 99, message: "late", frame: 4 },
  ]);
  const real = read("sulfur_cube_tnt_priming/with the block it ignores a 100 damage player attack, fire primes it at 120, a blast at 15-44.json");
  const [f] = parseFailures(real.failures, real.frames);
  assert.equal(f.tick, 31);
  assert.ok(real.frames![f.frame].tick >= 31 && (f.frame === 0 || real.frames![f.frame - 1].tick < 31));
  assert.match(f.message, /^run execute .*invulnerable/);
});
