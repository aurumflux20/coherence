"""Coherence spine — rungs 1–5 + evolving dominos (6) + memory (7)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from coherence.claimproof.steps import ClaimProof
from coherence.core.types import Bundle, Record, Truth, new_id
from coherence.decisions.log import DecisionLog
from coherence.evolve.dominos import DominoChain, seed_agent_pr_cascade
from coherence.evolve.memory import EvolutionMemory
from coherence.replay.engine import Replayer
from coherence.review.triage import Reviewer
from coherence.skills.audit import SkillAuditor


class Coherence:
    """Single entry: layers stay coherent by sharing one Bundle.

    Revolutionary loop:
      rungs solve reality → dominos order the cascade →
      solve requires lesson → evolution memory compounds →
      next session is more coherent (Gilbert next always set).
    """

    def __init__(
        self,
        title: str = "session",
        *,
        memory_path: Optional[str | Path] = None,
        seed_cascade: bool = False,
    ) -> None:
        self.bundle = Bundle(id=new_id("bun"), title=title)
        self.claimproof = ClaimProof(self.bundle)
        self.skills = SkillAuditor(self.bundle)
        self.decisions = DecisionLog(self.bundle)
        self.replay = Replayer(self.bundle)
        self.review = Reviewer(self.bundle)
        self.dominos = DominoChain(self.bundle, name=title)
        self.evolve = EvolutionMemory(self.bundle, path=memory_path)
        if seed_cascade:
            seed_agent_pr_cascade(self.dominos)

    def solve_domino(
        self,
        domino_id: str,
        *,
        proof: str,
        lesson: str,
        proof_record_id: str = "",
        tags: Optional[list[str]] = None,
    ) -> Record:
        """Knock a domino + teach evolution memory (one atomic product action)."""
        rec = self.dominos.solve(
            domino_id,
            proof=proof,
            lesson=lesson,
            proof_record_id=proof_record_id,
        )
        nxt = self.dominos.head()
        self.evolve.learn(
            problem=rec.claimed,
            lesson=lesson,
            proof=proof,
            next_domino=nxt.next_action if nxt else "chain complete",
            source_domino=domino_id,
            tags=tags,
        )
        return rec

    def summary(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle.id,
            "title": self.bundle.title,
            "counts": self.bundle.counts(),
            "records": len(self.bundle.records),
            "rungs_present": sorted({r.rung for r in self.bundle.records}),
            "dominos_open": self.dominos.head().title if self.dominos.head() else None,
            "evolution": self.evolve.stats(),
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
            if r.kind in ("domino", "evolution"):
                continue  # summarized below
            lines.append(r.plain_english())
            lines.append("")
        lines.append(self.dominos.plain_english())
        lines.append("")
        lines.append(self.evolve.plain_english())
        reviews = self.bundle.by_rung(5)
        if reviews:
            lines.append("")
            lines.append("── triage (rung 5) ──")
            lines.append(reviews[-1].plain_english())
        lines.append("══════════════════════════════════════")
        return "\n".join(lines)

    def require_coherent(self) -> Optional[Record]:
        """Fail closed if higher rung invents proof lower rung denied."""
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

    def require_dominos_clear(self) -> Optional[Record]:
        """Gilbert cascade: open dominos mean the chain is not done."""
        head = self.dominos.head()
        if head is None:
            return None
        bad = Record(
            id=new_id("coh"),
            rung=6,
            kind="domino",
            truth=Truth.BLOCKED,
            summary=f"open domino remains: {head.title}",
            claimed="session marked done",
            proven="chain not complete",
            next_action=head.next_action,
            meta={"domino": head.to_dict()},
        )
        self.bundle.add(bad)
        return bad
