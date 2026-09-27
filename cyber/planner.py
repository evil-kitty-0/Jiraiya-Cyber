"""Planner for the authorization-first security workflow.

The planner creates tasks only; it does not execute network attacks or shell commands.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityTask:
    phase: str
    objective: str
    requires_authorization: bool = False


def plan_assessment(target: str) -> list[SecurityTask]:
    if not target.strip():
        raise ValueError("target is required")
    return [
        SecurityTask("recon", f"Map the explicitly authorized attack surface for {target}"),
        SecurityTask("analysis", "Identify candidate security weaknesses from collected evidence"),
        SecurityTask("verification", "Validate candidate findings using non-destructive checks"),
        SecurityTask("authorization", "Request explicit approval before any controlled PoC", True),
        SecurityTask("reporting", "Prepare evidence-backed vulnerability reports"),
    ]
