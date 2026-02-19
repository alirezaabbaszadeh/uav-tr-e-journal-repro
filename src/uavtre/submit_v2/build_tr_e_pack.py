from __future__ import annotations

import argparse
import json
from pathlib import Path

from .portal_pack_builder import build_tr_e_upload_pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build submit_v2 TR-E upload pack zip.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--submission-dir", default="output_submit_v2/submission")
    parser.add_argument("--manuscript-outdir", default="output_submit_v2/manuscript")
    parser.add_argument("--manuscript-root", default="manuscript_submit_v2/tr_e")
    parser.add_argument("--pdf-variant", default="camera_ready", choices=["anonymous", "camera_ready"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[3]

    submission_dir = root / args.submission_dir
    manuscript_outdir = root / args.manuscript_outdir
    manuscript_root = root / args.manuscript_root

    audit = submission_dir / f"AUDIT_RECHECK_{args.campaign_id}.json"
    manifest = submission_dir / f"MANUSCRIPT_EXEC_MANIFEST_{args.campaign_id}.json"

    pack = build_tr_e_upload_pack(
        campaign_id=args.campaign_id,
        out_submission_dir=submission_dir,
        out_manuscript_dir=manuscript_outdir,
        manuscript_root=manuscript_root,
        audit_recheck_json=audit,
        manifest_json=manifest,
        pdf_variant=args.pdf_variant,
    )

    print(json.dumps({"pack": pack.as_posix()}, indent=2))


if __name__ == "__main__":
    main()
