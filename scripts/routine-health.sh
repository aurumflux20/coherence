#!/usr/bin/env bash
# Routine health check for Coherence.
# Exit 0 = GREEN · Exit 1 = RED (Nova must fix)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

OUT="${COHERENCE_HEALTH_OUT:-$ROOT/.coherence/health-latest.json}"
mkdir -p "$(dirname "$OUT")"

echo "[routine-health] $(date -u +%Y-%m-%dT%H:%M:%SZ) root=$ROOT"
python -m coherence health --out "$OUT"
code=$?
if [[ "$code" -ne 0 ]]; then
  echo "[routine-health] RED — see $OUT"
  echo "[routine-health] NEXT: Nova fix per docs/NOVA-HEALTH-AGENT.md"
  exit 1
fi
echo "[routine-health] GREEN"
exit 0
