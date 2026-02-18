from __future__ import annotations

import numpy as np

from ..io.schema import ScenarioData


def compute_distance_and_time_matrices(
    scenario: ScenarioData,
) -> tuple[np.ndarray, np.ndarray]:
    coords = np.vstack([scenario.depot_xy, scenario.client_xy])
    n_nodes = coords.shape[0]

    distance = np.zeros((n_nodes, n_nodes), dtype=float)
    travel_time = np.zeros((n_nodes, n_nodes), dtype=float)

    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            dist = float(np.linalg.norm(coords[i] - coords[j]))
            distance[i, j] = dist
            distance[j, i] = dist
            t = dist / max(1e-9, scenario.speed_mps)
            travel_time[i, j] = t
            travel_time[j, i] = t

    return distance, travel_time
