from __future__ import annotations

import argparse
import json
from pathlib import Path

from .portal_pack_builder import build_tr_e_upload_pack, check_pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build submit_v1 TR-E upload pack.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--submission-dir", default="output_submit_v1/submission")
    parser.add_argument("--manuscript-out", default="output_submit_v1/manuscript")
    parser.add_argument("--manuscript-root", default="manuscript_submit_v1/tr_e")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[3]

    submission = root / args.submission_dir
    pack = build_tr_e_upload_pack(
        campaign_id=args.campaign_id,
        out_submission_dir=submission,
        out_manuscript_dir=root / args.manuscript_out,
        manuscript_root=root / args.manuscript_root,
        audit_recheck_json=submission / f"AUDIT_RECHECK_{args.campaign_id}.json",
        manifest_json=submission / f"MANUSCRIPT_EXEC_MANIFEST_{args.campaign_id}.json",
    )
    check = check_pack(pack, args.campaign_id)
    print(json.dumps(check, indent=2))
    if not check.get("passed", False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
