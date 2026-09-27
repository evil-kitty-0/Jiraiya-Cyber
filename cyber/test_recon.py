"""Tests for safe reconnaissance analysis without network access."""
import unittest

from cyber.recon import header_findings
from cyber.scope import Scope, ScopeError


class ReconTests(unittest.TestCase):
    def test_missing_security_headers_are_reported(self):
        result = {
            "url": "https://example.com/app",
            "status": 200,
            "headers": {"content-type": "text/html"},
        }
        findings = header_findings(result)
        titles = {x["title"] for x in findings}
        self.assertIn("Missing Content-Security-Policy", titles)
        self.assertIn("Missing Strict-Transport-Security", titles)

    def test_scope_blocks_out_of_scope_recon(self):
        scope = Scope(program="demo", allowed_hosts=("example.com",))
        with self.assertRaises(ScopeError):
            scope.require("https://not-example.com/")


if __name__ == "__main__":
    unittest.main()
