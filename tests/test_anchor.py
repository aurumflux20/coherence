"""Rekor anchor: offline, with a fake log. The real log is exercised once, by hand."""
from __future__ import annotations

import base64
import hashlib
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


class FakeRekor:
    """Just enough of Rekor's dsse entry API to test both directions."""

    def __init__(self) -> None:
        self.entries: dict[str, dict] = {}
        self.posts = 0

    def __call__(self, url: str, body, method: str):
        if method == "POST":
            self.posts += 1
            proposal = json.loads(body)
            env = json.loads(proposal["spec"]["proposedContent"]["envelope"])
            payload = base64.b64decode(env["payload"])
            h = hashlib.sha256(payload).hexdigest()
            uuid = "24296fb24b8ad77a" + h[:48]
            if uuid in self.entries:
                return 409, json.dumps({uuid: self.entries[uuid]}).encode()
            entry_body = {"apiVersion": "0.0.1", "kind": "dsse",
                          "spec": {"payloadHash": {"algorithm": "sha256", "value": h}}}
            self.entries[uuid] = {"body": base64.b64encode(json.dumps(entry_body).encode()).decode(),
                                  "integratedTime": 1788600000, "logID": "fake", "logIndex": 4163431}
            return 201, json.dumps({uuid: self.entries[uuid]}).encode()
        uuid = url.rsplit("/", 1)[-1]
        if uuid not in self.entries:
            return 404, b"{}"
        return 200, json.dumps({uuid: self.entries[uuid]}).encode()


@unittest.skipUnless(HAVE_CRYPTO, "needs: pip install coherence-check[attest]")
class TestAnchor(unittest.TestCase):
    def setUp(self) -> None:
        from coherence.attest import attest, keygen
        self.tmp = Path(tempfile.mkdtemp())
        session = self.tmp / "session.json"
        SessionStore(session).prove_command("true", claim="anchored fact", next_action="anchor it")
        self.key, self.pub = keygen(self.tmp / "keys")
        self.env = self.tmp / "attestation.json"
        attest(session, self.key, self.env, issuer="unit")
        self.log = FakeRekor()

    def test_anchor_then_check_binds_by_payload_hash(self):
        from coherence.attest.anchor import anchor, check_anchor
        r = anchor(self.env, self.pub, fetch=self.log)
        self.assertEqual(r["status"], "anchored")
        side = Path(r["sidecar"])
        self.assertTrue(side.exists())
        c = check_anchor(self.env, side, fetch=self.log)
        self.assertEqual(c["status"], "anchored")
        self.assertEqual(c["integratedTime"], 1788600000)

    def test_anchor_is_idempotent(self):
        from coherence.attest.anchor import anchor
        a = anchor(self.env, self.pub, fetch=self.log)
        b = anchor(self.env, self.pub, fetch=self.log)
        self.assertEqual(a["uuid"], b["uuid"])
        self.assertEqual(self.log.posts, 2)
        self.assertEqual(len(self.log.entries), 1)

    def test_anchor_cannot_be_borrowed_by_another_record(self):
        """The sidecar of record A must not verify record B."""
        from coherence.attest import attest, keygen
        from coherence.attest.anchor import anchor, check_anchor
        r = anchor(self.env, self.pub, fetch=self.log)
        other_session = self.tmp / "other.json"
        SessionStore(other_session).prove_command("true", claim="a different fact", next_action="x")
        other_env = self.tmp / "other-attestation.json"
        attest(other_session, self.key, other_env, issuer="unit")
        c = check_anchor(other_env, Path(r["sidecar"]), fetch=self.log)
        self.assertEqual(c["status"], "payload_mismatch")

    def test_missing_entry_is_not_found(self):
        from coherence.attest.anchor import check_anchor
        side = self.tmp / "side.json"
        side.write_text(json.dumps({"log": "https://fake", "uuid": "nope"}))
        self.assertEqual(check_anchor(self.env, side, fetch=self.log)["status"], "not_found")

    def test_rejection_is_reported_not_raised(self):
        from coherence.attest.anchor import anchor
        def bad(url, body, method):
            return 400, b'{"message":"schema"}'
        r = anchor(self.env, self.pub, fetch=bad)
        self.assertEqual(r["status"], "rejected")
        self.assertEqual(r["http"], 400)
