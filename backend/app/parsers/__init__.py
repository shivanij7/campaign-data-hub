"""Registry of platform parsers. Adding a platform = one module + one line here."""
from __future__ import annotations

from ..models import ParsedFile
from . import google, linkedin, meta
from .common import FatalFileError

PARSERS = {
    "meta_ads": meta.parse,
    "google_ads": google.parse,
    "linkedin_ads": linkedin.parse,
}


def parse_file(platform: str, path, rates) -> ParsedFile:
    """Never raises (NFR-2): an unreadable file becomes ParsedFile(fatal=...)."""
    try:
        return PARSERS[platform](path, rates)
    except FatalFileError as exc:
        return ParsedFile(fatal=str(exc))
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all at the isolation boundary
        return ParsedFile(fatal=f"{type(exc).__name__}: {exc}")
