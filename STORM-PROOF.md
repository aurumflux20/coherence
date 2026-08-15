# COHERENCE — STORM PROOF

**Style:** same honesty bar as EffectFence / Seal storm proofs.  
**Not:** marketing. **Is:** measured attacks on our own law.

---

## Claim under test

| # | Claim |
|---|--------|
| 1 | **Chat is never DONE** — `said` / illusion cannot become evidence |
| 2 | **Only evidence is DONE** — mixed said/prove storms keep counts exact |
| 3 | **Empty next is illegal** — Gilbert holds under concurrent construction |
| 4 | **Memory refuses undoned** — no proof ⇒ no lesson, under races |
| 5 | **Domino order** — non-head cannot solve while head is open (barrier race) |
| 6 | **Evolution compounds** — proven lessons load in session 2 with NEXT |
| 7 | **CI gate** — open facts fail `check`; proven-only session passes |

**Law:**

```text
Nothing is done unless there is evidence.
Nothing is finished unless there is a next.
Nothing is remembered unless it was done.
```

---

## How to run

```bash
# from clone
python3 storm.py

# or after pip install -e .
python3 storm.py
```

**Exit 0** = all checks PASS.  
**Exit 1** = at least one FAIL (do not claim storm-proof).

Also in CI: `.github/workflows/ci.yml` runs `python storm.py`.

---

## Representative result

Run on developer machine / CI (fill after green runs):

| Check | N / shape | Verdict |
|-------|-----------|---------|
| Chat never done | 500 threads `said` | PASS if done=0 |
| Evidence only | 200 mixed | PASS if counts match |
| Empty next | 100 races | PASS if all rejected |
| Memory undoned | 100 races | PASS if lessons=0 |
| Domino order | 40 barrier | PASS if non-head 0 wins |
| Evolution compounds | 2 sessions | PASS if hint+NEXT |
| CI gate | session files | PASS if exits 1 then 0 |

Re-run and paste a real table into a PR when numbers change.

---

## What this does **not** prove

| Not proven | Why |
|------------|-----|
| Multi-process Postgres exactly-once | That is Seal’s storm |
| MCP tool concurrency fence | That is EffectFence |
| Skill malware detection quality | v0 capability tags only |
| Production review-radar accuracy | Heuristic triage v0 |

We only prove **Coherence’s law** under hostile in-process races + session gate.

---

## Evolution is the key (after proof)

Storm proves the law is real.  
**Depth** means:

1. Every **PROVEN** solve can teach memory  
2. Memory only accepts **done** facts  
3. Next session **applies** lessons with Gilbert **NEXT**  
4. Dominos force cascade order so evolution isn’t random notes  

Without storm: “evolving” is a story.  
With storm: “evolving” is constrained by the same law.

---

## Bugs we will treat as ship-blockers

- Any `said` counted as done  
- Any `learn` without proof that persists  
- Any empty `next` accepted  
- Domino solve skipping the open head  
- Session `check` green with open facts  

Found by storm or users → fix → re-run storm → update this file.
