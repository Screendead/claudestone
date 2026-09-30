import { Test } from "../model";

export function testFlags(t: Test): string {
  const edges = (d: Test["delays"]) => Object.entries(d ?? {}).map(([o, v]) =>
    typeof v === "number" ? `${o} ${v}t` : `${o} ${Object.entries(v).map(([e, w]) => `${e} ${w}t`).join(" ")}`).join(", ");
  return [t.delays && `delays ${edges(t.delays)}`, t.max_delays && `max ${edges(t.max_delays)}`,
    t.settle !== undefined && `settle ${t.settle}t`, t.glitch_free && "glitch-free", t.reset === false && "no reset"]
    .filter(Boolean).join(" · ");
}
