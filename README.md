# uav_tr_e_project

Journal-grade reproducibility repository for reliability-aware multi-UAV pickup and delivery experiments targeting *Transportation Research Part E* (TR-E).

## Scope
- Main heuristic engine: OR-Tools with soft/hard TW support and net-load capacity dimension.
- Baseline heuristic: PyVRP (baseline/ablation).
- Exact/bound engine: HiGHS MIP with certificate-aware claim policy.
- Scientific claim policy:
  - `N <= 10`: exact claim only with optimality certificate.
  - `N = 20/40`: incumbent + bound + gap.
  - `N = 80`: scalability only (no gap claim).

## Repository Layout
- `src/uavtre/` core package.
- `configs/` base config, v3 profiles, and A/B calibrated overrides.
- `benchmarks/frozen/` frozen benchmark instances.
- `outputs/` generated CSVs, campaign folders, and audits.
- `output/submission/` manuscript pack artifacts.
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

## V3 Robust Campaign (CPU-Sharded)
Run full two-stage campaign (A/B, core + robustness):
```bash
PYTHONPATH=src ./scripts/run_journal_v3_robust.sh
```

Useful environment overrides:
```bash
CAMPAIGN_ID=journal_v3_demo NUM_SHARDS=12 MAX_CASES=0 \
RUN_STAGE1_CORE=1 RUN_STAGE2_ROBUST=1 \
PYTHONPATH=src ./scripts/run_journal_v3_robust.sh
```

Campaign artifacts are written to:
- `outputs/campaigns/<campaign_id>/...`
- `outputs/audit/journal_readiness_<campaign_id>.json`

Campaign metadata files:
- `CAMPAIGN_MANIFEST.json`
- `RUN_PLAN.json`
- `ENV_SNAPSHOT.json`
- `COMMAND_LOG.csv`

## Manuscript Pack (Campaign-Locked)
Build manuscript-support artifacts and reviewer bundles from one campaign:
```bash
./scripts/build_manuscript_pack.sh \
  --campaign-id <campaign_id> \
  --campaign-root outputs/campaigns \
  --submission-dir output/submission
```

Generated campaign-suffixed files:
- `output/submission/claim_evidence_map_<campaign_id>.md`
- `output/submission/results_discussion_draft_<campaign_id>.md`
- `output/submission/next_steps_<campaign_id>.md`
- `output/submission/TABLE_FIGURE_INDEX_<campaign_id>.md`
- `output/submission/MANUSCRIPT_PACK_MANIFEST_<campaign_id>.json`

## Public CLI Interfaces
```bash
python -m uavtre.run_experiments --config configs/base.json --output outputs/results_main.csv

python -m uavtre.run_benchmarks \
  --config configs/base.json \
  --profile main_table \
  --profile-override configs/overrides/main_table_v3_core_fullseed_A_calibrated.json \
  --output outputs/results_main.csv \
  --benchmark-dir benchmarks/frozen \
  --shard-index 0 --num-shards 12 --resume \
  --campaign-id journal_v3_demo --stage-tag core_main_A

python -m uavtre.make_review_pack --mode anonymous --campaign-id journal_v3_demo
python -m uavtre.make_review_pack --mode camera_ready --campaign-id journal_v3_demo
```

## Outputs
- `results_main.csv`
- `results_routes.csv`
- `results_significance.csv`

`results_significance.csv` includes Holm-adjusted p-values, effect size, CI, and pair counts.

## Journal Readiness Audit
Run gate check for a campaign:
```bash
PYTHONPATH=src .venv/bin/python scripts/audit_journal_readiness.py \
  --campaign-id <campaign_id> \
  --campaign-root outputs/campaigns \
  --json-out outputs/audit/journal_readiness_<campaign_id>.json \
  --fail-on-critical --fail-on-high
```

## Review Packaging
Campaign-scoped bundles:
```bash
CAMPAIGN_ID=<campaign_id> CAMPAIGN_ROOT=outputs/campaigns ./scripts/make_review_pack.sh
```

## Docker Workflow
```bash
docker build -t uavtre:1.0.0 .
docker run --rm -v "$PWD":/workspace -w /workspace uavtre:1.0.0 \
  python -m uavtre.run_experiments --config configs/base.json --profile quick --output outputs/results_main.csv --max-cases 1
```

## License
MIT (see `LICENSE`).
