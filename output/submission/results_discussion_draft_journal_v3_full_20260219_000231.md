# Results and Discussion Draft (journal_v3_full_20260219_000231)

## 1. Protocol and Coverage
The campaign covers both TW families (`A`, `B`), main sizes `N=10/20/40`, and scalability size `N=80` with policy-gated reporting.

## 2. Family-A vs Family-B Service Shift
For OR-Tools at `N=20`, on-time performance shifts from `46.29%` (A) to `36.30%` (B), while total tardiness shifts from `77.30` to `94.60` minutes.
At `N=40`, on-time shifts `49.70% -> 41.27%`.

## 3. Feasibility and Bound-Gap Evidence
At `N=40`, OR-Tools remains feasible in A/B with rates `0.972` and `0.969`, while PyVRP rates are `0.000` and `0.000`.
At `N=20`, OR-Tools gap is tighter than PyVRP in both families (A: `11.14%` vs `25.60%`; B: `11.36%` vs `27.83%`).

## 4. Statistical Interpretation (Strict Reporting)
Family A runtime comparison (`ortools_main` vs `pyvrp_baseline`): p_holm=`0.057335`, effect_direction=`a_better`, effect_size=`-0.1917`, CI=[`-0.0081`, `-0.0034`], n_pairs=`240`.
Family B runtime comparison (`ortools_main` vs `pyvrp_baseline`): p_holm=`0.052393`, effect_direction=`a_better`, effect_size=`-0.2167`, CI=[`-0.0087`, `-0.0064`], n_pairs=`240`.
Family A tardiness comparison: p_holm=`0.000000`, effect_direction=`b_better`, n_pairs=`156`.
Family B tardiness comparison: p_holm=`0.000000`, effect_direction=`b_better`, n_pairs=`156`.

## 5. Scalability Policy
All `N=80` statements must remain operational/scalability-only; no bound/gap claim is admissible by policy.
