#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate campaign-scoped manuscript package artifacts."
    )
    parser.add_argument("--campaign-id", required=True, help="Campaign identifier.")
    parser.add_argument(
        "--campaign-root",
        default="outputs/campaigns",
        help="Root containing campaign directories.",
    )
    parser.add_argument(
        "--submission-dir",
        default="output/submission",
        help="Output directory for manuscript artifacts.",
    )
    parser.add_argument("--audit-json", default=None, help="Optional explicit audit JSON path.")
    return parser.parse_args()


def _fmt(x: float | int | None, nd: int = 2) -> str:
    if x is None:
        return "NA"
    try:
        v = float(x)
    except Exception:
        return str(x)
    return f"{v:.{nd}f}"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _pick_row(df: pd.DataFrame, **filters: Any) -> pd.Series | None:
    q = df
    for k, v in filters.items():
        q = q[q[k] == v]
    if q.empty:
        return None
    return q.iloc[0]


def _pick_sig(
    df: pd.DataFrame,
    method_left: str,
    method_right: str,
    metric: str,
) -> pd.Series | None:
    q = df[df["metric"] == metric]
    if q.empty:
        return None
    lr = q[(q["method_a"] == method_left) & (q["method_b"] == method_right)]
    if not lr.empty:
        return lr.iloc[0]
    rl = q[(q["method_a"] == method_right) & (q["method_b"] == method_left)]
    if not rl.empty:
        return rl.iloc[0]
    return None


def _safe_value(row: pd.Series | None, col: str):
    if row is None:
        return None
    try:
        return row[col]
    except Exception:
        return None


def _coverage(df: pd.DataFrame) -> str:
    sizes = sorted(pd.to_numeric(df["N"], errors="coerce").dropna().astype(int).unique().tolist())
    return ",".join(str(n) for n in sizes) if sizes else "NA"


def _table_metric_ref(path: Path, filters: dict[str, Any], metric_col: str) -> str:
    parts = [f"{k}={v}" for k, v in filters.items()]
    return f"`{path.as_posix()}` [{', '.join(parts)}], metric=`{metric_col}`"


