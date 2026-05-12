import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { downloadTailoredResumeUrl, getApplication, regenerate } from "@/api/client";
import type {
  ApplicationDetail,
  CoverLetter,
  GapAnalysis,
  TailoredResume,
} from "@/api/types";
import { StepProgress } from "@/components/StepProgress";
import { useAnalyseStream } from "@/hooks/useAnalyseStream";
import { useAppStore } from "@/store/appStore";

type TabKey = "resume" | "letter" | "gap";

interface ResultData {
  application_id: string;
  cover_letter: CoverLetter | null;
  gap_analysis: GapAnalysis | null;
  tailored_resume: TailoredResume | null;
}

function latestOutput(detail: ApplicationDetail, type: string): any {
  const matches = detail.outputs.filter((o) => o.output_type === type);
  if (matches.length === 0) return null;
  return [...matches].sort((a, b) => b.version - a.version)[0].content;
}

function is404(err: unknown): boolean {
  return (err as any)?.response?.status === 404;
}

export function ResultsPage() {
  const { appId } = useParams();
  const id = appId ?? null;
  const navigate = useNavigate();
  const liveJobId = useAppStore((s) => s.currentJobId);
  const [tab, setTab] = useState<TabKey>("resume");

  // The URL param is either a saved application id (opened from the dashboard
  // or a reload) or a live job id (just kicked off in Step 2). Try to load it
  // as a stored application; if it doesn't exist yet, treat it as a live job
  // and stream the run. Skip the lookup entirely when we know it's a fresh run.
  const knownLive = id != null && id === liveJobId;
  const appQuery = useQuery({
    queryKey: ["application", id],
    queryFn: () => getApplication(id!),
    enabled: id != null && !knownLive,
    retry: false,
  });

  const streamJobId =
    id != null && (knownLive || (appQuery.isError && is404(appQuery.error)))
      ? id
      : null;
  const stream = useAnalyseStream(streamJobId);

  const stored: ResultData | null = useMemo(
    () =>
      appQuery.data
        ? {
            application_id: appQuery.data.id,
            cover_letter: latestOutput(appQuery.data, "cover_letter"),
            gap_analysis: latestOutput(appQuery.data, "gap_analysis"),
            tailored_resume: latestOutput(appQuery.data, "tailored_resume"),
          }
        : null,
    [appQuery.data],
  );
  const result: ResultData | null = stored ?? (stream.result as ResultData | null);

  // Once a live run finishes it knows its persisted application id — swap the
  // URL so a reload (or back-button) reopens the saved copy, not a dead stream.
  useEffect(() => {
    const aid = stream.result?.application_id;
    if (aid && aid !== id) navigate(`/results/${aid}`, { replace: true });
  }, [stream.result, id, navigate]);

  // Reset to the résumé tab only when a different application loads — not on
  // every render (a fresh `result` object each render would lock the tab).
  useEffect(() => {
    if (result) setTab("resume");
  }, [result?.application_id]);

  const notFound = appQuery.isError && is404(appQuery.error) && streamJobId == null;
  const loading =
    !result &&
    !notFound &&
    !stream.error &&
    ((appQuery.isLoading && !knownLive) || streamJobId != null);
  const live = streamJobId != null && !result;

  return (
    <div className="space-y-10">
      <header className="flex items-end justify-between flex-wrap gap-4 reveal reveal-1">
        <div>
          <div className="num-mark">STEP 3 OF 3 · REVIEW &amp; DOWNLOAD</div>
          <h2 className="display text-[clamp(2.5rem,5vw,4rem)] mt-2">
            Your tailored <span className="ital text-mint">application</span>.
          </h2>
          <p className="text-dim text-[15px] mt-3 max-w-xl">
            Three artifacts, generated for this posting — each independently
            regenerable. Review, re-run, export.
          </p>
        </div>
        <div className="glass px-4 py-2 text-[12px] flex items-center gap-3 font-mono">
          <span className="text-dim uppercase tracking-widest2">
            {stored ? "app" : "job"}
          </span>
          <span className="text-text">
            {(result?.application_id ?? id)?.slice(0, 8) ?? "—"}
          </span>
          {live && (
            <span className="chip chip-lavender">
              <span className="live-dot" /> working
            </span>
          )}
        </div>
      </header>

      {live && <StepProgress steps={stream.steps} />}

      {notFound && (
        <div className="glass border-coral/40 p-4 flex items-start gap-3">
          <span className="text-coral mt-0.5">⊘</span>
          <div className="text-sm text-coral">
            <div className="font-medium">Application not found</div>
            <div className="text-coral/80 mt-0.5">
              It may have been deleted. Head back to the dashboard.
            </div>
          </div>
        </div>
      )}

      {stream.error && (
        <div className="glass border-coral/40 p-4 flex items-start gap-3">
          <span className="text-coral mt-0.5">⊘</span>
          <div className="text-sm text-coral">
            <div className="font-medium">Something went wrong ({stream.error.code})</div>
            <div className="text-coral/80 mt-0.5">{stream.error.message}</div>
            <div className="text-coral/80 mt-1">Go back to Step 2 and try again.</div>
          </div>
        </div>
      )}

      {loading && (
        <div className="glass p-8 scan">
          <div className="text-sm text-text caret">
            {live
              ? "Running the pipeline — streaming each step, ~20 seconds."
              : "Loading your saved application…"}
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-6 reveal reveal-2">
          <TabBar tab={tab} setTab={setTab} />

          <div key={tab} className="reveal">
            {tab === "resume" &&
              (result.tailored_resume ? (
                <TailoredResumeTab
                  resume={result.tailored_resume}
                  applicationId={result.application_id}
                />
              ) : (
                <EmptyResume />
              ))}
            {tab === "letter" && result.cover_letter && (
              <CoverLetterTab
                letter={result.cover_letter}
                applicationId={result.application_id}
              />
            )}
            {tab === "gap" && result.gap_analysis && (
              <GapAnalysisTab
                gap={result.gap_analysis}
                applicationId={result.application_id}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TabBar({
  tab,
  setTab,
}: {
  tab: TabKey;
  setTab: (t: TabKey) => void;
}) {
  const items: { k: TabKey; n: string; label: string; desc: string; tone: string }[] = [
    { k: "resume", n: "I", label: "Tailored Résumé", desc: "Retrieval-grounded rewrite", tone: "mint" },
    { k: "letter", n: "II", label: "Cover Letter", desc: "Drafted from your experience", tone: "lavender" },
    { k: "gap", n: "III", label: "Fit & Gaps", desc: "Semantic match & gap report", tone: "lime" },
  ];
  return (
    <div className="glass p-2 grid grid-cols-3 gap-2">
      {items.map((it) => {
        const active = tab === it.k;
        return (
          <button
            key={it.k}
            onClick={() => setTab(it.k)}
            className={[
              "relative text-left px-5 py-4 rounded-xl transition-all duration-500 overflow-hidden",
              active
                ? "bg-white/[0.04] border border-white/10"
                : "hover:bg-white/[0.02] border border-transparent",
            ].join(" ")}
          >
            {active && (
              <span
                className="absolute inset-x-0 top-0 h-px"
                style={{
                  background:
                    it.tone === "mint"
                      ? "linear-gradient(90deg, transparent, #5eead4, transparent)"
                      : it.tone === "lavender"
                        ? "linear-gradient(90deg, transparent, #a78bfa, transparent)"
                        : "linear-gradient(90deg, transparent, #bef264, transparent)",
                }}
              />
            )}
            <div
              className={[
                "font-mono text-[10px] uppercase tracking-widest2 mb-1",
                active
                  ? it.tone === "mint"
                    ? "text-mint"
                    : it.tone === "lavender"
                      ? "text-lavender"
                      : "text-lime"
                  : "text-muted",
              ].join(" ")}
            >
              §{it.n}
            </div>
            <div
              className={[
                "font-display text-2xl leading-tight",
                active ? "text-text" : "text-dim",
              ].join(" ")}
            >
              {it.label}
            </div>
            <div className={["text-[13px] mt-1 leading-snug", active ? "text-dim" : "text-dim/70"].join(" ")}>
              {it.desc}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function copy(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

function ActionBar({
  children,
  meta,
}: {
  children: React.ReactNode;
  meta?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {children}
      {meta && <div className="ml-auto">{meta}</div>}
    </div>
  );
}

function CoverLetterTab({
  letter,
  applicationId,
}: {
  letter: CoverLetter;
  applicationId: string;
}) {
  const text = [
    letter.greeting,
    letter.opening_paragraph,
    ...letter.body_paragraphs,
    letter.closing_paragraph,
    letter.sign_off,
  ].join("\n\n");
  const regen = useMutation({
    mutationFn: () => regenerate(applicationId, "cover_letter"),
  });
  const [copied, setCopied] = useState(false);
  return (
    <div className="space-y-5">
      <ActionBar
        meta={
          <span className="flex gap-2">
            <span className="chip" title="How many keywords from the job posting appear in the letter">
              {letter.keyword_match_count} job keywords used
            </span>
            <span className="chip" title="Estimated tone match, 0–1">
              tone match {Math.round(letter.tone_score * 100)}%
            </span>
          </span>
        }
      >
        <button
          onClick={() => {
            copy(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
          className="btn btn-primary"
        >
          {copied ? "✓ Copied to clipboard" : "Copy text"}
        </button>
        <button
          onClick={() => regen.mutate()}
          disabled={regen.isPending}
          className="btn btn-ghost"
        >
          {regen.isPending ? "Redrafting…" : "↻ Regenerate"}
        </button>
      </ActionBar>
      <p className="text-[13.5px] text-dim">
        A draft — read it through and swap in specifics before sending.
      </p>

      <article className="glass-strong p-10 max-w-3xl mx-auto relative">
        <div className="absolute -top-3 left-8 px-3 num-mark bg-obsidian">
          ✎ Letter
        </div>
        <p className="font-display text-2xl mb-6 text-text">{letter.greeting}</p>
        <div className="space-y-5 text-[15px] leading-[1.75] text-text/90">
          <p className="first-letter:font-display first-letter:text-6xl first-letter:float-left first-letter:mr-3 first-letter:leading-[0.85] first-letter:text-mint">
            {letter.opening_paragraph}
          </p>
          {letter.body_paragraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
          <p>{letter.closing_paragraph}</p>
        </div>
        <p className="mt-8 font-display ital text-xl text-lavender">
          {letter.sign_off}
        </p>
      </article>
    </div>
  );
}

function GapAnalysisTab({
  gap,
  applicationId,
}: {
  gap: GapAnalysis;
  applicationId: string;
}) {
  const regen = useMutation({
    mutationFn: () => regenerate(applicationId, "gap_analysis"),
  });
  const score = gap.overall_match_score;
  const pct = Math.round(score * 100);

  return (
    <div className="space-y-7">
      <div className="grid grid-cols-12 gap-6 items-stretch">
        <div className="col-span-12 md:col-span-5 glass-strong p-7 relative overflow-hidden">
          <div className="eyebrow mb-3">How well you match this job</div>
          <div className="display text-[8rem] leading-none flex items-baseline">
            <span className="grad-text">{pct}</span>
            <span className="text-3xl text-mint ml-2">%</span>
          </div>
          <div className="text-[13px] text-dim mt-1">
            {pct >= 75
              ? "Strong fit — apply with confidence."
              : pct >= 50
                ? "Decent fit — worth applying; lean on transferable skills."
                : "Stretch role — apply only if you really want it, and address the gaps head-on."}
          </div>
          <RingScore value={pct} />
          <div
            className="absolute -bottom-20 -right-20 w-60 h-60 rounded-full opacity-30 blur-3xl pointer-events-none"
            style={{
              background:
                pct >= 75
                  ? "#5eead4"
                  : pct >= 50
                    ? "#a78bfa"
                    : "#fb7185",
            }}
          />
        </div>
        <div className="col-span-12 md:col-span-7 glass p-7 flex flex-col justify-between">
          <div>
            <div className="eyebrow mb-3">What we'd do</div>
            <p className="font-display text-[clamp(1.5rem,2.4vw,2rem)] leading-snug text-text">
              {gap.recommendation}
            </p>
          </div>
          <div className="flex justify-end mt-4">
            <button
              onClick={() => regen.mutate()}
              disabled={regen.isPending}
              className="btn btn-ghost"
            >
              {regen.isPending ? "…" : "↻ Regenerate"}
            </button>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <Group title="You've got these" hint="Wanted, and your résumé shows it" sigil="✓" tone="mint">
          <ul className="space-y-3">
            {gap.matched_skills.length === 0 && <Empty />}
            {gap.matched_skills.map((s, i) => (
              <li key={i} className="reveal" style={{ animationDelay: `${i * 50}ms` }}>
                <div className="font-display text-lg">{s.skill}</div>
                <div className="text-sm text-dim">{s.evidence}</div>
              </li>
            ))}
          </ul>
        </Group>
        <Group title="Gaps to address" hint="Wanted, not evident — “must-have” matters most" sigil="!" tone="coral">
          <ul className="space-y-3">
            {gap.missing_skills.length === 0 && <Empty />}
            {gap.missing_skills.map((s, i) => (
              <li key={i} className="reveal" style={{ animationDelay: `${i * 50}ms` }}>
                <div className="font-display text-lg flex items-baseline gap-2 flex-wrap">
                  <span>{s.skill}</span>
                  <span
                    className={
                      s.severity === "required"
                        ? "chip chip-coral"
                        : "chip chip-amber"
                    }
                  >
                    {s.severity === "required" ? "must-have" : "nice-to-have"}
                  </span>
                </div>
                <div className="text-sm text-dim">{s.suggestion}</div>
              </li>
            ))}
          </ul>
        </Group>
        <Group title="Close enough to count" hint="Your experience maps onto their asks" sigil="↻" tone="lavender">
          <ul className="space-y-3">
            {gap.transferable_skills.length === 0 && <Empty />}
            {gap.transferable_skills.map((s, i) => (
              <li key={i} className="reveal" style={{ animationDelay: `${i * 50}ms` }}>
                <div className="font-display text-lg">
                  <span>{s.skill}</span>
                  <span className="text-lavender ital"> → </span>
                  <span>{s.maps_to}</span>
                </div>
                <div className="text-sm text-dim">{s.explanation}</div>
              </li>
            ))}
          </ul>
        </Group>
      </div>
    </div>
  );
}

function RingScore({ value }: { value: number }) {
  const blocks = 28;
  const filled = Math.round((value / 100) * blocks);
  return (
    <div className="mt-5 flex gap-[3px]">
      {Array.from({ length: blocks }).map((_, i) => (
        <span
          key={i}
          className={[
            "h-3 flex-1 rounded-sm transition-all duration-700",
            i < filled
              ? "bg-gradient-to-t from-mint to-lavender"
              : "bg-white/8",
          ].join(" ")}
          style={{ transitionDelay: `${i * 25}ms` }}
        />
      ))}
    </div>
  );
}

function TailoredResumeTab({
  resume,
  applicationId,
}: {
  resume: TailoredResume;
  applicationId: string;
}) {
  const regen = useMutation({
    mutationFn: () => regenerate(applicationId, "tailored_resume"),
  });

  let body: React.ReactNode = null;
  if (resume.format === "pdf_source") {
    body =
      resume.markdown?.trim() ? (
        <ResumePreview markdown={resume.markdown} />
      ) : (
        <EmptyResume />
      );
  } else if (resume.format === "tex") {
    body = <CodeBlock filename="main.tex" content={resume.full_tex} />;
  } else {
    body = (
      <div className="space-y-2">
        {resume.files.map((f, i) => (
          <details
            key={f.path}
            className="glass overflow-hidden group reveal"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <summary className="px-4 py-3 cursor-pointer font-mono text-[12px] flex items-center gap-3 list-none">
              <span className="text-mint transition-transform group-open:rotate-90">▸</span>
              <span className="text-text">{f.path}</span>
              <span className="ml-auto chip">
                {f.content.length} chars
              </span>
            </summary>
            <CodeBlock filename={f.path} content={f.content} naked />
          </details>
        ))}
      </div>
    );
  }

  const fmtLabel =
    resume.format === "pdf_source"
      ? "PDF"
      : resume.format === "tex"
        ? "LaTeX (.tex)"
        : "LaTeX project";

  return (
    <div className="space-y-5">
      <ActionBar
        meta={<span className="chip chip-mint">downloads as · {fmtLabel}</span>}
      >
        <a href={downloadTailoredResumeUrl(applicationId)} className="btn btn-primary">
          ↓ Download résumé
        </a>
        <button
          onClick={() => regen.mutate()}
          disabled={regen.isPending}
          className="btn btn-ghost"
        >
          {regen.isPending ? "Redrafting…" : "↻ Regenerate"}
        </button>
      </ActionBar>

      <p className="text-[13.5px] text-dim">
        Grounded in your indexed résumé — every claim traced back, run through
        an anti-fabrication check. Regenerate for a fresh pass.
      </p>

      {body}

      {resume.change_log?.length > 0 && (
        <section className="mt-6">
          <div className="flex items-baseline gap-3 mb-4">
            <span className="num-mark">What changed &amp; why</span>
            <div className="flex-1 div-grad" />
          </div>
          <ul className="space-y-2">
            {resume.change_log.map((c, i) => (
              <li
                key={i}
                className="glass grid grid-cols-12 gap-3 p-3 hover:border-mint/30 transition-colors reveal"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <span className="col-span-1 font-mono text-[11px] text-mint">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="col-span-3 font-mono text-[11px] uppercase tracking-widest2 text-dim">
                  {c.section}
                </span>
                <span className="col-span-5 text-sm text-text">{c.change}</span>
                <span className="col-span-3 text-sm text-dim ital">
                  {c.reason}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function CodeBlock({
  filename,
  content,
  naked,
}: {
  filename: string;
  content: string;
  naked?: boolean;
}) {
  return (
    <div className={naked ? "" : "glass overflow-hidden"}>
      {!naked && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/5">
          <span className="font-mono text-[10px] uppercase tracking-widest2 text-dim">
            {filename}
          </span>
          <span className="flex gap-1">
            <span className="w-2 h-2 bg-coral rounded-full" />
            <span className="w-2 h-2 bg-amber rounded-full" />
            <span className="w-2 h-2 bg-mint rounded-full" />
          </span>
        </div>
      )}
      <pre className="overflow-auto text-xs p-5 font-mono leading-relaxed text-text/90 bg-black/30">
        {content}
      </pre>
    </div>
  );
}

function Group({
  title,
  hint,
  sigil,
  tone,
  children,
}: {
  title: string;
  hint?: string;
  sigil: string;
  tone: "mint" | "coral" | "lavender";
  children: React.ReactNode;
}) {
  const toneClass =
    tone === "mint"
      ? "text-mint"
      : tone === "coral"
        ? "text-coral"
        : "text-lavender";
  return (
    <div className="glass p-5 hover:-translate-y-0.5 transition-transform duration-500">
      <div className="flex items-center gap-2 mb-1">
        <span
          className={[
            "w-7 h-7 rounded-full grid place-items-center border text-[12px] shrink-0",
            toneClass,
            tone === "mint"
              ? "border-mint/40 bg-mint/5"
              : tone === "coral"
                ? "border-coral/40 bg-coral/5"
                : "border-lavender/40 bg-lavender/5",
          ].join(" ")}
        >
          {sigil}
        </span>
        <h3 className="font-display text-xl">{title}</h3>
      </div>
      {hint && <p className="text-[13px] text-dim mb-4 leading-snug">{hint}</p>}
      {!hint && <div className="mb-4" />}
      {children}
    </div>
  );
}

function Empty() {
  return <li className="text-sm text-dim ital">— nothing here</li>;
}

function EmptyResume() {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="glass-strong p-14 text-center">
        <div className="num-mark mb-3">empty document</div>
        <div className="font-display text-3xl text-dim ital">
          No résumé content was produced.
        </div>
        <div className="font-mono text-[10px] uppercase tracking-widest2 text-muted mt-3">
          regenerate to retry
        </div>
      </div>
    </div>
  );
}

function ResumePreview({ markdown }: { markdown: string }) {
  return (
    <div className="mx-auto max-w-3xl isolate">
      <div className="rounded-xl shadow-[0_30px_60px_-20px_rgba(0,0,0,0.65),0_0_0_1px_rgba(255,255,255,0.06)] overflow-hidden">
        <div
          className="px-12 py-12 text-slate-900 [color-scheme:light] relative"
          style={{
            background:
              "linear-gradient(180deg, #fdfcf8 0%, #f7f5ee 100%)",
          }}
        >
          <span
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage:
                "radial-gradient(rgba(0,0,0,0.6) 1px, transparent 1px)",
              backgroundSize: "3px 3px",
            }}
          />
          <article className="resume-doc relative">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => (
                  <h1 className="text-3xl font-semibold tracking-tight text-slate-900 mb-1">
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 className="mt-6 mb-2 pb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-900 border-b border-slate-300">
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className="mt-3 mb-1 text-[14px] font-semibold text-slate-900">
                    {children}
                  </h3>
                ),
                p: ({ children }) => (
                  <p className="text-[13.5px] leading-relaxed text-slate-700 my-1">
                    {children}
                  </p>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc pl-5 my-1.5 space-y-1 text-[13.5px] leading-relaxed text-slate-700 marker:text-slate-400">
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal pl-5 my-1.5 space-y-1 text-[13.5px] leading-relaxed text-slate-700">
                    {children}
                  </ol>
                ),
                li: ({ children }) => <li className="pl-1">{children}</li>,
                strong: ({ children }) => (
                  <strong className="font-semibold text-slate-900">{children}</strong>
                ),
                em: ({ children }) => (
                  <em className="text-slate-600">{children}</em>
                ),
                a: ({ children, href }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="text-slate-900 underline decoration-slate-300 hover:decoration-slate-700"
                  >
                    {children}
                  </a>
                ),
                hr: () => <hr className="my-4 border-slate-300" />,
                table: ({ children }) => (
                  <table className="my-3 w-full border-collapse text-[13px]">
                    {children}
                  </table>
                ),
                th: ({ children }) => (
                  <th className="border-b border-slate-300 px-2 py-1 text-left font-semibold">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="border-b border-slate-200 px-2 py-1 align-top">
                    {children}
                  </td>
                ),
                code: ({ children }) => (
                  <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[12px] text-slate-800">
                    {children}
                  </code>
                ),
              }}
            >
              {markdown}
            </ReactMarkdown>
          </article>
        </div>
      </div>
    </div>
  );
}
