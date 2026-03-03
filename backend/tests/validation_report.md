# BioGate Week 4 Real-World Validation Report

## Test dataset

- **Fixture**: `backend/tests/fixtures/real_world_test.csv`
- **Total vendors**: 27
- **Composition**:
  - **Known BCC / subsidiaries (expected Red or Amber)**: BGI Research, BGI Genomics, Huawei Technologies, MGI Tech Co, Complete Genomics, WuXi AppTec, WuXi Biologics (7)
  - **Chinese-origin, not on watchlists (possible Yellow if country-flagged)**: SinoGene Scientific, Beijing Genomics Institute (non-BGI), Shanghai Biotech Co, Shenzhen Instrument Co (4)
  - **US/EU clean (expected Green)**: Thermo Fisher, Illumina, Agilent, Bio-Rad, MilliporeSigma, Corning, Sigma-Aldrich, Fisher Scientific, Beckman Coulter, Waters, Eurofins, Sartorius, Qiagen, Merck KGaA, Bruker, PerkinElmer (16)

## How to run validation

1. Ensure migrations 001–006 are applied (including `vendor_overrides`, `audit_reports`, `vendors.risk_reasoning`).
2. Run watchlist ingestion (BIS, OFAC, UFLPA) so `watchlist_entities` and `watchlist_snapshots` are populated.
3. From repo root:
   ```bash
   curl -X POST -H "Authorization: Bearer $BIOGATE_API_KEY" -F "file=@backend/tests/fixtures/real_world_test.csv" http://localhost:8000/audits/upload
   ```
4. Note `audit_id` from the response; then:
   ```bash
   curl -H "Authorization: Bearer $BIOGATE_API_KEY" "http://localhost:8000/audits/{audit_id}/report" -o report.json
   ```
5. Manually review every Red and Amber vendor in `report.json`: correct classification?, match evidence?, would a compliance officer agree?

## Metrics (fill after run)

| Metric | Target | Actual |
|--------|--------|--------|
| **False negative rate (Red)** | 0% – no known BCC missed | _TBD_ |
| **False positive rate (Red)** | 0% | _TBD_ |
| **False positive rate (Yellow)** | < 5% | _TBD_ |
| **Pipeline time (CSV upload → report)** | < 30 seconds | _TBD_ |

## Tier distribution (fill after run)

| Tier | Count |
|------|-------|
| Red | _TBD_ |
| Amber | _TBD_ |
| Yellow | _TBD_ |
| Green | _TBD_ |

## Manual review notes (fill after run)

- **Red / Amber**: For each flagged vendor, document (a) was the flag correct?, (b) match evidence, (c) would a compliance officer agree?
- **Bugs or threshold issues**: List any found and fixes applied.

## Definition of Done

- [ ] Risk scoring thresholds configurable without code changes
- [ ] Red/Amber/Yellow/Green correct on 25-vendor real-world test; 0% false negative for known BCC
- [ ] Manual override stores justification + user + timestamp; original tier preserved
- [ ] JSON risk report generates with valid schema, watchlist metadata, disclaimers; stored and retrievable via API
- [ ] Parent company resolution ≥ 2 levels; BCC subsidiaries correctly flagged
- [ ] Validation report documents FP rate, FN rate, and performance metrics
