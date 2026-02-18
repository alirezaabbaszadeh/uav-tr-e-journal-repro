from __future__ import annotations

import hashlib
import itertools
import math
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

from ..costs import build_edge_data, compute_distance_and_time_matrices, evaluate_routes
from ..io.export_csv import (
    resolve_output_paths,
    write_results_main,
    write_results_routes,
    write_results_significance,
)
from ..io.schema import CostSpec, RouteRecord, RunResult, ScenarioSpec, SolverOutput
from ..risk import compute_risk_matrix
from ..scenario import (
    generate_scenario,
    load_frozen_instance,
    save_frozen_instance,
    scenario_instance_id,
)
from ..solvers import solve_with_highs, solve_with_ortools, solve_with_pyvrp
from .significance import compute_significance_results


def _workspace_fingerprint() -> str:
    root = Path(__file__).resolve().parents[3]
    digest = hashlib.sha256()
    patterns = [
        "pyproject.toml",
        "requirements-lock.txt",
        "src/**/*.py",
        "configs/**/*.json",
    ]

    paths: List[Path] = []
    for pattern in patterns:
        paths.extend(root.glob(pattern))

    for path in sorted(p for p in paths if p.is_file()):
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())

    return f"nogit-{digest.hexdigest()[:12]}"


def _git_sha_or_unknown() -> str:
    try:
        cmd = ["git", "rev-parse", "--short", "HEAD"]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
        if out:
            return out
    except Exception:
        pass
    return _workspace_fingerprint()


def _environment_hash() -> str:
    payload = f"{sys.version}|{platform.platform()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _claim_regime(n_clients: int, scalability_size: int) -> str:
    if n_clients <= 10:
        return "exact"
    if n_clients >= scalability_size:
        return "scalability_only"
    return "bound_gap"


def _time_limits_for_size(cfg, n_clients: int, profile_name: str) -> Dict[str, float]:
    if profile_name == "quick":
        return {"heuristic": 10.0, "highs": 10.0}

    tl = cfg.solver.time_limits
    if n_clients <= 10:
        exact = float(tl.get("exact_n10_s", 3600.0))
        return {"heuristic": exact, "highs": exact}
    if n_clients == 20:
        bound = float(tl.get("bound_n20_s", 900.0))
        return {"heuristic": bound, "highs": bound}
    if n_clients == 40:
        bound = float(tl.get("bound_n40_s", 1800.0))
        return {"heuristic": bound, "highs": bound}

    scalability = float(tl.get("scalability_n80_s", 900.0))
    return {"heuristic": scalability, "highs": 0.0}


def _iter_specs(cfg, profile_name: str, max_cases: int = 0) -> Iterable[ScenarioSpec]:
    profile = cfg.profiles[profile_name]
    sizes = list(profile.sizes)
    if profile.include_scalability:
        sizes.append(cfg.scalability_size)

    count = 0
    for seed, n, b, d, k, lo, ltw in itertools.product(
        profile.seeds,
        sizes,
        profile.bs_counts,
        profile.deltas_min,
        profile.edge_samples,
        profile.lambda_out,
        profile.lambda_tw,
    ):
        if max_cases and count >= max_cases:
            break
        run_key = (
            f"seed{seed}_N{n}_M{cfg.num_uavs}_D{d}_B{b}_K{k}_"
            f"lo{lo}_lt{ltw}_tw{cfg.tw.family}"
        )
        yield ScenarioSpec(
            run_id=run_key,
            seed=int(seed),
            n_clients=int(n),
            num_uavs=cfg.num_uavs,
            delta_min=int(d),
            bs_count=int(b),
            edge_samples=int(k),
            lambda_out=float(lo),
            lambda_tw=float(ltw),
            tw_family=cfg.tw.family,
            tw_mode=cfg.tw.mode,
        )
        count += 1


def _safe_solver_call(name: str, func, *args, **kwargs) -> SolverOutput:
    start = time.perf_counter()
    try:
        out: SolverOutput = func(*args, **kwargs)
    except Exception as exc:  # pragma: no cover
        return SolverOutput(
            method=name,
            status=f"unavailable:{exc}",
            objective=None,
            bound=None,
            gap_pct=None,
            runtime_s=time.perf_counter() - start,
            routes=[],
            metadata={"error": str(exc)},
        )

    out.runtime_s = time.perf_counter() - start
    out.method = name
    return out


