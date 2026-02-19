#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate campaign-scoped release note.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--campaign-root", default="outputs/campaigns")
    parser.add_argument("--submission-dir", default="output/submission")
    parser.add_argument("--audit-json", default=None)
    return parser.parse_args()


def _pick(df: pd.DataFrame, **filters) -> pd.Series:
    q = df
    for k, v in filters.items():
        q = q[q[k] == v]
    if q.empty:
        raise ValueError(f"missing row for filters={filters}")
    return q.iloc[0]


def main() -> None:
    args = parse_args()

    campaign_root = Path(args.campaign_root)
    if not campaign_root.is_absolute():
        campaign_root = ROOT / campaign_root

    submission_dir = Path(args.submission_dir)
    if not submission_dir.is_absolute():
        submission_dir = ROOT / submission_dir

    campaign_dir = campaign_root / args.campaign_id
    if not campaign_dir.exists():
        raise FileNotFoundError(campaign_dir)

    if args.audit_json:
        audit_path = Path(args.audit_json)
        if not audit_path.is_absolute():
            audit_path = ROOT / audit_path
    else:
        audit_path = ROOT / "outputs" / "audit" / f"journal_readiness_{args.campaign_id}.json"

    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    kpi_a = pd.read_csv(campaign_dir / "paper_A" / "table_main_kpi_summary.csv")
    kpi_b = pd.read_csv(campaign_dir / "paper_B" / "table_main_kpi_summary.csv")
    feas_a = pd.read_csv(campaign_dir / "paper_A" / "table_feasibility_rate.csv")
    feas_b = pd.read_csv(campaign_dir / "paper_B" / "table_feasibility_rate.csv")
    gap_a = pd.read_csv(campaign_dir / "paper_A" / "table_gap_summary.csv")
    gap_b = pd.read_csv(campaign_dir / "paper_B" / "table_gap_summary.csv")

    ort20a = _pick(kpi_a, method="ortools_main", N=20)
    ort20b = _pick(kpi_b, method="ortools_main", N=20)
    fe40oa = _pick(feas_a, method="ortools_main", N=40)
    fe40ob = _pick(feas_b, method="ortools_main", N=40)
    fe40pa = _pick(feas_a, method="pyvrp_baseline", N=40)
    fe40pb = _pick(feas_b, method="pyvrp_baseline", N=40)
    g20oa = _pick(gap_a, method="ortools_main", N=20)
    g20ob = _pick(gap_b, method="ortools_main", N=20)
    g20pa = _pick(gap_a, method="pyvrp_baseline", N=20)
    g20pb = _pick(gap_b, method="pyvrp_baseline", N=20)

    note = f"""# Release Note: v1.0.0-journal-repro (Campaign Locked)

## Release Scope
- Campaign ID: `{args.campaign_id}`
- Target: TR-E reproducible manuscript package
- Readiness audit: `{audit['summary']}`

## Evidence Snapshot (Campaign-Locked)
- Family stress effect (OR-Tools, N=20):
  - on-time: `{ort20a['on_time_pct_mean']:.2f}% -> {ort20b['on_time_pct_mean']:.2f}%` (A -> B)
  - tardiness: `{ort20a['total_tardiness_min_mean']:.2f} -> {ort20b['total_tardiness_min_mean']:.2f}` minutes
- Feasibility at N=40:
  - OR-Tools: A `{fe40oa['feasible_rate']:.3f}`, B `{fe40ob['feasible_rate']:.3f}`
  - PyVRP baseline: A `{fe40pa['feasible_rate']:.3f}`, B `{fe40pb['feasible_rate']:.3f}`
- Gap at N=20 (mean %):
  - Family A: OR-Tools `{g20oa['gap_pct_mean']:.2f}%` vs PyVRP `{g20pa['gap_pct_mean']:.2f}%`
  - Family B: OR-Tools `{g20ob['gap_pct_mean']:.2f}%` vs PyVRP `{g20pb['gap_pct_mean']:.2f}%`

## Interfaces Added for Release
- `scripts/build_manuscript_pack.sh`
- `scripts/check_manuscript_pack_consistency.py`
- Campaign-scoped review packaging via `uavtre.make_review_pack`

## Artifacts
- `output/submission/claim_evidence_map_{args.campaign_id}.md`
- `output/submission/results_discussion_draft_{args.campaign_id}.md`
- `output/submission/next_steps_{args.campaign_id}.md`
- `output/submission/TABLE_FIGURE_INDEX_{args.campaign_id}.md`
- `output/submission/MANUSCRIPT_PACK_MANIFEST_{args.campaign_id}.json`

## Final Notes
- CPU-sharded execution is the canonical runtime path for this solver stack.
- `N=80` remains strictly `scalability_only` with no bound/gap claims.
"""

    out = submission_dir / f"RELEASE_NOTE_{args.campaign_id}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(note, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
