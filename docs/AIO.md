# Authority–Intent–Outcome (AIO) — Phase 1 (Coherence)

## The problem (plain)

When a human pays, one click often meant: who, what they meant, and that money moved.  
When an **agent** touches money, those split apart. Chat saying “tests passed” or “refunded” is not proof.

**AIO** = continuously answer, in evidence form:

1. **Authority** — who/what was allowed to act  
2. **Intent** — what scoped action was meant  
3. **Outcome** — whether the rail’s settled state matches (or is explicitly UNKNOWN)

## What Coherence is in Phase 1

**Evidence pillar before merge.**  
Coherence records `Fact(claim, evidence, next)` and fails CI when claims stay open, empty, or **tampered** (hash-chain, exit 3). The check must run as a step the **agent does not control**.

Use it so **money-path PRs** (billing / Stripe / payouts / payments) cannot merge on chat green.

```bash
python -m coherence prove-cmd "pytest -q" --claim "unit tests"
python -m coherence check
python -m coherence report --out coherence-report.md
python -m coherence aio          # Phase-1 money-path evidence checklist
```

Copy-paste workflow with path filters: [`.github/workflows/coherence-money-path.yml.example`](../.github/workflows/coherence-money-path.yml.example)

## What Phase 1 is NOT

| Not this | Why |
|---|---|
| Runtime exactly-once / double-charge fence | Different product lane (admission at the money tool) |
| Google AP2 / network intent tokens | Network protocols; we don’t claim to be AP2 |
| “Banks require Coherence” | False — **your** branch protection requires the check |
| Full AIO truth plane | Later phases; don’t market Phase 1 as complete |

## Phase map (honest)

| Phase | Question | Coherence today |
|---|---|---|
| **1 — Evidence** | Did we prove claims before money-path code merged? | **Yes** — prove-cmd / check / Action / `aio` |
| 2 — Admission | Was the live money tool call admitted once under scoped intent? | Out of scope here |
| 3 — Settlement bind | Does Stripe/ledger state match the agent claim (or UNKNOWN)? | Not built as a product yet |

## Next

See [CI.md](CI.md) for the PR gate. See [ARCHITECTURE.md](ARCHITECTURE.md) for the Fact model.
