from __future__ import annotations

import argparse

from ..experiments.runner import run_experiment_matrix
from ..io.loaders import get_default_config_path, load_project_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate/refresh frozen benchmarks and run experiment profile."
    )
    parser.add_argument("--config", type=str, default=str(get_default_config_path()))
    parser.add_argument("--profile", type=str, default="main_table")
    parser.add_argument("--output", type=str, default="outputs/results_main.csv")
    parser.add_argument("--benchmark-dir", type=str, default="benchmarks/frozen")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--profile-override", type=str, default=None)
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
        freeze_benchmarks=True,
        benchmark_dir=args.benchmark_dir,
    )


if __name__ == "__main__":
    main()
