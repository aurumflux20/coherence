"""Coherence spine — one object that owns the bundle and all rungs."""

from __future__ import annotations

from typing import Any, Optional

from coherence.claimproof.steps import ClaimProof
from coherence.core.types import Bundle, Record, Truth, new_id
from coherence.decisions.log import DecisionLog
from coherence.replay.engine import Replayer
from coherence.review.triage import Reviewer
from coherence.skills.audit import SkillAuditor


class Coherence:
    """Single entry: layers 1–5 stay coherent by sharing one Bundle."""

    def __init__(self, title: str = "session") -> None:
        self.bundle = Bundle(id=new_id("bun"), title=title)
        self.claimproof = ClaimProof(self.bundle)
        self.skills = SkillAuditor(self.bundle)
        self.decisions = DecisionLog(self.bundle)
        self.replay = Replayer(self.bundle)
        self.review = Reviewer(self.bundle)

    def summary(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle.id,
            "title": self.bundle.title,
            "counts": self.bundle.counts(),
            "records": len(self.bundle.records),
            "rungs_present": sorted({r.rung for r in self.bundle.records}),
        }

    def plain_english(self) -> str:
        lines = [
            "══════════════════════════════════════",
            "  COHERENCE — agent reality report",
            f"  {self.bundle.title} ({self.bundle.id})",
            "══════════════════════════════════════",
            f"  counts: {self.bundle.counts()}",
            "",
        ]
        for r in self.bundle.records:
            lines.append(r.plain_english())
            lines.append("")
        # If review already ran, highlight it
        reviews = self.bundle.by_rung(5)
        if reviews:
            lines.append("── triage (rung 5) ──")
            lines.append(reviews[-1].plain_english())
        lines.append("══════════════════════════════════════")
        return "\n".join(lines)

    def require_coherent(self) -> Optional[Record]:
        """Fail closed if higher rung invents proof lower rung denied.

        Returns a BLOCKED record if incoherent; else None.
        """
        # Any review saying proven-heavy while steps are all claimed → flag
        steps = self.bundle.by_rung(1)
        if not steps:
            return None
        proven_steps = [s for s in steps if s.truth == Truth.PROVEN]
        claimed_only = [s for s in steps if s.truth == Truth.CLAIMED]
        reviews = self.bundle.by_rung(5)
        for rev in reviews:
            if rev.meta.get("auto_merge_ok") and claimed_only and not proven_steps:
                bad = Record(
                    id=new_id("coh"),
                    rung=0,
                    kind="coherence_guard",
                    truth=Truth.BLOCKED,
                    summary="Review wanted auto-merge but no step is PROVEN",
                    next_action="prove tests/commands on rung 1 before triage auto-merge",
                    claimed=rev.claimed,
                    proven="coherence guard blocked invented trust",
                    meta={"guard": "no_fake_proof"},
                )
                self.bundle.add(bad)
                return bad
        return None
