#!/usr/bin/env bash
set -euo pipefail

MAIN_PATH="${MAIN_PATH:-outputs/main_table_v2/results_main.csv}"
SCAL_PATH="${SCAL_PATH:-outputs/scalability_v2/results_main.csv}"
OUT_DIR="${OUT_DIR:-outputs/paper_v2}"

export MAIN_PATH
export SCAL_PATH
export OUT_DIR

.venv/bin/python - <<'PY'
import os
from pathlib import Path
import numpy as np
import pandas as pd

main_path = Path(os.environ['MAIN_PATH'])
scal_path = Path(os.environ['SCAL_PATH'])
out_dir = Path(os.environ['OUT_DIR'])
out_dir.mkdir(parents=True, exist_ok=True)


def clean_inf(df: pd.DataFrame) -> pd.DataFrame:
    return df.replace([np.inf, -np.inf], np.nan)

frames = []
if main_path.exists():
    frames.append(clean_inf(pd.read_csv(main_path)))
if scal_path.exists():
    frames.append(clean_inf(pd.read_csv(scal_path)))
if not frames:
    raise SystemExit('No result files found for paper table generation.')

combined = pd.concat(frames, ignore_index=True)

if main_path.exists():
    dm = clean_inf(pd.read_csv(main_path))
    kpis = ['on_time_pct', 'total_tardiness_min', 'total_energy', 'risk_mean', 'runtime_total_s']
    main_summary = dm[dm['feasible_flag'] == 1].groupby(['method', 'N'])[kpis].agg(['mean', 'std']).reset_index()
    main_summary.columns = ['_'.join(c).strip('_') for c in main_summary.columns]
    main_summary.to_csv(out_dir / 'table_main_kpi_summary.csv', index=False)

    gap_summary = dm[(dm['claim_regime'] == 'bound_gap') & (dm['N'].isin([20, 40]))].groupby(
        ['method', 'N']
    )[['gap_pct', 'best_bound', 'incumbent_obj']].agg(['mean', 'std']).reset_index()
    gap_summary.columns = ['_'.join(c).strip('_') for c in gap_summary.columns]
    gap_summary.to_csv(out_dir / 'table_gap_summary.csv', index=False)

    feas = dm.groupby(['method', 'N'])['feasible_flag'].mean().reset_index(name='feasible_rate')
    feas.to_csv(out_dir / 'table_feasibility_rate.csv', index=False)

if scal_path.exists():
    ds = clean_inf(pd.read_csv(scal_path))
    ds.to_csv(out_dir / 'table_scalability_raw.csv', index=False)

insight = combined[
    (combined['feasible_flag'] == 1) & (combined['method'].isin(['ortools_main', 'pyvrp_baseline']))
].groupby(['method', 'B', 'Delta_min'])[['on_time_pct', 'total_tardiness_min', 'risk_mean']].mean().reset_index()
insight.to_csv(out_dir / 'table_managerial_insight_support.csv', index=False)

risk_check = combined.groupby(['method'])['risk_mean'].mean().reset_index(name='risk_mean_avg')
risk_check.to_csv(out_dir / 'table_risk_signal_check.csv', index=False)
PY
