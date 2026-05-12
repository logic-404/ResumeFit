import { useEffect, useRef, useState } from "react";

export interface StepInfo {
  name: string;
  status: "started" | "done";
  ms?: number;
}

export interface StreamState {
  steps: Record<string, StepInfo>;
  result: any | null;
  error: { code: string; message: string } | null;
  done: boolean;
}

export function useAnalyseStream(jobId: string | null): StreamState {
  const [state, setState] = useState<StreamState>({
    steps: {},
    result: null,
    error: null,
    done: false,
  });
  const ref = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;
    const es = new EventSource(`/api/v1/analyse/${jobId}/stream`);
    ref.current = es;

    es.addEventListener("step", (ev) => {
      const data = JSON.parse((ev as MessageEvent).data);
      setState((s) => ({ ...s, steps: { ...s.steps, [data.name]: data } }));
    });
    es.addEventListener("result", (ev) => {
      const data = JSON.parse((ev as MessageEvent).data);
      setState((s) => ({ ...s, result: data, done: true }));
      es.close();
    });
    es.addEventListener("error", (ev) => {
      const me = ev as MessageEvent;
      let parsed: { code: string; message: string } | null = null;
      try {
        parsed = me.data ? JSON.parse(me.data) : null;
      } catch {
        parsed = null;
      }
      if (parsed) {
        setState((s) => ({ ...s, error: parsed, done: true }));
        es.close();
      }
    });

    return () => es.close();
  }, [jobId]);

  return state;
}
