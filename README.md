# Coherence

### One stack so AI agent work stops falling apart in your head.

Agents claim. Skills install. Specs live in Slack. PRs flood.  
**Coherence** is five rungs that share **one language** so engineers see **one reality**.

```text
5  review     → what needs human eyes
4  replay     → can we re-check what was proven?
3  decisions  → locked project truths
2  skills     → what did we install (MCP/skills risk)?
1  claimproof → CLAIMED vs PROVEN (base language)
```

Not a payment product. Not a rewrite of GitHub.  
It **sits on top** of agents + CI + MCP and makes them **complete together**.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m coherence demo
```

---

## 5th-grade picture

| Rung | Kid words |
|------|-----------|
| 1 | “Said it” is not “showed it” |
| 2 | Don’t plug in mystery toys |
| 3 | We already decided the rules |
| 4 | Can we do the same check again? |
| 5 | What should a human look at first? |

**Coherence** = all five talk to each other so the story doesn’t break.

---

## Ideal user

- Engineers using **coding agents** daily  
- Staff/seniors drowning in **AI PRs**  
- Teams installing **skills/MCP** without a bill of materials  
- Big-tech and startups who need **shared reality**, not more chat  

---

## Code shape

```
coherence/
  claimproof/   # rung 1
  skills/       # rung 2
  decisions/    # rung 3
  replay/       # rung 4
  review/       # rung 5
  core/         # shared CLAIM/PROOF/NEXT + Bundle + spine
```

One object:

```python
from coherence import Coherence

c = Coherence(title="my-pr")
c.skills.audit("shell-runner", ["shell"])
c.decisions.lock("api", "MUST NOT break v1 clients")
c.claimproof.cmd("tests", "pytest -q", exit_code=0)
c.replay.check()
c.review.triage()
print(c.plain_english())
```

---

## Coherence rules

1. Higher rungs **cannot invent** PROVEN if rung 1 only has CLAIMED.  
2. Every record has **NEXT** (what to do).  
3. Ship order is **1 → 2 → 3 → 4 → 5** (all named now; deepen in order).  

Full map: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## License

MIT
