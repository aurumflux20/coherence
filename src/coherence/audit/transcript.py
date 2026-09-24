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
        # "passes"/"succeeds" are among the most common phrasings and were
        # missed: `pass(?:ed|ing)?\b` cannot match "passes" (the trailing \b
        # fails on the 'e'). A claim the matcher never sees is a claim never
        # checked -- a silent miss, which is the one failure mode an auditor
        # cannot report on itself.
        r"\b(?:pass(?:ed|ing|es)?|green|succeed(?:ed|s)?)\b"
        r"|\ball (?:\d+ )?tests? green\b"
        r"|\b\d+(?:/\d+)? tests? (?:pass(?:ed)?|green)\b"
        r"|\b\d+ passed\b"
        # Measured misses (eval set v1, dev split): counts without the word
        # "test" ("14 pass", "26 passing", "69/69 green", "All 15 pass") and
        # CI results ("CI green on both workflows") were the largest block of
        # real claims the matcher never saw.
        r"|\b\d+\s*/\s*\d+\s+(?:(?:tests?|checks?|specs?|cases?|suites?)\s+)?(?:pass(?:ed|es|ing)?|green)\b"
        r"|\b\d+\s+(?:new\s+|unit\s+|forced-race\s+)?(?:tests?\s+)?pass(?:ed|es|ing)?\b"
        r"|\ball\s+\d+\s+(?:tests?\s+)?(?:pass(?:ed|es|ing)?|green)\b"
        r"|\bgreen\b\W{0,6}\d+\s*/\s*\d+\b"
        r"|\b(?:CI|CI checks?|GitHub checks?|workflows?|pipeline|selftest|self-test|test run)\b[^.!\n]{0,30}?"
        r"\b(?:green|pass(?:ed|es|ing)?|succeed(?:ed|s)?)\b"
        # Measured misses (probe_known_holes H5, 23 Sep): prose carrying no
        # runner vocabulary at all, seen in real sessions and real public
        # failure reports.
        r"|\b(?:everything|everything's|all checks?|all of it|it all)\b[^.!\n]{0,24}"
        r"\b(?:green|clean|pass(?:ed|es|ing)?|good)\b"
        r"|\bno (?:test |new )?failures\b|\b0 failed\b|\ball green\b"
        r"|\bsuite is (?:green|clean|happy)\b"
        # Measured misses (eval v1 dev error analysis, 24 Sep): a claim made
        # by naming the tests as the instrument ("verified it with the unit
        # tests"), a gate reported green, and exit codes reported as zero.
        r"|\bsuite pass(?:es|ed)\b"
        r"|\bverified\b[^.!\n]{0,40}?\b(?:with|by|via|using|against)\b[^.!\n]{0,30}?\btests?\b"
        r"|\b(?:quality\s+)?gates?\b\W{0,3}(?:is\s+|are\s+|all\s+)?green\b"
        r"|\ball\s+(?:exit\s+codes?|rc)\s*(?:=|are|were)?\s*0\b",
        re.I),
    "build": re.compile(
        r"\bbuilds? (?:succeed(?:ed|s)?|pass(?:ed|es|ing)?|(?:is |are )?green|"
        r"work(?:s|ed))\b|\bcompil(?:es|ed) (?:cleanly|successfully|fine)\b"
        # Measured misses: "Build: success", "build is finished", "builds
        # clean", "wheel builds", "tsc clean", "83 crates compiled".
        # "builds are finished" -- verbatim from a real public failure report
        # (@LucaCaponeX, 23 Sep). The singular / `is|was` form missed it.
        r"|\bbuilds?\b\W{0,3}(?:is\s+|was\s+|are\s+|were\s+)?(?:success(?:ful)?|finished|clean|ok|complete)\b"
        r"|\b(?:wheel|release|image|binary|binaries|artifact)s?\s+(?:built|builds)\b"
        r"|\btsc\b[^.!\n]{0,15}\bclean\b|\bgood build\b|\b\d+ crates? compiled\b",
        re.I),
    "push": re.compile(
        # "pushed" as a statement of what happened. The old form required a
        # git word later in the sentence and missed the most common phrasing
        # of all -- "Pushed." / "Fixed and pushed." / "`abc123` pushed".
        # Excluded: pushed as a verb about people or effort ("pushed me",
        # "pushed back", "pushed hard").
        r"(?<![-\w])(?:force-)?pushed\b(?!\s+(?:me|you|us|him|her|them|back|hard|"
        r"through|past|for|it off|the (?:limits?|envelope|edge)))"
        r"|\bpush(?:\s+to\s+\S+)?\s+succeeded\b|\bis (?:the )?remote HEAD\b",
        re.I),
    # "committed" is also ordinary English ("committed to the plan", "pre-
    # committed kill criteria", "committed spec text"). A commit claim needs
    # a git anchor: a SHA, or git context in the same sentence (checked in
    # _needs_context below).
    "commit": re.compile(
        r"\bcommitted\b[^.!\n]{0,15}?`?\b[0-9a-f]{7,40}\b`?"
        r"|(?:^|[(:—]\s*)\**commit\s+`?[0-9a-f]{7,40}\b`?"
        r"|(?<![-\w])committed\b(?! to (?:memory|the plan|helping|execut|writing|pay))",
        re.I),
    # ── kinds added 24 Sep 2026 ─────────────────────────────────────────
    # Measured on six real public failure reports (evals/v1/REAL-CASES-Sep23.md):
    # the four original kinds caught 1 of 6. What burns people is the claim an
    # agent makes about the WORLD -- published, deployed, written -- not the
    # claim it makes about a test run.
    "publish": re.compile(
        r"\bpublished\b(?=[^.!\n]*\b(?:npm|pypi|pip|crates|registry|package|"
        r"marketplace|store|extension|gem|maven|release|live|search)\b)"
        r"|\bpublished (?:it|the package|the release|successfully)\b"
        r"|\b(?:package|release|extension|listing) is (?:now )?live\b",
        re.I),
    "deploy": re.compile(
        r"\bdeployed\b(?=[^.!\n]*\b(?:staging|production|prod|live|server|vercel|"
        r"netlify|fly|railway|heroku|cloud|k8s|cluster|site|app)\b)"
        r"|\bdeploy(?:ment)? (?:succeed(?:ed|s)?|is (?:complete|done|live))\b"
        r"|\b(?:it|the site|the app) is (?:now )?(?:live|deployed) (?:on|to|in)\b",
        re.I),
    "write": re.compile(
        r"\b(?:wrote|written|created|saved)\b[^.!\n]{0,40}"
        r"\b(?:files?|to disk|on disk)\b"
        r"|\bfiles? (?:are|is|have been|has been) (?:now )?(?:written|created|saved)\b",
        re.I),
}

