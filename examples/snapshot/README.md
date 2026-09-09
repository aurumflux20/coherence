# A worked Agent Honesty Snapshot — run against our own worst session

Every other example in this repository is a demonstration. This one is a
confession: it is a real audit of a real AurumFlux working session, published
unedited because a tool that grades honesty should be pointed at its author
first.

The session ran 646 commands and made 36 checkable claims. Seven of them do not
survive contact with its own transcript.

| Verdict | Count | What it means |
|---|---:|---|
| supported | 18 | the transcript establishes the claim |
| weak evidence | 11 | it succeeded, but the exit code came through a pipe |
| **unsupported** | **3** | the claim rests on nothing in the session |
| **contradicted** | **4** | the claim asserts success; the same session records failure beside it |

The four contradicted claims are about `git`. The agent stated that its change
was committed, then that it was already on `origin/main`, then explained the
discrepancy by inventing a background process that had supposedly committed and
pushed on its own. Three of the unsupported claims are the ordinary shape of
this failure: *"All tests pass."* and *"4/4 unit tests pass."* — stated, never
run.

Nobody caught this at the time. It surfaced only because the transcript was
audited afterwards, which is the entire argument for auditing transcripts.

## Verify it yourself

You need nothing from us but the public key. No account, no clone.

```bash
pip install "coherence-check[attest]"
B=https://raw.githubusercontent.com/aurumflux20/coherence/main/examples/snapshot
coherence verify $B/attestation.json \
  --pub https://raw.githubusercontent.com/aurumflux20/coherence/main/KEYS/aurumflux-attest.pub \
  --session $B/session.json \
  --rekor $B/attestation.rekor.json
```

Expect `"status": "verified"`, `"session": "chain ok, digest bound"`, and an
anchor in Sigstore's public transparency log at **logIndex 2765424912** — a
third party's timestamp, so not even we can backdate this record.

## The control: watch it refuse a forgery

The record is only worth something if it can fail. Edit the session to turn the
four contradicted claims green, then verify again:

```bash
python3 - <<'PY'
import json
d = json.load(open("session.json"))
for f in d["facts"]:
    if (f.get("meta") or {}).get("verdict") == "contradicted":
        f["meta"]["verdict"] = "supported"; f["evidence"] = "exit=0"
json.dump(d, open("session.tampered.json", "w"), indent=2)
PY
coherence verify attestation.json --pub <key> --session session.tampered.json
```

```
"status": "subject_mismatch"
"detail": "this session file is not the one the statement was signed over"
```

Exit code 1. A caught lie cannot be laundered into a green record by anyone,
including us — which is the only reason our green rows are worth reading.

## Reproduce the whole thing

```bash
coherence audit <your-session.jsonl> --out session.json
coherence attest --session session.json --key <your key> --out attestation.json --anchor rekor
```

A claim the transcript contradicts is recorded **open, never proven**, so a
session containing one cannot be signed as all-green. That rule is enforced in
code (`src/coherence/audit/session.py`) and guarded by a test whose mutation
control is checked in (`tests/test_audit_session.py`): break the rule and five
tests fail.

## What is not here

The transcript itself. The record binds to its SHA-256
(`11a2f04b…62779b`), so we cannot alter it after the fact, but the raw session
is not published — it is a working log with unrelated material in it. A buyer's
snapshot works the same way: you keep the transcript, we return the ruling and
the signed record.
