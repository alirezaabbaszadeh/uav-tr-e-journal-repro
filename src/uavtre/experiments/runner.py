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
from typing import Dict, Iterable, List, Sequence, Set, Tuple

import pandas as pd

from ..costs import build_edge_data, compute_distance_and_time_matrices, evaluate_routes
from ..io.export_csv import resolve_output_paths, write_results_significance
from ..io.schema import (
    CostSpec,
    RESULTS_MAIN_COLUMNS,
    RESULTS_ROUTES_COLUMNS,
    RouteRecord,
    RunResult,
    ScenarioSpec,
    SolverOutput,
)
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


def _iter_specs(
    cfg,
    profile_name: str,
    max_cases: int = 0,
    shard_index: int = 0,
    num_shards: int = 1,
) -> Iterable[ScenarioSpec]:
    if num_shards < 1:
        raise ValueError("num_shards must be >= 1")
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("shard_index must be in [0, num_shards)")

    profile = cfg.profiles[profile_name]
    sizes = list(profile.sizes)
    if profile.include_scalability:
        sizes.append(cfg.scalability_size)

    count = 0
    for spec_idx, (seed, n, b, d, k, lo, ltw) in enumerate(
        itertools.product(
            profile.seeds,
            sizes,
            profile.bs_counts,
            profile.deltas_min,
            profile.edge_samples,
            profile.lambda_out,
            profile.lambda_tw,
        )
    ):
        if spec_idx % num_shards != shard_index:
            continue
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


