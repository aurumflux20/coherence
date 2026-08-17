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


# ── tamper-evidence: the whole "agents can't fake green" promise ─────────
import json as _json
from pathlib import Path as _Path

from coherence.ci.session import SessionStore


def test_untouched_session_verifies_ok(tmp_path):
    store = SessionStore(tmp_path / "s.json")
    store.prove_command("true", claim="unit tests")
    assert store.verify()["status"] == "ok"


def test_editing_a_recorded_fact_is_detected(tmp_path):
    """The launch-day attack: the agent flips its own 'open' fact to 'proven'
    by editing the JSON. The chain must catch it, and check must fail hard."""
    p = _Path(tmp_path / "s.json")
    store = SessionStore(p)
    store.prove_command("false", claim="lint")   # exits non-zero -> open/blocked, no evidence

    data = _json.loads(p.read_text())
    data["facts"][0]["evidence"] = "exit_code=0 output_digest=deadbeef"  # forge proof
    p.write_text(_json.dumps(data, indent=2))

    v = store.verify()
    assert v["status"] == "tampered"
    assert v["position"] == 0


def test_appending_a_fake_proven_fact_is_detected(tmp_path):
    p = _Path(tmp_path / "s.json")
    store = SessionStore(p)
    store.prove_command("true", claim="real")

    data = _json.loads(p.read_text())
    data["facts"].append({
        "id": "fact_forged", "claim": "everything passed", "next": "chain complete",
        "evidence": "exit_code=0", "kind": "step", "meta": {}, "created_at": 0,
        "artifacts": [], "prev_hash": data["chain_head"], "entry_hash": "0" * 64,
    })
    p.write_text(_json.dumps(data, indent=2))

    assert store.verify()["status"] == "tampered"


def test_reordering_entries_is_detected(tmp_path):
    p = _Path(tmp_path / "s.json")
    store = SessionStore(p)
    store.prove_command("true", claim="first")
    store.prove_command("true", claim="second")

    data = _json.loads(p.read_text())
    data["facts"].reverse()
    p.write_text(_json.dumps(data, indent=2))

    assert store.verify()["status"] == "tampered"


def test_full_output_evidence_covers_stderr(tmp_path):
    """A command that exits 0 while writing to stderr must not lose that
    evidence — two runs differing only in stderr must fingerprint differently."""
    store = SessionStore(tmp_path / "s.json")
    c1, f1, _ = store.prove_command("printf one >&2; true", claim="c")
    d1 = f1.artifacts[0].meta["output_digest"]

    store2 = SessionStore(tmp_path / "s2.json")
    _, f2, _ = store2.prove_command("printf two >&2; true", claim="c")
    d2 = f2.artifacts[0].meta["output_digest"]

    assert d1 != d2, "stderr must be part of the evidence digest"
    assert f1.artifacts[0].meta["stderr_bytes"] == 3
