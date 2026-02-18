from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


RESULTS_MAIN_COLUMNS = [
    "run_id",
    "profile",
    "git_sha",
    "env_hash",
    "timestamp",
    "seed",
    "method",
    "N",
    "M",
    "Delta_min",
    "B",
    "K",
    "lambda_out",
    "lambda_tw",
    "tw_family",
    "tw_mode",
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
    "claim_regime",
]

RESULTS_ROUTES_COLUMNS = [
    "run_id",
    "uav_id",
    "route_node_sequence",
    "route_energy",
    "route_risk_mean",
    "route_tardiness_min",
    "route_time_s",
]

RESULTS_SIGNIFICANCE_COLUMNS = [
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
]


@dataclass(frozen=True)
class ScenarioSpec:
    run_id: str
    seed: int
    n_clients: int
    num_uavs: int
    delta_min: int
    bs_count: int
    edge_samples: int
    lambda_out: float
    lambda_tw: float
    tw_family: str
    tw_mode: str


@dataclass(frozen=True)
class CostSpec:
    energy_per_m: float
    risk_scale: float
    cost_scale: float
    lambda_out: float
    lambda_tw: float


@dataclass
class RouteRecord:
    run_id: str
    uav_id: int
    route_node_sequence: str
    route_energy: float
    route_risk_mean: float
    route_tardiness_min: float
    route_time_s: float


@dataclass
class RunResult:
    run_id: str
    profile: str
    git_sha: str
    env_hash: str
    timestamp: str
    seed: int
    method: str
    N: int
    M: int
    Delta_min: int
    B: int
    K: int
    lambda_out: float
    lambda_tw: float
    tw_family: str
    tw_mode: str
    on_time_pct: Optional[float]
    total_tardiness_min: Optional[float]
    total_energy: Optional[float]
    risk_mean: Optional[float]
    risk_max_route: Optional[float]
    runtime_edge_s: float
    runtime_solve_s: float
    runtime_total_s: float
    incumbent_obj: Optional[float]
    best_bound: Optional[float]
    gap_pct: Optional[float]
    feasible_flag: int
    claim_regime: str

    def to_row(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "profile": self.profile,
            "git_sha": self.git_sha,
            "env_hash": self.env_hash,
            "timestamp": self.timestamp,
            "seed": self.seed,
            "method": self.method,
            "N": self.N,
            "M": self.M,
            "Delta_min": self.Delta_min,
            "B": self.B,
            "K": self.K,
            "lambda_out": self.lambda_out,
            "lambda_tw": self.lambda_tw,
            "tw_family": self.tw_family,
            "tw_mode": self.tw_mode,
            "on_time_pct": self.on_time_pct,
            "total_tardiness_min": self.total_tardiness_min,
            "total_energy": self.total_energy,
            "risk_mean": self.risk_mean,
            "risk_max_route": self.risk_max_route,
            "runtime_edge_s": self.runtime_edge_s,
            "runtime_solve_s": self.runtime_solve_s,
            "runtime_total_s": self.runtime_total_s,
            "incumbent_obj": self.incumbent_obj,
            "best_bound": self.best_bound,
            "gap_pct": self.gap_pct,
            "feasible_flag": self.feasible_flag,
            "claim_regime": self.claim_regime,
        }


@dataclass
class SignificanceResult:
    comparison_id: str
    method_a: str
    method_b: str
    metric: str
    test_name: str
    p_value: Optional[float]
    p_value_adj: Optional[float]
    correction_method: str
    effect_direction: str
    effect_size: Optional[float]
    ci_low: Optional[float]
    ci_high: Optional[float]
    n_pairs: int
    significant_flag: int

    def to_row(self) -> Dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "method_a": self.method_a,
            "method_b": self.method_b,
            "metric": self.metric,
            "test_name": self.test_name,
            "p_value": self.p_value,
            "p_value_adj": self.p_value_adj,
            "correction_method": self.correction_method,
            "effect_direction": self.effect_direction,
            "effect_size": self.effect_size,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "n_pairs": self.n_pairs,
            "significant_flag": self.significant_flag,
        }


@dataclass
class ScenarioData:
    depot_xy: np.ndarray
    client_xy: np.ndarray
    delivery: np.ndarray
    pickup: np.ndarray
    service_duration_s: np.ndarray
    tw_early_s: np.ndarray
    tw_late_s: np.ndarray
    bs_xy: np.ndarray
    speed_mps: float
    capacity_kg: float
    altitude_m: float


@dataclass
class EdgeData:
    distance_m: np.ndarray
    travel_time_s: np.ndarray
    risk: np.ndarray
    energy: np.ndarray
    cost: np.ndarray


@dataclass
class SolverOutput:
    method: str
    status: str
    objective: Optional[float]
    bound: Optional[float]
    gap_pct: Optional[float]
    runtime_s: float
    routes: List[List[int]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    seeds: List[int]
    sizes: List[int]
    include_scalability: bool
    bs_counts: List[int]
    deltas_min: List[int]
    edge_samples: List[int]
    lambda_out: List[float]
    lambda_tw: List[float]
    max_cases: int = 0


@dataclass(frozen=True)
class TimeWindowConfig:
    mode: str
    family: str
    family_b_shrink: float
    family_b_jitter_min: float


@dataclass(frozen=True)
class SolverConfig:
    heuristic_engine: str
    time_limits: Dict[str, float]
    ortools_first_solution: str
    ortools_metaheuristic: str
    pyvrp_max_iterations: int
    pyvrp_max_runtime_s: float


@dataclass(frozen=True)
class ProjectConfig:
    area_km: float
    depot_location: str
    num_uavs: int
    capacity_kg: float
    speed_mps: float
    altitude_m: float
    service_duration_s: float
    client_weights_kg: List[float]
    delivery_ratio: float
    pickup_ratio: float
    both_ratio: float
    bs_counts: List[int]
    sizes: List[int]
    scalability_size: int
    seeds: List[int]
    edge_samples: int
    edge_samples_sensitivity: List[int]
    lambda_out: List[float]
    lambda_tw: List[float]
    weight_scale: float
    cost_scale: float
    risk_scale: float
    comm: Dict[str, Any]
    energy: Dict[str, Any]
    tw: TimeWindowConfig
    solver: SolverConfig
    profiles: Dict[str, ProfileConfig]
