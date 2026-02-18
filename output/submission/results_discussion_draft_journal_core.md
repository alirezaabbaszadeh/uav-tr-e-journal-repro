# Results and Discussion Draft (Submit-Ready, Journal-Core)

## 1. Coverage and Protocol Compliance
The journal-core campaign (`journal_core_20260219_013349`) covers both time-window families (A/B), main-table sizes (`N=10/20/40`), and scalability (`N=80`). The automated readiness audit passed with zero critical and high failures.

## 2. Performance Under Baseline and Stress TW
For Family A, OR-Tools preserves feasibility through `N=40`, with on-time means of `63.75%` (`N=20`) and `89.38%` (`N=40`).
Under Family B stress windows, OR-Tools service quality drops: on-time at `N=20` decreases to `28.75%`, and mean tardiness rises from `24.36` to `53.64` minutes. At `N=40`, on-time decreases from `89.38%` to `74.38%`.

## 3. Bound-Gap Evidence at N=20
At `N=20`, OR-Tools reports tighter mean gaps than PyVRP in both families: Family A `7.74%` vs `15.23%`, Family B `8.03%` vs `16.88%`.

## 4. Solver Role Separation
PyVRP provides strong service at `N=20` but does not sustain feasibility at `N=40` in either family; therefore it remains a baseline/ablation solver. OR-Tools is the operational heuristic engine for soft-TW reporting.

## 5. Statistical Interpretation
Holm-adjusted inference is still sparse in this campaign. Family A yields no adjusted-significant pairwise effects, while Family B includes one adjusted-significant runtime effect for OR-Tools vs PyVRP (`p_adj=0.0146`). Results are suitable for structured drafting and protocol validation; broader inferential claims require expanded replication.

## 6. Scalability Reporting
For `N=80`, outputs are intentionally reported under the scalability-only regime, without bound/gap claims, consistent with claim policy.

## 7. Managerial Implication
Stress time windows primarily degrade service reliability (on-time and tardiness) before producing consistent risk/energy gains. This indicates that SLA-oriented deployment should prioritize TW robustness design before marginal route-cost optimization.
