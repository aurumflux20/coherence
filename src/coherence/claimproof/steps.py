"""Rung 1 — Claim ≠ Proven (base language)."""

from __future__ import annotations

from typing import Any, Optional

from coherence.core.types import Artifact, Bundle, Record, Truth, digest, new_id


class ClaimProof:
    def __init__(self, bundle: Bundle) -> None:
        self.bundle = bundle

    def claim(self, step: str, said: str, *, next_action: str = "") -> Record:
        """Agent or human *says* something — not proven."""
        rec = Record(
            id=new_id("step"),
            rung=1,
            kind="step",
            truth=Truth.CLAIMED,
            summary=step,
            claimed=said,
            proven="",
            next_action=next_action
            or "attach proof via prove() or treat as untrusted",
            meta={"step": step},
        )
        return self.bundle.add(rec)

    def prove(
        self,
        step: str,
        *,
        said: str,
        artifact_kind: str,
        artifact_value: str,
        meta: Optional[dict[str, Any]] = None,
    ) -> Record:
        """Same step with checkable evidence."""
        art = Artifact(kind=artifact_kind, value=str(artifact_value), meta=meta or {})
        rec = Record(
            id=new_id("step"),
            rung=1,
            kind="step",
            truth=Truth.PROVEN,
            summary=step,
            claimed=said,
            proven=f"{artifact_kind}={art.fingerprint()}",
            artifacts=[art],
            next_action="safe to use this step as evidence for higher rungs",
            meta={"step": step},
        )
        return self.bundle.add(rec)

    def illusion(self, step: str, said: str) -> Record:
        """Treated as done in chat/memory with zero evidence."""
        rec = Record(
            id=new_id("step"),
            rung=1,
            kind="step",
            truth=Truth.ILLUSION,
            summary=step,
            claimed=said,
            proven="none — illusion",
            next_action="do not trust; run prove() with a real artifact",
            meta={"step": step},
        )
        return self.bundle.add(rec)

    def cmd(
        self,
        step: str,
        command: str,
        exit_code: int,
        *,
        stdout_digest: str = "",
    ) -> Record:
        """Convenience: command proof from exit code."""
        if exit_code == 0:
            return self.prove(
                step,
                said=f"ran: {command}",
                artifact_kind="cmd_exit",
                artifact_value=f"{command} → {exit_code}",
                meta={"stdout_digest": stdout_digest or digest(command)},
            )
        rec = Record(
            id=new_id("step"),
            rung=1,
            kind="step",
            truth=Truth.BLOCKED,
            summary=step,
            claimed=f"ran: {command}",
            proven=f"exit_code={exit_code}",
            artifacts=[
                Artifact(kind="cmd_exit", value=f"{command} → {exit_code}")
            ],
            next_action="fix the command; do not claim success",
            meta={"step": step, "exit_code": exit_code},
        )
        return self.bundle.add(rec)
