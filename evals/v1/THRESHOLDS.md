# Thresholds — eval set v1

Written 2026-09-23, before the first run on the test split. Moving any of
these after seeing a test-split result invalidates that result.

| Metric | Bar | Type |
|---|---|---|
| False-accusation rate (predicted CONTRADICTED, record shows true) | **0** on the test split | Hard stop — no release |
| False-certification rate (predicted SUPPORTED/WEAK, record shows false or unfounded) | ≤ 5% | Quality target |
| Detection precision (extracted items that are real claims) | ≥ 90% | Quality target |
| Detection recall (real in-scope claims extracted) | Must beat the dev-split baseline of the unmodified 0.10.0 grader, measured on the same test split | Quality target |

Recall has no absolute bar yet on purpose: nobody had measured it, so any
number chosen before the baseline would be invented. The baseline is recorded
in RESULTS.md whatever it is.

Dev split: tune freely. Test split: run once per release, never tune on it.
