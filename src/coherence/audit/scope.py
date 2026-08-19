"""Blast radius: what did the agent touch — and what can't we tell?

`audit` answers "did it do what it said?". This answers the harder twin:
"did it do anything it did NOT say?" — the 3am question for anyone who lets an
agent run unattended, and the one every security review asks as "show me
everything the agent touched."

Proving a negative from a log is a logic trap: absence of evidence is not
evidence of absence. A single `bash deploy.sh` can hide any effect in the
world. The usual responses are both wrong:

  * claim completeness anyway (a lie that gets someone breached), or
  * demand syscall-level sandboxing, ship nothing, and leave the question
    unanswered forever — which is where the industry actually sits.

This module takes the third road, and it is the same rule Seal's witness is
built on: **UNKNOWN never collapses into ABSENT.** Commands whose effects
cannot be determined statically are not skipped and not guessed at — they are
reported as OPAQUE, counted, and printed, and the verdict states plainly that
the report is bounded by them. A bounded answer that says where its edge is
beats both a false complete one and no answer at all.

What is extracted (best effort, from the transcript already on disk):
  files written · repos pushed · network hosts contacted · packages installed

What makes a command OPAQUE:
  running a script file, `eval`, command substitution, piping a download into
  a shell, `source`, or a base64 decode into execution — anything whose real
  effects live somewhere this file cannot see.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .transcript import _events           # same parser, one source of truth

# ── effects we CAN read directly off the command line ────────────────────
_WRITE_TOOLS = {"Write", "Edit", "NotebookEdit", "MultiEdit"}

_NET = re.compile(
    r"\b(?:curl|wget|http|https)\b[^\n|;]*?"
    r"(?:https?://)?([a-z0-9.-]+\.[a-z]{2,})(?:[/:\s]|$)", re.I)
_GH_API = re.compile(r"\bgh\s+(?:api|repo|pr|issue|release|run|search)\b", re.I)
_PUSH = re.compile(r"\bgit\s+push\b[^\n;&|]*", re.I)
_INSTALL = re.compile(
    r"\b(?:pip|pip3|python3?\s+-m\s+pip)\s+install\s+([^\n;&|]+)"
    r"|\bnpm\s+(?:i|install|publish)\s*([^\n;&|]*)"
    r"|\bcargo\s+(?:install|publish)\s*([^\n;&|]*)"
    r"|\bbrew\s+install\s+([^\n;&|]+)", re.I)
_REDIRECT = re.compile(r"(?<![>\d])>{1,2}\s*([^\s&|;]+)")
_FILE_MUT = re.compile(
    r"\b(?:rm|mv|cp|chmod|chown|touch|mkdir|ln)\s+(-[^\s]*\s+)*([^\n;&|]+)", re.I)

# ── what we deliberately CANNOT read: the honest edge ────────────────────
_OPAQUE_RULES = [
    (re.compile(r"\beval\b"),                      "eval — constructs code at runtime"),
    (re.compile(r"\bsource\s+|\.\s+/"),            "source — runs another file's contents"),
    (re.compile(r"(?:curl|wget)[^\n]*\|\s*(?:ba|z|)sh\b"),
                                                   "download piped into a shell"),
    (re.compile(r"\bbase64\s+(?:-d|--decode)[^\n]*\|"),
                                                   "base64 decoded into execution"),
    (re.compile(r"\b(?:ba|z|)sh\s+[^\s-][^\n;&|]*\.(?:sh|bash)\b"),
                                                   "runs a script file"),
    (re.compile(r"\b(?:python3?|node|ruby|perl)\s+[^\s-][^\n;&|]*\.(?:py|js|rb|pl)\b"),
                                                   "runs a program file"),
    (re.compile(r"\$\((?!\s*(?:pwd|date|basename|dirname|echo)\b)"),
                                                   "command substitution"),
    (re.compile(r"\bmake\b|\bnpm\s+run\b|\byarn\s+\w+"),
                                                   "delegates to a script target"),
    (re.compile(r"\bdocker\s+run\b|\bssh\b"),      "executes in another environment"),
]

# hosts that are noise, not reach: the agent's own machine
_LOCAL = re.compile(r"^(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])")


@dataclass
class Scope:
    files: set = field(default_factory=set)
    pushes: set = field(default_factory=set)
    hosts: set = field(default_factory=set)
    installs: set = field(default_factory=set)
    opaque: list = field(default_factory=list)     # (seq, command, why)
    commands: int = 0
    parsed_events: int = 0

    def looks_like_transcript(self) -> bool:
        """False when the file yielded nothing an agent session would contain.

        A blast-radius report that says "0 commands, fully readable" over a
        README, an empty file, or a mistyped path is the worst possible
        output: it reads as an all-clear for a file that was never examined.
        That is exactly the UNKNOWN-collapsing-into-ABSENT failure this module
        refuses to make about commands, so it must not make it about its own
        input either.
        """
        return self.parsed_events > 0

    def bounded(self) -> bool:
        """True when opaque commands exist — the report has a known edge."""
        return bool(self.opaque)

    def exit_code(self) -> int:
        """0 = fully readable · 1 = readable but BOUNDED by opaque commands.

        Never 0 while anything is opaque: a report that cannot see everything
        must not exit like one that can.
        """
        return 1 if self.opaque else 0


def _clean_path(p: str) -> str | None:
    p = p.strip().strip("\"'")
    if not p or p.startswith("-") or p in ("/dev/null", "/dev/stdout", "/dev/stderr"):
        return None
    return p if len(p) < 200 else None


def scope_transcript(path: Path | str) -> Scope:
    s = Scope()
    pending_writes: dict = {}

    for ev in _events(Path(path)):
        s.parsed_events += 1
        if ev[0] == "text":
            continue
        if ev[0] == "cmd_use":
            _, seq, _tid, cmd = ev
            s.commands += 1

            for rx, why in _OPAQUE_RULES:
                if rx.search(cmd):
                    s.opaque.append((seq, cmd.strip()[:120], why))
                    break            # one reason is enough to mark it unreadable

            for m in _NET.finditer(cmd):
                h = m.group(1).lower()
                if not _LOCAL.match(h):
                    s.hosts.add(h)
            if _GH_API.search(cmd):
                s.hosts.add("api.github.com")
            for m in _PUSH.finditer(cmd):
                s.pushes.add(m.group(0).strip()[:80])
            for m in _INSTALL.finditer(cmd):
                pkg = next((g for g in m.groups() if g), "").strip()[:60]
                s.installs.add(pkg or "(unnamed)")
            for rx in (_REDIRECT, _FILE_MUT):
                for m in rx.finditer(cmd):
                    p = _clean_path(m.group(m.lastindex or 1))
                    if p:
                        s.files.add(p)

    # file-writing TOOL calls (Write/Edit) are recorded structurally, not by regex
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            try:
                d = json.loads(raw)
            except Exception:
                continue
            msg = d.get("message") or {}
            for c in (msg.get("content") or []) if isinstance(msg.get("content"), list) else []:
                if isinstance(c, dict) and c.get("type") == "tool_use" \
                        and c.get("name") in _WRITE_TOOLS:
                    fp = (c.get("input") or {}).get("file_path")
                    if fp:
                        s.files.add(str(fp))
    return s
