from __future__ import annotations

import argparse
import json
from pathlib import Path

from .claim_guard import validate_claims


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate submit_v1 claims against evidence index.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--submission-dir", default="output_submit_v1/submission")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    submission = Path(args.submission_dir)
    res = validate_claims(
        campaign_id=args.campaign_id,
        evidence_csv=submission / f"EVIDENCE_INDEX_{args.campaign_id}.csv",
        claim_registry_yaml=submission / f"CLAIM_REGISTRY_{args.campaign_id}.yaml",
        report_path=submission / f"CLAIM_GUARD_REPORT_{args.campaign_id}.json",
    )
    print(
        json.dumps(
            {
                "campaign_id": args.campaign_id,
                "passed": res.passed,
                "report": res.report_path.as_posix(),
                "unresolved": res.unresolved,
                "policy_violations": res.policy_violations,
            },
            indent=2,
        )
    )
    if not res.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
