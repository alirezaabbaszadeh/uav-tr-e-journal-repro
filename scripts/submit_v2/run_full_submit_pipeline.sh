#!/usr/bin/env bash
set -euo pipefail

CAMPAIGN_ID="${1:-journal_v3_full_20260219_000231}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="${PY_BIN:-.venv/bin/python}"

"$PY_BIN" -m uavtre.submit_v2.run \
  --campaign-id "$CAMPAIGN_ID" \
  --campaign-root outputs/campaigns \
  --mode full \
  --resume
