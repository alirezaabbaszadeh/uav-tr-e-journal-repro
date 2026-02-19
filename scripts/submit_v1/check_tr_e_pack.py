#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from uavtre.submit_v1.portal_pack_builder import check_pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check submit_v1 TR-E upload pack completeness.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument(
        "--pack",
        default=None,
        help="Optional explicit pack path. Defaults to output_submit_v1/submission/TR_E_UPLOAD_PACK_<id>.zip",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.pack:
        pack = Path(args.pack)
        if not pack.is_absolute():
            pack = root / pack
    else:
        pack = root / "output_submit_v1" / "submission" / f"TR_E_UPLOAD_PACK_{args.campaign_id}.zip"

    result = check_pack(pack, args.campaign_id)
    print(json.dumps(result, indent=2))
    if not result.get("passed", False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
