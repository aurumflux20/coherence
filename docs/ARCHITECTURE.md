# Coherence — one stack, five rungs

**Name:** Coherence  
**Job:** Make agent work *coherent* for engineers — same reality for claims, installs, decisions, runs, and review.  
**Not:** payment rails, Stripe, or AurumFlux product glue.

---

## The single problem

Agents act faster than humans can trust.  
Tools already exist (Git, CI, MCP, issue trackers). They are **incomplete** as a chain.

**Coherence** is the missing chain: five rungs, one vocabulary.

---

## Shared vocabulary (spine)

Everything in Coherence speaks:

| Word | Meaning |
|------|---------|
| **CLAIM** | Agent or human *said* something happened |
| **PROOF** | Machine-checkable evidence it happened |
| **ARTIFACT** | Hashable output (log, test report, file, command result) |
| **NEXT** | What a human or agent must do now (never silent) |
| **STATUS** | Closed set: claimed · proven · blocked · open · illusion |

**Rung 1 defines the alphabet. Rungs 2–5 only add nouns that still use CLAIM/PROOF/NEXT.**

---

## Rung map

```
[5] review     Review radar     — what deserves human eyes
      ↑ consumes risk signals from 1–4
[4] replay     Agent replay     — same run twice?
      ↑ replays proven traces from 1
[3] decisions  Decision capsule — locked project truths
      ↑ constraints before/while agents act
[2] skills     Skill/MCP audit  — what may be installed
      ↑ bill of materials before tools run
[1] claimproof Claim ≠ Proven   — base language of every step
      ↑
 Existing: GitHub · CI · agents · MCP · issues
```

| Rung | Package module | Input | Output |
|-----:|----------------|-------|--------|
| 1 | `coherence.claimproof` | step name + claim + optional proof | `StepRecord` |
| 2 | `coherence.skills` | skill manifest / path | `SkillBill` + risk |
| 3 | `coherence.decisions` | decision text + id | append-only `DecisionLog` |
| 4 | `coherence.replay` | list of proven steps | `ReplayReport` |
| 5 | `coherence.review` | PR-like bundle of 1–4 signals | `ReviewTriage` |

---

## Coherence rule (non-negotiable)

1. **No PROOF without ARTIFACT** (or explicit fail).  
2. **No silent OK** — every record has `next_action`.  
3. **Higher rungs may only strengthen lower ones** — review cannot invent “proven” if claimproof said claimed.  
4. **Ship order = rung order** — product may *name* all five; code lands 1 → 2 → 3 → 4 → 5.  
5. **One brand, one install, one mental model.**

---

## Data flow (one session)

```
skills.audit(install)     → SkillBill          (rung 2)
decisions.load(repo)      → DecisionLog        (rung 3)
agent runs tools…
claimproof.record(step)   → StepRecord[]       (rung 1)
replay.check(steps)       → ReplayReport       (rung 4)
review.triage(bundle)     → ReviewTriage       (rung 5)
```

Human opens **one** summary: what was claimed, proven, installed, constrained, replayable, and worth review.

---

## What we do not do here

- Payment / Stripe / mission pricing  
- Hosted secret custody  
- “Replace GitHub”  

We **complete** the agent toolchain they already have.
