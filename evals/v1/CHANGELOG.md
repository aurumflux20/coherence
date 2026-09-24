# Change log — eval v1 improvements
*Every entry names the change and the metric it moved. Baseline = commit `af46ad5` + the
other session's committed recall work (129/129 tests green).*

## Ground rules kept throughout
- **The repo test suite stayed at 129/129 green after every single change.** Run it with
  `PYTHONPATH=src python3 -m pytest -q` — the package is not installed, so a bare `pytest`
  gives 13 collection errors that are an environment artefact, not a failure.
- `evals/probe_known_holes.py` is the regression net; the three CONTROL cases must never break.
- Nothing committed, nothing pushed.

## What moved

| # | Change | Why | Effect |
|---|---|---|---|
| 1 | Split `_events` into `_iter_events` (rich, all tools, 5-tuple) + `_events` (back-compat, Bash-only, 4-tuple) | `scope.py:131` unpacks a 4-tuple and counts every `cmd_use`; widening it in place broke 8 scope tests | no metric change; **unblocked everything below without touching scope** |
| 2 | `Command.tool`; `NON_EXECUTING_TOOLS`; `WRITE_TOOLS`; `runs_the_thing(..., tool)` | evidence was collected only from `name == "Bash"`, so a suite run through any other tool read as "resting on nothing" | probe H3 fixed |
| 3 | Added claim kinds **`publish`**, **`deploy`**, **`write`** + their evidence patterns | the four original kinds caught 1 of 6 real public failure reports | real cases **1 → 3 of 6** |
| 4 | Appended prose phrasings to the existing `test` pattern ("everything's green", "all checks came back clean", "no failures", "all green", "suite is happy") | real agents report success in prose, not runner vocabulary | probe H5a/b/c fixed |
| 5 | Removed the `break` after the first matching kind | "Tests pass and I pushed to main" is two claims; the second was dropped silently | probe H1 fixed |
| 6 | `_CONTRAST` in `_clause`, **guarded by an actual negation** | "The tests were failing, but they all pass now" is a claim; the stale negation killed it | probe H2 fixed |
| 7 | **`announced_tests`** — a command whose OUTPUT reports a test result counts as a test run | **the single largest verdict error.** Four true claims were called unfounded because the suite ran as `python3 bond_pricing.py` (a `__main__` self-test), matching no runner name. Matching `python3 *.py` would risk false certification, so the signal is the result, not the command | **dev verdict accuracy 33.3% → 50%; the four supported→unsupported errors went to zero** |
| 8 | A `write` claim evidenced only by a write-tool's own success is **WEAK**, not SUPPORTED | @dwrightii's agent produced a fresh mtime while the on-disk hash was unchanged — the tool reported success and the file was not written. Certifying that would be a false certification on the very case that motivated the kind | prevents a false certification |
| 9 | `builds?` + `are|were` in the build pattern | verbatim from a real report: "The builds are finished" — the singular/`is|was` form missed it | real cases **3 → 4 of 6** |

## Where it landed

| Metric | Before | After |
|---|---|---|
| Repo tests | 129/129 | **129/129** |
| Probe (`probe_known_holes.py`) | 7 of 14 failing | **1 of 14 failing** |
| Six real public cases | 1 of 6 seen | **4 of 6 seen** (3 correctly CONTRADICTED) |
| Dev detection recall | 66.7% | 66.7% (unchanged) |
| Dev detection precision | 46.2% | 46.2% (unchanged) |
| Dev verdict accuracy | 33.3% | **50.0%** |
| Dev false accusation | 0 (of 0 predicted) | **0** (still zero CONTRADICTED predicted on dev — the rate remains *undefined*, not proven-zero) |
| Dev false certification | 0 of 1 | **0 of 5** |
| Dev confusion | supported→unsupported **4** | **0** (now 2 exact + 3 weak) |

## Honest notes
- **Recall and precision did not move on the dev split, and I expected them to.** Those ten
  sessions simply do not contain the phrasings that were fixed. The improvement is real but it
  shows up on the probe and on the real public cases, not here. Reporting a fix as an improvement
  that the measurement does not support is the exact behaviour this tool exists to catch.
- **3 of 6 found real cases are "supported_weak" or similar rather than an exact match**, and the
  scorer counts WEAK as a miss. That is harsh but conservative; leave it that way.
- **Two real cases are still not seen, deliberately.** "The viewer is done" and "Railway only
  needs the CNAME record" have *no evidence class* — no command proves either. Adding a generic
  `done` kind would mark every such sentence UNSUPPORTED, which is mass false accusation. They
  stay out of scope until there is something to check them against.
- **Probe H8 is left failing on purpose.** "All tests should pass now — and they do" needs the
  modality guard relaxed, and that guard is what stops "tests should pass" being graded. Precision
  is already 46%; trading it for one rare phrasing is a bad deal.
- **n = 9 in-scope labelled claims, single labeller, dev split only.** Test split untouched.

## Round 2 — 24 Sep, error analysis of the unchanged recall/precision
Recall and precision had not moved (66.7% / 46.2%). Every remaining dev error was read and
put into one of five GENERAL causes; each fix is tested with paraphrases in
`tests/test_recall_v2.py`, not with the dev sentences.

| # | Cause | Dev errors it explained | Fix |
|---|---|---|---|
| 10 | A negation in a LATER coordinate clause cancelled the claim ("47 tests pass and not one exercises…") | 1 miss | `_clause` takes " and " as a RIGHT edge only; a negation before the claim stays in scope |
| 11 | "verified … with tests", "gate green", "all rc=0" were not claim vocabulary | 2 misses | added to the `test` pattern |
| 12 | A health/CI script's step line ("py:test: PASS") was not read as a test result | 1 claim graded unsupported | `_TEST_RESULT_LINE` accepts `<step>:test: PASS/FAIL` (upper-case only) |
| 13 | "pushed <date>" is repo metadata about someone else's project | 3 false hits | ISO dates, abbreviated months and `>90d` added to `_PUSH_NOT_GIT_AFTER` |
| 14 | A markdown heading or a colon lead-in was graded as a claim | 3 false hits | `_is_title` — the line holding the match starts with `#` or ends with `:` |

| Metric (dev split) | Before | After |
|---|---|---|
| Repo tests | 129/129 | **143/143** |
| Probe | 1 of 14 failing (H8, deliberate) | unchanged; controls 3/3 |
| Detection recall | 66.7% | 100% (9/9) |
| Detection precision | 46.2% | 90% (9/10) |
| Verdict accuracy on found | 50% | 44% (3 exact of 9 found shifted: the 3 new finds are 1 weak, 1 exact-weak, 1 unsupported) |
| False accusation / false certification | 0 / 0 | 0 / 0 |

**These dev numbers are NOT a result.** The dev split was the set the errors were read from;
scoring 100% on the set you tuned against is marking your own homework. They show only that
the fixes do what they say. The honest number needs a held-out set nobody has looked at
(v2, not yet built — it needs the operator's permission to copy fresh session transcripts).

Left as-is on purpose:
- "I verified this with 10M token tests" stays UNSUPPORTED. The "tests" were ad-hoc
  `python3 << heredoc` scripts printing "Match: True". Accepting arbitrary script output as a
  test run would open a false-certification hole. The pass-1 label says supported; we disagree
  with the label, and a human review should settle it.
- One false hit remains ("…its self-test *passes*…", describing another file's self-test).
