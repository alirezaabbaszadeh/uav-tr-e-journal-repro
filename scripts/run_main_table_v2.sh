#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"

BASE_CFG="configs/base.json"
PROFILE_OVERRIDE="configs/profiles/main_table_v2.json"
COMM_OVERRIDE="configs/overrides/comm_calibrated_q1.json"
MERGED_OVERRIDE="configs/overrides/main_table_v2_calibrated.json"

.venv/bin/python scripts/calibrate_comm_profile.py \
  --config "$BASE_CFG" \
  --profile quick \
  --target-low 0.05 \
  --target-high 0.25 \
  --bs-count 4 \
  --n-clients 20 \
  --delta-min 10 \
  --seeds 1 2 3 \
  --output "$COMM_OVERRIDE"

.venv/bin/python - <<'PY'
import json
from pathlib import Path

profile_path = Path('configs/profiles/main_table_v2.json')
comm_path = Path('configs/overrides/comm_calibrated_q1.json')
out_path = Path('configs/overrides/main_table_v2_calibrated.json')


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
out_path.write_text(json.dumps(merged, indent=2), encoding='utf-8')
print('written', out_path)
PY

.venv/bin/python -m uavtre.run_benchmarks \
  --config "$BASE_CFG" \
  --profile main_table \
  --profile-override "$MERGED_OVERRIDE" \
  --output outputs/main_table_v2/results_main.csv \
  --benchmark-dir benchmarks/frozen/main_table_v2 \
  --max-cases "${MAX_CASES:-0}"
