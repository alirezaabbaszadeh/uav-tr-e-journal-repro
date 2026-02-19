from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bundle_builder import build_bundles


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build submit_v2 reviewer bundles (anonymous/camera_ready).")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--campaign-root", default="outputs/campaigns")
    parser.add_argument("--submission-dir", default="output_submit_v2/submission")
    parser.add_argument("--bundles-root", default="submission_submit_v2")
    parser.add_argument("--bundle", default="both", choices=["anonymous", "camera_ready", "both"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[3]

    campaign_dir = root / args.campaign_root / args.campaign_id
    if not campaign_dir.exists() and Path(args.campaign_root).name == args.campaign_id:
        campaign_dir = root / args.campaign_root

    written = build_bundles(
        root=root,
        campaign_dir=campaign_dir,
        campaign_id=args.campaign_id,
        out_submission_dir=root / args.submission_dir,
        bundles_root=root / args.bundles_root,
        bundle_mode=args.bundle,
    )

    print(json.dumps({"bundles": [p.as_posix() for p in written]}, indent=2))


if __name__ == "__main__":
    main()
