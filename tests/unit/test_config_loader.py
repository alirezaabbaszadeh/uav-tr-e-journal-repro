from __future__ import annotations

from pathlib import Path

from uavtre.io.loaders import load_project_config


ROOT = Path(__file__).resolve().parents[2]


def test_load_config_with_profiles() -> None:
    cfg = load_project_config(ROOT / "configs" / "base.json", profile_name="quick")

    assert cfg.tw.mode in {"soft", "hard"}
    assert cfg.tw.family in {"A", "B"}
    assert "quick" in cfg.profiles
    assert cfg.solver.heuristic_engine in {"ortools", "pyvrp"}
    assert "exact_n10_s" in cfg.solver.time_limits
