#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"

CAMPAIGN_ID="${CAMPAIGN_ID:-journal_v3_full_20260219_000231}"
CAMPAIGN_ROOT="${CAMPAIGN_ROOT:-outputs/campaigns}"
MODE="${MODE:-full}"
RESUME_FLAG="${RESUME_FLAG:-1}"
RUN_ID="${RUN_ID:-}"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

cmd=("$PYTHON_BIN" -m uavtre.submit_v1.run
  --campaign-id "$CAMPAIGN_ID"
  --campaign-root "$CAMPAIGN_ROOT"
  --mode "$MODE")

if [[ "$RESUME_FLAG" == "1" ]]; then
  cmd+=(--resume)
fi
if [[ -n "$RUN_ID" ]]; then
  cmd+=(--run-id "$RUN_ID")
fi

"${cmd[@]}"
