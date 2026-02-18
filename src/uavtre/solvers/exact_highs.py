from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from ..io.schema import EdgeData, ScenarioData, SolverOutput

try:
    from highspy import Highs
except ImportError:  # pragma: no cover
    Highs = None


def _status_is_optimal(status: str) -> bool:
    s = status.lower()
    return "optimal" in s and "not" not in s


def _safe_finite(value: float | None) -> float | None:
    if value is None:
        return None
    if not np.isfinite(value):
        return None
    return float(value)


def _extract_routes(
    col_value: np.ndarray,
    x_index: Dict[Tuple[int, int, int], int],
    n_nodes: int,
    num_uavs: int,
) -> List[List[int]]:
    routes: List[List[int]] = []

    for k in range(num_uavs):
        succ: Dict[int, int] = {}
        for i in range(n_nodes):
            best_j = None
            best_val = 0.0
            for j in range(n_nodes):
                if i == j:
                    continue
                idx = x_index[(i, j, k)]
                val = float(col_value[idx]) if idx < len(col_value) else 0.0
                if val > best_val:
                    best_val = val
                    best_j = j
            if best_j is not None and best_val > 0.5:
                succ[i] = best_j

        route: List[int] = []
        cur = 0
        seen = {0}
        for _ in range(n_nodes + 5):
            nxt = succ.get(cur)
            if nxt is None or nxt == 0:
                break
            if nxt in seen:
                break
            route.append(int(nxt - 1))
            seen.add(nxt)
            cur = nxt

        routes.append(route)

    return routes


