"""Response models (they also drive the OpenAPI docs at /docs)."""
from __future__ import annotations

from pydantic import BaseModel


class Derived(BaseModel):
    spend_usd: float
    impressions: int
    clicks: int
    ctr: float | None        # clicks / impressions; null when impressions = 0
    cpc: float | None        # spend / clicks;       null when clicks = 0


class MetricOut(Derived):
    id: int
    delivery_id: int
    source_row: int
    platform: str
    campaign: str
    date: str
    transforms: list[str]    # rules applied to produce this row (NFR-3)


class MetricPage(BaseModel):
    items: list[MetricOut]
    total: int
    limit: int
    offset: int


class GroupOut(Derived):
    platform: str
    campaign: str | None     # null when group_by=platform
    rows: int                # campaign-days contributing


class SourceDelivery(BaseModel):
    delivery_id: int
    filename: str
    health: str
    rows: int


class Lineage(BaseModel):
    deliveries: list[SourceDelivery]      # which deliveries produced these numbers
    transforms: dict[str, int]            # which normalization rules touched them (rule -> rows)


class SummaryOut(BaseModel):
    group_by: str
    filters: dict
    totals: Derived
    groups: list[GroupOut]
    lineage: Lineage


class CheckOut(BaseModel):
    name: str
    level: str
    status: str
    summary: str
    details: dict


class Problem(BaseModel):
    check: str
    status: str
    summary: str


class DeliveryOut(BaseModel):
    id: int
    platform: str
    week_start: str
    filename: str
    received: bool
    health: str
    rows_read: int
    rows_loaded: int
    rows_quarantined: int
    ingested_at: str
    check_counts: dict[str, int]
    problems: list[Problem]               # the non-passing checks, for at-a-glance scanning


class QuarantinedRow(BaseModel):
    source_row: int
    code: str
    field: str | None
    message: str
    raw: dict | None


class DeliveryDetail(DeliveryOut):
    content_hash: str | None
    checks: list[CheckOut]
    quarantined_rows: list[QuarantinedRow]


class IngestRequest(BaseModel):
    filename: str | None = None           # omit for a full run; set to re-ingest one delivery


class IngestResult(BaseModel):
    mode: str                             # "full" | "single"
    deliveries: list[dict]
    errors: list[dict]
    health_counts: dict[str, int]
