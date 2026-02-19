#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"

CAMPAIGN_ID=""
CAMPAIGN_ROOT="outputs/campaigns"
SUBMISSION_DIR="output/submission"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --campaign-id)
      CAMPAIGN_ID="$2"
      shift 2
      ;;
    --campaign-root)
      CAMPAIGN_ROOT="$2"
      shift 2
      ;;
    --submission-dir)
      SUBMISSION_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$CAMPAIGN_ID" ]]; then
  echo "--campaign-id is required" >&2
  exit 2
fi

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

echo "[1/4] Building manuscript pack..."
./scripts/build_manuscript_pack.sh \
  --campaign-id "$CAMPAIGN_ID" \
  --campaign-root "$CAMPAIGN_ROOT" \
  --submission-dir "$SUBMISSION_DIR"

echo "[2/4] Running journal audit gates..."
"$PYTHON_BIN" scripts/audit_journal_readiness.py \
  --campaign-id "$CAMPAIGN_ID" \
  --campaign-root "$CAMPAIGN_ROOT" \
  --json-out "outputs/audit/journal_readiness_${CAMPAIGN_ID}.json" \
  --fail-on-critical --fail-on-high

echo "[3/4] Running manuscript-pack consistency checks..."
"$PYTHON_BIN" scripts/check_manuscript_pack_consistency.py \
  --campaign-id "$CAMPAIGN_ID" \
  --submission-dir "$SUBMISSION_DIR" \
  --anonymous-dir "submission/anonymous" \
  --camera-ready-dir "submission/camera_ready"

echo "[4/4] Checking anonymous bundle for identity leaks..."
if rg -n -i "ali|@gmail|orcid|affiliation|university|author" \
  submission/anonymous \
  --glob '!**/*.json' --glob '!**/*.csv' > /tmp/uavtre_anonymous_leaks.txt; then
  echo "anonymous bundle contains potential identity markers:" >&2
  cat /tmp/uavtre_anonymous_leaks.txt >&2
  exit 1
fi

echo "reviewer preflight passed for campaign: $CAMPAIGN_ID"
echo "audit: outputs/audit/journal_readiness_${CAMPAIGN_ID}.json"
echo "manifest: $SUBMISSION_DIR/MANUSCRIPT_PACK_MANIFEST_${CAMPAIGN_ID}.json"
