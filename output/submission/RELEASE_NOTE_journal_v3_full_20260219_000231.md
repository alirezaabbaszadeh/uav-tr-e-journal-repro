# Release Note: v1.0.0-journal-repro (Campaign Locked)

## Release Scope
- Campaign ID: `journal_v3_full_20260219_000231`
- Target: TR-E reproducible manuscript package
- Readiness audit: `{'total_gates': 25, 'critical_failed': 0, 'high_failed': 0, 'medium_failed': 0, 'overall_pass': True}`

## Evidence Snapshot (Campaign-Locked)
- Family stress effect (OR-Tools, N=20):
  - on-time: `46.29% -> 36.30%` (A -> B)
  - tardiness: `77.30 -> 94.60` minutes
- Feasibility at N=40:
  - OR-Tools: A `0.972`, B `0.969`
  - PyVRP baseline: A `0.000`, B `0.000`
- Gap at N=20 (mean %):
  - Family A: OR-Tools `11.14%` vs PyVRP `25.60%`
  - Family B: OR-Tools `11.36%` vs PyVRP `27.83%`

## Interfaces Added for Release
- `scripts/build_manuscript_pack.sh`
- `scripts/check_manuscript_pack_consistency.py`
- Campaign-scoped review packaging via `uavtre.make_review_pack`

## Artifacts
- `output/submission/claim_evidence_map_journal_v3_full_20260219_000231.md`
- `output/submission/results_discussion_draft_journal_v3_full_20260219_000231.md`
- `output/submission/next_steps_journal_v3_full_20260219_000231.md`
- `output/submission/TABLE_FIGURE_INDEX_journal_v3_full_20260219_000231.md`
- `output/submission/MANUSCRIPT_PACK_MANIFEST_journal_v3_full_20260219_000231.json`

## Final Notes
- CPU-sharded execution is the canonical runtime path for this solver stack.
- `N=80` remains strictly `scalability_only` with no bound/gap claims.
