# Build Instructions

## 1) Environment bootstrap
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
pip install -e .
```

## 2) Run/refresh full campaign (CPU-sharded, 12 shards)
```bash
CAMPAIGN_ID=journal_v3_full_20260219_000231 NUM_SHARDS=12 MAX_CASES=0 \
RUN_STAGE1_CORE=1 RUN_STAGE2_ROBUST=1 \
PYTHONPATH=src ./scripts/run_journal_v3_robust.sh
```

## 3) Run campaign readiness audit
```bash
PYTHONPATH=src .venv/bin/python scripts/audit_journal_readiness.py \
  --campaign-id journal_v3_full_20260219_000231 \
  --campaign-root /home/ali/code/UAV/uav_tr_e_project/outputs/campaigns \
  --json-out outputs/audit/journal_readiness_journal_v3_full_20260219_000231.json \
  --fail-on-critical --fail-on-high
```

## 4) Build manuscript package + review bundles
```bash
./scripts/build_manuscript_pack.sh \
  --campaign-id journal_v3_full_20260219_000231 \
  --campaign-root /home/ali/code/UAV/uav_tr_e_project/outputs/campaigns \
  --submission-dir /home/ali/code/UAV/uav_tr_e_project/output/submission
```

## 5) Command provenance
- Campaign run plan: `outputs/campaigns/journal_v3_full_20260219_000231/RUN_PLAN.json`
- Command history: `outputs/campaigns/journal_v3_full_20260219_000231/COMMAND_LOG.csv`
- Environment snapshot: `outputs/campaigns/journal_v3_full_20260219_000231/ENV_SNAPSHOT.json`
- Launcher and stage logs: `outputs/campaigns/journal_v3_full_20260219_000231/logs/*.log`