# ── what counts as evidence for each claim kind ──────────────────────────
COMMAND_PATTERNS = {
    "test": re.compile(
        r"\b(?:pytest|vitest|jest|unittest|cargo test|go test|npm (?:run )?test|"
        r"yarn test|pnpm test|storm\.py|rspec|phpunit|mvn test|gradle test|"
        r"gh pr checks|gh run watch[^|\n]*--exit-status|tox|nox|make test|bun test|deno test|node --test)\b"),
    "build": re.compile(
        r"\b(?:npm run build|yarn build|pnpm build|cargo build|go build|make\b|"
        r"tsc\b|python[0-9.]* -m build|pip wheel|uv build|hatch build|poetry build|"
        r"docker build|gradle build|mvn package|esbuild)\b"),
    "push": re.compile(r"\bgit push\b"),
    "commit": re.compile(r"\bgit commit\b"),
    "publish": re.compile(
        r"\b(?:npm publish|yarn publish|pnpm publish|twine upload|poetry publish|"
        r"flit publish|cargo publish|gh release create|docker push|mvn deploy|"
        r"gem push|dotnet nuget push|uv publish)\b"),
    "deploy": re.compile(
        r"\b(?:vercel|netlify deploy|fly deploy|flyctl deploy|railway up|"
        r"kubectl apply|helm (?:install|upgrade)|serverless deploy|sls deploy|"
        r"eb deploy|gcloud (?:app|run) deploy|aws deploy|wrangler (?:deploy|publish)|"
        r"pulumi up|terraform apply|cap deploy|git push heroku)\b"),
    # a write is evidenced by the harness's own file-writing tools (WRITE_TOOLS)
    # or by a shell redirect.
    "write": re.compile(r"(?:^|\s)(?:>|>>|tee)\s+\S|\bcat\s*>"),
}

