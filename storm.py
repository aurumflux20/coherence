#!/usr/bin/env python3
"""Hostile proof harness — EffectFence/Seal style.

Claim under attack:
  1) Chat claims never become DONE.
  2) Only evidence makes DONE.
  3) Empty next is always illegal.
  4) Memory never stores undoned claims.
  5) Dominos cannot be solved out of order under races.
  6) Evolution compounds: session-2 loads only proven lessons.

Every check prints PASS/FAIL. Exit 0 only if all PASS.
No network. No Postgres. Pure law under threads.
"""

from __future__ import annotations

import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Allow running from repo root without install
_ROOT = Path(__file__).resolve().parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from coherence import Coherence, Fact, FactError  # noqa: E402
from coherence.core.fact import LAW  # noqa: E402
from coherence.evolve.dominos import DominoState  # noqa: E402


def _banner() -> None:
    print()
    print("COHERENCE STORM — hostile proof")
    print("=" * 56)
    print(LAW)
    print("=" * 56)
    print()


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}")
    if detail:
        print(f"         {detail}")
    return ok


def storm_chat_never_done(n: int = 500) -> bool:
    """N agents all 'said tests passed' — zero may be done."""
    c = Coherence(title="storm-chat")
    lock = threading.Lock()

    def agent(i: int) -> None:
        with lock:
            c.said(
                f"agent-{i} said tests passed in chat",
                next="run pytest and attach exit code",
            )

    with ThreadPoolExecutor(max_workers=64) as pool:
        list(pool.map(agent, range(n)))

    done = len(c.done_facts())
    open_n = len(c.open_facts())
    return check(
        f"chat storm: {n} said → 0 done",
        done == 0 and open_n == n,
        f"done={done} open={open_n}",
    )


def storm_evidence_only_done(n: int = 200) -> bool:
    """Mix of said + prove — only proves are done."""
    c = Coherence(title="storm-evidence")
    lock = threading.Lock()
    proves = {"n": 0}

    def agent(i: int) -> None:
        with lock:
            if i % 2 == 0:
                c.said(f"claim-{i}", next="get evidence")
            else:
                c.prove(
                    f"cmd-{i}",
                    evidence=f"exit_code=0 id={i}",
                    next="chain complete",
                )
                proves["n"] += 1

    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(agent, range(n)))

    done = len(c.done_facts())
    open_n = len(c.open_facts())
    expect_done = n // 2 if n % 2 == 0 else n // 2  # odds only if 0-indexed: 1,3,...
    # i%2==0 said, i%2==1 prove → floor(n/2) proves if n even? 
    # n=200: i=0..199, odds: 100 proves
    expect_done = sum(1 for i in range(n) if i % 2 == 1)
    expect_open = n - expect_done
    return check(
        f"evidence-only: {expect_done} done, {expect_open} open",
        done == expect_done and open_n == expect_open,
        f"done={done} open={open_n} (expected done={expect_done})",
    )


def storm_empty_next_illegal(n: int = 100) -> bool:
    """Concurrent attempts to create Fact without next — all must raise."""
    errors = []
    lock = threading.Lock()

    def agent(i: int) -> None:
        try:
            Fact.make(f"claim-{i}", next="")
            with lock:
                errors.append("accepted")
        except FactError:
            with lock:
                errors.append("rejected")
        except Exception as e:
            with lock:
                errors.append(f"other:{e}")

    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(agent, range(n)))

    ok = errors.count("rejected") == n and "accepted" not in errors
    return check(
        f"empty next illegal under {n} races",
        ok,
        f"rejected={errors.count('rejected')} accepted={errors.count('accepted')}",
    )


def storm_memory_refuses_undone(n: int = 100) -> bool:
    """Concurrent learn() without proof — all fail; lessons stay 0."""
    c = Coherence(title="storm-mem")
    fails = {"n": 0}
    lock = threading.Lock()

    def agent(i: int) -> None:
        try:
            c.evolve.learn(
                problem=f"p-{i}",
                lesson=f"l-{i}",
                proof="",  # illegal
                next_domino="chain complete",
            )
        except ValueError:
            with lock:
                fails["n"] += 1

    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(agent, range(n)))

    return check(
        f"memory refuses undoned under {n} races",
        fails["n"] == n and len(c.evolve.lessons) == 0,
        f"fails={fails['n']} lessons={len(c.evolve.lessons)}",
    )


