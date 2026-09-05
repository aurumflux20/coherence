"""Evidence checklist — which claims must carry proof before a merge.

A session records what an agent claimed and what it proved. Most claims can
wait for a human to read them. Some cannot: a claim that money moved, that a
deploy went out, that data was migrated or deleted, that a credential was
rotated. Those are *consequential* claims, and this module names them so the
gate can refuse a merge while any of them is still a sentence with no evidence.

A profile is just a set of words that marks a class of consequential claim.
Money is one profile. It is not what Coherence is for; it is one place where a
false "done" costs the most. Runtime prevention of a double charge is Seal's
job, not this module's — this only reads the record afterwards.
"""

from __future__ import annotations

from typing import Any, Iterable

from coherence import Coherence
from coherence.core.fact import Truth

PROFILES: dict[str, tuple[str, ...]] = {
    "money": (
        "stripe", "billing", "payment", "payout", "refund", "charge", "invoice",
        "subscription", "payroll", "transfer", "checkout", "paymentintent",
    ),
    "deploy": (
        "deploy", "release", "rollout", "rolled out", "shipped to prod",
        "production", "hotfix", "cut over",
    ),
    "data": (
        "migration", "migrate", "backfill", "drop table", "truncate", "delete",
        "purge", "schema change", "reindex",
    ),
    "security": (
        "auth", "token", "secret", "permission", "acl", "role", "credential",
        "rotate", "key rotation", "allowlist",
    ),
}

ALL = tuple(PROFILES)


def _matches(text: str, words: Iterable[str]) -> bool:
    t = (text or "").lower()
    return any(w in t for w in words)


def _is_open(f) -> bool:
    return (
        not f.evidence
        or f.truth in (Truth.ILLUSION, Truth.BLOCKED)
        or bool(f.meta.get("blocked"))
    )


def checklist(c: Coherence, profiles: Iterable[str] = ALL) -> dict[str, Any]:
    """Grade every consequential claim in the session against its evidence.

    Returns a report with per-profile counts and a flat list of gaps. `ok` is
    true only when no matched claim is open. A session with no matched claims
    is `ok` and says so — absence of consequential claims is not a finding.
    """
    chosen = [p for p in profiles if p in PROFILES]
    unknown = [p for p in profiles if p not in PROFILES]
    per: dict[str, dict[str, int]] = {}
    gaps: list[dict[str, str]] = []
    matched_total = proven_total = open_total = 0
    for name in chosen:
        words = PROFILES[name]
        matched = [f for f in c.facts if _matches(f"{f.claim} {f.evidence} {f.next}", words)]
        open_ = [f for f in matched if _is_open(f)]
        per[name] = {"matched": len(matched), "proven": len(matched) - len(open_), "open": len(open_)}
        matched_total += len(matched)
        proven_total += len(matched) - len(open_)
        open_total += len(open_)
        for f in open_:
            gaps.append({"profile": name, "claim": f.claim, "next": f.next,
                         "reason": f"{name} claim without durable evidence"})
    return {
        "profiles": per,
        "unknown_profiles": unknown,
        "matched": matched_total,
        "proven": proven_total,
        "open": open_total,
        "gaps": gaps,
        "ok": open_total == 0,
        "next": (
            "close every open consequential claim with prove-cmd before merge"
            if open_total
            else "no open consequential claims in this session"
        ),
    }


def format_checklist(report: dict[str, Any]) -> str:
    lines = ["Evidence checklist — consequential claims vs. proof"]
    for name, counts in report["profiles"].items():
        lines.append(f"  {name:<9} matched {counts['matched']:>3}   proven {counts['proven']:>3}   open {counts['open']:>3}")
    if report["unknown_profiles"]:
        lines.append(f"  (unknown profiles ignored: {', '.join(report['unknown_profiles'])})")
    for g in report["gaps"]:
        lines.append(f"  OPEN [{g['profile']}] {g['claim']}")
        if g.get("next"):
            lines.append(f"       next: {g['next']}")
    lines.append(("  OK — " if report["ok"] else "  BLOCK — ") + report["next"])
    return "\n".join(lines)
