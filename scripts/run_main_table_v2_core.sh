#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

BASE_CFG="configs/base.json"
PROFILE_OVERRIDE="configs/profiles/main_table_v2_core.json"
COMM_OVERRIDE="configs/overrides/comm_calibrated_q1.json"

TW_FAMILY="${TW_FAMILY:-A}"
if [[ -n "${OUTPUT_DIR:-}" ]]; then
  OUTPUT_DIR="${OUTPUT_DIR}"
elif [[ "$TW_FAMILY" == "A" ]]; then
  OUTPUT_DIR="outputs/main_table_v2_core"
else
  OUTPUT_DIR="outputs/main_table_v2_core_${TW_FAMILY}"
fi

if [[ -n "${BENCHMARK_DIR:-}" ]]; then
  BENCHMARK_DIR="${BENCHMARK_DIR}"
elif [[ "$TW_FAMILY" == "A" ]]; then
  BENCHMARK_DIR="benchmarks/frozen/main_table_v2_core"
else
  BENCHMARK_DIR="benchmarks/frozen/main_table_v2_core_${TW_FAMILY}"
fi

MERGED_OVERRIDE="configs/overrides/main_table_v2_core_${TW_FAMILY}_calibrated.json"

"$PYTHON_BIN" scripts/calibrate_comm_profile.py \
  --config "$BASE_CFG" \
  --profile quick \
  --target-low 0.05 \
  --target-high 0.25 \
  --bs-count 4 \
  --n-clients 20 \
  --delta-min 10 \
  --seeds 1 2 3 \
  --output "$COMM_OVERRIDE"

PROFILE_OVERRIDE="$PROFILE_OVERRIDE" COMM_OVERRIDE="$COMM_OVERRIDE" MERGED_OVERRIDE="$MERGED_OVERRIDE" TW_FAMILY="$TW_FAMILY" "$PYTHON_BIN" - <<'PY'
import json
import os
from pathlib import Path

profile_path = Path(os.environ['PROFILE_OVERRIDE'])
comm_path = Path(os.environ['COMM_OVERRIDE'])
out_path = Path(os.environ['MERGED_OVERRIDE'])
tw_family = os.environ.get('TW_FAMILY', 'A')


def deep_merge(a, b):
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

p = json.loads(profile_path.read_text(encoding='utf-8'))
c = json.loads(comm_path.read_text(encoding='utf-8'))
merged = deep_merge(p, c)
merged.setdefault('tw', {})
merged['tw']['family'] = tw_family
out_path.write_text(json.dumps(merged, indent=2), encoding='utf-8')
print('written', out_path)
PY

mkdir -p "$OUTPUT_DIR" "$BENCHMARK_DIR"
"$PYTHON_BIN" -m uavtre.run_benchmarks \
  --config "$BASE_CFG" \
  --profile main_table \
  --profile-override "$MERGED_OVERRIDE" \
  --output "$OUTPUT_DIR/results_main.csv" \
  --benchmark-dir "$BENCHMARK_DIR" \
  --max-cases "${MAX_CASES:-0}"
