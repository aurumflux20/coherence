"""Signed record: attest / verify / mutation control."""
from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

try:
    import cryptography  # noqa: F401
    HAVE_CRYPTO = True
except ImportError:  # pragma: no cover
    HAVE_CRYPTO = False

from coherence.ci.session import SessionStore


@unittest.skipUnless(HAVE_CRYPTO, "needs: pip install coherence-check[attest]")
class TestAttest(unittest.TestCase):
    def setUp(self) -> None:
        from coherence.attest import attest, keygen, verify
        self.attest, self.keygen, self.verify = attest, keygen, verify
        self.tmp = Path(tempfile.mkdtemp())
        self.session = self.tmp / "session.json"
        store = SessionStore(self.session)
        store.prove_command("true", claim="tests pass", next_action="ship")
        self.key, self.pub = self.keygen(self.tmp / "keys")
        self.env = self.tmp / "attestation.json"
        self.attest(self.session, self.key, self.env, issuer="unit")

    def test_round_trip_verifies_with_only_envelope_and_pubkey(self):
        r = self.verify(self.env, self.pub)
        self.assertEqual(r["status"], "verified")
        self.assertIn("not checked", r["session"])

    def test_round_trip_binds_to_the_exact_session_file(self):
        r = self.verify(self.env, self.pub, self.session)
        self.assertEqual(r["status"], "verified")
        self.assertEqual(r["session"], "chain ok, digest bound")

    def test_envelope_is_dsse_with_intoto_statement(self):
        e = json.loads(self.env.read_text())
        self.assertEqual(e["payloadType"], "application/vnd.in-toto+json")
        st = json.loads(base64.b64decode(e["payload"]))
        self.assertEqual(st["_type"], "https://in-toto.io/Statement/v1")
        self.assertEqual(st["subject"][0]["name"], "session.json")
        self.assertIn("chain_head", st["predicate"])

    def test_tampered_session_does_not_verify(self):
        d = json.loads(self.session.read_text())
        d["facts"][0]["claim"] = "tests pass (they did not)"
        t = self.tmp / "t.json"
        t.write_text(json.dumps(d))
        self.assertNotEqual(self.verify(self.env, self.pub, t)["status"], "verified")

    def test_wrong_key_is_bad_signature(self):
        _, pub2 = self.keygen(self.tmp / "keys2")
        self.assertEqual(self.verify(self.env, pub2, self.session)["status"], "bad_signature")

    def test_edited_payload_is_bad_signature(self):
        e = json.loads(self.env.read_text())
        raw = base64.b64decode(e["payload"]).replace(b'"issuer":"unit"', b'"issuer":"x"')
        e["payload"] = base64.b64encode(raw).decode()
        p = self.tmp / "e.json"
        p.write_text(json.dumps(e))
        self.assertEqual(self.verify(p, self.pub, self.session)["status"], "bad_signature")

    def test_attest_refuses_a_tampered_chain(self):
        d = json.loads(self.session.read_text())
        d["facts"][0]["claim"] = "edited before signing"
        self.session.write_text(json.dumps(d))
        with self.assertRaises(SystemExit):
            self.attest(self.session, self.key, self.tmp / "no.json")

    def test_selftest_reports_honest_instrument(self):
        from coherence.attest import selftest
        r = selftest()
        self.assertEqual(r["instrument"], "honest", r)
