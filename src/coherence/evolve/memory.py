"""Evolution memory — Coherence gets more coherent as problems are solved.

Append-only lessons. Loaded on next session so the tool does not forget.
Not ML magic: structured memory + reuse. Domino-aware.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from coherence.core.types import Artifact, Bundle, Record, Truth, digest, new_id


@dataclass
class Lesson:
    """One solved problem that should change future behavior."""

    id: str
    problem: str
    lesson: str
    proof: str
    next_domino: str
    source_domino: str = ""
    uses: int = 0
    created_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Lesson":
        return Lesson(
            id=d["id"],
            problem=d.get("problem", ""),
            lesson=d.get("lesson", ""),
            proof=d.get("proof", ""),
            next_domino=d.get("next_domino", ""),
            source_domino=d.get("source_domino", ""),
            uses=int(d.get("uses", 0)),
            created_at=float(d.get("created_at", time.time())),
            tags=list(d.get("tags") or []),
        )


class EvolutionMemory:
    """Persistent (optional) lesson store that compounds with use."""

    def __init__(
        self,
        bundle: Bundle,
        path: Optional[str | Path] = None,
    ) -> None:
        self.bundle = bundle
        self.path = Path(path) if path else None
        self.lessons: list[Lesson] = []
        if self.path and self.path.exists():
            self.load()

    def learn(
        self,
        *,
        problem: str,
        lesson: str,
        proof: str,
        next_domino: str,
        source_domino: str = "",
        tags: Optional[list[str]] = None,
    ) -> Lesson:
        # 320 IQ: nothing is remembered unless it was done (has evidence)
        if not (proof or "").strip():
            raise ValueError(
                "LAW: nothing is remembered unless it was done — proof/evidence required"
            )
        if not lesson.strip():
            raise ValueError("Gilbert/Evolution: empty lesson — nothing to remember")
        if not next_domino.strip():
            raise ValueError(
                "Gilbert: learning requires next_domino "
                "(what the cascade needs next, or 'chain complete')"
            )
        L = Lesson(
            id=new_id("les"),
            problem=problem.strip(),
            lesson=lesson.strip(),
            proof=proof.strip(),
            next_domino=next_domino.strip(),
            source_domino=source_domino,
            tags=list(tags or []),
        )
        self.lessons.append(L)
        self._persist()

        art = Artifact(
            kind="lesson",
            value=digest(L.to_dict()),
            meta=L.to_dict(),
        )
        self.bundle.add(
            Record(
                id=new_id("evo"),
                rung=7,
                kind="evolution",
                truth=Truth.PROVEN,
                summary=f"learned: {L.lesson[:80]}",
                claimed=problem,
                proven=proof,
                artifacts=[art],
                next_action=f"apply in future sessions → next risk: {L.next_domino}",
                meta={"lesson_id": L.id, "lesson": L.to_dict()},
            )
        )
        return L

    def apply_hints(self, problem_text: str) -> list[Lesson]:
        """Return past lessons that may apply (simple substring match v0)."""
        q = problem_text.lower()
        hits = []
        for L in self.lessons:
            blob = f"{L.problem} {L.lesson} {' '.join(L.tags)}".lower()
            if any(tok in blob for tok in q.split() if len(tok) > 3):
                L.uses += 1
                hits.append(L)
        if hits:
            self._persist()
            self.bundle.add(
                Record(
                    id=new_id("evo"),
                    rung=7,
                    kind="evolution",
                    truth=Truth.CLAIMED,
                    summary=f"evolution memory matched {len(hits)} lesson(s)",
                    claimed=problem_text,
                    proven=f"lesson_ids={[h.id for h in hits]}",
                    next_action=(
                        hits[0].next_domino
                        if hits
                        else "no next — add a lesson when you solve this"
                    ),
                    meta={"matched": [h.to_dict() for h in hits]},
                )
            )
        return hits

    def load(self) -> None:
        if not self.path or not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.lessons = [Lesson.from_dict(x) for x in data.get("lessons", [])]

    def _persist(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": time.time(),
            "lessons": [L.to_dict() for L in self.lessons],
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def stats(self) -> dict[str, Any]:
        return {
            "lessons": len(self.lessons),
            "total_uses": sum(L.uses for L in self.lessons),
            "path": str(self.path) if self.path else None,
        }

    def plain_english(self) -> str:
        if not self.lessons:
            return "EVOLUTION MEMORY: empty — solve a domino to teach Coherence"
        lines = [f"EVOLUTION MEMORY · {len(self.lessons)} lesson(s)", "─" * 40]
        for L in self.lessons[-10:]:
            lines.append(f"  • {L.lesson}")
            lines.append(f"    from: {L.problem[:60]}")
            lines.append(f"    NEXT: {L.next_domino}")
            lines.append(f"    uses: {L.uses}")
        return "\n".join(lines)
