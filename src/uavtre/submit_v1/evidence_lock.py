from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .state import sha256_file, utc_now_iso


@dataclass(frozen=True)
class EvidenceLockResult:
    passed: bool
    report_path: Path
    missing_files: list[str]


REQUIRED_CAMPAIGN_FILES = [
    "CAMPAIGN_MANIFEST.json",
    "RUN_PLAN.json",
    "ENV_SNAPSHOT.json",
    "COMMAND_LOG.csv",
]


def run_evidence_lock(campaign_dir: Path, report_path: Path) -> EvidenceLockResult:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    files: list[dict[str, object]] = []
    for name in REQUIRED_CAMPAIGN_FILES:
        path = campaign_dir / name
        if not path.exists():
            missing.append(name)
            files.append(
                {
                    "name": name,
                    "path": path.as_posix(),
                    "exists": False,
                    "sha256": None,
                    "bytes": 0,
                }
            )
            continue
        files.append(
            {
                "name": name,
                "path": path.as_posix(),
                "exists": True,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )

    report = {
        "generated_at_utc": utc_now_iso(),
        "campaign_dir": campaign_dir.as_posix(),
        "required_files": files,
        "missing_files": missing,
        "passed": len(missing) == 0,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return EvidenceLockResult(
        passed=len(missing) == 0,
        report_path=report_path,
        missing_files=missing,
    )
