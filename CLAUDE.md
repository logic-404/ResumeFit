# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Backend (run from `backend/`, venv at `.venv/Scripts/`):

```bash
# install
uv venv .venv --python 3.11
uv pip install -e .[dev]

# db schema (PostgreSQL 16, needs pgcrypto)
psql "$DATABASE_URL" -f db/schema.sql

# dev server
.venv/Scripts/uvicorn app.main:app --reload --port 8000

# tests (pytest-asyncio auto mode; testpaths=tests)
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe -m pytest tests/test_tools.py::test_name -q   # single test

# eval harness — replays pipeline against eval/expectations.yaml
.venv/Scripts/python.exe -m eval.run_eval
```

Frontend (run from `frontend/`):

```bash
npm install
npm run dev          # vite, port 5173, proxies /api/* → :8000
npm run build        # tsc -b && vite build
npm run lint         # tsc --noEmit (no eslint configured)
```

No backend linter or formatter is configured. Pre-stage a profile via `POST /profile/upload` before running `eval/run_eval`.

## Architecture

Two services: FastAPI backend + React/Vite frontend. Single-user app — profile singleton enforced at DB layer (`UNIQUE INDEX one_profile_only ON profiles ((true))`).

### Pipeline (LangGraph) — `app/pipeline/graph.py`

State machine with parallel fan-out:

```
parse_jd → gap_analysis → {cover_letter ∥ tailored_resume} → persist
```

- `cover_letter` and `tailored_resume` run concurrently — both depend only on `gap_analysis` output.
- `persist_node` writes `Application` + 3 `GeneratedOutput` rows (cover_letter, gap_analysis, tailored_resume) in **one transaction**.
- `_retrying()` wraps each skill call with tenacity exponential backoff, **only** on `RateLimitError | APITimeoutError | APIConnectionError`. Schema/validation errors surface immediately — do not widen the retry exception tuple.
- `PipelineState` is a `TypedDict(total=False)`. Nodes return partial dicts that LangGraph merges; always merge `metrics` back in (`out | {"metrics": new_state["metrics"]}`).
- Graph is compiled once via module-level `_compiled` singleton (`get_graph()`).

### Streaming UX

`POST /api/v1/analyse` returns `job_id` immediately; pipeline runs in background task. Frontend opens `GET /api/v1/analyse/{job_id}/stream` (SSE, `sse-starlette`). Each node calls `_push(job_id, "step", ...)` via `app/pipeline/streaming.py` registry. Frontend hook `useAnalyseStream` consumes events and renders `StepProgress`.

### Layered code structure (`backend/app/`)

- `api/` — REST routes: `profile`, `analyse`, `applications`, `dashboard`. Thin — delegate to skills/services.
- `skills/` — LLM-driven units: `parse_jd`, `gap_analyse`, `write_cover_letter`, `tailor_resume`, `scrape_jd`, `parse_profile`. Each takes a `SkillContext(inputs=...)`, returns a Pydantic model. **This is where prompts live.**
- `tools/` — deterministic helpers callable by skills: `fetch_jd`, `resume_retriever` (Chroma vector search), `skill_taxonomy`, `web_search` (Brave, gated by `ENABLE_WEB_SEARCH`), `latex_compile` (gated by `ENABLE_LATEX_COMPILE`), `entity_diff`.
- `services/` — non-LLM infra: `pdf_parser`, `latex_resolver`, `upload_guard` (≤5MB, ≤50 files, MIME+suffix allowlist), `resume_chunker`, `embeddings`, `vector_store` (Chroma client wrapper), `resume_packager` (TailoredResume → PDF: pdf_source via styled HTML→xhtml2pdf; tex/tex_project via pdflatex), `resume_styled` (the resume-design layer — layout/typography/spacing CSS for `pdf_source` resumes; CSS is an xhtml2pdf subset: no flex/grid/sibling-combinators, page-break control via `-pdf-keep-with-next` only), `stats`.
- `models/` — SQLAlchemy 2.0 async ORM. `schemas/` — Pydantic request/response + pipeline contracts.
- `pipeline/` — `graph.py` (LangGraph), `runner.py` (background task entry), `streaming.py` (SSE registry).

### Storage split

- **PostgreSQL** (asyncpg + SQLAlchemy async): `profiles`, `applications`, `generated_outputs`. Schema in `backend/db/schema.sql`.
- **Chroma** (file-backed at `CHROMA_PATH`, default `./chroma_db`, no server): `resume_chunks` collection — embeddings of resume sections for retrieval during cover-letter / tailored-resume generation.

### Anti-fabrication / hardening

- `entity_diff` tool inspects tailored resume for new companies, dates, numerics not in source. On violation, the `tailor_resume` skill regenerates **once** before failing.
- LaTeX outputs (when source format is `.tex`) compiled via `pdflatex` before persist; on failure, errors fed back for one repair pass. Gate with `ENABLE_LATEX_COMPILE=false` if `pdflatex` unavailable.
- JD token cap: 8k tokens enforced on `/analyse`.
- Resume length: `tailor_resume` prompt targets ≤2 pages (trim weakest bullets, cap ~3–5 per role). Not hard-enforced — no page-count guard post-render.

### Models

Two tiers via env: `EXTRACTION_MODEL` (parse_jd, gap_analyse) and `GENERATION_MODEL` (write_cover_letter, tailor_resume). Default to `gpt-5.4-nano` / `gpt-5.4-mini`. Embeddings via `EMBEDDING_MODEL` (default `text-embedding-3-small`).

### Frontend

- React 18 + Vite + TypeScript + Tailwind. Routing: `react-router-dom`. State: Zustand (`store/appStore.ts`). Server state: `@tanstack/react-query`. Forms: `react-hook-form` + Zod.
- Pages: `Upload` → `Analyse` → `Results` (SSE-driven tabs) → `Dashboard`.
- API client in `src/api/client.ts`; types mirror backend Pydantic schemas in `src/api/types.ts`.

## Conventions

- Async everywhere on backend (FastAPI + SQLAlchemy async + httpx). Do not introduce sync DB calls.
- Skills return Pydantic models; nodes call `.model_dump()` before stuffing into `PipelineState`.
- New pipeline nodes: emit `step` events at `started` / `done`, record metric via `_record_metric`, wrap LLM calls in `_retrying()`.
- New skills go in `app/skills/`, inherit pattern from existing ones (`SkillContext` input contract). New deterministic helpers go in `app/tools/`.
