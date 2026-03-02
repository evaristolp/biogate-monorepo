-- Add parent_company and equipment_type from Claude normalization.
ALTER TABLE vendors
  ADD COLUMN IF NOT EXISTS parent_company TEXT,
  ADD COLUMN IF NOT EXISTS equipment_type TEXT;

COMMENT ON COLUMN vendors.parent_company IS 'Ultimate parent company from Claude (parent_company_hint)';
COMMENT ON COLUMN vendors.equipment_type IS 'Equipment/supply type from Claude (equipment_type_hint)';