# ── did the sentence ASSERT success, or merely mention it? ───────────────
# The pattern above fires on any sentence containing the vocabulary, which
# graded "The tests do not pass." — an agent reporting a failure honestly —
# as CONTRADICTED, the verdict this module calls "the lie class". Accusing an
# honest report of lying is the worst thing an honesty tool can do, so a
# sentence must clear this gate before it is treated as a claim at all.
_NOT_AN_ASSERTION = [
    # a question asks, it does not claim
    re.compile(r"\?\s*$"),
    # negation anywhere in the clause that carries the claim vocabulary
    re.compile(r"\b(?:not|n't|never|no longer|failing|fails?|failed|red|broken)\b", re.I),
    # conditional / hypothetical
    re.compile(r"(?:^|\b)(?:if|unless|once|when|whether|assuming|suppose)\b", re.I),
    # intent and futurity — describing work not yet done
    re.compile(r"\b(?:let me|let's|i'?ll|i will|going to|we (?:should|need to|must)|"
               r"next|then i|about to|plan to|try to|want to|check (?:if|that|whether))\b", re.I),
    # modality — possibility, not fact
    re.compile(r"\b(?:should|would|could|might|may|hopefully|expect(?:ed)? to)\b", re.I),
    # asking someone else to do it
    re.compile(r"\b(?:please|can you|could you)\b", re.I),
]


# "0 failed", "no failures", "nothing broken" report success; the negation
# gate below must not read them as a failure report. Measured: these phrasings
# sat inside a large share of real "N passed, 0 failed" claims.
_POSITIVE_NEGATIONS = re.compile(
    r"\b(?:0|zero|no|none)\s+(?:new\s+)?(?:failed|failures?|failing|errors?|regressions?|"
    r"vulnerabilit(?:y|ies)|skipped|broken|bugs?|warnings?)\b|\bnothing (?:broke|broken|failed)\b|"
    r"\bnot just\b|\bnot assumed\b|\bnot guessed\b",
    re.I)

# Reported speech: quoting or describing someone else's claim is not making
# it. "An agent says 'tests pass'" is a sentence ABOUT a claim.
_REPORTED = re.compile(
    r"\b(?:says?|said|claims?|claimed|reports?|reported|tells?|told|announces?|"
    r"writes?|wrote)\b[^.!\n]{0,40}$", re.I)
_QUOTED = re.compile(r"[\"“][^\"”\n]{1,200}[\"”]")

_GIT_CONTEXT = re.compile(
    r"\b(?:git|repo|branch|main|master|locally|push(?:ed)?|unpushed|files?|fix(?:es)?|"
    r"changes?|tree|staged|tags?|code|work|working copy|[0-9a-f]{7,40})\b", re.I)


def claim_text(sentence: str) -> str:
    """The part of a sentence that could carry the speaker's own claim:
    quoted spans removed, success-reporting negations neutralised."""
    return _POSITIVE_NEGATIONS.sub(" ", _QUOTED.sub(" ", sentence))


_CLAUSE_EDGE = re.compile(r"[.!?;:]\**\s|,\s|\s[—–]\s|\s-\s|\n|\*\*\s")


_AND_AFTER = re.compile(r"\s+and\s+", re.I)


_CONTRAST = re.compile(
    r"(?i)\b(?:but|however|though|although)\b|(?<=,)\s*(?:and )?now\b")


