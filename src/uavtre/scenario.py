from __future__ import annotations

from typing import Dict

import numpy as np

from .data_types import ScenarioData


def _baseline_times(
    client_xy: np.ndarray,
    depot_xy: np.ndarray,
    speed_mps: float,
    service_duration_s: float,
    num_uavs: int,
) -> np.ndarray:
    angles = np.arctan2(client_xy[:, 1] - depot_xy[1], client_xy[:, 0] - depot_xy[0])
    order = np.argsort(angles)
    groups = [[] for _ in range(num_uavs)]
    for idx, c_idx in enumerate(order):
        groups[idx % num_uavs].append(int(c_idx))

    times = np.zeros(len(client_xy), dtype=float)
    for group in groups:
        t = 0.0
        prev = depot_xy
        for i in group:
            dist = float(np.linalg.norm(client_xy[i] - prev))
            t += dist / speed_mps
            times[i] = t
            t += service_duration_s
            prev = client_xy[i]
    return times


def generate_scenario(
    cfg: Dict,
    seed: int,
    num_clients: int,
    bs_count: int,
    tw_delta_min: float,
) -> ScenarioData:
    rng = np.random.default_rng(seed)
    area_m = cfg["area_km"] * 1000.0

    if cfg.get("depot_location", "center") == "center":
        depot_xy = np.array([area_m / 2, area_m / 2], dtype=float)
    else:
        depot_xy = rng.uniform(0, area_m, size=2)

    client_xy = rng.uniform(0, area_m, size=(num_clients, 2))
    bs_xy = rng.uniform(0, area_m, size=(bs_count, 2))

    w_min, w_max = cfg["client_weights_kg"]
    weights = rng.uniform(w_min, w_max, size=num_clients)

    delivery_ratio = cfg.get("delivery_ratio", 0.5)
    pickup_ratio = cfg.get("pickup_ratio", 0.5)
    both_ratio = cfg.get("both_ratio", 0.0)

    types = rng.choice(
        ["delivery", "pickup", "both"],
        size=num_clients,
        p=[delivery_ratio, pickup_ratio, both_ratio],
    )

    delivery = np.zeros(num_clients, dtype=float)
    pickup = np.zeros(num_clients, dtype=float)
    for i, t in enumerate(types):
        if t == "delivery":
            delivery[i] = weights[i]
        elif t == "pickup":
            pickup[i] = weights[i]
        else:
            delivery[i] = weights[i] * 0.5
            pickup[i] = weights[i] * 0.5

    service_duration_s = float(cfg["service_duration_s"])
    baseline = _baseline_times(
        client_xy, depot_xy, cfg["speed_mps"], service_duration_s, cfg["num_uavs"]
    )
    delta_s = tw_delta_min * 60.0
    tw_early = np.maximum(0.0, baseline - delta_s)
    tw_late = baseline + delta_s

    return ScenarioData(
        depot_xy=depot_xy,
        client_xy=client_xy,
        delivery=delivery,
        pickup=pickup,
        service_duration_s=np.full(num_clients, service_duration_s, dtype=float),
        tw_early_s=tw_early,
        tw_late_s=tw_late,
        bs_xy=bs_xy,
        speed_mps=float(cfg["speed_mps"]),
        capacity_kg=float(cfg["capacity_kg"]),
        altitude_m=float(cfg["altitude_m"]),
    )
