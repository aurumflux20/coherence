"""AIO Phase 1 checklist — session Facts (CI path)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coherence.aio.checklist import aio_checklist, format_aio_checklist
from coherence.ci.session import SessionStore


class TestAioChecklist(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.session = self.tmp / "session.json"
        self.store = SessionStore(self.session)

    def test_ok_when_no_money_claims(self):
        self.store.prove_command("true", claim="unit tests", next_action="chain complete")
        c = self.store.load()
        r = aio_checklist(c)
        self.assertTrue(r["ok"])
        self.assertEqual(r["money_claims"], 0)
        self.assertEqual(r["phase"], 1)

    def test_flags_open_money_claim(self):
        c = self.store.load()
        c.said("stripe refund completed", "attach Stripe refund id evidence")
        self.store.save(c)
        c2 = self.store.load()
        r = aio_checklist(c2)
        self.assertGreaterEqual(r["money_claims"], 1)
        self.assertGreaterEqual(r["money_open"], 1)
        self.assertFalse(r["ok"])
        text = format_aio_checklist(r)
        self.assertIn("Phase 1", text)
        self.assertIn("NOT included", text)

    def test_proven_money_claim_ok(self):
        self.store.prove_command(
            "true",
            claim="stripe webhook tests",
            next_action="chain complete",
        )
        c = self.store.load()
        r = aio_checklist(c)
        self.assertGreaterEqual(r["money_claims"], 1)
        self.assertEqual(r["money_open"], 0)
        self.assertTrue(r["ok"])


if __name__ == "__main__":
    unittest.main()
