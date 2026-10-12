"""All SQL that writes a delivery. One delivery = one transaction."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .db import transaction
from .models import DeliveryContext
from .quality.base import CheckResult


def replace_delivery(conn, ctx: DeliveryContext, results: list[CheckResult], health: str) -> int:
    """Delete any previous copy of this delivery (cascades) and write the new one atomically."""
    errors = [i for i in ctx.issues if i.severity == "error"]
    quarantined_rows = len({i.row for i in errors})
    with transaction(conn):
        conn.execute("DELETE FROM deliveries WHERE filename = ?", (ctx.filename,))
        cur = conn.execute(
            "INSERT INTO deliveries (platform, week_start, filename, received, content_hash, rows_read,"
            " rows_loaded, rows_quarantined, health, ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (ctx.platform, ctx.week_start.isoformat() if ctx.week_start else "unknown", ctx.filename,
             int(ctx.received), ctx.content_hash, ctx.rows_read, len(ctx.loaded), quarantined_rows, health,
             datetime.now(timezone.utc).isoformat(timespec="seconds")))
        did = cur.lastrowid
        conn.executemany(
            "INSERT INTO metrics (delivery_id, source_row, platform, campaign, date, spend_usd,"
            " impressions, clicks, transforms) VALUES (?,?,?,?,?,?,?,?,?)",
            [(did, m.source_row, ctx.platform, m.campaign, m.date.isoformat(), float(m.spend_usd),
              m.impressions, m.clicks, json.dumps(m.transforms)) for m in ctx.loaded])
        conn.executemany(
            "INSERT INTO quarantined_rows (delivery_id, source_row, code, field, message, raw)"
            " VALUES (?,?,?,?,?,?)",
            [(did, i.row, i.code, i.field, i.message, json.dumps(i.raw, default=str)) for i in errors])
        conn.executemany(
            "INSERT INTO quality_checks (delivery_id, check_name, level, status, summary, details)"
            " VALUES (?,?,?,?,?,?)",
            [(did, r.name, r.level, r.status, r.summary, json.dumps(r.details)) for r in results])
    return did
