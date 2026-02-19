#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate GitHub release assets from manuscript pack.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--tag", default="v1.0.0-journal-repro")
    parser.add_argument("--submission-dir", default="output/submission")
    return parser.parse_args()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> None:
    args = parse_args()
    submission_dir = ROOT / args.submission_dir

    release_note = submission_dir / f"RELEASE_NOTE_{args.campaign_id}.md"
    pack_manifest = submission_dir / f"MANUSCRIPT_PACK_MANIFEST_{args.campaign_id}.json"
    claim_map = submission_dir / f"claim_evidence_map_{args.campaign_id}.md"
    table_index = submission_dir / f"TABLE_FIGURE_INDEX_{args.campaign_id}.md"
    discussion = submission_dir / f"results_discussion_draft_{args.campaign_id}.md"
    next_steps = submission_dir / f"next_steps_{args.campaign_id}.md"
    build_instructions = submission_dir / "build_instructions.md"
    checklist = submission_dir / "tr_e_presubmission_checklist.md"
    highlights = submission_dir / "proposal_highlights.txt"

    required = [
        release_note,
        pack_manifest,
        claim_map,
        table_index,
        discussion,
        next_steps,
        build_instructions,
        checklist,
        highlights,
    ]

    missing = [p for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("missing required files: " + ", ".join(p.as_posix() for p in missing))

    manifest = json.loads(pack_manifest.read_text(encoding="utf-8"))

    sha_out = submission_dir / f"ARTIFACT_SHA256_{args.campaign_id}.txt"
    with sha_out.open("w", encoding="utf-8") as f:
        for p in required:
            rel = p.relative_to(ROOT).as_posix()
            f.write(f"{_sha256(p)}  {rel}\n")

    release_body_out = submission_dir / f"GITHUB_RELEASE_BODY_{args.tag}.md"
    release_body = f"""# {args.tag}

Campaign-locked TR-E manuscript package release.

## Locked Campaign
- Campaign ID: `{args.campaign_id}`
- Audit summary: `{manifest.get('audit_summary', {})}`

## Included Artifacts
- `output/submission/RELEASE_NOTE_{args.campaign_id}.md`
- `output/submission/claim_evidence_map_{args.campaign_id}.md`
- `output/submission/results_discussion_draft_{args.campaign_id}.md`
- `output/submission/next_steps_{args.campaign_id}.md`
- `output/submission/TABLE_FIGURE_INDEX_{args.campaign_id}.md`
- `output/submission/MANUSCRIPT_PACK_MANIFEST_{args.campaign_id}.json`
- `output/submission/ARTIFACT_SHA256_{args.campaign_id}.txt`

## Policy Lock
- `N<=10`: exact-with-certificate
- `N=20/40`: bound-gap
- `N=80`: scalability-only

## Notes
- CPU-sharded execution is canonical for this solver stack.
- Anonymous/camera-ready bundles are campaign-scoped and reproducible.
"""
    release_body_out.write_text(release_body, encoding="utf-8")

    push_out = submission_dir / f"PUSH_INSTRUCTIONS_{args.tag}.md"
    push_text = f"""# Push Instructions ({args.tag})

No git remote is currently configured in this repository.

## 1) Add remote
```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
```

## 2) Push branch and tag
```bash
git push -u origin main
git push origin {args.tag}
```

## 3) Create GitHub release
Use this body:
- `output/submission/GITHUB_RELEASE_BODY_{args.tag}.md`

Optional checksum attachment reference:
- `output/submission/ARTIFACT_SHA256_{args.campaign_id}.txt`
"""
    push_out.write_text(push_text, encoding="utf-8")

    print(sha_out)
    print(release_body_out)
    print(push_out)


if __name__ == "__main__":
    main()
