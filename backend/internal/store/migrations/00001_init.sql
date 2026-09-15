-- +goose Up

-- Anonymous demo users: a nickname, no password.
CREATE TABLE sessions (
    id          uuid PRIMARY KEY,
    nickname    text        NOT NULL CHECK (char_length(nickname) BETWEEN 1 AND 32),
    ip          inet        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- One row per submitted comment. The id is a UUIDv7 generated in Go, so it
-- sorts by time and the API can return it before this row is written.
CREATE TABLE comments (
    id             uuid PRIMARY KEY,
    session_id     uuid        NOT NULL REFERENCES sessions (id),
    raw_text       text        NOT NULL CHECK (char_length(raw_text) <= 5000),
    -- sha256 of raw_text exactly as sent to the model (also the cache key).
    text_sha256    bytea       NOT NULL CHECK (octet_length(text_sha256) = 32),
    -- Which model + threshold configuration produced the result.
    artifact_hash  text        NOT NULL,
    -- The full AnalysisResult from the Python pipeline (AI/contracts/schema.py):
    -- guards, form patterns and spans stay available without extra tables.
    result         jsonb       NOT NULL,
    latency_ms     double precision NOT NULL CHECK (latency_ms >= 0),
    queue_wait_ms  double precision CHECK (queue_wait_ms >= 0),
    from_cache     boolean     NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- One row per offense type (content code) per comment, after channel fusion.
CREATE TABLE analysis_results (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    comment_id     uuid        NOT NULL REFERENCES comments (id) ON DELETE CASCADE,
    offense_type   text        NOT NULL CHECK (offense_type IN (
                       'A1','A2','A3','A4','B1','B2','B3','B4','B5',
                       'C1','C2','C3','C4','C5','D1','CLEAN')),
    score          double precision NOT NULL CHECK (score >= 0 AND score <= 1),
    threshold      double precision,        -- NULL = the decision layer did not decide
    fired          boolean,                 -- NULL = not decided
    engine         text        NOT NULL CHECK (engine IN ('rule', 'lexicon', 'model')),
    source         text        NOT NULL,    -- e.g. m3_encoder@normalized
    model_version  text        NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- The verdict Python's decision layer produced. Go stores it, never derives it.
CREATE TABLE moderation_decisions (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    comment_id     uuid        NOT NULL UNIQUE REFERENCES comments (id) ON DELETE CASCADE,
    -- NULL when the decision layer itself failed (verdict: null).
    final_action   text                 CHECK (final_action IN ('block', 'escalate', 'review', 'nudge', 'clean')),
    fired_types    text[]      NOT NULL DEFAULT '{}',
    guards_active  text[]      NOT NULL DEFAULT '{}',
    -- true when a module was a stub, failed or returned invalid output.
    degraded       boolean     NOT NULL,
    explanation    text        NOT NULL,   -- Turkish sentence, verbatim
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE request_metrics (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    endpoint       text        NOT NULL,
    method         text        NOT NULL,
    status_code    smallint    NOT NULL,
    latency_ms     double precision NOT NULL CHECK (latency_ms >= 0),
    queue_wait_ms  double precision,
    batch_size     smallint,
    cache_hit      boolean,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- Feed: newest first, cursor on (created_at, id).
CREATE INDEX comments_feed_idx ON comments (created_at DESC, id DESC);
CREATE INDEX comments_session_idx ON comments (session_id, created_at DESC);

-- Dashboard: totals per type, only fired rows are counted.
CREATE INDEX analysis_results_type_idx ON analysis_results (offense_type, created_at) WHERE fired;
CREATE INDEX analysis_results_comment_idx ON analysis_results (comment_id);

-- Dashboard: action counts; flagged list = everything that is not clean.
CREATE INDEX moderation_decisions_action_idx ON moderation_decisions (final_action, created_at);
CREATE INDEX moderation_decisions_flagged_idx ON moderation_decisions (created_at DESC)
    WHERE final_action IS DISTINCT FROM 'clean';

-- Append-only, time-ordered: BRIN is tiny and fast for time ranges.
CREATE INDEX request_metrics_created_brin ON request_metrics USING brin (created_at);

-- +goose Down
DROP TABLE request_metrics;
DROP TABLE moderation_decisions;
DROP TABLE analysis_results;
DROP TABLE comments;
DROP TABLE sessions;
