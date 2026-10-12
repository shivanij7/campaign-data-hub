"""FR-5: data health."""
from __future__ import annotations

import json
from enum import Enum

from fastapi import APIRouter, Depends

from ..deps import Platform, get_conn
from ..errors import ApiError
from ..schemas import DeliveryDetail, DeliveryOut

router = APIRouter(prefix="/deliveries", tags=["data health"])


class Health(str, Enum):
    passed = "pass"
    warn = "warn"
    fail = "fail"


def _delivery(row, counts: dict, problems: list) -> dict:
    return {"id": row["id"], "platform": row["platform"], "week_start": row["week_start"],
            "filename": row["filename"], "received": bool(row["received"]), "health": row["health"],
            "rows_read": row["rows_read"], "rows_loaded": row["rows_loaded"],
            "rows_quarantined": row["rows_quarantined"], "ingested_at": row["ingested_at"],
            "check_counts": {s: counts.get(s, 0) for s in ("pass", "warn", "fail")}, "problems": problems}


@router.get("", response_model=list[DeliveryOut], summary="All deliveries with their health")
def list_deliveries(health: Health | None = None, platform: Platform | None = None, conn=Depends(get_conn)):
    counts: dict[int, dict] = {}
    problems: dict[int, list] = {}
    for c in conn.execute("SELECT delivery_id, check_name, status, summary FROM quality_checks ORDER BY id"):
        counts.setdefault(c["delivery_id"], {}).setdefault(c["status"], 0)
        counts[c["delivery_id"]][c["status"]] += 1
        if c["status"] != "pass":
            problems.setdefault(c["delivery_id"], []).append(
                {"check": c["check_name"], "status": c["status"], "summary": c["summary"]})

    clauses, params = [], []
    if health:
        clauses.append("health = ?"); params.append(health.value)
    if platform:
        clauses.append("platform = ?"); params.append(platform.value)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(f"SELECT * FROM deliveries{where} ORDER BY week_start, platform, filename", params)
    return [_delivery(r, counts.get(r["id"], {}), problems.get(r["id"], [])) for r in rows]


@router.get("/{delivery_id}", response_model=DeliveryDetail, summary="Full quality report for one delivery")
def get_delivery(delivery_id: int, conn=Depends(get_conn)):
    row = conn.execute("SELECT * FROM deliveries WHERE id = ?", (delivery_id,)).fetchone()
    if row is None:
        raise ApiError(404, "delivery_not_found", f"no delivery with id {delivery_id}")
    checks = [{"name": c["check_name"], "level": c["level"], "status": c["status"], "summary": c["summary"],
               "details": json.loads(c["details"])}
              for c in conn.execute("SELECT * FROM quality_checks WHERE delivery_id = ? ORDER BY id", (delivery_id,))]
    quarantined = [{"source_row": q["source_row"], "code": q["code"], "field": q["field"], "message": q["message"],
                    "raw": json.loads(q["raw"]) if q["raw"] else None}
                   for q in conn.execute("SELECT * FROM quarantined_rows WHERE delivery_id = ? "
                                         "ORDER BY source_row, id", (delivery_id,))]
    counts: dict = {}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    problems = [{"check": c["name"], "status": c["status"], "summary": c["summary"]}
                for c in checks if c["status"] != "pass"]
    return {**_delivery(row, counts, problems), "content_hash": row["content_hash"],
            "checks": checks, "quarantined_rows": quarantined}
