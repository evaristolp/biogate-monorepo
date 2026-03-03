"""
Pydantic models for BioGate JSON risk report. Mirrors risk_report_schema.json.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ReportMetadata(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    audit_id: UUID
    organization_id: UUID
    organization_name: str = "Default Organization"
    generated_at: datetime = Field(default_factory=lambda: datetime.now())
    pipeline_version: str = "1.0"
    scoring_config_version: str = "1.0.0"


class WatchlistMetadataItem(BaseModel):
    source_list: str
    snapshot_date: str
    record_count: int
    file_hash: str | None = None


class VendorsByTier(BaseModel):
    red: int = 0
    amber: int = 0
    yellow: int = 0
    green: int = 0


class ReportSummary(BaseModel):
    total_vendors: int
    vendors_by_tier: VendorsByTier
    overall_risk_assessment: str
    flagged_vendor_count: int


class VendorReportItem(BaseModel):
    vendor_id: UUID
    raw_input_name: str
    normalized_name: str | None = None
    country: str | None = None
    parent_company: str | None = None
    equipment_type: str | None = None
    risk_tier: str
    effective_tier: str
    match_evidence: list[dict[str, Any]] = Field(default_factory=list)
    override_history: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class RiskReport(BaseModel):
    report_metadata: ReportMetadata
    watchlist_metadata: list[WatchlistMetadataItem] = Field(default_factory=list)
    summary: ReportSummary
    vendors: list[VendorReportItem]
    disclaimers: list[str] = Field(default_factory=list)


DEFAULT_DISCLAIMER = (
    "This report screens against available proxy watchlists. "
    "The official OMB Biotechnology Company of Concern list has not yet been published as of this report date. "
    "Results represent best-effort compliance screening."
)