def _ensure_columns(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[list(columns)]


def _rows_to_main_df(rows: List[RunResult]) -> pd.DataFrame:
    df = pd.DataFrame([row.to_row() for row in rows])
    if df.empty:
        df = pd.DataFrame(columns=RESULTS_MAIN_COLUMNS)
    return _ensure_columns(df, RESULTS_MAIN_COLUMNS)


def _rows_to_routes_df(rows: List[RouteRecord]) -> pd.DataFrame:
    df = pd.DataFrame([row.__dict__ for row in rows])
    if df.empty:
        df = pd.DataFrame(columns=RESULTS_ROUTES_COLUMNS)
    return _ensure_columns(df, RESULTS_ROUTES_COLUMNS)


def _merge_resume_df(
    existing: pd.DataFrame | None,
    fresh: pd.DataFrame,
    dedup_keys: Sequence[str],
    columns: Sequence[str],
) -> pd.DataFrame:
    if existing is None or existing.empty:
        return _ensure_columns(fresh, columns)
    if fresh.empty:
        return _ensure_columns(existing.copy(), columns)

    merged = pd.concat([existing, fresh], ignore_index=True)
    if dedup_keys:
        merged = merged.drop_duplicates(subset=list(dedup_keys), keep="first")
    else:
        merged = merged.drop_duplicates(keep="first")
    return _ensure_columns(merged, columns)


def _solver_run_id(profile_name: str, spec: ScenarioSpec, method: str) -> str:
    return f"{profile_name}_{spec.run_id}_{method}"


def _planned_methods(cfg, base_claim_regime: str) -> List[str]:
    methods: List[str]
    if cfg.solver.heuristic_engine.lower() == "pyvrp":
        methods = ["pyvrp_main"]
    else:
        methods = ["ortools_main", "pyvrp_baseline"]
    if base_claim_regime != "scalability_only":
        methods.append("highs_exact_bound")
    return methods


def _existing_main_lookup(df: pd.DataFrame | None) -> Dict[str, dict]:
    if df is None or df.empty:
        return {}
    out: Dict[str, dict] = {}
    for row in df.to_dict(orient="records"):
        out[str(row.get("run_id", ""))] = row
    return out


def _existing_main_keys(df: pd.DataFrame | None) -> Set[Tuple[str, str]]:
    if df is None or df.empty:
        return set()
    keys: Set[Tuple[str, str]] = set()
    for _, row in df[["run_id", "method"]].dropna().iterrows():
        keys.add((str(row["run_id"]), str(row["method"])))
    return keys


def run_experiment_matrix(
    cfg,
    profile_name: str,
    output_main_path: str | Path,
    max_cases: int = 0,
    freeze_benchmarks: bool = False,
    benchmark_dir: str | Path | None = None,
    shard_index: int = 0,
    num_shards: int = 1,
    resume: bool = False,
    existing_main_df: pd.DataFrame | None = None,
    existing_routes_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    timestamp = datetime.now(timezone.utc).isoformat()
    git_sha = _git_sha_or_unknown()
    env_hash = _environment_hash()

    main_rows: List[RunResult] = []
    route_rows: List[RouteRecord] = []

    main_path, routes_path, sig_path = resolve_output_paths(output_main_path)
    benchmark_root = Path(benchmark_dir) if benchmark_dir else None

    if resume:
        if existing_main_df is None and main_path.exists():
            existing_main_df = _ensure_columns(pd.read_csv(main_path), RESULTS_MAIN_COLUMNS)
        if existing_routes_df is None and routes_path.exists():
            existing_routes_df = _ensure_columns(pd.read_csv(routes_path), RESULTS_ROUTES_COLUMNS)

    existing_main_df = (
        _ensure_columns(existing_main_df, RESULTS_MAIN_COLUMNS)
        if existing_main_df is not None
        else None
    )
    existing_routes_df = (
        _ensure_columns(existing_routes_df, RESULTS_ROUTES_COLUMNS)
        if existing_routes_df is not None
        else None
    )
    resume_keys = _existing_main_keys(existing_main_df) if resume else set()
    existing_lookup = _existing_main_lookup(existing_main_df) if resume else {}

    for spec in _iter_specs(
        cfg,
        profile_name=profile_name,
        max_cases=max_cases,
        shard_index=shard_index,
        num_shards=num_shards,
    ):
        base_claim_regime = _claim_regime(spec.n_clients, cfg.scalability_size)
        time_limits = _time_limits_for_size(cfg, spec.n_clients, profile_name)
        planned_methods = _planned_methods(cfg, base_claim_regime)

        if resume:
            planned_keys = {
                (_solver_run_id(profile_name, spec, method), method)
                for method in planned_methods
            }
            if planned_keys and planned_keys.issubset(resume_keys):
                continue

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
        highs_existing_row = None
        for method in planned_methods:
            run_id = _solver_run_id(profile_name, spec, method)
            key = (run_id, method)
            if resume and key in resume_keys:
                if method == "highs_exact_bound":
                    highs_existing_row = existing_lookup.get(run_id)
                continue

            if method == "pyvrp_main":
                solver_outputs.append(
                    _safe_solver_call(
                        method,
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
            elif method == "ortools_main":
                solver_outputs.append(
                    _safe_solver_call(
                        method,
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
            elif method == "pyvrp_baseline":
                solver_outputs.append(
                    _safe_solver_call(
                        method,
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
            elif method == "highs_exact_bound":
                solver_outputs.append(
                    _safe_solver_call(
                        method,
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
        if highs_bound is None and highs_existing_row is not None:
            highs_bound = _sanitize_finite(highs_existing_row.get("best_bound"))

        exact_certified = False
        if base_claim_regime == "exact":
            if highs_out is not None:
                exact_certified = _is_optimal_status(highs_out.status)
            elif highs_existing_row is not None:
                exact_certified = str(highs_existing_row.get("claim_regime", "")) == "exact"

        claim_regime = base_claim_regime
        if base_claim_regime == "exact" and not exact_certified:
            claim_regime = "bound_gap"

        for out in solver_outputs:
            run_id = _solver_run_id(profile_name, spec, out.method)
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

    df_main_fresh = _rows_to_main_df(main_rows)
    df_routes_fresh = _rows_to_routes_df(route_rows)

    if resume:
        df_main = _merge_resume_df(
            existing=existing_main_df,
            fresh=df_main_fresh,
            dedup_keys=["run_id", "method"],
            columns=RESULTS_MAIN_COLUMNS,
        )
        df_routes = _merge_resume_df(
            existing=existing_routes_df,
            fresh=df_routes_fresh,
            dedup_keys=["run_id", "uav_id", "route_node_sequence"],
            columns=RESULTS_ROUTES_COLUMNS,
        )
    else:
        df_main = df_main_fresh
        df_routes = df_routes_fresh

    main_path.parent.mkdir(parents=True, exist_ok=True)
    routes_path.parent.mkdir(parents=True, exist_ok=True)
    df_main.to_csv(main_path, index=False)
    df_routes.to_csv(routes_path, index=False)

    sig_rows = compute_significance_results(df_main)
    df_sig = write_results_significance(sig_path, sig_rows)

    return df_main, df_routes, df_sig
