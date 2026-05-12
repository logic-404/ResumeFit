import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { previewJd, startAnalyse } from "@/api/client";
import { useAppStore } from "@/store/appStore";

export function AnalysePage() {
  const navigate = useNavigate();
  const setJobId = useAppStore((s) => s.setJobId);

  const [jdText, setJdText] = useState("");
  const [jdUrl, setJdUrl] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [prefilled, setPrefilled] = useState(false);
  const lastPreviewedUrl = useRef<string>("");
  const previewSeq = useRef(0);

  const runPreview = async (url: string) => {
    const trimmed = url.trim();
    if (!trimmed) return;
    if (trimmed === lastPreviewedUrl.current) return;
    try {
      new URL(trimmed);
    } catch {
      return;
    }
    lastPreviewedUrl.current = trimmed;
    const seq = ++previewSeq.current;
    setPreviewing(true);
    setPreviewError(null);
    setPrefilled(false);
    try {
      const data = await previewJd(trimmed);
      if (seq !== previewSeq.current) return;
      if (data.company && !companyName) setCompanyName(data.company);
      if (data.role && !roleTitle) setRoleTitle(data.role);
      if (data.jd_text && !jdText) setJdText(data.jd_text);
      setPrefilled(true);
    } catch (e: any) {
      if (seq !== previewSeq.current) return;
      setPreviewError(
        e?.response?.data?.detail?.message || e?.message || "Preview failed",
      );
    } finally {
      if (seq === previewSeq.current) setPreviewing(false);
    }
  };

  const mut = useMutation({
    mutationFn: startAnalyse,
    onSuccess: ({ job_id }) => {
      setJobId(job_id);
      navigate(`/results/${encodeURIComponent(job_id)}`);
    },
    onError: (e: any) =>
      setError(e?.response?.data?.detail?.message || e.message || "Failed"),
  });

  const submit = () => {
    setError(null);
    if (!jdText && !jdUrl) {
      setError("Add the job description — paste the text above, or give us a posting URL.");
      return;
    }
    mut.mutate({
      jd_text: jdText || undefined,
      jd_url: jdUrl || undefined,
      company_name: companyName || undefined,
      role_title: roleTitle || undefined,
      job_url: jdUrl || undefined,
    });
  };

  const wordCount = jdText.trim() ? jdText.trim().split(/\s+/).length : 0;
  const tokens = Math.round(wordCount * 1.3);

  return (
    <div className="grid grid-cols-12 gap-10">
      <aside className="col-span-12 md:col-span-4 space-y-6 reveal reveal-1">
        <div className="num-mark">STEP 2 OF 3 · TAILOR</div>
        <h2 className="display text-[clamp(2.5rem,4.5vw,3.75rem)]">
          Add the <span className="ital text-lavender">job posting</span>.
        </h2>
        <p className="text-dim leading-relaxed max-w-sm text-[15px]">
          Paste the posting or drop a link. The pipeline parses the JD, runs a
          gap analysis against your indexed profile, then fans out — résumé
          tailoring and cover-letter drafting run in parallel:
        </p>
        <ul className="space-y-2 text-sm text-dim max-w-sm">
          <li className="flex gap-2"><span className="text-mint mt-0.5">1.</span><span><span className="text-text">Fit score</span> — semantic match, surfaced gaps</span></li>
          <li className="flex gap-2"><span className="text-mint mt-0.5">2.</span><span><span className="text-text">Tailored résumé</span> — retrieval-grounded, anti-fabrication checked</span></li>
          <li className="flex gap-2"><span className="text-mint mt-0.5">3.</span><span><span className="text-text">Cover letter</span> — drawn from your real experience</span></li>
        </ul>
        <div className="glass p-4 space-y-2.5">
          <div className="flex items-center justify-between text-[13px]">
            <span className="text-dim">Pipeline run time</span>
            <span className="text-mint">~20&nbsp;sec</span>
          </div>
          <div className="flex items-center justify-between text-[13px]">
            <span className="text-dim">Job description length</span>
            <span className={tokens > 8000 ? "text-coral" : "text-text"}>
              {tokens.toLocaleString()} / 8,000 tok
            </span>
          </div>
          {tokens > 8000 && (
            <div className="text-[12px] text-coral leading-snug">
              Too long — trim the posting to the role, responsibilities and
              requirements.
            </div>
          )}
        </div>
      </aside>

      <section className="col-span-12 md:col-span-8 space-y-6 reveal reveal-2">
        <div className="grid sm:grid-cols-2 gap-5">
          <Field label="Company" num="i">
            <input
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Aperture Labs"
              className="field-input"
            />
          </Field>
          <Field label="Role title" num="ii">
            <input
              value={roleTitle}
              onChange={(e) => setRoleTitle(e.target.value)}
              placeholder="Staff Engineer"
              className="field-input"
            />
          </Field>
        </div>

        <Field label="Posting URL (optional)" num="iii">
          <input
            value={jdUrl}
            onChange={(e) => setJdUrl(e.target.value)}
            onBlur={(e) => runPreview(e.target.value)}
            placeholder="https://boards.greenhouse.io/…"
            className="field-input font-mono text-sm"
          />
          <div className="mt-1.5 text-[13px] text-dim">
            {previewing ? (
              <span className="text-dim">Fetching the posting…</span>
            ) : previewError ? (
              <span className="text-coral">⊘ Couldn't fetch it — {previewError}. Paste the text below instead.</span>
            ) : prefilled ? (
              <span className="text-mint">✓ Fetched — fields below are filled in. Edit anything that looks off.</span>
            ) : (
              <span>Paste a link, then click away — or just paste the text below.</span>
            )}
          </div>
        </Field>

        <div>
          <div className="flex items-baseline justify-between mb-2">
            <span className="eyebrow">§ iv · Job description {jdText ? "" : "(required)"}</span>
            <div className="flex items-center gap-2 text-[12.5px]">
              <span className="text-dim">{wordCount} words</span>
              <span className="text-muted">·</span>
              <span className={tokens > 8000 ? "text-coral" : "text-mint"}>
                {tokens.toLocaleString()} / 8,000 tokens
              </span>
            </div>
          </div>
          <div className="glass p-1">
            <textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              rows={16}
              placeholder="Paste the full job posting here — title, responsibilities, requirements, the lot. The more complete it is, the better the tailoring."
              className="w-full bg-transparent p-5 font-mono text-[13.5px] leading-relaxed resize-y focus:outline-none placeholder:text-muted"
            />
          </div>
        </div>

        {error && (
          <div className="glass border-coral/40 p-4 flex items-start gap-3">
            <span className="text-coral mt-0.5">⊘</span>
            <div className="text-sm text-coral">
              <div className="font-medium">Couldn't start</div>
              <div className="text-coral/80 mt-0.5">{error}</div>
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-4 pt-3">
          <button onClick={submit} disabled={mut.isPending} className="btn btn-primary">
            <span>{mut.isPending ? "Spinning up the pipeline…" : "Run the pipeline"}</span>
            <Arrow />
          </button>
          <span className="text-[13.5px] text-dim">
            ~20 seconds — every pipeline step streams in live over SSE.
          </span>
        </div>
      </section>
    </div>
  );
}

function Field({
  label,
  num,
  children,
}: {
  label: string;
  num: string;
  children: React.ReactNode;
}) {
  return (
    <label className="field">
      <span className="eyebrow block mb-1.5">
        § {num} · {label}
      </span>
      {children}
    </label>
  );
}

function Arrow() {
  return (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
      <path
        d="M2 7 H12 M8 3 L12 7 L8 11"
        stroke="currentColor"
        strokeWidth="1.6"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