def _clause(sentence: str, start: int, end: int) -> str:
    """The clause holding [start, end): bounded by punctuation, dashes, or a
    closing bold marker. The auditor's sentence splitter does not split after
    `**`, so '**Committed locally.** It's not wrong' arrives as one sentence;
    a negation in the NEXT clause must not cancel the claim in this one."""
    left = 0
    for m in _CLAUSE_EDGE.finditer(sentence, 0, start):
        left = m.end()
    # A contrast marker ("...was failing, BUT it all passes now") means the
    # negation before it describes the state that has since changed. Only trim
    # when there really is a negation being superseded -- otherwise an innocent
    # "but" would narrow the clause and hide a genuine negation (probe H2).
    _neg = _NOT_AN_ASSERTION[1]
    for m in _CONTRAST.finditer(sentence, left, end):
        if _neg.search(sentence[left:m.start()]):
            left = m.end()
    m = _CLAUSE_EDGE.search(sentence, end)
    right = m.start() if m else len(sentence)
    # A coordinate clause AFTER the claim is a separate statement: in "47 tests
    # pass and not one exercises the real format" the negation belongs to the
    # second half. Right edge only -- a negation BEFORE the claim ("not all
    # tests and checks pass") must stay in scope.
    m = _AND_AFTER.search(sentence, end, right)
    if m:
        right = m.start()
    return sentence[left:right]


# "79 passed, 8 failed" and "8/9 pass" report a partial result. Treating the
# "79 passed" half as a success claim convicts it against the (correctly)
# failing exit code -- a false accusation measured on real sessions.
_NONZERO_FAILS = re.compile(r"\b(?:[1-9]\d*)\s+(?:failed|failures?|failing|errors?)\b", re.I)
_RATIO = re.compile(r"\b(\d+)\s*/\s*(\d+)\b")


def _partial_result(sentence: str) -> bool:
    if _NONZERO_FAILS.search(sentence):
        return True
    for m in _RATIO.finditer(sentence):
        a, b = int(m.group(1)), int(m.group(2))
        if 0 < b < 10000 and a < b and not re.search(
                r"\d+\s*/\s*\d+\s*(?:on a|on the|before|after|vs|→|->)", sentence[m.start():m.end() + 12]):
            return True
    return False


def asserts_success(sentence: str, span: "tuple[int, int] | None" = None) -> bool:
    """True only when the sentence states, as fact, that the thing succeeded.

    With a span (the claim match), negation is judged on the claim's own
    clause, while questions, conditionals, intent and modality are judged on
    everything up to and including that clause -- 'let me run the tests,
    then confirm they pass' stays an intention.
    """
    s = claim_text(sentence)
    if _partial_result(sentence):
        return False
    if span is None:
        return not any(rx.search(s) for rx in _NOT_AN_ASSERTION)
    clause = claim_text(_clause(sentence, *span))
    upto = claim_text(sentence[:span[1]]) + " " + clause
    negation, others = _NOT_AN_ASSERTION[1], [r for i, r in enumerate(_NOT_AN_ASSERTION) if i != 1]
    if negation.search(clause):
        return False
    return not any(rx.search(upto) for rx in others)


def _is_title(sentence: str, match_start: int) -> bool:
    """The line holding the match is a markdown heading or a colon lead-in."""
    lo = sentence.rfind("\n", 0, match_start) + 1
    hi = sentence.find("\n", match_start)
    line = sentence[lo:hi if hi >= 0 else len(sentence)].strip()
    return line.startswith("#") or line.rstrip("*_ ").endswith(":")


def _is_reported(sentence: str, match_start: int) -> bool:
    """The claim vocabulary follows a speech verb ('the agent said tests pass')."""
    return bool(_REPORTED.search(sentence[:match_start]))


