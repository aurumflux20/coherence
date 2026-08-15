"""python -m coherence demo|evolve|law|prove-cmd|check|report"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from coherence import Coherence
from coherence.ci.session import (
    DEFAULT_SESSION,
    SessionStore,
    build_report,
    check_exit_code,
    report_markdown,
)


def law() -> int:
    from coherence.core.fact import LAW

    print()
    print("COHERENCE · 320 IQ law")
    print("=" * 50)
    print(LAW)
    print()
    print("Atom: Fact(claim, evidence, next)")
    print("  done      ⇔ evidence non-empty")
    print("  finished  ⇔ next non-empty (always)")
    print("  remember  ⇔ done only")
    print()
    print("Everything else is costume.")
    print("Docs: docs/320IQ.md")
    return 0


def demo() -> int:
    print()
    print("COHERENCE — one law, five costumes")
    print("=" * 50)
    from coherence.core.fact import LAW

    print(LAW)
    print()

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
    print()
    print("COHERENCE EVOLVE — dominos + Gilbert next + memory")
    print("=" * 56)

    mem = Path(tempfile.gettempdir()) / "coherence_evolve_demo.json"
    if mem.exists():
        mem.unlink()

    c1 = Coherence(title="session-1", memory_path=mem, seed_cascade=True)
    print(c1.dominos.plain_english())
    print()

    head = c1.dominos.head()
    assert head is not None
    print(f"ACTIVE: {head.title}")
    print(f"GILBERT NEXT: {head.next_action}")
    print()

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


def cmd_prove(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="coherence prove-cmd")
    p.add_argument("command", help="shell command to run and prove")
    p.add_argument("--session", default=str(DEFAULT_SESSION))
    p.add_argument("--claim", default="")
    p.add_argument(
        "--next",
        default="close remaining open facts or chain complete",
        dest="next_action",
    )
    args = p.parse_args(argv)
    store = SessionStore(args.session)
    c, fact, code = store.prove_command(
        args.command,
        claim=args.claim or None,
        next_action=args.next_action,
    )
    print(fact.plain_english())
    print(f"session: {store.path}  facts_done={len(c.done_facts())} open={len(c.open_facts())}")
    # CI: non-zero if command failed
    return 0 if code == 0 else 1


def cmd_said(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="coherence said")
    p.add_argument("claim")
    p.add_argument("--next", required=True, dest="next_action")
    p.add_argument("--session", default=str(DEFAULT_SESSION))
    args = p.parse_args(argv)
    store = SessionStore(args.session)
    c = store.load()
    f = c.said(args.claim, args.next_action)
    store.save(c)
    print(f.plain_english())
    return 0


def cmd_check(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="coherence check")
    p.add_argument("--session", default=str(DEFAULT_SESSION))
    p.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="fail if zero proven facts (default)",
    )
    p.add_argument("--no-strict", action="store_true", help="allow empty session")
    args = p.parse_args(argv)
    strict = not args.no_strict
    store = SessionStore(args.session)
    c = store.load()
    report = build_report(c)
    print(json.dumps(report, indent=2))
    code = check_exit_code(c, strict=strict)
    if code == 0:
        print("CHECK PASS", file=sys.stderr)
    elif code == 2:
        print("CHECK FAIL: no proven facts (strict)", file=sys.stderr)
    else:
        print("CHECK FAIL: open or blocked facts remain", file=sys.stderr)
    return code


def cmd_report(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="coherence report")
    p.add_argument("--session", default=str(DEFAULT_SESSION))
    p.add_argument("--json", action="store_true")
    p.add_argument("--out", default="", help="write markdown or json to file")
    args = p.parse_args(argv)
    store = SessionStore(args.session)
    c = store.load()
    if args.json:
        body = json.dumps(build_report(c), indent=2)
    else:
        body = report_markdown(c)
    if args.out:
        Path(args.out).write_text(body + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(body)
    return 0


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(demo())
    cmd = argv[0].lower()
    rest = argv[1:]
    if cmd in ("demo", "run"):
        raise SystemExit(demo())
    if cmd in ("evolve", "domino", "flywheel"):
        raise SystemExit(evolve_demo())
    if cmd in ("law", "320", "iq"):
        raise SystemExit(law())
    if cmd in ("storm", "proof", "storm-proof"):
        # Hostile proof harness (EffectFence/Seal style)
        from pathlib import Path as _P
        import runpy

        storm = _P(__file__).resolve().parents[2] / "storm.py"
        if not storm.exists():
            # installed wheel: look beside package or cwd
            storm = _P.cwd() / "storm.py"
        if storm.exists():
            raise SystemExit(runpy.run_path(str(storm), run_name="__main__") or 0)
        print("storm.py not found — run from repo: python storm.py", file=sys.stderr)
        raise SystemExit(2)
    if cmd in ("prove-cmd", "prove_cmd", "prove"):
        raise SystemExit(cmd_prove(rest))
    if cmd == "said":
        raise SystemExit(cmd_said(rest))
    if cmd == "check":
        raise SystemExit(cmd_check(rest))
    if cmd == "report":
        raise SystemExit(cmd_report(rest))
    if cmd in ("-h", "--help", "help"):
        print(
            "Usage: python -m coherence <command>\n"
            "  law | demo | evolve | storm\n"
            "  said CLAIM --next NEXT\n"
            "  prove-cmd 'pytest -q'\n"
            "  check [--no-strict]\n"
            "  report [--json] [--out file.md]\n"
        )
        raise SystemExit(0)
    print(f"Unknown command: {cmd}. Try: law | demo | prove-cmd | check | report", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
