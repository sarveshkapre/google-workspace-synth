from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanCounts:
    users_create: int = 0
    users_update: int = 0
    users_skip: int = 0
    users_conflict: int = 0
    groups_create: int = 0
    groups_update: int = 0
    groups_skip: int = 0
    groups_conflict: int = 0
    licenses_assign: int = 0
    drives_create: int = 0
    drives_skip: int = 0
    drives_conflict: int = 0
    folders_create: int = 0
    docs_create: int = 0
    docs_update: int = 0
    permissions_create: int = 0


@dataclass
class PlanReport:
    run_name: str
    counts: PlanCounts = field(default_factory=PlanCounts)
    warnings: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_name": self.run_name,
            "counts": self.counts.__dict__,
            "warnings": list(self.warnings),
            "conflicts": list(self.conflicts),
            "prerequisites": list(self.prerequisites),
        }


@dataclass
class ApplyReport:
    run_name: str
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_name": self.run_name,
            "created": list(self.created),
            "updated": list(self.updated),
            "skipped": list(self.skipped),
            "warnings": list(self.warnings),
            "conflicts": list(self.conflicts),
        }