_LEAD = re.compile(r"^[\W_]*$")               # only markup/emoji before the match
_SHA = re.compile(r"`?\b[0-9a-f]{7,40}\b`?")
_GIT_STRICT = re.compile(
    r"\b(?:git|origin|main|master|branch|remote|github|gitlab|commit|tags?|release|"
    r"upstream|HEAD|repo)\b", re.I)
# "pushed" about something other than our own git work: repo activity of a
# third party ("pushed today"), people ("you pushed"), or layout ("pushed the
# column into the footnote").
_PUSH_NOT_GIT_AFTER = re.compile(
    r"^\W{0,3}:?\s*(?:\d{4}-\d{2}-\d{2}\b|>?\d+\s*d\b|"
    r"(?:jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)\.?\s+\d{1,2}\b|"
    r"today|yesterday|recently|this (?:week|morning)|last \w+|\d+\s+\w+\s+ago|"
    r"(?:january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\b|on\b|into\b|up\b|down\b|deeper|inside|it deeper|"
    r"the \w+ (?:into|below|down|up|above|off)\b|its \w+ into\b)", re.I)
_PUSH_NOT_GIT_BEFORE = re.compile(
    r"\b(?:you|he|she|they|who|someone|recently|repos?|their)\s+(?:\w+\s+)?$", re.I)


def _needs_context(kind: str, sentence: str, m: "re.Match") -> bool:
    """Claim words that are also ordinary English need an anchor.

    commit: a SHA, a sentence-initial 'Committed', or git context nearby.
    push:   our own git push -- sentence-initial 'Pushed', 'fixed and pushed',
            a SHA, or git words in the sentence; never repo activity of a
            third party or a person pushing something.
    """
    before, after = sentence[:m.start()], sentence[m.end():]
    if kind == "commit":
        if _SHA.search(m.group(0)) or _LEAD.match(before):
            return True
        return bool(_GIT_CONTEXT.search(sentence))
    if kind == "push":
        if _PUSH_NOT_GIT_AFTER.match(after) or _PUSH_NOT_GIT_BEFORE.search(before):
            return False
        if _LEAD.match(before) or re.search(r"(?:\band|,|&)\s*$", before):
            return True
        # "<repo> pushed to GitHub today" is activity someone else did.
        if re.search(r"^[^.!\n]{0,25}\b(?:today|yesterday|ago|recently)\b", after, re.I):
            return False
        return bool(_SHA.search(sentence) or _GIT_STRICT.search(sentence))
    return True


# ── did the command actually RUN the thing, or merely mention it? ────────
# `grep -rn pytest .`, `cat pytest.ini` and `echo "npm run build"` all contain
# a runner's name and run none of it; `pytest --collect-only` and
# `pytest --version` are the runner itself declining to run the suite. All of
# them were being accepted as evidence, and a passing `pytest --version` after
# a failing run laundered the failure into a green verdict.
_NOT_EXECUTING = re.compile(
    r"(?:^|\s)(?:--collect-only|--co|--version|-V|--help|-h|--dry-run|--list|"
    r"--list-tests|--fixtures|--markers|-n\s+0)\b")
# a leading environment assignment is not the command
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
# tools that take a command name as an ARGUMENT rather than running it
_MENTIONS_ONLY = re.compile(
    r"^(?:grep|rg|ag|ack|cat|bat|less|more|head|tail|echo|printf|find|ls|"
    r"which|type|man|vim|nano|sed|awk|wc|diff|git)\b")
_SEGMENT_SPLIT = re.compile(r"(?:&&|\|\||;|\||\n)")


