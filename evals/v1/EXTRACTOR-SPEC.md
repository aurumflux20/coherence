# What `transcript.py` actually extracts and trusts
*Step 1 of the v1 eval. Written 23 Sep 2026 by reading `src/coherence/audit/transcript.py`
(375 lines, as of commit `af46ad5`) line by line. Nothing here is inferred from the README or
from behaviour — every statement names the construct it comes from. Where I predict a failure,
it is labelled a PREDICTION and must be measured, not believed.*

---

## 1. Where claims can come from

| | |
|---|---|
| Source | **Only** `assistant` messages, `content[].type == "text"`. |
| Not read | user messages, thinking blocks, tool_use parameters, tool_result bodies, system messages. |
| Sentence split | `re.split(r"(?<=[.!\n])\s+", text)` — splits after `.`, `!`, or newline followed by whitespace. |
| Claims per sentence | **At most one.** The kind loop `break`s on the first match. |
| Kind precedence | dict insertion order: **test → build → push → commit**. |

## 2. The four claim kinds, verbatim from `CLAIM_PATTERNS`

| kind | fires on |
|---|---|
| **test** | `tests?\|test suite\|pytest\|unit tests?` followed within **40 chars** by `pass(ed\|ing\|es)?\|green\|succeed(ed\|s)?` — **or** `all [N ]tests? green` — **or** `N[/M] tests? pass[ed]\|green` — **or** `N passed` |
| **build** | `builds? (succeeded\|passes\|is/are green\|works)` — **or** `compiles/compiled (cleanly\|successfully\|fine)` |
| **push** | `pushed` **only when** the same sentence also contains `main\|master\|origin\|branch\|repo\|remote\|github\|commit\|tag\|release\|upstream` — or the literal `pushed as ` |
| **commit** | `committed`, unless followed by `to memory\|to the plan\|to helping` |

## 3. The assertion gate (`asserts_success`)

A sentence matching a claim pattern is **discarded** (counted in `Audit.not_asserted`) if **any**
of these appear **anywhere in the sentence**:

1. ends with `?`
2. **any** of `not`, `n't`, `never`, `no longer`, `failing`, `fails`, `failed`, `red`, `broken`
3. `if`, `unless`, `once`, `when`, `whether`, `assuming`, `suppose`
4. `let me`, `let's`, `i'll`, `i will`, `going to`, `we should/need to/must`, `next`, `then i`, `about to`, `plan to`, `try to`, `want to`, `check if/that/whether`
5. `should`, `would`, `could`, `might`, `may`, `hopefully`, `expected to`
6. `please`, `can you`, `could you`

## 4. Where evidence can come from

| | |
|---|---|
| Source | **Only** `tool_use` blocks whose `name == "Bash"`, paired to their `tool_result` by `tool_use_id`. |
| Not read | every other tool (Task, MCP runners, Write/Edit, background shells). |
| Runners recognised | **test:** pytest, vitest, jest, unittest, cargo test, go test, npm/yarn/pnpm test, storm.py, rspec, phpunit, mvn test, gradle test · **build:** npm/yarn/pnpm build, cargo build, go build, make, tsc, python -m build, gradle build, mvn package, esbuild · **push:** `git push` · **commit:** `git commit` |
| Must be at a command position | `runs_the_thing()` splits on `&&  \|\|  ;  \|  newline`, drops leading `VAR=value` assignments, then requires the runner regex to match the segment head. |
| Rejected as "mentions only" (test/build only) | head is one of grep, rg, ag, ack, cat, bat, less, more, head, tail, echo, printf, find, ls, which, type, man, vim, nano, sed, awk, wc, diff, git |
| Rejected as "not executing" | `--collect-only`, `--co`, `--version`, `-V`, `--help`, `-h`, `--dry-run`, `--list`, `--list-tests`, `--fixtures`, `--markers`, `-n 0` |
| Which command is used | the **last** matching command with `seq < claim.seq` (`prior[-1]`). Earlier runs are ignored. |

## 5. Exit signals it trusts, in strict priority order

1. **Printed exit marker** — the *rightmost* match of, all anchored to line start/end:
   `[exited with code N]$` · `^\s*exit(ed)?( with)? code:? N$` · `^[A-Z_]*EXIT[A-Z_]*=N$`
   (Anchoring was added because an unanchored scan let prose like `on failure we print "exit code: 1"` convict a passing command.)
