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

"$PYTHON_BIN" scripts/generate_journal_core_writing_pack.py \
  --campaign-id "$CAMPAIGN_ID" \
  --campaign-root "$CAMPAIGN_ROOT" \
  --submission-dir "$SUBMISSION_DIR"

"$PYTHON_BIN" -m uavtre.make_review_pack \
  --mode anonymous \
  --campaign-root "$CAMPAIGN_ROOT" \
  --campaign-id "$CAMPAIGN_ID"

"$PYTHON_BIN" -m uavtre.make_review_pack \
  --mode camera_ready \
  --campaign-root "$CAMPAIGN_ROOT" \
  --campaign-id "$CAMPAIGN_ID"

required=(
  "$SUBMISSION_DIR/claim_evidence_map_${CAMPAIGN_ID}.md"
  "$SUBMISSION_DIR/results_discussion_draft_${CAMPAIGN_ID}.md"
  "$SUBMISSION_DIR/next_steps_${CAMPAIGN_ID}.md"
  "$SUBMISSION_DIR/TABLE_FIGURE_INDEX_${CAMPAIGN_ID}.md"
  "$SUBMISSION_DIR/MANUSCRIPT_PACK_MANIFEST_${CAMPAIGN_ID}.json"
  "submission/anonymous/BUNDLE_MANIFEST.json"
  "submission/camera_ready/BUNDLE_MANIFEST.json"
)

for p in "${required[@]}"; do
  if [[ ! -f "$p" ]]; then
    echo "missing required artifact: $p" >&2
    exit 1
  fi
done

echo "manuscript pack built for campaign: $CAMPAIGN_ID"
