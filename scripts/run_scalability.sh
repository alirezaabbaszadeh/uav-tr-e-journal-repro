#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:src"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

"$PYTHON_BIN" -m uavtre.run_benchmarks \
  --config configs/base.json \
  --profile scalability \
  --output outputs/results_main.csv \
  --benchmark-dir benchmarks/frozen
