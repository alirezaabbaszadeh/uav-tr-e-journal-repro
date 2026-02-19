from __future__ import annotations

import argparse
import json
from pathlib import Path

from .orchestrator import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run submit_v2 end-to-end pipeline (campaign-locked, no rerun).")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--campaign-root", default="outputs/campaigns")
    parser.add_argument("--mode", default="full", choices=["full"])
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[3]

    ctx = run_pipeline(
        root=root,
        campaign_id=args.campaign_id,
        campaign_root=args.campaign_root,
        mode=args.mode,
        resume=args.resume,
        run_id=args.run_id,
    )

    print(
        json.dumps(
            {
                "campaign_id": args.campaign_id,
                "run_id": ctx.run_id,
                "state": ctx.state_path.as_posix(),
                "out_submission": ctx.out_submit_dir.as_posix(),
                "out_manuscript": ctx.out_manuscript_dir.as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
