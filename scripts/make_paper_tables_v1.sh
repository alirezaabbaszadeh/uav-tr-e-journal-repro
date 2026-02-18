#!/usr/bin/env bash
set -euo pipefail

.venv/bin/python - <<'PY'
from pathlib import Path
import numpy as np
import pandas as pd

main_path = Path('outputs/main_table_v1/results_main.csv')
scal_path = Path('outputs/scalability_v1/results_main.csv')
out_dir = Path('outputs/paper_v1')
out_dir.mkdir(parents=True, exist_ok=True)


def clean_inf(df: pd.DataFrame) -> pd.DataFrame:
    return df.replace([np.inf, -np.inf], np.nan)


frames = []
if main_path.exists():
    frames.append(pd.read_csv(main_path))
if scal_path.exists():
    frames.append(pd.read_csv(scal_path))

if not frames:
    raise SystemExit('No input results found.')

if len(frames) == 2:
    combined = pd.concat(frames, ignore_index=True)
else:
    combined = frames[0]

combined = clean_inf(combined)

if main_path.exists():
    df = clean_inf(pd.read_csv(main_path))

    kpis = ['on_time_pct', 'total_tardiness_min', 'total_energy', 'risk_mean', 'runtime_total_s']
    main_summary = (
        df[df['feasible_flag'] == 1]
        .groupby(['method', 'N'])[kpis]
        .agg(['mean', 'std'])
        .reset_index()
    )
    main_summary.columns = ['_'.join(c).strip('_') for c in main_summary.columns]
    main_summary.to_csv(out_dir / 'table_main_kpi_summary.csv', index=False)

    gap_raw = df[(df['N'].isin([20, 40])) & (df['claim_regime'] == 'bound_gap')].copy()
    gap_raw['gap_pct'] = pd.to_numeric(gap_raw['gap_pct'], errors='coerce')
    gap_raw['best_bound'] = pd.to_numeric(gap_raw['best_bound'], errors='coerce')
    gap_raw['incumbent_obj'] = pd.to_numeric(gap_raw['incumbent_obj'], errors='coerce')
    gap_raw = clean_inf(gap_raw)

    gap_summary = (
        gap_raw.groupby(['method', 'N'])[['gap_pct', 'best_bound', 'incumbent_obj']]
        .agg(['mean', 'std'])
        .reset_index()
    )
    gap_summary.columns = ['_'.join(c).strip('_') for c in gap_summary.columns]
    gap_summary.to_csv(out_dir / 'table_gap_summary.csv', index=False)

    feasibility_summary = (
        df.groupby(['method', 'N'])['feasible_flag']
        .mean()
        .reset_index(name='feasible_rate')
    )
    feasibility_summary.to_csv(out_dir / 'table_feasibility_rate.csv', index=False)

if scal_path.exists():
    ds = clean_inf(pd.read_csv(scal_path))
    ds.to_csv(out_dir / 'table_scalability_raw.csv', index=False)

insight = (
    combined[(combined['feasible_flag'] == 1) & (combined['method'].isin(['ortools_main', 'pyvrp_baseline']))]
    .groupby(['method', 'B', 'Delta_min'])[['on_time_pct', 'total_tardiness_min', 'risk_mean']]
    .mean()
    .reset_index()
)
insight = clean_inf(insight)
insight.to_csv(out_dir / 'table_managerial_insight_support.csv', index=False)
PY
