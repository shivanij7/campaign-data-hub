"""Plain dataclasses passed between parsers, checks and the pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class RowIssue:
    """Something noticed about one source row.

    severity "error"      -> row cannot be trusted, it is quarantined (not loaded)
    severity "correction" -> row is loaded, but we repaired a value (e.g. trimmed a name)
    """
    row: int                      # CSV line number (header = 1) / JSON array position (1-based)
    code: str
    severity: str
    field: str | None
    message: str
    raw: dict | None = None


@dataclass
class MetricRow:
    """One validated, canonical row (before campaign-name canonicalization / scale fixes)."""
    source_row: int
    campaign: str
    date: date
    spend_usd: Decimal
    impressions: int
    clicks: int
    transforms: list[str] = field(default_factory=list)   # NFR-3 traceability


@dataclass
class ParsedFile:
    rows_read: int = 0
    metrics: list[MetricRow] = field(default_factory=list)
    issues: list[RowIssue] = field(default_factory=list)
    fatal: str | None = None      # whole file unreadable (bad JSON, missing columns, ...)


@dataclass
class ScaleFinding:
    """Is this delivery's spend on the same scale as the platform's other deliveries?"""
    delivery_cpm: float           # median spend (USD) per 1,000 impressions in this delivery
    baseline_cpm: float           # median of the same figure across the platform's other deliveries
    ratio: float
    anomalous: bool
    factor: int | None = None     # recognized unit error (e.g. 100 = cents), if any
    corrected: bool = False


@dataclass
class DeliveryContext:
    """Everything the quality checks may look at for one delivery. Checks only *read* this."""
    filename: str
    platform: str
    week_start: date | None
    received: bool = True                 # False = expected but never arrived
    recognized: bool = True               # False = filename does not follow the convention
    content_hash: str | None = None
    window: tuple[date, date] | None = None     # dates this delivery is expected to cover
    rows_read: int = 0
    fatal: str | None = None
    loaded: list[MetricRow] = field(default_factory=list)       # rows that will be stored
    issues: list[RowIssue] = field(default_factory=list)        # everything noticed, row level
    duplicate_of: str | None = None       # byte-identical to an earlier delivery
    scale: ScaleFinding | None = None
    expected_campaigns: frozenset[str] = frozenset()

    @property
    def usable(self) -> bool:
        """True when row/file-level checks make sense for this delivery."""
        return self.received and self.recognized and self.fatal is None and self.duplicate_of is None
