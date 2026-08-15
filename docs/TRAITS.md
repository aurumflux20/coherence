# Traits of great code (what Coherence must not miss)

We use this checklist when reviewing our own work and PRs.

## 1 · Correctness

| Trait | Meaning here |
|-------|----------------|
| **Law-shaped** | Empty evidence ⇒ not done; empty next ⇒ error |
| **Fail closed** | Bad input raises with a **NEXT**, never silent wrong PROVEN |
| **Tested** | Unit tests for Fact, rungs, dominos, memory |
| **Honest limits** | Docs say what we do **not** claim |

## 2 · Clarity

| Trait | Meaning here |
|-------|----------------|
| **One idea per module** | Fact is the atom; rungs are costumes |
| **Names match meaning** | `said` / `prove` / `solve_domino` |
| **Readable without a tour** | `python -m coherence law` is enough to start |
| **5th-grade law, adult edges** | Simple rule, precise failure modes |

## 3 · Simplicity (320 IQ)

| Trait | Meaning here |
|-------|----------------|
| **Delete until it hurts** | No feature that doesn’t enforce the law |
| **Stdlib core** | No required heavy deps for the kernel |
| **Small public API** | `Coherence`, `Fact`, demos |

## 4 · Reliability

| Trait | Meaning here |
|-------|----------------|
| **Deterministic tests** | No network, no flaky time races in unit tests |
| **Idempotent lessons** | Memory append-only, not rewrite history silently |
| **Cascade order** | Cannot solve domino N+1 before N |

## 5 · Security & hygiene

| Trait | Meaning here |
|-------|----------------|
| **No secrets in repo** | No keys, tokens, private URLs with creds |
| **SECURITY.md** | Private report path |
| **Dependency minimal** | Smaller attack surface |
| **Input validation** | Empty claim/next/evidence paths blocked |

## 6 · Open-source completeness (GitHub)

| Trait | File / practice |
|-------|-----------------|
| Discoverable pitch | `README.md` |
| License | `LICENSE` (Apache 2.0) |
| How to help | `CONTRIBUTING.md` |
| Community norms | `CODE_OF_CONDUCT.md` |
| Vuln process | `SECURITY.md` |
| History | `CHANGELOG.md` |
| Help map | `SUPPORT.md` |
| Automation | `.github/workflows/ci.yml` |
| Issue/PR templates | `.github/` |
| Reproducible install | `pyproject.toml` + `pip install -e .` |
| Isolation | Own repo; not seal monorepo |

## 7 · Empathy for the ideal user

| Trait | Meaning here |
|-------|----------------|
| **Staff/DevEx bottleneck** | Saves verification time, not adds ceremony |
| **30-second demo** | `python -m coherence demo` |
| **Badge-ready later** | Facts can become CI signals |

## PR self-score

Before merge, answer:

1. Does it strengthen **evidence** or **next**?  
2. Would a tired staff eng understand the README change?  
3. Did tests fail when we broke the law on purpose?  
4. Did we add weight without law?  

If (4) is yes → cut.