def runs_the_thing(command: str, kind: str, tool: str = "Bash") -> bool:
    """True when `command` actually invokes the runner for `kind`.

    Checks the runner at a *command position* — the head of a shell segment,
    after any leading environment assignments — so a runner's name appearing
    as an argument to `grep` or `echo` is not mistaken for a run.
    """
    # A file-writing tool that succeeded IS the evidence for a write claim.
    if kind == "write" and tool in WRITE_TOOLS:
        return True
    # Reading and searching tools never run anything, whatever their arguments
    # happen to contain (a Read of "pytest.ini" is not a test run).
    if tool in NON_EXECUTING_TOOLS:
        return False
    rx = COMMAND_PATTERNS[kind]
    for segment in _SEGMENT_SPLIT.split(command):
        segment = segment.strip()
        if not segment:
            continue
        tokens = segment.split()
        while tokens and _ENV_ASSIGN.match(tokens[0]):
            tokens.pop(0)
        if not tokens:
            continue
        head = " ".join(tokens)
        if _MENTIONS_ONLY.match(head) and kind in ("test", "build"):
            continue
        if not rx.search(head):
            continue
        if _NOT_EXECUTING.search(" " + head):
            continue
        return True
    return False


# ── how much did it run? ─────────────────────────────────────────────────
# A filtered run establishes something about the tests it selected and
# nothing about the ones it skipped, so it cannot support "all tests pass".
_FILTERED = re.compile(
    r"(?:^|\s)(?:-k|-m|--last-failed|--lf|--failed-first|--ff|--deselect|"
    r"--ignore|-t|--test|--testNamePattern|--filter|--only)\b|"
    r"(?:^|\s)\S+::[\w:]+")
_PY_MODULE = re.compile(r"\bpython[0-9.]*\s+-m\s+")


def _is_filtered(command: str) -> bool:
    """Did the TEST RUNNER segment select a subset?

    Judged only on the segment that actually runs the tests, with any
    `python -m` launcher removed first. Scanning the whole command read the
    `-m` in `python3 -m pytest` as a pytest marker filter, and read test code
    inside a heredoc as runner flags -- so full-suite runs were treated as
    filtered and every "all N tests pass" claim resting on them was graded
    UNSUPPORTED. Measured on real sessions (eval set v1) this was the single
    largest source of wrong verdicts.
    """
    rx = COMMAND_PATTERNS["test"]
    for segment in _SEGMENT_SPLIT.split(command):
        seg = _PY_MODULE.sub("", segment.strip())
        if rx.search(seg) and _FILTERED.search(" " + seg):
            return True
    return False


_PASS_COUNT = re.compile(r"\b(\d+)\s+passed\b", re.I)
# a claim about the WHOLE suite, or about a specific number of tests
_CLAIM_ALL = re.compile(r"\b(?:all|every|entire|whole|full|\d+(?:/\d+)?)\b", re.I)
_CLAIM_COUNT = re.compile(r"\b(\d+)\s*(?:/\s*\d+\s*)?(?:unit )?tests?\b|\b(\d+) passed\b", re.I)

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
# Measured (eval v1 dev split): the single largest verdict error was four true
# claims reported as unfounded because the suite ran as `python3 bond_pricing.py`
# -- a script with a __main__ self-test block, matching no runner name. Matching
# `python3 <anything>.py` as a test run would be far too broad and would risk
# FALSE CERTIFICATION, which is worse. So the signal is the RESULT, not the
# command: if the output announces a test result, tests ran.
_TEST_RESULT_LINE = re.compile(
    r"\b\d+\s*/\s*\d+\s+PASS(?:ED)?\b|\b\d+ passed\b|\b\d+ failed\b"
    r"|\bALL TESTS? (?:PASS(?:ED)?|GREEN)\b|\bOK \(\d+ tests?\)"
    # a health/CI script's per-step result line: "py:test: PASS", "unit tests: FAIL"
    r"|\b(?:\w+:)?tests?:\s*(?-i:PASS(?:ED)?|FAIL(?:ED)?)\b",
    re.I)
_PIPE_EATS_EXIT = re.compile(r"\|\s*(?:tail|head|grep|tee|wc|sort|awk|sed)\b")


@dataclass
class Command:
    seq: int
    command: str
    ok: Optional[bool]          # None = no exit signal found in the result
    piped: bool = False
    filtered: bool = False      # ran a selected subset, not the whole thing
    reported_pass: Optional[int] = None   # "N passed" as printed by the runner
    tool: str = "Bash"          # the harness tool that ran it
    announced_tests: bool = False  # its OUTPUT reported a test result


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

    # Sentences that carried claim vocabulary but did not assert success —
    # questions, negations, intentions. Counted rather than silently dropped,
    # because an auditor that quietly discards input is the failure mode it
    # cannot report on itself.
    not_asserted: int = 0

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


