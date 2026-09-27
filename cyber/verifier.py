"""Non-destructive verification proposal layer.

Actual active testing must be implemented behind the authorization gate. The first
version returns a verification plan instead of touching a target.
"""

from dataclasses import dataclass

from .scope import Scope


@dataclass(frozen=True)
class VerificationPlan:
    finding_id: str
    target: str
    action: str
    expected_signal: str
    requires_explicit_authorization: bool = True


def propose_verification(finding, scope: Scope) -> VerificationPlan:
    scope.require(finding.target)
    return VerificationPlan(
        finding_id=finding.id,
        target=finding.target,
        action="controlled_non_destructive_poc",
        expected_signal="A reproducible response/evidence pattern confirming the suspected issue",
    )
