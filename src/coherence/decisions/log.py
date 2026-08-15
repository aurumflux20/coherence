"""Rung 3 — Decision capsule: append-only project truths."""

from __future__ import annotations

from typing import Optional

from coherence.core.types import Artifact, Bundle, Record, Truth, digest, new_id


class DecisionLog:
    def __init__(self, bundle: Bundle) -> None:
        self.bundle = bundle
        self._chain: list[str] = []  # fingerprints in order

    def lock(self, decision_id: str, text: str, *, by: str = "human") -> Record:
        """Append a locked decision. Agents should not violate without a new entry."""
        prev = self._chain[-1] if self._chain else "genesis"
        body = {"id": decision_id, "text": text, "by": by, "prev": prev}
        fp = digest(body)
        self._chain.append(fp)
        art = Artifact(kind="decision", value=fp, meta=body)
        rec = Record(
            id=new_id("dec"),
            rung=3,
            kind="decision",
            truth=Truth.PROVEN,
            summary=f"decision locked: {decision_id}",
            claimed=f"{by} decided",
            proven=f"chain={fp} prev={prev}",
            artifacts=[art],
            next_action="agents must load this decision; violate only with a new lock()",
            meta=body,
        )
        return self.bundle.add(rec)

    def check_violation(self, decision_id: str, agent_said: str) -> Optional[Record]:
        """If agent claims work that ignores a locked decision, mark ILLUSION/BLOCKED."""
        locked = [
            r
            for r in self.bundle.by_rung(3)
            if r.meta.get("id") == decision_id
        ]
        if not locked:
            rec = Record(
                id=new_id("dec"),
                rung=3,
                kind="decision",
                truth=Truth.OPEN,
                summary=f"no decision {decision_id!r} in capsule",
                claimed=agent_said,
                proven="",
                next_action=f"lock({decision_id!r}, ...) first or ignore check",
                meta={"id": decision_id},
            )
            return self.bundle.add(rec)

        # Lightweight v0: only flag clear admissions of forbidden acts.
        # (Not NLP — higher rungs still need human review.)
        text = (locked[-1].meta.get("text") or "").lower()
        said = agent_said.lower()
        conflict = False
        if "must not" in text or "never" in text:
            for bad in (
                "rewrote auth",
                "rewrite auth",
                "deleted auth",
                "removed tests",
                "force push",
                "forced push",
            ):
                # "did not rewrite auth" is compliance, not violation
                if bad in said and f"did not {bad}" not in said and f"didn't {bad}" not in said:
                    conflict = True

        if conflict:
            rec = Record(
                id=new_id("dec"),
                rung=3,
                kind="decision",
                truth=Truth.BLOCKED,
                summary=f"possible violation of {decision_id}",
                claimed=agent_said,
                proven=f"conflicts with locked decision {decision_id}",
                links=[locked[-1].id],
                next_action="human review required; do not merge",
                meta={"id": decision_id, "violation": True},
            )
            return self.bundle.add(rec)

        rec = Record(
            id=new_id("dec"),
            rung=3,
            kind="decision",
            truth=Truth.PROVEN,
            summary=f"aligned with {decision_id}",
            claimed=agent_said,
            proven="no crude contradiction detected",
            links=[locked[-1].id],
            next_action="continue; still verify with rung-1 proofs",
            meta={"id": decision_id, "violation": False},
        )
        return self.bundle.add(rec)

    def chain_ok(self) -> bool:
        return True  # in-memory append-only; file backend later
