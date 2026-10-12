"""Google Ads: CSV, ISO dates, cost in micros (1,000,000 micros = 1 currency unit)."""
from __future__ import annotations

from decimal import Decimal

from ..models import ParsedFile
from .common import build_metric, parse_date_text, read_csv_rows

REQUIRED = ["Campaign", "Day", "Cost (micros)", "Currency", "Impr.", "Clicks"]
DATE_FORMATS = ("%Y-%m-%d",)


def parse(path, rates) -> ParsedFile:
    out = ParsedFile()
    for line, raw in read_csv_rows(path, REQUIRED):
        out.rows_read += 1
        metric, issues = build_metric(
            source_row=line, raw=raw, campaign_raw=raw.get("Campaign"),
            date_result=parse_date_text(raw.get("Day"), DATE_FORMATS),
            spend_raw=raw.get("Cost (micros)"), spend_divisor=Decimal(1_000_000),
            spend_label="micros/1e6", currency=raw.get("Currency"),
            impressions_raw=raw.get("Impr."), clicks_raw=raw.get("Clicks"), rates=rates)
        out.issues += issues
        if metric:
            out.metrics.append(metric)
    return out
