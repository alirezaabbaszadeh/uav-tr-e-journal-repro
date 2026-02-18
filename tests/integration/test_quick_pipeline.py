from __future__ import annotations

from pathlib import Path

import pandas as pd

from uavtre.experiments.runner import run_experiment_matrix
from uavtre.io.loaders import load_project_config


ROOT = Path(__file__).resolve().parents[2]


def test_quick_pipeline_outputs(tmp_path: Path) -> None:
    cfg = load_project_config(ROOT / "configs" / "base.json", profile_name="quick")
    out = tmp_path / "results_main.csv"

    df_main, df_routes, df_sig = run_experiment_matrix(
        cfg=cfg,
        profile_name="quick",
        output_main_path=out,
        max_cases=1,
        freeze_benchmarks=True,
        benchmark_dir=tmp_path / "frozen",
    )

    assert (tmp_path / "results_main.csv").exists()
    assert (tmp_path / "results_routes.csv").exists()
    assert (tmp_path / "results_significance.csv").exists()

    # Main results must include quick profile rows.
    assert not df_main.empty
    assert set(df_main["profile"]) == {"quick"}

    # Route and significance tables can be empty when optional solvers are unavailable.
    assert isinstance(df_routes, pd.DataFrame)
    assert isinstance(df_sig, pd.DataFrame)
