# Changelog

All notable changes to this project are documented here.  
Format inspired by [Keep a Changelog](https://keepachangelog.com/).  
Versioning: [SemVer](https://semver.org/).

## [0.11.0] — 2026-09-23

Measured for the first time against real sessions: eval set v1, 20 Claude Code
transcripts, every checkable claim hand-labelled. Full method and disclosures:
[evals/v1/RESULTS.md](evals/v1/RESULTS.md). Held-out split, 0.10.0 → 0.11.0:
recall 20.7% → 43.5%, precision 75.0% → 86.3%, verdict accuracy 54.2% → 88.0%,
true claims wrongly graded "unsupported" 43% → 3%.

### Fixed
- `python3 -m pytest` was read as a marker-filtered run (the `-m`), so full-suite
  runs could not support "all N tests pass" claims. The filter check now reads
  only the runner segment.
- A claim that names its tool ("the wheel builds", "cargo test passes") is
  judged only by that tool's runs; a failing run of another tool no longer
  convicts it.
- A negation in a later clause no longer cancels a claim in an earlier one
  ("**Committed locally.** It's not wrong…"). "0 failed", "no failures" and
  "zero bugs" read as success, not negation.

### Added — claim phrasings found on real sessions
- Counts without the word "test": "14 pass", "26 passing", "69/69 green", "All 15 pass".
- CI results: "CI green on both workflows" (evidence: `gh pr checks`).
- Bare push and commit reports: "Pushed.", "Fixed and pushed.", "Committed."
- Build phrasings: "Build: success", "build is finished", "wheel builds", "tsc clean".

### Changed — fewer things that are not claims
- Quoted and reported claims ("the agent said tests pass") are not claims.
- "Pushed" about other people's repos, people, or page layout is not a push.
- "Committed" without git context ("committed to the plan", "pre-committed")
  is not a commit.
- Partial results ("79 passed, 8 failed", "8/9 pass") are failure reports,
  never success claims.
- `coherence audit` prints one line pointing to the paid Snapshot when it
  finds unsupported or contradicted claims. `COHERENCE_NO_OFFER=1` hides it.

### Eval harness
- `evals/extract.py`, `evals/detect.py`, `evals/score.py`; labelling guide,
  thresholds set before the test run, results. Transcripts stay private.

## [0.6.0 – 0.10.0] — 2026-08-17 → 2026-09-10

Published to PyPI as `coherence-check`; see the git log for detail. Highlights:
signed attestations (DSSE / in-toto, Sigstore Rekor anchor), `audit --out`
signable sessions, conformance recording, and the 0.10.0 grader fix that stopped
accusing honest failure reports.

## [Unreleased]
- checklist: consequential claims (money, deploy, data, security profiles) must carry proof before merge; `coherence checklist`.

## [0.5.1] — 2026-08-15

### Added

- `python -m coherence health` — law + tests + storm report  
- Scheduled workflow `health-scheduled.yml` (daily UTC 14:00)  
- [docs/HEALTH.md](docs/HEALTH.md) — timely health vs honest self-heal limits  

## [0.5.0] — 2026-08-15

### Added

- **`storm.py` + STORM-PROOF.md** — EffectFence-style hostile proof (7 claims)  
- Evolution **hash chain** + `verify_chain()` (append-only integrity)  
- CI runs storm; README: proof first, then deepen evolution  

## [0.4.0] — 2026-08-15

### Added

- **CI ship feature:** `prove-cmd`, `said`, `check`, `report`  
- Session file `.coherence/session.json`  
- Markdown + shields badge URL in report  
- Dogfood workflow `.github/workflows/coherence-pr.yml`  
- [docs/CI.md](docs/CI.md) · [docs/DISTRIBUTION.md](docs/DISTRIBUTION.md)  

## [0.3.0] — 2026-08-15

### Added

- **Fact** atom (`claim` / `evidence` / `next`) — 320 IQ core law  
- `Coherence.said` / `Coherence.prove`  
- `docs/320IQ.md`, `python -m coherence law`  
- Evolution memory refuses empty proof  

### Changed

- README centered on one law, two fields  

## [0.2.0] — 2026-08-15

### Added

- Domino chains (rung 6) + Gilbert-required `next_action`  
- Evolution memory (rung 7) with optional file persistence  
- `python -m coherence evolve`  
- `docs/EVOLUTION-AND-DOMINOS.md`  

## [0.1.0] — 2026-08-15

### Added

- Initial public spine: claimproof, skills, decisions, replay, review  
- Shared `Bundle` / `Record` / `Truth`  
- Architecture docs, Apache 2.0 license, demo CLI  

[Unreleased]: https://github.com/aurumflux20/coherence/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/aurumflux20/coherence/releases/tag/v0.3.0
[0.2.0]: https://github.com/aurumflux20/coherence/releases/tag/v0.2.0
[0.1.0]: https://github.com/aurumflux20/coherence/releases/tag/v0.1.0
