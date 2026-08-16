"""Domino chains — cascade problems with Gilbert next_action on every stone.

Murphy: cascades will go wrong if links are silent.
Gilbert: solving one stone MUST name what to do next (or 'chain complete').
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from coherence.core.types import Artifact, Bundle, Record, Truth, digest, new_id


class DominoState(str, Enum):
    WAITING = "waiting"  # blocked on earlier stone
    OPEN = "open"  # this is the active problem
    SOLVED = "solved"
    SKIPPED = "skipped"


@dataclass
class Domino:
    """One stone in a failure/success cascade."""

    id: str
    title: str
    problem: str
    next_action: str  # Gilbert: required always
    state: DominoState = DominoState.WAITING
    order: int = 0
    proof: str = ""
    lesson: str = ""
    record_id: str = ""
    solved_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "problem": self.problem,
            "next_action": self.next_action,
            "state": self.state.value,
            "order": self.order,
            "proof": self.proof,
            "lesson": self.lesson,
            "record_id": self.record_id,
            "solved_at": self.solved_at,
        }


class DominoChain:
    """Ordered cascade. Only the head OPEN stone may be solved.

    Revolutionary product rule:
      solve(i) requires proof + lesson + (next stone's next_action already set
      or explicit chain_complete on the last stone).
    """

    def __init__(self, bundle: Bundle, name: str = "default") -> None:
        self.bundle = bundle
        self.name = name
        self.stones: list[Domino] = []

    def add(
        self,
        title: str,
        problem: str,
        next_action: str,
        *,
        domino_id: Optional[str] = None,
    ) -> Domino:
        if not (next_action or "").strip():
            raise ValueError(
                "every domino must name next_action "
                "(what to do after this stone, or 'chain complete')"
            )
        d = Domino(
            id=domino_id or new_id("dom"),
            title=title.strip(),
            problem=problem.strip(),
            next_action=next_action.strip(),
            order=len(self.stones),
            state=DominoState.OPEN if not self.stones else DominoState.WAITING,
        )
        self.stones.append(d)
        self._sync_head()
        self.bundle.add(
            Record(
                id=new_id("dom"),
                rung=6,
                kind="domino",
                truth=Truth.OPEN if d.state == DominoState.OPEN else Truth.CLAIMED,
                summary=f"domino added: {d.title}",
                claimed=d.problem,
                proven="",
                next_action=d.next_action
                if d.state == DominoState.OPEN
                else f"wait — solve earlier dominos first; later: {d.next_action}",
                meta={"domino": d.to_dict(), "chain": self.name},
            )
        )
        return d

    def head(self) -> Optional[Domino]:
        for s in self.stones:
            if s.state == DominoState.OPEN:
                return s
        return None

    def _sync_head(self) -> None:
        """First unsolved becomes OPEN; rest WAITING."""
        found_open = False
        for s in self.stones:
            if s.state == DominoState.SOLVED or s.state == DominoState.SKIPPED:
                continue
            if not found_open:
                s.state = DominoState.OPEN
                found_open = True
            else:
                s.state = DominoState.WAITING

    def solve(
        self,
        domino_id: str,
        *,
        proof: str,
        lesson: str,
        proof_record_id: str = "",
    ) -> Record:
        """Knock one stone. Requires proof + lesson (evolution fuel)."""
        if not (proof or "").strip():
            raise ValueError("cannot solve a domino without proof")
        if not (lesson or "").strip():
            raise ValueError(
                "Evolution: cannot solve without a lesson "
                "(what Coherence should remember)"
            )

        stone = next((s for s in self.stones if s.id == domino_id), None)
        if stone is None:
            raise KeyError(f"unknown domino: {domino_id}")
        if stone.state != DominoState.OPEN:
            raise RuntimeError(
                f"domino {stone.title!r} is {stone.state.value} — "
                f"NEXT: solve the OPEN head first ({self.head() and self.head().title})"
            )

        stone.state = DominoState.SOLVED
        stone.proof = proof.strip()
        stone.lesson = lesson.strip()
        stone.record_id = proof_record_id
        stone.solved_at = time.time()
        self._sync_head()

        nxt = self.head()
        if nxt:
            next_msg = (
                f"DOMINO KNOCKED → next OPEN: {nxt.title!r} | "
                f"NEXT: {nxt.next_action}"
            )
            truth = Truth.PROVEN
        else:
            next_msg = "DOMINO CHAIN COMPLETE — no silent remainder"
            truth = Truth.PROVEN

        art = Artifact(
            kind="domino_solved",
            value=digest(stone.to_dict()),
            meta=stone.to_dict(),
        )
        rec = Record(
            id=new_id("dom"),
            rung=6,
            kind="domino",
            truth=truth,
            summary=f"domino solved: {stone.title}",
            claimed=stone.problem,
            proven=proof,
            artifacts=[art],
            links=[proof_record_id] if proof_record_id else [],
            next_action=next_msg,
            meta={
                "domino": stone.to_dict(),
                "lesson": lesson,
                "chain": self.name,
                "chain_complete": nxt is None,
                "next_domino_id": nxt.id if nxt else None,
            },
        )
        return self.bundle.add(rec)

    def open_risks(self) -> list[Domino]:
        return [s for s in self.stones if s.state in (DominoState.OPEN, DominoState.WAITING)]

    def plain_english(self) -> str:
        lines = [f"DOMINO CHAIN · {self.name}", "─" * 40]
        for s in self.stones:
            mark = {
                DominoState.SOLVED: "✓",
                DominoState.OPEN: "►",
                DominoState.WAITING: "·",
                DominoState.SKIPPED: "~",
            }[s.state]
            lines.append(f"  {mark} [{s.state.value}] {s.order + 1}. {s.title}")
            lines.append(f"      problem: {s.problem}")
            lines.append(f"      NEXT:    {s.next_action}")
            if s.lesson:
                lines.append(f"      lesson:  {s.lesson}")
        head = self.head()
        if head:
            lines.append("─" * 40)
            lines.append(f"ACTIVE NEXT: {head.next_action}")
        else:
            lines.append("─" * 40)
            lines.append("CHAIN COMPLETE")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "stones": [s.to_dict() for s in self.stones],
            "open": self.head().id if self.head() else None,
        }


def seed_agent_pr_cascade(chain: DominoChain) -> DominoChain:
    """Classic silent-failure cascade engineers live through."""
    chain.add(
        "Illusion of tests",
        "Agent said tests passed in chat — no artifact",
        next_action="run real tests and prove() exit code 0 (rung 1)",
    )
    chain.add(
        "Unreviewed skill power",
        "High-risk skill/MCP may be loaded without a bill of materials",
        next_action="audit skills and accept or refuse high risk (rung 2)",
    )
    chain.add(
        "Decision drift",
        "Change may violate locked project decisions",
        next_action="check decision capsule; lock new decision if intentional (rung 3)",
    )
    chain.add(
        "Non-replayable green",
        "Green once may not be stable",
        next_action="run replay check on proven steps (rung 4)",
    )
    chain.add(
        "Human attention misallocated",
        "Seniors review everything or nothing",
        next_action="run review triage; only must_review blocks merge (rung 5)",
    )
    return chain
