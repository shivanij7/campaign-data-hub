"""Row validation shared by all platforms.

Platform parsers only *extract* raw values; every validity rule lives here so a new
rule (or a new platform) is a one-place change.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from ..models import MetricRow, RowIssue


class FatalFileError(Exception):
    """The file as a whole cannot be parsed (not a single row's fault)."""


# ---------- readers ----------------------------------------------------------------

def read_csv_rows(path, required: list[str]):
    """Yield (line_number, row_dict). Header is line 1, so first data row is line 2."""
    with open(path, newline="", encoding="utf-8-sig") as fh:   # utf-8-sig tolerates a BOM
        reader = csv.DictReader(fh)
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            raise FatalFileError(f"missing required columns: {missing}")
        for line_no, row in enumerate(reader, start=2):
            yield line_no, {k: v for k, v in row.items() if k is not None}


# ---------- dates ------------------------------------------------------------------

@dataclass
class DateResult:
    value: date | None = None
    error: str | None = None        # "missing" or a description
    deviation: str | None = None    # format actually used when it was not the platform's primary


def parse_date_text(raw, formats: tuple[str, ...]) -> DateResult:
    """Try formats in order; formats[0] is the platform's documented one."""
    text = "" if raw is None else str(raw).strip()
    if not text:
        return DateResult(error="missing")
    for i, fmt in enumerate(formats):
        try:
            return DateResult(value=datetime.strptime(text, fmt).date(),
                              deviation=fmt if i else None)
        except ValueError:
            continue
    return DateResult(error=f"not a valid date: {text!r}")   # also catches 06/31


def parse_epoch_ms(raw) -> DateResult:
    if raw is None or raw == "":
        return DateResult(error="missing")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return DateResult(error=f"timestamp is not a number: {raw!r}")
    try:
        return DateResult(value=datetime.fromtimestamp(raw / 1000, tz=timezone.utc).date())
    except (OverflowError, OSError, ValueError):
        return DateResult(error=f"timestamp out of range: {raw!r}")


# ---------- numbers ----------------------------------------------------------------

_INT_RE = re.compile(r"-?\d+")


def parse_int(raw) -> tuple[int | None, str | None]:
    """Returns (value, error). error is "missing" or a description."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, "missing"
    if isinstance(raw, bool):
        return None, f"not an integer: {raw!r}"
    if isinstance(raw, int):
        return raw, None
    if isinstance(raw, str) and _INT_RE.fullmatch(raw.strip()):
        return int(raw.strip()), None
    return None, f"not an integer: {raw!r}"


def parse_decimal(raw) -> tuple[Decimal | None, str | None]:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, "missing"
    if isinstance(raw, bool):
        return None, f"not a number: {raw!r}"
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        return None, f"not a number: {raw!r}"
    if not value.is_finite():
        return None, f"not a finite number: {raw!r}"
    return value, None


# ---------- the one place rows are validated -----------------------------------------

def build_metric(*, source_row: int, raw: dict, campaign_raw, date_result: DateResult,
                 spend_raw, spend_divisor: Decimal, spend_label: str | None, currency: str | None,
                 impressions_raw, clicks_raw, rates: dict[str, Decimal]
                 ) -> tuple[MetricRow | None, list[RowIssue]]:
    """Validate + convert one row. Returns (row or None if quarantined, issues)."""
    issues: list[RowIssue] = []

    def add(code: str, severity: str, field: str | None, message: str):
        issues.append(RowIssue(source_row, code, severity, field, message, raw))

    # campaign
    text = "" if campaign_raw is None else str(campaign_raw)
    campaign = " ".join(text.split())
    if not campaign:
        add("missing_field", "error", "campaign", "campaign name is empty")
    elif campaign != text:
        add("campaign_whitespace", "correction", "campaign",
            f"trimmed/collapsed whitespace in {text!r}")

    # date
    if date_result.error == "missing":
        add("missing_field", "error", "date", "date is missing")
    elif date_result.error:
        add("invalid_date", "error", "date", date_result.error)
    elif date_result.deviation:
        add("date_format_deviation", "correction", "date",
            f"date was not in the platform's usual format; parsed with {date_result.deviation!r}")

    # spend (+ currency)
    amount, err = parse_decimal(spend_raw)
    spend_usd = None
    if err == "missing":
        add("missing_field", "error", "spend", "spend is missing")
    elif err:
        add("invalid_number", "error", "spend", err)
    elif amount < 0:
        add("negative_value", "error", "spend", f"spend is negative: {amount}")
    else:
        code = (currency or "").strip().upper()
        rate = rates.get(code)
        if rate is None:
            add("unknown_currency", "error", "currency", f"no exchange rate for currency {currency!r}")
        else:
            spend_usd = amount / spend_divisor * rate

    # impressions / clicks
    values: dict[str, int | None] = {}
    for name, raw_val in (("impressions", impressions_raw), ("clicks", clicks_raw)):
        val, err = parse_int(raw_val)
        values[name] = val
        if err == "missing":
            add("missing_field", "error", name, f"{name} is missing")
        elif err:
            add("invalid_number", "error", name, err)
        elif val < 0:
            add("negative_value", "error", name, f"{name} is negative: {val}")
    imp, clk = values["impressions"], values["clicks"]
    if imp is not None and clk is not None and clk > imp and imp >= 0 and clk >= 0:
        add("clicks_exceed_impressions", "error", "clicks", f"clicks ({clk}) > impressions ({imp})")

    if any(i.severity == "error" for i in issues):
        return None, issues

    transforms = []
    if spend_label:
        transforms.append(spend_label)
    code = (currency or "").strip().upper()
    if rates[code] != 1:
        transforms.append(f"fx {code}->USD @ {rates[code]}")
    return MetricRow(source_row, campaign, date_result.value, spend_usd.quantize(Decimal("0.000001")),
                     imp, clk, transforms), issues
