"""Signed record — the half of Coherence that cannot be self-issued.

A hash chain (ci/session.py) makes a session tamper-EVIDENT: edit any fact and
`coherence check` refuses it. It does not make the record trustworthy to a
stranger, because anyone can regenerate a perfectly consistent chain from
scratch. A self-administered pass is a declaration, not a verification.

This module adds the signature. `attest` signs the chain head with an issuer
key and emits a DSSE envelope carrying an in-toto v1 Statement, so the record
speaks the same format SLSA/in-toto tooling already consumes. `verify` checks
it with nothing but the envelope and a public key — and, when the session file
is present, also recomputes the chain and binds the envelope to that exact
file by digest. `selftest` is the mutation control: a tampered session, a
wrong key, and an edited payload must each FAIL, or the instrument is lying.

Signing needs the optional extra:  pip install "coherence-check[attest]"
"""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from coherence.ci.session import SessionStore

PAYLOAD_TYPE = "application/vnd.in-toto+json"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://aurumflux.co/coherence/attestation/v1"


def _crypto():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as e:  # pragma: no cover
        raise SystemExit(
            'signing needs the optional extra: pip install "coherence-check[attest]"'
        ) from e
    return serialization, ed25519


def _pae(payload_type: str, payload: bytes) -> bytes:
    """DSSE pre-authentication encoding, exactly as the spec defines it."""
    t = payload_type.encode()
    return b" ".join([b"DSSEv1", str(len(t)).encode(), t, str(len(payload)).encode(), payload])


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _keyid(pub_raw: bytes) -> str:
    return hashlib.sha256(pub_raw).hexdigest()[:16]


def _git_head() -> Optional[str]:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except Exception:
        return None



# --------------------------------------------------------------------------- remote inputs

