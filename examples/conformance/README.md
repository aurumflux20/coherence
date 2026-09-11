# A conformance run you can check without trusting us

These files are one real run of the retry-safety battery against a client that
double-pays, recorded, signed and timestamped. Nothing here is a claim you have
to take our word for.

**This is the artefact a paid verification produces.** Same battery, same
format, same signature and same public timestamp — the only difference is that
the subject is your client instead of the deliberately broken one below.

| file | what it is |
|---|---|
| `naive_pay.py` | the subject: a deliberately broken client, so the run is reproducible |
| `result.json` | the run as data — all **10 modes**, and how many **distinct settlements** landed for one purchase |
| `session.json` | the same run as a hash-chained record; the failing modes are recorded **open**, not proven |
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

This example **fails**. The client under test paid again in **seven of ten**
modes, and the record says so — `open: 7`, with the failing modes named. A run
that double-pays cannot be recorded as an all-green session, because a mode that
failed is written with no evidence, and `coherence check` refuses it.

The seven include the four `reconcile_*` modes, where the client does the right
thing — it asks whether the payment landed before retrying — and then mis-reads
the answer. Three of those four answer with HTTP 200 and something that is not
an answer: prose saying "not available", a body too large for a buffered read, a
response truncated mid-record. A client that treats any of those as "it never
happened" pays twice.

Try to launder it: edit `session.json` so a failing mode reads as a pass, then
re-run the command above against your edited file. It answers
`subject_mismatch` and exits non-zero.

## Producing one of these

```bash
# reproduce this exact example
hostile-facilitator test --json result.json -- python3 naive_pay.py

# or point it at your own client
hostile-facilitator test --json result.json -- <the command that makes ONE purchase>
coherence conformance result.json --out session.json
coherence attest --session session.json --key <your key> --anchor rekor
```
