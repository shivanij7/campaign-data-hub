"""LinkedIn Ads: JSON array, epoch-millisecond dates (UTC), spend as {amount: "str", currency}."""
from __future__ import annotations

import json
from decimal import Decimal

from ..models import ParsedFile, RowIssue
from .common import FatalFileError, build_metric, parse_epoch_ms


def parse(path, rates) -> ParsedFile:
    with open(path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise FatalFileError("expected a JSON array of records at the top level")

    out = ParsedFile()
    for position, item in enumerate(data, start=1):
        out.rows_read += 1
        if not isinstance(item, dict):
            out.issues.append(RowIssue(position, "malformed_record", "error", None,
                                       f"record is not an object: {item!r}", {"value": repr(item)}))
            continue
        spend = item.get("spend")
        spend = spend if isinstance(spend, dict) else {}
        metric, issues = build_metric(
            source_row=position, raw=item, campaign_raw=item.get("campaign"),
            date_result=parse_epoch_ms(item.get("date_ts")),
            spend_raw=spend.get("amount"), spend_divisor=Decimal(1), spend_label=None,
            currency=spend.get("currency"),
            impressions_raw=item.get("impressions"), clicks_raw=item.get("clicks"), rates=rates)
        out.issues += issues
        if metric:
            out.metrics.append(metric)
    return out
