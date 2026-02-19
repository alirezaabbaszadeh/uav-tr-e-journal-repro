from __future__ import annotations

import pandas as pd

from uavtre.submit_v1.claim_guard import validate_claims, write_claim_registry_yaml
from uavtre.submit_v1.evidence_index import EVIDENCE_COLUMNS


def _base_rows() -> list[dict[str, object]]:
    rows = []

    def add(claim: str, metric: str, value: object) -> None:
        rows.append(
            {
                "claim_id": claim,
                "source_path": "x.csv",
                "table_or_fig_id": "t1",
                "metric": metric,
                "value": value,
                "slice": "s",
                "command": "cmd",
                "verified": 1,
            }
        )

    for m, v in [
        ("audit_overall_pass", 1),
        ("coverage_main_a_10_20_40", 1),
        ("coverage_main_b_10_20_40", 1),
    ]:
        add("C1", m, v)

    for m in [
        "on_time_pct_a_n20_ortools",
        "on_time_pct_b_n20_ortools",
        "tardiness_min_a_n20_ortools",
        "tardiness_min_b_n20_ortools",
    ]:
        add("C2", m, 1.0)

    for m in [
        "feasible_rate_a_n40_ortools",
        "feasible_rate_b_n40_ortools",
        "feasible_rate_a_n40_pyvrp",
        "feasible_rate_b_n40_pyvrp",
    ]:
        add("C3", m, 1.0)

    for m in [
        "gap_pct_a_n20_ortools",
        "gap_pct_b_n20_ortools",
        "gap_pct_a_n20_pyvrp",
        "gap_pct_b_n20_pyvrp",
    ]:
        add("C4", m, 1.0)

    for m in [
        "runtime_p_holm_a",
        "runtime_p_holm_b",
        "runtime_effect_size_a",
        "runtime_effect_size_b",
        "runtime_ci_low_a",
        "runtime_ci_high_a",
        "runtime_ci_low_b",
        "runtime_ci_high_b",
        "runtime_n_pairs_a",
        "runtime_n_pairs_b",
    ]:
        add("C5", m, 1.0)

    for m, v in [
        ("n80_rows_count", 10),
        ("n80_invalid_bound_gap_rows", 0),
        ("n80_invalid_regime_rows", 0),
    ]:
        add("C6", m, v)

    return rows


def test_claim_guard_passes_with_complete_metrics(tmp_path):
    evidence_csv = tmp_path / "EVIDENCE_INDEX_test.csv"
    claim_yaml = tmp_path / "CLAIM_REGISTRY_test.yaml"
    report = tmp_path / "CLAIM_GUARD_REPORT_test.json"

    df = pd.DataFrame(_base_rows(), columns=EVIDENCE_COLUMNS)
    df.to_csv(evidence_csv, index=False)
    write_claim_registry_yaml("test", claim_yaml)

    result = validate_claims(
        campaign_id="test",
        evidence_csv=evidence_csv,
        claim_registry_yaml=claim_yaml,
        report_path=report,
    )
    assert result.passed


def test_claim_guard_fails_on_n80_policy_violation(tmp_path):
    evidence_csv = tmp_path / "EVIDENCE_INDEX_test.csv"
    claim_yaml = tmp_path / "CLAIM_REGISTRY_test.yaml"
    report = tmp_path / "CLAIM_GUARD_REPORT_test.json"

    rows = _base_rows()
    for row in rows:
        if row["claim_id"] == "C6" and row["metric"] == "n80_invalid_bound_gap_rows":
            row["value"] = 2
    pd.DataFrame(rows, columns=EVIDENCE_COLUMNS).to_csv(evidence_csv, index=False)
    write_claim_registry_yaml("test", claim_yaml)

    result = validate_claims(
        campaign_id="test",
        evidence_csv=evidence_csv,
        claim_registry_yaml=claim_yaml,
        report_path=report,
    )
    assert not result.passed
    assert any("n80_invalid_bound_gap_rows" in x for x in result.policy_violations)
