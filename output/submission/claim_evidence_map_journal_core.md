# Claim-to-Evidence Map (Journal-Core Campaign)

## Scope
- Campaign ID: `journal_core_20260219_013349`
- Families covered: `A`, `B`
- Sizes covered: main `N=10/20/40`, scalability `N=80`
- Readiness gate: `{'total_gates': 18, 'critical_failed': 0, 'high_failed': 0, 'medium_failed': 0, 'overall_pass': True}`

## Claims
| Claim ID | Claim Statement | Evidence | Status |
|---|---|---|---|
| C1 | Claim-policy gates are satisfied (exact/bound/scalability by size). | `outputs/audit/journal_readiness_journal_core_20260219_013349.json` | Passed |
| C2 | Soft-TW stress (Family B) reduces OR-Tools service quality at medium/large sizes. | `outputs/paper_v2_core/table_main_kpi_summary.csv` vs `outputs/paper_v2_core_B/table_main_kpi_summary.csv`: OR-Tools `N=20` on-time `63.75% -> 28.75%`, tardiness `24.36 -> 53.64` min. | Supported |
| C3 | OR-Tools remains feasible at `N=40` in both families, while PyVRP baseline loses feasibility at `N=40`. | `outputs/paper_v2_core/table_feasibility_rate.csv`, `outputs/paper_v2_core_B/table_feasibility_rate.csv` | Supported |
| C4 | At `N=20`, OR-Tools has tighter bound-gap than PyVRP baseline. | `outputs/paper_v2_core/table_gap_summary.csv`: OR-Tools mean gap `7.74%` vs PyVRP `15.23%`; `outputs/paper_v2_core_B/table_gap_summary.csv`: `8.03%` vs `16.88%`. | Supported |
| C5 | Statistical power remains limited for broad inferential claims. | `outputs/main_table_v2_core/results_significance.csv` (significant rows=0), `outputs/main_table_v2_core_B/results_significance.csv` (significant rows=1); adjusted-significant result appears for Family-B runtime (`p_adj=0.0146`). | Caution |
| C6 | Scalability regime (`N=80`) is operational-only (no bound/gap claims). | `outputs/scalability_v2_core/results_main.csv`, `outputs/scalability_v2_core_B/results_main.csv` with `claim_regime=scalability_only`. | Passed |

## Notes for Manuscript
- Use C1/C3/C4/C6 as confirmed evidence claims.
- Present C2 as stress-robustness finding.
- Present C5 as limitation and rationale for expanded-seed pre-submission run.
