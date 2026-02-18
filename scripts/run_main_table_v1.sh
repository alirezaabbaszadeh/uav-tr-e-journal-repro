#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:src"

.venv/bin/python -m uavtre.run_benchmarks \
  --config configs/base.json \
  --profile main_table \
  --profile-override configs/profiles/main_table_v1.json \
  --output outputs/main_table_v1/results_main.csv \
  --benchmark-dir benchmarks/frozen/main_table_v1
