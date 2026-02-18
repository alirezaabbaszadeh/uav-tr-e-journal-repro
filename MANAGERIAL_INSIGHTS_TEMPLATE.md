# Managerial Insights Template (TR-E)

Use this template to convert experiment outputs into managerial statements.

## Insight 1: Minimum BS Density for SLA
- Target SLA: `on_time_pct >= ...`
- Threshold identified at: `B = ...`
- Evidence source: `outputs/results_main.csv` filtered by `N, Delta_min, lambda_out, lambda_tw`
- Practical implication: `...`

## Insight 2: Marginal Value of Additional UAV
- Compare `M=2` vs `M=3` vs `M=4` (if available)
- Change in `on_time_pct`, `total_tardiness_min`, `runtime_total_s`
- Diminishing-return point: `...`

## Insight 3: Time-Window Tightness Breakpoint
- Evaluate `Delta_min in {10,5,2}`
- Detect breakpoint where tardiness growth becomes superlinear
- Operational recommendation: `...`

## Statistical Support
- Confirm key pairwise comparisons using `outputs/results_significance.csv`
- Require `significant_flag=1` for claims in the manuscript
