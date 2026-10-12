"""Orchestration: analyse the folder, run checks, persist. Safe to run any number of times."""
from __future__ import annotations

from . import store
from .analysis import analyse
from .db import transaction
from .quality import health_from, run_checks


class DeliveryNotFound(Exception):
    pass


def ingest(conn, directory=None, only: str | None = None) -> dict:
    """Full run (only=None): rebuild everything from the folder -- same input, same result.
    Single run (only=<filename>): replace just that delivery.

    A delivery that fails to write is reported in `errors`; the others still load (NFR-2).
    """
    contexts = analyse(directory)             # pure; if this raises nothing has been modified yet
    if only is not None and only not in {c.filename for c in contexts}:
        raise DeliveryNotFound(only)

    if only is None:
        with transaction(conn):
            conn.execute("DELETE FROM deliveries")        # cascades to metrics, checks, quarantine

    loaded, errors = [], []
    for ctx in contexts:
        if only is not None and ctx.filename != only:
            continue
        try:
            results = run_checks(ctx)
            health = health_from(results)
            store.replace_delivery(conn, ctx, results, health)
            loaded.append({"filename": ctx.filename, "platform": ctx.platform, "health": health,
                           "rows_read": ctx.rows_read, "rows_loaded": len(ctx.loaded)})
        except Exception as exc:  # noqa: BLE001 - isolation boundary
            errors.append({"filename": ctx.filename, "error": f"{type(exc).__name__}: {exc}"})
    return {"deliveries": loaded, "errors": errors}
