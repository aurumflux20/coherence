"""Turn an audited session into a record a stranger can check.

`coherence audit` prints a report. A report is a claim by whoever ran it — the
same "a self-administered pass is a declaration, not a verification" problem
the signed record exists to solve, and the sharper version of it here: the only
witness to whether an agent read a file is the agent saying it did.

This module is the bridge. It reads an agent transcript, rules on every
checkable claim, and writes a coherence session whose hash chain covers each
ruling, so the existing `attest` can sign it and `verify` can check it with
nothing but a public key.

Two rules make the record worth signing, and they mirror `coherence.conformance`:

1. **A claim the transcript CONTRADICTS is recorded OPEN, never proven.** So is
   one resting on nothing. A session containing a caught lie cannot be signed
   as all-green by anyone, including the person who ran it.
2. **The record binds to the exact transcript** by SHA-256. Edit the session
   file afterwards and the digest in the signed chain no longer matches the
   file you are holding.

A weak verdict — the command succeeded but its exit code came through a pipe —
is recorded proven, with the weakness named in the evidence rather than hidden,
because the claim did happen; it is the evidence that is thin.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from coherence.audit.transcript import (
    CONTRADICTED,
    SUPPORTED,
    UNSUPPORTED,
    WEAK,
    audit_transcript,
)
from coherence.ci.session import SessionStore
from coherence.core.fact import Fact, FactKind
from coherence.core.spine import Coherence
from coherence.core.types import Artifact, digest_full

SCHEMA = "https://aurumflux.co/coherence/audit-session/v1"

#: What a reader should do about each verdict. Recorded next to the claim so
#: the record is actionable rather than only accusatory.
_NEXT = {
    CONTRADICTED: ("re-establish this claim from the run itself: its own transcript "
                   "records a failing exit code beside it"),
    UNSUPPORTED: ("re-run the check this claim describes; nothing in the transcript "
                  "establishes it either way"),
}


class TranscriptError(SystemExit):
    """The input is not an agent transcript we can honestly record."""


def _claim_evidence(claim: Any) -> str:
    ev = (claim.evidence or "").strip()
    if claim.verdict == WEAK:
        return (f"{ev} — WEAK: the exit code reaching this claim passed through a "
                f"pipe, so it reports the last stage, not the command").strip(" —")
    return ev


def from_audit(transcript_path: Path, session_path: Path, *, title: str = "") -> dict[str, Any]:
    """Write a session recording every checkable claim in one transcript.

    Returns the summary. Facts: one per claim (proven when the transcript
    supports it, open when it contradicts it or rests on nothing) plus one
    binding the record to the transcript's digest.
    """
    transcript_path = Path(transcript_path)
    if not transcript_path.exists() or not transcript_path.is_file():
        raise TranscriptError(f"not a readable file: {transcript_path}")

    audit = audit_transcript(str(transcript_path))
    # A file we could not read as a transcript must never be signed as a clean
    # audit. This is the UNKNOWN-collapsed-into-CLEAN failure the whole tool
    # exists to catch, and it would be worst of all inside a signed artifact.
    if not audit.looks_like_transcript():
        raise TranscriptError(
            f"refusing to record: {transcript_path.name} does not look like an agent "
            f"transcript (no commands or assistant messages found). This is NOT a "
            f"clean result."
        )

    raw = transcript_path.read_bytes()
    transcript_digest = digest_full({"bytes": raw.decode("utf-8", errors="replace")})
    counts = audit.counts()

    c = Coherence(title=title or f"agent honesty snapshot — {transcript_path.name}")

    # The subject of the snapshot, proven by the file itself.
    c.prove(
        (f"transcript audited: {len(audit.claims)} checkable claims across "
         f"{audit.commands} commands"),
        evidence=f"transcript_sha256={transcript_digest} file={transcript_path.name}",
        next="sign this session, then anyone verifies it with the public key",
        kind=FactKind.STEP,
        artifact=Artifact(
            kind="agent_transcript",
            value=transcript_path.name,
            meta={
                "transcript_digest": transcript_digest,
                "schema": SCHEMA,
                "commands": audit.commands,
                "lines": audit.lines,
                "claims": len(audit.claims),
                "counts": counts,
            },
        ),
        meta={"transcript_digest": transcript_digest, "schema": SCHEMA},
    )

    for claim in audit.claims:
        meta = {
            "seq": claim.seq,
            "kind": claim.kind,
            "verdict": claim.verdict,
            "transcript_digest": transcript_digest,
        }
        artifact = Artifact(kind="agent_claim", value=f"seq-{claim.seq}", meta=meta)
        if claim.verdict in (SUPPORTED, WEAK):
            c.prove(
                claim.text,
                evidence=_claim_evidence(claim),
                next="none — the transcript establishes this claim",
                kind=FactKind.STEP,
                artifact=artifact,
                meta=meta,
            )
        else:
            # Deliberately NOT proven. A claim its own transcript contradicts is
            # unfinished work, and the record must say so even when the person
            # signing it would rather it did not.
            c.note(
                Fact.make(
                    claim.text,
                    _NEXT.get(claim.verdict, "establish this claim before relying on it"),
                    evidence="",
                    kind=FactKind.STEP,
                    artifacts=[artifact],
                    meta=meta,
                )
            )

    store = SessionStore(session_path)
    store.save(c)
    data = json.loads(Path(session_path).read_text(encoding="utf-8"))
    return {
        "status": "recorded",
        "session": str(session_path),
        "chain_head": data.get("chain_head"),
        "transcript": transcript_path.name,
        "transcript_digest": transcript_digest,
        "commands": audit.commands,
        "claims": len(audit.claims),
        "supported": counts.get(SUPPORTED, 0),
        "supported_weak": counts.get(WEAK, 0),
        "unsupported": counts.get(UNSUPPORTED, 0),
        "contradicted": counts.get(CONTRADICTED, 0),
        "proven": len(c.done_facts()),
        "open": len(c.open_facts()),
    }
