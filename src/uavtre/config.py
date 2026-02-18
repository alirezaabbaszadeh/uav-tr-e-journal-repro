from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .io.loaders import get_default_config_path, load_project_config


def load_config(path: str | Path) -> Dict[str, Any]:
    cfg = load_project_config(path)
    return {
        "area_km": cfg.area_km,
        "depot_location": cfg.depot_location,
        "num_uavs": cfg.num_uavs,
        "capacity_kg": cfg.capacity_kg,
        "speed_mps": cfg.speed_mps,
        "altitude_m": cfg.altitude_m,
        "service_duration_s": cfg.service_duration_s,
        "client_weights_kg": cfg.client_weights_kg,
        "delivery_ratio": cfg.delivery_ratio,
        "pickup_ratio": cfg.pickup_ratio,
        "both_ratio": cfg.both_ratio,
        "bs_counts": cfg.bs_counts,
        "time_window_minutes": cfg.profiles["main_table"].deltas_min,
        "lambda_out": cfg.lambda_out,
        "lambda_tw": cfg.lambda_tw,
        "edge_samples": cfg.edge_samples,
        "edge_samples_sensitivity": cfg.edge_samples_sensitivity,
        "seeds": cfg.seeds,
        "sizes": cfg.sizes,
        "scalability_size": cfg.scalability_size,
        "weight_scale": cfg.weight_scale,
        "cost_scale": cfg.cost_scale,
        "risk_scale": cfg.risk_scale,
        "comm": cfg.comm,
        "energy": cfg.energy,
        "profiles": {k: v.__dict__ for k, v in cfg.profiles.items()},
    }


__all__ = ["get_default_config_path", "load_config", "load_project_config"]
