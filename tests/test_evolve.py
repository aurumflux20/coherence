"""Dominos + evolution memory."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coherence import Coherence
from coherence.evolve.dominos import DominoState


class TestDominos(unittest.TestCase):
    def test_gilbert_requires_next_action(self):
        c = Coherence()
        with self.assertRaises(ValueError):
            c.dominos.add("x", "problem", next_action="  ")

    def test_cannot_solve_out_of_order(self):
        c = Coherence(seed_cascade=True)
        second = c.dominos.stones[1]
        with self.assertRaises(RuntimeError):
            c.dominos.solve(second.id, proof="p", lesson="l")

    def test_solve_requires_lesson_and_proof(self):
        c = Coherence(seed_cascade=True)
        h = c.dominos.head()
        with self.assertRaises(ValueError):
            c.dominos.solve(h.id, proof="", lesson="l")
        with self.assertRaises(ValueError):
            c.dominos.solve(h.id, proof="p", lesson="")

    def test_solve_advances_head_and_learns(self):
        mem = Path(tempfile.mkdtemp()) / "evo.json"
        c = Coherence(memory_path=mem, seed_cascade=True)
        h = c.dominos.head()
        self.assertEqual(h.state, DominoState.OPEN)
        rec = c.claimproof.cmd("t", "true", 0)
        c.solve_domino(
            h.id,
            proof="proven",
            lesson="always prove tests",
            proof_record_id=rec.id,
        )
        self.assertEqual(h.state, DominoState.SOLVED)
        self.assertIsNotNone(c.dominos.head())
        self.assertEqual(len(c.evolve.lessons), 1)
        self.assertTrue(mem.exists())

        c2 = Coherence(memory_path=mem)
        self.assertEqual(len(c2.evolve.lessons), 1)
        hits = c2.evolve.apply_hints("prove tests")
        self.assertTrue(len(hits) >= 1)

    def test_chain_complete_next(self):
        c = Coherence()
        d = c.dominos.add("only", "one problem", next_action="chain complete")
        c.solve_domino(d.id, proof="done", lesson="single stone chains still learn")
        self.assertIsNone(c.dominos.head())
        self.assertEqual(c.evolve.lessons[0].next_domino, "chain complete")

    def test_require_dominos_clear(self):
        c = Coherence(seed_cascade=True)
        bad = c.require_dominos_clear()
        self.assertIsNotNone(bad)
        # solve all
        while c.dominos.head():
            h = c.dominos.head()
            c.solve_domino(h.id, proof="p", lesson=f"learned {h.title}")
        self.assertIsNone(c.require_dominos_clear())


if __name__ == "__main__":
    unittest.main()
