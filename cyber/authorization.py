"""One-time, bounded authorization for controlled PoC execution.

Authorization is explicit and scoped to one finding/target/action. This module does
not execute a PoC; it only issues and consumes authorization records.
"""

from dataclasses import dataclass, asdict, field
from time import time
from uuid import uuid4


class AuthorizationError(ValueError):
    pass


@dataclass
class Authorization:
    finding_id: str
    target: str
    action: str
    max_attempts: int = 1
    expires_in_seconds: int = 300
    id: str = field(default_factory=lambda: f"AUTH-{uuid4().hex[:10]}")
    created_at: float = field(default_factory=time)
    attempts: int = 0
    used: bool = False
    approved: bool = False

    def active(self) -> bool:
        return (self.approved and not self.used and self.attempts < self.max_attempts and
                time() < self.created_at + self.expires_in_seconds)

    def consume(self) -> None:
        if not self.active():
            raise AuthorizationError("authorization is expired, exhausted, or already used")
        self.attempts += 1
        self.used = True

    def as_dict(self) -> dict:
        data = asdict(self)
        data["active"] = self.active()
        return data


class AuthorizationManager:
    def __init__(self):
        self._records: dict[str, Authorization] = {}

    def request(self, finding_id: str, target: str, action: str,
                max_attempts: int = 1, expires_in_seconds: int = 300) -> Authorization:
        if max_attempts < 1 or max_attempts > 3:
            raise AuthorizationError("max_attempts must be between 1 and 3")
        if expires_in_seconds < 30 or expires_in_seconds > 3600:
            raise AuthorizationError("expires_in_seconds must be between 30 and 3600")
        record = Authorization(finding_id, target, action, max_attempts, expires_in_seconds)
        self._records[record.id] = record
        return record

    def authorize(self, authorization_id: str) -> Authorization:
        record = self._records.get(authorization_id)
        if record is None:
            raise AuthorizationError("authorization record not found")
        if record.used:
            raise AuthorizationError("authorization has already been consumed")
        if time() >= record.created_at + record.expires_in_seconds:
            raise AuthorizationError("authorization has expired")
        record.approved = True
        return record

    def consume(self, authorization_id: str, finding_id: str, target: str, action: str) -> Authorization:
        record = self.authorize(authorization_id)
        if record.finding_id != finding_id or record.target != target or record.action != action:
            raise AuthorizationError("authorization does not match the requested operation")
        record.consume()
        return record

    def get(self, authorization_id: str) -> dict | None:
        record = self._records.get(authorization_id)
        return record.as_dict() if record else None
