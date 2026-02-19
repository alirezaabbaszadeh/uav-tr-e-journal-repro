from __future__ import annotations

import argparse
import json
from pathlib import Path

from .manuscript_builder import compile_manuscript, generate_assets
from .manuscript_writer import write_sections


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build submit_v1 manuscript assets and PDF.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--campaign-root", default="outputs/campaigns")
    parser.add_argument("--submission-dir", default="output_submit_v1/submission")
    parser.add_argument("--manuscript-root", default="manuscript_submit_v1/tr_e")
    parser.add_argument("--outdir", default="output_submit_v1/manuscript")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[3]
    campaign_dir = root / args.campaign_root / args.campaign_id
    if not campaign_dir.exists() and Path(args.campaign_root).name == args.campaign_id:
        campaign_dir = root / args.campaign_root

    submission = root / args.submission_dir
    manuscript_root = root / args.manuscript_root
    outdir = root / args.outdir

    assets = generate_assets(campaign_dir=campaign_dir, generated_root=manuscript_root / "generated")
    sections = write_sections(
        campaign_id=args.campaign_id,
        evidence_csv=submission / f"EVIDENCE_INDEX_{args.campaign_id}.csv",
        sections_dir=manuscript_root / "sections",
    )
    pdf = compile_manuscript(root=root, manuscript_root=manuscript_root, outdir=outdir)

    print(
        json.dumps(
            {
                "campaign_id": args.campaign_id,
                "assets": [p.as_posix() for p in assets],
                "sections": [p.as_posix() for p in sections],
                "pdf": pdf.as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
