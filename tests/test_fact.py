"""320 IQ atom — Fact law."""
from __future__ import annotations

import unittest

from coherence import Coherence
from coherence.core.fact import LAW, Fact, FactError


class TestFact(unittest.TestCase):
    def test_next_required(self):
        with self.assertRaises(FactError):
            Fact.make("x", next="")

    def test_said_not_done(self):
        f = Fact.said("tests passed", next="run pytest")
        self.assertFalse(f.done)
        self.assertTrue(f.finished_shape)

    def test_proven_is_done(self):
        f = Fact.proven("tests", "exit 0", next="merge or next domino")
        self.assertTrue(f.done)

    def test_proven_without_evidence_fails(self):
        with self.assertRaises(FactError):
            Fact.proven("x", "", next="y")

    def test_coherence_said_prove(self):
        c = Coherence()
        a = c.said("agent claimed green", next="prove with pytest")
        b = c.prove("pytest", "exit 0", next="chain complete")
        self.assertEqual(len(c.open_facts()), 1)
        self.assertEqual(len(c.done_facts()), 1)
        self.assertFalse(a.done)
        self.assertTrue(b.done)
        self.assertIn("evidence", c.LAW.lower())

    def test_memory_rejects_empty_proof(self):
        c = Coherence()
        with self.assertRaises(ValueError):
            c.evolve.learn(
                problem="p",
                lesson="l",
                proof="",
                next_domino="chain complete",
            )

    def test_law_constant(self):
        self.assertIn("evidence", LAW)
        self.assertIn("next", LAW)


if __name__ == "__main__":
    unittest.main()
