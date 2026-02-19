from __future__ import annotations

import pandas as pd

from uavtre.experiments.significance import compute_significance_results


def test_significance_outputs_adjusted_pvalues_and_effect_size() -> None:
    rows = []
    for seed in [1, 2, 3, 4, 5]:
        common = {
            "seed": seed,
            "N": 10,
            "M": 3,
            "Delta_min": 10,
            "B": 4,
            "K": 10,
            "lambda_out": 0.5,
            "lambda_tw": 1.0,
            "tw_family": "A",
            "tw_mode": "soft",
            "profile": "quick",
            "runtime_total_s": 1.0 + seed,
            "on_time_pct": 80.0 + seed,
            "total_tardiness_min": 5.0,
            "total_energy": 1000.0,
            "risk_mean": 0.1,
        }
        rows.append({**common, "method": "a"})
        rows.append({**common, "method": "b", "on_time_pct": 70.0 + seed})

    df = pd.DataFrame(rows)
    out = compute_significance_results(df)
    assert out
    first = out[0]

    if first.comparison_id == "scipy_missing":
        assert first.test_name == "wilcoxon_signed_rank"
        assert first.method_a == "NA"
        assert first.method_b == "NA"
        return

    assert first.p_value is not None
    assert first.p_value_adj is not None
    assert first.effect_size is not None
    assert first.n_pairs > 0
    assert first.correction_method == "holm-bonferroni"
