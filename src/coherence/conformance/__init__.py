"""Turn a conformance RUN into a record a stranger can check.

A battery prints a scorecard. A scorecard is a claim by whoever ran it — the
same "self-administered pass is a declaration, not a verification" problem the
signed record exists to solve. This module is the bridge: it reads a
`hostile-facilitator` result document and writes a coherence session whose
hash chain covers every measured mode, so the existing `attest` can sign it and
`verify` can check it with nothing but a public key.

Two rules make the record worth signing:

1. **A failing mode is recorded as an OPEN fact, never a proven one.** A run
   where the client double-paid cannot produce an all-green record, no matter
   who runs it. `coherence check` on such a session refuses it.
2. **The record binds to the exact result file** by SHA-256. Edit the result
   after the fact and the digest recorded in the signed chain no longer matches
   the file you are holding.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from coherence.core.fact import Fact, FactKind
from coherence.core.spine import Coherence
from coherence.core.types import Artifact, digest_full
from coherence.ci.session import SessionStore

SCHEMA = "https://aurumflux.co/hostile-facilitator/result/v1"
TOOL = "hostile-facilitator"


class ResultError(SystemExit):
    """The input is not a conformance result we can honestly record."""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ResultError(f"not a conformance result: {msg}")


def load_result(path: Path) -> dict[str, Any]:
    """Read and validate. A malformed file must fail loudly, never sign as empty."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        raise ResultError(f"unreadable result file: {e}") from e
    _require(isinstance(doc, dict), "top level is not an object")
    _require(doc.get("tool") == TOOL, f"tool is {doc.get('tool')!r}, expected {TOOL!r}")
    rows = doc.get("results")
    _require(isinstance(rows, list) and rows, "no results to record")
    for r in rows:
        _require(isinstance(r, dict) and r.get("mode"), "a result row has no mode")
    _require(isinstance(doc.get("summary"), dict), "no summary")
    return doc


def _mode_claim(row: dict[str, Any]) -> str:
    mode = row["mode"]
    if row.get("error"):
        return f"{mode}: run errored — {row['error']}"
    n = row.get("distinct")
    if n is None:
        return f"{mode}: no settlement count recorded"
    word = "settlement" if n == 1 else "settlements"
    return f"{mode}: {n} distinct {word} for one purchase"


def from_result(result_path: Path, session_path: Path, *, title: str = "") -> dict[str, Any]:
    """Write a session recording every mode of one conformance run.

    Returns the summary. Facts: one per mode (proven when exactly one
    settlement landed, open otherwise) plus one binding the record to the
    result file's digest.
    """
    result_path = Path(result_path)
    doc = load_result(result_path)
    raw = result_path.read_bytes()
    file_digest = digest_full({"bytes": raw.decode("utf-8", errors="replace")})
    rows = doc["results"]
    target = (doc.get("target") or {}).get("command") or []
    tool_version = doc.get("version", "unknown")

    c = Coherence(title=title or f"conformance run — {TOOL} {tool_version}")

    # The subject of the run, proven by the file itself.
    c.prove(
        f"conformance run recorded: {TOOL} {tool_version}, {len(rows)} modes",
        evidence=f"result_sha256={file_digest} file={result_path.name}",
        next="sign this session, then anyone verifies it with the public key",
        kind=FactKind.STEP,
        artifact=Artifact(kind="conformance_result", value=str(result_path.name),
                          meta={"result_digest": file_digest, "tool": TOOL,
                                "tool_version": tool_version,
                                "target_command": target,
                                "started_at": doc.get("started_at"),
                                "finished_at": doc.get("finished_at")}),
        meta={"result_digest": file_digest},
    )

    for row in rows:
        claim = _mode_claim(row)
        meta = {"mode": row["mode"], "distinct": row.get("distinct"),
                "settle_calls": row.get("settle_calls"),
                "unidentified": row.get("unidentified"),
                "passed": bool(row.get("passed")), "result_digest": file_digest}
        if row.get("passed"):
            c.prove(
                claim,
                evidence=(f"mode={row['mode']} distinct_settlements={row.get('distinct')} "
                          f"settle_calls={row.get('settle_calls')}"),
                next="none — this mode is safe",
                kind=FactKind.STEP,
                artifact=Artifact(kind="conformance_mode", value=row["mode"], meta=meta),
                meta=meta,
            )
        else:
            # Deliberately NOT proven: a mode that double-paid (or errored) is
            # unfinished work, and the record must say so even when the person
            # signing it would rather it didn't.
            c.note(Fact.make(
                claim,
                "fix the client: re-present the SAME payment authorization on an "
                "ambiguous retry instead of minting a new one, then re-run the battery",
                evidence="",
                kind=FactKind.STEP,
                artifacts=[Artifact(kind="conformance_mode", value=row["mode"], meta=meta)],
                meta=meta,
            ))

    store = SessionStore(session_path)
    store.save(c)
    data = json.loads(Path(session_path).read_text(encoding="utf-8"))
    summary = doc["summary"]
    return {
        "status": "recorded",
        "session": str(session_path),
        "chain_head": data.get("chain_head"),
        "result_digest": file_digest,
        "tool": TOOL,
        "tool_version": tool_version,
        "modes": len(rows),
        "safe": summary.get("safe"),
        "verdict": summary.get("verdict"),
        "double_paying_modes": summary.get("double_paying_modes") or [],
        "proven": len(c.done_facts()),
        "open": len(c.open_facts()),
    }
