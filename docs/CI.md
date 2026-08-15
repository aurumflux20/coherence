# CI / PR check (ship feature)

## Goal

Agents and humans stop merging on **chat green**.  
CI records **evidence** and fails if Facts stay **open**.

## Commands

```bash
# Run a real command; record DONE if exit 0
python -m coherence prove-cmd "pytest -q" --claim "unit tests"

# Optional: record a claim that still needs proof
python -m coherence said "refactored utils" --next "add tests"

# Exit 1 if open/blocked; exit 2 if zero proven (strict)
python -m coherence check

# Markdown for PR comment / artifact
python -m coherence report --out coherence-report.md
python -m coherence report --json
```

Session file (gitignored): `.coherence/session.json`

## Copy-paste GitHub Action (any repo)

```yaml
name: Coherence
on: [pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install "git+https://github.com/aurumflux20/coherence.git"
      - run: |
          python -m coherence prove-cmd "pytest -q" --claim "unit tests" --next "chain complete"
          python -m coherence check
          python -m coherence report --out coherence-report.md
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coherence-report
          path: coherence-report.md
```

This repo dogfoods the same pattern in `.github/workflows/coherence-pr.yml`.

## Badge

After `check` / `report`, JSON includes `shields_url`, e.g.

```text
https://img.shields.io/badge/coherence-1_proven-0_open-brightgreen
```

Paste into your README once you generate a report locally or from CI.
