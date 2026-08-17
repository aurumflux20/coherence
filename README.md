# Coherence

[![CI](https://github.com/aurumflux20/coherence/actions/workflows/ci.yml/badge.svg)](https://github.com/aurumflux20/coherence/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

### Your agent says the work is done. This makes it prove it.

An AI agent writes code and reports back: *"Tests passed. Done."* But "done" was
a sentence in a chat window, not an exit code. Nobody re-ran it. The spec from
three messages ago got quietly dropped. The PR is a wall of changes with no
signal about what actually needs a human's eyes.

Coherence is a small Python library and command-line tool that records the
difference between **what an agent said** and **what it actually proved** — and
always keeps a **next step**. It has one rule:

```text
Nothing is done unless there is evidence.
Nothing is finished unless there is a next step.
Nothing is remembered unless it was actually done.
```

No dependencies. Pure standard library. It runs where your code runs.

---

## The problem it fixes

Agents write code fast, so the slow part is now a human checking it. And the
usual signals lie:

- **"Tests passed"** in a chat message is not the same as a green exit code.
- A spec agreed at the start of a task gets forgotten halfway through.
- The agent installed some skill or MCP tool and you have no record of what.
- A big agent-written PR gives you no idea which line actually matters.

Coherence turns each of those into a **Fact** — a claim, the evidence for it
(if any), and the next step. A claim with no evidence is simply **not done**,
and the code enforces that; you can't mark something proven without attaching
the proof.

**Who it's for:** engineers and tech leads who ship code with AI agents every
day and are tired of trusting "done" on faith.

---

## Install

```bash
pip install "git+https://github.com/aurumflux20/coherence.git"
```

Or for local development:

```bash
git clone https://github.com/aurumflux20/coherence.git
cd coherence
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

**Requires:** Python 3.10 or newer. **No dependencies** — standard library only.

---

## 60-second look

```bash
python3 -m coherence law     # the whole idea in three sentences
python3 storm.py             # the hostile proof — must exit 0
python3 -m coherence demo    # a worked example
```

In code:

```python
from coherence import Coherence

c = Coherence()

# the agent claims something in chat — recorded, but NOT counted as done
c.said("tests passed", next="actually run pytest and attach the exit code")

# now prove it — evidence attached, so it counts
c.prove("pytest -q", evidence="exit_code=0", next="chain complete")

print(c.plain_english())
```

`said()` records a claim with no proof. `prove()` refuses to exist without
evidence — it will raise rather than let you record a lie.

---

## Stop agents faking a green check in CI

Drop this into a pull-request workflow and an agent can no longer say "all
green" without the evidence to back it:

```bash
python3 -m coherence prove-cmd "pytest -q" --claim "unit tests"
python3 -m coherence check     # exits 1 if any claim is still unproven
python3 -m coherence report --out coherence-report.md
```

Copy-paste GitHub Action: [docs/CI.md](docs/CI.md). This repo runs it on its own
PRs — see `.github/workflows/coherence-pr.yml`.

---

## Proof, not promises

Everything above is tested the hostile way. `storm.py` throws hundreds of
racing, lying, half-finished claims at the rule and checks it never bends:

```
[PASS] 500 chat claims → 0 counted as done
[PASS] a claim with no next step is rejected, 100/100 under a race
[PASS] memory refuses to store anything that was never proven
[PASS] CI gate: unproven work fails, proven-only work passes
RESULT: 7/7 checks PASS
```

Run it yourself — it must exit 0. Full write-up: [STORM-PROOF.md](STORM-PROOF.md).

---

## GitHub Action — the gate in one block

```yaml
permissions:
  pull-requests: write   # for the sticky report comment

steps:
  - uses: actions/checkout@v4
  - uses: aurumflux20/coherence@v1
    with:
      prove: |
        pytest -q
        npm test
```

Each command becomes evidence. The PR fails on claims without proof, on an
empty session, or — loudest of all — on a session that was edited after the
facts were recorded (exit 3). A sticky comment on the PR shows what was proven
and what is still open, so reviewers see it without installing anything.

---

## Trust boundary — who runs the check

This matters most, so it goes first.

The session file records what was proven. **The protection only holds when
something the agent does not control runs the check** — normally your CI, not
the agent under review. If the agent that writes the session can also edit the
file and then declare itself green, the guarantee is gone.

Coherence closes the tampering half of that: every session entry is
hash-chained, so editing, deleting, or reordering a recorded fact breaks the
chain, and `coherence check` fails with exit code 3 at the exact entry that was
changed — a forged "green" is caught, not trusted.

```bash
# In CI (not the agent): the check re-verifies the chain before trusting a
# single fact. A tampered session fails here even if every fact reads "proven".
coherence check          # exit 0 pass · 1 open facts · 2 empty · 3 tampered
```

What it still does **not** do: stop an agent that never records a fact at all,
or one running as the same identity as your CI with write access to the run
itself. Chaining makes after-the-fact edits detectable; it does not make the
writer honest. Run the check as a step your agent cannot rewrite.

---

## Honest limits

Printed here so you find them now, not later:

| What it does | What it does not do |
|---|---|
| Record claim vs. evidence, always with a next step | Stop a rogue tool that has your keys and ignores it |
| Run locally, standard library only | Replace GitHub, your CI, or your test runner |
| Keep an optional lesson memory on disk | Ship as a hosted multi-tenant service |

Coherence records what was proven. It does not *do* the proving for you — you
still write the test; it just refuses to let "done" mean anything less.

---

## Documentation

| Doc | What's in it |
|-----|--------------|
| [docs/INDEX.md](docs/INDEX.md) | Full map |
| [docs/CI.md](docs/CI.md) | The PR check and badge |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How it's built |
| [CHANGELOG.md](CHANGELOG.md) | Versions |
| [SUPPORT.md](SUPPORT.md) | Help + related projects |

Security issues: please report privately per [SECURITY.md](SECURITY.md), not as
a public issue.

---

## Related projects (separate repos)

| Repo | Role |
|------|------|
| [seal](https://github.com/aurumflux20/seal) | Exactly-once admission for agent money actions |
| [effectfence](https://github.com/aurumflux20/effectfence) | In-process fence against double-firing effects |
| [fencescan](https://github.com/aurumflux20/fencescan) | Static scan for double-effect risks |

---

## License

**Apache License 2.0** — see [LICENSE](LICENSE).

In plain words: use it, change it, ship it inside your own product, even sell
something built on top of it — no restrictions, no fees, no asking. This is
built to help developers; the only ask back is a ⭐ if it did.

© 2026 AurumFlux (A. Kaur)
