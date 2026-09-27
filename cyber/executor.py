"""Bounded, authorization-gated verification executor.

The executor supports only a single ordinary GET against the exact authorized target.
It is intentionally not a generic HTTP client, shell, payload runner, crawler, or
exploit framework.
"""

from dataclasses import dataclass, asdict
from time import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


@dataclass
class VerificationResult:
    finding_id: str
    target: str
    action: str
    status: int | None
    headers: dict
    confirmed_signals: list[str]
    error: str | None = None
    timestamp: float = 0.0

    def as_dict(self):
        return asdict(self)


def execute_authorized_get(finding, authorization) -> dict:
    if not authorization.approved or not authorization.active():
        raise PermissionError("authorization is not active")
    if authorization.finding_id != finding.id:
        raise PermissionError("authorization/finding mismatch")
    if authorization.target != finding.target:
        raise PermissionError("authorization/target mismatch")
    if authorization.action != "controlled_non_destructive_poc":
        raise PermissionError("unsupported verification action")

    # Consume exactly once immediately before the network action.
    authorization.consume()
    request = Request(finding.target, headers={"User-Agent": "Jiraiya-Cyber/0.1 (authorized-verification)"}, method="GET")
    try:
        with urlopen(request, timeout=5) as response:
            headers = {k.lower(): v for k, v in response.headers.items()}
            result = VerificationResult(
                finding.id, finding.target, authorization.action, response.status,
                headers, _signals(finding, response.status, headers), timestamp=time()
            )
    except HTTPError as exc:
        headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
        result = VerificationResult(finding.id, finding.target, authorization.action, exc.code,
                                    headers, _signals(finding, exc.code, headers), timestamp=time())
    except (URLError, TimeoutError, OSError) as exc:
        result = VerificationResult(finding.id, finding.target, authorization.action, None, {}, [], str(exc), time())

    return result.as_dict()


def _signals(finding, status, headers):
    signals = []
    title = finding.title.lower()
    if "content-security-policy" in title and "content-security-policy" not in headers:
        signals.append("content-security-policy still absent")
    if "strict-transport-security" in title and "strict-transport-security" not in headers:
        signals.append("strict-transport-security still absent")
    if "x-content-type-options" in title and "x-content-type-options" not in headers:
        signals.append("x-content-type-options still absent")
    if "referrer-policy" in title and "referrer-policy" not in headers:
        signals.append("referrer-policy still absent")
    return signals
