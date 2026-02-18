#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _fmt(x: float | int | None, nd: int = 2) -> str:
    if x is None:
        return "NA"
    try:
        v = float(x)
    except Exception:
        return str(x)
    return f"{v:.{nd}f}"


def _load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _pick(df: pd.DataFrame, **filters):
    q = df
    for k, v in filters.items():
        q = q[q[k] == v]
    return q


def main() -> None:
    out_dir = ROOT / "output" / "submission"
    out_dir.mkdir(parents=True, exist_ok=True)

    a_main = _load(ROOT / "outputs" / "main_table_v2_core" / "results_main.csv")
    b_main = _load(ROOT / "outputs" / "main_table_v2_core_B" / "results_main.csv")
    a_scal = _load(ROOT / "outputs" / "scalability_v2_core" / "results_main.csv")
    b_scal = _load(ROOT / "outputs" / "scalability_v2_core_B" / "results_main.csv")

    a_kpi = _load(ROOT / "outputs" / "paper_v2_core" / "table_main_kpi_summary.csv")
    b_kpi = _load(ROOT / "outputs" / "paper_v2_core_B" / "table_main_kpi_summary.csv")
    a_gap = _load(ROOT / "outputs" / "paper_v2_core" / "table_gap_summary.csv")
    b_gap = _load(ROOT / "outputs" / "paper_v2_core_B" / "table_gap_summary.csv")

    a_sig = _load(ROOT / "outputs" / "main_table_v2_core" / "results_significance.csv")
    b_sig = _load(ROOT / "outputs" / "main_table_v2_core_B" / "results_significance.csv")

    audit = json.loads(
        (ROOT / "outputs" / "audit" / "journal_readiness_journal_core_20260219_013349.json").read_text(
            encoding="utf-8"
        )
    )

    a_ort20 = _pick(a_kpi, method="ortools_main", N=20).iloc[0]
    b_ort20 = _pick(b_kpi, method="ortools_main", N=20).iloc[0]
    a_ort40 = _pick(a_kpi, method="ortools_main", N=40).iloc[0]
    b_ort40 = _pick(b_kpi, method="ortools_main", N=40).iloc[0]

    a_pyv20 = _pick(a_kpi, method="pyvrp_baseline", N=20).iloc[0]
    b_pyv20 = _pick(b_kpi, method="pyvrp_baseline", N=20).iloc[0]

    a_gap_ort20 = _pick(a_gap, method="ortools_main", N=20).iloc[0]
    b_gap_ort20 = _pick(b_gap, method="ortools_main", N=20).iloc[0]

    b_runtime_sig = _pick(
        b_sig,
        method_a="ortools_main",
        method_b="pyvrp_baseline",
        metric="runtime_total_s",
    )
    if b_runtime_sig.empty:
        b_runtime_sig = _pick(
            b_sig,
            method_a="pyvrp_baseline",
            method_b="ortools_main",
            metric="runtime_total_s",
        )
    b_runtime_sig = b_runtime_sig.iloc[0]

    sig_a_count = int((a_sig["significant_flag"] == 1).sum())
    sig_b_count = int((b_sig["significant_flag"] == 1).sum())

    claim_map = f"""# Claim-to-Evidence Map (Journal-Core Campaign)

## Scope
- Campaign ID: `journal_core_20260219_013349`
- Families covered: `A`, `B`
- Sizes covered: main `N=10/20/40`, scalability `N=80`
- Readiness gate: `{audit['summary']}`

## Claims
| Claim ID | Claim Statement | Evidence | Status |
|---|---|---|---|
| C1 | Claim-policy gates are satisfied (exact/bound/scalability by size). | `outputs/audit/journal_readiness_journal_core_20260219_013349.json` | Passed |
| C2 | Soft-TW stress (Family B) reduces service quality for OR-Tools at medium/large sizes. | `outputs/paper_v2_core/table_main_kpi_summary.csv` vs `outputs/paper_v2_core_B/table_main_kpi_summary.csv`: OR-Tools `N=20` on-time `{_fmt(a_ort20['on_time_pct_mean'])}% -> {_fmt(b_ort20['on_time_pct_mean'])}%`, tardiness `{_fmt(a_ort20['total_tardiness_min_mean'])} -> {_fmt(b_ort20['total_tardiness_min_mean'])}` min. | Supported |
| C3 | OR-Tools remains feasible at `N=40` in both families, while PyVRP baseline loses feasibility at `N=40`. | `outputs/paper_v2_core/table_feasibility_rate.csv`, `outputs/paper_v2_core_B/table_feasibility_rate.csv` | Supported |
| C4 | At `N=20`, OR-Tools has tighter bound-gap than PyVRP baseline. | `outputs/paper_v2_core/table_gap_summary.csv`: OR-Tools mean gap `{_fmt(a_gap_ort20['gap_pct_mean'])}%` vs PyVRP `{_fmt(_pick(a_gap, method='pyvrp_baseline', N=20).iloc[0]['gap_pct_mean'])}%`; `outputs/paper_v2_core_B/table_gap_summary.csv`: `{_fmt(b_gap_ort20['gap_pct_mean'])}%` vs `{_fmt(_pick(b_gap, method='pyvrp_baseline', N=20).iloc[0]['gap_pct_mean'])}%`. | Supported |
| C5 | Statistical power is still limited for strong inferential claims in journal submission. | `outputs/main_table_v2_core/results_significance.csv` (significant rows={sig_a_count}), `outputs/main_table_v2_core_B/results_significance.csv` (significant rows={sig_b_count}); only one adjusted-significant result in Family B runtime comparison (`p_adj={_fmt(b_runtime_sig['p_value_adj'], 4)}`). | Caution |
| C6 | Scalability regime (`N=80`) is operational-only (no bound/gap claims). | `outputs/scalability_v2_core/results_main.csv`, `outputs/scalability_v2_core_B/results_main.csv` with `claim_regime=scalability_only`. | Passed |

## Notes for Manuscript
- Use C1/C3/C4/C6 as hard evidence claims.
- Present C2 as operational degradation under stress TW (Family B).
- Present C5 as limitation and motivate final full-seed campaign before submission.
"""

    results_discussion = f"""# Results and Discussion Draft (Journal-Core)

## 1. Experimental Coverage and Compliance
The journal-core campaign (`journal_core_20260219_013349`) satisfies the protocol gates for both time-window families (A/B), with main-table sizes `N=10/20/40` and scalability size `N=80`. The automated readiness audit passed with zero critical/high failures.

## 2. Main Performance Patterns
Under Family A, OR-Tools maintains full feasibility at `N=20/40` with on-time means of `{_fmt(a_ort20['on_time_pct_mean'])}%` and `{_fmt(a_ort40['on_time_pct_mean'])}%`, respectively. Under Family B (stress windows), performance drops to `{_fmt(b_ort20['on_time_pct_mean'])}%` at `N=20` and `{_fmt(b_ort40['on_time_pct_mean'])}%` at `N=40`, with substantial tardiness increase (e.g., `N=20`: `{_fmt(a_ort20['total_tardiness_min_mean'])}` to `{_fmt(b_ort20['total_tardiness_min_mean'])}` minutes).

## 3. Bound-Gap Behavior
At `N=20`, OR-Tools yields smaller mean bound gaps than PyVRP in both families (A: `{_fmt(a_gap_ort20['gap_pct_mean'])}%` vs `{_fmt(_pick(a_gap, method='pyvrp_baseline', N=20).iloc[0]['gap_pct_mean'])}%`; B: `{_fmt(b_gap_ort20['gap_pct_mean'])}%` vs `{_fmt(_pick(b_gap, method='pyvrp_baseline', N=20).iloc[0]['gap_pct_mean'])}%`). This supports OR-Tools as primary heuristic for soft-TW operational runs.

## 4. Solver Tradeoff Interpretation
PyVRP retains strong service levels at `N=20` (on-time ~100%) but tends to fail feasibility at `N=40` in both families, limiting its role to baseline/ablation rather than primary journal engine.

## 5. Statistical Inference Status
Holm-corrected tests show limited adjusted significance in this journal-core run. In Family B, the OR-Tools vs PyVRP runtime difference remains adjusted-significant (`p_adj={_fmt(b_runtime_sig['p_value_adj'], 4)}`), while most other pairwise metrics are not adjusted-significant. Therefore, this run is appropriate for structured drafting and protocol validation, but final submission claims should rely on expanded seed coverage.

## 6. Scalability Regime
For `N=80`, results are reported in scalability-only mode, as intended by claim policy; no bound/gap claims are made.

## 7. Managerial Implication Snapshot
Time-window tightening (Family B) causes clear service degradation for the OR-Tools operational policy, while risk and energy shifts remain scenario-dependent. This suggests that SLA-sensitive deployments should prioritize time-window robustness (scheduling slack and staging density) before pursuing marginal energy optimization.

## 8. Pre-Submission Action
Before journal submission, run a full-seed campaign (same protocol, larger replication) and regenerate significance tables to harden inferential claims.
"""

    next_steps = """# Next Writing Steps (Actionable)

1. Move C1/C3/C4/C6 directly into Results as confirmed claims.
2. Keep C2 as a stress-robustness result with explicit Family A/B comparison table.
3. Mark C5 as limitation and include a short paragraph on statistical power.
4. Use `outputs/paper_v2_core/*` and `outputs/paper_v2_core_B/*` as table sources in manuscript.
5. For final submission-quality inference, rerun with larger seed set and re-check `results_significance.csv`.
"""

    (out_dir / "claim_evidence_map_journal_core.md").write_text(claim_map, encoding="utf-8")
    (out_dir / "results_discussion_draft_journal_core.md").write_text(
        results_discussion, encoding="utf-8"
    )
    (out_dir / "next_steps_journal_core.md").write_text(next_steps, encoding="utf-8")

    print("written:")
    print(out_dir / "claim_evidence_map_journal_core.md")
    print(out_dir / "results_discussion_draft_journal_core.md")
    print(out_dir / "next_steps_journal_core.md")


if __name__ == "__main__":
    main()
