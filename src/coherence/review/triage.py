"""Rung 5 — Review radar: what deserves human eyes."""

from __future__ import annotations

from coherence.core.types import Artifact, Bundle, Record, Truth, digest, new_id


class Reviewer:
    def __init__(self, bundle: Bundle) -> None:
        self.bundle = bundle

    def triage(self) -> Record:
        """Score from rungs 1–4. Never invents PROVEN (coherence rule)."""
        steps = self.bundle.by_rung(1)
        skills = self.bundle.by_rung(2)
        decisions = self.bundle.by_rung(3)
        replays = self.bundle.by_rung(4)

        proven = sum(1 for s in steps if s.truth == Truth.PROVEN)
        claimed = sum(1 for s in steps if s.truth == Truth.CLAIMED)
        illusions = sum(1 for s in steps if s.truth == Truth.ILLUSION)
        blocked = sum(
            1
            for s in steps + skills + decisions + replays
            if s.truth == Truth.BLOCKED
        )
        high_skills = sum(1 for s in skills if s.meta.get("risk") == "high")
        violations = sum(1 for d in decisions if d.meta.get("violation"))
        replay_bad = any(r.truth == Truth.BLOCKED for r in replays)

        # Priority: must_review > skim > low_risk
        if blocked or violations or illusions or replay_bad or high_skills:
            priority = "must_review"
            auto_merge_ok = False
            truth = Truth.BLOCKED if (blocked or violations) else Truth.CLAIMED
            nxt = "human must review — risk signals present"
        elif claimed and not proven:
            priority = "must_review"
            auto_merge_ok = False
            truth = Truth.CLAIMED
            nxt = "only CLAIMED steps — prove tests/commands before merge"
        elif proven and claimed == 0 and not high_skills:
            priority = "low_risk"
            auto_merge_ok = True
            truth = Truth.PROVEN
            nxt = "low risk by coherence signals — still your policy on auto-merge"
        else:
            priority = "skim"
            auto_merge_ok = False
            truth = Truth.CLAIMED
            nxt = "skim review — mixed signals"

        score = {
            "priority": priority,
            "proven_steps": proven,
            "claimed_steps": claimed,
            "illusions": illusions,
            "blocked": blocked,
            "high_risk_skills": high_skills,
            "decision_violations": violations,
            "auto_merge_ok": auto_merge_ok,
        }
        art = Artifact(kind="triage", value=digest(score), meta=score)
        rec = Record(
            id=new_id("rev"),
            rung=5,
            kind="review",
            truth=truth,
            summary=f"review triage: {priority}",
            claimed="PR/session ready for humans",
            proven=f"priority={priority} proven_steps={proven}",
            artifacts=[art],
            next_action=nxt,
            meta=score,
        )
        return self.bundle.add(rec)
