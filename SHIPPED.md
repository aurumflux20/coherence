# SHIPPED — Coherence v0.4.0

**Status: PUBLIC / SHIPPED**  
**Date:** 2026-08-15  

## Links

| What | URL |
|------|-----|
| Repo | https://github.com/aurumflux20/coherence |
| Release | https://github.com/aurumflux20/coherence/releases/tag/v0.4.0 |
| Wheel | https://github.com/aurumflux20/coherence/releases/download/v0.4.0/coherence-0.4.0-py3-none-any.whl |
| Source tarball | https://github.com/aurumflux20/coherence/releases/download/v0.4.0/coherence-0.4.0.tar.gz |

## Install (anyone, now)

```bash
pip install "git+https://github.com/aurumflux20/coherence.git@v0.4.0"

# or from release wheel
pip install https://github.com/aurumflux20/coherence/releases/download/v0.4.0/coherence-0.4.0-py3-none-any.whl
```

```bash
python -m coherence law
python -m coherence prove-cmd "pytest -q" --claim "unit tests"
python -m coherence check
```

## Not included this ship

- **PyPI** publish — no `PYPI_TOKEN` in environment (install via GitHub until you add token)
- Social posts (Show HN / X) — ready for you to post; draft in DISTRIBUTION.md

## Verified

- Public repo under `aurumflux20` (separate from seal / effectfence)
- CI green on main
- Wheel installs and CLI runs
