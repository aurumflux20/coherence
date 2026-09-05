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
    print("COHERENCE · the law")
    print("=" * 50)
    print(LAW)
    print()
    print("Atom: Fact(claim, evidence, next)")
    print("  done      ⇔ evidence non-empty")
    print("  finished  ⇔ next non-empty (always)")
    print("  remember  ⇔ done only")
    print()
    print("Everything else is a view over the same Fact.")
    print("Docs: README.md")
    return 0


def demo() -> int:
    print()
    print("COHERENCE — one law, five kinds of Fact")
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
    print("COHERENCE EVOLVE — dominos + next steps + memory")
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

    # Integrity FIRST. If the session file was edited after the facts were
    # recorded, nothing else it says can be trusted — so a tampered chain is a
    # hard failure (exit 3) before any fact is read. This is the guard that
    # makes "agents can't fake green" true for the case that actually matters:
    # the policed agent editing its own session on disk.
    integ = store.verify()
    if integ["status"] == "tampered":
        print(json.dumps({"ok": False, "integrity": integ}, indent=2))
        print(f"CHECK FAIL: session tampered at entry {integ.get('position')} "
              f"— {integ.get('detail')}", file=sys.stderr)
        return 3

    c = store.load()
    report = build_report(c)
    report["integrity"] = integ
    print(json.dumps(report, indent=2))
    code = check_exit_code(c, strict=strict)
    if code == 0:
        note = "" if integ["status"] == "ok" else f" ({integ['status']})"
        print(f"CHECK PASS{note}", file=sys.stderr)
    elif code == 2:
        print("CHECK FAIL: no proven facts (strict)", file=sys.stderr)
    else:
        print("CHECK FAIL: open or blocked facts remain", file=sys.stderr)
    return code


def cmd_scope(argv: list[str]) -> int:
    """Blast radius: what the agent touched, and where this report's edge is."""
    p = argparse.ArgumentParser(prog="coherence scope")
    p.add_argument("transcript")
    p.add_argument("--json", action="store_true", dest="as_json")
    p.add_argument("--full", action="store_true", help="list every item, not a sample")
    args = p.parse_args(argv)
    from pathlib import Path as _P
    _p = _P(args.transcript)
    if not _p.exists() or not _p.is_file():
        print(f"error: not a readable file: {args.transcript}", file=sys.stderr)
        return 3
    from coherence.audit.scope import scope_transcript
    sc = scope_transcript(args.transcript)
    # Same rule `audit` follows: a file we could not read as a transcript must
    # never print like a clean, fully-readable report.
    if not sc.looks_like_transcript():
        print(f"error: {args.transcript} does not look like an agent transcript "
              f"(nothing parseable found).", file=sys.stderr)
        print("       Expected a Claude Code .jsonl session file. This is NOT "
              "a clean result.", file=sys.stderr)
        return 3
    if args.as_json:
        print(json.dumps({
            "commands": sc.commands, "bounded": sc.bounded(),
            "files": sorted(sc.files), "pushes": sorted(sc.pushes),
            "hosts": sorted(sc.hosts), "installs": sorted(sc.installs),
            "opaque": [{"line": a, "command": b, "why": c} for a, b, c in sc.opaque],
        }, indent=2))
        return sc.exit_code()

    def show(label, items):
        items = sorted(items)
        print(f"\n  {label} ({len(items)})")
        for i in (items if args.full else items[:8]):
            print(f"    {i}")
        if not args.full and len(items) > 8:
            print(f"    … {len(items) - 8} more (--full)")

    print(f"blast radius of {sc.commands} commands\n")
    show("files touched", sc.files)
    show("repos pushed", sc.pushes)
    show("network hosts contacted", sc.hosts)
    show("packages installed", sc.installs)

    print(f"\n  OPAQUE — effects this report CANNOT see ({len(sc.opaque)})")
    for seq, cmd, why in (sc.opaque if args.full else sc.opaque[:8]):
        print(f"    line {seq}: {cmd}")
        print(f"        why: {why}")
    if not args.full and len(sc.opaque) > 8:
        print(f"    … {len(sc.opaque) - 8} more (--full)")

    if sc.bounded():
        print(f"\nVERDICT: BOUNDED — {len(sc.opaque)} command(s) could do anything this")
        print("report cannot see. Everything above is what IS visible, not everything")
        print("that happened. Unknown is reported as unknown, never as 'nothing'.")
    else:
        print("\nVERDICT: fully readable — every command's effects were determinable.")
    return sc.exit_code()


