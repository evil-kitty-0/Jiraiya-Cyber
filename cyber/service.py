"""Runtime coordinator for the Jiraiya-Cyber foundation.

This service owns in-memory assessment state for the local Jiraiya API process. It
only creates findings/plans and authorization records; it never performs network
exploitation.
"""

from .authorization import AuthorizationError, AuthorizationManager
from .findings import Finding
from .scope import Scope, ScopeError
from .verifier import propose_verification
from .recon import run_recon, header_findings
from .reporter import build_report
from .executor import execute_authorized_get


class CyberService:
    def __init__(self):
        self.scope: Scope | None = None
        self.findings: dict[str, Finding] = {}
        self.authorization = AuthorizationManager()

    def set_scope(self, data: dict) -> dict:
        self.scope = Scope(
            program=str(data.get("program", "")).strip(),
            allowed_hosts=tuple(str(x).strip().lower() for x in data.get("allowed_hosts", []) if str(x).strip()),
            excluded_hosts=tuple(str(x).strip().lower() for x in data.get("excluded_hosts", []) if str(x).strip()),
            allowed_paths=tuple(data.get("allowed_paths", ["/*"])),
            excluded_paths=tuple(data.get("excluded_paths", [])),
            notes=str(data.get("notes", "")),
        )
        return self.scope.as_dict()

    def create_finding(self, data: dict) -> dict:
        if self.scope is None:
            raise ScopeError("configure an explicit cyber scope first")
        target = str(data.get("target", "")).strip()
        self.scope.require(target)
        finding = Finding(
            title=str(data.get("title", "Potential security finding")),
            vulnerability_type=str(data.get("vulnerability_type", "unknown")),
            target=target,
            endpoint=str(data.get("endpoint", target)),
            confidence=float(data.get("confidence", 0.0)),
            description=str(data.get("description", "")),
        )
        finding.request_verification()
        self.findings[finding.id] = finding
        return finding.as_dict()

    def verification_plan(self, finding_id: str) -> dict:
        finding = self._finding(finding_id)
        if self.scope is None:
            raise ScopeError("configure an explicit cyber scope first")
        return propose_verification(finding, self.scope).__dict__

    def request_authorization(self, finding_id: str, action: str = "controlled_non_destructive_poc",
                              max_attempts: int = 1, expires_in_seconds: int = 300) -> dict:
        finding = self._finding(finding_id)
        record = self.authorization.request(
            finding.id, finding.target, action, max_attempts, expires_in_seconds
        )
        return record.as_dict()

    def authorize(self, authorization_id: str) -> dict:
        return self.authorization.authorize(authorization_id).as_dict()

    def consume_authorization(self, authorization_id: str, finding_id: str, action: str) -> dict:
        finding = self._finding(finding_id)
        record = self.authorization.get_record(authorization_id)
        if record is None:
            raise AuthorizationError("authorization not found")
        if record.action != action:
            raise AuthorizationError("authorization action mismatch")
        if record.finding_id != finding.id:
            raise AuthorizationError("authorization finding mismatch")
        if record.target != finding.target:
            raise AuthorizationError("authorization target mismatch")
        if not record.active():
            raise AuthorizationError("authorization is not active")
        result = execute_authorized_get(finding, record)
        if result.get("confirmed_signals"):
            finding.mark_verified()
        finding.evidence.append({"type": "authorized_verification", "data": result})
        return {
            "authorized": True,
            "authorization": record.as_dict(),
            "result": result,
            "finding": finding.as_dict(),
        }

    def recon(self, urls: list[str], max_requests: int = 5) -> dict:
        if self.scope is None:
            raise ScopeError("configure an explicit cyber scope first")
        results = run_recon(self.scope, urls, max_requests)
        created = []
        for result in results:
            for candidate in header_findings(result):
                finding = Finding(**candidate)
                finding.request_verification()
                finding.evidence.append({"type": "recon", "data": result})
                self.findings[finding.id] = finding
                created.append(finding.as_dict())
        return {"results": results, "findings": created}

    def report(self, finding_id: str, impact: str = "", remediation: str = "") -> dict:
        finding = self._finding(finding_id)
        return build_report(finding, impact, remediation)

    def list_findings(self) -> list[dict]:
        return [finding.as_dict() for finding in self.findings.values()]

    def _finding(self, finding_id: str) -> Finding:
        finding = self.findings.get(finding_id)
        if finding is None:
            raise KeyError("finding not found")
        return finding


service = CyberService()
