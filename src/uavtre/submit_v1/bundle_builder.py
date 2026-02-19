from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)


def _copy_tree(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def _write_anonymous_overrides(bundle_dir: Path) -> None:
    (bundle_dir / "README_ANONYMOUS.md").write_text(
        "# Anonymous Review Package (submit_v1)\n\n"
        "This bundle removes author identifiers for double-anonymous review.\n",
        encoding="utf-8",
    )
    (bundle_dir / "CITATION.cff").write_text(
        "cff-version: 1.2.0\n"
        "message: \"Please cite the camera-ready DOI after acceptance.\"\n"
        "title: \"Reliability-Aware Multi-UAV Pickup and Delivery\"\n"
        "type: software\n"
        "authors:\n"
        "  - family-names: \"Anonymous\"\n"
        "    given-names: \"Author\"\n",
        encoding="utf-8",
    )


def scan_identity_leaks(bundle_dir: Path) -> list[str]:
    patt = re.compile(r"(abbaszadeh|alireza|@gmail|orcid)", re.IGNORECASE)
    leaks: list[str] = []

    scan_targets: list[Path] = [
        bundle_dir / "README.md",
        bundle_dir / "README_ANONYMOUS.md",
        bundle_dir / "CITATION.cff",
        bundle_dir / "output_submit_v1" / "submission",
    ]

    files: list[Path] = []
    for target in scan_targets:
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            for path in target.rglob("*"):
                if path.is_file():
                    files.append(path)

    for path in files:
        if path.suffix.lower() in {".json", ".csv", ".png", ".jpg", ".pdf", ".zip", ".py"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if patt.search(text):
            leaks.append(path.as_posix())
    return leaks


def _build_single_bundle(
    *,
    mode: str,
    root: Path,
    campaign_dir: Path,
    campaign_id: str,
    out_submission_dir: Path,
    bundles_root: Path,
) -> Path:
    bundle_dir = bundles_root / mode
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    common_files = [
        "README.md",
        "REPRODUCIBILITY.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "MANAGERIAL_INSIGHTS_TEMPLATE.md",
        "requirements.txt",
        "requirements-lock.txt",
        "pyproject.toml",
        "Dockerfile",
    ]
    common_dirs = [
        "src",
        "configs",
        "scripts",
        "tests",
        "manuscript_submit_v1",
    ]

    for name in common_files:
        _copy_file(root / name, bundle_dir / name)
    for name in common_dirs:
        _copy_tree(root / name, bundle_dir / name)

    _copy_tree(campaign_dir, bundle_dir / "outputs" / "campaigns" / campaign_id)
    _copy_tree(root / "output_submit_v1", bundle_dir / "output_submit_v1")

    if mode == "anonymous":
        _write_anonymous_overrides(bundle_dir)
    else:
        _copy_file(root / "CITATION.cff", bundle_dir / "CITATION.cff")

    leaks: list[str] = []
    if mode == "anonymous":
        leaks = scan_identity_leaks(bundle_dir)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "campaign_id": campaign_id,
        "campaign_source": campaign_dir.as_posix(),
        "submission_source": out_submission_dir.as_posix(),
        "text_file_count": len(list(bundle_dir.rglob("*.md"))) + len(list(bundle_dir.rglob("*.txt"))),
        "campaign_json_count": len(list((bundle_dir / "outputs" / "campaigns" / campaign_id).rglob("*.json"))),
        "campaign_csv_count": len(list((bundle_dir / "outputs" / "campaigns" / campaign_id).rglob("*.csv"))),
        "identity_leaks": leaks,
        "passed": len(leaks) == 0,
    }
    (bundle_dir / "BUNDLE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if mode == "anonymous" and leaks:
        raise RuntimeError(f"anonymous bundle contains identity markers: {leaks[:3]}")

    return bundle_dir


def build_bundles(
    *,
    root: Path,
    campaign_dir: Path,
    campaign_id: str,
    out_submission_dir: Path,
    bundles_root: Path,
    bundle_mode: str,
) -> list[Path]:
    bundles_root.mkdir(parents=True, exist_ok=True)

    modes = [bundle_mode]
    if bundle_mode == "both":
        modes = ["anonymous", "camera_ready"]

    written: list[Path] = []
    for mode in modes:
        written.append(
            _build_single_bundle(
                mode=mode,
                root=root,
                campaign_dir=campaign_dir,
                campaign_id=campaign_id,
                out_submission_dir=out_submission_dir,
                bundles_root=bundles_root,
            )
        )
    return written
