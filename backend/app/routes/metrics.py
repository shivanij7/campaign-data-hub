"""FR-4: normalized metrics, totals and derived metrics."""
from __future__ import annotations

import json
from collections import Counter
from enum import Enum

from fastapi import APIRouter, Depends, Query

from ..deps import Filters, get_conn, get_filters
from ..schemas import MetricPage, SummaryOut

router = APIRouter(prefix="/metrics", tags=["metrics"])


def derive(spend, impressions, clicks) -> dict:
    """The single definition of the derived metrics. Division by zero -> null, never 0 or an error."""
    spend, impressions, clicks = spend or 0.0, impressions or 0, clicks or 0
    return {"spend_usd": round(spend, 4), "impressions": impressions, "clicks": clicks,
            "ctr": round(clicks / impressions, 6) if impressions else None,
            "cpc": round(spend / clicks, 4) if clicks else None}


@router.get("", response_model=MetricPage, summary="List normalized daily metrics")
def list_metrics(f: Filters = Depends(get_filters), limit: int = Query(100, ge=1, le=1000),
                 offset: int = Query(0, ge=0), conn=Depends(get_conn)):
    where, params = f.sql()
    total = conn.execute(f"SELECT COUNT(*) FROM metrics m{where}", params).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM metrics m{where} ORDER BY m.date, m.platform, m.campaign LIMIT ? OFFSET ?",
                        params + [limit, offset]).fetchall()
    items = [{**derive(r["spend_usd"], r["impressions"], r["clicks"]), "id": r["id"],
              "delivery_id": r["delivery_id"], "source_row": r["source_row"], "platform": r["platform"],
              "campaign": r["campaign"], "date": r["date"], "transforms": json.loads(r["transforms"])}
             for r in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


class GroupBy(str, Enum):
    campaign = "campaign"
    platform = "platform"


class SortBy(str, Enum):
    spend_usd = "spend_usd"
    impressions = "impressions"
    clicks = "clicks"
    ctr = "ctr"
    cpc = "cpc"
    campaign = "campaign"
    platform = "platform"


class Order(str, Enum):
    asc = "asc"
    desc = "desc"


@router.get("/summary", response_model=SummaryOut,
            summary="Totals + CTR/CPC, grouped by campaign or platform, with lineage")
def summary(f: Filters = Depends(get_filters), group_by: GroupBy = GroupBy.campaign,
            sort_by: SortBy = SortBy.spend_usd, order: Order = Order.desc, conn=Depends(get_conn)):
    where, params = f.sql()
    keys = "m.platform, m.campaign" if group_by == GroupBy.campaign else "m.platform"
    agg = "SUM(m.spend_usd) s, SUM(m.impressions) i, SUM(m.clicks) c, COUNT(*) n"

    groups = [{**derive(r["s"], r["i"], r["c"]), "platform": r["platform"],
               "campaign": r["campaign"] if group_by == GroupBy.campaign else None, "rows": r["n"]}
              for r in conn.execute(f"SELECT {keys}, {agg} FROM metrics m{where} GROUP BY {keys}", params)]

    # sort in Python: ctr/cpc are derived, and nulls always go last whatever the direction
    present = [g for g in groups if g[sort_by.value] is not None]
    absent = [g for g in groups if g[sort_by.value] is None]
    present.sort(key=lambda g: g[sort_by.value].lower() if isinstance(g[sort_by.value], str) else g[sort_by.value],
                 reverse=order == Order.desc)

    t = conn.execute(f"SELECT {agg} FROM metrics m{where}", params).fetchone()

    deliveries = [dict(r) for r in conn.execute(
        f"SELECT d.id delivery_id, d.filename, d.health, COUNT(*) rows FROM metrics m "
        f"JOIN deliveries d ON d.id = m.delivery_id{where} GROUP BY d.id ORDER BY d.week_start, d.platform", params)]
    # transforms are stored as e.g. "unit_scale: spend / 100 (...)"; the rule name is the part before ':'
    rules: Counter = Counter()
    for r in conn.execute(f"SELECT m.transforms FROM metrics m{where}", params):
        for transform in json.loads(r["transforms"]):
            rules[transform.split(":")[0]] += 1

    return {"group_by": group_by.value, "filters": f.echo(), "totals": derive(t["s"], t["i"], t["c"]),
            "groups": present + absent, "lineage": {"deliveries": deliveries, "transforms": dict(rules)}}
