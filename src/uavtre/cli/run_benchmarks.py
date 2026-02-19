from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shlex
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from ..experiments.runner import run_experiment_matrix
from ..io.loaders import get_default_config_path, load_project_config

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


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
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--campaign-id", type=str, default=None)
    parser.add_argument("--campaign-root", type=str, default="outputs/campaigns")
    parser.add_argument("--stage-tag", type=str, default="default_stage")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


@contextmanager
def _locked_file(path: Path, mode: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode, encoding="utf-8", newline="") as f:
        if fcntl is not None:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield f
        finally:
            f.flush()
            os.fsync(f.fileno())
            if fcntl is not None:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _command_text() -> str:
    return " ".join(shlex.quote(x) for x in sys.argv)


def _collect_env_snapshot() -> dict:
    return {
        "generated_at_utc": _utc_now(),
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
    }


def _upsert_json_list_file(path: Path, root_key: str, row: dict) -> None:
    with _locked_file(path, "a+") as f:
        f.seek(0)
        raw = f.read().strip()
        if raw:
            payload = json.loads(raw)
        else:
            payload = {
                root_key: [],
                "created_at_utc": _utc_now(),
            }

        payload.setdefault(root_key, [])
        payload[root_key].append(row)
        payload["updated_at_utc"] = _utc_now()

        f.seek(0)
        f.truncate()
        json.dump(payload, f, indent=2)


def _append_command_log(path: Path, row: dict) -> None:
    with _locked_file(path, "a+") as f:
        f.seek(0)
        has_content = bool(f.read(1))
        f.seek(0, os.SEEK_END)

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp_utc",
                "campaign_id",
                "stage_tag",
                "profile",
                "shard_index",
                "num_shards",
                "resume",
                "command",
                "output",
                "benchmark_dir",
            ],
        )
        if not has_content:
            writer.writeheader()
        writer.writerow(row)


def _campaign_dir(args: argparse.Namespace) -> Path | None:
    if not args.campaign_id:
        return None
    return Path(args.campaign_root) / args.campaign_id


def _write_campaign_metadata_before(args: argparse.Namespace) -> None:
    camp_dir = _campaign_dir(args)
    if camp_dir is None:
        return

    env_path = camp_dir / "ENV_SNAPSHOT.json"
    if not env_path.exists():
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(json.dumps(_collect_env_snapshot(), indent=2), encoding="utf-8")

    run_plan_row = {
        "timestamp_utc": _utc_now(),
        "campaign_id": args.campaign_id,
        "stage_tag": args.stage_tag,
        "profile": args.profile,
        "shard_index": int(args.shard_index),
        "num_shards": int(args.num_shards),
        "resume": int(bool(args.resume)),
        "config": args.config,
        "profile_override": args.profile_override,
        "output": args.output,
        "benchmark_dir": args.benchmark_dir,
        "max_cases": int(args.max_cases),
    }
    _upsert_json_list_file(camp_dir / "RUN_PLAN.json", "runs", run_plan_row)

    _append_command_log(
        camp_dir / "COMMAND_LOG.csv",
        {
            "timestamp_utc": _utc_now(),
            "campaign_id": args.campaign_id,
            "stage_tag": args.stage_tag,
            "profile": args.profile,
            "shard_index": int(args.shard_index),
            "num_shards": int(args.num_shards),
            "resume": int(bool(args.resume)),
            "command": _command_text(),
            "output": args.output,
            "benchmark_dir": args.benchmark_dir,
        },
    )


def _write_campaign_metadata_after(args: argparse.Namespace, rows_main: int, rows_routes: int) -> None:
    camp_dir = _campaign_dir(args)
    if camp_dir is None:
        return

    manifest_row = {
        "timestamp_utc": _utc_now(),
        "campaign_id": args.campaign_id,
        "stage_tag": args.stage_tag,
        "profile": args.profile,
        "shard_index": int(args.shard_index),
        "num_shards": int(args.num_shards),
        "resume": int(bool(args.resume)),
        "output": args.output,
        "benchmark_dir": args.benchmark_dir,
        "rows_main": int(rows_main),
        "rows_routes": int(rows_routes),
    }
    _upsert_json_list_file(camp_dir / "CAMPAIGN_MANIFEST.json", "completed_runs", manifest_row)


def main() -> None:
    args = parse_args()

    if args.num_shards < 1:
        raise SystemExit("--num-shards must be >= 1")
    if args.shard_index < 0 or args.shard_index >= args.num_shards:
        raise SystemExit("--shard-index must satisfy 0 <= shard-index < num-shards")
    if args.stage_tag and not args.campaign_id:
        # Keep standalone runs simple; stage tags are campaign metadata.
        args.stage_tag = "default_stage"

    cfg = load_project_config(
        config_path=args.config,
        profile_name=args.profile,
        profile_override_path=args.profile_override,
    )

    _write_campaign_metadata_before(args)

    df_main, df_routes, _ = run_experiment_matrix(
        cfg=cfg,
        profile_name=args.profile,
        output_main_path=args.output,
        max_cases=max(0, int(args.max_cases)),
        freeze_benchmarks=True,
        benchmark_dir=args.benchmark_dir,
        shard_index=int(args.shard_index),
        num_shards=int(args.num_shards),
        resume=bool(args.resume),
    )

    _write_campaign_metadata_after(args, rows_main=len(df_main), rows_routes=len(df_routes))


if __name__ == "__main__":
    main()
