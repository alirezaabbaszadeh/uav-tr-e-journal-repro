# Build Instructions

## Python (venv)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
pip install -e .
```

## Quick Sanity Run
```bash
PYTHONPATH=src .venv/bin/python -m uavtre.run_experiments   --config configs/base.json   --profile quick   --output outputs/results_main.csv   --max-cases 1
```

## Journal-Core Campaign (A/B)
```bash
PYTHONPATH=src .venv/bin/python -m uavtre.run_benchmarks   --config configs/base.json   --profile main_table   --profile-override configs/overrides/main_table_journal_core_A.json   --output outputs/main_table_v2_core/results_main.csv   --benchmark-dir benchmarks/frozen/main_table_v2_core

PYTHONPATH=src .venv/bin/python -m uavtre.run_benchmarks   --config configs/base.json   --profile scalability   --profile-override configs/overrides/scalability_journal_core_A.json   --output outputs/scalability_v2_core/results_main.csv   --benchmark-dir benchmarks/frozen/scalability_v2_core

PYTHONPATH=src .venv/bin/python -m uavtre.run_benchmarks   --config configs/base.json   --profile main_table   --profile-override configs/overrides/main_table_journal_core_B.json   --output outputs/main_table_v2_core_B/results_main.csv   --benchmark-dir benchmarks/frozen/main_table_v2_core_B

PYTHONPATH=src .venv/bin/python -m uavtre.run_benchmarks   --config configs/base.json   --profile scalability   --profile-override configs/overrides/scalability_journal_core_B.json   --output outputs/scalability_v2_core_B/results_main.csv   --benchmark-dir benchmarks/frozen/scalability_v2_core_B
```

## Audit + Writing Pack
```bash
PYTHONPATH=src .venv/bin/python scripts/audit_journal_readiness.py   --output-root outputs   --json-out outputs/audit/journal_readiness_journal_core_20260219_013349.json   --fail-on-critical

PYTHONPATH=src .venv/bin/python scripts/generate_journal_core_writing_pack.py
```

## Review Bundles
```bash
./scripts/make_review_pack.sh
```
