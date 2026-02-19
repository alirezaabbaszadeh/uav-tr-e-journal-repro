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
        "# Anonymous Review Package (submit_v2)\n\n"
        "This bundle is prepared for double-anonymous review.\n"
        "All identity markers should be removed from the manuscript PDF and the repository metadata.\n",
        encoding="utf-8",
    )

    # Anonymous CITATION stub (camera-ready DOI after acceptance).
    (bundle_dir / "CITATION.cff").write_text(
        "cff-version: 1.2.0\n"
        "message: \"Please cite the camera-ready DOI after acceptance.\"\n"
        "title: \"Reliability-Aware Multi-UAV Pickup and Delivery under Communication Risk and Soft Time Windows\"\n"
        "type: software\n"
        "authors:\n"
        "  - family-names: \"Anonymous\"\n"
        "    given-names: \"Author\"\n",
        encoding="utf-8",
    )

    # Overwrite submit_v2 submission metadata and cover letter inside the anonymous bundle so
    # leak scans pass, while keeping metadata TODO-free for tool stability.
    sub = bundle_dir / "output_submit_v2" / "submission"
    sub.mkdir(parents=True, exist_ok=True)

    # Template can remain TODO-based in anonymous bundles.
    (sub / "TR_E_METADATA_TEMPLATE.yaml").write_text(
        "title: TODO_TITLE\n"
        "running_title: TODO_RUNNING_TITLE\n"
        "abstract: TODO_ABSTRACT\n"
        "keywords: TODO_KEYWORDS\n"
        "authors: TODO_AUTHORS\n"
        "corresponding_author: TODO_CORRESPONDING_AUTHOR\n"
        "affiliations: TODO_AFFILIATIONS\n"
        "funding: TODO_FUNDING\n"
        "conflicts: TODO_CONFLICTS\n"
        "data_code_availability: TODO_DATA_CODE_AVAILABILITY\n",
        encoding="utf-8",
    )

    # Materialized metadata is anonymous-safe (no TODO tokens, no identity markers).
    (sub / "TR_E_METADATA.yaml").write_text(
        "title: Reliability-Aware Multi-UAV Pickup and Delivery under Communication Risk and Soft Time Windows\n"
        "running_title: Reliability-Aware Multi-UAV Logistics\n"
        "abstract: Anonymous review version. Results are evidence-locked to the provided campaign artifacts.\n"
        "keywords: UAV logistics; pickup and delivery; VRPTW; communication risk; soft time windows; reproducibility\n"
        "authors: Anonymous Author\n"
        "corresponding_author: Anonymous Author\n"
        "affiliations: Anonymous Affiliation\n"
        "funding: Withheld for anonymous review\n"
        "conflicts: Withheld for anonymous review\n"
        "data_code_availability: Withheld for anonymous review\n",
        encoding="utf-8",
    )

    (sub / "cover_letter.txt").write_text(
        "Dear Editor,\n\n"
        "Please consider our manuscript for Transportation Research Part E.\n\n"
        "Sincerely,\n"
        "Corresponding Author\n",
        encoding="utf-8",
    )

    # Remove identity from LaTeX source even in the camera-ready branch.
    main_tex = bundle_dir / "manuscript_submit_v2" / "tr_e" / "main.tex"
    if main_tex.exists():
        tex = main_tex.read_text(encoding="utf-8", errors="ignore")
        patt = re.compile(r"\\ifdefined\\ANON.*?\\fi", re.DOTALL)
        repl = (
            "\\ifdefined\\ANON\n"
            "  \\author{Anonymous Author}\n"
            "  \\address{}\n"
            "\\else\n"
            "  \\author{Corresponding Author}\n"
            "  \\address{Affiliation withheld for anonymous review}\n"
            "\\fi"
        )
        new_tex, n = patt.subn(lambda _m: repl, tex, count=1)
        if n == 1:
            main_tex.write_text(new_tex, encoding="utf-8")


def scan_identity_leaks(bundle_dir: Path) -> list[str]:
    patt = re.compile(r"(abbaszadeh|alireza|@gmail|@iau\.ir|orcid|github\.com/alireza)", re.IGNORECASE)
    leaks: list[str] = []

    scan_targets: list[Path] = [
        bundle_dir / "README.md",
        bundle_dir / "README_ANONYMOUS.md",
        bundle_dir / "CITATION.cff",
        bundle_dir / "output_submit_v2" / "submission",
        bundle_dir / "manuscript_submit_v2" / "tr_e",
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
        "manuscript_submit_v2",
    ]

    for name in common_files:
        _copy_file(root / name, bundle_dir / name)
    for name in common_dirs:
        _copy_tree(root / name, bundle_dir / name)

    # Campaign-locked evidence.
    _copy_tree(campaign_dir, bundle_dir / "outputs" / "campaigns" / campaign_id)
    _copy_tree(root / "output_submit_v2", bundle_dir / "output_submit_v2")

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
