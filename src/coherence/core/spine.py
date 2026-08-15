"""Coherence spine — one law, many costumes.

320 IQ: everything is a Fact (evidence + next).
Rungs/dominos/memory are packaging around that atom.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from coherence.claimproof.steps import ClaimProof
from coherence.core.fact import LAW, Fact, FactError, FactKind
from coherence.core.types import Bundle, Record, Truth, new_id
from coherence.decisions.log import DecisionLog
from coherence.evolve.dominos import DominoChain, seed_agent_pr_cascade
from coherence.evolve.memory import EvolutionMemory
from coherence.replay.engine import Replayer
from coherence.review.triage import Reviewer
from coherence.skills.audit import SkillAuditor


class Coherence:
    """Single entry.

    Law:
      Nothing is done unless there is evidence.
      Nothing is finished unless there is a next.
      Nothing is remembered unless it was done.
    """

    LAW = LAW

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
        self.facts: list[Fact] = []
        if seed_cascade:
            seed_agent_pr_cascade(self.dominos)

    def note(self, fact: Fact) -> Fact:
        """Record a Fact — the only write path that matters at 320 IQ."""
        if not fact.finished_shape:
            raise FactError(
                "Fact missing next",
                "set next= or use Fact.make(..., next=...)",
            )
        self.facts.append(fact)
        self.bundle.add(fact.to_record())
        return fact

    def said(self, claim: str, next: str, **kwargs: Any) -> Fact:
        """Not done — claim only. Still requires next (Gilbert)."""
        return self.note(Fact.said(claim, next, **kwargs))

    def prove(self, claim: str, evidence: str, next: str, **kwargs: Any) -> Fact:
        """Done — has evidence. Still requires next."""
        return self.note(Fact.proven(claim, evidence, next, **kwargs))

    def solve_domino(
        self,
        domino_id: str,
        *,
        proof: str,
        lesson: str,
        proof_record_id: str = "",
        tags: Optional[list[str]] = None,
    ) -> Record:
        """Knock a domino + teach evolution memory (only if proof = done)."""
        if not (proof or "").strip():
            raise FactError(
                "cannot solve domino without evidence",
                "prove the step first, then solve_domino(proof=...)",
            )
        rec = self.dominos.solve(
            domino_id,
            proof=proof,
            lesson=lesson,
            proof_record_id=proof_record_id,
        )
        nxt = self.dominos.head()
        # 320 IQ: only done things are remembered
        done = Fact.proven(
            claim=rec.claimed,
            evidence=proof,
            next=nxt.next_action if nxt else "chain complete",
            kind=FactKind.LESSON,
            meta={"lesson": lesson, "domino_id": domino_id},
        )
        self.facts.append(done)
        self.evolve.learn(
            problem=rec.claimed,
            lesson=lesson,
            proof=proof,
            next_domino=nxt.next_action if nxt else "chain complete",
            source_domino=domino_id,
            tags=tags,
        )
        return rec

    def open_facts(self) -> list[Fact]:
        """Not done — still need evidence."""
        return [f for f in self.facts if not f.done]

    def done_facts(self) -> list[Fact]:
        return [f for f in self.facts if f.done]

    def summary(self) -> dict[str, Any]:
        return {
            "law": LAW,
            "bundle_id": self.bundle.id,
            "title": self.bundle.title,
            "counts": self.bundle.counts(),
            "records": len(self.bundle.records),
            "facts_open": len(self.open_facts()),
            "facts_done": len(self.done_facts()),
            "rungs_present": sorted({r.rung for r in self.bundle.records}),
            "dominos_open": self.dominos.head().title if self.dominos.head() else None,
            "evolution": self.evolve.stats(),
        }

    def plain_english(self) -> str:
        lines = [
            "══════════════════════════════════════",
            "  COHERENCE — one law",
            f"  {LAW}",
            f"  {self.bundle.title} ({self.bundle.id})",
            "══════════════════════════════════════",
            f"  facts: {len(self.done_facts())} done · {len(self.open_facts())} open",
            f"  counts: {self.bundle.counts()}",
            "",
        ]
        if self.facts:
            lines.append("── facts (the atom) ──")
            for f in self.facts[-12:]:
                lines.append(f.plain_english())
                lines.append("")

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
