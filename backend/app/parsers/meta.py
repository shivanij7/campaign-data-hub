"""Meta Ads: CSV, MM/DD/YYYY dates, spend already in USD dollars."""
from __future__ import annotations

from decimal import Decimal

from ..models import ParsedFile
from .common import build_metric, parse_date_text, read_csv_rows

REQUIRED = ["campaign_name", "date", "spend_usd", "impressions", "clicks"]
DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d")      # primary first; ISO seen as a deviation in the data


def parse(path, rates) -> ParsedFile:
    out = ParsedFile()
    for line, raw in read_csv_rows(path, REQUIRED):
        out.rows_read += 1
        metric, issues = build_metric(
            source_row=line, raw=raw, campaign_raw=raw.get("campaign_name"),
            date_result=parse_date_text(raw.get("date"), DATE_FORMATS),
            spend_raw=raw.get("spend_usd"), spend_divisor=Decimal(1), spend_label=None,
            currency="USD", impressions_raw=raw.get("impressions"), clicks_raw=raw.get("clicks"),
            rates=rates)
        out.issues += issues
        if metric:
            out.metrics.append(metric)
    return out
