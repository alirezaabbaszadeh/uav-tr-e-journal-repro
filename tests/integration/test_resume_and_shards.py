from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from uavtre.experiments.runner import run_experiment_matrix
from uavtre.io.loaders import load_project_config


ROOT = Path(__file__).resolve().parents[2]


def _tiny_override() -> dict:
    return {
        "solver": {
            "time_limits": {
                "exact_n10_s": 1,
                "bound_n20_s": 1,
                "bound_n40_s": 1,
                "scalability_n80_s": 1,
                "heuristic_default_s": 1,
            },
            "pyvrp_max_runtime_s": 1,
            "pyvrp_max_iterations": 100,
        },
        "profiles": {
            "main_table": {
                "seeds": [1, 2],
                "sizes": [10],
                "include_scalability": False,
                "bs_counts": [4],
                "deltas_min": [10],
                "edge_samples": [10],
                "lambda_out": [0.5],
                "lambda_tw": [1.0],
                "max_cases": 0,
            }
        },
    }


def test_sharded_union_matches_nonsharded_keys(tmp_path: Path) -> None:
    override_path = tmp_path / "override.json"
    override_path.write_text(json.dumps(_tiny_override()), encoding="utf-8")

    cfg = load_project_config(
        config_path=ROOT / "configs" / "base.json",
        profile_name="main_table",
        profile_override_path=override_path,
    )

    full_main, _, _ = run_experiment_matrix(
        cfg=cfg,
        profile_name="main_table",
        output_main_path=tmp_path / "full" / "results_main.csv",
        freeze_benchmarks=True,
        benchmark_dir=tmp_path / "frozen_full",
        num_shards=1,
        shard_index=0,
    )

    shard0_main, _, _ = run_experiment_matrix(
        cfg=cfg,
        profile_name="main_table",
        output_main_path=tmp_path / "shard0" / "results_main.csv",
        freeze_benchmarks=True,
        benchmark_dir=tmp_path / "frozen_sharded",
        num_shards=2,
        shard_index=0,
    )
    shard1_main, _, _ = run_experiment_matrix(
        cfg=cfg,
        profile_name="main_table",
        output_main_path=tmp_path / "shard1" / "results_main.csv",
        freeze_benchmarks=True,
        benchmark_dir=tmp_path / "frozen_sharded",
        num_shards=2,
        shard_index=1,
    )

    union = pd.concat([shard0_main, shard1_main], ignore_index=True)
    union_keys = {
        (str(r["run_id"]), str(r["method"]))
        for _, r in union[["run_id", "method"]].dropna().iterrows()
    }
    full_keys = {
        (str(r["run_id"]), str(r["method"]))
        for _, r in full_main[["run_id", "method"]].dropna().iterrows()
    }

    assert union_keys == full_keys


def test_resume_skips_existing_rows(tmp_path: Path) -> None:
    override_path = tmp_path / "override.json"
    override_path.write_text(json.dumps(_tiny_override()), encoding="utf-8")

    cfg = load_project_config(
        config_path=ROOT / "configs" / "base.json",
        profile_name="main_table",
        profile_override_path=override_path,
    )

    out_path = tmp_path / "resume" / "results_main.csv"

    first_main, _, _ = run_experiment_matrix(
        cfg=cfg,
        profile_name="main_table",
        output_main_path=out_path,
        freeze_benchmarks=True,
        benchmark_dir=tmp_path / "frozen",
        num_shards=1,
        shard_index=0,
        resume=False,
    )

    second_main, _, _ = run_experiment_matrix(
        cfg=cfg,
        profile_name="main_table",
        output_main_path=out_path,
        freeze_benchmarks=True,
        benchmark_dir=tmp_path / "frozen",
        num_shards=1,
        shard_index=0,
        resume=True,
    )

    assert len(second_main) == len(first_main)
    keys = second_main[["run_id", "method"]].dropna()
    assert len(keys.drop_duplicates()) == len(keys)
