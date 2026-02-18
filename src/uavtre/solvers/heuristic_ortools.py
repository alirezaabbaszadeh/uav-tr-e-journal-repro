from __future__ import annotations

from typing import Dict, List

import numpy as np

from ..io.schema import EdgeData, ScenarioData, SolverOutput

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
except ImportError:  # pragma: no cover
    pywrapcp = None
    routing_enums_pb2 = None


def _enum_value(enum_obj, name: str, default_name: str) -> int:
    if hasattr(enum_obj, name):
        return int(getattr(enum_obj, name))
    return int(getattr(enum_obj, default_name))


def solve_with_ortools(
    scenario: ScenarioData,
    edge: EdgeData,
    cfg_solver: Dict[str, float | str],
    seed: int,
    tw_mode: str,
    lambda_tw: float,
    weight_scale: float,
    time_limit_s: float,
) -> SolverOutput:
    if pywrapcp is None or routing_enums_pb2 is None:
        raise RuntimeError("OR-Tools is not installed. Install `ortools` to use this solver.")

    n_clients = len(scenario.client_xy)
    n_nodes = n_clients + 1
    num_vehicles = max(1, int(cfg_solver.get("num_uavs", 1)))

    manager = pywrapcp.RoutingIndexManager(n_nodes, num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    cost = np.round(edge.cost).astype(int)
    travel = np.round(edge.travel_time_s).astype(int)
    service = np.round(scenario.service_duration_s).astype(int)

    delivery = np.round(scenario.delivery * weight_scale).astype(int)
    pickup = np.round(scenario.pickup * weight_scale).astype(int)
    capacity = int(round(float(scenario.capacity_kg) * float(weight_scale)))

    def arc_cost_cb(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        return int(cost[i, j])

    arc_idx = routing.RegisterTransitCallback(arc_cost_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(arc_idx)

    def time_cb(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        service_i = 0 if i == 0 else int(service[i - 1])
        return int(travel[i, j] + service_i)

    time_idx = routing.RegisterTransitCallback(time_cb)
    horizon = int(max(1e6, np.max(travel) * (n_nodes + 2)))
    routing.AddDimension(
        time_idx,
        horizon,
        horizon,
        False,
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    def net_load_cb(from_index: int) -> int:
        node = manager.IndexToNode(from_index)
        if node == 0:
            return 0
        i = node - 1
        return int(pickup[i] - delivery[i])

    load_idx = routing.RegisterUnaryTransitCallback(net_load_cb)
    routing.AddDimensionWithVehicleCapacity(
        load_idx,
        0,
        [capacity] * num_vehicles,
        False,
        "NetLoad",
    )
    load_dim = routing.GetDimensionOrDie("NetLoad")

    cost_scale = float(cfg_solver.get("cost_scale", 1000.0))
    tardiness_penalty_per_sec = max(0.0, cost_scale * float(lambda_tw) / 60.0)
    tardiness_penalty = int(round(tardiness_penalty_per_sec))

    drop_penalty = int(max(np.max(cost) * 10, 1_000_000))
    tw_mode = tw_mode.lower()
    for client in range(1, n_nodes):
        idx = manager.NodeToIndex(client)
        routing.AddDisjunction([idx], drop_penalty)

        early = int(round(scenario.tw_early_s[client - 1]))
        late = int(round(scenario.tw_late_s[client - 1]))

        if tw_mode == "hard":
            time_dim.CumulVar(idx).SetRange(early, late)
        else:
            time_dim.CumulVar(idx).SetMin(early)
            if tardiness_penalty > 0:
                time_dim.SetCumulVarSoftUpperBound(idx, late, tardiness_penalty)

    for vehicle_id in range(num_vehicles):
        start_idx = routing.Start(vehicle_id)
        end_idx = routing.End(vehicle_id)

        time_dim.CumulVar(start_idx).SetRange(0, horizon)
        time_dim.CumulVar(end_idx).SetRange(0, horizon)

        load_dim.CumulVar(start_idx).SetRange(0, capacity)
        load_dim.CumulVar(end_idx).SetRange(0, capacity)

    params = pywrapcp.DefaultRoutingSearchParameters()
    first_solution_name = str(cfg_solver.get("ortools_first_solution", "PATH_CHEAPEST_ARC"))
    meta_name = str(cfg_solver.get("ortools_metaheuristic", "GUIDED_LOCAL_SEARCH"))

    params.first_solution_strategy = _enum_value(
        routing_enums_pb2.FirstSolutionStrategy,
        first_solution_name,
        "PATH_CHEAPEST_ARC",
    )
    params.local_search_metaheuristic = _enum_value(
        routing_enums_pb2.LocalSearchMetaheuristic,
        meta_name,
        "GUIDED_LOCAL_SEARCH",
    )
    params.time_limit.seconds = max(1, int(time_limit_s))
    params.log_search = False
    if hasattr(params, "random_seed"):
        params.random_seed = int(seed)

    assignment = routing.SolveWithParameters(params)
    if assignment is None:
        params.first_solution_strategy = _enum_value(
            routing_enums_pb2.FirstSolutionStrategy,
            "AUTOMATIC",
            "PATH_CHEAPEST_ARC",
        )
        assignment = routing.SolveWithParameters(params)

    if assignment is None:
        return SolverOutput(
            method="ortools",
            status="infeasible",
            objective=None,
            bound=None,
            gap_pct=None,
            runtime_s=float(time_limit_s),
            routes=[],
            metadata={"engine": "ortools"},
        )

    routes: List[List[int]] = []
    for vehicle_id in range(num_vehicles):
        route: List[int] = []
        idx = routing.Start(vehicle_id)
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node != 0:
                route.append(node - 1)
            idx = assignment.Value(routing.NextVar(idx))
        routes.append(route)

    return SolverOutput(
        method="ortools",
        status="feasible",
        objective=float(assignment.ObjectiveValue()),
        bound=None,
        gap_pct=None,
        runtime_s=float(time_limit_s),
        routes=routes,
        metadata={
            "engine": "ortools",
            "capacity_model": "net_load",
            "tardiness_penalty_per_sec": tardiness_penalty,
        },
    )
