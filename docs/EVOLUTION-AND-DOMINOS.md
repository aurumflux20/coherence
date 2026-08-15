# Coherence that evolves · Dominos · Gilbert

## Revolutionary claim (honest)

Most tools are static: you use them the same way on day 1 and day 100.  
**Coherence is meant to get smarter as you solve problems with it.**

Every **PROVEN** fix can:

1. Knock the current **domino** (this problem is settled).  
2. **Name the next domino** (Gilbert — never leave “what now?” empty).  
3. Write a **lesson** into evolution memory so the *next* session starts more coherent.

That is the flywheel:

```
use → solve → prove → learn → next domino → use again
```

We do **not** claim magic AGI self-rewriting.  
We claim: **append-only memory + forced next actions + cascade checks** — so the product compounds with use.

---

## Gilbert’s Law (product form)

> Nobody is told what to do.  
> Chat creates the illusion that the next step is obvious.

**Domino rule:** you may not mark a problem solved without a **non-empty `next_action`** for what the cascade requires next.  
If there is no next problem, next_action must explicitly say **`chain complete`**.

Silent success is illegal.

---

## Domino problem (why cascades kill teams)

One silent failure becomes five:

```
illusion "tests passed"
  → merge
    → prod break
      → blame agent
        → disable agents
          → velocity dies
```

**Coherence dominos** make the cascade **visible and ordered**:

- You must face domino N before pretending N+3 is fine.  
- Solving N surfaces N+1 with a clear NEXT.  
- Evolution memory records “when X was proven, Y was the next risk.”

---

## Evolution memory

Stored as JSON (local file or in-process):

| Field | Meaning |
|-------|---------|
| `lesson` | What we learned |
| `problem` | What was wrong |
| `proof` | What made it PROVEN |
| `next_domino` | What Gilbert forced next |
| `uses` | How often this lesson was applied |

On `Coherence(title=..., memory_path=...)`, prior lessons **load** and can seed dominos so the tool doesn’t start from zero every time.

---

## What “keeps evolving” means in code

| Mechanism | File |
|-----------|------|
| Domino chain | `coherence/evolve/dominos.py` |
| Learn on solve | `coherence/evolve/memory.py` |
| Spine wiring | `coherence/core/spine.py` → `c.dominos` · `c.evolve` |
| Demo flywheel | `python -m coherence evolve` |

Future (not yet): community lesson packs, CI that fails if open dominos remain, shared org memory.

---

## One line

> **Every solved problem must teach the system and name the next problem — or Gilbert says communication did not happen.**
