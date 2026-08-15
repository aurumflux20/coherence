"""python -m coherence demo"""

from __future__ import annotations

import sys

from coherence import Coherence, Truth


def demo() -> int:
    print()
    print("COHERENCE — five rungs, one reality")
    print("=" * 50)

    c = Coherence(title="demo-pr-agent-fix")

    # Rung 2 — what did we install?
    c.skills.audit(
        "web-search-skill",
        ["network", "read"],
        source="marketplace:example",
    )
    c.skills.audit(
        "shell-runner",
        ["shell", "filesystem_write"],
        source="random-gist",
    )

    # Rung 3 — project truths
    c.decisions.lock(
        "auth-boundary",
        "MUST NOT rewrite auth without human; tests must stay green",
        by="staff-eng",
    )

    # Rung 1 — claims vs proofs
    c.claimproof.illusion("unit tests", "agent said tests passed in chat")
    c.claimproof.claim("refactored utils", "looks cleaner", next_action="add proof")
    c.claimproof.cmd("unit tests", "pytest -q", exit_code=0)
    c.claimproof.cmd("typecheck", "mypy src", exit_code=1)

    # Rung 3 check agent story
    c.decisions.check_violation(
        "auth-boundary",
        "I did not rewrite auth; only utils",
    )

    # Rung 4 — replay surface
    c.replay.check()

    # Rung 5 — triage
    triage = c.review.triage()
    guard = c.require_coherent()

    print(c.plain_english())
    print("summary:", c.summary())
    print()
    print(f"triage priority: {triage.meta.get('priority')}")
    print(f"coherence guard: {guard.summary if guard else 'ok'}")
    print()
    print("PASS — rungs 1–5 share one Bundle")
    print("Docs: docs/ARCHITECTURE.md")
    return 0


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = (argv[0] if argv else "demo").lower()
    if cmd in ("demo", "run"):
        raise SystemExit(demo())
    if cmd in ("-h", "--help"):
        print("Usage: python -m coherence demo")
        raise SystemExit(0)
    print("Unknown command. Try: demo", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
