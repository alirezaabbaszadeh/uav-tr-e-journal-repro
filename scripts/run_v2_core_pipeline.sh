#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"

MAIN_MAX_CASES="${MAIN_MAX_CASES:-48}"
SCAL_MAX_CASES="${SCAL_MAX_CASES:-16}"
RUN_TW_B="${RUN_TW_B:-1}"

MAX_CASES="$MAIN_MAX_CASES" TW_FAMILY=A ./scripts/run_main_table_v2_core.sh
MAX_CASES="$SCAL_MAX_CASES" TW_FAMILY=A ./scripts/run_scalability_v2_core.sh
MAIN_PATH=outputs/main_table_v2_core/results_main.csv \
SCAL_PATH=outputs/scalability_v2_core/results_main.csv \
OUT_DIR=outputs/paper_v2_core \
./scripts/make_paper_tables_v2.sh

if [[ "$RUN_TW_B" == "1" ]]; then
  MAX_CASES="$MAIN_MAX_CASES" TW_FAMILY=B OUTPUT_DIR=outputs/main_table_v2_core_B BENCHMARK_DIR=benchmarks/frozen/main_table_v2_core_B ./scripts/run_main_table_v2_core.sh
  MAX_CASES="$SCAL_MAX_CASES" TW_FAMILY=B OUTPUT_DIR=outputs/scalability_v2_core_B BENCHMARK_DIR=benchmarks/frozen/scalability_v2_core_B ./scripts/run_scalability_v2_core.sh
  MAIN_PATH=outputs/main_table_v2_core_B/results_main.csv \
  SCAL_PATH=outputs/scalability_v2_core_B/results_main.csv \
  OUT_DIR=outputs/paper_v2_core_B \
  ./scripts/make_paper_tables_v2.sh
fi

echo "v2_core pipeline complete"
