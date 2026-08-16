"""CI session file — Facts on disk for PR checks and badges.

Ship feature: agents/scripts write a session JSON; CI runs `coherence check`.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from coherence.core.fact import Fact, FactKind
from coherence.core.spine import Coherence
from coherence.core.types import Artifact, Truth, digest


DEFAULT_SESSION = Path(".coherence/session.json")


def _fact_to_dict(f: Fact) -> dict[str, Any]:
    return {
        "id": f.id,
        "claim": f.claim,
        "evidence": f.evidence,
        "next": f.next,
        "kind": f.kind.value,
        "meta": f.meta,
        "created_at": f.created_at,
        "artifacts": [
            {"kind": a.kind, "value": a.value, "meta": a.meta} for a in f.artifacts
        ],
    }


def _fact_from_dict(d: dict[str, Any]) -> Fact:
    arts = [
        Artifact(kind=a["kind"], value=a["value"], meta=a.get("meta") or {})
        for a in d.get("artifacts") or []
    ]
    return Fact.make(
        d["claim"],
        d["next"],
        evidence=d.get("evidence") or "",
        kind=FactKind(d.get("kind") or "step"),
        artifacts=arts,
        meta=d.get("meta") or {},
        fact_id=d.get("id"),
    )


class SessionStore:
    """Persist Coherence facts for CI across steps."""

    def __init__(self, path: Path | str = DEFAULT_SESSION) -> None:
        self.path = Path(path)

    def load(self) -> Coherence:
        title = "ci-session"
        facts: list[Fact] = []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            title = data.get("title") or title
            for raw in data.get("facts") or []:
                facts.append(_fact_from_dict(raw))
        c = Coherence(title=title)
        for f in facts:
            c.note(f)
        return c

    def save(self, c: Coherence) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "title": c.bundle.title,
            "updated_at": time.time(),
            "law": c.LAW,
            "facts": [_fact_to_dict(f) for f in c.facts],
            "summary": {
                "done": len(c.done_facts()),
                "open": len(c.open_facts()),
            },
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def prove_command(
        self,
        command: str,
        *,
        claim: Optional[str] = None,
        next_action: str = "review remaining open facts or chain complete",
        cwd: Optional[Path] = None,
    ) -> tuple[Coherence, Fact, int]:
        """Run a shell command; record PROVEN or BLOCKED Fact; save session."""
        c = self.load()
        claim = claim or f"ran: {command}"
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=600,
            )
            code = int(proc.returncode)
        except subprocess.TimeoutExpired:
            f = c.note(
                Fact.make(
                    claim,
                    next_action,
                    evidence="",
                    kind=FactKind.STEP,
                    meta={"blocked": True, "timeout": True, "command": command},
                )
            )
            # mark as blocked via meta — evidence empty = not done
            self.save(c)
            return c, f, 124

        if code == 0:
            out_d = digest((proc.stdout or "")[:2000])
            art = Artifact(
                kind="cmd_exit",
                value=f"{command} → 0",
                meta={"stdout_digest": out_d},
            )
            f = c.prove(
                claim,
                evidence=f"exit_code=0 digest={out_d}",
                next=next_action,
                kind=FactKind.STEP,
                artifact=art,
                meta={"command": command},
            )
        else:
            f = c.note(
                Fact.make(
                    claim,
                    next=f"fix command (exit {code}); re-run prove",
                    evidence="",
                    kind=FactKind.STEP,
                    meta={
                        "blocked": True,
                        "exit_code": code,
                        "command": command,
                    },
                )
            )
        self.save(c)
        return c, f, code


def build_report(c: Coherence) -> dict[str, Any]:
    """Machine report for badges / PR comments."""
    done = c.done_facts()
    open_f = c.open_facts()
    blocked = [f for f in c.facts if f.meta.get("blocked") or f.truth == Truth.BLOCKED]
    illusions = [f for f in c.facts if f.truth == Truth.ILLUSION]
    ok = len(open_f) == 0 and len(blocked) == 0 and len(done) > 0
    # soft ok: no open and no blocked even if zero facts
    soft_ok = len(open_f) == 0 and len(blocked) == 0
    return {
        "ok": ok,
        "soft_ok": soft_ok,
        "law": c.LAW,
        "title": c.bundle.title,
        "done": len(done),
        "open": len(open_f),
        "blocked": len(blocked),
        "illusions": len(illusions),
        "total_facts": len(c.facts),
        "open_next": [f.next for f in open_f[:10]],
        "badge_label": "coherence",
        "badge_message": (
            f"{len(done)} proven · {len(open_f)} open"
            if c.facts
            else "no facts"
        ),
        "badge_color": "green" if soft_ok and len(done) > 0 else (
            "yellow" if soft_ok else "red"
        ),
        "shields_url": _shields(
            len(done), len(open_f), soft_ok and len(done) > 0
        ),
    }


def _shields(done: int, open_n: int, green: bool) -> str:
    msg = f"{done}_proven-{open_n}_open"
    color = "brightgreen" if green else ("yellow" if open_n == 0 else "red")
    return (
        f"https://img.shields.io/badge/coherence-{msg}-{color}"
    )


def report_markdown(c: Coherence) -> str:
    r = build_report(c)
    lines = [
        "## Coherence report",
        "",
        f"![coherence]({r['shields_url']})",
        "",
        f"**{r['done']} proven** · **{r['open']} open** · "
        f"**{r['blocked']} blocked** · **{r['illusions']} illusion**",
        "",
        f"> {r['law']}",
        "",
    ]
    if r["open_next"]:
        lines.append("### Open — what to do next")
        for n in r["open_next"]:
            lines.append(f"- {n}")
        lines.append("")
    if r["soft_ok"] and r["done"] > 0:
        lines.append("**Status:** green — no open facts.")
    elif r["soft_ok"]:
        lines.append("**Status:** empty session — record facts with `coherence prove-cmd`.")
    else:
        lines.append("**Status:** red — close open/blocked facts before merge.")
    lines.append("")
    lines.append("_Generated by [aurumflux20/coherence](https://github.com/aurumflux20/coherence)_")
    return "\n".join(lines)


def check_exit_code(c: Coherence, *, strict: bool = True) -> int:
    """0 = pass, 1 = open/blocked facts, 2 = empty under strict."""
    r = build_report(c)
    if r["open"] or r["blocked"]:
        return 1
    if strict and r["done"] == 0:
        return 2
    return 0
