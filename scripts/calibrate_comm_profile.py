#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from uavtre.io.loaders import load_project_config
from uavtre.io.schema import ScenarioSpec
from uavtre.risk.edge_risk import compute_risk_matrix
from uavtre.scenario.generator import generate_scenario


def mean_edge_risk(cfg, bs_count: int, n_clients: int, delta_min: int, seeds: list[int]) -> float:
    means: list[float] = []
    for seed in seeds:
        spec = ScenarioSpec(
            run_id=f"cal_{seed}",
            seed=seed,
            n_clients=n_clients,
            num_uavs=cfg.num_uavs,
            delta_min=delta_min,
            bs_count=bs_count,
            edge_samples=cfg.edge_samples,
            lambda_out=0.5,
            lambda_tw=1.0,
            tw_family=cfg.tw.family,
            tw_mode=cfg.tw.mode,
        )
        scenario = generate_scenario(cfg, spec)
        risk = compute_risk_matrix(scenario, cfg.comm, cfg.edge_samples)
        vals = risk[np.triu_indices_from(risk, 1)]
        means.append(float(vals.mean()))
    return float(np.mean(means))


def calibrate(cfg, target_low: float, target_high: float, bs_count: int, n_clients: int, delta_min: int, seeds: list[int]):
    # Keep channel model structure fixed and tune operational threshold.
    candidates = []
    base_thr = float(cfg.comm["snr_threshold_db"])
    for snr_thr in np.linspace(base_thr, base_thr + 40.0, 17):
        cfg.comm["snr_threshold_db"] = float(snr_thr)
        mr = mean_edge_risk(cfg, bs_count, n_clients, delta_min, seeds)
        score = 0.0
        if mr < target_low:
            score = target_low - mr
        elif mr > target_high:
            score = mr - target_high
        candidates.append((score, mr, float(snr_thr)))

    candidates.sort(key=lambda x: x[0])
    best = candidates[0]
    return {
        "snr_threshold_db": best[2],
        "mean_edge_risk": best[1],
        "target_low": target_low,
        "target_high": target_high,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Calibrate comm parameters for non-degenerate outage risk.")
    p.add_argument("--config", type=str, default="configs/base.json")
    p.add_argument("--profile", type=str, default="quick")
    p.add_argument("--target-low", type=float, default=0.05)
    p.add_argument("--target-high", type=float, default=0.25)
    p.add_argument("--bs-count", type=int, default=4)
    p.add_argument("--n-clients", type=int, default=20)
    p.add_argument("--delta-min", type=int, default=10)
    p.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    p.add_argument("--output", type=str, default="configs/overrides/comm_calibrated_q1.json")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_project_config(args.config, profile_name=args.profile)
    result = calibrate(
        cfg=cfg,
        target_low=args.target_low,
        target_high=args.target_high,
        bs_count=args.bs_count,
        n_clients=args.n_clients,
        delta_min=args.delta_min,
        seeds=args.seeds,
    )

    payload = {
        "comm": {
            "snr_threshold_db": result["snr_threshold_db"],
        },
        "meta": {
            "calibrated_mean_edge_risk": result["mean_edge_risk"],
            "target_low": result["target_low"],
            "target_high": result["target_high"],
            "basis": {
                "bs_count": args.bs_count,
                "n_clients": args.n_clients,
                "delta_min": args.delta_min,
                "seeds": args.seeds,
            },
        },
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"calibrated snr_threshold_db={result['snr_threshold_db']:.2f}")
    print(f"estimated mean_edge_risk={result['mean_edge_risk']:.4f}")
    print(f"written override: {out}")


if __name__ == "__main__":
    main()
