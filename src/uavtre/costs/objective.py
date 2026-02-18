from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from ..io.schema import CostSpec, EdgeData, ScenarioData


@dataclass
class EvaluatedRoutes:
    feasible: bool
    on_time_pct: float
    total_tardiness_min: float
    total_energy: float
    risk_mean: float
    risk_max_route: float
    incumbent_obj: float
    route_rows: List[dict]


def build_edge_data(
    distance_m: np.ndarray,
    travel_time_s: np.ndarray,
    risk: np.ndarray,
    cost_spec: CostSpec,
) -> EdgeData:
    energy = cost_spec.energy_per_m * distance_m
    # Arc-level objective term: energy + communication-risk contribution.
    cost = cost_spec.cost_scale * (
        energy + cost_spec.lambda_out * cost_spec.risk_scale * risk
    )
    return EdgeData(
        distance_m=distance_m,
        travel_time_s=travel_time_s,
        risk=risk,
        energy=energy,
        cost=cost,
    )


def evaluate_routes(
    scenario: ScenarioData,
    edge: EdgeData,
    routes: List[List[int]],
    cost_spec: CostSpec,
    run_id: str,
) -> EvaluatedRoutes:
    n_clients = len(scenario.client_xy)
    visited = set()

    on_time = 0
    total_tardiness_s = 0.0
    total_energy = 0.0
    total_risk_sum = 0.0
    total_arc_count = 0
    risk_max_route = 0.0

    route_rows: List[dict] = []

    for uav_id, route in enumerate(routes):
        if not route:
            route_rows.append(
                {
                    "run_id": run_id,
                    "uav_id": uav_id,
                    "route_node_sequence": "0->0",
                    "route_energy": 0.0,
                    "route_risk_mean": 0.0,
                    "route_tardiness_min": 0.0,
                    "route_time_s": 0.0,
                }
            )
            continue

        current = 0
        time_s = 0.0
        route_energy = 0.0
        route_risk_sum = 0.0
        route_arc_count = 0
        route_tardiness_s = 0.0

        path_nodes = [0]

        for client_idx in route:
            visited.add(int(client_idx))
            node = client_idx + 1

            time_s += edge.travel_time_s[current, node]
            service_start_s = max(time_s, scenario.tw_early_s[client_idx])
            tardiness_s = max(0.0, service_start_s - scenario.tw_late_s[client_idx])
            route_tardiness_s += tardiness_s
            total_tardiness_s += tardiness_s
            if tardiness_s <= 1e-9:
                on_time += 1

            time_s = service_start_s + scenario.service_duration_s[client_idx]

            route_energy += edge.energy[current, node]
            route_risk_sum += edge.risk[current, node]
            route_arc_count += 1

            total_energy += edge.energy[current, node]
            total_risk_sum += edge.risk[current, node]
            total_arc_count += 1

            current = node
            path_nodes.append(node)

        route_energy += edge.energy[current, 0]
        route_risk_sum += edge.risk[current, 0]
        route_arc_count += 1

        total_energy += edge.energy[current, 0]
        total_risk_sum += edge.risk[current, 0]
        total_arc_count += 1

        path_nodes.append(0)

        route_risk_mean = route_risk_sum / max(1, route_arc_count)
        risk_max_route = max(risk_max_route, route_risk_mean)

        route_rows.append(
            {
                "run_id": run_id,
                "uav_id": uav_id,
                "route_node_sequence": "->".join(str(v) for v in path_nodes),
                "route_energy": route_energy,
                "route_risk_mean": route_risk_mean,
                "route_tardiness_min": route_tardiness_s / 60.0,
                "route_time_s": time_s,
            }
        )

    feasible = len(visited) == n_clients
    on_time_pct = 100.0 * on_time / max(1, n_clients)
    total_tardiness_min = total_tardiness_s / 60.0
    risk_mean = total_risk_sum / max(1, total_arc_count)

    # Keep the objective consistent with arc-level solver costs.
    incumbent_obj = cost_spec.cost_scale * (
        total_energy
        + cost_spec.lambda_out * cost_spec.risk_scale * total_risk_sum
        + cost_spec.lambda_tw * total_tardiness_min
    )

    if not feasible:
        on_time_pct = float("nan")
        total_tardiness_min = float("nan")
        total_energy = float("nan")
        risk_mean = float("nan")
        risk_max_route = float("nan")
        incumbent_obj = float("nan")

    return EvaluatedRoutes(
        feasible=feasible,
        on_time_pct=on_time_pct,
        total_tardiness_min=total_tardiness_min,
        total_energy=total_energy,
        risk_mean=risk_mean,
        risk_max_route=risk_max_route,
        incumbent_obj=incumbent_obj,
        route_rows=route_rows,
    )
