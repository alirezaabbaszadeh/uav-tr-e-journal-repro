from __future__ import annotations

import argparse

from ..experiments.runner import run_experiment_matrix
from ..io.loaders import get_default_config_path, load_project_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run UAV TR-E experiment matrix.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(get_default_config_path()),
        help="Path to base config JSON.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/results_main.csv",
        help="Path for results_main.csv.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="main_table",
        help="Profile name: quick | main_table | scalability.",
    )
    parser.add_argument(
        "--profile-override",
        type=str,
        default=None,
        help="Optional profile JSON override.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Optional hard cap for number of scenario cases.",
    )
    parser.add_argument(
        "--benchmark-dir",
        type=str,
        default="benchmarks/frozen",
        help="Frozen benchmark directory (read if files exist).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_project_config(
        config_path=args.config,
        profile_name=args.profile,
        profile_override_path=args.profile_override,
    )

    run_experiment_matrix(
        cfg=cfg,
        profile_name=args.profile,
        output_main_path=args.output,
        max_cases=max(0, int(args.max_cases)),
        freeze_benchmarks=False,
        benchmark_dir=args.benchmark_dir,
    )


if __name__ == "__main__":
    main()
