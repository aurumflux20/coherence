# Coherence

[![CI](https://github.com/aurumflux20/coherence/actions/workflows/ci.yml/badge.svg)](https://github.com/aurumflux20/coherence/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub](https://img.shields.io/badge/github-aurumflux20%2Fcoherence-black)](https://github.com/aurumflux20/coherence)

### One law. Two fields. Everything else is costume.

```text
Nothing is done unless there is evidence.
Nothing is finished unless there is a next.
Nothing is remembered unless it was done.
```

**Coherence** helps engineers verify **AI agent work**: what was *said*, what was *shown*, and what to do **next** — so agent PRs stop living on chat vibes.

Standalone public repo under [AurumFlux](https://github.com/aurumflux20).  
**Not** a monorepo with [seal](https://github.com/aurumflux20/seal) or [effectfence](https://github.com/aurumflux20/effectfence).

---

## Why it exists

Agents write code fast. Humans become the **verification bottleneck**.

- “Tests passed” in chat ≠ exit code  
- Mystery skills/MCP installs  
- Specs forgotten mid-PR  
- Review flood with no priority  

Coherence is a **small Python library + CLI** that records reality as **Facts** and optional **domino** cascades that evolve as you solve problems.

Ideal user: **staff engineer / tech lead / DevEx** who ships with coding agents daily.

---

## Install

```bash
# from GitHub
pip install "git+https://github.com/aurumflux20/coherence.git"

# or clone (dev)
git clone https://github.com/aurumflux20/coherence.git
cd coherence
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

**Requires:** Python 3.10+ · **Dependencies:** none (stdlib only)

---

## 30-second start

```bash
python -m coherence law      # the whole product in three sentences
python storm.py              # hostile proof (EffectFence-style) — must exit 0
python -m coherence demo     # rungs 1–5
python -m coherence evolve   # dominos + memory flywheel
```

**Proof first:** [STORM-PROOF.md](STORM-PROOF.md) — chat never DONE, memory only from evidence, dominos ordered, evolution compounds.

```python
from coherence import Coherence

c = Coherence()
c.said("tests passed in chat", next="run pytest and attach exit code")
c.prove("pytest -q", evidence="exit_code=0", next="chain complete")
print(c.plain_english())
```

### CI ship feature (agents can’t fake green)

```bash
python -m coherence prove-cmd "pytest -q" --claim "unit tests"
python -m coherence check              # exit 1 if open facts
python -m coherence report --out coherence-report.md
```

Copy-paste Action: [docs/CI.md](docs/CI.md) · dogfood workflow: `.github/workflows/coherence-pr.yml`

More: [`examples/basic_fact.py`](examples/basic_fact.py) · [`examples/full_rungs.py`](examples/full_rungs.py)

---

## The atom: Fact

| Field | Rule |
|-------|------|
| **evidence** | empty ⇒ **not done** |
| **next** | empty ⇒ **illegal** (Gilbert) |
| **remember** | only if **done** |

Rungs are **costumes** for the same Fact:

```text
7  evolution   remember only DONE facts
6  dominos     ordered cascade; next names the next stone
5  review      what needs human eyes
4  replay      re-check evidence
3  decisions   locked project rules
2  skills      install bill of materials
1  claimproof  said vs evidence
```

Philosophy: [docs/320IQ.md](docs/320IQ.md)

---

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/INDEX.md](docs/INDEX.md) | Full map |
| [docs/CI.md](docs/CI.md) | **PR check + badge (ship feature)** |
| [docs/DISTRIBUTION.md](docs/DISTRIBUTION.md) | **How people find us** |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Rung design |
| [docs/EVOLUTION-AND-DOMINOS.md](docs/EVOLUTION-AND-DOMINOS.md) | Cascades + learning |
| [docs/TRAITS.md](docs/TRAITS.md) | Traits of great code (our bar) |
| [CHANGELOG.md](CHANGELOG.md) | Versions |
| [SUPPORT.md](SUPPORT.md) | Help + related projects |

---

## Development & CI

```bash
pip install -e ".[dev]"
python -m unittest discover -s tests -v
```

CI runs on Python 3.10–3.12 (see `.github/workflows/ci.yml`).

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md) · Conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

---

## Security

Report vulnerabilities privately — [SECURITY.md](SECURITY.md).  
Do **not** open public issues for security bugs.

---

## Honest limits

| We do | We do not |
|-------|-----------|
| Record claim vs evidence + next | Stop offline rogue tools with stolen keys |
| Local/stdlib kernel | Replace GitHub or your CI vendor |
| Optional lesson memory on disk | Hosted multi-tenant SaaS in this repo |
| Link to sibling AurumFlux tools | Share git history with seal/effectfence |

---

## Related (separate repos)

| Repo | Role |
|------|------|
| [effectfence](https://github.com/aurumflux20/effectfence) | Causal concurrency fence |
| [seal](https://github.com/aurumflux20/seal) | Production admission / gateway |
| [fencescan](https://github.com/aurumflux20/fencescan) | Static double-effect scan |

---

## License

[MIT](LICENSE) © AurumFlux
