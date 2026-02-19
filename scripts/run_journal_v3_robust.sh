#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

TIMESTAMP_UTC="$(date -u +%Y%m%d_%H%M%S)"
CAMPAIGN_ID="${CAMPAIGN_ID:-journal_v3_${TIMESTAMP_UTC}}"
CAMPAIGN_ROOT="${CAMPAIGN_ROOT:-outputs/campaigns}"
CAMPAIGN_DIR="${CAMPAIGN_ROOT}/${CAMPAIGN_ID}"
NUM_SHARDS="${NUM_SHARDS:-12}"
MAX_CASES="${MAX_CASES:-0}"
RUN_STAGE1_CORE="${RUN_STAGE1_CORE:-1}"
RUN_STAGE2_ROBUST="${RUN_STAGE2_ROBUST:-1}"

mkdir -p "${CAMPAIGN_DIR}/logs" "${CAMPAIGN_DIR}/benchmarks"

echo "campaign_id=${CAMPAIGN_ID}"
echo "campaign_dir=${CAMPAIGN_DIR}"
echo "num_shards=${NUM_SHARDS}"

run_sharded_stage() {
  local profile="$1"
  local override_path="$2"
  local output_dir="$3"
  local benchmark_dir="$4"
  local stage_tag="$5"

  mkdir -p "$output_dir/shards" "$benchmark_dir"

  local pids=()
  local shard
  for (( shard=0; shard<NUM_SHARDS; shard++ )); do
    local shard_dir
    shard_dir="$output_dir/shards/shard_$(printf '%02d' "$shard")"
    mkdir -p "$shard_dir"

    local log_file
    log_file="${CAMPAIGN_DIR}/logs/${stage_tag}_shard$(printf '%02d' "$shard").log"

    local cmd=(
      "$PYTHON_BIN" -m uavtre.run_benchmarks
      --config configs/base.json
      --profile "$profile"
      --profile-override "$override_path"
      --output "$shard_dir/results_main.csv"
      --benchmark-dir "$benchmark_dir"
      --campaign-id "$CAMPAIGN_ID"
      --campaign-root "$CAMPAIGN_ROOT"
      --stage-tag "$stage_tag"
      --shard-index "$shard"
      --num-shards "$NUM_SHARDS"
      --resume
    )
    if [[ "$MAX_CASES" != "0" ]]; then
      cmd+=(--max-cases "$MAX_CASES")
    fi

    ("${cmd[@]}") >"$log_file" 2>&1 &
    pids+=("$!")
  done

  local fail=0
  local pid
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      fail=1
    fi
  done

  if [[ "$fail" != "0" ]]; then
    echo "stage failed: ${stage_tag}" >&2
    return 1
  fi

  "$PYTHON_BIN" scripts/merge_sharded_results.py \
    --shards-root "$output_dir/shards" \
    --output-dir "$output_dir" \
    --require-shards "$NUM_SHARDS" \
    >"${CAMPAIGN_DIR}/logs/${stage_tag}_merge.log" 2>&1
}

if [[ "$RUN_STAGE1_CORE" == "1" ]]; then
  run_sharded_stage "main_table" "configs/overrides/main_table_v3_core_fullseed_A_calibrated.json" \
    "${CAMPAIGN_DIR}/main_A_core" "${CAMPAIGN_DIR}/benchmarks/main_A_core" "core_main_A"

  run_sharded_stage "scalability" "configs/overrides/scalability_v3_core_fullseed_A_calibrated.json" \
    "${CAMPAIGN_DIR}/scal_A_core" "${CAMPAIGN_DIR}/benchmarks/scal_A_core" "core_scal_A"

  run_sharded_stage "main_table" "configs/overrides/main_table_v3_core_fullseed_B_calibrated.json" \
    "${CAMPAIGN_DIR}/main_B_core" "${CAMPAIGN_DIR}/benchmarks/main_B_core" "core_main_B"

  run_sharded_stage "scalability" "configs/overrides/scalability_v3_core_fullseed_B_calibrated.json" \
    "${CAMPAIGN_DIR}/scal_B_core" "${CAMPAIGN_DIR}/benchmarks/scal_B_core" "core_scal_B"
fi

