from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..io.schema import ProjectConfig, ScenarioData, ScenarioSpec
from .time_windows import build_time_windows


def scenario_instance_id(spec: ScenarioSpec) -> str:
    return (
        f"seed{spec.seed}_N{spec.n_clients}_M{spec.num_uavs}_D{spec.delta_min}_"
        f"B{spec.bs_count}_K{spec.edge_samples}_lo{spec.lambda_out}_lt{spec.lambda_tw}_"
        f"tw{spec.tw_family}"
    )


def _baseline_times(
    client_xy: np.ndarray,
    depot_xy: np.ndarray,
    speed_mps: float,
    service_duration_s: float,
    num_uavs: int,
) -> np.ndarray:
    angles = np.arctan2(client_xy[:, 1] - depot_xy[1], client_xy[:, 0] - depot_xy[0])
    order = np.argsort(angles)
    groups = [[] for _ in range(max(1, num_uavs))]

    for idx, client_idx in enumerate(order):
        groups[idx % max(1, num_uavs)].append(int(client_idx))

    baseline = np.zeros(len(client_xy), dtype=float)
    for group in groups:
        t = 0.0
        prev = depot_xy
        for i in group:
            dist = float(np.linalg.norm(client_xy[i] - prev))
            t += dist / speed_mps
            baseline[i] = t
            t += service_duration_s
            prev = client_xy[i]
    return baseline


def generate_scenario(cfg: ProjectConfig, spec: ScenarioSpec) -> ScenarioData:
    seed = (
        spec.seed * 10_000
        + spec.n_clients * 100
        + spec.bs_count * 10
        + spec.delta_min
        + spec.edge_samples
    )
    rng = np.random.default_rng(seed)
    area_m = cfg.area_km * 1000.0

    if cfg.depot_location == "center":
        depot_xy = np.array([area_m / 2.0, area_m / 2.0], dtype=float)
    else:
        depot_xy = rng.uniform(0.0, area_m, size=2)

    client_xy = rng.uniform(0.0, area_m, size=(spec.n_clients, 2))
    bs_xy = rng.uniform(0.0, area_m, size=(spec.bs_count, 2))

    weights = rng.uniform(
        cfg.client_weights_kg[0], cfg.client_weights_kg[1], size=spec.n_clients
    )
    service_duration_s = np.full(spec.n_clients, cfg.service_duration_s, dtype=float)

    types = rng.choice(
        ["delivery", "pickup", "both"],
        size=spec.n_clients,
        p=[cfg.delivery_ratio, cfg.pickup_ratio, cfg.both_ratio],
    )

    delivery = np.zeros(spec.n_clients, dtype=float)
    pickup = np.zeros(spec.n_clients, dtype=float)
    for i, task_type in enumerate(types):
        if task_type == "delivery":
            delivery[i] = weights[i]
        elif task_type == "pickup":
            pickup[i] = weights[i]
        else:
            delivery[i] = 0.5 * weights[i]
            pickup[i] = 0.5 * weights[i]

    baseline_times = _baseline_times(
        client_xy=client_xy,
        depot_xy=depot_xy,
        speed_mps=cfg.speed_mps,
        service_duration_s=cfg.service_duration_s,
        num_uavs=cfg.num_uavs,
    )

    tw_early, tw_late = build_time_windows(
        baseline_times_s=baseline_times,
        delta_min=spec.delta_min,
        family=spec.tw_family,
        rng=rng,
        family_b_shrink=cfg.tw.family_b_shrink,
        family_b_jitter_min=cfg.tw.family_b_jitter_min,
    )

    return ScenarioData(
        depot_xy=depot_xy,
        client_xy=client_xy,
        delivery=delivery,
        pickup=pickup,
        service_duration_s=service_duration_s,
        tw_early_s=tw_early,
        tw_late_s=tw_late,
        bs_xy=bs_xy,
        speed_mps=cfg.speed_mps,
        capacity_kg=cfg.capacity_kg,
        altitude_m=cfg.altitude_m,
    )


def save_frozen_instance(path: Path, spec: ScenarioSpec, scenario: ScenarioData) -> None:
    payload = {
        "spec": {
            "run_id": spec.run_id,
            "seed": spec.seed,
            "n_clients": spec.n_clients,
            "num_uavs": spec.num_uavs,
            "delta_min": spec.delta_min,
            "bs_count": spec.bs_count,
            "edge_samples": spec.edge_samples,
            "lambda_out": spec.lambda_out,
            "lambda_tw": spec.lambda_tw,
            "tw_family": spec.tw_family,
            "tw_mode": spec.tw_mode,
        },
        "scenario": {
            "depot_xy": scenario.depot_xy.tolist(),
            "client_xy": scenario.client_xy.tolist(),
            "delivery": scenario.delivery.tolist(),
            "pickup": scenario.pickup.tolist(),
            "service_duration_s": scenario.service_duration_s.tolist(),
            "tw_early_s": scenario.tw_early_s.tolist(),
            "tw_late_s": scenario.tw_late_s.tolist(),
            "bs_xy": scenario.bs_xy.tolist(),
            "speed_mps": scenario.speed_mps,
            "capacity_kg": scenario.capacity_kg,
            "altitude_m": scenario.altitude_m,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_frozen_instance(path: Path) -> ScenarioData:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    raw = payload["scenario"]
    return ScenarioData(
        depot_xy=np.array(raw["depot_xy"], dtype=float),
        client_xy=np.array(raw["client_xy"], dtype=float),
        delivery=np.array(raw["delivery"], dtype=float),
        pickup=np.array(raw["pickup"], dtype=float),
        service_duration_s=np.array(raw["service_duration_s"], dtype=float),
        tw_early_s=np.array(raw["tw_early_s"], dtype=float),
        tw_late_s=np.array(raw["tw_late_s"], dtype=float),
        bs_xy=np.array(raw["bs_xy"], dtype=float),
        speed_mps=float(raw["speed_mps"]),
        capacity_kg=float(raw["capacity_kg"]),
        altitude_m=float(raw["altitude_m"]),
    )
