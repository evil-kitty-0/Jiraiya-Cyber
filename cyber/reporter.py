"""Bug-bounty style report generation from structured findings."""

from .evidence import redact


def build_report(finding, impact: str = "", remediation: str = "") -> dict:
    return {
        "title": redact(finding.title),
        "severity": "UNSET",
        "affected_asset": redact(finding.target),
        "endpoint": redact(finding.endpoint),
        "vulnerability_type": redact(finding.vulnerability_type),
        "summary": redact(finding.description),
        "steps_to_reproduce": ["Use only the authorized verification procedure recorded for this finding."],
        "evidence": finding.evidence,
        "impact": redact(impact),
        "remediation": redact(remediation),
        "finding_id": finding.id,
    }
