# uav_tr_e_project

Journal-grade reproducibility repository for reliability-aware multi-UAV pickup and delivery experiments targeting *Transportation Research Part E* (TR-E).

## Scope
- Main heuristic engine: OR-Tools with soft/hard TW support and net-load capacity dimension.
- Baseline heuristic: PyVRP (reported as baseline/ablation when feasible coverage degrades).
- Exact/bound engine: HiGHS MIP with certificate-aware claim policy.
- Scientific claim policy:
  - `N <= 10`: exact claim only with optimality certificate.
  - `N = 20/40`: incumbent + bound + gap.
  - `N = 80`: scalability only (no gap claim).

## Repository Layout
- `src/uavtre/` core package.
- `configs/` base config and profile overrides.
- `benchmarks/frozen/` frozen benchmark instances.
- `outputs/` generated CSVs and figures.
- `submission/anonymous/` and `submission/camera_ready/` review bundles.

## Quick Start (venv)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
pip install -e .
```

Quick deterministic run:
```bash
./scripts/run_quick.sh
```

## Journal Campaign (Calibrated + Claim-Ready)
Main table + scalability (TW family A):
```bash
MAIN_MAX_CASES=48 SCAL_MAX_CASES=16 RUN_TW_B=0 ./scripts/run_v2_core_pipeline.sh
```

Main table + scalability for both TW families A and B:
```bash
MAIN_MAX_CASES=48 SCAL_MAX_CASES=16 RUN_TW_B=1 ./scripts/run_v2_core_pipeline.sh
```

Outputs:
- `outputs/main_table_v2_core/`, `outputs/scalability_v2_core/`, `outputs/paper_v2_core/` (TW A)
- `outputs/main_table_v2_core_B/`, `outputs/scalability_v2_core_B/`, `outputs/paper_v2_core_B/` (TW B)

## Public CLI Interfaces
```bash
python -m uavtre.run_experiments --config configs/base.json --output outputs/results_main.csv
python -m uavtre.run_benchmarks --config configs/base.json --profile main_table
python -m uavtre.make_review_pack --mode anonymous
python -m uavtre.make_review_pack --mode camera_ready
```

## Outputs
- `outputs/results_main.csv`
- `outputs/results_routes.csv`
- `outputs/results_significance.csv`

`results_significance.csv` includes adjusted p-values (Holm), effect size, CI, and pair counts.

## Determinism and Reproducibility
- Deterministic seeds are explicit in configs.
- Base communication profile is calibrated (`snr_threshold_db=25.0`) and can be re-calibrated via `scripts/calibrate_comm_profile.py`.
- Frozen benchmark instances are generated under `benchmarks/frozen/`.
- Outputs include `run_id`, `profile`, `git_sha` (or deterministic fallback hash), and `timestamp`.
- Reproduction instructions: see `REPRODUCIBILITY.md`.

## Review Packaging
Generate both bundles:
```bash
./scripts/make_review_pack.sh
```

Bundle manifests are produced as `submission/*/BUNDLE_MANIFEST.json`.

## Docker Workflow
```bash
docker build -t uavtre:1.0.0 .
docker run --rm -v "$PWD":/workspace -w /workspace uavtre:1.0.0 \
  python -m uavtre.run_experiments --config configs/base.json --profile quick --output outputs/results_main.csv --max-cases 1
```

## License
MIT (see `LICENSE`).

## Journal Readiness Audit
Run the automated gate check after campaign runs:
```bash
PYTHONPATH=src .venv/bin/python scripts/audit_journal_readiness.py --output-root outputs --fail-on-critical
```
A JSON audit report is written to `outputs/audit/`.
