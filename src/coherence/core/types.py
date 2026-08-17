"""Shared spine for all Coherence rungs — CLAIM / PROOF / NEXT."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class Truth(str, Enum):
    """Closed set — no ambiguous free-text-only outcomes."""

    CLAIMED = "claimed"  # said, not proven
    PROVEN = "proven"  # evidence attached
    ILLUSION = "illusion"  # treated as proven but no evidence
    BLOCKED = "blocked"
    OPEN = "open"


def digest(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def digest_full(obj: Any) -> str:
    """Untruncated SHA-256. Use for tamper-evidence (chain links), where the
    16-char id-grade digest above would be too easy to collide on purpose."""
    raw = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass(frozen=True)
class Artifact:
    """Something checkable: command output, file hash, URL, log blob ref."""

    kind: str  # e.g. "cmd_exit", "file_sha", "log"
    value: str
    meta: dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        return digest({"kind": self.kind, "value": self.value, "meta": self.meta})


@dataclass
class Record:
    """Universal unit every rung can emit or consume."""

    id: str
    rung: int  # 1..5
    kind: str  # step | skill | decision | replay | review
    truth: Truth
    summary: str
    next_action: str
    claimed: str = ""
    proven: str = ""
    artifacts: list[Artifact] = field(default_factory=list)
    links: list[str] = field(default_factory=list)  # other record ids
    created_at: float = field(default_factory=time.time)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["truth"] = self.truth.value
        return d

    def plain_english(self) -> str:
        arts = ", ".join(a.kind for a in self.artifacts) or "none"
        return (
            f"[rung {self.rung} · {self.kind}] {self.truth.value.upper()}\n"
            f"  {self.summary}\n"
            f"  CLAIMED: {self.claimed or '—'}\n"
            f"  PROVEN:  {self.proven or '—'}\n"
            f"  artifacts: {arts}\n"
            f"  NEXT: {self.next_action}"
        )


@dataclass
class Bundle:
    """One agent session / PR / run — all rungs hang off this."""

    id: str
    title: str
    records: list[Record] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add(self, record: Record) -> Record:
        self.records.append(record)
        return record

    def by_rung(self, rung: int) -> list[Record]:
        return [r for r in self.records if r.rung == rung]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.records:
            out[r.truth.value] = out.get(r.truth.value, 0) + 1
        return out

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "counts": self.counts(),
            "records": [r.to_dict() for r in self.records],
        }
