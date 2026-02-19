from __future__ import annotations

import json
from pathlib import Path

from uavtre.experiments.runner import _iter_specs
from uavtre.io.loaders import load_project_config


ROOT = Path(__file__).resolve().parents[2]


def test_shard_partition_is_disjoint_and_complete(tmp_path: Path) -> None:
    override = {
        "profiles": {
            "main_table": {
                "seeds": [1, 2, 3],
                "sizes": [10],
                "include_scalability": False,
                "bs_counts": [4],
                "deltas_min": [10],
                "edge_samples": [10],
                "lambda_out": [0.5],
                "lambda_tw": [1.0],
                "max_cases": 0,
            }
        }
    }
    override_path = tmp_path / "override.json"
    override_path.write_text(json.dumps(override), encoding="utf-8")

    cfg = load_project_config(
        config_path=ROOT / "configs" / "base.json",
        profile_name="main_table",
        profile_override_path=override_path,
    )

    all_specs = list(_iter_specs(cfg, "main_table", num_shards=1, shard_index=0))
    shard0 = list(_iter_specs(cfg, "main_table", num_shards=2, shard_index=0))
    shard1 = list(_iter_specs(cfg, "main_table", num_shards=2, shard_index=1))

    ids_all = {s.run_id for s in all_specs}
    ids_0 = {s.run_id for s in shard0}
    ids_1 = {s.run_id for s in shard1}

    assert ids_0.isdisjoint(ids_1)
    assert ids_0 | ids_1 == ids_all
