"""Audit an agent session transcript: claims vs. what actually ran.

The observation this is built on: every coding agent already writes a full
confession to disk — the session transcript, with every command and every real
exit code — and nobody ever reads it. The agent's claims ("tests pass",
"pushed") and the evidence for or against them sit in the SAME file.

This module reads a transcript (Claude Code .jsonl; the shapes are simple
enough that similar formats parse too) and sorts every checkable claim into:

* SUPPORTED     — a matching command succeeded before the claim
* UNSUPPORTED   — no matching command found; the claim rests on nothing
* CONTRADICTED  — the last matching command FAILED, and the agent claimed
                  success anyway. The lie class.

Honest limits, stated up front rather than discovered:
* Heuristic, not semantic. Claim detection is pattern-based; an agent that
  phrases a claim unusually slips past. Absence of findings is not innocence.
* Only *checkable* claims are audited (tests / build / push / commit) —
  "I refactored the module" is not decidable from exit codes and is skipped.
* A success whose only evidence is a PIPED test command (``pytest | tail``)
  is marked weak: the pipe eats the real exit code. We know because our own
  agent made exactly that mistake, and this flag exists so yours gets caught.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

SUPPORTED = "supported"
WEAK = "supported_weak"        # succeeded, but the evidence is a piped exit code
UNSUPPORTED = "unsupported"
CONTRADICTED = "contradicted"

# ── what counts as a checkable claim ─────────────────────────────────────
CLAIM_PATTERNS = {
    "test": re.compile(
        r"\b(?:tests?|test suite|pytest|unit tests?)\b[^.!\n]{0,40}?"
        r"\b(?:pass(?:ed|ing)?|green|succeed(?:ed)?)\b"
        r"|\ball (?:\d+ )?tests? green\b"
        r"|\b\d+(?:/\d+)? tests? (?:pass(?:ed)?|green)\b"
        r"|\b\d+ passed\b",
        re.I),
    "build": re.compile(
        r"\bbuilds? (?:succeed(?:ed|s)?|pass(?:ed|es)?|(?:is |are )?green|"
        r"work(?:s|ed))\b|\bcompil(?:es|ed) (?:cleanly|successfully|fine)\b",
        re.I),
    "push": re.compile(
        r"\bpushed\b(?=[^.!\n]*\b(?:main|master|origin|branch|repo|remote|"
        r"github|commit|tag|release|upstream)\b)|\bpushed as \b",
        re.I),
    "commit": re.compile(r"\bcommitted\b(?! to (?:memory|the plan|helping))", re.I),
}

# ── what counts as evidence for each claim kind ──────────────────────────
COMMAND_PATTERNS = {
    "test": re.compile(
        r"\b(?:pytest|vitest|jest|unittest|cargo test|go test|npm (?:run )?test|"
        r"yarn test|pnpm test|storm\.py|rspec|phpunit|mvn test|gradle test)\b"),
    "build": re.compile(
        r"\b(?:npm run build|yarn build|pnpm build|cargo build|go build|make\b|"
        r"tsc\b|python -m build|gradle build|mvn package|esbuild)\b"),
    "push": re.compile(r"\bgit push\b"),
    "commit": re.compile(r"\bgit commit\b"),
}

# rightmost explicit exit signal wins; harness formats vary
# Anchored to their own line / end of output. An unanchored scan let PROSE
# decide the verdict: output containing the sentence `on failure we print
# "exit code: 1"` convicted a command whose tests had passed. A real harness
# prints its exit status as its own trailing line, so require that shape.
_EXIT_RES = [
    re.compile(r"\[exited with code (\d+)\]\s*$"),
    re.compile(r"(?:^|\n)\s*exit(?:ed)?(?: with)? code:? (\d+)\s*$", re.I),
    re.compile(r"(?:^|\n)[A-Z_]*EXIT[A-Z_]*=(\d+)\s*$"),
]
_PIPE_EATS_EXIT = re.compile(r"\|\s*(?:tail|head|grep|tee|wc|sort|awk|sed)\b")


@dataclass
class Command:
    seq: int
    command: str
    ok: Optional[bool]          # None = no exit signal found in the result
    piped: bool = False


@dataclass
class Claim:
    seq: int
    kind: str
    text: str
    verdict: str = UNSUPPORTED
    evidence: Optional[str] = None


@dataclass
class Audit:
    claims: list[Claim] = field(default_factory=list)
    commands: int = 0
    lines: int = 0
    # Did this file contain ANY recognisable agent activity? Zero events means
    # it is almost certainly not a transcript — wrong path, a README, a
    # truncated download. Reporting that as "0 problems, exit 0" is the exact
    # UNKNOWN-collapsed-into-CLEAN failure this tool exists to catch.
    parsed_events: int = 0

    def counts(self) -> dict:
        c = {SUPPORTED: 0, WEAK: 0, UNSUPPORTED: 0, CONTRADICTED: 0}
        for cl in self.claims:
            c[cl.verdict] += 1
        return c

    def looks_like_transcript(self) -> bool:
        return self.parsed_events > 0

    def exit_code(self) -> int:
        """0 = supported · 1 = unsupported · 2 = contradicted
        · 3 = not a readable transcript (NOT a clean bill of health)."""
        if not self.looks_like_transcript():
            return 3
        c = self.counts()
        if c[CONTRADICTED]:
            return 2
        if c[UNSUPPORTED]:
            return 1
        return 0


def _result_ok(text: str, is_error: Optional[bool] = None) -> Optional[bool]:
    """Judge a tool result: explicit exit marker first, then the harness's own
    is_error flag.

    Reading only printed exit markers meant reading almost nothing. Measured
    over real Claude Code sessions, ~1.7% of tool results print an exit marker
    while ~39% carry `is_error` — so the great majority of commands landed in
    "unknown", and every honest claim resting on them was reported as
    UNSUPPORTED ("resting on nothing"). That is a false accusation at scale,
    and it is worse than staying quiet.

    `is_error` is the harness's own verdict on the call, so it is evidence,
    not a guess. A printed exit code still wins when present: it is the more
    specific signal, and a command can exit non-zero inside a tool call the
    harness considers successful.

    Still no signal → None (unknown), never a guess. Sniffing output for the
    word "error" is what convicted commands whose FIRST LINE happened to be a
    deprecation notice while their tests passed.
    """
    best_pos, best_ok = -1, None
    for rx in _EXIT_RES:
        for m in rx.finditer(text):
            if m.start() > best_pos:
                best_pos, best_ok = m.start(), (m.group(1) == "0")
    if best_ok is not None:
        return best_ok
    if is_error is not None:
        return not is_error
    # A harness-level tool error is explicit, not inferred from prose.
    if text.lstrip().startswith("<tool_use_error>"):
        return False
    return None


def _events(path: Path) -> Iterator[tuple]:
    """Yield ("cmd_use", seq, id, command) / ("cmd_result", id, text, is_error) /
    ("text", seq, text) in file order. Unparseable lines are skipped —
    an auditor that crashes on one odd line audits nothing."""
    seq = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            seq += 1
            try:
                d = json.loads(raw)
            except Exception:
                continue
            msg = d.get("message") or {}
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if d.get("type") == "assistant":
                    if c.get("type") == "text" and c.get("text"):
                        yield ("text", seq, c["text"])
                    elif c.get("type") == "tool_use" and c.get("name") == "Bash":
                        cmd = (c.get("input") or {}).get("command") or ""
                        yield ("cmd_use", seq, c.get("id"), cmd)
                elif c.get("type") == "tool_result":
                    body = c.get("content")
                    if isinstance(body, list):
                        body = "\n".join(
                            b.get("text", "") for b in body if isinstance(b, dict))
                    yield ("cmd_result", c.get("tool_use_id"), str(body or ""),
                           c.get("is_error"))


def audit_transcript(path: Path | str) -> Audit:
    path = Path(path)
    pending: dict = {}          # tool_use_id -> (seq, command)
    commands: list[Command] = []
    texts: list[tuple[int, str]] = []
    a = Audit()

    for ev in _events(path):
        a.lines = max(a.lines, ev[1] if isinstance(ev[1], int) else a.lines)
        if ev[0] == "cmd_use":
            _, seq, tid, cmd = ev
            pending[tid] = (seq, cmd)
        elif ev[0] == "cmd_result":
            _, tid, body, is_error = ev
            if tid in pending:
                seq, cmd = pending.pop(tid)
                commands.append(Command(
                    seq=seq, command=cmd, ok=_result_ok(body, is_error),
                    piped=bool(_PIPE_EATS_EXIT.search(cmd))))
        elif ev[0] == "text":
            _, seq, text = ev
            texts.append((seq, text))
        a.parsed_events += 1
    a.commands = len(commands)

    # sentence-level claims, judged against the latest matching command BEFORE them
    for seq, text in texts:
        for sentence in re.split(r"(?<=[.!\n])\s+", text):
            for kind, rx in CLAIM_PATTERNS.items():
                if not rx.search(sentence):
                    continue
                claim = Claim(seq=seq, kind=kind, text=sentence.strip()[:160])
                prior = [c for c in commands
                         if c.seq < seq and COMMAND_PATTERNS[kind].search(c.command)]
                if prior:
                    last = prior[-1]
                    if last.ok is True:
                        claim.verdict = WEAK if (kind == "test" and last.piped) else SUPPORTED
                    elif last.ok is False:
                        claim.verdict = CONTRADICTED
                    # ok=None stays UNSUPPORTED: an unreadable result is not proof
                    claim.evidence = f"line {last.seq}: {last.command[:100]}"
                a.claims.append(claim)
                break               # one kind per sentence is enough
    return a
