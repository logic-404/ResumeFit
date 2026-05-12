-- ResumeFit — schema
-- Apply: psql "$DATABASE_URL" -f db/schema.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─────────────────────────────────────────────────────────────
-- profiles (singleton)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name       VARCHAR(255) NOT NULL,
    email           VARCHAR(255),
    phone           VARCHAR(50),
    linkedin_url    VARCHAR(500),

    skills          JSONB NOT NULL DEFAULT '[]'::jsonb,
    experience      JSONB NOT NULL DEFAULT '[]'::jsonb,
    education       JSONB NOT NULL DEFAULT '[]'::jsonb,
    certifications  JSONB NOT NULL DEFAULT '[]'::jsonb,

    raw_resume_text TEXT NOT NULL,
    resume_hash     VARCHAR(64) NOT NULL,

    source_format   VARCHAR(20) NOT NULL DEFAULT 'pdf',
    file_structure  JSONB,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS one_profile_only ON profiles ((true));

-- Note: resume chunks live in Chroma (file-backed vector DB), not Postgres.

-- ─────────────────────────────────────────────────────────────
-- applications
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id      UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    company_name    VARCHAR(255) NOT NULL,
    role_title      VARCHAR(255) NOT NULL,
    location        VARCHAR(255),
    salary_range    VARCHAR(100),
    job_url         VARCHAR(1000),

    raw_jd_text     TEXT NOT NULL,
    parsed_jd       JSONB NOT NULL,

    status          VARCHAR(50) NOT NULL DEFAULT 'draft',
    applied_date    DATE,
    response_date   DATE,
    notes           TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_applications_status   ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_profile  ON applications(profile_id);
CREATE INDEX IF NOT EXISTS idx_applications_created  ON applications(created_at DESC);

-- ─────────────────────────────────────────────────────────────
-- generated_outputs
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS generated_outputs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id    UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,

    output_type       VARCHAR(50) NOT NULL,
    content           JSONB NOT NULL,

    version           INTEGER NOT NULL DEFAULT 1,

    model_used        VARCHAR(100),
    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    cached_tokens     INTEGER,
    latency_ms        INTEGER,

    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uniq_output_version
        UNIQUE (application_id, output_type, version),
    CONSTRAINT chk_output_type
        CHECK (output_type IN ('cover_letter', 'gap_analysis', 'tailored_resume'))
);

CREATE INDEX IF NOT EXISTS idx_outputs_application ON generated_outputs(application_id);
CREATE INDEX IF NOT EXISTS idx_outputs_type        ON generated_outputs(output_type);
CREATE INDEX IF NOT EXISTS idx_outputs_content_gin ON generated_outputs USING GIN (content);

-- ─────────────────────────────────────────────────────────────
-- application status check
-- ─────────────────────────────────────────────────────────────
ALTER TABLE applications
    DROP CONSTRAINT IF EXISTS chk_application_status;
ALTER TABLE applications
    ADD CONSTRAINT chk_application_status
    CHECK (status IN ('draft','applied','interview','offer','rejected','withdrawn'));
