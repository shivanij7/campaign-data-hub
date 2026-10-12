"""FR-6: trigger ingestion."""
from __future__ import annotations

import threading
from collections import Counter

from fastapi import APIRouter, Depends

from .. import pipeline
from ..deps import get_conn
from ..errors import ApiError
from ..schemas import IngestRequest, IngestResult

router = APIRouter(prefix="/ingestions", tags=["ingestion"])
_running = threading.Lock()          # one ingestion at a time (a full run rebuilds the tables)


@router.post("", response_model=IngestResult, summary="Run ingestion (full, or re-ingest one delivery)")
def create_ingestion(body: IngestRequest | None = None, conn=Depends(get_conn)):
    filename = body.filename if body else None
    if not _running.acquire(blocking=False):
        raise ApiError(409, "ingestion_in_progress", "another ingestion is already running; retry shortly")
    try:
        result = pipeline.ingest(conn, only=filename)
    except pipeline.DeliveryNotFound:
        raise ApiError(404, "delivery_not_found", f"no delivery named {filename!r} in the deliveries folder")
    except OSError as exc:
        raise ApiError(500, "deliveries_unavailable", f"cannot read deliveries folder: {exc}")
    finally:
        _running.release()
    return {"mode": "single" if filename else "full", **result,
            "health_counts": dict(Counter(d["health"] for d in result["deliveries"]))}
