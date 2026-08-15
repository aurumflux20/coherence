# Coherence

### One reality for agent work — that gets smarter every time you solve a problem.

Agents claim. Skills install. Specs live in Slack. PRs flood.  
**Coherence** is five rungs + **dominos** + **evolution memory** so engineers see **one reality** that **compounds with use**.

```text
7  evolution  → lessons from solved problems (memory grows)
6  dominos    → cascade order + Gilbert NEXT on every stone
5  review     → what needs human eyes
4  replay     → can we re-check what was proven?
3  decisions  → locked project truths
2  skills     → what did we install (MCP/skills risk)?
1  claimproof → CLAIMED vs PROVEN (base language)
```

### Revolutionary loop

```text
use → prove → knock domino → must leave a lesson + NEXT
    → memory saves it → next session starts more coherent
```

**Gilbert’s Law (product form):** you cannot “solve” without naming what to do next  
(or explicit `chain complete`). Silent success is illegal.

**Domino problem:** one lie (“tests passed”) knocks merge → prod → blame → freeze agents.  
Coherence makes that cascade **visible and ordered**.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m coherence demo
python -m coherence evolve
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

c = Coherence(title="my-pr", memory_path=".coherence/memory.json", seed_cascade=True)
c.skills.audit("shell-runner", ["shell"])
c.decisions.lock("api", "MUST NOT break v1 clients")
proof = c.claimproof.cmd("tests", "pytest -q", exit_code=0)
c.replay.check()
c.review.triage()

# Knock the active domino — MUST teach the system
head = c.dominos.head()
c.solve_domino(
    head.id,
    proof=proof.proven,
    lesson="Chat green is not CI green",
    proof_record_id=proof.id,
)
print(c.plain_english())
```

---

## Coherence rules

1. Higher rungs **cannot invent** PROVEN if rung 1 only has CLAIMED.  
2. Every record has **NEXT** (what to do).  
3. Every **solved domino** needs **proof + lesson + next** (Gilbert).  
4. Evolution memory **loads next session** — the product evolves with use.  
5. Deepen rungs **1 → 5** in public; dominos/memory are the flywheel.

Full map: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/EVOLUTION-AND-DOMINOS.md](docs/EVOLUTION-AND-DOMINOS.md)

---

## License

MIT