def cmd_audit(argv: list[str]) -> int:
    """Audit an agent transcript: every checkable claim vs. what actually ran."""
    p = argparse.ArgumentParser(prog="coherence audit")
    p.add_argument("transcript", nargs="?",
                   help="agent session .jsonl (Claude Code format)")
    p.add_argument("--demo", action="store_true",
                   help="audit a bundled sample session — no setup needed; "
                        "shows all four verdicts, including a caught lie")
    p.add_argument("--json", action="store_true", dest="as_json")
    args = p.parse_args(argv)
    from coherence.audit.transcript import (
        audit_transcript, SUPPORTED, WEAK, UNSUPPORTED, CONTRADICTED)
    from pathlib import Path as _P
    if args.demo:
        args.transcript = str(_P(__file__).parent / "data" / "sample-session.jsonl")
        print(f"auditing bundled sample session\n")
    if not args.transcript:
        print("error: give a transcript path, or --demo to audit a bundled "
              "sample session.", file=sys.stderr)
        return 3
    _t = _P(args.transcript)
    if not _t.exists() or not _t.is_file():
        print(f"error: not a readable file: {args.transcript}", file=sys.stderr)
        return 3
    a = audit_transcript(args.transcript)
    # A file we could not read as a transcript must never print like a clean
    # audit. Say so, and exit non-zero.
    if not a.looks_like_transcript():
        print(f"error: {args.transcript} does not look like an agent transcript "
              f"(no commands or assistant messages found).", file=sys.stderr)
        print("       Expected a Claude Code .jsonl session file. This is NOT "
              "a clean result.", file=sys.stderr)
        return 3
    c = a.counts()
    if args.as_json:
        print(json.dumps({
            "commands": a.commands, "claims": len(a.claims), "counts": c,
            "findings": [vars(x) for x in a.claims
                         if x.verdict in (UNSUPPORTED, CONTRADICTED, WEAK)],
        }, indent=2))
        return a.exit_code()
    print(f"audited: {a.commands} commands, {len(a.claims)} checkable claims\n")
    print(f"  supported     {c[SUPPORTED]}")
    print(f"  weak evidence {c[WEAK]}   (piped exit codes — pytest | tail class)")
    print(f"  unsupported   {c[UNSUPPORTED]}   (claims resting on nothing)")
    print(f"  CONTRADICTED  {c[CONTRADICTED]}   (claimed success; its own transcript says failure)")
    for x in a.claims:
        if x.verdict == CONTRADICTED:
            print(f"\n  LIE at line {x.seq} [{x.kind}]: \"{x.text}\"")
            print(f"      evidence against: {x.evidence}")
    for x in a.claims:
        if x.verdict == UNSUPPORTED:
            print(f"\n  unsupported line {x.seq} [{x.kind}]: \"{x.text[:100]}\"")
    print(f"\nexit {a.exit_code()}  (0 all supported · 1 unsupported · 2 contradicted)")
    return a.exit_code()


def cmd_tamper_demo(argv: list[str]) -> int:
    """Show, in one command, the thing that is hard to believe from prose:
    a forged 'proven' in the session file is caught.

    Runs entirely in a throwaway temp directory — touches nothing of yours.
    """
    import tempfile
    from coherence.ci.session import SessionStore

    with tempfile.TemporaryDirectory() as td:
        sess = Path(td) / "session.json"
        store = SessionStore(sess)

        print("1. An agent runs a check. It FAILS — so no proof is recorded.")
        store.prove_command("false", claim="test suite")
        print(f"   coherence check  ->  exit {cmd_exit(sess)}   (open fact, no evidence)\n")

        print("2. The agent edits its own session file to claim it passed.")
        data = json.loads(sess.read_text())
        data["facts"][0]["evidence"] = "exit_code=0 output_digest=deadbeef"
        data["facts"][0]["next"] = "chain complete"
        sess.write_text(json.dumps(data, indent=2))
        print('   forged: evidence = "exit_code=0 ..."\n')

        print("3. The check runs again. The hash chain does not match.")
        code = cmd_exit(sess)
        v = store.verify()
        print(f"   coherence check  ->  exit {code}   {v['status'].upper()} at entry {v.get('position')}")
        print(f"   {v.get('detail')}\n")

        if code != 3:
            print("UNEXPECTED: tampering was not caught", file=sys.stderr)
            return 1
        print("A forged green is caught. That is the whole idea.")
        print("Exit codes: 0 pass · 1 open facts · 2 empty · 3 tampered")
    return 0


def cmd_exit(session: Path) -> int:
    """Run the real check logic quietly and return only its exit code."""
    from coherence.ci.session import SessionStore, check_exit_code
    store = SessionStore(session)
    integ = store.verify()
    if integ["status"] == "tampered":
        return 3
    return check_exit_code(store.load(), strict=True)


