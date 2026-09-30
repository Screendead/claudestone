export interface Frame {
  tick: number;
  event: string;
  signals: Record<string, number>;
  /** Comparator output strengths; dense traces only. */
  levels?: Record<string, number>;
  reply?: string;
}
export interface TraceData { frames: Frame[] | null; sparse: boolean; failures: string[] }

/** A trace file's text, or null when there is none yet; frames is null when there is no readable trace. */
export function parseTrace(text: string | null): TraceData {
  let js: { frames?: Frame[]; sparse?: boolean; failures?: string[] };
  try { js = JSON.parse(text ?? ""); } catch { return { frames: null, sparse: false, failures: [] }; }
  return {
    frames: Array.isArray(js.frames) ? js.frames : null,
    sparse: js.sparse === true,
    failures: Array.isArray(js.failures) ? js.failures.map(String) : [],
  };
}

export interface Failure { tick: number | null; message: string; frame: number }
/** Failures read "tick N[ (repeat i/n)]: message"; frame is the first frame at or after that tick. */
export function parseFailures(failures: string[], frames: Frame[] | null): Failure[] {
  return failures.map((f) => {
    const m = /^tick (\d+)(?: \(([^)]*)\))?: ([\s\S]*)$/.exec(f);
    const tick = m ? Number(m[1]) : null;
    const i = tick === null || !frames ? -1 : frames.findIndex((fr) => fr.tick >= tick);
    const message = m ? (m[2] ? `(${m[2]}) ${m[3]}` : m[3]) : f;
    return { tick, message, frame: i < 0 ? Math.max(0, (frames?.length ?? 1) - 1) : i };
  });
}