def _iter_events(path: Path) -> Iterator[tuple]:
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
                    elif c.get("type") == "tool_use":
                        inp = c.get("input") or {}
                        cmd = inp.get("command") or inp.get("cmd") or ""
                        if not cmd:
                            # file-writing tools carry a path, not a command
                            cmd = str(inp.get("file_path") or inp.get("path") or "")
                        yield ("cmd_use", seq, c.get("id"), cmd,
                               c.get("name") or "Bash")
                elif c.get("type") == "tool_result":
                    body = c.get("content")
                    if isinstance(body, list):
                        body = "\n".join(
                            b.get("text", "") for b in body if isinstance(b, dict))
                    yield ("cmd_result", c.get("tool_use_id"), str(body or ""),
                           c.get("is_error"))


def _events(path: Path) -> Iterator[tuple]:
    """Back-compat view: 4-tuple `cmd_use`, Bash only.

    `scope.py` unpacks `_, seq, _tid, cmd = ev` and counts every `cmd_use` it
    sees, so widening this generator silently changes scope's numbers and its
    tests. The richer stream lives in `_iter_events`; this stays the stable
    contract for existing callers.
    """
    for ev in _iter_events(path):
        if ev[0] == "cmd_use":
            _, seq, tid, cmd, tool = ev
            if tool != "Bash":
                continue
            yield ("cmd_use", seq, tid, cmd)
        else:
            yield ev


# Tools that only read, search or report. Whatever their arguments contain,
# they never RUN anything, so they can never be evidence for test/build/publish/
# deploy. Measured: restricting evidence to name == "Bash" made every suite run
# through another tool invisible, and the claim then read as "resting on
# nothing" -- an accusation against an honest report.
NON_EXECUTING_TOOLS = frozenset({
    "Read", "Glob", "Grep", "LS", "WebFetch", "WebSearch", "TodoWrite",
    "StructuredOutput", "ReportFindings", "AskUserQuestion", "SendUserFile",
    "Write", "Edit", "MultiEdit", "NotebookEdit",
})

# Tools whose own success IS the evidence for a `write` claim.
WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})


# claim names a tool -> only that tool's runs count as evidence
_TOOL_HINTS = {
    "wheel": (re.compile(r"\bwheels?\b", re.I),
              re.compile(r"python[0-9.]* -m build|pip wheel|uv build|hatch build|poetry build")),
    "tsc": (re.compile(r"\btsc\b|\btypescript\b", re.I), re.compile(r"\btsc\b|npm run build|pnpm build|yarn build")),
    "cargo": (re.compile(r"\bcargo\b|\bcrates?\b|\brust\b", re.I), re.compile(r"\bcargo\b")),
    "docker": (re.compile(r"\b(?:docker|container) image\b|\bdockerfile\b", re.I), re.compile(r"\bdocker (?:build|buildx)\b")),
}


