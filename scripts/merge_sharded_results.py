#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from uavtre.experiments.significance import compute_significance_results
from uavtre.io.export_csv import write_results_significance
from uavtre.io.schema import RESULTS_MAIN_COLUMNS, RESULTS_ROUTES_COLUMNS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge sharded benchmark outputs.")
    parser.add_argument("--shards-root", required=True, help="Directory containing shard_* folders.")
    parser.add_argument("--output-dir", required=True, help="Merged output directory.")
    parser.add_argument(
        "--require-shards",
        type=int,
        default=1,
        help="Minimum shard count expected.",
    )
    return parser.parse_args()


def _ensure_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df[cols]


def main() -> None:
    args = parse_args()
    shards_root = Path(args.shards_root)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    shard_dirs = sorted([p for p in shards_root.glob("shard_*") if p.is_dir()])
    if len(shard_dirs) < int(args.require_shards):
        raise SystemExit(
            f"expected at least {args.require_shards} shard dirs under {shards_root}, got {len(shard_dirs)}"
        )

    main_parts: list[pd.DataFrame] = []
    route_parts: list[pd.DataFrame] = []

    for shard in shard_dirs:
        m = shard / "results_main.csv"
        r = shard / "results_routes.csv"
        if m.exists():
            main_parts.append(pd.read_csv(m))
        if r.exists():
            route_parts.append(pd.read_csv(r))

    if not main_parts:
        raise SystemExit(f"no shard results_main.csv found under {shards_root}")

    merged_main = _ensure_columns(pd.concat(main_parts, ignore_index=True), RESULTS_MAIN_COLUMNS)
    merged_main = merged_main.drop_duplicates(subset=["run_id", "method"], keep="first")
    merged_main.to_csv(out_dir / "results_main.csv", index=False)

    if route_parts:
        merged_routes = _ensure_columns(pd.concat(route_parts, ignore_index=True), RESULTS_ROUTES_COLUMNS)
        merged_routes = merged_routes.drop_duplicates(
            subset=["run_id", "uav_id", "route_node_sequence"],
            keep="first",
        )
    else:
        merged_routes = pd.DataFrame(columns=RESULTS_ROUTES_COLUMNS)
    merged_routes.to_csv(out_dir / "results_routes.csv", index=False)

    sig_rows = compute_significance_results(merged_main)
    write_results_significance(out_dir / "results_significance.csv", sig_rows)

    print(
        f"merged shards={len(shard_dirs)} rows_main={len(merged_main)} rows_routes={len(merged_routes)}"
    )


if __name__ == "__main__":
    main()