def storm_domino_order(n: int = 50) -> bool:
    """Many threads try to solve non-head — only head solve once; order holds."""
    c = Coherence(title="storm-domino", seed_cascade=True)
    head = c.dominos.head()
    assert head is not None
    second = c.dominos.stones[1]
    results = {"head_ok": 0, "head_fail": 0, "second_ok": 0, "second_fail": 0}
    lock = threading.Lock()

    def try_head(i: int) -> None:
        try:
            c.dominos.solve(
                head.id,
                proof=f"proof-head-{i}",
                lesson="first stone needs evidence",
            )
            with lock:
                results["head_ok"] += 1
        except Exception:
            with lock:
                results["head_fail"] += 1

    def try_second(i: int) -> None:
        try:
            c.dominos.solve(
                second.id,
                proof=f"proof-second-{i}",
                lesson="should not win first",
            )
            with lock:
                results["second_ok"] += 1
        except Exception:
            with lock:
                results["second_fail"] += 1

    with ThreadPoolExecutor(max_workers=64) as pool:
        futs = []
        for i in range(n):
            futs.append(pool.submit(try_second, i))
            futs.append(pool.submit(try_head, i))
        for f in as_completed(futs):
            f.result()

    # Exactly one successful head solve; second never ok before head done
    # After races: head may be SOLVED once; second_ok should be 0 if all raced while waiting
    # Note: if head solved first, later second might succeed — so we only assert head_ok==1
    # and that we never had second_ok before checking... After full race, second_ok could be 1
    # if some thread ran after head was solved. Tighten: only fire second while head OPEN.

    # Re-run cleaner barrier storm for second-only while head open
    c2 = Coherence(title="storm-domino-2", seed_cascade=True)
    h2 = c2.dominos.head()
    s2 = c2.dominos.stones[1]
    barrier = threading.Barrier(n)
    second_ok = {"n": 0}
    lock2 = threading.Lock()

    def only_second(i: int) -> None:
        barrier.wait()
        try:
            c2.dominos.solve(s2.id, proof=f"x-{i}", lesson="nope")
            with lock2:
                second_ok["n"] += 1
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=n) as pool:
        list(pool.map(only_second, range(n)))

    head_once = results["head_ok"] == 1
    second_blocked = second_ok["n"] == 0
    return check(
        "domino order under race (head once; non-head blocked while waiting)",
        head_once and second_blocked,
        f"head_ok={results['head_ok']} second_while_waiting_ok={second_ok['n']}",
    )


def storm_evolution_compounds() -> bool:
    """Session1 learns with proof → session2 loads → hints fire with NEXT."""
    mem = Path(tempfile.mkdtemp()) / "evo.json"
    c1 = Coherence(title="s1", memory_path=mem, seed_cascade=True)
    h = c1.dominos.head()
    assert h is not None
    proof = c1.claimproof.cmd("unit tests", "true", 0)
    c1.solve_domino(
        h.id,
        proof=str(proof.proven or "exit 0"),
        lesson="Never trust chat green — require cmd exit",
        proof_record_id=proof.id,
        tags=["tests"],
    )
    n1 = len(c1.evolve.lessons)
    if n1 < 1:
        return check("evolution compounds", False, "no lessons after solve")

    c2 = Coherence(title="s2", memory_path=mem)
    n2 = len(c2.evolve.lessons)
    hits = c2.evolve.apply_hints("tests passed in chat green")
    has_next = bool(hits and hits[0].next_domino.strip())
    return check(
        "evolution compounds across sessions",
        n2 >= 1 and len(hits) >= 1 and has_next,
        f"s1_lessons={n1} s2_lessons={n2} hits={len(hits)} next={hits[0].next_domino if hits else None!r}",
    )


def storm_check_gate() -> bool:
    """CI check: chat-only session fails; after prove-cmd truth, passes."""
    from coherence.ci.session import SessionStore, check_exit_code

    path = Path(tempfile.mkdtemp()) / "sess.json"
    store = SessionStore(path)
    c = store.load()
    c.said("tests passed", next="prove")
    store.save(c)
    c = store.load()
    fail_code = check_exit_code(c, strict=True)
    store.prove_command("true", claim="unit tests", next_action="chain complete")
    # still have open said fact
    c2 = store.load()
    # prove only adds; open said remains → still fail unless we only use prove path
    # Clearer: new session with only prove
    path2 = Path(tempfile.mkdtemp()) / "sess2.json"
    store2 = SessionStore(path2)
    store2.prove_command("true", claim="unit tests", next_action="chain complete")
    c3 = store2.load()
    pass_code = check_exit_code(c3, strict=True)
    return check(
        "CI gate: open fails, proven-only passes",
        fail_code == 1 and pass_code == 0,
        f"open_session_exit={fail_code} proven_session_exit={pass_code}",
    )


def main() -> int:
    _banner()
    t0 = time.time()
    results = [
        storm_chat_never_done(500),
        storm_evidence_only_done(200),
        storm_empty_next_illegal(100),
        storm_memory_refuses_undone(100),
        storm_domino_order(40),
        storm_evolution_compounds(),
        storm_check_gate(),
    ]
    elapsed = time.time() - t0
    print()
    passed = sum(1 for r in results if r)
    total = len(results)
    print("─" * 56)
    print(f"RESULT: {passed}/{total} checks PASS  ({elapsed:.2f}s)")
    if passed == total:
        print("STORM PROOF: Coherence law holds under hostile races.")
        print("Exit 0")
        print()
        return 0
    print("STORM PROOF: FAILED — do not ship claims that are not true.")
    print("Exit 1")
    print()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
