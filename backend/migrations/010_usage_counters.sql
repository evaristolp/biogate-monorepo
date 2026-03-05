-- Simple usage counters for free-tier / rate limiting.
-- Tracks how many times a given identity has called a given endpoint.

CREATE TABLE IF NOT EXISTS usage_counters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    first_used_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS usage_counters_identity_endpoint_idx
    ON usage_counters(identity, endpoint);

COMMENT ON TABLE usage_counters IS 'Per-identity usage counters for free-tier limits (e.g. 2–3 free runs per endpoint).';
COMMENT ON COLUMN usage_counters.identity IS 'Opaque identity string (e.g. user:email@example.com or api_key:<hash>).';
COMMENT ON COLUMN usage_counters.endpoint IS 'Logical endpoint name such as audits/upload_and_audit.';

