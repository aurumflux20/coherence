"""An audited session must be signable — and a caught lie must never sign green.

`coherence audit` prints a report, and a report is a claim by whoever ran it.
The property that matters here is the same one conformance guards: a claim the
transcript CONTRADICTS must NOT be recordable as proven — by anyone, including
us.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coherence.audit.session import from_audit, TranscriptError
from coherence.audit.transcript import audit_transcript
from coherence.ci.session import SessionStore

SAMPLE = Path(__file__).resolve().parents[1] / "src" / "coherence" / "data" / "sample-session.jsonl"


class TestAuditSession(unittest.TestCase):
    def _record(self, tmp):
        out = Path(tmp) / "session.json"
        summary = from_audit(SAMPLE, out, title="test snapshot")
        return summary, json.loads(out.read_text(encoding="utf-8")), out

    def test_the_sample_contains_a_caught_lie(self):
        """Guards the fixture: without a contradiction the rest passes vacuously."""
        self.assertGreaterEqual(audit_transcript(str(SAMPLE)).counts()["contradicted"], 1)

    def test_a_contradicted_claim_is_recorded_open_never_proven(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary, data, _ = self._record(tmp)
            bad = [f for f in data["facts"]
                   if (f.get("meta") or {}).get("verdict") == "contradicted"]
            self.assertTrue(bad, "the sample's contradicted claim must appear")
            for f in bad:
                self.assertFalse(f.get("evidence"),
                                 "a contradicted claim must carry no evidence")
            self.assertEqual(summary["contradicted"], len(bad))
            self.assertGreaterEqual(summary["open"], len(bad))

    def test_an_unsupported_claim_is_also_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, data, _ = self._record(tmp)
            for f in data["facts"]:
                if (f.get("meta") or {}).get("verdict") == "unsupported":
                    self.assertFalse(f.get("evidence"))

    def test_the_record_binds_to_the_transcript_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary, data, _ = self._record(tmp)
            self.assertEqual(len(summary["transcript_digest"]), 64)
            self.assertTrue(any(
                (f.get("meta") or {}).get("transcript_digest") == summary["transcript_digest"]
                for f in data["facts"]))

    def test_the_session_chain_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, out = self._record(tmp)
            self.assertEqual(SessionStore(out).verify()["status"], "ok")

    def test_counts_match_the_audit_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary, _, _ = self._record(tmp)
            c = audit_transcript(str(SAMPLE)).counts()
            self.assertEqual(summary["claims"], sum(c.values()))
            self.assertEqual(summary["contradicted"], c["contradicted"])
            self.assertEqual(summary["supported"], c["supported"])

    def test_a_file_that_is_not_a_transcript_is_refused(self):
        """The worst possible failure would be signing 'clean' over a file we
        could not read. It must raise, not record."""
        with tempfile.TemporaryDirectory() as tmp:
            junk = Path(tmp) / "notes.md"
            junk.write_text("# just a readme\n", encoding="utf-8")
            with self.assertRaises(TranscriptError):
                from_audit(junk, Path(tmp) / "s.json", title="junk")

    def test_a_missing_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(TranscriptError):
                from_audit(Path(tmp) / "nope.jsonl", Path(tmp) / "s.json")


if __name__ == "__main__":
    unittest.main()
