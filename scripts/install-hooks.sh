#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cp scripts/pre-push.sample .git/hooks/pre-push
chmod +x .git/hooks/pre-push scripts/check-remote-safe.sh
echo "Installed pre-push isolation hook."
