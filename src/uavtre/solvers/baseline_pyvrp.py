from __future__ import annotations

from typing import List

import numpy as np

from ..io.schema import EdgeData, ScenarioData, SolverOutput

try:
    from pyvrp import Model
    from pyvrp.stop import MaxIterations, MaxRuntime
except ImportError:  # pragma: no cover
    Model = None
    MaxIterations = None
    MaxRuntime = None


def solve_with_pyvrp(
    scenario: ScenarioData,
    edge: EdgeData,
    num_uavs: int,
    weight_scale: float,
    seed: int,
    max_iterations: int,
    max_runtime_s: float,
) -> SolverOutput:
    if Model is None:
        raise RuntimeError("PyVRP is not installed. Install `pyvrp` to use this solver.")

    model = Model()
    depot = model.add_depot(float(scenario.depot_xy[0]), float(scenario.depot_xy[1]))
    model.add_vehicle_type(
        num_available=int(num_uavs),
        capacity=int(round(scenario.capacity_kg * weight_scale)),
        unit_distance_cost=1,
        unit_duration_cost=0,
    )

    clients = []
    for i in range(len(scenario.client_xy)):
        client = model.add_client(
            float(scenario.client_xy[i, 0]),
            float(scenario.client_xy[i, 1]),
            delivery=int(round(scenario.delivery[i] * weight_scale)),
            pickup=int(round(scenario.pickup[i] * weight_scale)),
            service_duration=int(round(scenario.service_duration_s[i])),
            tw_early=int(round(scenario.tw_early_s[i])),
            tw_late=int(round(scenario.tw_late_s[i])),
        )
        clients.append(client)

    nodes = [depot] + clients
    cost = np.round(edge.cost).astype(int)
    duration = np.round(edge.travel_time_s).astype(int)

    for i in range(len(nodes)):
        for j in range(len(nodes)):
            if i == j:
                continue
            model.add_edge(
                nodes[i],
                nodes[j],
                distance=int(cost[i, j]),
                duration=int(duration[i, j]),
            )

    stop = MaxIterations(int(max_iterations))
    if max_runtime_s > 0:
        stop = MaxRuntime(float(max_runtime_s))

    result = model.solve(stop, seed=seed, display=False)

    routes: List[List[int]] = []
    for route in result.best.routes():
        visits = route.visits()
        routes.append([v - 1 for v in visits])

    return SolverOutput(
        method="pyvrp",
        status="feasible" if result.is_feasible() else "infeasible",
        objective=float(result.cost()),
        bound=None,
        gap_pct=None,
        runtime_s=float(result.runtime),
        routes=routes,
        metadata={"engine": "pyvrp"},
    )
