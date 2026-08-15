"""Rung 2 — Skill / MCP bill of materials + simple risk."""

from __future__ import annotations

from typing import Any, Iterable

from coherence.core.types import Artifact, Bundle, Record, Truth, digest, new_id

# Capabilities that raise risk when a skill asks for them
_HOT = frozenset(
    {
        "shell",
        "exec",
        "network",
        "net",
        "filesystem_write",
        "fs_write",
        "secrets",
        "env",
        "browser",
        "email",
        "payment",
    }
)


class SkillAuditor:
    def __init__(self, bundle: Bundle) -> None:
        self.bundle = bundle

    def audit(
        self,
        name: str,
        capabilities: Iterable[str],
        *,
        source: str = "unknown",
    ) -> Record:
        caps = sorted({c.strip().lower() for c in capabilities if c and c.strip()})
        hot = [c for c in caps if c in _HOT or any(h in c for h in _HOT)]
        risk = "high" if hot else ("medium" if caps else "low")
        bill = {
            "name": name,
            "source": source,
            "capabilities": caps,
            "hot": hot,
            "risk": risk,
        }
        art = Artifact(kind="skill_bill", value=digest(bill), meta=bill)
        if risk == "high":
            truth = Truth.CLAIMED  # install is a claim until human accepts
            nxt = (
                f"HIGH risk skill {name!r} wants {hot} — "
                "human must accept install or refuse"
            )
            proven = f"bill={art.fingerprint()} risk=high"
        else:
            truth = Truth.PROVEN
            nxt = f"skill {name!r} bill recorded; ok to load under policy"
            proven = f"bill={art.fingerprint()} risk={risk}"

        rec = Record(
            id=new_id("skl"),
            rung=2,
            kind="skill",
            truth=truth,
            summary=f"skill audit: {name}",
            claimed=f"install {name} from {source}",
            proven=proven,
            artifacts=[art],
            next_action=nxt,
            meta=bill,
        )
        return self.bundle.add(rec)
