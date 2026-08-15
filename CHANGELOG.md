# Changelog

All notable changes to this project are documented here.  
Format inspired by [Keep a Changelog](https://keepachangelog.com/).  
Versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Planned

- PyPI package name (`aurumflux-coherence` if needed)  
- Stronger decision checks without false positives  

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
- Architecture docs, MIT license, demo CLI  

[Unreleased]: https://github.com/aurumflux20/coherence/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/aurumflux20/coherence/releases/tag/v0.3.0
[0.2.0]: https://github.com/aurumflux20/coherence/releases/tag/v0.2.0
[0.1.0]: https://github.com/aurumflux20/coherence/releases/tag/v0.1.0
