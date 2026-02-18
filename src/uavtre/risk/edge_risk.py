from __future__ import annotations

import numpy as np

from ..io.schema import ScenarioData
from .radio_model import edge_outage_risk


def compute_risk_matrix(
    scenario: ScenarioData,
    comm_params: dict,
    edge_samples: int,
) -> np.ndarray:
    coords = np.vstack([scenario.depot_xy, scenario.client_xy])
    n_nodes = coords.shape[0]
    risk = np.zeros((n_nodes, n_nodes), dtype=float)

    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            r = edge_outage_risk(
                p1=coords[i],
                p2=coords[j],
                bs_xy=scenario.bs_xy,
                altitude_m=scenario.altitude_m,
                k_samples=edge_samples,
                comm_params=comm_params,
            )
            risk[i, j] = r
            risk[j, i] = r

    return risk
