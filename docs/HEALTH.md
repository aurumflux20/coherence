# Health checks — timely, honest

## Question

How do we know Coherence is still healthy tomorrow, not only on the day we shipped?

## What we automate

| Check | When | Command |
|-------|------|---------|
| Law smoke | every PR + daily | `python -m coherence law` |
| Unit tests | every PR + daily | `unittest discover` |
| Storm proof | every PR + daily | `python storm.py` |
| Full health | daily schedule + manual | `python -m coherence health` |
| Evolution chain | if memory file given | `--memory path` |

**Scheduled:** `.github/workflows/health-scheduled.yml` — cron `0 14 * * *` UTC + **Run workflow** button.

## Commands

```bash
# Local / CI one-shot
python -m coherence health
python -m coherence health --out health-report.json
python -m coherence health --memory .coherence/memory.json
```

Exit **0** = GREEN · Exit **1** = RED (with Gilbert-style NEXT printed).

## Can it keep resolving its own bugs?

### Yes (automated)

| Capability | Reality |
|------------|---------|
| **Detect** regressions | Storm + tests + scheduled health |
| **Block** bad merges | CI red on main/PR |
| **Report** what failed + NEXT | health JSON / logs |
| **Remember** proven fixes | evolution memory (only with evidence) |

### No (not without a human / agent session you control)

| Fantasy | Truth |
|---------|--------|
| Unsupervised “fix all bugs forever” | Dangerous and false |
| Silent auto-push to main | Against AurumFlux deploy discipline |
| AI invents patches with no proof | Breaks Coherence’s own law |

### Practical “self-healing” loop (honest)

```
scheduled health RED
  → GitHub notifies (failed workflow)
  → human or coding agent opens issue / local fix
  → prove with storm + tests (evidence)
  → PR → CI green → merge
  → optional: solve_domino + lesson into evolution memory
```

That is **detect → prove fix → merge → learn** — not a black-box self-rewriting binary.

## Metrics that mean healthy

| Green | Red |
|-------|-----|
| `coherence health` exit 0 | any check FAIL |
| Storm 7/7 | storm exit 1 |
| Scheduled workflow success | cron failure email/notification |

## Ship rule

**No depth feature merges while health/storm is red.**
