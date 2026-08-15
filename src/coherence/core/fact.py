"""THE atom. 320 IQ: two fields that matter — evidence and next.

Everything in Coherence is a Fact in costume.
  - claim     : what was said (can be wrong)
  - evidence  : if empty, it is NOT done
  - next      : if empty, it is ILLEGAL (Gilbert)

Nothing is remembered without evidence.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from coherence.core.types import Artifact, Record, Truth, digest, new_id


class FactError(ValueError):
    """Law violation — fail closed, always say what to do."""

    def __init__(self, message: str, next_action: str):
        self.next_action = next_action
        super().__init__(f"{message} | NEXT: {next_action}")


class FactKind(str, Enum):
    """Costume only — law is the same for all."""

    STEP = "step"  # rung 1
    SKILL = "skill"  # rung 2
    DECISION = "decision"  # rung 3
    REPLAY = "replay"  # rung 4
    REVIEW = "review"  # rung 5
    DOMINO = "domino"  # rung 6
    LESSON = "lesson"  # rung 7


@dataclass(frozen=True)
class Fact:
    """The only object that matters.

    320 IQ contract:
      done      ⇔ evidence is non-empty
      finished  ⇔ next is non-empty  (always required)
      remember  ⇔ done  (enforced by learn())
    """

    id: str
    claim: str
    evidence: str  # empty = not done
    next: str  # empty = illegal at construction
    kind: FactKind = FactKind.STEP
    artifacts: tuple[Artifact, ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    # ── law ─────────────────────────────────────────────────────────────

    @property
    def done(self) -> bool:
        """Has evidence. Chat does not count."""
        return bool(self.evidence and self.evidence.strip())

    @property
    def finished_shape(self) -> bool:
        """Gilbert: next is always present (construction enforces)."""
        return bool(self.next and self.next.strip())

    @property
    def truth(self) -> Truth:
        if self.done:
            return Truth.PROVEN
        if self.meta.get("illusion"):
            return Truth.ILLUSION
        if self.meta.get("blocked"):
            return Truth.BLOCKED
        return Truth.CLAIMED

    def rememberable(self) -> bool:
        """320 IQ: only done facts may become memory."""
        return self.done

    # ── construction (law enforced here) ────────────────────────────────

    @staticmethod
    def make(
        claim: str,
        next: str,
        *,
        evidence: str = "",
        kind: FactKind = FactKind.STEP,
        artifacts: Optional[list[Artifact]] = None,
        meta: Optional[dict[str, Any]] = None,
        fact_id: Optional[str] = None,
    ) -> "Fact":
        claim = (claim or "").strip()
        next = (next or "").strip()
        evidence = (evidence or "").strip()
        if not claim:
            raise FactError("empty claim", "say what happened or what was asserted")
        if not next:
            raise FactError(
                "Gilbert: empty next — communication did not happen",
                "set next= to the next real action, or 'chain complete'",
            )
        return Fact(
            id=fact_id or new_id("fact"),
            claim=claim,
            evidence=evidence,
            next=next,
            kind=kind,
            artifacts=tuple(artifacts or ()),
            meta=dict(meta or {}),
        )

    @staticmethod
    def said(claim: str, next: str, **kwargs: Any) -> "Fact":
        """Not done — claim only."""
        return Fact.make(claim, next, evidence="", **kwargs)

    @staticmethod
    def proven(
        claim: str,
        evidence: str,
        next: str,
        *,
        artifact: Optional[Artifact] = None,
        **kwargs: Any,
    ) -> "Fact":
        """Done — has evidence."""
        if not (evidence or "").strip():
            raise FactError(
                "proven() without evidence is a lie",
                "pass evidence= or use said()",
            )
        arts = [artifact] if artifact else None
        return Fact.make(claim, next, evidence=evidence, artifacts=arts, **kwargs)

    def with_evidence(self, evidence: str, *, artifact: Optional[Artifact] = None) -> "Fact":
        """Promote claim → done. Next stays (or caller replaces via make)."""
        if not (evidence or "").strip():
            raise FactError("empty evidence", "attach a real artifact fingerprint")
        arts = list(self.artifacts)
        if artifact:
            arts.append(artifact)
        return Fact.make(
            self.claim,
            self.next,
            evidence=evidence,
            kind=self.kind,
            artifacts=arts,
            meta=dict(self.meta),
            fact_id=self.id,
        )

    # ── bridge to existing Record spine ─────────────────────────────────

    def to_record(self, *, rung: Optional[int] = None) -> Record:
        rung_map = {
            FactKind.STEP: 1,
            FactKind.SKILL: 2,
            FactKind.DECISION: 3,
            FactKind.REPLAY: 4,
            FactKind.REVIEW: 5,
            FactKind.DOMINO: 6,
            FactKind.LESSON: 7,
        }
        r = rung if rung is not None else rung_map.get(self.kind, 1)
        return Record(
            id=self.id,
            rung=r,
            kind=self.kind.value,
            truth=self.truth,
            summary=self.claim[:120],
            next_action=self.next,
            claimed=self.claim,
            proven=self.evidence if self.done else "",
            artifacts=list(self.artifacts),
            meta={**self.meta, "fact": True, "done": self.done},
            created_at=self.created_at,
        )

    def plain_english(self) -> str:
        status = "DONE" if self.done else "NOT DONE"
        return (
            f"FACT [{status}] {self.kind.value}\n"
            f"  claim:    {self.claim}\n"
            f"  evidence: {self.evidence or '—'}\n"
            f"  next:     {self.next}"
        )

    def fingerprint(self) -> str:
        return digest(
            {
                "claim": self.claim,
                "evidence": self.evidence,
                "next": self.next,
                "kind": self.kind.value,
            }
        )


# The law as a string constant — importable, printable, non-negotiable
LAW = (
    "Nothing is done unless there is evidence. "
    "Nothing is finished unless there is a next. "
    "Nothing is remembered unless it was done."
)
