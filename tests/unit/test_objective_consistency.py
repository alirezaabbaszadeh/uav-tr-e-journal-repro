from __future__ import annotations

import numpy as np

from uavtre.costs.objective import evaluate_routes
from uavtre.io.schema import CostSpec, EdgeData, ScenarioData


def test_evaluated_objective_matches_arc_space_definition() -> None:
    scenario = ScenarioData(
        depot_xy=np.array([0.0, 0.0]),
        client_xy=np.array([[1.0, 0.0]]),
        delivery=np.array([1.0]),
        pickup=np.array([0.0]),
        service_duration_s=np.array([0.0]),
        tw_early_s=np.array([0.0]),
        tw_late_s=np.array([0.0]),
        bs_xy=np.array([[0.0, 0.0]]),
        speed_mps=1.0,
        capacity_kg=2.0,
        altitude_m=100.0,
    )

    edge = EdgeData(
        distance_m=np.array([[0.0, 2.0], [2.0, 0.0]]),
        travel_time_s=np.array([[0.0, 120.0], [120.0, 0.0]]),
        risk=np.array([[0.0, 0.5], [0.25, 0.0]]),
        energy=np.array([[0.0, 2.0], [2.0, 0.0]]),
        cost=np.array([[0.0, 0.0], [0.0, 0.0]]),
    )

    cost_spec = CostSpec(
        energy_per_m=1.0,
        risk_scale=10.0,
        cost_scale=100.0,
        lambda_out=2.0,
        lambda_tw=3.0,
    )

    evaluated = evaluate_routes(scenario, edge, routes=[[0]], cost_spec=cost_spec, run_id="x")

    total_energy = 4.0
    total_risk_sum = 0.75
    total_tardiness_min = 2.0
    expected = 100.0 * (total_energy + 2.0 * 10.0 * total_risk_sum + 3.0 * total_tardiness_min)

    assert abs(evaluated.incumbent_obj - expected) < 1e-9
