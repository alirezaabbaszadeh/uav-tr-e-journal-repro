from __future__ import annotations

from typing import Dict, List

import numpy as np

from .data_types import EdgeData, ScenarioData


def evaluate_routes(
    scenario: ScenarioData,
    edge: EdgeData,
    routes: List[List[int]],
) -> Dict[str, float]:
    n_clients = scenario.client_xy.shape[0]
    on_time = 0
    total_tardiness = 0.0
    total_energy = 0.0
    total_risk = 0.0
    total_distance = 0.0

    for route in routes:
        if not route:
            continue
        current = 0  # depot
        t = 0.0
        for idx in route:
            node = idx + 1
            t += edge.travel_time_s[current, node]
            start = max(t, scenario.tw_early_s[idx])
            tard = max(0.0, start - scenario.tw_late_s[idx])
            total_tardiness += tard
            if start <= scenario.tw_late_s[idx]:
                on_time += 1
            t = start + scenario.service_duration_s[idx]

            total_energy += edge.energy[current, node]
            total_risk += edge.risk[current, node]
            total_distance += edge.distance_m[current, node]
            current = node

        # return to depot
        total_energy += edge.energy[current, 0]
        total_risk += edge.risk[current, 0]
        total_distance += edge.distance_m[current, 0]

    on_time_rate = on_time / max(1, n_clients)
    return {
        "on_time_rate": on_time_rate,
        "total_tardiness_s": total_tardiness,
        "total_energy": total_energy,
        "total_risk": total_risk,
        "total_distance_m": total_distance,
    }
