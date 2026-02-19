#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate campaign-scoped manuscript package integrity.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--submission-dir", default="output/submission")
    parser.add_argument("--anonymous-dir", default="submission/anonymous")
    parser.add_argument("--camera-ready-dir", default="submission/camera_ready")
    return parser.parse_args()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_exists(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"missing file: {path.as_posix()}")


def _check_no_pattern(path: Path, pattern: str, errors: list[str], allow_if_contains: str | None = None) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    if pattern in text:
        if allow_if_contains and allow_if_contains in path.as_posix():
            return
        errors.append(f"forbidden pattern '{pattern}' in {path.as_posix()}")


def _validate_bundle(bundle_dir: Path, campaign_id: str, errors: list[str]) -> None:
    manifest_path = bundle_dir / "BUNDLE_MANIFEST.json"
    _check_exists(manifest_path, errors)
    if not manifest_path.exists():
        return

    manifest = _load_json(manifest_path)
    if str(manifest.get("campaign_id")) != campaign_id:
        errors.append(
            f"bundle campaign mismatch in {manifest_path.as_posix()}: "
            f"{manifest.get('campaign_id')} != {campaign_id}"
        )

    if int(manifest.get("submission_artifact_count", 0)) < 8:
        errors.append(f"bundle missing submission artifacts in {manifest_path.as_posix()}")

    for rel in manifest.get("submission_artifacts", []):
        path = bundle_dir / rel
        _check_exists(path, errors)


def main() -> None:
    args = parse_args()
    campaign_id = args.campaign_id

    submission_dir = Path(args.submission_dir)
    anonymous_dir = Path(args.anonymous_dir)
    camera_ready_dir = Path(args.camera_ready_dir)

    required = [
        submission_dir / f"claim_evidence_map_{campaign_id}.md",
        submission_dir / f"results_discussion_draft_{campaign_id}.md",
        submission_dir / f"next_steps_{campaign_id}.md",
        submission_dir / f"TABLE_FIGURE_INDEX_{campaign_id}.md",
        submission_dir / f"MANUSCRIPT_PACK_MANIFEST_{campaign_id}.json",
        submission_dir / f"RELEASE_NOTE_{campaign_id}.md",
        submission_dir / "build_instructions.md",
        submission_dir / "tr_e_presubmission_checklist.md",
        submission_dir / "proposal_highlights.txt",
        submission_dir / "cover_letter_draft.txt",
    ]

    errors: list[str] = []

    for path in required:
        _check_exists(path, errors)

    # No stale names in active submission root.
    for path in submission_dir.glob("*"):
        if path.is_file() and "journal_core" in path.name:
            errors.append(f"stale filename in submission root: {path.as_posix()}")

    manifest_path = submission_dir / f"MANUSCRIPT_PACK_MANIFEST_{campaign_id}.json"
    if manifest_path.exists():
        manifest = _load_json(manifest_path)
        if str(manifest.get("campaign_id")) != campaign_id:
            errors.append("manifest campaign_id mismatch")
        audit = manifest.get("audit_summary", {})
        if not bool(audit.get("overall_pass", False)):
            errors.append("audit_summary.overall_pass is false")
        if str(manifest.get("campaign_root", "")).startswith("/"):
            errors.append("manifest campaign_root must be relative")
        if str(manifest.get("campaign_dir", "")).startswith("/"):
            errors.append("manifest campaign_dir must be relative")
        if str(manifest.get("audit_json", "")).startswith("/"):
            errors.append("manifest audit_json must be relative")

    # No absolute host paths or stale keywords in active artifacts.
    active_files = [
        submission_dir / f"claim_evidence_map_{campaign_id}.md",
        submission_dir / f"results_discussion_draft_{campaign_id}.md",
        submission_dir / f"next_steps_{campaign_id}.md",
        submission_dir / f"TABLE_FIGURE_INDEX_{campaign_id}.md",
        submission_dir / f"MANUSCRIPT_PACK_MANIFEST_{campaign_id}.json",
        submission_dir / f"RELEASE_NOTE_{campaign_id}.md",
        submission_dir / "build_instructions.md",
        anonymous_dir / "BUNDLE_MANIFEST.json",
        camera_ready_dir / "BUNDLE_MANIFEST.json",
        anonymous_dir / "output" / "submission" / f"claim_evidence_map_{campaign_id}.md",
        anonymous_dir / "output" / "submission" / f"RELEASE_NOTE_{campaign_id}.md",
        anonymous_dir / "output" / "submission" / "build_instructions.md",
        camera_ready_dir / "output" / "submission" / f"claim_evidence_map_{campaign_id}.md",
        camera_ready_dir / "output" / "submission" / f"RELEASE_NOTE_{campaign_id}.md",
        camera_ready_dir / "output" / "submission" / "build_instructions.md",
    ]

    for path in active_files:
        _check_no_pattern(path, "/home/", errors)
        _check_no_pattern(path, "/mnt/", errors)
        _check_no_pattern(path, "journal_core", errors)

    _validate_bundle(anonymous_dir, campaign_id, errors)
    _validate_bundle(camera_ready_dir, campaign_id, errors)

    result = {
        "campaign_id": campaign_id,
        "checks": len(required) + 7,
        "errors": errors,
        "passed": len(errors) == 0,
    }
    print(json.dumps(result, indent=2))

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
