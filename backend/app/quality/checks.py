"""Concrete quality checks, grouped by the level they operate on."""
from __future__ import annotations

from collections import Counter
from datetime import timedelta

from ..models import DeliveryContext
from . import policy
from .base import Check, CheckResult


# =============================== delivery level ======================================

class DeliveryReceived(Check):
    """Cadence: every platform must deliver once per week."""
    name, level = "delivery_received", "delivery"

    def applies(self, ctx): return ctx.recognized

    def run(self, ctx):
        if ctx.received:
            return self.result("pass", "delivery received")
        return self.result("fail", f"no {ctx.platform} delivery received for week starting {ctx.week_start}",
                           platform=ctx.platform, week_start=str(ctx.week_start))


class DuplicateDelivery(Check):
    """Same bytes delivered twice (e.g. a '_resend'). Only the first copy is loaded."""
    name, level = "duplicate_delivery", "delivery"

    def applies(self, ctx): return ctx.received and ctx.recognized

    def run(self, ctx):
        if ctx.duplicate_of:
            return self.result("fail", f"byte-identical to {ctx.duplicate_of}; not loaded to avoid double counting",
                               duplicate_of=ctx.duplicate_of, content_hash=ctx.content_hash)
        return self.result("pass", "content is unique among deliveries", content_hash=ctx.content_hash)


# ================================= file level ========================================

class FilenameRecognised(Check):
    name, level = "filename_recognized", "file"

    def applies(self, ctx): return ctx.received

    def run(self, ctx):
        if ctx.recognized:
            return self.result("pass", "filename follows <platform>_<week-start>[_resend].<ext>")
        return self.result("fail", "filename does not match any known platform/week pattern; file ignored",
                           filename=ctx.filename)


class FileReadable(Check):
    name, level = "file_readable", "file"

    def applies(self, ctx): return ctx.received and ctx.recognized and ctx.duplicate_of is None

    def run(self, ctx):
        if ctx.fatal:
            return self.result("fail", f"file could not be parsed: {ctx.fatal}", error=ctx.fatal)
        return self.result("pass", f"parsed {ctx.rows_read} rows", rows_read=ctx.rows_read)


class Coverage(Check):
    """Volume: did every (campaign, day) we expect actually arrive with valid data?"""
    name, level = "coverage", "file"

    def applies(self, ctx): return bool(ctx.usable and ctx.window and ctx.expected_campaigns)

    def run(self, ctx):
        start, end = ctx.window
        days = [start + timedelta(d) for d in range((end - start).days + 1)]
        expected = {(c, d) for c in ctx.expected_campaigns for d in days}
        present = {(m.campaign, m.date) for m in ctx.loaded}
        missing = sorted(expected - present)
        ratio = 1 - len(missing) / len(expected)
        status = "pass" if not missing else "warn" if ratio >= policy.COVERAGE_WARN_MIN else "fail"
        return self.result(
            status, f"{len(expected) - len(missing)} of {len(expected)} expected campaign-days present ({ratio:.0%})",
            expected_cells=len(expected), present_cells=len(expected) - len(missing), ratio=round(ratio, 4),
            window=[str(start), str(end)], campaigns=sorted(ctx.expected_campaigns),
            missing=[{"campaign": c, "date": d.isoformat()} for c, d in missing[:policy.MAX_EXAMPLES]])


class DateWindow(Check):
    """Rows dated outside the week the filename promises."""
    name, level = "date_window", "file"

    def applies(self, ctx): return bool(ctx.usable and ctx.window)

    def run(self, ctx):
        start, end = ctx.window
        outside = [m for m in ctx.loaded if not start <= m.date <= end]
        if not outside:
            return self.result("pass", f"all rows within {start}..{end}")
        fraction = len(outside) / len(ctx.loaded)
        status = "fail" if fraction > policy.DATE_WINDOW_FAIL_FRACTION else "warn"
        return self.result(status, f"{len(outside)} rows dated outside {start}..{end}",
                           window=[str(start), str(end)], count=len(outside),
                           examples=[{"row": m.source_row, "date": m.date.isoformat()}
                                     for m in outside[:policy.MAX_EXAMPLES]])


class UnitScale(Check):
    """Spend per 1,000 impressions compared with the platform's other deliveries."""
    name, level = "unit_scale", "file"

    def applies(self, ctx): return ctx.usable and ctx.scale is not None

    def run(self, ctx):
        s = ctx.scale
        evidence = dict(delivery_cpm=round(s.delivery_cpm, 4), baseline_cpm=round(s.baseline_cpm, 4),
                        ratio=round(s.ratio, 3), factor=s.factor, corrected=s.corrected)
        if not s.anomalous:
            return self.result("pass", f"spend scale consistent with platform baseline ({s.ratio:.2f}x)", **evidence)
        if s.corrected:
            return self.result("fail", f"spend is ~{s.factor}x the platform baseline ({s.ratio:.0f}x); "
                                       f"divided by {s.factor} during normalization", **evidence)
        return self.result("fail", f"spend is {s.ratio:.2f}x the platform baseline and no known unit error "
                                   f"explains it; values loaded unchanged", **evidence)


# ================================= row level =========================================

class RowIssueCheck(Check):
    """Reports row issues of the given codes. One configurable class covers several checks."""
    level = "row"

    def __init__(self, name: str, codes: set[str], what: str, fail_above: float | None = None):
        self.name, self.codes, self.what, self.fail_above = name, frozenset(codes), what, fail_above

    def run(self, ctx: DeliveryContext) -> CheckResult:
        hits = [i for i in ctx.issues if i.code in self.codes]
        rows = {i.row for i in hits}
        if not rows:
            return self.result("pass", f"no {self.what}", rows_read=ctx.rows_read)
        fraction = len(rows) / max(ctx.rows_read, 1)
        status = "fail" if self.fail_above is not None and fraction > self.fail_above else "warn"
        by_code = dict(Counter(i.code for i in hits))
        return self.result(
            status, f"{len(rows)} of {ctx.rows_read} rows with {self.what} ({fraction:.1%})",
            affected_rows=len(rows), rows_read=ctx.rows_read, fraction=round(fraction, 4), by_code=by_code,
            examples=[{"row": i.row, "code": i.code, "field": i.field, "message": i.message}
                      for i in hits[:policy.MAX_EXAMPLES]])
