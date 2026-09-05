"""Evidence checklist: consequential claims must carry proof."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coherence.checklist import PROFILES, checklist, format_checklist
from coherence.ci.session import SessionStore


class TestChecklist(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.store = SessionStore(self.tmp / "session.json")

    def test_no_consequential_claims_is_ok_and_says_so(self):
        self.store.prove_command("true", claim="unit tests", next_action="chain complete")
        r = checklist(self.store.load())
        self.assertTrue(r["ok"])
        self.assertEqual(r["matched"], 0)
        self.assertIn("no open consequential", r["next"])

    def test_open_money_claim_blocks(self):
        c = self.store.load()
        c.said("stripe refund completed", "attach the refund id")
        self.store.save(c)
        r = checklist(self.store.load())
        self.assertFalse(r["ok"])
        self.assertEqual(r["profiles"]["money"]["open"], 1)
        self.assertEqual(r["gaps"][0]["profile"], "money")
        self.assertIn("BLOCK", format_checklist(r))

    def test_proven_money_claim_is_ok(self):
        self.store.prove_command("true", claim="stripe webhook tests", next_action="chain complete")
        r = checklist(self.store.load())
        self.assertEqual(r["profiles"]["money"]["matched"], 1)
        self.assertEqual(r["profiles"]["money"]["open"], 0)
        self.assertTrue(r["ok"])

    def test_deploy_profile_catches_an_unproven_deploy(self):
        c = self.store.load()
        c.said("deployed to production", "attach the deploy log")
        self.store.save(c)
        r = checklist(self.store.load())
        self.assertFalse(r["ok"])
        self.assertEqual(r["profiles"]["deploy"]["open"], 1)
        self.assertEqual(r["profiles"]["money"]["open"], 0)

    def test_profile_selection_filters(self):
        c = self.store.load()
        c.said("deployed to production", "attach the deploy log")
        self.store.save(c)
        r = checklist(self.store.load(), profiles=("money",))
        self.assertTrue(r["ok"])  # deploy not selected, so not graded
        self.assertNotIn("deploy", r["profiles"])

    def test_unknown_profile_is_reported_not_fatal(self):
        r = checklist(self.store.load(), profiles=("money", "nope"))
        self.assertEqual(r["unknown_profiles"], ["nope"])
        self.assertTrue(r["ok"])

    def test_all_profiles_exist(self):
        for name in ("money", "deploy", "data", "security"):
            self.assertIn(name, PROFILES)
