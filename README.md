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
- `output/submission/RELEASE_NOTE_<campaign_id>.md`

Automated integrity check:
- `scripts/check_manuscript_pack_consistency.py`

One-command reviewer preflight:
```bash
./scripts/reviewer_preflight.sh \
  --campaign-id <campaign_id> \
  --campaign-root outputs/campaigns \
  --submission-dir output/submission
```
This runs manuscript-pack build, audit gates, consistency checks, and anonymous leak scan.

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

## submit_v1 Greenfield Pipeline
Isolated end-to-end final-submission workflow (no edits to legacy flow outputs):
```bash
PYTHONPATH=src ./scripts/submit_v1/run_full_submit_pipeline.sh
```

Direct CLI entrypoint:
```bash
python -m uavtre.submit_v1.run \
  --campaign-id journal_v3_full_20260219_000231 \
  --campaign-root outputs/campaigns \
  --mode full --resume
```

submit_v1 outputs:
- `output_submit_v1/submission/`
- `output_submit_v1/manuscript/main.pdf`
- `submission_submit_v1/anonymous/`
- `submission_submit_v1/camera_ready/`
- `outputs/pipeline_v1_runs/<run_id>/STATE.json`

## submit_v2 Greenfield Pipeline (Journal-Grade Manuscript + TR-E Upload Pack)
submit_v2 upgrades the manuscript to an Elsevier/TR-E-style LaTeX document with real tables/figures (no placeholders),
validated evidence tags (\evid{...}), and campaign-scoped reviewer bundles.

Run end-to-end (campaign-locked, no rerun):
```bash
PYTHONPATH=src ./scripts/submit_v2/run_full_submit_pipeline.sh journal_v3_full_20260219_000231
```

Direct CLI entrypoint:
```bash
PYTHONPATH=src .venv/bin/python -m uavtre.submit_v2.run   --campaign-id journal_v3_full_20260219_000231   --campaign-root outputs/campaigns   --mode full --resume
```

submit_v2 outputs:
- `output_submit_v2/submission/`
- `output_submit_v2/manuscript/anonymous/main.pdf`
- `output_submit_v2/manuscript/camera_ready/main.pdf`
- `submission_submit_v2/anonymous/`
- `submission_submit_v2/camera_ready/`
- `outputs/pipeline_v2_runs/<run_id>/STATE.json`

