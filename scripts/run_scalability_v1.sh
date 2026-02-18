#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:src"

.venv/bin/python -m uavtre.run_benchmarks \
  --config configs/base.json \
  --profile scalability \
  --profile-override configs/profiles/scalability_v1.json \
  --output outputs/scalability_v1/results_main.csv \
  --benchmark-dir benchmarks/frozen/scalability_v1
