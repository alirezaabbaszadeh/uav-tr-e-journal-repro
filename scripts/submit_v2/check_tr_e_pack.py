#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ensure_src_on_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    sys.path.insert(0, src.as_posix())
    return root


ROOT = _ensure_src_on_path()

from uavtre.submit_v2.portal_pack_builder import check_pack  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check submit_v2 TR-E upload pack completeness.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument(
        "--pack",
        default=None,
        help="Optional explicit pack path. Defaults to output_submit_v2/submission/TR_E_UPLOAD_PACK_<id>.zip",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.pack:
        pack = Path(args.pack)
        if not pack.is_absolute():
            pack = ROOT / pack
    else:
        pack = ROOT / "output_submit_v2" / "submission" / f"TR_E_UPLOAD_PACK_{args.campaign_id}.zip"

    result = check_pack(pack, args.campaign_id)
    print(json.dumps(result, indent=2))
    if not result.get("passed", False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
