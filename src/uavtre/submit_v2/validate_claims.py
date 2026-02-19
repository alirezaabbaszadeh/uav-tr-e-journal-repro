from __future__ import annotations

import argparse
import json
from pathlib import Path

from .claim_guard import validate_claims


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate submit_v2 claims against evidence index.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--submission-dir", default="output_submit_v2/submission")
    parser.add_argument("--manuscript-root", default="manuscript_submit_v2/tr_e")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[3]

    submission_dir = root / args.submission_dir
    evidence_csv = submission_dir / f"EVIDENCE_INDEX_{args.campaign_id}.csv"
    claim_yaml = submission_dir / f"CLAIM_REGISTRY_{args.campaign_id}.yaml"
    report = submission_dir / f"CLAIM_GUARD_REPORT_{args.campaign_id}.json"

    res = validate_claims(
        campaign_id=args.campaign_id,
        evidence_csv=evidence_csv,
        claim_registry_yaml=claim_yaml,
        report_path=report,
        manuscript_root=root / args.manuscript_root,
    )

    print(json.dumps({"passed": res.passed, "report": res.report_path.as_posix()}, indent=2))


if __name__ == "__main__":
    main()
