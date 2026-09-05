# Evidence checklist — which claims must carry proof before a merge

Most of what an agent claims can wait for a human to read it. Some claims cannot:

- **money** — a charge, refund, payout, invoice, subscription change
- **deploy** — a release, rollout, hotfix, cut-over to production
- **data** — a migration, backfill, delete, truncate, schema change
- **security** — a credential, token, permission, role, key rotation

Those are *consequential* claims. `coherence checklist` reads the session and refuses to call the run clean while any consequential claim is still a sentence with no evidence beside it.

```bash
python -m coherence prove-cmd "pytest -q tests/billing" --claim "billing tests"
python -m coherence checklist                    # all profiles
python -m coherence checklist --profile money    # one profile
python -m coherence checklist --json
```

Exit `0` when every matched claim is proven (or nothing matched); `1` when a gap is open. The gap names the claim and the recorded next step.

## Profiles are words, not policy

A profile is a set of words that marks a class of claim. Add your own in `coherence.checklist.PROFILES` — the module is deliberately small so that the list is the whole mechanism and there is nothing hidden behind it.

## What this is not

This reads the record *afterwards*. It does not stop a double charge while it happens, it does not admit or block payments, and it does not talk to any payment rail. Runtime prevention of a duplicate effect is what [Seal](https://github.com/aurumflux20/seal) and [EffectFence](https://github.com/aurumflux20/effectfence) do. Coherence proves; Seal prevents. Use either, or both.

## In CI

Copy `.github/workflows/coherence-checklist.yml.example`, set the `prove:` lines, and the gate fails a PR whose consequential claims have no evidence — the same way the plain gate fails a PR with any open fact, just scoped to the claims that cost the most when they are false.
