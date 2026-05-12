# ResumeFit

AI-powered tool that turns a resume and a job description into three tailored artefacts: a **tailored resume** (same source format as your upload), a **cover letter**, and a **gap analysis**, with a persistent application dashboard.

## Features

- **Tailored resume** — regrounds bullets to the JD while `entity_diff` blocks fabricated companies, dates, and numbers; optional LaTeX compile-and-repair for `.tex` sources.
- **Cover letter** — generation with resume retrieval; optional Brave web search when enabled.
- **Gap analysis** — JD parsing plus resume chunk retrieval and skill taxonomy lookup.
- **Streaming UI** — `POST /analyse` returns immediately; the client follows SSE for step progress and final payloads.
- **Single profile** — enforced in PostgreSQL; Chroma stores resume chunks for retrieval.

## Architecture

High level: the browser talks to FastAPI over REST and SSE; the analyse job runs in a LangGraph pipeline and persists to Postgres while using Chroma for resume chunk retrieval. Skill and tool names are listed in [Pipeline reference](#pipeline-reference-langgraph) below.

```mermaid
flowchart TB
  subgraph client["Client"]
    FE["React · Vite · Tailwind<br/>Upload · Analyse · Results · Dashboard"]
  end

  subgraph server["Backend"]
    API["FastAPI — REST + SSE"]
    LG["LangGraph<br/>parse_jd → gap_analyse → cover_letter ∥ tailor_resume → persist"]
    API --> LG
  end

  subgraph data["Storage"]
    PG[("PostgreSQL<br/>profiles · applications · outputs")]
    CH[("Chroma (file-backed)<br/>resume_chunks")]
  end

  FE <-->|HTTPS| API
  LG --> PG
  LG --> CH
```

## Prerequisites

- Python 3.11+
- PostgreSQL 16 — `db/schema.sql` runs `CREATE EXTENSION IF NOT EXISTS pgcrypto` (needed for UUID generation)
- Node.js 20+
- **Chroma** — file-backed at `CHROMA_PATH` (default `./chroma_db`); created on first run; no separate server
- `pdflatex` on PATH for LaTeX verify/repair (set `ENABLE_LATEX_COMPILE=false` to skip)
- OpenAI API key

## Installation

### Backend

```bash
cd backend
uv venv .venv --python 3.11        # or: python -m venv .venv
uv pip install -e .[dev]           # or: .venv/Scripts/pip install -e .[dev]

cp .env.example .env               # then edit DATABASE_URL + OPENAI_API_KEY
```

Apply the database schema (bash / Git Bash):

```bash
psql "$DATABASE_URL" -f db/schema.sql
```

> [!NOTE]
> On **Windows PowerShell**, use `psql $env:DATABASE_URL -f db/schema.sql` (from `backend/`). Adjust the connection string in `.env` to match your Postgres host and database name.

```bash
.venv/Scripts/uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

> [!NOTE]
> Folders like `.cursor/` and `.claude/` are in `.gitignore` so editor and agent config stay local; they are not required to run the app.

## Usage

- **API docs** — http://localhost:8000/docs after the backend is up.
- **App** — http://localhost:5173 with Vite dev server; `/api/*` is proxied to port 8000.
- **Production build (frontend)** — `cd frontend && npm run build` (runs `tsc -b` then Vite); `npm run preview` serves the build locally.
- **Eval harness** — from `backend/`, with venv activated:

```bash
.venv/Scripts/python.exe -m eval.run_eval
```

Reads `eval/expectations.yaml`, replays the pipeline per resume/JD pair, and asserts match bands, skills, anti-fabrication, and cover-letter keyword coverage. Exit code 1 on regression. Stage the resume via `POST /profile/upload` first.

> [!WARNING]
> Never commit real API keys. Copy `backend/.env.example` to `backend/.env` and keep secrets there; that file and other `.env.*` files (except `**/.env.example`) are gitignored.

## Configuration (`.env`)

| Var | Purpose |
|-----|---------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` |
| `OPENAI_API_KEY` | required |
| `EXTRACTION_MODEL` | default `gpt-5.4-nano` (parse / gap analysis) |
| `GENERATION_MODEL` | default `gpt-5.4-mini` (cover letter / tailored resume) |
| `EMBEDDING_MODEL` | default `text-embedding-3-small` |
| `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` | LangSmith traces |
| `BRAVE_SEARCH_API_KEY` | required if `ENABLE_WEB_SEARCH=true` |
| `ENABLE_WEB_SEARCH` | default `false` |
| `ENABLE_LATEX_COMPILE` | default `true` |
| `PDFLATEX_BIN` | default `pdflatex` |
| `CHROMA_PATH` | vector store directory, default `./chroma_db` |
| `CHROMA_COLLECTION` | default `resume_chunks` |
| `CORS_ORIGINS` | comma-separated, default `http://localhost:5173` |
| `APP_ENV` | e.g. `development` |
| `APP_PORT` | default `8000` (reference for deployment; uvicorn CLI still sets the listen port) |

## Pipeline reference (LangGraph)

| Stage | Skill | Tools used | Model |
|-------|-------|------------|-------|
| 1 | `parse_jd` | — | extraction |
| 2 | `gap_analyse` | `resume_retriever`, `skill_taxonomy_lookup` | extraction |
| 3 | `write_cover_letter` | `resume_retriever`, `web_search` (optional) | generation |
| 4 | `tailor_resume` | `resume_retriever`, `entity_diff`, `latex_compile_check` | generation |
| 5 | `persist` | — | n/a (DB) |

Stages 3 and 4 run in parallel after stage 2. The persist node writes application plus generated outputs in **one transaction**.

### Streaming

`POST /api/v1/analyse` returns a `job_id` immediately; the pipeline runs in the background. The client opens `GET /api/v1/analyse/{job_id}/stream` (SSE), renders step progress from `step` events, then the three result tabs on the final `result` event.

### Hardening

- Singleton profile: `UNIQUE INDEX one_profile_only ON profiles ((true))`.
- Upload guard: ≤ 5 MB per file, ≤ 50 files per request, MIME + suffix allowlist.
- JD token cap (8k tokens) on `/analyse`.
- Tenacity retries on transient OpenAI errors (rate limit, timeout, connection only).
- `entity_diff` triggers one regeneration on violation before failing.
- LaTeX: `pdflatex` before persist; one repair pass on compile failure.

## Repository layout

```
backend/
  app/
    api/           {profile, analyse, applications, dashboard}.py
    models/        SQLAlchemy ORM
    schemas/       Pydantic request/response + pipeline contracts
    skills/        parse_jd · gap_analyse · write_cover_letter · tailor_resume · scrape_jd · parse_profile
    tools/         fetch_jd · resume_retriever · skill_taxonomy · web_search · latex_compile · entity_diff
    pipeline/      graph.py (LangGraph) · runner.py · streaming.py
    services/      pdf_parser · latex_resolver · upload_guard · resume_chunker · embeddings ·
                   vector_store · resume_packager · resume_styled · stats
  db/schema.sql
  eval/            golden/ + expectations.yaml + run_eval.py + evaluators.py
  tests/           pytest suite

frontend/
  src/
    pages/         Upload, Analyse, Results, Dashboard
    components/    Layout, StepProgress
    hooks/         useAnalyseStream
    api/           client.ts, types.ts
    store/         appStore.ts (Zustand)
```

## Tests

```bash
# backend
cd backend && .venv/Scripts/python.exe -m pytest tests -q
# frontend
cd frontend && npm run lint
```

`npm run lint` runs `tsc --noEmit` (no ESLint in this repo).
