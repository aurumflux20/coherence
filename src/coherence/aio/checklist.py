"""Phase-1 AIO checklist over a Coherence session.

Flags money-related claims that lack evidence. Does not call Stripe or admit payments.
"""

from __future__ import annotations

from typing import Any

from coherence import Coherence
from coherence.core.fact import Truth

MONEY_KEYWORDS = (
    "stripe",
    "billing",
    "payment",
    "payout",
    "refund",
    "charge",
    "invoice",
    "subscription",
    "payroll",
    "transfer",
    "checkout",
    "paymentintent",
)


def _looks_money(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in MONEY_KEYWORDS)


def aio_checklist(c: Coherence) -> dict[str, Any]:
    """Return Phase-1 evidence checklist for money-related facts."""
    money_facts = []
    for f in c.facts:
        blob = f"{f.claim} {f.evidence} {f.next}"
        if _looks_money(blob):
            money_facts.append(f)

    open_money = [
        f
        for f in money_facts
        if not f.evidence
        or f.truth in (Truth.ILLUSION, Truth.BLOCKED)
        or f.meta.get("blocked")
    ]
    proven_money = [f for f in money_facts if f.evidence and f not in open_money]

    gaps = []
    for f in open_money:
        gaps.append(
            {
                "claim": f.claim,
                "next": f.next,
                "reason": "money-related claim without durable evidence",
            }
        )

    return {
        "phase": 1,
        "pillar": "evidence",
        "not_included": [
            "runtime admission / exactly-once",
            "AP2 / network intent tokens",
            "provider settlement bind",
        ],
        "money_claims": len(money_facts),
        "money_proven": len(proven_money),
        "money_open": len(open_money),
        "gaps": gaps,
        "ok": len(open_money) == 0,
        "next": (
            "close money-path claims with prove-cmd before merge"
            if open_money
            else "Phase-1 evidence checklist clear for money-tagged claims "
            "(or no money-tagged claims in session)"
        ),
    }


def format_aio_checklist(report: dict[str, Any]) -> str:
    lines = [
        "AIO Phase 1 — evidence checklist (Coherence)",
        "=" * 48,
        f"money-tagged claims: {report['money_claims']}",
        f"  proven: {report['money_proven']}",
        f"  open:   {report['money_open']}",
        "",
        "NOT included: runtime admission · AP2 · settlement bind",
        "",
    ]
    if report["gaps"]:
        lines.append("Gaps:")
        for g in report["gaps"]:
            lines.append(f"  - {g['claim']!r} — {g['reason']}")
            if g.get("next"):
                lines.append(f"    next: {g['next']}")
        lines.append("")
    lines.append(f"NEXT: {report['next']}")
    lines.append(f"ok: {report['ok']}")
    return "\n".join(lines)
