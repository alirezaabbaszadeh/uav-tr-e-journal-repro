from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .schema import ProfileConfig, ProjectConfig, SolverConfig, TimeWindowConfig


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_profiles(cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    defaults = {
        "quick": {
            "seeds": cfg["seeds"][:1],
            "sizes": cfg["sizes"][:1],
            "include_scalability": False,
            "bs_counts": cfg["bs_counts"][:1],
            "deltas_min": cfg["time_window_minutes"][:1],
            "edge_samples": [cfg["edge_samples"]],
            "lambda_out": cfg["lambda_out"][:1],
            "lambda_tw": cfg["lambda_tw"][:1],
            "max_cases": 1,
        },
        "main_table": {
            "seeds": cfg["seeds"],
            "sizes": cfg["sizes"],
            "include_scalability": False,
            "bs_counts": cfg["bs_counts"],
            "deltas_min": cfg["time_window_minutes"],
            "edge_samples": [cfg["edge_samples"]],
            "lambda_out": cfg["lambda_out"],
            "lambda_tw": cfg["lambda_tw"],
            "max_cases": 0,
        },
        "scalability": {
            "seeds": cfg["seeds"],
            "sizes": [],
            "include_scalability": True,
            "bs_counts": cfg["bs_counts"][:1],
            "deltas_min": cfg["time_window_minutes"][:1],
            "edge_samples": [cfg["edge_samples"]],
            "lambda_out": cfg["lambda_out"][:1],
            "lambda_tw": cfg["lambda_tw"][:1],
            "max_cases": 0,
        },
    }

    out = defaults
    for name, profile in cfg.get("profiles", {}).items():
        out[name] = _deep_merge(out.get(name, {}), profile)
    return out


def _coerce_legacy_schema(cfg: Dict[str, Any]) -> Dict[str, Any]:
    cfg = dict(cfg)

    cfg.setdefault("time_window_minutes", [10, 5, 2])
    cfg.setdefault("lambda_out", [0.0, 0.5, 1.0])
    cfg.setdefault("lambda_tw", [0.0, 1.0, 5.0])
    cfg.setdefault("edge_samples", 10)
    cfg.setdefault("edge_samples_sensitivity", [5, 10, 20])

    tw = cfg.get("tw", {})
    tw.setdefault("mode", "soft")
    tw.setdefault("family", "A")
    tw.setdefault("family_b_shrink", 0.8)
    tw.setdefault("family_b_jitter_min", 1.0)
    cfg["tw"] = tw

    solver = cfg.get("solver", {})
    # Backward compatibility from old keys
    if "heuristic_engine" not in solver:
        if "pyvrp" in cfg and cfg.get("pyvrp", {}).get("use_as_main", False):
            solver["heuristic_engine"] = "pyvrp"
        else:
            solver["heuristic_engine"] = "ortools"

    if "time_limits" not in solver:
        highs = cfg.get("highs", {})
        solver["time_limits"] = {
            "exact_n10_s": float(highs.get("time_limit_exact_s", 3600)),
            "bound_n20_s": float(highs.get("time_limit_bound_s", 900)),
            "bound_n40_s": float(highs.get("time_limit_bound_s", 1800)),
            "scalability_n80_s": 900.0,
            "heuristic_default_s": float(cfg.get("pyvrp", {}).get("max_runtime_s", 120)),
        }

    solver.setdefault("ortools_first_solution", "PATH_CHEAPEST_ARC")
    solver.setdefault("ortools_metaheuristic", "GUIDED_LOCAL_SEARCH")
    solver.setdefault("pyvrp_max_iterations", int(cfg.get("pyvrp", {}).get("max_iterations", 2000)))
    solver.setdefault("pyvrp_max_runtime_s", float(cfg.get("pyvrp", {}).get("max_runtime_s", 120)))
    cfg["solver"] = solver

    cfg.setdefault("profiles", {})
    cfg["profiles"] = _normalize_profiles(cfg)

    return cfg


def load_project_config(
    config_path: str | Path,
    profile_name: str | None = None,
    profile_override_path: str | Path | None = None,
) -> ProjectConfig:
    base = _load_json(Path(config_path))

    if profile_override_path:
        base = _deep_merge(base, _load_json(Path(profile_override_path)))

    cfg = _coerce_legacy_schema(base)

    if profile_name is None:
        profile_name = "main_table"

    if profile_name not in cfg["profiles"]:
        raise ValueError(f"Unknown profile: {profile_name}")

    profiles = {
        name: ProfileConfig(
            name=name,
            seeds=list(profile["seeds"]),
            sizes=list(profile["sizes"]),
            include_scalability=bool(profile["include_scalability"]),
            bs_counts=list(profile["bs_counts"]),
            deltas_min=list(profile["deltas_min"]),
            edge_samples=list(profile["edge_samples"]),
            lambda_out=list(profile["lambda_out"]),
            lambda_tw=list(profile["lambda_tw"]),
            max_cases=int(profile.get("max_cases", 0)),
        )
        for name, profile in cfg["profiles"].items()
    }

    tw = TimeWindowConfig(
        mode=cfg["tw"]["mode"],
        family=cfg["tw"]["family"],
        family_b_shrink=float(cfg["tw"]["family_b_shrink"]),
        family_b_jitter_min=float(cfg["tw"]["family_b_jitter_min"]),
    )

    solver = SolverConfig(
        heuristic_engine=cfg["solver"]["heuristic_engine"],
        time_limits={k: float(v) for k, v in cfg["solver"]["time_limits"].items()},
        ortools_first_solution=cfg["solver"]["ortools_first_solution"],
        ortools_metaheuristic=cfg["solver"]["ortools_metaheuristic"],
        pyvrp_max_iterations=int(cfg["solver"]["pyvrp_max_iterations"]),
        pyvrp_max_runtime_s=float(cfg["solver"]["pyvrp_max_runtime_s"]),
    )

    return ProjectConfig(
        area_km=float(cfg["area_km"]),
        depot_location=str(cfg.get("depot_location", "center")),
        num_uavs=int(cfg["num_uavs"]),
        capacity_kg=float(cfg["capacity_kg"]),
        speed_mps=float(cfg["speed_mps"]),
        altitude_m=float(cfg["altitude_m"]),
        service_duration_s=float(cfg["service_duration_s"]),
        client_weights_kg=[float(cfg["client_weights_kg"][0]), float(cfg["client_weights_kg"][1])],
        delivery_ratio=float(cfg.get("delivery_ratio", 0.5)),
        pickup_ratio=float(cfg.get("pickup_ratio", 0.5)),
        both_ratio=float(cfg.get("both_ratio", 0.0)),
        bs_counts=[int(v) for v in cfg["bs_counts"]],
        sizes=[int(v) for v in cfg["sizes"]],
        scalability_size=int(cfg["scalability_size"]),
        seeds=[int(v) for v in cfg["seeds"]],
        edge_samples=int(cfg["edge_samples"]),
        edge_samples_sensitivity=[int(v) for v in cfg["edge_samples_sensitivity"]],
        lambda_out=[float(v) for v in cfg["lambda_out"]],
        lambda_tw=[float(v) for v in cfg["lambda_tw"]],
        weight_scale=float(cfg.get("weight_scale", 1000)),
        cost_scale=float(cfg.get("cost_scale", 1000)),
        risk_scale=float(cfg.get("risk_scale", 1000)),
        comm=dict(cfg["comm"]),
        energy=dict(cfg["energy"]),
        tw=tw,
        solver=solver,
        profiles=profiles,
    )


def get_default_config_path() -> Path:
    return Path(__file__).resolve().parents[3] / "configs" / "base.json"