if [[ "$RUN_STAGE2_ROBUST" == "1" ]]; then
  run_sharded_stage "main_table" "configs/overrides/main_table_v3_robustness_A_calibrated.json" \
    "${CAMPAIGN_DIR}/main_A_robust" "${CAMPAIGN_DIR}/benchmarks/main_A_robust" "robust_main_A"

  run_sharded_stage "main_table" "configs/overrides/main_table_v3_robustness_B_calibrated.json" \
    "${CAMPAIGN_DIR}/main_B_robust" "${CAMPAIGN_DIR}/benchmarks/main_B_robust" "robust_main_B"

  run_sharded_stage "main_table" "configs/overrides/main_table_v3_k_sensitivity_A_calibrated.json" \
    "${CAMPAIGN_DIR}/main_A_k" "${CAMPAIGN_DIR}/benchmarks/main_A_k" "robust_k_A"

  run_sharded_stage "main_table" "configs/overrides/main_table_v3_k_sensitivity_B_calibrated.json" \
    "${CAMPAIGN_DIR}/main_B_k" "${CAMPAIGN_DIR}/benchmarks/main_B_k" "robust_k_B"

  run_sharded_stage "scalability" "configs/overrides/scalability_v3_robustness_A_calibrated.json" \
    "${CAMPAIGN_DIR}/scal_A_robust" "${CAMPAIGN_DIR}/benchmarks/scal_A_robust" "robust_scal_A"

  run_sharded_stage "scalability" "configs/overrides/scalability_v3_robustness_B_calibrated.json" \
    "${CAMPAIGN_DIR}/scal_B_robust" "${CAMPAIGN_DIR}/benchmarks/scal_B_robust" "robust_scal_B"
fi

CAMPAIGN_DIR="$CAMPAIGN_DIR" "$PYTHON_BIN" - <<'PY'
import os
from pathlib import Path
import pandas as pd

camp = Path(os.environ["CAMPAIGN_DIR"])
(camp / "aggregated").mkdir(parents=True, exist_ok=True)

families = {
    "A": {
        "main": ["main_A_core", "main_A_robust", "main_A_k"],
        "scal": ["scal_A_core", "scal_A_robust"],
    },
    "B": {
        "main": ["main_B_core", "main_B_robust", "main_B_k"],
        "scal": ["scal_B_core", "scal_B_robust"],
    },
}

all_main = []
all_scal = []
for fam, parts in families.items():
    main_frames = []
    for d in parts["main"]:
        p = camp / d / "results_main.csv"
        if p.exists():
            main_frames.append(pd.read_csv(p))
    scal_frames = []
    for d in parts["scal"]:
        p = camp / d / "results_main.csv"
        if p.exists():
            scal_frames.append(pd.read_csv(p))

    if not main_frames or not scal_frames:
        continue

    main_df = pd.concat(main_frames, ignore_index=True)
    scal_df = pd.concat(scal_frames, ignore_index=True)
    main_df.to_csv(camp / "aggregated" / f"main_{fam}.csv", index=False)
    scal_df.to_csv(camp / "aggregated" / f"scal_{fam}.csv", index=False)

    all_main.append(main_df)
    all_scal.append(scal_df)

if all_main and all_scal:
    pd.concat(all_main, ignore_index=True).to_csv(camp / "aggregated" / "main_combined.csv", index=False)
    pd.concat(all_scal, ignore_index=True).to_csv(camp / "aggregated" / "scal_combined.csv", index=False)
PY

for fam in A B; do
  if [[ -f "${CAMPAIGN_DIR}/aggregated/main_${fam}.csv" && -f "${CAMPAIGN_DIR}/aggregated/scal_${fam}.csv" ]]; then
    MAIN_PATH="${CAMPAIGN_DIR}/aggregated/main_${fam}.csv" \
    SCAL_PATH="${CAMPAIGN_DIR}/aggregated/scal_${fam}.csv" \
    OUT_DIR="${CAMPAIGN_DIR}/paper_${fam}" \
    PYTHON_BIN="$PYTHON_BIN" ./scripts/make_paper_tables_v2.sh
  fi
done

if [[ -f "${CAMPAIGN_DIR}/aggregated/main_combined.csv" && -f "${CAMPAIGN_DIR}/aggregated/scal_combined.csv" ]]; then
  MAIN_PATH="${CAMPAIGN_DIR}/aggregated/main_combined.csv" \
  SCAL_PATH="${CAMPAIGN_DIR}/aggregated/scal_combined.csv" \
  OUT_DIR="${CAMPAIGN_DIR}/paper_combined" \
  PYTHON_BIN="$PYTHON_BIN" ./scripts/make_paper_tables_v2.sh
fi

AUDIT_CMD=(
  "$PYTHON_BIN" scripts/audit_journal_readiness.py
  --campaign-id "$CAMPAIGN_ID"
  --campaign-root "$CAMPAIGN_ROOT"
  --json-out "outputs/audit/journal_readiness_${CAMPAIGN_ID}.json"
)
if [[ "$MAX_CASES" == "0" ]]; then
  AUDIT_CMD+=(--fail-on-critical --fail-on-high)
fi
"${AUDIT_CMD[@]}" >"${CAMPAIGN_DIR}/logs/audit_${CAMPAIGN_ID}.log" 2>&1

./scripts/build_manuscript_pack.sh \
  --campaign-id "$CAMPAIGN_ID" \
  --campaign-root "$CAMPAIGN_ROOT" \
  --submission-dir "output/submission"

echo "v3 robust campaign complete: ${CAMPAIGN_ID}"
