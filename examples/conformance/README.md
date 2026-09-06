# A conformance run you can check without trusting us

These four files are one real run of the retry-safety battery against a client
that double-pays, recorded, signed and timestamped. Nothing here is a claim you
have to take our word for.

| file | what it is |
|---|---|
| `result.json` | the run as data — every mode, and how many **distinct settlements** landed for one purchase |
| `session.json` | the same run as a hash-chained record; the two failing modes are recorded **open**, not proven |
| `attestation.json` | that record's chain head, signed (DSSE + in-toto v1) |
| `attestation.rekor.json` | where the signature sits in Sigstore's public transparency log |

## Check it

```bash
pip install "coherence-check[attest]"
coherence verify \
  https://raw.githubusercontent.com/aurumflux20/coherence/main/examples/conformance/attestation.json \
  --pub https://raw.githubusercontent.com/aurumflux20/coherence/main/KEYS/aurumflux-attest.pub \
  --session https://raw.githubusercontent.com/aurumflux20/coherence/main/examples/conformance/session.json \
  --rekor https://raw.githubusercontent.com/aurumflux20/coherence/main/examples/conformance/attestation.rekor.json
```

`verified` means: this signature is ours, this session is the exact file it was
signed over, its chain recomputes, and the timestamp is in a public log neither
we nor you control.

## The part that makes it evidence rather than marketing

This example **fails**. The client under test settled twice in two of seven
modes, and the record says so — `open: 2`, with the failing modes named. A run
that double-pays cannot be recorded as an all-green session, because a mode
that failed is written with no evidence, and `coherence check` refuses it.

Try to launder it: edit `session.json` so a failing mode reads as a pass, then
re-run the command above against your edited file. It answers
`subject_mismatch` and exits non-zero.

## Producing one of these

```bash
hostile-facilitator test --json result.json -- <the command that makes ONE purchase>
coherence conformance result.json --out session.json
coherence attest --session session.json --key <your key> --anchor rekor
```
