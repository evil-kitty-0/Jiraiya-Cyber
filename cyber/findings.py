"""Structured security findings and lifecycle state."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from time import time
from uuid import uuid4


class FindingStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    REPORTED = "REPORTED"


@dataclass
class Finding:
    title: str
    vulnerability_type: str
    target: str
    endpoint: str
    confidence: float
    description: str = ""
    evidence: list[dict] = field(default_factory=list)
    id: str = field(default_factory=lambda: f"F-{uuid4().hex[:10]}")
    status: FindingStatus = FindingStatus.DISCOVERED
    verification_requested: bool = False
    created_at: float = field(default_factory=time)

    def request_verification(self) -> None:
        if self.status not in {FindingStatus.DISCOVERED, FindingStatus.NEEDS_VERIFICATION}:
            raise ValueError(f"cannot request verification from {self.status}")
        self.status = FindingStatus.NEEDS_VERIFICATION
        self.verification_requested = True

    def mark_verified(self, evidence: dict | None = None) -> None:
        if self.status != FindingStatus.NEEDS_VERIFICATION:
            raise ValueError("finding must be awaiting verification")
        if evidence:
            self.evidence.append(evidence)
        self.status = FindingStatus.VERIFIED

    def reject(self, reason: str = "") -> None:
        self.status = FindingStatus.REJECTED
        if reason:
            self.evidence.append({"type": "rejection", "reason": reason})

    def mark_reported(self) -> None:
        if self.status != FindingStatus.VERIFIED:
            raise ValueError("only verified findings can be reported")
        self.status = FindingStatus.REPORTED

    def as_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data
