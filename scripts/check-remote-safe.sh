#!/usr/bin/env bash
# Refuse remotes that point at other AurumFlux / product repos.
set -euo pipefail
cd "$(dirname "$0")/.."

UNSAFE='seal|aurumflux-api|bondpermit|/glint\.|glint-|\.git/seal'
found=0
while read -r name url; do
  [ -z "${name:-}" ] && continue
  if echo "$url" | grep -Eiq "$UNSAFE"; then
    echo "UNSAFE remote: $name → $url" >&2
    found=1
  else
    echo "ok remote: $name → $url"
  fi
done < <(git remote -v | awk '{print $1, $2}' | sort -u)

if [ "$found" -ne 0 ]; then
  if [ "${COHERENCE_ALLOW_UNSAFE_REMOTE:-}" = "1" ]; then
    echo "WARNING: override COHERENCE_ALLOW_UNSAFE_REMOTE=1" >&2
    exit 0
  fi
  echo "Refusing: Coherence must not share remotes with seal/aurumflux-api/etc." >&2
  echo "Create a NEW empty GitHub repo named coherence and point origin there." >&2
  exit 1
fi

if ! git remote | grep -q .; then
  echo "No remotes configured (safe). Add origin only to a NEW empty coherence repo."
fi
exit 0
