import type { StepInfo } from "@/hooks/useAnalyseStream";

const STEPS = [
  { key: "parse_jd", label: "Parse the JD", glyph: "◆" },
  { key: "gap_analysis", label: "Gap analysis", glyph: "◇" },
  { key: "cover_letter", label: "Draft cover letter", glyph: "✎" },
  { key: "tailored_resume", label: "Tailor résumé", glyph: "❖" },
  { key: "persist", label: "Persist", glyph: "◉" },
];

export function StepProgress({ steps }: { steps: Record<string, StepInfo> }) {
  const total = STEPS.length;
  const done = STEPS.filter((s) => steps[s.key]?.status === "done").length;
  const pct = Math.round((done / total) * 100);
  const running = STEPS.some((s) => steps[s.key]?.status === "started");

  return (
    <div className="glass p-6 reveal reveal-1">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <span className="eyebrow">Pipeline</span>
          {running && (
            <span className="chip chip-mint">
              <span className="live-dot" /> working…
            </span>
          )}
          {done === total && (
            <span className="chip chip-mint">✓ done</span>
          )}
        </div>
        <div className="font-mono text-[12px] tracking-widest2 text-dim">
          <span className="text-text">{done}</span>
          <span className="text-muted"> of {total} steps · </span>
          <span className="text-mint">{pct}%</span>
        </div>
      </div>

      {/* fluid progress bar */}
      <div className="relative h-[3px] rounded-full bg-white/5 overflow-hidden mb-6">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-[width] duration-700 ease-[cubic-bezier(.2,.7,.1,1)]"
          style={{
            width: `${pct}%`,
            background:
              "linear-gradient(90deg, #5eead4 0%, #a78bfa 60%, #bef264 100%)",
            boxShadow: "0 0 24px rgba(94,234,212,0.55)",
          }}
        />
      </div>

      <ol className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {STEPS.map((s, i) => {
          const info = steps[s.key];
          const status = info?.status;
          const active = status === "started";
          const complete = status === "done";
          return (
            <li
              key={s.key}
              className={[
                "relative rounded-2xl p-4 border transition-all duration-500",
                complete
                  ? "border-mint/30 bg-mint/[0.03]"
                  : active
                    ? "border-lavender/40 bg-lavender/[0.05] breathe"
                    : "border-white/5 bg-white/[0.015]",
              ].join(" ")}
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <div className="flex items-center justify-between mb-3">
                <span
                  className={[
                    "font-mono text-[10px] tracking-widest2",
                    complete ? "text-mint" : active ? "text-lavender" : "text-muted",
                  ].join(" ")}
                >
                  {String(i + 1).padStart(2, "0")}
                </span>
                <Glyph status={status} glyph={s.glyph} />
              </div>
              <div
                className={[
                  "font-display text-lg leading-tight",
                  complete || active ? "text-text" : "text-dim",
                ].join(" ")}
              >
                {s.label}
              </div>
              <div className="font-mono text-[10px] uppercase tracking-widest2 mt-2">
                {complete ? (
                  <span className="text-mint">
                    {info?.ms ? `${info.ms}ms ✓` : "done"}
                  </span>
                ) : active ? (
                  <span className="text-lavender caret">running</span>
                ) : (
                  <span className="text-muted">queued</span>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function Glyph({ status, glyph }: { status?: "started" | "done"; glyph: string }) {
  if (status === "done") {
    return (
      <span className="w-6 h-6 rounded-full bg-mint/15 border border-mint/40 grid place-items-center text-mint">
        <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
          <path
            d="M2 7.5 L6 11 L12 3"
            stroke="currentColor"
            strokeWidth="1.6"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
    );
  }
  if (status === "started") {
    return (
      <span className="w-6 h-6 rounded-full grid place-items-center text-lavender border border-lavender/40">
        <span className="w-1.5 h-1.5 rounded-full bg-lavender animate-pulse" />
      </span>
    );
  }
  return (
    <span className="w-6 h-6 rounded-full grid place-items-center text-muted border border-white/10 text-[11px]">
      {glyph}
    </span>
  );
}