def _local(path_or_url) -> Path:
    """Accept a local path or an https URL. A URL is fetched to a temp file so a
    stranger can verify a published record with one command and no clone."""
    import tempfile
    import urllib.request
    s = str(path_or_url)
    if s.startswith("http://") or s.startswith("https://"):
        req = urllib.request.Request(s, headers={"User-Agent": "coherence-verify/1"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        f = tempfile.NamedTemporaryFile(delete=False, suffix="-" + s.rsplit("/", 1)[-1][:40])
        f.write(data); f.close()
        return Path(f.name)
    return Path(s)

# --------------------------------------------------------------------------- keys

def keygen(out_dir: Path) -> tuple[Path, Path]:
    """Create an Ed25519 issuer keypair. Private key is written 0600."""
    serialization, ed25519 = _crypto()
    out_dir.mkdir(parents=True, exist_ok=True)
    priv = ed25519.Ed25519PrivateKey.generate()
    key_path = out_dir / "coherence-attest.key"
    pub_path = out_dir / "coherence-attest.pub"
    key_path.write_bytes(priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    key_path.chmod(0o600)
    pub_path.write_bytes(priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return key_path, pub_path


def _load_private(key_path: Path):
    serialization, _ = _crypto()
    return serialization.load_pem_private_key(key_path.read_bytes(), password=None)


def _load_public(pub_path: Path):
    serialization, _ = _crypto()
    return serialization.load_pem_public_key(pub_path.read_bytes())


def _raw_public(pub) -> bytes:
    serialization, _ = _crypto()
    return pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


# --------------------------------------------------------------------------- attest

def attest(session_path: Path, key_path: Path, out_path: Path, issuer: str = "") -> dict[str, Any]:
    """Sign a session's chain head. Refuses a session whose chain does not verify."""
    store = SessionStore(session_path)
    chain = store.verify()
    if chain.get("status") != "ok":
        raise SystemExit(f"refusing to attest: session chain is {chain.get('status')} — {chain.get('detail', '')}")
    data = json.loads(session_path.read_text(encoding="utf-8"))
    priv = _load_private(key_path)
    pub_raw = _raw_public(priv.public_key())
    statement = {
        "_type": STATEMENT_TYPE,
        "subject": [{"name": session_path.name, "digest": {"sha256": _sha256_file(session_path)}}],
        "predicateType": PREDICATE_TYPE,
        "predicate": {
            "law": data.get("law"),
            "title": data.get("title"),
            "chain_head": data.get("chain_head"),
            "entries": len(data.get("facts") or []),
            "done": (data.get("summary") or {}).get("done"),
            "open": (data.get("summary") or {}).get("open"),
            "issued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "issuer": issuer or "unspecified",
            # Anchor: partial. A git head binds the record to a commit; it does not
            # prove the wall-clock time. An external timestamp is property 2, part 2.
            "anchor": {"git_head": _git_head()},
        },
    }
    payload = json.dumps(statement, sort_keys=True, separators=(",", ":")).encode()
    sig = priv.sign(_pae(PAYLOAD_TYPE, payload))
    envelope = {
        "payloadType": PAYLOAD_TYPE,
        "payload": base64.b64encode(payload).decode(),
        "signatures": [{"keyid": _keyid(pub_raw), "sig": base64.b64encode(sig).decode()}],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return {"status": "attested", "out": str(out_path), "chain_head": data.get("chain_head"),
            "entries": statement["predicate"]["entries"], "keyid": envelope["signatures"][0]["keyid"]}


# --------------------------------------------------------------------------- verify

def verify(envelope_path: Path, pub_path: Path, session_path: Optional[Path] = None) -> dict[str, Any]:
    """Verify with nothing but the envelope and a public key.

    Statuses, never softened:
      verified          signature good; if a session was given, it is the exact file
                        the statement names and its chain recomputes cleanly
      bad_signature     signature does not verify under this key (or payload edited)
      unsupported       not a DSSE/in-toto envelope of the kind we issue
      subject_mismatch  session file digest is not the one the statement was signed over
      chain_tampered    session file's own hash chain does not recompute
      head_mismatch     session chain head differs from the signed one
    """
    try:
        envelope_path = _local(envelope_path)
        pub_path = _local(pub_path)
        if session_path is not None:
            session_path = _local(session_path)
        env = json.loads(Path(envelope_path).read_text(encoding="utf-8"))
    except Exception as e:
        return {"status": "unsupported", "detail": f"unreadable envelope: {e}"}
    if env.get("payloadType") != PAYLOAD_TYPE or not env.get("signatures"):
        return {"status": "unsupported", "detail": "not a DSSE envelope with an in-toto payload"}
    try:
        payload = base64.b64decode(env["payload"])
        sig = base64.b64decode(env["signatures"][0]["sig"])
    except Exception as e:
        return {"status": "unsupported", "detail": f"malformed envelope fields: {e}"}
    pub = _load_public(pub_path)
    keyid = _keyid(_raw_public(pub))
    try:
        pub.verify(sig, _pae(PAYLOAD_TYPE, payload))
    except Exception:
        return {"status": "bad_signature", "keyid": keyid}
    try:
        statement = json.loads(payload)
    except Exception:
        return {"status": "unsupported", "detail": "payload is not JSON"}
    if statement.get("_type") != STATEMENT_TYPE or statement.get("predicateType") != PREDICATE_TYPE:
        return {"status": "unsupported", "detail": "statement/predicate type is not one we issue"}
    result: dict[str, Any] = {"status": "verified", "keyid": keyid,
                              "chain_head": statement["predicate"].get("chain_head"),
                              "entries": statement["predicate"].get("entries"),
                              "issued_at": statement["predicate"].get("issued_at")}
    if session_path is None:
        result["session"] = "not checked (no session file given)"
        return result
    session_path = Path(session_path)
    want = (statement["subject"][0].get("digest") or {}).get("sha256")
    if _sha256_file(session_path) != want:
        return {"status": "subject_mismatch", "keyid": keyid,
                "detail": "this session file is not the one the statement was signed over"}
    chain = SessionStore(session_path).verify()
    if chain.get("status") != "ok":
        return {"status": "chain_tampered", "keyid": keyid, "detail": chain}
    data = json.loads(session_path.read_text(encoding="utf-8"))
    if data.get("chain_head") != statement["predicate"].get("chain_head"):
        return {"status": "head_mismatch", "keyid": keyid}
    result["session"] = "chain ok, digest bound"
    return result


# --------------------------------------------------------------------------- mutation control

def selftest() -> dict[str, Any]:
    """The instrument must be able to fail. Three mutations, each must NOT verify."""
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="coherence-attest-"))
    session = tmp / "session.json"
    store = SessionStore(session)
    store.prove_command("true", claim="selftest: a real proven fact", next_action="attest it")
    key, pub = keygen(tmp / "keys")
    env = tmp / "attestation.json"
    attest(session, key, env, issuer="selftest")
    base = verify(env, pub, session)
    checks: dict[str, Any] = {"baseline": base["status"]}

    # 1. tampered session: flip the claim, keep everything else
    tampered = tmp / "session-tampered.json"
    d = json.loads(session.read_text())
    d["facts"][0]["claim"] = "selftest: a claim that was never proven"
    tampered.write_text(json.dumps(d, indent=2))
    checks["tampered_session"] = verify(env, pub, tampered)["status"]

    # 2. wrong key: a fresh issuer must not verify this envelope
    _, pub2 = keygen(tmp / "keys2")
    checks["wrong_key"] = verify(env, pub2, session)["status"]

    # 3. edited payload: change one byte of the signed statement
    e = json.loads(env.read_text())
    raw = base64.b64decode(e["payload"])
    raw2 = raw.replace(b'"issuer":"selftest"', b'"issuer":"someone"')
    e["payload"] = base64.b64encode(raw2).decode()
    edited = tmp / "attestation-edited.json"
    edited.write_text(json.dumps(e))
    checks["edited_payload"] = verify(edited, pub, session)["status"]

    ok = (checks["baseline"] == "verified"
          and checks["tampered_session"] != "verified"
          and checks["wrong_key"] != "verified"
          and checks["edited_payload"] != "verified")
    checks["instrument"] = "honest" if ok else "LYING"
    return checks