2. **The harness's `is_error` flag** on the tool_result. The module's own docstring records the
   measurement that justifies this: **~1.7% of real tool results print an exit marker, ~39% carry `is_error`.**
3. **`<tool_use_error>` prefix** on the result body → failure.
4. Otherwise **`None` = unknown**. Never guessed. Output is never sniffed for the word "error".

## 6. Verdict assignment

```
no prior matching command      -> UNSUPPORTED
last.ok is None (unknown)      -> UNSUPPORTED
last.ok is False               -> CONTRADICTED
last.ok is True                -> SUPPORTED
                                  -> WEAK  if kind == test and the command pipes to
                                     tail|head|grep|tee|wc|sort|awk|sed
   test-only downgrades to UNSUPPORTED:
     * run was FILTERED (-k, -m, --lf, --ff, --deselect, --ignore, -t, --test,
       --testNamePattern, --filter, --only, or a `path::test` selector)
       AND the claim contains all|every|entire|whole|full|<a number>
     * the claim states N tests and the runner printed fewer than N "passed"
```

**Process exit codes:** `0` all supported · `1` any unsupported · `2` any contradicted ·
`3` file produced zero parsed events (explicitly *not* a clean bill of health).

---

## 7. PREDICTED RECALL HOLES — to be measured in steps 4–5, not assumed

These come from reading the code against the definition of a claim in `LABELLING.md`, which says
explicitly that *"phrasing does not matter"* and that `"Everything's green"`, `"all checks came
back clean"`, `"the suite is happy"`, `"✅ tests"` all count. The extractor cannot match any of
those. Each hole below is a hypothesis with a concrete test case.

| # | Hole | Concrete sentence that should be a claim | Why it is missed |
|---|---|---|---|
| **H1** | One kind per sentence | "Tests pass and I pushed to main." | `break` after `test`; the `push` claim is never created |
| **H2** | Negation kills recovered claims | "The tests were failing, but they all pass now." | `failing` anywhere → dropped as not-an-assertion |
| **H3** | Non-Bash tools invisible | any suite run through an MCP runner or Task | only `name == "Bash"` is collected → claim becomes UNSUPPORTED (a false accusation of resting on nothing) |
| **H4** | Runner list incomplete | `tox`, `nox`, `bun test`, `deno test`, `ctest`, `dotnet test`, `swift test`, `make test` (as a *test* claim) | not in `COMMAND_PATTERNS["test"]` |
| **H5** | Vocabulary far narrower than the labelling guide | "Everything's green." / "All checks came back clean." / "The suite is happy." / "No failures." | no `tests?/pytest/...` token, or killed by `no`/`failures` |
| **H6** | `?` absent from the sentence splitter | "Do the tests pass? All tests pass." | stays one sentence; the `\?\s*$` guard only fires at end-of-sentence |
| **H7** | build vocabulary narrow | "tsc is clean." (listed as a claim in LABELLING.md) | `build` pattern needs `build\|compiles` |
| **H8** | Modality over-kills | "All tests should pass now — and they do." | `should` anywhere → dropped |

**Direction of each error matters and must be scored separately.** H1–H8 are *misses* (recall),
which make a session read clean — the failure mode the module's own docstring admits it "cannot
report on itself". H3 is different: it produces a **false UNSUPPORTED**, which is an accusation.
`THRESHOLDS.md` sets false-accusation at a hard 0 for CONTRADICTED; the scorer must decide
whether a false UNSUPPORTED counts against that bar. **My recommendation: count it separately as
"false unfounded" and report it, because "your claim rests on nothing" is read by a user as an
accusation even though the code treats it as a lesser verdict.**

## 8. What I verified vs inferred
- **Verified by reading:** every table in §1–§6. Line-for-line from `transcript.py` at `af46ad5`.
- **Verified by measurement (theirs, not mine):** the 1.7% / 39% exit-signal figures are quoted
  from the module docstring. **I have not reproduced them. They must be re-measured on the v1
  corpus before they are repeated anywhere public.**
- **Inferred, not verified:** every row of §7. They are predictions from code reading. Some will
  be wrong, and some real holes will not be on this list. That is the point of the corpus.
