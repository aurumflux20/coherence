"""CI session: prove-cmd, check, report."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coherence.ci.session import (
    SessionStore,
    build_report,
    check_exit_code,
    report_markdown,
)


class TestCISession(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.session = self.tmp / "session.json"
        self.store = SessionStore(self.session)

    def test_prove_true_and_check_pass(self):
        c, f, code = self.store.prove_command("true", claim="noop", next_action="chain complete")
        self.assertEqual(code, 0)
        self.assertTrue(f.done)
        self.assertTrue(self.session.exists())
        c2 = self.store.load()
        self.assertEqual(len(c2.done_facts()), 1)
        self.assertEqual(check_exit_code(c2, strict=True), 0)

    def test_prove_false_leaves_open(self):
        c, f, code = self.store.prove_command("false", claim="fail", next_action="fix")
        self.assertNotEqual(code, 0)
        self.assertFalse(f.done)
        self.assertEqual(check_exit_code(c, strict=True), 1)

    def test_strict_empty(self):
        c = self.store.load()
        self.assertEqual(check_exit_code(c, strict=True), 2)
        self.assertEqual(check_exit_code(c, strict=False), 0)

    def test_report_markdown_and_json(self):
        self.store.prove_command("true", claim="ok", next_action="chain complete")
        c = self.store.load()
        md = report_markdown(c)
        self.assertIn("Coherence report", md)
        self.assertIn("shields.io", md)
        r = build_report(c)
        self.assertTrue(r["ok"])
        self.assertIn("proven", r["badge_message"])
        json.dumps(r)  # serializable


if __name__ == "__main__":
    unittest.main()
