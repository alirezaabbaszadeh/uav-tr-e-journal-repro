from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build review package bundles.")
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["anonymous", "camera_ready"],
        help="Bundle type.",
    )
    parser.add_argument(
        "--campaign-root",
        type=str,
        default="outputs/campaigns",
        help="Root directory containing campaign folders.",
    )
    parser.add_argument(
        "--campaign-id",
        type=str,
        default=None,
        help="If set, package only artifacts from this campaign.",
    )
    return parser.parse_args()


def _resolve_rooted(path_like: str | Path) -> Path:
    path = Path(path_like)
    if path.is_absolute():
        return path
    return ROOT / path


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)


def _copy_tree(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def _write_anonymous_metadata(bundle_dir: Path) -> None:
    (bundle_dir / "README_ANONYMOUS.md").write_text(
        "# Anonymous Review Package\n\n"
        "This package removes author identifiers for double-anonymous review.\n"
        "All experiments can be reproduced using REPRODUCIBILITY.md and scripts/.\n",
        encoding="utf-8",
    )

    (bundle_dir / "CITATION.cff").write_text(
        "cff-version: 1.2.0\n"
        "message: \"If accepted, please cite the camera-ready DOI.\"\n"
        "title: \"Reliability-Aware Multi-UAV Pickup and Delivery\"\n"
        "type: software\n"
        "authors:\n"
        "  - family-names: \"Anonymous\"\n"
        "    given-names: \"Author\"\n",
        encoding="utf-8",
    )

    (bundle_dir / "LICENSE").write_text(
        "MIT License\n\n"
        "Copyright (c) 2026 Anonymous Authors\n\n"
        "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
        "of this software and associated documentation files (the \"Software\"), to deal\n"
        "in the Software without restriction, including without limitation the rights\n"
        "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
        "copies of the Software, and to permit persons to whom the Software is\n"
        "furnished to do so, subject to the following conditions:\n\n"
        "The above copyright notice and this permission notice shall be included in all\n"
        "copies or substantial portions of the Software.\n\n"
        "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n"
        "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
        "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n"
        "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n"
        "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n"
        "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n"
        "SOFTWARE.\n",
        encoding="utf-8",
    )

    anon_pyproject = bundle_dir / "pyproject.toml"
    if anon_pyproject.exists():
        text = anon_pyproject.read_text(encoding="utf-8")
        text = re.sub(
            r'\{ name = "[^"]+" \}',
            '{ name = "Anonymous Authors" }',
            text,
            count=1,
        )
        text = text.replace(
            "https://github.com/anonymous/uav_tr_e_project",
            "https://anonymous.invalid/repository",
        )
        anon_pyproject.write_text(text, encoding="utf-8")


def _write_camera_ready_metadata(bundle_dir: Path) -> None:
    src_citation = ROOT / "CITATION.cff"
    if src_citation.exists():
        _copy_file(src_citation, bundle_dir / "CITATION.cff")


def _copy_submission_artifacts(bundle_dir: Path, campaign_id: str) -> list[str]:
    src_submission = ROOT / "output" / "submission"
    dst_submission = bundle_dir / "output" / "submission"
    copied: list[str] = []
    if not src_submission.exists():
        return copied

    candidates = [
        f"claim_evidence_map_{campaign_id}.md",
        f"results_discussion_draft_{campaign_id}.md",
        f"next_steps_{campaign_id}.md",
        f"TABLE_FIGURE_INDEX_{campaign_id}.md",
        f"MANUSCRIPT_PACK_MANIFEST_{campaign_id}.json",
        "build_instructions.md",
        "tr_e_presubmission_checklist.md",
        "proposal_highlights.txt",
        "cover_letter_draft.txt",
    ]

    for name in candidates:
        src = src_submission / name
        if src.exists():
            dst = dst_submission / name
            _copy_file(src, dst)
            copied.append(str(dst.relative_to(bundle_dir)))

    return copied


def _copy_campaign_artifacts(
    bundle_dir: Path,
    campaign_dir: Path,
    campaign_id: str,
    include_logs: bool,
) -> dict:
    dst_campaign = bundle_dir / "outputs" / "campaigns" / campaign_id
    _copy_tree(campaign_dir, dst_campaign)

    if not include_logs:
        shutil.rmtree(dst_campaign / "logs", ignore_errors=True)

    bench_src = campaign_dir / "benchmarks"
    if bench_src.exists():
        _copy_tree(bench_src, bundle_dir / "benchmarks")

    copied_submission = _copy_submission_artifacts(bundle_dir, campaign_id)

    source_manifest = campaign_dir / "CAMPAIGN_MANIFEST.json"
    source_run_plan = campaign_dir / "RUN_PLAN.json"
    source_env = campaign_dir / "ENV_SNAPSHOT.json"
    source_cmd = campaign_dir / "COMMAND_LOG.csv"

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "campaign_id": campaign_id,
        "campaign_source": _display_path(campaign_dir),
        "campaign_source_files": {
            "CAMPAIGN_MANIFEST.json": source_manifest.exists(),
            "RUN_PLAN.json": source_run_plan.exists(),
            "ENV_SNAPSHOT.json": source_env.exists(),
            "COMMAND_LOG.csv": source_cmd.exists(),
        },
        "include_logs": int(include_logs),
        "campaign_files_json": len(list(campaign_dir.rglob("*.json"))),
        "campaign_files_csv": len(list(campaign_dir.rglob("*.csv"))),
        "bundle_campaign_json": len(list(dst_campaign.rglob("*.json"))),
        "bundle_campaign_csv": len(list(dst_campaign.rglob("*.csv"))),
        "submission_artifacts": copied_submission,
        "submission_artifact_count": len(copied_submission),
    }
    (bundle_dir / "BUNDLE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return manifest


def _copy_best_available_artifacts(bundle_dir: Path) -> dict:
    src_bench = ROOT / "benchmarks" / "frozen"
    dst_bench = bundle_dir / "benchmarks" / "frozen"

    src_out = ROOT / "outputs"
    dst_out = bundle_dir / "outputs"

    bench_candidates = [
        "main_table_full",
        "scalability_full",
        "main_table_v2_core",
        "scalability_v2_core",
        "main_table_v2",
        "scalability_v2",
        "main_table_v1",
        "scalability_v1",
    ]

    out_candidates = [
        "main_table_v2_core",
        "scalability_v2_core",
        "paper_v2_core",
        "main_table_v2",
        "scalability_v2",
        "paper_v2",
        "main_table_v1",
        "scalability_v1",
        "paper_v1",
    ]

    copied_bench_dirs = []
    for name in bench_candidates:
        src = src_bench / name
        if src.exists() and any(src.glob("*.json")):
            _copy_tree(src, dst_bench / name)
            copied_bench_dirs.append(name)

    if not copied_bench_dirs and src_bench.exists():
        _copy_tree(src_bench, dst_bench)
        copied_bench_dirs.append("root_fallback")

    copied_out_dirs = []
    for name in out_candidates:
        src = src_out / name
        if src.exists() and any(src.glob("*.csv")):
            _copy_tree(src, dst_out / name)
            copied_out_dirs.append(name)

    for csv_name in ["results_main.csv", "results_routes.csv", "results_significance.csv"]:
        _copy_file(src_out / csv_name, dst_out / csv_name)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "copied_benchmark_dirs": copied_bench_dirs,
        "copied_output_dirs": copied_out_dirs,
        "benchmark_json_count": len(list((bundle_dir / "benchmarks").rglob("*.json"))),
        "output_csv_count": len(list((bundle_dir / "outputs").rglob("*.csv"))),
    }
    (bundle_dir / "BUNDLE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return manifest


def build_bundle(mode: str, campaign_root: str | Path, campaign_id: str | None) -> Path:
    bundle_dir = ROOT / "submission" / mode
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    common_files = [
        "README.md",
        "LICENSE",
        "REPRODUCIBILITY.md",
        "CONTRIBUTING.md",
        "MANAGERIAL_INSIGHTS_TEMPLATE.md",
        "pyproject.toml",
        "requirements.txt",
        "requirements-lock.txt",
        "Dockerfile",
        ".gitignore",
    ]

    common_dirs = [
        "src",
        "configs",
        "scripts",
        "tests",
        ".github/workflows",
    ]

    for file_name in common_files:
        _copy_file(ROOT / file_name, bundle_dir / file_name)

    for dir_name in common_dirs:
        _copy_tree(ROOT / dir_name, bundle_dir / dir_name)

    if campaign_id:
        campaign_root_resolved = _resolve_rooted(campaign_root)
        campaign_dir = campaign_root_resolved / campaign_id
        if not campaign_dir.exists():
            raise FileNotFoundError(f"campaign directory not found: {campaign_dir}")
        _copy_campaign_artifacts(
            bundle_dir,
            campaign_dir,
            campaign_id,
            include_logs=(mode != "anonymous"),
        )
    else:
        _copy_best_available_artifacts(bundle_dir)

    if mode == "anonymous":
        _write_anonymous_metadata(bundle_dir)
    else:
        _write_camera_ready_metadata(bundle_dir)

    return bundle_dir


def main() -> None:
    args = parse_args()
    build_bundle(args.mode, campaign_root=args.campaign_root, campaign_id=args.campaign_id)


if __name__ == "__main__":
    main()
