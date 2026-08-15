# Coherence

### One law. Two fields. Everything else is costume.

```text
Nothing is done unless there is evidence.
Nothing is finished unless there is a next.
Nothing is remembered unless it was done.
```

That is **320 IQ** building: not more features — **one rule so hard it stays true**.

| Field | Rule |
|-------|------|
| **evidence** | empty ⇒ **not done** (chat doesn’t count) |
| **next** | empty ⇒ **illegal** (Gilbert — always tell what to do) |

The atom is a **Fact**. Rungs, dominos, memory = costumes for Fact.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m coherence law
python -m coherence demo
python -m coherence evolve
```

```python
from coherence import Coherence

c = Coherence()
c.said("tests passed in chat", next="run pytest and attach exit code")
c.prove("pytest", "exit 0", next="chain complete")
# only the second is done → only done things may be remembered
```

### Costumes (same law)

```text
7  evolution  → remember only DONE facts
6  dominos    → ordered Facts; next points at next stone
5  review     → Fact: what needs eyes
4  replay     → Fact: re-check evidence
3  decisions  → Fact: locked rule
2  skills     → Fact: install bill
1  claimproof → Fact: said vs evidence
```

180 IQ adds modules. **320 IQ deletes until the law is obvious.**  
See [docs/320IQ.md](docs/320IQ.md).

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
