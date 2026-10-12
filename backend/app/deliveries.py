"""Finding delivery files and reading what their names promise."""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

FILENAME_RE = re.compile(
    r"^(?P<platform>meta_ads|google_ads|linkedin_ads)_(?P<week>\d{4}-\d{2}-\d{2})"
    r"(?P<resend>_resend)?\.(csv|json)$")


@dataclass(frozen=True)
class DeliveryFile:
    path: Path
    platform: str
    week_start: date
    is_resend: bool

    @property
    def filename(self) -> str:
        return self.path.name


def discover(directory: Path) -> tuple[list[DeliveryFile], list[str]]:
    """Returns (recognized files in processing order, names we could not interpret).

    Processing order is chronological, originals before resends, so the *first* copy
    of a duplicated delivery is the one that is loaded.
    """
    files: list[DeliveryFile] = []
    unrecognized: list[str] = []
    for path in sorted(Path(directory).iterdir()):
        if not path.is_file() or path.name.startswith("."):      # .DS_Store etc.
            continue
        m = FILENAME_RE.match(path.name)
        try:
            week = date.fromisoformat(m.group("week")) if m else None
        except ValueError:
            week = None
        if not m or week is None:
            unrecognized.append(path.name)
            continue
        files.append(DeliveryFile(path, m.group("platform"), week, bool(m.group("resend"))))
    files.sort(key=lambda f: (f.week_start, f.is_resend, f.platform))
    return files, unrecognized


def expected_window(week_start: date) -> tuple[date, date]:
    """A delivery covers 7 days from week_start, cut off at the end of that month.

    (The README says the 06-29 delivery covers two days: 06-29 and 06-30.)
    """
    month_end = date(week_start.year, week_start.month,
                     calendar.monthrange(week_start.year, week_start.month)[1])
    return week_start, min(week_start + timedelta(days=6), month_end)
