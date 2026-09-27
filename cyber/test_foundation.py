"""Basic tests for the authorization-first cyber foundation."""
import unittest

from cyber.authorization import AuthorizationError, AuthorizationManager
from cyber.findings import Finding, FindingStatus
from cyber.scope import Scope, ScopeError
from cyber.verifier import propose_verification


class CyberFoundationTests(unittest.TestCase):
    def setUp(self):
        self.scope = Scope(
            program="demo",
            allowed_hosts=("example.com",),
            excluded_paths=("/admin/*",),
        )

    def test_scope(self):
        self.scope.require("https://example.com/app")
        with self.assertRaises(ScopeError):
            self.scope.require("https://evil.example/app")
        with self.assertRaises(ScopeError):
            self.scope.require("https://example.com/admin/panel")

    def test_finding_lifecycle(self):
        finding = Finding("Test issue", "demo", "https://example.com", "/app", 0.8)
        finding.request_verification()
        self.assertEqual(finding.status, FindingStatus.NEEDS_VERIFICATION)
        finding.mark_verified({"signal": "expected"})
        self.assertEqual(finding.status, FindingStatus.VERIFIED)
        finding.mark_reported()
        self.assertEqual(finding.status, FindingStatus.REPORTED)

    def test_authorization_is_exact_and_one_time(self):
        finding = Finding("Test issue", "demo", "https://example.com", "/app", 0.8)
        manager = AuthorizationManager()
        auth = manager.request(finding.id, finding.target, "controlled_non_destructive_poc")
        manager.consume(auth.id, finding.id, finding.target, "controlled_non_destructive_poc")
        with self.assertRaises(AuthorizationError):
            manager.consume(auth.id, finding.id, finding.target, "controlled_non_destructive_poc")

    def test_verification_proposal_checks_scope(self):
        finding = Finding("Test issue", "demo", "https://example.com", "/app", 0.8)
        plan = propose_verification(finding, self.scope)
        self.assertTrue(plan.requires_explicit_authorization)


if __name__ == "__main__":
    unittest.main()