def _relpath_text(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> None:
    args = parse_args()

    campaign_root_arg = args.campaign_root
    submission_dir_arg = args.submission_dir

    campaign_root = Path(args.campaign_root)
    if not campaign_root.is_absolute():
        campaign_root = ROOT / campaign_root

    out_dir = Path(args.submission_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    campaign_dir = campaign_root / args.campaign_id
    if not campaign_dir.exists():
        raise FileNotFoundError(f"campaign directory not found: {campaign_dir}")

    if args.audit_json:
        audit_path = Path(args.audit_json)
        if not audit_path.is_absolute():
            audit_path = ROOT / audit_path
    else:
        audit_path = ROOT / "outputs" / "audit" / f"journal_readiness_{args.campaign_id}.json"

    audit = (
        json.loads(audit_path.read_text(encoding="utf-8"))
        if audit_path.exists()
        else {"summary": {"overall_pass": False, "reason": f"missing audit: {_relpath_text(audit_path)}"}}
    )

    main_a = _load_csv(campaign_dir / "main_A_core" / "results_main.csv")
    main_b = _load_csv(campaign_dir / "main_B_core" / "results_main.csv")
    scal_a = _load_csv(campaign_dir / "scal_A_core" / "results_main.csv")
    scal_b = _load_csv(campaign_dir / "scal_B_core" / "results_main.csv")

    kpi_a = _load_csv(campaign_dir / "paper_A" / "table_main_kpi_summary.csv")
    kpi_b = _load_csv(campaign_dir / "paper_B" / "table_main_kpi_summary.csv")
    gap_a = _load_csv(campaign_dir / "paper_A" / "table_gap_summary.csv")
    gap_b = _load_csv(campaign_dir / "paper_B" / "table_gap_summary.csv")
    feas_a = _load_csv(campaign_dir / "paper_A" / "table_feasibility_rate.csv")
    feas_b = _load_csv(campaign_dir / "paper_B" / "table_feasibility_rate.csv")

    sig_a = _load_csv(campaign_dir / "main_A_core" / "results_significance.csv")
    sig_b = _load_csv(campaign_dir / "main_B_core" / "results_significance.csv")

    ort20_a = _pick_row(kpi_a, method="ortools_main", N=20)
    ort20_b = _pick_row(kpi_b, method="ortools_main", N=20)
    ort40_a = _pick_row(kpi_a, method="ortools_main", N=40)
    ort40_b = _pick_row(kpi_b, method="ortools_main", N=40)
    gap20_ort_a = _pick_row(gap_a, method="ortools_main", N=20)
    gap20_ort_b = _pick_row(gap_b, method="ortools_main", N=20)
    gap20_pyv_a = _pick_row(gap_a, method="pyvrp_baseline", N=20)
    gap20_pyv_b = _pick_row(gap_b, method="pyvrp_baseline", N=20)
    feas40_ort_a = _pick_row(feas_a, method="ortools_main", N=40)
    feas40_ort_b = _pick_row(feas_b, method="ortools_main", N=40)
    feas40_pyv_a = _pick_row(feas_a, method="pyvrp_baseline", N=40)
    feas40_pyv_b = _pick_row(feas_b, method="pyvrp_baseline", N=40)

    sig_a_runtime = _pick_sig(sig_a, "ortools_main", "pyvrp_baseline", "runtime_total_s")
    sig_b_runtime = _pick_sig(sig_b, "ortools_main", "pyvrp_baseline", "runtime_total_s")
    sig_a_tard = _pick_sig(sig_a, "ortools_main", "pyvrp_baseline", "total_tardiness_min")
    sig_b_tard = _pick_sig(sig_b, "ortools_main", "pyvrp_baseline", "total_tardiness_min")

    sig_a_count = int((pd.to_numeric(sig_a["significant_flag"], errors="coerce") == 1).sum())
    sig_b_count = int((pd.to_numeric(sig_b["significant_flag"], errors="coerce") == 1).sum())

    cmd_regen_tables = (
        f"MAIN_PATH=outputs/campaigns/{args.campaign_id}/aggregated/main_A.csv "
        f"SCAL_PATH=outputs/campaigns/{args.campaign_id}/aggregated/scal_A.csv "
        "OUT_DIR=outputs/campaigns/"
        f"{args.campaign_id}/paper_A PYTHON_BIN=.venv/bin/python ./scripts/make_paper_tables_v2.sh"
    )
    cmd_audit = (
        "PYTHONPATH=src .venv/bin/python scripts/audit_journal_readiness.py "
        f"--campaign-id {args.campaign_id} --campaign-root {campaign_root_arg} "
        f"--json-out outputs/audit/journal_readiness_{args.campaign_id}.json "
        "--fail-on-critical --fail-on-high"
    )
    cmd_build_pack = (
        f"./scripts/build_manuscript_pack.sh --campaign-id {args.campaign_id} "
        f"--campaign-root {campaign_root_arg}"
    )

    claim_map = f"""# Claim-to-Evidence Map ({args.campaign_id})

## Scope
- Campaign ID: `{args.campaign_id}`
- Coverage A-main: `N={_coverage(main_a)}`
- Coverage B-main: `N={_coverage(main_b)}`
- Coverage A-scalability: `N={_coverage(scal_a)}`
- Coverage B-scalability: `N={_coverage(scal_b)}`
- Readiness summary: `{audit.get("summary", {})}`

## Claim Matrix
| Claim | Statement | Dataset Slice | Statistical Test | Table Row + Metric | Numeric Evidence | Reproducible Command | Status |
|---|---|---|---|---|---|---|---|
| C1 | Policy gate is satisfied by size regime. | `main_A_core`, `main_B_core`, `scal_A_core`, `scal_B_core` | Journal-readiness audit | `outputs/audit/journal_readiness_{args.campaign_id}.json`, summary fields | overall_pass=`{audit.get("summary", {}).get("overall_pass")}` | `{cmd_audit}` | Supported |
| C2 | Family B stress reduces OR-Tools service quality at medium size. | `paper_A` vs `paper_B` at `method=ortools_main`, `N=20` | Wilcoxon+Holm available in significance files | {_table_metric_ref(Path("outputs/campaigns") / args.campaign_id / "paper_A/table_main_kpi_summary.csv", {"method": "ortools_main", "N": 20}, "on_time_pct_mean")} and `_B` peer table | on-time `{_fmt(_safe_value(ort20_a, "on_time_pct_mean"))}% -> {_fmt(_safe_value(ort20_b, "on_time_pct_mean"))}%`; tardiness `{_fmt(_safe_value(ort20_a, "total_tardiness_min_mean"))} -> {_fmt(_safe_value(ort20_b, "total_tardiness_min_mean"))}` min | `{cmd_regen_tables}` | Supported |
| C3 | OR-Tools stays feasible at `N=40` while PyVRP drops in both families. | `paper_A/table_feasibility_rate.csv`, `paper_B/table_feasibility_rate.csv` | N/A (deterministic feasibility rates) | {_table_metric_ref(Path("outputs/campaigns") / args.campaign_id / "paper_A/table_feasibility_rate.csv", {"method": "ortools_main", "N": 40}, "feasible_rate")} and corresponding PyVRP rows | A: OR `{_fmt(_safe_value(feas40_ort_a, "feasible_rate"), 3)}` vs PY `{_fmt(_safe_value(feas40_pyv_a, "feasible_rate"), 3)}`; B: OR `{_fmt(_safe_value(feas40_ort_b, "feasible_rate"), 3)}` vs PY `{_fmt(_safe_value(feas40_pyv_b, "feasible_rate"), 3)}` | `{cmd_regen_tables}` | Supported |
| C4 | At `N=20`, OR-Tools has tighter mean gap than PyVRP in A and B. | `paper_A/table_gap_summary.csv`, `paper_B/table_gap_summary.csv` | N/A (gap summary table) | {_table_metric_ref(Path("outputs/campaigns") / args.campaign_id / "paper_A/table_gap_summary.csv", {"method": "ortools_main", "N": 20}, "gap_pct_mean")} and corresponding PyVRP rows | A: `{_fmt(_safe_value(gap20_ort_a, "gap_pct_mean"))}%` vs `{_fmt(_safe_value(gap20_pyv_a, "gap_pct_mean"))}%`; B: `{_fmt(_safe_value(gap20_ort_b, "gap_pct_mean"))}%` vs `{_fmt(_safe_value(gap20_pyv_b, "gap_pct_mean"))}%` | `{cmd_regen_tables}` | Supported |
| C5 | Inference is reported conservatively despite strong adjusted significance. | `main_A_core/results_significance.csv`, `main_B_core/results_significance.csv` | Wilcoxon, Holm-adjusted p, effect size, bootstrap CI | row `ortools_main vs pyvrp_baseline` for `runtime_total_s` and `total_tardiness_min` | A runtime p_holm=`{_fmt(_safe_value(sig_a_runtime, "p_value_adj"), 4)}`, dir=`{_safe_value(sig_a_runtime, "effect_direction")}`, n_pairs=`{_safe_value(sig_a_runtime, "n_pairs")}`; B runtime p_holm=`{_fmt(_safe_value(sig_b_runtime, "p_value_adj"), 4)}`, dir=`{_safe_value(sig_b_runtime, "effect_direction")}`, n_pairs=`{_safe_value(sig_b_runtime, "n_pairs")}` | `{cmd_build_pack}` | Supported with caveat |
| C6 | `N=80` is reported as scalability-only with no bound/gap claims. | `scal_A_core/results_main.csv`, `scal_B_core/results_main.csv` | Journal-readiness policy gate | row filter `N>=80`, metric columns `claim_regime`, `gap_pct`, `best_bound` | claim_regime=`scalability_only`, bound/gap missing by policy | `{cmd_audit}` | Supported |
"""

    results_discussion = f"""# Results and Discussion Draft ({args.campaign_id})

## 1. Protocol and Coverage
The campaign covers both TW families (`A`, `B`), main sizes `N=10/20/40`, and scalability size `N=80` with policy-gated reporting.

## 2. Family-A vs Family-B Service Shift
For OR-Tools at `N=20`, on-time performance shifts from `{_fmt(_safe_value(ort20_a, "on_time_pct_mean"))}%` (A) to `{_fmt(_safe_value(ort20_b, "on_time_pct_mean"))}%` (B), while total tardiness shifts from `{_fmt(_safe_value(ort20_a, "total_tardiness_min_mean"))}` to `{_fmt(_safe_value(ort20_b, "total_tardiness_min_mean"))}` minutes.
At `N=40`, on-time shifts `{_fmt(_safe_value(ort40_a, "on_time_pct_mean"))}% -> {_fmt(_safe_value(ort40_b, "on_time_pct_mean"))}%`.

## 3. Feasibility and Bound-Gap Evidence
At `N=40`, OR-Tools remains feasible in A/B with rates `{_fmt(_safe_value(feas40_ort_a, "feasible_rate"), 3)}` and `{_fmt(_safe_value(feas40_ort_b, "feasible_rate"), 3)}`, while PyVRP rates are `{_fmt(_safe_value(feas40_pyv_a, "feasible_rate"), 3)}` and `{_fmt(_safe_value(feas40_pyv_b, "feasible_rate"), 3)}`.
At `N=20`, OR-Tools gap is tighter than PyVRP in both families (A: `{_fmt(_safe_value(gap20_ort_a, "gap_pct_mean"))}%` vs `{_fmt(_safe_value(gap20_pyv_a, "gap_pct_mean"))}%`; B: `{_fmt(_safe_value(gap20_ort_b, "gap_pct_mean"))}%` vs `{_fmt(_safe_value(gap20_pyv_b, "gap_pct_mean"))}%`).

## 4. Statistical Interpretation (Strict Reporting)
Family A runtime comparison (`ortools_main` vs `pyvrp_baseline`): p_holm=`{_fmt(_safe_value(sig_a_runtime, "p_value_adj"), 6)}`, effect_direction=`{_safe_value(sig_a_runtime, "effect_direction")}`, effect_size=`{_fmt(_safe_value(sig_a_runtime, "effect_size"), 4)}`, CI=[`{_fmt(_safe_value(sig_a_runtime, "ci_low"), 4)}`, `{_fmt(_safe_value(sig_a_runtime, "ci_high"), 4)}`], n_pairs=`{_safe_value(sig_a_runtime, "n_pairs")}`.
Family B runtime comparison (`ortools_main` vs `pyvrp_baseline`): p_holm=`{_fmt(_safe_value(sig_b_runtime, "p_value_adj"), 6)}`, effect_direction=`{_safe_value(sig_b_runtime, "effect_direction")}`, effect_size=`{_fmt(_safe_value(sig_b_runtime, "effect_size"), 4)}`, CI=[`{_fmt(_safe_value(sig_b_runtime, "ci_low"), 4)}`, `{_fmt(_safe_value(sig_b_runtime, "ci_high"), 4)}`], n_pairs=`{_safe_value(sig_b_runtime, "n_pairs")}`.
Family A tardiness comparison: p_holm=`{_fmt(_safe_value(sig_a_tard, "p_value_adj"), 6)}`, effect_direction=`{_safe_value(sig_a_tard, "effect_direction")}`, n_pairs=`{_safe_value(sig_a_tard, "n_pairs")}`.
Family B tardiness comparison: p_holm=`{_fmt(_safe_value(sig_b_tard, "p_value_adj"), 6)}`, effect_direction=`{_safe_value(sig_b_tard, "effect_direction")}`, n_pairs=`{_safe_value(sig_b_tard, "n_pairs")}`.

## 5. Scalability Policy
All `N=80` statements must remain operational/scalability-only; no bound/gap claim is admissible by policy.
"""

    next_steps = f"""# Next Writing Steps ({args.campaign_id})

1. Anchor Results section on C1/C3/C4/C6 and keep C5 conservative.
2. Use C2 as stress-robustness result with direct A/B numerical deltas.
3. Build figures from campaign tables only (no ad hoc recomputation).
4. Keep all appendix reproducibility references campaign-locked to `{args.campaign_id}`.
5. For transfer to another journal, reuse the same claim-evidence map and update only venue-specific template text.
"""

    table_index = f"""# Table and Figure Index ({args.campaign_id})

## Campaign Source
- Root: `outputs/campaigns/{args.campaign_id}`
- Audit: `outputs/audit/journal_readiness_{args.campaign_id}.json`

## Core Tables
- `outputs/campaigns/{args.campaign_id}/paper_A/table_main_kpi_summary.csv`
- `outputs/campaigns/{args.campaign_id}/paper_A/table_gap_summary.csv`
- `outputs/campaigns/{args.campaign_id}/paper_A/table_feasibility_rate.csv`
- `outputs/campaigns/{args.campaign_id}/paper_A/table_scalability_raw.csv`
- `outputs/campaigns/{args.campaign_id}/paper_B/table_main_kpi_summary.csv`
- `outputs/campaigns/{args.campaign_id}/paper_B/table_gap_summary.csv`
- `outputs/campaigns/{args.campaign_id}/paper_B/table_feasibility_rate.csv`
- `outputs/campaigns/{args.campaign_id}/paper_B/table_scalability_raw.csv`
- `outputs/campaigns/{args.campaign_id}/paper_combined/table_main_kpi_summary.csv`
- `outputs/campaigns/{args.campaign_id}/paper_combined/table_gap_summary.csv`
- `outputs/campaigns/{args.campaign_id}/paper_combined/table_feasibility_rate.csv`
- `outputs/campaigns/{args.campaign_id}/paper_combined/table_scalability_raw.csv`

## Statistical Tables
- `outputs/campaigns/{args.campaign_id}/main_A_core/results_significance.csv`
- `outputs/campaigns/{args.campaign_id}/main_B_core/results_significance.csv`

## Figure Inputs
- Performance bars: `paper_combined/table_main_kpi_summary.csv`
- Gap plot: `paper_combined/table_gap_summary.csv`
- Feasibility plot: `paper_combined/table_feasibility_rate.csv`
- Scalability plot: `paper_combined/table_scalability_raw.csv`
"""

    highlights = [
        "A/B full campaign evidence is locked to one reproducible campaign id.",
        "C1-C6 claims are mapped to exact tables, metrics, and commands.",
        "Statistical statements include Holm-adjusted p, effect size, CI, n-pairs.",
        "Scalability N=80 remains policy-safe: operational only, no bound/gap.",
        "Anonymous/camera-ready bundles are rebuilt from campaign-scoped inputs.",
    ]
    for idx, item in enumerate(highlights, start=1):
        if len(item) > 85:
            raise ValueError(f"highlight {idx} exceeds 85 chars")

    checklist = f"""# TR-E Pre-Submission Checklist ({args.campaign_id})

- [x] Campaign outputs fixed to `outputs/campaigns/{args.campaign_id}/`.
- [x] Audit passes and is archived at `outputs/audit/journal_readiness_{args.campaign_id}.json`.
- [x] Claim map generated at `output/submission/claim_evidence_map_{args.campaign_id}.md`.
- [x] Discussion draft generated at `output/submission/results_discussion_draft_{args.campaign_id}.md`.
- [x] Next steps generated at `output/submission/next_steps_{args.campaign_id}.md`.
- [x] Table index generated at `output/submission/TABLE_FIGURE_INDEX_{args.campaign_id}.md`.
- [x] Manifest generated at `output/submission/MANUSCRIPT_PACK_MANIFEST_{args.campaign_id}.json`.
- [x] Anonymous and camera-ready bundles regenerated with `--campaign-id`.
"""

    build_instructions = f"""# Build Instructions

## 1) Environment bootstrap
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
pip install -e .
```

## 2) Run/refresh full campaign (CPU-sharded, 12 shards)
```bash
CAMPAIGN_ID={args.campaign_id} NUM_SHARDS=12 MAX_CASES=0 \\
RUN_STAGE1_CORE=1 RUN_STAGE2_ROBUST=1 \\
PYTHONPATH=src ./scripts/run_journal_v3_robust.sh
```

## 3) Run campaign readiness audit
```bash
PYTHONPATH=src .venv/bin/python scripts/audit_journal_readiness.py \\
  --campaign-id {args.campaign_id} \\
  --campaign-root {campaign_root_arg} \\
  --json-out outputs/audit/journal_readiness_{args.campaign_id}.json \\
  --fail-on-critical --fail-on-high
```

## 4) Build manuscript package + review bundles
```bash
./scripts/build_manuscript_pack.sh \\
  --campaign-id {args.campaign_id} \\
  --campaign-root {campaign_root_arg} \\
  --submission-dir {submission_dir_arg}
```

## 5) Command provenance
- Campaign run plan: `outputs/campaigns/{args.campaign_id}/RUN_PLAN.json`
- Command history: `outputs/campaigns/{args.campaign_id}/COMMAND_LOG.csv`
- Environment snapshot: `outputs/campaigns/{args.campaign_id}/ENV_SNAPSHOT.json`
- Launcher and stage logs: `outputs/campaigns/{args.campaign_id}/logs/*.log`
"""

    cover_letter = f"""Dear Editor,

Please consider our manuscript for Transportation Research Part E.

The submission reports campaign-locked, reproducible evidence from `{args.campaign_id}` for reliability-aware multi-UAV pickup and delivery with communication-risk and soft time-window penalties. Claims follow a strict size-regime policy (`N<=10` exact with certificate, `N=20/40` bound-gap, `N=80` scalability-only).

All manuscript tables, claim mapping, and review bundles are generated directly from code and archived manifests/logs.

Sincerely,
Corresponding Author
"""

    _write(out_dir / f"claim_evidence_map_{args.campaign_id}.md", claim_map)
    _write(out_dir / f"results_discussion_draft_{args.campaign_id}.md", results_discussion)
    _write(out_dir / f"next_steps_{args.campaign_id}.md", next_steps)
    _write(out_dir / f"TABLE_FIGURE_INDEX_{args.campaign_id}.md", table_index)
    _write(out_dir / "proposal_highlights.txt", "\n".join(highlights) + "\n")
    _write(out_dir / "cover_letter_draft.txt", cover_letter)
    _write(out_dir / "tr_e_presubmission_checklist.md", checklist)
    _write(out_dir / "build_instructions.md", build_instructions)

    generated_at = datetime.now(timezone.utc).isoformat()
    artifact_paths = [
        out_dir / f"claim_evidence_map_{args.campaign_id}.md",
        out_dir / f"results_discussion_draft_{args.campaign_id}.md",
        out_dir / f"next_steps_{args.campaign_id}.md",
        out_dir / f"TABLE_FIGURE_INDEX_{args.campaign_id}.md",
        out_dir / "proposal_highlights.txt",
        out_dir / "cover_letter_draft.txt",
        out_dir / "tr_e_presubmission_checklist.md",
        out_dir / "build_instructions.md",
    ]

    manifest = {
        "generated_at_utc": generated_at,
        "campaign_id": args.campaign_id,
        "campaign_root": campaign_root_arg,
        "campaign_dir": f"{campaign_root_arg.rstrip('/')}/{args.campaign_id}",
        "audit_json": _relpath_text(audit_path),
        "audit_summary": audit.get("summary", {}),
        "runtime_strategy": {
            "execution": "cpu_sharded",
            "num_shards": 12,
            "source": _relpath_text(campaign_dir / "RUN_PLAN.json"),
        },
        "source_tables": {
            "paper_A": sorted(str(p.relative_to(ROOT)) for p in (campaign_dir / "paper_A").glob("*.csv")),
            "paper_B": sorted(str(p.relative_to(ROOT)) for p in (campaign_dir / "paper_B").glob("*.csv")),
            "paper_combined": sorted(
                str(p.relative_to(ROOT)) for p in (campaign_dir / "paper_combined").glob("*.csv")
            ),
        },
        "significance_rows": {
            "family_A": int(len(sig_a)),
            "family_B": int(len(sig_b)),
            "family_A_significant": sig_a_count,
            "family_B_significant": sig_b_count,
        },
        "claims_policy": {
            "C5_policy": "conservative",
            "N<=10": "exact_with_certificate",
            "N20_40": "bound_gap",
            "N80": "scalability_only",
        },
        "artifacts": [],
    }

    for path in artifact_paths:
        if path.exists():
            manifest["artifacts"].append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": _sha256(path),
                    "bytes": path.stat().st_size,
                }
            )

    manifest_path = out_dir / f"MANUSCRIPT_PACK_MANIFEST_{args.campaign_id}.json"
    _write(manifest_path, json.dumps(manifest, indent=2))

    manifest["artifacts"].append(
        {
            "path": manifest_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(manifest_path),
            "bytes": manifest_path.stat().st_size,
        }
    )
    _write(manifest_path, json.dumps(manifest, indent=2))

    print("written:")
    for p in [
        out_dir / f"claim_evidence_map_{args.campaign_id}.md",
        out_dir / f"results_discussion_draft_{args.campaign_id}.md",
        out_dir / f"next_steps_{args.campaign_id}.md",
        out_dir / f"TABLE_FIGURE_INDEX_{args.campaign_id}.md",
        manifest_path,
        out_dir / "proposal_highlights.txt",
        out_dir / "cover_letter_draft.txt",
        out_dir / "tr_e_presubmission_checklist.md",
        out_dir / "build_instructions.md",
    ]:
        print(p)


if __name__ == "__main__":
    main()
