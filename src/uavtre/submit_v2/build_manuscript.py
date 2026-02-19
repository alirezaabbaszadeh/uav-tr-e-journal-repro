from __future__ import annotations

import argparse
import json
from pathlib import Path

from .manuscript_builder import compile_manuscript, generate_assets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build submit_v2 manuscript assets and PDF(s).")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--campaign-root", default="outputs/campaigns")
    parser.add_argument("--manuscript-root", default="manuscript_submit_v2/tr_e")
    parser.add_argument("--outdir", default="output_submit_v2/manuscript")
    parser.add_argument(
        "--variant",
        default="both",
        choices=["anonymous", "camera_ready", "both"],
        help="Which PDF variant(s) to build.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[3]

    campaign_dir = root / args.campaign_root / args.campaign_id
    if not campaign_dir.exists() and Path(args.campaign_root).name == args.campaign_id:
        campaign_dir = root / args.campaign_root

    manuscript_root = root / args.manuscript_root
    outdir = root / args.outdir

    assets = generate_assets(campaign_dir=campaign_dir, manuscript_root=manuscript_root)

    built: dict[str, str] = {}
    variants = [args.variant]
    if args.variant == "both":
        variants = ["anonymous", "camera_ready"]

    for v in variants:
        pdf = compile_manuscript(
            root=root,
            manuscript_root=manuscript_root,
            outdir=outdir / v,
            variant=v,
        )
        built[v] = pdf.as_posix()

    print(
        json.dumps(
            {
                "campaign_id": args.campaign_id,
                "assets": [p.as_posix() for p in assets],
                "pdfs": built,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
