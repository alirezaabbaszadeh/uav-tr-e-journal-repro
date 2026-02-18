from __future__ import annotations

from typing import Dict

import numpy as np

from .comms import edge_outage_risk
from .data_types import EdgeData, ScenarioData


def compute_edge_data(
    scenario: ScenarioData,
    lambda_out: float,
    comm_params: Dict,
    energy_params: Dict,
    cost_scale: float,
    risk_scale: float,
    k_samples: int,
) -> EdgeData:
    coords = np.vstack([scenario.depot_xy, scenario.client_xy])
    n = coords.shape[0]

    distance = np.zeros((n, n), dtype=float)
    travel = np.zeros((n, n), dtype=float)
    risk = np.zeros((n, n), dtype=float)

    for i in range(n):
        for j in range(i + 1, n):
            dist = float(np.linalg.norm(coords[i] - coords[j]))
            distance[i, j] = distance[j, i] = dist
            travel_t = dist / scenario.speed_mps
            travel[i, j] = travel[j, i] = travel_t

            r = edge_outage_risk(
                coords[i],
                coords[j],
                scenario.bs_xy,
                scenario.altitude_m,
                k_samples,
                comm_params,
            )
            risk[i, j] = risk[j, i] = r

    energy = energy_params["e_per_m"] * distance
    cost = energy + lambda_out * risk * risk_scale

    return EdgeData(
        distance_m=distance,
        travel_time_s=travel,
        risk=risk,
        energy=energy,
        cost=cost * cost_scale,
    )
