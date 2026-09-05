"""External timestamp anchor — property 2, part 2.

A signature proves who signed; it does not prove *when*. Anyone holding the
key can sign a record today and write yesterday's date in it. An external,
append-only log closes that: the envelope is submitted to Sigstore's public
Rekor transparency log, which records an integrated time and an inclusion
proof that neither the issuer nor the verifier controls.

`anchor()` posts the DSSE envelope as a Rekor `dsse` entry and writes a small
sidecar (uuid, logIndex, integratedTime, logID). `check_anchor()` re-fetches
the entry by uuid and confirms it is a dsse entry whose payload hash matches
this envelope's payload — so the anchor cannot be borrowed from some other
record. Network is only touched by these two functions; stdlib only.
"""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

REKOR = "https://rekor.sigstore.dev"
Fetcher = Callable[[str, Optional[bytes], str], tuple[int, bytes]]


def _http(url: str, body: Optional[bytes], method: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": "coherence-attest/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _payload_sha256(envelope: dict[str, Any]) -> str:
    return hashlib.sha256(base64.b64decode(envelope["payload"])).hexdigest()


def anchor(envelope_path: Path, pub_path: Path, out_path: Optional[Path] = None,
           base: str = REKOR, fetch: Fetcher = _http) -> dict[str, Any]:
    """Submit the envelope to Rekor. Idempotent: an existing entry is returned, not duplicated."""
    envelope_path = Path(envelope_path)
    env_text = envelope_path.read_text(encoding="utf-8")
    envelope = json.loads(env_text)
    pem_b64 = base64.b64encode(Path(pub_path).read_bytes()).decode()
    proposal = {"apiVersion": "0.0.1", "kind": "dsse",
                "spec": {"proposedContent": {"envelope": json.dumps(envelope, separators=(",", ":")),
                                             "verifiers": [pem_b64]}}}
    status, raw = fetch(f"{base}/api/v1/log/entries", json.dumps(proposal).encode(), "POST")
    if status == 409:
        # Already in the log. Rekor answers with the existing entry's location or body.
        try:
            existing = json.loads(raw)
        except Exception:
            existing = {}
        if not existing:
            return {"status": "exists", "detail": "entry already in log; re-run check with the saved uuid"}
        raw_entry = existing
    elif status not in (200, 201):
        return {"status": "rejected", "http": status, "detail": raw[:400].decode(errors="replace")}
    else:
        raw_entry = json.loads(raw)
    uuid, entry = next(iter(raw_entry.items()))
    side = {"log": base, "uuid": uuid, "logIndex": entry.get("logIndex"),
            "integratedTime": entry.get("integratedTime"), "logID": entry.get("logID"),
            "payload_sha256": _payload_sha256(envelope)}
    out = Path(out_path) if out_path else envelope_path.with_suffix(".rekor.json")
    out.write_text(json.dumps(side, indent=2), encoding="utf-8")
    return {"status": "anchored", "uuid": uuid, "logIndex": side["logIndex"],
            "integratedTime": side["integratedTime"], "sidecar": str(out)}


def check_anchor(envelope_path: Path, sidecar_path: Path, fetch: Fetcher = _http) -> dict[str, Any]:
    """Re-fetch the log entry and bind it to THIS envelope by payload hash.

    Statuses: anchored · not_found · wrong_kind · payload_mismatch · unreachable
    """
    from coherence.attest import _local
    side = json.loads(_local(sidecar_path).read_text(encoding="utf-8"))
    envelope = json.loads(_local(envelope_path).read_text(encoding="utf-8"))
    want = _payload_sha256(envelope)
    status, raw = fetch(f"{side['log']}/api/v1/log/entries/{side['uuid']}", None, "GET")
    if status == 404:
        return {"status": "not_found", "uuid": side["uuid"]}
    if status != 200:
        return {"status": "unreachable", "http": status}
    entry = next(iter(json.loads(raw).values()))
    body = json.loads(base64.b64decode(entry["body"]))
    if body.get("kind") != "dsse":
        return {"status": "wrong_kind", "kind": body.get("kind")}
    got = ((body.get("spec") or {}).get("payloadHash") or {}).get("value")
    if got != want:
        return {"status": "payload_mismatch", "logged": got, "envelope": want}
    return {"status": "anchored", "uuid": side["uuid"], "logIndex": entry.get("logIndex"),
            "integratedTime": entry.get("integratedTime"), "logID": entry.get("logID")}
