"""python -m coherence demo|evolve"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from coherence import Coherence, Truth


def demo() -> int:
    print()
    print("COHERENCE — five rungs, one reality")
    print("=" * 50)

    c = Coherence(title="demo-pr-agent-fix")
    c.skills.audit("web-search-skill", ["network", "read"], source="marketplace:example")
    c.skills.audit("shell-runner", ["shell", "filesystem_write"], source="random-gist")
    c.decisions.lock(
        "auth-boundary",
        "MUST NOT rewrite auth without human; tests must stay green",
        by="staff-eng",
    )
    c.claimproof.illusion("unit tests", "agent said tests passed in chat")
    c.claimproof.claim("refactored utils", "looks cleaner", next_action="add proof")
    c.claimproof.cmd("unit tests", "pytest -q", exit_code=0)
    c.claimproof.cmd("typecheck", "mypy src", exit_code=1)
    c.decisions.check_violation("auth-boundary", "I did not rewrite auth; only utils")
    c.replay.check()
    triage = c.review.triage()
    guard = c.require_coherent()

    print(c.plain_english())
    print("summary:", c.summary())
    print(f"triage priority: {triage.meta.get('priority')}")
    print(f"coherence guard: {guard.summary if guard else 'ok'}")
    print("PASS — rungs 1–5 share one Bundle")
    return 0


def evolve_demo() -> int:
    """Show flywheel: cascade → prove → solve domino → memory → next session."""
    print()
    print("COHERENCE EVOLVE — dominos + Gilbert next + memory")
    print("=" * 56)

    mem = Path(tempfile.gettempdir()) / "coherence_evolve_demo.json"
    if mem.exists():
        mem.unlink()

    # ── Session 1: face the cascade ───────────────────────────────────────
    c1 = Coherence(title="session-1", memory_path=mem, seed_cascade=True)
    print(c1.dominos.plain_english())
    print()

    head = c1.dominos.head()
    assert head is not None
    print(f"ACTIVE: {head.title}")
    print(f"GILBERT NEXT: {head.next_action}")
    print()

    # Solve first domino with real proof (rung 1)
    proof_rec = c1.claimproof.cmd("unit tests", "pytest -q", exit_code=0)
    c1.solve_domino(
        head.id,
        proof=f"cmd proven {proof_rec.proven}",
        lesson="Never trust chat 'tests passed' — require cmd_exit artifact",
        proof_record_id=proof_rec.id,
        tags=["tests", "illusion"],
    )
    print("After knock #1:")
    print(c1.dominos.plain_english())
    print()
    print(c1.evolve.plain_english())
    print()

    # Knock second with skill audit
    head2 = c1.dominos.head()
    assert head2 is not None
    sk = c1.skills.audit("shell-runner", ["shell"], source="gist")
    c1.solve_domino(
        head2.id,
        proof=f"skill bill {sk.proven}",
        lesson="High-risk skills must surface on the same report as test proof",
        proof_record_id=sk.id,
        tags=["skills"],
    )

    print("Session 1 summary:", c1.summary())
    print()

    # ── Session 2: memory loads — more coherent start ─────────────────────
    c2 = Coherence(title="session-2", memory_path=mem)
    print("SESSION 2 — evolution memory loaded")
    print(c2.evolve.plain_english())
    hints = c2.evolve.apply_hints("agent said tests passed in chat")
    print(f"hints for 'tests passed in chat': {len(hints)}")
    if hints:
        print(f"  lesson: {hints[0].lesson}")
        print(f"  GILBERT NEXT from memory: {hints[0].next_domino}")
    print()
    print("stats:", c2.evolve.stats())
    print()
    print("PASS — use → solve → learn → next session more coherent")
    print("Docs: docs/EVOLUTION-AND-DOMINOS.md")
    return 0


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = (argv[0] if argv else "demo").lower()
    if cmd in ("demo", "run"):
        raise SystemExit(demo())
    if cmd in ("evolve", "domino", "flywheel"):
        raise SystemExit(evolve_demo())
    if cmd in ("-h", "--help"):
        print("Usage: python -m coherence demo|evolve")
        raise SystemExit(0)
    print("Unknown command. Try: demo | evolve", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
