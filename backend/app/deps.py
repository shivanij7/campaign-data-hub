"""Request-scoped dependencies: DB connection and the filters shared by metric endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from fastapi import Request

from . import db
from .errors import ApiError


class Platform(str, Enum):
    meta_ads = "meta_ads"
    google_ads = "google_ads"
    linkedin_ads = "linkedin_ads"


def get_conn(request: Request):
    conn = db.connect(request.app.state.db_path, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


@dataclass
class Filters:
    platform: Platform | None = None
    date_from: date | None = None
    date_to: date | None = None
    campaign: str | None = None

    def sql(self) -> tuple[str, list]:
        """WHERE clause (on table alias m) + params. Shared so list and summary can never disagree."""
        clauses, params = [], []
        if self.platform:
            clauses.append("m.platform = ?"); params.append(self.platform.value)
        if self.date_from:
            clauses.append("m.date >= ?"); params.append(self.date_from.isoformat())
        if self.date_to:
            clauses.append("m.date <= ?"); params.append(self.date_to.isoformat())
        if self.campaign:
            clauses.append("m.campaign = ?"); params.append(self.campaign)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def echo(self) -> dict:
        return {"platform": self.platform.value if self.platform else None,
                "date_from": self.date_from.isoformat() if self.date_from else None,
                "date_to": self.date_to.isoformat() if self.date_to else None,
                "campaign": self.campaign}


def get_filters(platform: Platform | None = None, date_from: date | None = None,
                date_to: date | None = None, campaign: str | None = None) -> Filters:
    if date_from and date_to and date_from > date_to:
        raise ApiError(422, "invalid_date_range", "date_from must not be after date_to",
                       [{"field": "date_from", "message": f"{date_from} is after date_to {date_to}"}])
    return Filters(platform, date_from, date_to, campaign)
