"""The check interface. To add a check: subclass Check, implement run(), add it to CHECKS."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..models import DeliveryContext

STATUS_RANK = {"pass": 0, "warn": 1, "fail": 2}


@dataclass
class CheckResult:
    name: str
    level: str          # "row" | "file" | "delivery"
    status: str         # "pass" | "warn" | "fail"
    summary: str        # one human-readable line
    details: dict = field(default_factory=dict)    # JSON-serializable evidence


class Check(ABC):
    name: str
    level: str

    def applies(self, ctx: DeliveryContext) -> bool:
        """Checks that make no sense for a delivery (e.g. row checks on a missing file) are skipped."""
        return ctx.usable

    @abstractmethod
    def run(self, ctx: DeliveryContext) -> CheckResult: ...

    def result(self, status: str, summary: str, **details) -> CheckResult:
        return CheckResult(self.name, self.level, status, summary, details)