def cmd_checklist(argv: list[str]) -> int:
    """Consequential claims (money, deploy, data, security) must carry proof."""
    from coherence.checklist import ALL, checklist, format_checklist

    p = argparse.ArgumentParser(prog="coherence checklist")
    p.add_argument("--session", default=str(DEFAULT_SESSION))
    p.add_argument("--profile", default="all", help="comma-separated profiles, or all")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    profiles = ALL if args.profile == "all" else tuple(x.strip() for x in args.profile.split(",") if x.strip())
    report = checklist(SessionStore(args.session).load(), profiles)
    print(json.dumps(report, indent=2) if args.json else format_checklist(report))
    return 0 if report["ok"] else 1


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
    if cmd in ("health", "doctor", "status"):
        from coherence.health import plain_english, run_health, write_report

        p = argparse.ArgumentParser(prog="coherence health")
        p.add_argument("--out", default="", help="write JSON report path")
        p.add_argument("--memory", default="", help="optional evolution memory to verify")
        p.add_argument("--no-storm", action="store_true")
        args = p.parse_args(rest)
        report = run_health(
            include_storm=not args.no_storm,
            memory_path=Path(args.memory) if args.memory else None,
        )
        print(plain_english(report))
        if args.out:
            write_report(report, Path(args.out))
            print(f"wrote {args.out}")
        raise SystemExit(0 if report.ok else 1)
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
    if cmd == "scope":
        raise SystemExit(cmd_scope(rest))
    if cmd == "audit":
        raise SystemExit(cmd_audit(rest))
    if cmd in ("tamper-demo", "tamper_demo", "tamper"):
        raise SystemExit(cmd_tamper_demo(rest))
    if cmd == "keygen":
        from coherence.attest import keygen
        ap = argparse.ArgumentParser(prog="coherence keygen"); ap.add_argument("--out", default=".coherence/keys")
        a = ap.parse_args(rest); k, pub = keygen(Path(a.out))
        print(f"private key: {k}\npublic key:  {pub}\nshare the public key; never the private one."); raise SystemExit(0)
    if cmd == "attest":
        from coherence.attest import attest
        ap = argparse.ArgumentParser(prog="coherence attest")
        ap.add_argument("--session", default=".coherence/session.json"); ap.add_argument("--key", default=".coherence/keys/coherence-attest.key")
        ap.add_argument("--out", default=".coherence/attestation.json"); ap.add_argument("--issuer", default="")
        ap.add_argument("--anchor", choices=["rekor"], default=None, help="also submit to a public transparency log")
        ap.add_argument("--pub", default=None, help="public key (needed for --anchor); defaults beside --key")
        a = ap.parse_args(rest); r = attest(Path(a.session), Path(a.key), Path(a.out), issuer=a.issuer)
        if a.anchor == "rekor":
            from coherence.attest.anchor import anchor
            pub = Path(a.pub) if a.pub else Path(a.key).with_suffix(".pub")
            r["anchor"] = anchor(Path(a.out), pub)
        print(json.dumps(r, indent=2)); raise SystemExit(0 if r.get("anchor", {}).get("status", "anchored") in ("anchored", "exists") else 1)
    if cmd == "verify":
        from coherence.attest import verify
        ap = argparse.ArgumentParser(prog="coherence verify"); ap.add_argument("envelope")
        ap.add_argument("--pub", required=True); ap.add_argument("--session", default=None)
        ap.add_argument("--rekor", default=None, help="sidecar written by attest --anchor rekor; re-checks the log entry")
        a = ap.parse_args(rest); r = verify(a.envelope, a.pub, a.session if a.session else None)
        ok = r.get("status") == "verified"
        if a.rekor:
            from coherence.attest.anchor import check_anchor
            r["anchor"] = check_anchor(a.envelope, a.rekor)
            ok = ok and r["anchor"].get("status") == "anchored"
        print(json.dumps(r, indent=2)); raise SystemExit(0 if ok else 1)
    if cmd in ("attest-selftest", "attest_selftest"):
        from coherence.attest import selftest
        r = selftest(); print(json.dumps(r, indent=2)); raise SystemExit(0 if r.get("instrument") == "honest" else 3)
    if cmd == "checklist":
        raise SystemExit(cmd_checklist(rest))
    if cmd == "report":
        raise SystemExit(cmd_report(rest))
    if cmd in ("-h", "--help", "help"):
        print(
            "Usage: python -m coherence <command>\n"
            "  law | demo | evolve | storm | health\n"
            "  said CLAIM --next NEXT\n"
            "  prove-cmd 'pytest -q'\n"
            "  tamper-demo   (10s: forge a green, watch it get caught)\n"
            "  audit FILE.jsonl   (agent transcript: claims vs. what actually ran)\n"
            "  scope FILE.jsonl   (blast radius: what it touched + what we cannot see)\n"
            "  check [--no-strict]\n"
            "  report [--json] [--out file.md]\n"
            "  checklist [--profile money,deploy,data,security|all] [--json]   (consequential claims must carry proof)\n"
            "  keygen [--out DIR]                (issuer keypair; extra: coherence-check[attest])\n"
            "  attest [--session P] [--key P] [--anchor rekor]   (sign the chain head; optionally timestamp it in Sigstore Rekor)\n"
            "  verify ENVELOPE --pub P [--session P] [--rekor SIDECAR]  (record + public key only; --rekor re-checks the log)\n"
            "  attest-selftest                   (mutation control: tampered/wrong-key/edited must fail)\n"
        )
        raise SystemExit(0)
    print(f"Unknown command: {cmd}. Try: law | demo | prove-cmd | check | report", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
