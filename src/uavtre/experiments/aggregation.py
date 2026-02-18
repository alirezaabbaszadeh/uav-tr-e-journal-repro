from __future__ import annotations

import pandas as pd


def aggregate_main_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    group_cols = [
        "method",
        "N",
        "Delta_min",
        "B",
        "K",
        "lambda_out",
        "lambda_tw",
        "tw_family",
        "profile",
    ]
    metrics = [
        "on_time_pct",
        "total_tardiness_min",
        "total_energy",
        "risk_mean",
        "risk_max_route",
        "runtime_total_s",
        "gap_pct",
    ]

    agg = df.groupby(group_cols, dropna=False)[metrics].agg(["mean", "std"]).reset_index()
    agg.columns = ["_".join(c).strip("_") for c in agg.columns.values]
    return agg
