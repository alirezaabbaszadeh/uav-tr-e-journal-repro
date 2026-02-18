from __future__ import annotations

import argparse
import itertools
from pathlib import Path

from ..io.schema import ScenarioSpec
from ..io.loaders import get_default_config_path, load_project_config
from ..scenario import generate_scenario, save_frozen_instance, scenario_instance_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze deterministic benchmark instances only.")
    parser.add_argument("--config", type=str, default=str(get_default_config_path()))
    parser.add_argument("--profile", type=str, default="main_table")
    parser.add_argument("--benchmark-dir", type=str, default="benchmarks/frozen")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--profile-override", type=str, default=None)
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    return parser.parse_args()


def _iter_specs(cfg, profile_name: str, max_cases: int = 0):
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


def main() -> None:
    args = parse_args()
    cfg = load_project_config(
        config_path=args.config,
        profile_name=args.profile,
        profile_override_path=args.profile_override,
    )

    benchmark_root = Path(args.benchmark_dir)
    benchmark_root.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    for spec in _iter_specs(cfg, profile_name=args.profile, max_cases=max(0, int(args.max_cases))):
        scenario_id = scenario_instance_id(spec)
        path = benchmark_root / f"{scenario_id}.json"
        if path.exists() and not args.force:
            skipped += 1
            continue

        scenario = generate_scenario(cfg, spec)
        save_frozen_instance(path, spec, scenario)
        written += 1

    print(f"written={written} skipped={skipped} total={written + skipped}")


if __name__ == "__main__":
    main()
