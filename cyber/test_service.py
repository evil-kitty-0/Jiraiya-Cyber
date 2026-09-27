"""Tests for the Cyber runtime coordinator and explicit approval gate."""
import unittest
from unittest.mock import patch

from cyber.service import CyberService
from cyber.authorization import AuthorizationError


class CyberServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = CyberService()
        self.service.set_scope({
            "program": "demo",
            "allowed_hosts": ["example.com"],
            "allowed_paths": ["/app/*"],
        })
        self.finding = self.service.create_finding({
            "title": "Demo finding",
            "vulnerability_type": "demo",
            "target": "https://example.com/app/test",
            "endpoint": "https://example.com/app/test",
            "confidence": 0.9,
        })

    def test_request_does_not_approve(self):
        auth = self.service.request_authorization(self.finding["id"])
        self.assertFalse(auth["active"])
        with self.assertRaises(AuthorizationError):
            self.service.consume_authorization(auth["id"], self.finding["id"], "controlled_non_destructive_poc")

    def test_approval_then_consume(self):
        auth = self.service.request_authorization(self.finding["id"])
        approved = self.service.authorize(auth["id"])
        self.assertTrue(approved["active"])
        fake_result = {
            "finding_id": self.finding["id"],
            "target": "https://example.com/app/test",
            "action": "controlled_non_destructive_poc",
            "status": 200,
            "headers": {},
            "confirmed_signals": ["demo signal"],
            "error": None,
            "timestamp": 0.0,
        }
        with patch("cyber.service.execute_authorized_get", return_value=fake_result):
            consumed = self.service.consume_authorization(auth["id"], self.finding["id"], "controlled_non_destructive_poc")
        self.assertTrue(consumed["authorized"])
        self.assertEqual(consumed["finding"]["status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
