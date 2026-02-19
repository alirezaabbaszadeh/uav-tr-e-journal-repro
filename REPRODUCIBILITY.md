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

## 2) V3 Robust Campaign (Two-Stage, CPU-Sharded)
```bash
CAMPAIGN_ID=journal_v3_<ts> NUM_SHARDS=12 MAX_CASES=0 \
RUN_STAGE1_CORE=1 RUN_STAGE2_ROBUST=1 \
PYTHONPATH=src ./scripts/run_journal_v3_robust.sh
```

Main outputs:
- `outputs/campaigns/<campaign_id>/main_A_core/`
- `outputs/campaigns/<campaign_id>/main_B_core/`
- `outputs/campaigns/<campaign_id>/scal_A_core/`
- `outputs/campaigns/<campaign_id>/scal_B_core/`
- `outputs/campaigns/<campaign_id>/main_A_robust/`
- `outputs/campaigns/<campaign_id>/main_B_robust/`
- `outputs/campaigns/<campaign_id>/main_A_k/`
- `outputs/campaigns/<campaign_id>/main_B_k/`
- `outputs/campaigns/<campaign_id>/scal_A_robust/`
- `outputs/campaigns/<campaign_id>/scal_B_robust/`
- `outputs/campaigns/<campaign_id>/paper_A/`, `paper_B/`, `paper_combined/`

Campaign traceability files:
- `outputs/campaigns/<campaign_id>/CAMPAIGN_MANIFEST.json`
- `outputs/campaigns/<campaign_id>/RUN_PLAN.json`
- `outputs/campaigns/<campaign_id>/ENV_SNAPSHOT.json`
- `outputs/campaigns/<campaign_id>/COMMAND_LOG.csv`
- `outputs/campaigns/<campaign_id>/logs/*.log`

## 3) Shard Merge Contract
Each shard writes to:
- `<stage_dir>/shards/shard_XX/results_main.csv`
- `<stage_dir>/shards/shard_XX/results_routes.csv`

Merging is deterministic via:
```bash
PYTHONPATH=src .venv/bin/python scripts/merge_sharded_results.py \
  --shards-root <stage_dir>/shards \
  --output-dir <stage_dir> \
  --require-shards 12
```

## 4) Audit Gates
```bash
PYTHONPATH=src .venv/bin/python scripts/audit_journal_readiness.py \
  --campaign-id <campaign_id> \
  --campaign-root outputs/campaigns \
  --json-out outputs/audit/journal_readiness_<campaign_id>.json \
  --fail-on-critical --fail-on-high
```

The command fails non-zero when critical (or high, if requested) gates fail.

## 5) Manuscript Pack + Review Bundles
Generate campaign-locked manuscript artifacts and bundles:
```bash
./scripts/build_manuscript_pack.sh \
  --campaign-id <campaign_id> \
  --campaign-root outputs/campaigns \
  --submission-dir output/submission
```

Generated manuscript artifacts:
- `output/submission/claim_evidence_map_<campaign_id>.md`
- `output/submission/results_discussion_draft_<campaign_id>.md`
- `output/submission/next_steps_<campaign_id>.md`
- `output/submission/TABLE_FIGURE_INDEX_<campaign_id>.md`
- `output/submission/MANUSCRIPT_PACK_MANIFEST_<campaign_id>.json`
- `output/submission/RELEASE_NOTE_<campaign_id>.md`

Integrity validation:
```bash
PYTHONPATH=src .venv/bin/python scripts/check_manuscript_pack_consistency.py   --campaign-id <campaign_id>   --submission-dir output/submission   --anonymous-dir submission/anonymous   --camera-ready-dir submission/camera_ready
```

## 6) Determinism Expectations
- Scenario generation is seed-driven.
- Shard partition uses deterministic index modulo.
- Resume mode skips already-existing `(run_id, method)` rows.
- Re-running same campaign config and seed set should reproduce benchmark instances and policy-consistent outputs (within floating-point tolerance).
