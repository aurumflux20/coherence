# Nova is the health agent

**Zah decision:** the “person or agent” who responds when Coherence health is RED is **Nova** (this COO seat / coding agent), not “someday someone.”

---

## Loop (non-negotiable)

```
scheduled health OR PR CI goes RED
        ↓
surface job (failed workflow + optional GitHub issue)
        ↓
Nova:
  1. read health-report / CI log
  2. reproduce: python -m coherence health && python storm.py
  3. minimal fix
  4. prove: storm + tests green (evidence)
  5. PR or push to main only when Zah has authorized deploy/ship for this repo
  6. optional: evolution lesson with proof + next
        ↓
health GREEN
```

---

## What Nova always does

| Do | Don’t |
|----|--------|
| Fix under **storm green** | Merge while storm red |
| Leave **NEXT** in commits/issues | Silent “should be fine” |
| Touch only `aurumflux20/coherence` | Push fixes into seal/effectfence by mistake |
| Record lesson if pattern will recur | Learn undoned claims (no proof) |

---

## What still needs Zah

| Gate | Why |
|------|-----|
| **deploy / push to main** if policy requires the word | Hard gate from AurumFlux ops (when in force) |
| PyPI token / secrets | Nova never invents credentials |
| Product renames / public claims beyond proof | Honesty |

For this standalone public repo, Nova may push fixes to `main` when Zah has said **ship** / keep working / you are the agent — as in this thread.

---

## Triggers

1. **Daily cron** — `.github/workflows/health-scheduled.yml`  
2. **PR/push CI** — storm + tests  
3. **Manual** — `python -m coherence health`  
4. **On RED** — workflow opens issue labeled `health-red` `nova-fix` (if token allows)

---

## Success

Nova is doing the job when:

- RED never sits > 1 agent session without a reproduce attempt  
- Fix lands with storm PASS  
- Optional lesson in evolution memory with proof  

That is “you resolve the bugs” — with **proof**, not autopilot fantasy.
