# Results — eval v2, fresh held-out set (24 Sep 2026)

Scored ONCE, with the code at commit `1514695`+ (round-2 detection fixes). Aggregates only:
the labelled sentences are private session content and are not published.

## Why v2
The v1 dev split was used to find and fix errors (it now scores 9/9 recall — meaningless),
and the v1 test split had been run twice. v2 is 20 sessions nobody had looked at.

## Method
- **Sessions:** seeded random sample (seed 20260924) of 34 eligible sessions (≥3 Bash calls,
  ≥8 assistant texts), excluding every v1 source and any session that discusses this eval.
  Redacted locally; `evals/build_corpus_v2.py`. Redaction leak check: none.
- **Candidates:** `evals/extract.py` — 9,223 wide-net sentences, 36,183 outside it.
- **Pool** (`evals/make_pool_v2.py`): 300 random wide-net sentences (for recall), 120 random
  auditor extractions (for precision; 11 of 491 extractions could not be joined to a
  candidate and were not sampleable), 60 outside-net sentences. 475 unique items, shuffled,
  strata hidden.
- **Labels:** stage A (is it a claim?) by one model labeller from the sentence alone; stage B
  (was it true?) by three model labellers from the 12 prior tool calls. Labellers read only the
  guides (`evals/v1/LABELLING.md` + `LABELLING-v2.md`) and their input; none saw the auditor's
  output or the stratum. **Model-drafted, not human-reviewed.**
- **Scorer:** `evals/score_v2.py`, written before the labels were read.

## Numbers

| Metric | Value |
|---|---|
| Detection recall (random stratum) | **13 / 33 = 39.4%** (95% CI 24.7–56.3%) |
| … adjusted for claims outside the wide net | ~25% — **very noisy**: rests on 1 claim in a 60-sentence outside sample |
| Detection precision (extracted stratum) | **96 / 119 = 80.7%** (95% CI 72.7–86.8%) |
| Verdict accuracy, exact (n=105) | **59.0%** |
| Verdict accuracy, weak ≈ supported | 72.4% |
| False certification (said backed, record doesn't back it) | **16 / 88 = 18.2%** |
| False accusation (wrong CONTRADICTED) | **0 / 0** — it predicted no CONTRADICTED at all; the 3 true contradicted claims were graded supported (1) and unsupported (2) |
| True supported graded "unsupported" | 10 / 69 = 14.5% |

Recall by kind (random stratum): test 8/15 · push 2/4 · commit 1/3 · deploy 1/4 · build 1/1 · write 0/5 · publish 0/1.

## What it says, plainly
1. **The v1 held-out headline (88% verdicts right, 3% wrongly unsupported) did not reproduce.**
2. **False certification is the biggest risk.** Most of the 16 are one mechanism: the auditor
   takes the latest *matching* run anywhere earlier in the session, so a claim like "7 pass"
   or "All 181 tests pass" is certified by an unrelated or older run. Part of the 18% may be a
   labelling artefact: labellers saw only the 12 prior calls, the auditor sees the whole
   session. Neither side has been checked by a person.
3. **Recall misses** are mostly `write` ("written to the vault", "added to the doc"), bare SHAs
   ("One commit, `448db088`"), "pushed too", and counts in unusual shapes ("Tested 4 times, passed 4 times").

## Rules for what happens next
- v2 has now been scored. Fixes informed by these errors must be measured on a v3 set, not on v2.
- Until a person reviews a sample of labels, every number here is provisional.
