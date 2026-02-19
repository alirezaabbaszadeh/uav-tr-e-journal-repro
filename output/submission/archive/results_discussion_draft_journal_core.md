# Results and Discussion Draft (Campaign)

## 1. Coverage and Protocol Compliance
The campaign (`journal_v3_full_20260219_000231`) covers both time-window families (A/B), main-table sizes (`N=10/20/40`), and scalability (`N=80`).

## 2. Performance Under Baseline and Stress TW
For Family A, OR-Tools feasibility extends through `N=40`. Under Family B stress windows, service quality drops at medium/large sizes: `N=20` on-time `46.29% -> 36.30%`, tardiness `77.30 -> 94.60` min.

## 3. Bound-Gap Evidence at N=20
At `N=20`, OR-Tools shows tighter mean gap than PyVRP in both families: Family A `11.14%` vs `25.60%`, Family B `11.36%` vs `27.83%`.

## 4. Statistical Interpretation
Adjusted significance is reported with Holm correction, effect size, and CI. If adjusted-significant effects remain sparse, present them conservatively as directional evidence.

## 5. Scalability Reporting
For `N=80`, outputs are intentionally under `scalability_only`, with no bound/gap claims.
