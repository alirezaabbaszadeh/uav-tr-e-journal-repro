from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ClaimValidationResult:
    passed: bool
    report_path: Path
    unresolved: list[str]
    policy_violations: list[str]


DEFAULT_CLAIMS: list[dict[str, Any]] = [
    {
        "claim_id": "C1",
        "statement": "Policy gate is satisfied by size regime.",
        "status_policy": "supported",
        "required_metrics": [
            "audit_overall_pass",
            "coverage_main_a_10_20_40",
            "coverage_main_b_10_20_40",
        ],
        "allowed_slices": ["main_A_core", "main_B_core", "scal_A_core", "scal_B_core"],
        "forbidden_slices": [],
        "command_ref": "scripts/audit_journal_readiness.py",
    },
    {
        "claim_id": "C2",
        "statement": "Family B stress reduces OR-Tools service quality at medium size.",
        "status_policy": "supported",
        "required_metrics": [
            "on_time_pct_a_n20_ortools",
            "on_time_pct_b_n20_ortools",
            "tardiness_min_a_n20_ortools",
            "tardiness_min_b_n20_ortools",
        ],
        "allowed_slices": ["paper_A", "paper_B"],
        "forbidden_slices": [],
        "command_ref": "scripts/make_paper_tables_v2.sh",
    },
    {
        "claim_id": "C3",
        "statement": "OR-Tools stays feasible at N=40 while PyVRP drops in both families.",
        "status_policy": "supported",
        "required_metrics": [
            "feasible_rate_a_n40_ortools",
            "feasible_rate_b_n40_ortools",
            "feasible_rate_a_n40_pyvrp",
            "feasible_rate_b_n40_pyvrp",
        ],
        "allowed_slices": ["paper_A", "paper_B"],
        "forbidden_slices": [],
        "command_ref": "scripts/make_paper_tables_v2.sh",
    },
    {
        "claim_id": "C4",
        "statement": "At N=20, OR-Tools has tighter mean gap than PyVRP in A and B.",
        "status_policy": "supported",
        "required_metrics": [
            "gap_pct_a_n20_ortools",
            "gap_pct_b_n20_ortools",
            "gap_pct_a_n20_pyvrp",
            "gap_pct_b_n20_pyvrp",
        ],
        "allowed_slices": ["paper_A", "paper_B"],
        "forbidden_slices": [],
        "command_ref": "scripts/make_paper_tables_v2.sh",
    },
    {
        "claim_id": "C5",
        "statement": "Inference is reported conservatively with adjusted significance.",
        "status_policy": "supported_with_caveat",
        "required_metrics": [
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
        ],
        "allowed_slices": ["main_A_core", "main_B_core"],
        "forbidden_slices": [],
        "command_ref": "main_*_core/results_significance.csv",
    },
    {
        "claim_id": "C6",
        "statement": "N=80 remains scalability-only with no bound/gap claims.",
        "status_policy": "supported",
        "required_metrics": [
            "n80_rows_count",
            "n80_invalid_bound_gap_rows",
            "n80_invalid_regime_rows",
        ],
        "allowed_slices": ["scal_A_core", "scal_B_core"],
        "forbidden_slices": ["N80_bound", "N80_gap"],
        "command_ref": "scripts/audit_journal_readiness.py",
    },
]


def write_claim_registry_yaml(campaign_id: str, out_yaml: Path) -> Path:
    out_yaml.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"campaign_id: {campaign_id}")
    lines.append("claims:")
    for claim in DEFAULT_CLAIMS:
        lines.append(f"  - claim_id: {claim['claim_id']}")
        lines.append(f"    statement: \"{claim['statement']}\"")
        lines.append(f"    status_policy: {claim['status_policy']}")
        lines.append("    required_metrics:")
        for metric in claim["required_metrics"]:
            lines.append(f"      - {metric}")
        lines.append("    allowed_slices:")
        for item in claim["allowed_slices"]:
            lines.append(f"      - {item}")
        lines.append("    forbidden_slices:")
        for item in claim["forbidden_slices"]:
            lines.append(f"      - {item}")
        lines.append(f"    command_ref: {claim['command_ref']}")
    out_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_yaml


def _value_map(df: pd.DataFrame) -> dict[tuple[str, str], Any]:
    out: dict[tuple[str, str], Any] = {}
    for _, row in df.iterrows():
        out[(str(row["claim_id"]), str(row["metric"]))] = row["value"]
    return out


def validate_claims(
    *,
    campaign_id: str,
    evidence_csv: Path,
    claim_registry_yaml: Path,
    report_path: Path,
) -> ClaimValidationResult:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if not evidence_csv.exists():
        raise FileNotFoundError(evidence_csv)
    if not claim_registry_yaml.exists():
        raise FileNotFoundError(claim_registry_yaml)

    df = pd.read_csv(evidence_csv)
    vmap = _value_map(df)

    unresolved: list[str] = []
    policy_violations: list[str] = []
    claim_rows: list[dict[str, Any]] = []

    for claim in DEFAULT_CLAIMS:
        cid = claim["claim_id"]
        missing_metrics: list[str] = []
        null_metrics: list[str] = []
        for metric in claim["required_metrics"]:
            key = (cid, metric)
            if key not in vmap:
                missing_metrics.append(metric)
                continue
            value = vmap[key]
            if pd.isna(value):
                null_metrics.append(metric)

        status = "pass"
        if missing_metrics or null_metrics:
            status = "fail"
            unresolved.extend([f"{cid}:{m}" for m in missing_metrics + null_metrics])

        claim_rows.append(
            {
                "claim_id": cid,
                "status": status,
                "missing_metrics": missing_metrics,
                "null_metrics": null_metrics,
                "status_policy": claim["status_policy"],
            }
        )

    # strict policy checks
    if int(float(vmap.get(("C1", "audit_overall_pass"), 0))) != 1:
        policy_violations.append("C1 audit_overall_pass != 1")

    if int(float(vmap.get(("C6", "n80_invalid_bound_gap_rows"), 1))) != 0:
        policy_violations.append("C6 n80_invalid_bound_gap_rows must be 0")
    if int(float(vmap.get(("C6", "n80_invalid_regime_rows"), 1))) != 0:
        policy_violations.append("C6 n80_invalid_regime_rows must be 0")
    if int(float(vmap.get(("C6", "n80_rows_count"), 0))) <= 0:
        policy_violations.append("C6 n80_rows_count must be > 0")

    report = {
        "campaign_id": campaign_id,
        "claim_registry": claim_registry_yaml.as_posix(),
        "evidence_index": evidence_csv.as_posix(),
        "claims": claim_rows,
        "unresolved": unresolved,
        "policy_violations": policy_violations,
        "passed": len(unresolved) == 0 and len(policy_violations) == 0,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return ClaimValidationResult(
        passed=bool(report["passed"]),
        report_path=report_path,
        unresolved=unresolved,
        policy_violations=policy_violations,
    )
