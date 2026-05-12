import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { getProfile, uploadResume } from "@/api/client";
import type { Profile } from "@/api/types";

export function UploadPage() {
  const qc = useQueryClient();
  const profileQ = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const singleRef = useRef<HTMLInputElement>(null);
  const dirRef = useRef<HTMLInputElement>(null);

  const mut = useMutation({
    mutationFn: uploadResume,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile"] }),
    onError: (e: any) =>
      setError(e?.response?.data?.detail?.message || e.message || "Upload failed"),
  });

  const onSingle = (files: FileList | null) => {
    setError(null);
    if (!files || files.length === 0) return;
    mut.mutate([files[0]]);
  };
  const onDir = (files: FileList | null) => {
    setError(null);
    if (!files || files.length === 0) return;
    mut.mutate(Array.from(files));
  };

  return (
    <div className="grid grid-cols-12 gap-10">
      <aside className="col-span-12 md:col-span-4 space-y-5 reveal reveal-1">
        <div className="num-mark">STEP 1 OF 3 · UPLOAD</div>
        <h2 className="display text-[clamp(2.5rem,4.5vw,3.75rem)]">
          Upload your <span className="ital text-mint">résumé</span>.
        </h2>
        <p className="text-dim leading-relaxed max-w-sm text-[15px]">
          One-time ingest. ResumeFit parses your résumé into structured skills
          and experience, then embeds every section into a local vector store —
          so retrieval can pull the right evidence each time you tailor. PDF
          works out of the box; LaTeX authors can drop the whole project folder
          and <code className="font-mono text-mint/90">\input</code> /{" "}
          <code className="font-mono text-mint/90">\include</code> resolve
          automatically.
        </p>
        <div className="flex flex-wrap gap-2 pt-2">
          <span className="chip">PDF</span>
          <span className="chip">.tex</span>
          <span className="chip">LaTeX project folder</span>
          <span className="chip">local vector store</span>
          <span className="chip chip-mint">private · single-user</span>
        </div>
      </aside>

      <section
        className="col-span-12 md:col-span-8 space-y-6 reveal reveal-2"
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          onSingle(e.dataTransfer.files);
        }}
      >
        <div
          className={[
            "grid sm:grid-cols-2 gap-4 transition-transform duration-500",
            drag ? "scale-[1.01]" : "",
          ].join(" ")}
        >
          <UploadCard
            num="A"
            title="Single file"
            subtitle="One PDF or .tex file"
            hint="click to browse, or drop a file anywhere here"
            onClick={() => singleRef.current?.click()}
          />
          <UploadCard
            num="B"
            title="LaTeX project"
            subtitle="A folder of .tex source files"
            hint="\input and \include are resolved automatically"
            onClick={() => dirRef.current?.click()}
            tone="lavender"
          />
        </div>

        <input
          ref={singleRef}
          type="file"
          accept=".pdf,.tex"
          className="hidden"
          onChange={(e) => onSingle(e.target.files)}
        />
        <input
          ref={dirRef}
          type="file"
          // @ts-expect-error non-standard but supported by Chromium
          webkitdirectory=""
          directory=""
          multiple
          className="hidden"
          onChange={(e) => onDir(e.target.files)}
        />

        {mut.isPending && (
          <div className="glass p-5 scan flex items-center gap-3">
            <span className="live-dot" />
            <span className="text-sm text-text caret">
              Parsing your résumé, extracting structure, and building section embeddings…
            </span>
          </div>
        )}

        {error && (
          <div className="glass border-coral/40 p-4 flex items-start gap-3">
            <span className="text-coral mt-0.5">⊘</span>
            <div className="text-sm text-coral">
              <div className="font-medium">Upload failed</div>
              <div className="text-coral/80 mt-0.5">{error}</div>
            </div>
          </div>
        )}

        {profileQ.data && (
          <>
            <div className="glass border-mint/30 bg-mint/[0.04] px-4 py-3 flex items-center gap-3 text-sm">
              <span className="text-mint">✓</span>
              <span className="text-text">
                Résumé parsed and indexed. Next:{" "}
                <span className="text-mint">Step 2 — Tailor to a job</span>.
                Re-upload any time to re-index.
              </span>
            </div>
            <ProfileView profile={profileQ.data} />
          </>
        )}
        {!profileQ.isLoading && !profileQ.data && !mut.isPending && (
          <div className="glass p-10 text-center">
            <div className="eyebrow mb-2">No résumé indexed yet</div>
            <div className="font-display text-3xl text-dim ital">
              Pick a file above to get started
            </div>
            <div className="text-sm text-dim mt-3">
              Accepted: a single PDF or .tex file, or a LaTeX project folder.
              Max 5&nbsp;MB.
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function UploadCard({
  num,
  title,
  subtitle,
  hint,
  onClick,
  tone,
}: {
  num: string;
  title: string;
  subtitle: string;
  hint: string;
  onClick: () => void;
  tone?: "mint" | "lavender";
}) {
  const accent = tone === "lavender" ? "lavender" : "mint";
  return (
    <button
      onClick={onClick}
      className="group glass glow-border text-left p-7 relative transition-transform duration-500 hover:-translate-y-1"
    >
      <div className="flex items-center justify-between mb-12">
        <span
          className={[
            "font-mono text-[11px] tracking-widest2",
            accent === "mint" ? "text-mint" : "text-lavender",
          ].join(" ")}
        >
          OPT · {num}
        </span>
        <span
          className={[
            "w-9 h-9 rounded-full grid place-items-center transition-all duration-500",
            "border",
            accent === "mint"
              ? "border-mint/30 text-mint group-hover:bg-mint/10 group-hover:rotate-45"
              : "border-lavender/30 text-lavender group-hover:bg-lavender/10 group-hover:rotate-45",
          ].join(" ")}
        >
          <svg width="14" height="14" viewBox="0 0 22 22" fill="none">
            <path
              d="M5 17 L17 5 M17 5 H8 M17 5 V14"
              stroke="currentColor"
              strokeWidth="1.6"
              fill="none"
              strokeLinecap="round"
            />
          </svg>
        </span>
      </div>
      <div className="font-display text-3xl leading-tight">
        <span className="text-text">{title.split(" ")[0]}</span>{" "}
        <span className={accent === "mint" ? "text-mint ital" : "text-lavender ital"}>
          {title.split(" ").slice(1).join(" ")}
        </span>
      </div>
      <div className="text-sm text-dim mt-1">{subtitle}</div>
      <div className="div-grad my-5" />
      <div className="text-[12.5px] leading-snug text-dim">
        {hint}
      </div>
    </button>
  );
}

function ProfileView({ profile }: { profile: Profile }) {
  return (
    <article className="glass-strong p-7 space-y-8 reveal reveal-3">
      <header className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="eyebrow mb-1">Parsed profile · structured & indexed from your résumé</div>
          <div className="font-display text-5xl leading-none">
            {profile.full_name}
          </div>
          <div className="text-sm text-dim mt-2 font-mono">
            {profile.email}
            {profile.linkedin_url ? (
              <>
                {" · "}
                <span className="text-mint">{profile.linkedin_url}</span>
              </>
            ) : null}
          </div>
        </div>
        <span className="chip chip-mint">src · {profile.source_format}</span>
      </header>

      <div className="div-grad" />

      <Section num="i" title="Skills">
        <div className="flex flex-wrap gap-1.5">
          {profile.skills.map((s, i) => (
            <span
              key={i}
              className="chip hover:chip-mint hover:border-mint/40 hover:text-mint transition-all"
              style={{ animationDelay: `${i * 25}ms` }}
            >
              {s.name}
            </span>
          ))}
        </div>
      </Section>

      <Section num="ii" title="Experience">
        <ul className="space-y-6">
          {profile.experience.map((e, i) => (
            <li key={i} className="grid grid-cols-12 gap-4 group">
              <div className="col-span-12 md:col-span-3 font-mono text-[11px] uppercase tracking-widest2 text-muted">
                <div className="text-mint">{e.start_date ?? "?"}</div>
                <div>↓</div>
                <div>{e.end_date ?? "present"}</div>
              </div>
              <div className="col-span-12 md:col-span-9 border-l border-white/10 pl-5 group-hover:border-mint/40 transition-colors">
                <div className="font-display text-2xl leading-tight">
                  <span className="text-text">{e.role}</span>{" "}
                  <span className="text-lavender ital">@ {e.company}</span>
                </div>
                <ul className="mt-3 space-y-1.5 text-sm text-dim">
                  {e.bullets.map((b, j) => (
                    <li key={j} className="flex gap-2">
                      <span className="text-mint mt-1 select-none">▸</span>
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          ))}
        </ul>
      </Section>

      {profile.file_structure && (
        <Section num="iii" title="LaTeX project">
          <ul className="font-mono text-xs space-y-1">
            {profile.file_structure.files.map((f, i) => (
              <li key={i} className="flex items-center gap-3 hover:text-mint transition-colors">
                <span className="text-muted">{String(i + 1).padStart(2, "0")}</span>
                <span className="text-text">{f.path}</span>
                <span className="text-mint">·</span>
                <span className="text-dim">{f.role}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </article>
  );
}

function Section({
  num,
  title,
  children,
}: {
  num: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="flex items-baseline gap-3 mb-4">
        <span className="num-mark">§ {num}</span>
        <h3 className="font-display text-xl">{title}</h3>
        <div className="flex-1 div-grad" />
      </div>
      {children}
    </section>
  );
}