def solve_with_highs(
    scenario: ScenarioData,
    edge: EdgeData,
    num_uavs: int,
    weight_scale: float,
    time_limit_s: float,
    tw_mode: str,
    tardiness_cost_per_sec: float = 0.0,
    strict_gap: float = 0.0,
) -> SolverOutput:
    if Highs is None:
        raise RuntimeError("HiGHS is not installed. Install `highspy` to use this solver.")

    n_clients = scenario.client_xy.shape[0]
    n_nodes = n_clients + 1

    delivery = np.round(scenario.delivery * weight_scale).astype(int)
    pickup = np.round(scenario.pickup * weight_scale).astype(int)
    capacity = int(round(scenario.capacity_kg * weight_scale))

    tw_early = np.round(scenario.tw_early_s).astype(int)
    tw_late = np.round(scenario.tw_late_s).astype(int)
    service = np.round(scenario.service_duration_s).astype(int)
    travel = np.round(edge.travel_time_s).astype(int)
    cost = np.round(edge.cost).astype(float)

    max_travel = int(np.max(travel)) if n_nodes > 1 else 0
    max_service = int(np.max(service)) if n_clients > 0 else 0
    m_time = max(1, (max_travel + max_service) * (n_nodes + 1))
    m_load = capacity + int(np.max(delivery) + np.max(pickup) + 1) if n_clients else capacity + 1

    highs = Highs()
    highs.setOptionValue("time_limit", float(time_limit_s))
    highs.setOptionValue("mip_rel_gap", float(strict_gap))
    highs.setOptionValue("presolve", "on")

    empty_idx = np.array([], dtype=np.int32)
    empty_val = np.array([], dtype=np.float64)

    def add_cont(obj: float, lb: float, ub: float) -> int:
        col = highs.getNumCol()
        highs.addCol(obj, lb, ub, 0, empty_idx, empty_val)
        return col

    def add_bin(obj: float = 0.0) -> int:
        return int(highs.addBinary(obj=obj))

    def add_row(lhs: float, rhs: float, terms: List[tuple[int, float]]) -> None:
        idx = np.array([var for var, _ in terms], dtype=np.int32)
        val = np.array([coef for _, coef in terms], dtype=np.float64)
        highs.addRow(lhs, rhs, len(idx), idx, val)

    x: Dict[Tuple[int, int, int], int] = {}
    y: Dict[Tuple[int, int], int] = {}
    t: Dict[Tuple[int, int], int] = {}
    l: Dict[Tuple[int, int], int] = {}
    z: Dict[Tuple[int, int], int] = {}
    u: Dict[int, int] = {}

    tw_mode = tw_mode.lower()
    soft_tw = tw_mode != "hard"
    tardiness_obj = float(max(0.0, tardiness_cost_per_sec))

    for k in range(num_uavs):
        u[k] = add_bin(0.0)

    for i in range(1, n_nodes):
        for k in range(num_uavs):
            y[(i, k)] = add_bin(0.0)

    for i in range(n_nodes):
        for k in range(num_uavs):
            t[(i, k)] = add_cont(0.0, 0.0, 0.0 if i == 0 else float(m_time))
            l[(i, k)] = add_cont(0.0, 0.0, float(capacity))
            if i > 0 and soft_tw:
                z[(i, k)] = add_cont(tardiness_obj, 0.0, float(m_time))

    for i in range(n_nodes):
        for j in range(n_nodes):
            if i == j:
                continue
            for k in range(num_uavs):
                x[(i, j, k)] = add_bin(obj=float(cost[i, j]))

    # Each client must be visited exactly once.
    for i in range(1, n_nodes):
        add_row(1.0, 1.0, [(y[(i, k)], 1.0) for k in range(num_uavs)])

    # Depot flow equals activation variable.
    for k in range(num_uavs):
        terms_out = [(x[(0, j, k)], 1.0) for j in range(1, n_nodes)] + [(u[k], -1.0)]
        terms_in = [(x[(i, 0, k)], 1.0) for i in range(1, n_nodes)] + [(u[k], -1.0)]
        add_row(0.0, 0.0, terms_out)
        add_row(0.0, 0.0, terms_in)

    # Client flow conservation.
    for i in range(1, n_nodes):
        for k in range(num_uavs):
            terms_out = [(x[(i, j, k)], 1.0) for j in range(n_nodes) if j != i] + [
                (y[(i, k)], -1.0)
            ]
            terms_in = [(x[(j, i, k)], 1.0) for j in range(n_nodes) if j != i] + [
                (y[(i, k)], -1.0)
            ]
            add_row(0.0, 0.0, terms_out)
            add_row(0.0, 0.0, terms_in)

    # Time-window logic (hard or soft) + time propagation.
    for i in range(1, n_nodes):
        a_i = float(tw_early[i - 1])
        b_i = float(tw_late[i - 1])
        for k in range(num_uavs):
            add_row(a_i - m_time, 1e12, [(t[(i, k)], 1.0), (y[(i, k)], -m_time)])
            if soft_tw:
                add_row(
                    -1e12,
                    b_i + m_time,
                    [(t[(i, k)], 1.0), (z[(i, k)], -1.0), (y[(i, k)], m_time)],
                )
            else:
                add_row(-1e12, b_i + m_time, [(t[(i, k)], 1.0), (y[(i, k)], m_time)])

    for i in range(n_nodes):
        for j in range(1, n_nodes):
            if i == j:
                continue
            for k in range(num_uavs):
                s_i = 0 if i == 0 else int(service[i - 1])
                tij = int(travel[i, j])
                lhs = float(s_i + tij - m_time)
                add_row(
                    lhs,
                    1e12,
                    [(t[(j, k)], 1.0), (t[(i, k)], -1.0), (x[(i, j, k)], -m_time)],
                )

    # Capacity linking and propagation.
    for k in range(num_uavs):
        terms = [(l[(0, k)], 1.0)] + [
            (y[(i, k)], -float(delivery[i - 1])) for i in range(1, n_nodes)
        ]
        add_row(0.0, 0.0, terms)

    for i in range(1, n_nodes):
        for k in range(num_uavs):
            add_row(-1e12, 0.0, [(l[(i, k)], 1.0), (y[(i, k)], -capacity)])

    for i in range(n_nodes):
        for j in range(1, n_nodes):
            if i == j:
                continue
            dj = int(delivery[j - 1])
            pj = int(pickup[j - 1])
            for k in range(num_uavs):
                add_row(
                    -m_load - dj + pj,
                    1e12,
                    [(l[(j, k)], 1.0), (l[(i, k)], -1.0), (x[(i, j, k)], -m_load)],
                )
                add_row(
                    -1e12,
                    m_load - dj + pj,
                    [(l[(j, k)], 1.0), (l[(i, k)], -1.0), (x[(i, j, k)], m_load)],
                )

    highs.run()
    info = highs.getInfo()
    status = highs.modelStatusToString(highs.getModelStatus())

    objective = _safe_finite(float(info.objective_function_value) if info.valid else None)
    bound = _safe_finite(float(info.mip_dual_bound) if info.valid else None)

    gap_pct = None
    if objective is not None and bound is not None and abs(objective) > 1e-9:
        gap_pct = max(0.0, 100.0 * (objective - bound) / abs(objective))

    solution = highs.getSolution()
    col_value = np.array(solution.col_value if solution is not None else [], dtype=float)
    routes = _extract_routes(col_value, x, n_nodes, num_uavs)

    return SolverOutput(
        method="highs",
        status=status,
        objective=objective,
        bound=bound,
        gap_pct=gap_pct,
        runtime_s=float(highs.getRunTime()),
        routes=routes,
        metadata={
            "engine": "highs",
            "tw_mode": tw_mode,
            "soft_tw": int(soft_tw),
            "is_optimal": int(_status_is_optimal(status)),
        },
    )
