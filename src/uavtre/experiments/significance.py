from __future__ import annotations

from itertools import combinations
from typing import List

import numpy as np
import pandas as pd

from ..io.schema import SignificanceResult

try:
    from scipy.stats import wilcoxon
except ImportError:  # pragma: no cover
    wilcoxon = None


DEFAULT_METRICS = [
    "on_time_pct",
    "total_tardiness_min",
    "total_energy",
    "risk_mean",
    "runtime_total_s",
]

MAXIMIZE_METRICS = {"on_time_pct"}


def _rank_biserial(diff: np.ndarray) -> float:
    pos = int(np.sum(diff > 0.0))
    neg = int(np.sum(diff < 0.0))
    denom = pos + neg
    if denom == 0:
        return 0.0
    return float((pos - neg) / denom)


def _bootstrap_median_ci(diff: np.ndarray, alpha: float = 0.05) -> tuple[float | None, float | None]:
    n = len(diff)
    if n < 2:
        return None, None

    rng = np.random.default_rng(20260217)
    boots = np.empty(1000, dtype=float)
    for i in range(boots.size):
        sample = rng.choice(diff, size=n, replace=True)
        boots[i] = float(np.median(sample))

    low = float(np.quantile(boots, alpha / 2.0))
    high = float(np.quantile(boots, 1.0 - alpha / 2.0))
    return low, high


def _holm_adjust(p_values: List[float | None]) -> List[float | None]:
    adjusted: List[float | None] = [None] * len(p_values)

    valid = [(idx, float(p)) for idx, p in enumerate(p_values) if p is not None]
    if not valid:
        return adjusted

    valid.sort(key=lambda x: x[1])
    m = len(valid)
    prev = 0.0
    for rank, (idx, p) in enumerate(valid):
        val = (m - rank) * p
        val = max(val, prev)
        val = min(1.0, val)
        adjusted[idx] = val
        prev = val

    return adjusted


def compute_significance_results(
    results_main: pd.DataFrame,
    metrics: List[str] | None = None,
) -> List[SignificanceResult]:
    if metrics is None:
        metrics = DEFAULT_METRICS

    if results_main.empty:
        return []

    if wilcoxon is None:
        return [
            SignificanceResult(
                comparison_id="scipy_missing",
                method_a="NA",
                method_b="NA",
                metric="NA",
                test_name="wilcoxon_signed_rank",
                p_value=None,
                p_value_adj=None,
                correction_method="none",
                effect_direction="unknown",
                effect_size=None,
                ci_low=None,
                ci_high=None,
                n_pairs=0,
                significant_flag=0,
            )
        ]

    key_cols = [
        "seed",
        "N",
        "M",
        "Delta_min",
        "B",
        "K",
        "lambda_out",
        "lambda_tw",
        "tw_family",
        "tw_mode",
        "profile",
    ]

    methods = sorted(results_main["method"].dropna().unique().tolist())
    out: List[SignificanceResult] = []
    raw_p_values: List[float | None] = []

    for method_a, method_b in combinations(methods, 2):
        dfa = results_main[results_main["method"] == method_a]
        dfb = results_main[results_main["method"] == method_b]

        merged = dfa.merge(
            dfb,
            on=key_cols,
            suffixes=("_a", "_b"),
            how="inner",
        )
        if merged.empty:
            continue

        for metric in metrics:
            col_a = f"{metric}_a"
            col_b = f"{metric}_b"
            if col_a not in merged.columns or col_b not in merged.columns:
                continue

            paired = merged[[col_a, col_b]].dropna()
            if paired.empty:
                continue

            diff = paired[col_a].to_numpy(dtype=float) - paired[col_b].to_numpy(dtype=float)
            n_pairs = int(diff.size)

            if np.allclose(diff, 0.0):
                p_value = 1.0
            else:
                try:
                    stat = wilcoxon(diff, zero_method="wilcox", alternative="two-sided")
                    p_value = float(stat.pvalue)
                except ValueError:
                    p_value = None

            median_diff = float(np.median(diff))
            if abs(median_diff) <= 1e-12:
                effect_direction = "tie"
            elif metric in MAXIMIZE_METRICS:
                effect_direction = "a_better" if median_diff > 0 else "b_better"
            else:
                effect_direction = "a_better" if median_diff < 0 else "b_better"

            effect_size = _rank_biserial(diff)
            ci_low, ci_high = _bootstrap_median_ci(diff)

            out.append(
                SignificanceResult(
                    comparison_id=f"{method_a}_vs_{method_b}_{metric}",
                    method_a=method_a,
                    method_b=method_b,
                    metric=metric,
                    test_name="wilcoxon_signed_rank",
                    p_value=p_value,
                    p_value_adj=None,
                    correction_method="holm-bonferroni",
                    effect_direction=effect_direction,
                    effect_size=effect_size,
                    ci_low=ci_low,
                    ci_high=ci_high,
                    n_pairs=n_pairs,
                    significant_flag=0,
                )
            )
            raw_p_values.append(p_value)

    if not out:
        return []

    adjusted = _holm_adjust(raw_p_values)
    for i, row in enumerate(out):
        row.p_value_adj = adjusted[i]
        row.significant_flag = int(row.p_value_adj is not None and row.p_value_adj < 0.05)

    return out
