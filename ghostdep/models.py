"""Data models for ghostdep."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any


class Ecosystem(str, Enum):
    PYTHON = "python"
    NPM = "npm"
    CARGO = "cargo"
    GO = "go"
    UNKNOWN = "unknown"


class Status(str, Enum):
    VERIFIED = "verified"          # Confirmed on public registry and mature
    PHANTOM = "phantom"            # 404 on registry - hallucination risk!
    SUSPICIOUS = "suspicious"      # Exists, but has squatting / zero-maintenance traits
    NEWBORN = "newborn"            # Registered within last 30 days
    STDLIB = "stdlib"              # Language standard library / built-in
    LOCAL = "local"                # Relative import or workspace package
    SKIPPED = "skipped"            # Skipped due to offline mode or filter
    ERROR = "error"                # Network timeout or registry unreachable


@dataclass
class Dependency:
    name: str
    ecosystem: str
    source_file: str
    line_number: Optional[int] = None
    version_spec: Optional[str] = None
    source_type: str = "import"      # "import", "manifest", or "diff_add"
    status: Status = Status.VERIFIED
    details: str = ""
    registry_url: Optional[str] = None
    published_date: Optional[str] = None
    age_days: Optional[int] = None
    latest_version: Optional[str] = None
    similar_to: Optional[str] = None # Typosquatting / slopsquatting flag
    risk_score: int = 0             # 0 (safe) to 100 (critical)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class ScanReport:
    target: str
    dependencies: List[Dependency] = field(default_factory=list)
    total_scanned: int = 0
    phantom_count: int = 0
    suspicious_count: int = 0
    newborn_count: int = 0
    verified_count: int = 0
    stdlib_count: int = 0
    local_count: int = 0
    error_count: int = 0
    scan_duration_ms: float = 0.0

    def compute_metrics(self) -> None:
        self.total_scanned = len(self.dependencies)
        self.phantom_count = sum(1 for d in self.dependencies if d.status == Status.PHANTOM)
        self.suspicious_count = sum(1 for d in self.dependencies if d.status == Status.SUSPICIOUS)
        self.newborn_count = sum(1 for d in self.dependencies if d.status == Status.NEWBORN)
        self.verified_count = sum(1 for d in self.dependencies if d.status == Status.VERIFIED)
        self.stdlib_count = sum(1 for d in self.dependencies if d.status == Status.STDLIB)
        self.local_count = sum(1 for d in self.dependencies if d.status == Status.LOCAL)
        self.error_count = sum(1 for d in self.dependencies if d.status == Status.ERROR)

    def has_issues(self, fail_on: str = "phantom") -> bool:
        """Check if report violates pass criteria based on fail_on strategy."""
        fail_on = fail_on.lower()
        if fail_on == "phantom":
            return self.phantom_count > 0
        elif fail_on == "suspicious":
            return (self.phantom_count + self.suspicious_count) > 0
        elif fail_on == "newborn":
            return (self.phantom_count + self.suspicious_count + self.newborn_count) > 0
        elif fail_on == "any":
            return (self.phantom_count + self.suspicious_count + self.newborn_count + self.error_count) > 0
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "total_scanned": self.total_scanned,
            "metrics": {
                "phantom": self.phantom_count,
                "suspicious": self.suspicious_count,
                "newborn": self.newborn_count,
                "verified": self.verified_count,
                "stdlib": self.stdlib_count,
                "local": self.local_count,
                "errors": self.error_count,
            },
            "scan_duration_ms": round(self.scan_duration_ms, 2),
            "dependencies": [d.to_dict() for d in self.dependencies],
        }
