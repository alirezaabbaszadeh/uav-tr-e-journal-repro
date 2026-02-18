from __future__ import annotations

from uavtre.io.schema import (
    RESULTS_MAIN_COLUMNS,
    RESULTS_ROUTES_COLUMNS,
    RESULTS_SIGNIFICANCE_COLUMNS,
)


def test_main_columns_required() -> None:
    required = {
        "run_id",
        "method",
        "N",
        "M",
        "Delta_min",
        "B",
        "K",
        "lambda_out",
        "lambda_tw",
        "tw_family",
        "on_time_pct",
        "total_tardiness_min",
        "total_energy",
        "risk_mean",
        "risk_max_route",
        "runtime_edge_s",
        "runtime_solve_s",
        "runtime_total_s",
        "incumbent_obj",
        "best_bound",
        "gap_pct",
        "feasible_flag",
    }
    assert required.issubset(set(RESULTS_MAIN_COLUMNS))


def test_routes_columns_required() -> None:
    required = {
        "run_id",
        "uav_id",
        "route_node_sequence",
        "route_energy",
        "route_risk_mean",
        "route_tardiness_min",
        "route_time_s",
    }
    assert required == set(RESULTS_ROUTES_COLUMNS)


def test_significance_columns_required() -> None:
    required = {
        "comparison_id",
        "method_a",
        "method_b",
        "metric",
        "test_name",
        "p_value",
        "p_value_adj",
        "correction_method",
        "effect_direction",
        "effect_size",
        "ci_low",
        "ci_high",
        "n_pairs",
        "significant_flag",
    }
    assert required == set(RESULTS_SIGNIFICANCE_COLUMNS)
