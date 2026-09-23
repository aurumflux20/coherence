# Results — eval set v1

**Status: provisional.** Labels were drafted by a model (Claude) following
[LABELLING.md](LABELLING.md) without seeing the auditor's output. Human review
of the contradicted items, the misses and a 20% sample is still to be done;
these numbers will be updated, not quietly replaced, when it is.

## The corpus
- 20 real Claude Code sessions from our own work (Aug–Sep 2026), chosen at
  random (seed 20260923) from the 37 of 97 sessions with ≥ 20 shell commands.
- Split by session: 10 dev (tuning allowed), 10 test (held out).
- 10,162 candidate sentences labelled. Candidates are every assistant sentence
  caught by a deliberately wide vocabulary net, plus a random 400 from the
  41,540 sentences outside that net. **0 of the 400 outside the net were
  claims**, so the net is not hiding a large block of misses.
- 757 in-scope claims found by labellers (test / build / push / commit):
  525 dev, 232 test.
- Transcripts are private and are not in this repository.
  [manifest.json](manifest.json) records their SHA-256 digests.

## Test split — 0.10.0 vs 0.11.0

| | 0.10.0 | 0.11.0 |
|---|---:|---:|
| **Detection recall** — real claims the auditor found | 48 / 232 = **20.7%** | 101 / 232 = **43.5%** |
| **Detection precision** — extracted items that are real claims | 48 / 64 = 75.0% | 101 / 117 = 86.3% |
| **Verdict accuracy** on real claims found (supported and weak counted together) | 26 / 48 = 54.2% | 88 / 100 = 88.0% |
| True claims wrongly graded **unsupported** ("rests on nothing") | 19 / 44 = **43%** | 3 / 90 = **3%** |
| **False accusations** — graded CONTRADICTED, record shows true | 0 / 0 | 0 / 0 |
| False certifications — graded supported, record shows unfounded | 3 / 28 = 10.7% | 9 / 96 = 9.4% |

Dev split, 0.11.0: recall 52.4% (275 / 525), precision 89.0%.

## Against the thresholds set before the test run ([THRESHOLDS.md](THRESHOLDS.md))

| Bar | Result |
|---|---|
| False accusations = 0 | **Met** on the final run — see the disclosure below |
| False certification ≤ 5% | **Missed** — 9.4% |
| Detection precision ≥ 90% | **Missed** — 86.3% |
| Recall beats the 0.10.0 baseline | **Met** — 20.7% → 43.5% |

## Disclosure: the test split was run more than once
The first 0.11.0 run on the test split produced **one false accusation**: a
table row "Wheel builds | 0" was convicted by a failing `tsc` run in a
different repository. Reading the test errors also exposed a bug present
since 0.10.0: the `-m` in `python3 -m pytest` was read as a pytest marker
filter, so full-suite runs were treated as partial and true claims were graded
UNSUPPORTED. Both were fixed (tool-named claims are now judged only by that
tool; the filter check reads only the runner segment) and the test split was
re-run. Because test-split errors informed those fixes, the final test numbers
are optimistic. Eval set v2 will add sessions never looked at as a fresh
held-out split.

## What the auditor still misses (dev split, largest groups)
- Claims inside markdown tables and status boards.
- "Tested and working", "built, tested, shipped", "everything green" — success
  stated without a count or a runner name.
- Push and commit claims phrased as outcomes: "Shipped — `4ab65bb`",
  "on main and deploying", "local == origin/main".
- Evidence that arrives through a tool other than the shell, or a check run
  in CI and read with `gh run list`.

## Known structural limit
Evidence is matched by command, not by project. A test run in one repository
can support — or, rarely, contradict — a claim about another. Tool-named
claims are protected; unnamed ones are not yet.

## Reproduce
```bash
python evals/extract.py <transcripts_dir> candidates.jsonl --sample-outside 400
python evals/detect.py  <transcripts_dir> candidates_full.json stageA.jsonl evals/v1/manifest.json --split test
```
