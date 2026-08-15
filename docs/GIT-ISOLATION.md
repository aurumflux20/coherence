# Git isolation — Coherence is a standalone project

## Guarantees

| Rule | Status |
|------|--------|
| Own git root at `packages/coherence` | Yes — separate `.git` |
| **Live origin (only)** | `https://github.com/aurumflux20/coherence` |
| **Not** seal / effectfence / aurumflux-api | Yes — different repo, different history |
| **Not** a submodule of other products | Yes |
| Home monorepo must **not** track this tree | `packages/coherence/` in `~/`.gitignore |

## What this means

- `git push` from **seal**, **aurumflux-api**, or **~** cannot publish Coherence unless someone deliberately adds these files there (they should not).
- `git push` from **coherence** only goes where **you** set `origin` — and only after you create a **new empty** GitHub repo (recommended name: `coherence` under your org/user).
- Do **not** force-push Coherence into `aurumflux20/seal` or any existing product repo.

## Safe first publish (when Zah says so)

```bash
# 1) On GitHub: create NEW empty repo  (no README if you already have local history)
#    e.g. https://github.com/YOUR_USER/coherence
#    Do NOT use the seal repo URL.

# 2) Local only — from this directory:
cd ~/packages/coherence
git remote -v                    # must be empty first time
git remote add origin git@github.com:YOUR_USER/coherence.git
# refuse if URL contains seal or aurumflux-api:
./scripts/check-remote-safe.sh

git push -u origin main
```

## Blocked remote patterns (hook)

The `pre-push` hook refuses remotes whose URL matches:

- `seal`
- `aurumflux-api`
- `bondpermit`
- `glint` (repo name segment)

Override only if you truly mean it: `COHERENCE_ALLOW_UNSAFE_REMOTE=1`

## Risk to other projects

| Action | Risk to other repos |
|--------|---------------------|
| Edit/commit inside `packages/coherence` only | **None** |
| Push to a **new** `coherence` GitHub repo | **None** |
| `git add -A` from `~` without ignore | **Mitigated** by `packages/coherence/` in home `.gitignore` |
| Point `origin` at seal by mistake | **Blocked** by pre-push hook |