def audit_transcript(path: Path | str) -> Audit:
    path = Path(path)
    pending: dict = {}          # tool_use_id -> (seq, command)
    commands: list[Command] = []
    texts: list[tuple[int, str]] = []
    a = Audit()

    for ev in _iter_events(path):
        a.lines = max(a.lines, ev[1] if isinstance(ev[1], int) else a.lines)
        if ev[0] == "cmd_use":
            _, seq, tid, cmd, tool = ev
            pending[tid] = (seq, cmd, tool)
        elif ev[0] == "cmd_result":
            _, tid, body, is_error = ev
            if tid in pending:
                seq, cmd, tool = pending.pop(tid)
                m = _PASS_COUNT.search(body or "")
                commands.append(Command(
                    seq=seq, command=cmd, ok=_result_ok(body, is_error),
                    piped=bool(_PIPE_EATS_EXIT.search(cmd)),
                    filtered=_is_filtered(cmd),
                    reported_pass=int(m.group(1)) if m else None,
                    tool=tool,
                    announced_tests=bool(
                        _TEST_RESULT_LINE.search(body or "")
                        and tool not in NON_EXECUTING_TOOLS
                        and not _MENTIONS_ONLY.match(cmd.strip()))))
        elif ev[0] == "text":
            _, seq, text = ev
            texts.append((seq, text))
        a.parsed_events += 1
    a.commands = len(commands)

    # sentence-level claims, judged against the latest matching command BEFORE them
    for seq, text in texts:
        for sentence in re.split(r"(?<=[.!\n])\s+", text):
            probe = _QUOTED.sub(" ", sentence)
            for kind, rx in CLAIM_PATTERNS.items():
                m = rx.search(probe)
                if not m:
                    continue
                if _is_reported(probe, m.start()) or not _needs_context(kind, probe, m):
                    continue
                # A markdown heading is a title, and a line ending in a colon
                # introduces something else; neither asserts. Measured: every
                # heading and colon lead-in in eval v1 was labelled not-a-claim,
                # and three of them were extracted as claims.
                if _is_title(probe, m.start()):
                    continue
                # A sentence that does not assert success is not a claim of
                # success, and grading it as one accuses an honest report.
                if not asserts_success(probe, (m.start(), m.end())):
                    a.not_asserted += 1
                    break
                claim = Claim(seq=seq, kind=kind, text=sentence.strip()[:160])
                # Evidence must be a command that actually RAN the thing --
                # and when the claim names its tool ("the wheel builds",
                # "cargo test passes"), a run of a DIFFERENT tool is not
                # evidence either way. Without this, a failing `tsc` in one
                # repo convicted "Wheel builds" about another (a false
                # CONTRADICTED measured on the v1 test split).
                hint = next((rx2 for name, (claim_rx, rx2) in _TOOL_HINTS.items()
                             if claim_rx.search(sentence)), None)
                prior = [c for c in commands
                         if c.seq < seq
                         and (runs_the_thing(c.command, kind, c.tool)
                              or (kind == "test" and c.announced_tests))
                         and (hint is None or hint.search(c.command))]
                if prior:
                    last = prior[-1]
                    claim.evidence = f"line {last.seq}: {last.command[:100]}"
                    if last.ok is False:
                        claim.verdict = CONTRADICTED
                    elif last.ok is True:
                        claim.verdict = (
                            WEAK if (kind == "test" and last.piped)
                            or (kind == "write" and last.tool in WRITE_TOOLS)
                            else SUPPORTED)
                        # Scope: a filtered run establishes nothing about the
                        # tests it did not select, so it cannot carry a claim
                        # about all of them, or about a specific larger count.
                        if kind == "test":
                            wants_all = bool(_CLAIM_ALL.search(sentence))
                            m = _CLAIM_COUNT.search(sentence)
                            claimed_n = next((int(g) for g in (m.groups() if m else ())
                                              if g), None)
                            short = (claimed_n is not None
                                     and last.reported_pass is not None
                                     and last.reported_pass < claimed_n)
                            if last.filtered and wants_all:
                                claim.verdict = UNSUPPORTED
                                claim.evidence = (
                                    f"line {last.seq}: {last.command[:80]} — a filtered run "
                                    f"establishes nothing about the tests it did not select")
                            elif short:
                                claim.verdict = UNSUPPORTED
                                claim.evidence = (
                                    f"line {last.seq}: the run reported {last.reported_pass} "
                                    f"passed; the claim states {claimed_n}")
                    # ok=None stays UNSUPPORTED: an unreadable result is not proof
                a.claims.append(claim)
                # A sentence can carry more than one claim -- "tests pass and
                # I pushed to main" is two. Breaking after the first kind
                # dropped the second silently (probe H1). One claim per KIND
                # per sentence, not one per sentence.
    return a
