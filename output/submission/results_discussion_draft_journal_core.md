# Results and Discussion Draft (Journal-Core)

## 1. Experimental Coverage and Compliance
The journal-core campaign (`journal_core_20260219_013349`) satisfies the protocol gates for both time-window families (A/B), with main-table sizes `N=10/20/40` and scalability size `N=80`. The automated readiness audit passed with zero critical/high failures.

## 2. Main Performance Patterns
Under Family A, OR-Tools maintains full feasibility at `N=20/40` with on-time means of `63.75%` and `89.38%`, respectively. Under Family B (stress windows), performance drops to `28.75%` at `N=20` and `74.38%` at `N=40`, with substantial tardiness increase (e.g., `N=20`: `24.36` to `53.64` minutes).

## 3. Bound-Gap Behavior
At `N=20`, OR-Tools yields smaller mean bound gaps than PyVRP in both families (A: `7.74%` vs `15.23%`; B: `8.03%` vs `16.88%`). This supports OR-Tools as primary heuristic for soft-TW operational runs.

## 4. Solver Tradeoff Interpretation
PyVRP retains strong service levels at `N=20` (on-time ~100%) but tends to fail feasibility at `N=40` in both families, limiting its role to baseline/ablation rather than primary journal engine.

## 5. Statistical Inference Status
Holm-corrected tests show limited adjusted significance in this journal-core run. In Family B, the OR-Tools vs PyVRP runtime difference remains adjusted-significant (`p_adj=0.0146`), while most other pairwise metrics are not adjusted-significant. Therefore, this run is appropriate for structured drafting and protocol validation, but final submission claims should rely on expanded seed coverage.

## 6. Scalability Regime
For `N=80`, results are reported in scalability-only mode, as intended by claim policy; no bound/gap claims are made.

## 7. Managerial Implication Snapshot
Time-window tightening (Family B) causes clear service degradation for the OR-Tools operational policy, while risk and energy shifts remain scenario-dependent. This suggests that SLA-sensitive deployments should prioritize time-window robustness (scheduling slack and staging density) before pursuing marginal energy optimization.

## 8. Pre-Submission Action
Before journal submission, run a full-seed campaign (same protocol, larger replication) and regenerate significance tables to harden inferential claims.
