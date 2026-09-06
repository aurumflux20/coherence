"""A conformance run recorded as a signable session.

The property that matters: a run where the client double-paid must NOT be
recordable as an all-green record — by anyone, including us.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coherence.ci.session import SessionStore
from coherence.conformance import from_result, load_result, ResultError

MODES = ["accept_then_timeout", "5xx_after_settle", "double_402", "clean"]


def _doc(rows):
    return {"tool": "hostile-facilitator", "version": "0.1.2",
            "schema": "https://aurumflux.co/hostile-facilitator/result/v1",
            "target": {"command": ["./pay.sh"], "facilitator_env": "FACILITATOR_URL"},
            "battery": {"modes": MODES, "count": len(MODES)},
            "started_at": "2026-09-06T00:00:00Z", "finished_at": "2026-09-06T00:00:42Z",
            "results": rows,
            "summary": {"safe": sum(1 for r in rows if r.get("passed")), "total": len(rows),
                        "verdict": "PASS" if all(r.get("passed") for r in rows) else "FAIL",
                        "double_paying_modes": [r["mode"] for r in rows if (r.get("distinct") or 0) > 1],
                        "errored_modes": [r["mode"] for r in rows if r.get("error")]}}


def _rows(fail_first=False):
    rows = [{"mode": m, "distinct": 1, "settle_calls": 1, "unidentified": 0, "passed": True}
            for m in MODES]
    if fail_first:
        rows[0].update(distinct=2, settle_calls=2, passed=False)
    return rows


class TestConformance(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _write(self, doc) -> Path:
        p = self.tmp / "result.json"
        p.write_text(json.dumps(doc, indent=2))
        return p

    def test_clean_run_records_every_mode_as_proven(self):
        r = from_result(self._write(_doc(_rows())), self.tmp / "s.json")
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["open"], 0)
        self.assertEqual(r["proven"], len(MODES) + 1)   # modes + the binding fact

    def test_a_double_payment_cannot_be_recorded_as_proven(self):
        r = from_result(self._write(_doc(_rows(fail_first=True))), self.tmp / "s.json")
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["open"], 1)
        self.assertEqual(r["double_paying_modes"], ["accept_then_timeout"])
        data = json.loads((self.tmp / "s.json").read_text())
        failing = [f for f in data["facts"] if f["meta"].get("mode") == "accept_then_timeout"]
        self.assertEqual(len(failing), 1)
        self.assertEqual(failing[0]["evidence"], "")   # no evidence == not done

    def test_the_session_chain_verifies(self):
        from_result(self._write(_doc(_rows())), self.tmp / "s.json")
        self.assertEqual(SessionStore(self.tmp / "s.json").verify().get("status"), "ok")

    def test_record_binds_to_the_exact_result_file(self):
        p = self._write(_doc(_rows()))
        first = from_result(p, self.tmp / "a.json")
        # a run that measured something different is a different record
        p.write_text(json.dumps(_doc(_rows(fail_first=True)), indent=2))
        second = from_result(p, self.tmp / "b.json")
        self.assertNotEqual(first["result_digest"], second["result_digest"])
        self.assertNotEqual(first["chain_head"], second["chain_head"])

    def test_an_errored_mode_is_open_not_proven(self):
        rows = _rows()
        rows[1] = {"mode": MODES[1], "error": "client command not found", "distinct": None, "passed": False}
        r = from_result(self._write(_doc(rows)), self.tmp / "s.json")
        self.assertEqual(r["open"], 1)
        self.assertIn("errored", json.dumps(json.loads((self.tmp / "s.json").read_text())))

    def test_a_foreign_or_broken_file_is_refused_not_signed(self):
        bad = self.tmp / "bad.json"
        for content in ['{"tool": "something-else", "results": [], "summary": {}}',
                        '{"tool": "hostile-facilitator", "results": [], "summary": {}}',
                        'not json at all']:
            bad.write_text(content)
            with self.assertRaises(ResultError):
                load_result(bad)

    def test_records_the_command_that_was_driven(self):
        from_result(self._write(_doc(_rows())), self.tmp / "s.json")
        data = json.loads((self.tmp / "s.json").read_text())
        self.assertIn("./pay.sh", json.dumps(data))
