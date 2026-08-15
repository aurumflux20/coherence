"""Coherence stack — rungs share one bundle."""
from __future__ import annotations

import unittest

from coherence import Coherence, Truth


class TestCoherence(unittest.TestCase):
    def test_all_rungs_write_same_bundle(self):
        c = Coherence(title="t")
        c.skills.audit("s", ["read"])
        c.decisions.lock("d1", "MUST use HTTPS")
        c.claimproof.claim("x", "I did x")
        c.claimproof.cmd("tests", "pytest", 0)
        c.replay.check()
        c.review.triage()
        rungs = {r.rung for r in c.bundle.records}
        self.assertTrue({1, 2, 3, 4, 5}.issubset(rungs))
        self.assertEqual(c.bundle.title, "t")

    def test_claim_vs_prove(self):
        c = Coherence()
        a = c.claimproof.claim("t", "said")
        b = c.claimproof.cmd("t", "true", 0)
        self.assertEqual(a.truth, Truth.CLAIMED)
        self.assertEqual(b.truth, Truth.PROVEN)

    def test_high_skill_forces_review(self):
        c = Coherence()
        c.skills.audit("bad", ["shell", "secrets"])
        c.claimproof.cmd("tests", "pytest", 0)
        c.replay.check()
        t = c.review.triage()
        self.assertEqual(t.meta["priority"], "must_review")
        self.assertFalse(t.meta["auto_merge_ok"])

    def test_all_proven_low_risk(self):
        c = Coherence()
        c.skills.audit("ok", ["read"])
        c.claimproof.cmd("tests", "pytest", 0)
        c.replay.check()
        t = c.review.triage()
        self.assertEqual(t.meta["priority"], "low_risk")
        self.assertTrue(t.meta["auto_merge_ok"])

    def test_guard_blocks_fake_auto_merge(self):
        c = Coherence()
        c.claimproof.claim("tests", "passed in chat")
        # force a review record that wants auto merge without proven steps
        from coherence.core.types import Record, new_id

        c.bundle.add(
            Record(
                id=new_id("rev"),
                rung=5,
                kind="review",
                truth=Truth.CLAIMED,
                summary="fake",
                next_action="x",
                meta={"auto_merge_ok": True},
            )
        )
        bad = c.require_coherent()
        self.assertIsNotNone(bad)
        self.assertEqual(bad.truth, Truth.BLOCKED)


if __name__ == "__main__":
    unittest.main()
