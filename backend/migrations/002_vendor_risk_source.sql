-- Add parent-company match and effective score to vendors.
ALTER TABLE vendors
  ADD COLUMN IF NOT EXISTS risk_source TEXT,
  ADD COLUMN IF NOT EXISTS parent_match_evidence JSONB,
  ADD COLUMN IF NOT EXISTS effective_score INTEGER;

COMMENT ON COLUMN vendors.risk_source IS 'direct | parent_company';
COMMENT ON COLUMN vendors.parent_match_evidence IS 'Top match for parent_company_hint when risk_source=parent_company';
COMMENT ON COLUMN vendors.effective_score IS 'Score used for tier (max of direct and parent match when applicable)';
