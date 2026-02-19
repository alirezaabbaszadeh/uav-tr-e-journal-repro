#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:src"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

CMD_EXTRA=()
if [[ -n "${CAMPAIGN_ID:-}" ]]; then
  CMD_EXTRA+=(--campaign-id "$CAMPAIGN_ID")
fi
if [[ -n "${CAMPAIGN_ROOT:-}" ]]; then
  CMD_EXTRA+=(--campaign-root "$CAMPAIGN_ROOT")
fi

"$PYTHON_BIN" -m uavtre.make_review_pack --mode anonymous "${CMD_EXTRA[@]}"
"$PYTHON_BIN" -m uavtre.make_review_pack --mode camera_ready "${CMD_EXTRA[@]}"
