"""Check registry + runner."""
from __future__ import annotations

from ..models import DeliveryContext
from . import policy
from .base import STATUS_RANK, Check, CheckResult
from .checks import (Coverage, DateWindow, DeliveryReceived, DuplicateDelivery, FilenameRecognised,
                     FileReadable, RowIssueCheck, UnitScale)

# Order = order shown in reports. Add a new check by appending it here.
CHECKS: list[Check] = [
    FilenameRecognised(),
    FileReadable(),
    DeliveryReceived(),
    DuplicateDelivery(),
    RowIssueCheck("completeness", {"missing_field"}, "missing values", fail_above=policy.ROW_FAIL_FRACTION),
    RowIssueCheck("validity",
                  {"invalid_date", "invalid_number", "negative_value", "unknown_currency",
                   "clicks_exceed_impressions", "malformed_record"},
                  "invalid values", fail_above=policy.ROW_FAIL_FRACTION),
    # exact duplicates lose no information once removed -> always only a warning
    RowIssueCheck("duplicate_rows", {"duplicate_row"}, "exact duplicate rows"),
    # same key, different numbers: we cannot know which is right -> any occurrence fails
    RowIssueCheck("conflicting_duplicates", {"conflicting_duplicate"}, "conflicting duplicates", fail_above=0.0),
    RowIssueCheck("normalization", {"campaign_whitespace", "campaign_case", "date_format_deviation"},
                  "values repaired during normalization"),
    Coverage(),
    DateWindow(),
    UnitScale(),
]


def run_checks(ctx: DeliveryContext, checks: list[Check] = CHECKS) -> list[CheckResult]:
    """Run every applicable check. A crashing check is reported as a failure, never propagated."""
    results = []
    for check in checks:
        try:
            if not check.applies(ctx):
                continue
            results.append(check.run(ctx))
        except Exception as exc:  # noqa: BLE001 - isolation boundary (NFR-2)
            results.append(CheckResult(check.name, check.level, "fail",
                                       f"check crashed: {type(exc).__name__}: {exc}", {"error": repr(exc)}))
    return results


def health_from(results: list[CheckResult]) -> str:
    """Overall delivery health = worst check status."""
    worst = max((STATUS_RANK[r.status] for r in results), default=0)
    return {0: "pass", 1: "warn", 2: "fail"}[worst]
