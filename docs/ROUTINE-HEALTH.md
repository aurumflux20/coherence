# How Nova knows — routine health check

## Problem

A GitHub Action can go red at 14:00 UTC and **nobody tells the agent** until a human opens chat.

## Three layers (use all)

| Layer | What | How Nova learns |
|-------|------|-----------------|
| **1. GitHub daily cron** | `health-scheduled.yml` @ 14:00 UTC | Failed run + `health-red` issue on GitHub |
| **2. Local script** | `scripts/routine-health.sh` | Exit 1 + `.coherence/health-latest.json` |
| **3. Agent scheduler** | Grok/Nova scheduled task | **Wakes Nova** with a fix prompt when due |

Layer 3 is how **I** know without you remembering to ask.

---

## Layer 1 — already live

- Workflow: **Health (scheduled)**  
- Cron: `0 14 * * *`  
- On RED: issue `health-red` + `nova-fix`  
- Manual: Actions → Health (scheduled) → Run workflow  

---

## Layer 2 — local one-liner

```bash
cd ~/packages/coherence
./scripts/routine-health.sh
# GREEN exit 0 · RED exit 1 · report in .coherence/health-latest.json
```

Optional macOS launchd (daily 9:00 local) — install when you want disk-side cron:

```bash
# See scripts/com.aurumflux.coherence.health.plist
```

---

## Layer 3 — agent routine (this seat)

A **scheduled task** in the agent environment runs on an interval, e.g.:

1. Run `routine-health.sh` / `python -m coherence health`  
2. If GREEN → short note, done  
3. If RED → **Nova executes fix loop** (reproduce → fix → storm → push)

That is the answer to “how will you know?”: **the schedule pings the agent**, not only GitHub.

---

## Status file Nova should read first

| Path | Meaning |
|------|---------|
| `~/packages/coherence/.coherence/health-latest.json` | Last local health |
| GitHub issues label `health-red` | Open fix jobs |
| Actions → Health (scheduled) | Last cron result |

---

## Zah checklist (once)

1. Leave GitHub Actions enabled on `aurumflux20/coherence`  
2. Keep agent scheduler task enabled (created with this setup)  
3. When you open a session and say “health” / “resume coherence”, Nova checks labels + latest JSON  

---

## Honest limit

If **no** agent runtime is up and **no** one looks at GitHub, a red check only sits as a failed Action/issue until something wakes.  
Layer 3 + your “resume” habit close that gap.
