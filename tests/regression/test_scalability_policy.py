from __future__ import annotations

from uavtre.experiments.runner import _claim_regime
from uavtre.io.schema import RunResult


def test_n80_claim_regime_is_scalability_only() -> None:
    assert _claim_regime(80, 80) == "scalability_only"
    assert _claim_regime(120, 80) == "scalability_only"


def test_scalability_rows_keep_bound_gap_missing() -> None:
    row = RunResult(
        run_id="x",
        profile="scalability",
        git_sha="abc",
        env_hash="env",
        timestamp="2026-02-15T00:00:00+00:00",
        seed=1,
        method="ortools_main",
        N=80,
        M=3,
        Delta_min=10,
        B=4,
        K=10,
        lambda_out=0.5,
        lambda_tw=1.0,
        tw_family="A",
        tw_mode="soft",
        on_time_pct=None,
        total_tardiness_min=None,
        total_energy=None,
        risk_mean=None,
        risk_max_route=None,
        runtime_edge_s=1.0,
        runtime_solve_s=2.0,
        runtime_total_s=3.0,
        incumbent_obj=None,
        best_bound=None,
        gap_pct=None,
        feasible_flag=0,
        claim_regime="scalability_only",
    ).to_row()

    assert row["claim_regime"] == "scalability_only"
    assert row["best_bound"] is None
    assert row["gap_pct"] is None
