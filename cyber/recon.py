"""Scoped, non-destructive HTTP reconnaissance.

This module intentionally limits itself to caller-supplied URLs inside the configured
scope. It performs ordinary HTTP GET requests, follows no redirects, sends no attack
payloads, and caps the number of requests per call.
"""

from dataclasses import dataclass, asdict
from time import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .scope import Scope


@dataclass
class ReconResult:
    url: str
    status: int | None
    headers: dict
    content_type: str
    server: str
    error: str | None = None
    timestamp: float = 0.0

    def as_dict(self):
        return asdict(self)


def run_recon(scope: Scope, urls: list[str], max_requests: int = 5) -> list[dict]:
    if max_requests < 1 or max_requests > 5:
        raise ValueError("max_requests must be between 1 and 5")
    if len(urls) > max_requests:
        raise ValueError(f"at most {max_requests} URLs may be checked per request")

    results = []
    for url in urls:
        scope.require(url)
        request = Request(url, headers={"User-Agent": "Jiraiya-Cyber/0.1 (authorized-recon)"}, method="GET")
        try:
            with urlopen(request, timeout=5) as response:
                headers = {k.lower(): v for k, v in response.headers.items()}
                results.append(ReconResult(
                    url=url,
                    status=response.status,
                    headers=headers,
                    content_type=headers.get("content-type", ""),
                    server=headers.get("server", ""),
                    timestamp=time(),
                ).as_dict())
        except HTTPError as exc:
            headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            results.append(ReconResult(url, exc.code, headers, headers.get("content-type", ""), headers.get("server", ""), timestamp=time()).as_dict())
        except (URLError, TimeoutError, OSError) as exc:
            results.append(ReconResult(url, None, {}, "", "", error=str(exc), timestamp=time()).as_dict())
    return results


def header_findings(result: dict) -> list[dict]:
    if result.get("status") is None:
        return []
    headers = {str(k).lower(): str(v) for k, v in result.get("headers", {}).items()}
    findings = []
    checks = [
        ("content-security-policy", "Missing Content-Security-Policy", "security_headers", "Consider a CSP appropriate for the application."),
        ("x-content-type-options", "Missing X-Content-Type-Options", "security_headers", "Consider sending X-Content-Type-Options: nosniff."),
        ("referrer-policy", "Missing Referrer-Policy", "security_headers", "Consider an explicit Referrer-Policy appropriate for the application."),
    ]
    if result.get("url", "").lower().startswith("https://"):
        checks.append(("strict-transport-security", "Missing Strict-Transport-Security", "security_headers", "Consider HSTS after confirming HTTPS is correctly deployed."))
    for header, title, kind, remediation in checks:
        if header not in headers:
            findings.append({"title": title, "vulnerability_type": kind, "target": result["url"], "endpoint": result["url"], "confidence": 0.9, "description": remediation})
    return findings
