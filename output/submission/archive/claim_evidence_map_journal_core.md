# Claim-to-Evidence Map (Campaign)

## Scope
- Campaign ID: `journal_v3_full_20260219_000231`
- Families covered: `A`, `B`
- Sizes covered: main `N=10/20/40`, scalability `N=80`
- Readiness gate: `{'total_gates': 19, 'critical_failed': 0, 'high_failed': 0, 'medium_failed': 0, 'overall_pass': True}`

## Claims
| Claim ID | Claim Statement | Evidence | Status |
|---|---|---|---|
| C1 | Claim-policy gates are satisfied (exact/bound/scalability by size). | `outputs/audit/journal_readiness_journal_v3_full_20260219_000231.json` | Passed |
| C2 | Soft-TW stress (Family B) reduces OR-Tools service quality at medium/large sizes. | `paper_A/table_main_kpi_summary.csv` vs `paper_B/table_main_kpi_summary.csv`: OR-Tools `N=20` on-time `46.29% -> 36.30%`, tardiness `77.30 -> 94.60` min. | Supported |
| C3 | OR-Tools remains feasible at `N=40` in both families, while PyVRP baseline loses feasibility at `N=40`. | `paper_A/table_feasibility_rate.csv`, `paper_B/table_feasibility_rate.csv` | Supported |
| C4 | At `N=20`, OR-Tools has tighter bound-gap than PyVRP baseline. | `paper_A/table_gap_summary.csv`: OR-Tools mean gap `11.14%` vs PyVRP `25.60%`; `paper_B/table_gap_summary.csv`: `11.36%` vs `27.83%`. | Supported |
| C5 | Statistical power remains limited for broad inferential claims. | `main_A_core/results_significance.csv` (significant rows=12), `main_B_core/results_significance.csv` (significant rows=12); runtime adjusted p-value in family B: `0.0524`. | Caution |
| C6 | Scalability regime (`N=80`) is operational-only (no bound/gap claims). | `scal_A_core/results_main.csv`, `scal_B_core/results_main.csv` with `claim_regime=scalability_only`. | Passed |

## Notes for Manuscript
- Use C1/C3/C4/C6 as confirmed evidence claims.
- Present C2 as stress-robustness finding.
- Present C5 as limitation and rationale for expanded replication if needed.
