import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";

import {
  getDashboardStats,
  listApplications,
  patchApplication,
} from "@/api/client";
import type { Status } from "@/api/types";

const STATUSES: Status[] = [
  "draft",
  "applied",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
];

const STATUS_TONE: Record<Status, string> = {
  draft: "chip",
  applied: "chip chip-mint",
  interview: "chip chip-amber",
  offer: "chip chip-mint",
  rejected: "chip chip-coral",
  withdrawn: "chip",
};

export function DashboardPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Status | "all">("all");
  const [q, setQ] = useState("");

  const statsQ = useQuery({ queryKey: ["dash"], queryFn: getDashboardStats });
  const listQ = useQuery({
    queryKey: ["apps", filter, q],
    queryFn: () =>
      listApplications({
        status: filter === "all" ? undefined : filter,
        q: q || undefined,
      }),
  });

  const patch = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Status }) =>
      patchApplication(id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["apps"] });
      qc.invalidateQueries({ queryKey: ["dash"] });
    },
  });

  return (
    <div className="space-y-10">
      <header className="grid grid-cols-12 gap-6 items-end reveal reveal-1">
        <div className="col-span-12 md:col-span-7">
          <div className="num-mark">YOUR APPLICATIONS</div>
          <h2 className="display text-[clamp(2.5rem,5vw,4.5rem)] mt-2">
            Everything you've{" "}
            <span className="ital text-mint">tailored</span>.
          </h2>
          <p className="text-dim text-[15px] mt-3 max-w-xl">
            Every run through the pipeline, persisted. Click a company to reopen
            its artifacts.
          </p>
        </div>
        <div className="col-span-12 md:col-span-5 md:text-right space-y-1.5 text-[12.5px] text-dim">
          <div>
            {statsQ.data?.total_applications ?? "—"} applications total
          </div>
          <div className="text-muted">
            last refreshed {new Date().toLocaleTimeString()}
          </div>
        </div>
      </header>

      {statsQ.data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 reveal reveal-2">
          <Card label="Applications" value={statsQ.data.total_applications} hint="all time" tone="text" />
          <Card
            label="Response rate"
            value={`${(statsQ.data.response_rate * 100).toFixed(0)}%`}
            hint="of those applied"
            tone="mint"
          />
          <Card
            label="This week"
            value={statsQ.data.applications_this_week}
            hint="last 7 days"
            tone="lavender"
          />
          <Card
            label="This month"
            value={statsQ.data.applications_this_month}
            hint="last 30 days"
            tone="lime"
          />
        </div>
      )}

      {statsQ.data && (
        <div className="grid sm:grid-cols-2 gap-4 reveal reveal-3">
          <SkillList
            title="Your strengths"
            hint="Recurring matches across your applications"
            sigil="✓"
            items={statsQ.data.top_matched_skills}
            tone="mint"
          />
          <SkillList
            title="Recurring gaps"
            hint="Asked for often, not shown on your résumé"
            sigil="!"
            items={statsQ.data.top_missing_skills}
            tone="coral"
          />
        </div>
      )}

      {/* filter bar */}
      <div className="glass p-4 flex flex-wrap items-center gap-3">
        <span className="eyebrow">show</span>
        <div className="flex flex-wrap gap-1.5">
          <FilterChip active={filter === "all"} onClick={() => setFilter("all")}>
            all
          </FilterChip>
          {STATUSES.map((s) => (
            <FilterChip
              key={s}
              active={filter === s}
              onClick={() => setFilter(s)}
            >
              {s}
            </FilterChip>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/10 min-w-[260px] focus-within:border-mint/40 transition-colors">
          <SearchIcon />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by company or role…"
            className="flex-1 text-sm focus:outline-none bg-transparent placeholder:text-muted"
          />
        </div>
      </div>

      {/* table */}
      <div className="glass-strong overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/8">
                <Th>#</Th>
                <Th>Company</Th>
                <Th>Role</Th>
                <Th>Status</Th>
                <Th>Fit</Th>
                <Th>Added</Th>
              </tr>
            </thead>
            <tbody>
              {(listQ.data ?? []).map((a, i) => (
                <tr
                  key={a.id}
                  className="border-b border-white/5 hover:bg-mint/[0.04] transition-colors row-enter"
                  style={{ animationDelay: `${i * 30}ms` }}
                >
                  <Td>
                    <span className="font-mono text-[11px] text-muted">
                      {String(i + 1).padStart(3, "0")}
                    </span>
                  </Td>
                  <Td>
                    <Link
                      to={`/results/${a.id}`}
                      className="font-display text-lg text-text hover:text-mint transition-colors"
                    >
                      {a.company_name}
                    </Link>
                  </Td>
                  <Td>
                    <span className="text-dim">{a.role_title}</span>
                  </Td>
                  <Td>
                    <StatusSelect
                      value={a.status}
                      onChange={(s) => patch.mutate({ id: a.id, status: s })}
                    />
                  </Td>
                  <Td>
                    <MatchBar value={a.overall_match_score} />
                  </Td>
                  <Td>
                    <span className="font-mono text-[11px] text-muted">
                      {new Date(a.created_at).toISOString().slice(0, 10)}
                    </span>
                  </Td>
                </tr>
              ))}
              {listQ.data && listQ.data.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center">
                    <div className="font-display text-3xl text-dim ital">
                      Nothing here yet.
                    </div>
                    <div className="mt-2 text-sm text-dim">
                      Tailor your résumé to a job in{" "}
                      <Link to="/analyse" className="text-mint hover:underline">
                        Step 2
                      </Link>{" "}
                      and it'll show up here.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Card({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone: "text" | "mint" | "lavender" | "lime";
}) {
  const valueClass =
    tone === "mint"
      ? "text-mint"
      : tone === "lavender"
        ? "text-lavender"
        : tone === "lime"
          ? "text-lime"
          : "grad-text";
  return (
    <div className="glass p-5 relative overflow-hidden hover:-translate-y-0.5 transition-transform duration-500">
      <div className="eyebrow">{label}</div>
      <div className={["display text-5xl mt-3", valueClass].join(" ")}>{value}</div>
      {hint && (
        <div className="text-[12.5px] leading-snug text-dim mt-2">
          {hint}
        </div>
      )}
      <span
        className={[
          "absolute -bottom-12 -right-12 w-32 h-32 rounded-full opacity-30 blur-2xl pointer-events-none",
          tone === "mint"
            ? "bg-mint"
            : tone === "lavender"
              ? "bg-lavender"
              : tone === "lime"
                ? "bg-lime"
                : "bg-white/10",
        ].join(" ")}
      />
    </div>
  );
}

function SkillList({
  title,
  hint,
  sigil,
  items,
  tone,
}: {
  title: string;
  hint?: string;
  sigil: string;
  items: string[];
  tone: "mint" | "coral";
}) {
  return (
    <div className="glass p-5">
      <div className="flex items-center gap-2 mb-1">
        <span
          className={[
            "w-7 h-7 rounded-full grid place-items-center border text-[12px] shrink-0",
            tone === "mint"
              ? "text-mint border-mint/40 bg-mint/5"
              : "text-coral border-coral/40 bg-coral/5",
          ].join(" ")}
        >
          {sigil}
        </span>
        <h3 className="font-display text-xl">{title}</h3>
      </div>
      {hint && <p className="text-[13px] text-dim mb-4 leading-snug">{hint}</p>}
      {!hint && <div className="mb-4" />}
      <div className="flex flex-wrap gap-1.5">
        {items.length === 0 && (
          <span className="font-mono text-xs text-muted ital">— none yet</span>
        )}
        {items.map((s, i) => (
          <span
            key={i}
            className={tone === "mint" ? "chip chip-mint" : "chip chip-coral"}
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={[
        "font-mono text-[10px] uppercase tracking-widest2 px-3 py-1.5 rounded-full border transition-all duration-300",
        active
          ? "bg-mint text-obsidian border-mint shadow-[0_8px_24px_-8px_rgba(94,234,212,0.6)]"
          : "bg-white/[0.02] text-dim border-white/10 hover:border-mint/40 hover:text-mint",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function MatchBar({ value }: { value?: number | null }) {
  if (value == null) {
    return <span className="font-mono text-[11px] text-muted">—</span>;
  }
  const pct = Math.round(value * 100);
  const tone = pct >= 75 ? "mint" : pct >= 50 ? "lavender" : "coral";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-white/8 rounded-full overflow-hidden">
        <div
          className={[
            "h-full rounded-full transition-[width] duration-700",
            tone === "mint"
              ? "bg-gradient-to-r from-mint to-mint-soft"
              : tone === "lavender"
                ? "bg-gradient-to-r from-lavender to-lavender-deep"
                : "bg-coral",
          ].join(" ")}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={[
          "font-mono text-[11px]",
          tone === "mint" ? "text-mint" : tone === "lavender" ? "text-lavender" : "text-coral",
        ].join(" ")}
      >
        {pct}%
      </span>
    </div>
  );
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-dim">
      <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.2" />
      <path d="M9.5 9.5 L13 13" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

function StatusSelect({
  value,
  onChange,
}: {
  value: Status;
  onChange: (s: Status) => void;
}) {
  const [open, setOpen] = useState(false);
  const [focusIdx, setFocusIdx] = useState(STATUSES.indexOf(value));
  const ref = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLUListElement>(null);
  const [pos, setPos] = useState<{ top: number; right: number } | null>(null);

  useLayoutEffect(() => {
    if (!open || !btnRef.current) return;
    const update = () => {
      const r = btnRef.current!.getBoundingClientRect();
      // estimate menu height: ~36px/item + 8px padding; flip up if it would overflow viewport bottom
      const estH = STATUSES.length * 36 + 8;
      const below = window.innerHeight - r.bottom;
      const top =
        below < estH + 12 && r.top > estH + 12
          ? r.top - 6 - estH
          : r.bottom + 6;
      setPos({ top, right: window.innerWidth - r.right });
    };
    update();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      const t = e.target as Node;
      if (ref.current && !ref.current.contains(t) && menuRef.current && !menuRef.current.contains(t))
        setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusIdx((i) => (i + 1) % STATUSES.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusIdx((i) => (i - 1 + STATUSES.length) % STATUSES.length);
      } else if (e.key === "Enter") {
        e.preventDefault();
        onChange(STATUSES[focusIdx]);
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, focusIdx, onChange]);

  return (
    <div ref={ref} className="relative inline-block">
      <button
        ref={btnRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => {
          setFocusIdx(STATUSES.indexOf(value));
          setOpen((o) => !o);
        }}
        className={[
          STATUS_TONE[value],
          "cursor-pointer flex items-center gap-1.5",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mint/50",
        ].join(" ")}
      >
        <span>{value}</span>
        <svg
          width="9"
          height="9"
          viewBox="0 0 10 10"
          className={["transition-transform", open ? "rotate-180" : ""].join(" ")}
        >
          <path d="M2 4 L5 7 L8 4" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinecap="round" />
        </svg>
      </button>
      {open && pos && createPortal(
        <ul
          ref={menuRef}
          role="listbox"
          style={{ position: "fixed", top: pos.top, right: pos.right, maxHeight: "calc(100vh - 24px)", overflowY: "auto" }}
          className="z-[100] min-w-[140px] glass-strong p-1 space-y-0.5 shadow-[0_18px_40px_-12px_rgba(0,0,0,0.6)]"
        >
          {STATUSES.map((s, i) => {
            const active = s === value;
            const focused = i === focusIdx;
            return (
              <li key={s}>
                <button
                  role="option"
                  aria-selected={active}
                  onMouseEnter={() => setFocusIdx(i)}
                  onClick={() => {
                    onChange(s);
                    setOpen(false);
                  }}
                  className={[
                    "w-full flex items-center justify-between px-3 py-2 rounded-lg",
                    "font-mono text-[10px] uppercase tracking-[0.18em]",
                    "transition-colors",
                    focused ? "bg-white/[0.06]" : "bg-transparent",
                    active ? "text-mint" : "text-text",
                  ].join(" ")}
                >
                  <span>{s}</span>
                  {active && <span className="text-mint">✓</span>}
                </button>
              </li>
            );
          })}
        </ul>,
        document.body,
      )}
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-3 text-left font-mono text-[10px] uppercase tracking-widest2 text-dim">
      {children}
    </th>
  );
}
function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-4 py-3 align-middle">{children}</td>;
}