def _is_feasible_status(status: str) -> bool:
    status_lower = status.lower()
    if "infeasible" in status_lower:
        return False
    if "unavailable" in status_lower:
        return False
    return True


def _is_optimal_status(status: str) -> bool:
    s = status.lower()
    return "optimal" in s and "not" not in s


def _sanitize_finite(value: float | None) -> float | None:
    if value is None:
        return None
    v = float(value)
    if not math.isfinite(v):
        return None
    return v


def _compute_gap_pct(incumbent_obj: float | None, best_bound: float | None) -> float | None:
    incumbent = _sanitize_finite(incumbent_obj)
    bound = _sanitize_finite(best_bound)
    if incumbent is None or bound is None:
        return None

    tol = max(1e-6, 1e-6 * abs(incumbent))
    if bound > incumbent + tol:
        return None

    denom = max(abs(incumbent), 1e-9)
    gap = 100.0 * (incumbent - bound) / denom
    if not math.isfinite(gap):
        return None
    return max(0.0, gap)


def run_experiment_matrix(
    cfg,
    profile_name: str,
    output_main_path: str | Path,
    max_cases: int = 0,
    freeze_benchmarks: bool = False,
    benchmark_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    timestamp = datetime.now(timezone.utc).isoformat()
    git_sha = _git_sha_or_unknown()
    env_hash = _environment_hash()

    main_rows: List[RunResult] = []
    route_rows: List[RouteRecord] = []

    benchmark_root = Path(benchmark_dir) if benchmark_dir else None

    for spec in _iter_specs(cfg, profile_name=profile_name, max_cases=max_cases):
        base_claim_regime = _claim_regime(spec.n_clients, cfg.scalability_size)
        time_limits = _time_limits_for_size(cfg, spec.n_clients, profile_name)

        scenario_id = scenario_instance_id(spec)
        frozen_path = None
        if benchmark_root is not None:
            frozen_path = benchmark_root / f"{scenario_id}.json"

        if frozen_path and frozen_path.exists():
            scenario = load_frozen_instance(frozen_path)
        else:
            scenario = generate_scenario(cfg, spec)
            if freeze_benchmarks and frozen_path is not None:
                save_frozen_instance(frozen_path, spec, scenario)

        edge_start = time.perf_counter()
        distance_m, travel_s = compute_distance_and_time_matrices(scenario)
        risk = compute_risk_matrix(
            scenario=scenario,
            comm_params=cfg.comm,
            edge_samples=spec.edge_samples,
        )
        cost_spec = CostSpec(
            energy_per_m=float(cfg.energy.get("e_per_m", 1.0)),
            risk_scale=float(cfg.risk_scale),
            cost_scale=float(cfg.cost_scale),
            lambda_out=spec.lambda_out,
            lambda_tw=spec.lambda_tw,
        )
        edge = build_edge_data(distance_m, travel_s, risk, cost_spec)
        runtime_edge_s = time.perf_counter() - edge_start

        solver_outputs: List[SolverOutput] = []

        if cfg.solver.heuristic_engine.lower() == "pyvrp":
            solver_outputs.append(
                _safe_solver_call(
                    "pyvrp_main",
                    solve_with_pyvrp,
                    scenario,
                    edge,
                    cfg.num_uavs,
                    cfg.weight_scale,
                    spec.seed,
                    cfg.solver.pyvrp_max_iterations,
                    min(cfg.solver.pyvrp_max_runtime_s, time_limits["heuristic"]),
                )
            )
        else:
            solver_outputs.append(
                _safe_solver_call(
                    "ortools_main",
                    solve_with_ortools,
                    scenario,
                    edge,
                    {
                        "num_uavs": cfg.num_uavs,
                        "ortools_first_solution": cfg.solver.ortools_first_solution,
                        "ortools_metaheuristic": cfg.solver.ortools_metaheuristic,
                        "cost_scale": cfg.cost_scale,
                    },
                    spec.seed,
                    spec.tw_mode,
                    spec.lambda_tw,
                    cfg.weight_scale,
                    time_limits["heuristic"],
                )
            )
            solver_outputs.append(
                _safe_solver_call(
                    "pyvrp_baseline",
                    solve_with_pyvrp,
                    scenario,
                    edge,
                    cfg.num_uavs,
                    cfg.weight_scale,
                    spec.seed,
                    cfg.solver.pyvrp_max_iterations,
                    min(cfg.solver.pyvrp_max_runtime_s, time_limits["heuristic"]),
                )
            )

        if base_claim_regime != "scalability_only":
            solver_outputs.append(
                _safe_solver_call(
                    "highs_exact_bound",
                    solve_with_highs,
                    scenario,
                    edge,
                    cfg.num_uavs,
                    cfg.weight_scale,
                    time_limits["highs"],
                    spec.tw_mode,
                    float(cfg.cost_scale) * float(spec.lambda_tw) / 60.0,
                    0.0,
                )
            )

        highs_bound = None
        highs_out: SolverOutput | None = None
        for out in solver_outputs:
            if out.method == "highs_exact_bound":
                highs_out = out
                highs_bound = _sanitize_finite(out.bound)
                break

        exact_certified = False
        if base_claim_regime == "exact" and highs_out is not None:
            exact_certified = _is_optimal_status(highs_out.status)

        claim_regime = base_claim_regime
        if base_claim_regime == "exact" and not exact_certified:
            claim_regime = "bound_gap"

        for out in solver_outputs:
            run_id = f"{profile_name}_{spec.run_id}_{out.method}"
            feasible_flag = 0
            on_time_pct = None
            total_tardiness_min = None
            total_energy = None
            risk_mean = None
            risk_max_route = None
            incumbent_obj = None
            best_bound = None
            gap_pct = None

            if out.routes:
                evaluated = evaluate_routes(scenario, edge, out.routes, cost_spec, run_id)
                feasible_flag = int(evaluated.feasible and _is_feasible_status(out.status))
                if feasible_flag:
                    on_time_pct = float(evaluated.on_time_pct)
                    total_tardiness_min = float(evaluated.total_tardiness_min)
                    total_energy = float(evaluated.total_energy)
                    risk_mean = float(evaluated.risk_mean)
                    risk_max_route = float(evaluated.risk_max_route)
                    incumbent_obj = _sanitize_finite(float(evaluated.incumbent_obj))
                for rr in evaluated.route_rows:
                    route_rows.append(RouteRecord(**rr))
            else:
                feasible_flag = int(_is_feasible_status(out.status))
                incumbent_obj = _sanitize_finite(out.objective)

            if claim_regime == "scalability_only":
                best_bound = None
                gap_pct = None
            elif out.method == "highs_exact_bound":
                best_bound = _sanitize_finite(out.bound)
                if claim_regime == "exact":
                    gap_pct = 0.0
                    if incumbent_obj is None:
                        incumbent_obj = _sanitize_finite(out.objective)
                else:
                    gap_pct = _compute_gap_pct(
                        incumbent_obj if incumbent_obj is not None else out.objective,
                        best_bound,
                    )
            elif highs_bound is not None and incumbent_obj is not None:
                best_bound = highs_bound
                gap_pct = _compute_gap_pct(incumbent_obj, best_bound)

            runtime_solve_s = float(out.runtime_s)
            runtime_total_s = runtime_edge_s + runtime_solve_s

            main_rows.append(
                RunResult(
                    run_id=run_id,
                    profile=profile_name,
                    git_sha=git_sha,
                    env_hash=env_hash,
                    timestamp=timestamp,
                    seed=spec.seed,
                    method=out.method,
                    N=spec.n_clients,
                    M=spec.num_uavs,
                    Delta_min=spec.delta_min,
                    B=spec.bs_count,
                    K=spec.edge_samples,
                    lambda_out=spec.lambda_out,
                    lambda_tw=spec.lambda_tw,
                    tw_family=spec.tw_family,
                    tw_mode=spec.tw_mode,
                    on_time_pct=on_time_pct,
                    total_tardiness_min=total_tardiness_min,
                    total_energy=total_energy,
                    risk_mean=risk_mean,
                    risk_max_route=risk_max_route,
                    runtime_edge_s=runtime_edge_s,
                    runtime_solve_s=runtime_solve_s,
                    runtime_total_s=runtime_total_s,
                    incumbent_obj=incumbent_obj,
                    best_bound=best_bound,
                    gap_pct=gap_pct,
                    feasible_flag=feasible_flag,
                    claim_regime=claim_regime,
                )
            )

    main_path, routes_path, sig_path = resolve_output_paths(output_main_path)
    df_main = write_results_main(main_path, main_rows)
    df_routes = write_results_routes(routes_path, route_rows)

    sig_rows = compute_significance_results(df_main)
    df_sig = write_results_significance(sig_path, sig_rows)

    return df_main, df_routes, df_sig
