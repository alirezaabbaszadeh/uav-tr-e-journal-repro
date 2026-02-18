# Reproducibility Protocol

## 1) Local Reproduction (venv)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
pip install -e .
```

Quick deterministic check:
```bash
./scripts/run_quick.sh
```

Expected artifacts:
- `outputs/results_main.csv`
- `outputs/results_routes.csv`
- `outputs/results_significance.csv`

## 2) Journal Campaign (Calibrated Communication)
TW Family A only:
```bash
MAIN_MAX_CASES=48 SCAL_MAX_CASES=16 RUN_TW_B=0 ./scripts/run_v2_core_pipeline.sh
```

TW Family A + B:
```bash
MAIN_MAX_CASES=48 SCAL_MAX_CASES=16 RUN_TW_B=1 ./scripts/run_v2_core_pipeline.sh
```

Paper tables:
- `outputs/paper_v2_core/`
- `outputs/paper_v2_core_B/`

## 3) Frozen Benchmarks
Generate/refresh a deterministic set:
```bash
python -m uavtre.run_benchmarks --config configs/base.json --profile main_table --benchmark-dir benchmarks/frozen --output outputs/results_main.csv
```

Re-running with unchanged code/config should recreate the same frozen files and consistent objectives within floating-point tolerance.

## 4) CI-equivalent Local Check
```bash
pytest
python -m uavtre.run_benchmarks --config configs/base.json --profile main_table --profile-override configs/profiles/ci_journal_smoke.json --output outputs/ci_main/results_main.csv --benchmark-dir benchmarks/frozen/ci_main --max-cases 3
python -m uavtre.run_benchmarks --config configs/base.json --profile scalability --profile-override configs/profiles/ci_journal_smoke.json --output outputs/ci_scal/results_main.csv --benchmark-dir benchmarks/frozen/ci_scal --max-cases 2
```

## 5) Review Package Generation
```bash
./scripts/make_review_pack.sh
```

Packages are created in:
- `submission/anonymous/`
- `submission/camera_ready/`

Each bundle includes `BUNDLE_MANIFEST.json` with artifact counts.

## Journal-Readiness Gate
After generating campaign outputs, run:
```bash
PYTHONPATH=src .venv/bin/python scripts/audit_journal_readiness.py --output-root outputs --fail-on-critical
```
The command fails on unmet critical criteria and writes a detailed JSON report under `outputs/audit/`.
