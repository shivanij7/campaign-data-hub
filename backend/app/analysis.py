"""Turns a folder of deliveries into DeliveryContexts. Pure: reads files, touches no database.

Because it is a pure function of the folder contents, running it twice gives the same
answer -- that is what makes ingestion idempotent (NFR-1).

Stages (order matters):
  1. parse each file; flag byte-identical re-deliveries and skip them
  2. canonicalize campaign names (case/whitespace) using the most common spelling
  3. detect + correct unit/scale errors by comparing against the platform's other deliveries
  4. drop duplicate rows (first occurrence wins), within and across deliveries
  5. record corrections on the rows they touched (traceability)
  6. add placeholders for deliveries that never arrived and for unrecognizable filenames
"""
from __future__ import annotations

import hashlib
import statistics
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from . import config
from .deliveries import discover, expected_window
from .models import DeliveryContext, RowIssue, ScaleFinding
from .parsers import parse_file
from .quality import policy

SIX_DP = Decimal("0.000001")


def analyse(directory=None, rates=None) -> list[DeliveryContext]:
    directory = Path(directory or config.DELIVERIES_DIR)
    rates = rates or config.load_rates()
    files, unrecognized = discover(directory)

    # ---- 1. parse ---------------------------------------------------------------
    contexts: list[DeliveryContext] = []
    first_by_hash: dict[tuple[str, str], str] = {}
    for f in files:
        ctx = DeliveryContext(filename=f.filename, platform=f.platform, week_start=f.week_start,
                              window=expected_window(f.week_start))
        contexts.append(ctx)
        try:
            ctx.content_hash = hashlib.sha256(f.path.read_bytes()).hexdigest()
        except OSError as exc:
            ctx.fatal = f"{type(exc).__name__}: {exc}"
            continue
        key = (f.platform, ctx.content_hash)
        if key in first_by_hash:                      # same bytes already seen -> skip entirely
            ctx.duplicate_of = first_by_hash[key]
            continue
        first_by_hash[key] = f.filename
        parsed = parse_file(f.platform, f.path, rates)
        ctx.rows_read, ctx.fatal = parsed.rows_read, parsed.fatal
        ctx.issues, ctx.loaded = list(parsed.issues), list(parsed.metrics)

    active = [c for c in contexts if c.usable]
    _canonicalize_campaigns(active)
    vocabulary = _vocabulary(active)
    _detect_scale(active)
    _drop_duplicate_rows(active)
    _record_corrections(active)

    # ---- 6. placeholders ------------------------------------------------------------
    for c in contexts:
        c.expected_campaigns = vocabulary.get(c.platform, frozenset())
    contexts += _missing_deliveries(files, vocabulary)
    contexts += [DeliveryContext(filename=name, platform="unknown", week_start=None, recognized=False)
                 for name in unrecognized]
    return contexts


# ---------------------------------------------------------------------------------

def _canonicalize_campaigns(active: list[DeliveryContext]) -> None:
    """'brand awareness q2' and 'Brand Awareness Q2' are one campaign. Canonical form =
    the most frequent spelling per platform (ties broken alphabetically => deterministic)."""
    spellings: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for c in active:
        for m in c.loaded:
            spellings[(c.platform, m.campaign.casefold())][m.campaign] += 1
    canonical = {k: sorted(v.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for k, v in spellings.items()}
    for c in active:
        for m in c.loaded:
            target = canonical[(c.platform, m.campaign.casefold())]
            if m.campaign != target:
                c.issues.append(RowIssue(m.source_row, "campaign_case", "correction", "campaign",
                                         f"{m.campaign!r} -> {target!r} (most common spelling)"))
                m.campaign = target


def _vocabulary(active: list[DeliveryContext]) -> dict[str, frozenset[str]]:
    names: dict[str, set[str]] = defaultdict(set)
    for c in active:
        names[c.platform].update(m.campaign for m in c.loaded)
    return {p: frozenset(v) for p, v in names.items()}


def _detect_scale(active: list[DeliveryContext]) -> None:
    """Compare each delivery's median spend-per-1000-impressions with the median of the
    platform's *other* deliveries. A ratio near 100 or 1000 is a unit error and is corrected."""
    cpm: dict[str, list[tuple[DeliveryContext, float]]] = defaultdict(list)
    for c in active:
        values = [float(m.spend_usd) / m.impressions * 1000 for m in c.loaded if m.impressions > 0]
        if len(values) >= policy.SCALE_MIN_ROWS:
            cpm[c.platform].append((c, statistics.median(values)))

    for items in cpm.values():
        for ctx, own in items:                     # all medians were computed before any correction
            others = [v for o, v in items if o is not ctx]
            if len(others) < policy.SCALE_MIN_BASELINE_DELIVERIES:
                continue
            baseline = statistics.median(others)
            if baseline <= 0:
                continue
            ratio = own / baseline
            anomalous = not policy.SCALE_ANOMALY_LOW <= ratio <= policy.SCALE_ANOMALY_HIGH
            factor = next((f for f in policy.SCALE_FACTORS
                           if abs(ratio / f - 1) <= policy.SCALE_FACTOR_TOLERANCE), None) if anomalous else None
            finding = ScaleFinding(own, baseline, ratio, anomalous, factor)
            if factor:
                for m in ctx.loaded:
                    m.spend_usd = (m.spend_usd / Decimal(factor)).quantize(SIX_DP)
                    m.transforms.append(f"unit_scale: spend / {factor} "
                                        f"(delivery CPM was {ratio:.0f}x the platform baseline)")
                finding.corrected = True
            ctx.scale = finding


def _drop_duplicate_rows(active: list[DeliveryContext]) -> None:
    """One row per (platform, campaign, date). First occurrence in processing order wins."""
    seen: dict[tuple, tuple[str, int, tuple]] = {}
    for c in active:
        kept = []
        for m in c.loaded:
            key = (c.platform, m.campaign, m.date)
            values = (m.spend_usd, m.impressions, m.clicks)
            if key in seen:
                first_file, first_row, first_values = seen[key]
                same = values == first_values
                c.issues.append(RowIssue(
                    m.source_row, "duplicate_row" if same else "conflicting_duplicate", "error", None,
                    f"{'identical row' if same else 'different values for the same campaign/date'} "
                    f"already loaded from {first_file} row {first_row}",
                    {"campaign": m.campaign, "date": m.date.isoformat(), "spend_usd": str(m.spend_usd),
                     "impressions": m.impressions, "clicks": m.clicks}))
                continue
            seen[key] = (c.filename, m.source_row, values)
            kept.append(m)
        c.loaded = kept


def _record_corrections(active: list[DeliveryContext]) -> None:
    for c in active:
        by_row = {m.source_row: m for m in c.loaded}
        for issue in c.issues:
            if issue.severity == "correction" and issue.row in by_row:
                by_row[issue.row].transforms.append(f"{issue.code}: {issue.message}")


def _missing_deliveries(files, vocabulary) -> list[DeliveryContext]:
    """Expect one delivery per platform per week, from the first to the last week seen."""
    if not files:
        return []
    have = {(f.platform, f.week_start) for f in files}
    week, last = min(f.week_start for f in files), max(f.week_start for f in files)
    missing = []
    while week <= last:
        for platform in config.PLATFORMS:
            if (platform, week) not in have:
                missing.append(DeliveryContext(
                    filename=f"{platform}_{week.isoformat()} (missing)", platform=platform,
                    week_start=week, received=False, window=expected_window(week),
                    expected_campaigns=vocabulary.get(platform, frozenset())))
        week += timedelta(days=7)
    return missing
