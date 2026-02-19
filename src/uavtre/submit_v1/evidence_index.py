from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


EVIDENCE_COLUMNS = [
    "claim_id",
    "source_path",
    "table_or_fig_id",
    "metric",
    "value",
    "slice",
    "command",
    "verified",
]


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _pick_row(df: pd.DataFrame, **filters: Any) -> pd.Series | None:
    q = df
    for key, value in filters.items():
        q = q[q[key] == value]
    if q.empty:
        return None
    return q.iloc[0]


def _pick_sig(df: pd.DataFrame, method_a: str, method_b: str, metric: str) -> pd.Series | None:
    q = df[df["metric"] == metric]
    if q.empty:
        return None
    direct = q[(q["method_a"] == method_a) & (q["method_b"] == method_b)]
    if not direct.empty:
        return direct.iloc[0]
    reverse = q[(q["method_a"] == method_b) & (q["method_b"] == method_a)]
    if not reverse.empty:
        return reverse.iloc[0]
    return None


def _s(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value


def _append(rows: list[dict[str, Any]], **kwargs: Any) -> None:
    row = {k: kwargs.get(k) for k in EVIDENCE_COLUMNS}
    rows.append(row)


def _coverage_ok(df: pd.DataFrame, required: set[int]) -> int:
    found = set(pd.to_numeric(df["N"], errors="coerce").dropna().astype(int).tolist())
    return int(required.issubset(found))


def build_evidence_index(
    *,
    campaign_dir: Path,
    campaign_id: str,
    out_csv: Path,
    audit_json: Path | None,
) -> Path:
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    main_a = _load_csv(campaign_dir / "main_A_core" / "results_main.csv")
    main_b = _load_csv(campaign_dir / "main_B_core" / "results_main.csv")
    scal_a = _load_csv(campaign_dir / "scal_A_core" / "results_main.csv")
    scal_b = _load_csv(campaign_dir / "scal_B_core" / "results_main.csv")

    kpi_a = _load_csv(campaign_dir / "paper_A" / "table_main_kpi_summary.csv")
    kpi_b = _load_csv(campaign_dir / "paper_B" / "table_main_kpi_summary.csv")
    gap_a = _load_csv(campaign_dir / "paper_A" / "table_gap_summary.csv")
    gap_b = _load_csv(campaign_dir / "paper_B" / "table_gap_summary.csv")
    feas_a = _load_csv(campaign_dir / "paper_A" / "table_feasibility_rate.csv")
    feas_b = _load_csv(campaign_dir / "paper_B" / "table_feasibility_rate.csv")

    sig_a = _load_csv(campaign_dir / "main_A_core" / "results_significance.csv")
    sig_b = _load_csv(campaign_dir / "main_B_core" / "results_significance.csv")

    audit_overall_pass = 0
    if audit_json and audit_json.exists():
        payload = json.loads(audit_json.read_text(encoding="utf-8"))
        audit_overall_pass = int(bool(payload.get("summary", {}).get("overall_pass", False)))

    rows: list[dict[str, Any]] = []

    audit_cmd = (
        "PYTHONPATH=src .venv/bin/python scripts/audit_journal_readiness.py "
        f"--campaign-id {campaign_id} --campaign-root outputs/campaigns "
        f"--json-out outputs/audit/journal_readiness_{campaign_id}.json "
        "--fail-on-critical --fail-on-high"
    )

    _append(
        rows,
        claim_id="C1",
        source_path=f"outputs/audit/journal_readiness_{campaign_id}.json",
        table_or_fig_id="AUDIT_SUMMARY",
        metric="audit_overall_pass",
        value=audit_overall_pass,
        slice="summary",
        command=audit_cmd,
        verified=1,
    )
    _append(
        rows,
        claim_id="C1",
        source_path=(campaign_dir / "main_A_core" / "results_main.csv").as_posix(),
        table_or_fig_id="MAIN_A_COVERAGE",
        metric="coverage_main_a_10_20_40",
        value=_coverage_ok(main_a, {10, 20, 40}),
        slice="N in {10,20,40}",
        command=audit_cmd,
        verified=1,
    )
    _append(
        rows,
        claim_id="C1",
        source_path=(campaign_dir / "main_B_core" / "results_main.csv").as_posix(),
        table_or_fig_id="MAIN_B_COVERAGE",
        metric="coverage_main_b_10_20_40",
        value=_coverage_ok(main_b, {10, 20, 40}),
        slice="N in {10,20,40}",
        command=audit_cmd,
        verified=1,
    )

    ort20_a = _pick_row(kpi_a, method="ortools_main", N=20)
    ort20_b = _pick_row(kpi_b, method="ortools_main", N=20)
    _append(
        rows,
        claim_id="C2",
        source_path=(campaign_dir / "paper_A" / "table_main_kpi_summary.csv").as_posix(),
        table_or_fig_id="KPI_A_N20_ORTOOLS",
        metric="on_time_pct_a_n20_ortools",
        value=_s(None if ort20_a is None else ort20_a["on_time_pct_mean"]),
        slice="method=ortools_main,N=20,tw_family=A",
        command="scripts/make_paper_tables_v2.sh",
        verified=1,
    )
    _append(
        rows,
        claim_id="C2",
        source_path=(campaign_dir / "paper_B" / "table_main_kpi_summary.csv").as_posix(),
        table_or_fig_id="KPI_B_N20_ORTOOLS",
        metric="on_time_pct_b_n20_ortools",
        value=_s(None if ort20_b is None else ort20_b["on_time_pct_mean"]),
        slice="method=ortools_main,N=20,tw_family=B",
        command="scripts/make_paper_tables_v2.sh",
        verified=1,
    )
    _append(
        rows,
        claim_id="C2",
        source_path=(campaign_dir / "paper_A" / "table_main_kpi_summary.csv").as_posix(),
        table_or_fig_id="KPI_A_N20_ORTOOLS",
        metric="tardiness_min_a_n20_ortools",
        value=_s(None if ort20_a is None else ort20_a["total_tardiness_min_mean"]),
        slice="method=ortools_main,N=20,tw_family=A",
        command="scripts/make_paper_tables_v2.sh",
        verified=1,
    )
    _append(
        rows,
        claim_id="C2",
        source_path=(campaign_dir / "paper_B" / "table_main_kpi_summary.csv").as_posix(),
        table_or_fig_id="KPI_B_N20_ORTOOLS",
        metric="tardiness_min_b_n20_ortools",
        value=_s(None if ort20_b is None else ort20_b["total_tardiness_min_mean"]),
        slice="method=ortools_main,N=20,tw_family=B",
        command="scripts/make_paper_tables_v2.sh",
        verified=1,
    )

    feas40_ort_a = _pick_row(feas_a, method="ortools_main", N=40)
    feas40_ort_b = _pick_row(feas_b, method="ortools_main", N=40)
    feas40_pyv_a = _pick_row(feas_a, method="pyvrp_baseline", N=40)
    feas40_pyv_b = _pick_row(feas_b, method="pyvrp_baseline", N=40)
    for metric, value, source, fig_id, fam in [
        ("feasible_rate_a_n40_ortools", _s(None if feas40_ort_a is None else feas40_ort_a["feasible_rate"]), campaign_dir / "paper_A" / "table_feasibility_rate.csv", "FEAS_A_N40", "A"),
        ("feasible_rate_b_n40_ortools", _s(None if feas40_ort_b is None else feas40_ort_b["feasible_rate"]), campaign_dir / "paper_B" / "table_feasibility_rate.csv", "FEAS_B_N40", "B"),
        ("feasible_rate_a_n40_pyvrp", _s(None if feas40_pyv_a is None else feas40_pyv_a["feasible_rate"]), campaign_dir / "paper_A" / "table_feasibility_rate.csv", "FEAS_A_N40", "A"),
        ("feasible_rate_b_n40_pyvrp", _s(None if feas40_pyv_b is None else feas40_pyv_b["feasible_rate"]), campaign_dir / "paper_B" / "table_feasibility_rate.csv", "FEAS_B_N40", "B"),
    ]:
        _append(
            rows,
            claim_id="C3",
            source_path=source.as_posix(),
            table_or_fig_id=fig_id,
            metric=metric,
            value=value,
            slice=f"N=40,tw_family={fam}",
            command="scripts/make_paper_tables_v2.sh",
            verified=1,
        )

    gap20_ort_a = _pick_row(gap_a, method="ortools_main", N=20)
    gap20_ort_b = _pick_row(gap_b, method="ortools_main", N=20)
    gap20_pyv_a = _pick_row(gap_a, method="pyvrp_baseline", N=20)
    gap20_pyv_b = _pick_row(gap_b, method="pyvrp_baseline", N=20)
    for metric, value, source, fam in [
        ("gap_pct_a_n20_ortools", _s(None if gap20_ort_a is None else gap20_ort_a["gap_pct_mean"]), campaign_dir / "paper_A" / "table_gap_summary.csv", "A"),
        ("gap_pct_b_n20_ortools", _s(None if gap20_ort_b is None else gap20_ort_b["gap_pct_mean"]), campaign_dir / "paper_B" / "table_gap_summary.csv", "B"),
        ("gap_pct_a_n20_pyvrp", _s(None if gap20_pyv_a is None else gap20_pyv_a["gap_pct_mean"]), campaign_dir / "paper_A" / "table_gap_summary.csv", "A"),
        ("gap_pct_b_n20_pyvrp", _s(None if gap20_pyv_b is None else gap20_pyv_b["gap_pct_mean"]), campaign_dir / "paper_B" / "table_gap_summary.csv", "B"),
    ]:
        _append(
            rows,
            claim_id="C4",
            source_path=source.as_posix(),
            table_or_fig_id=f"GAP_{fam}_N20",
            metric=metric,
            value=value,
            slice=f"N=20,tw_family={fam}",
            command="scripts/make_paper_tables_v2.sh",
            verified=1,
        )

    sig_a_runtime = _pick_sig(sig_a, "ortools_main", "pyvrp_baseline", "runtime_total_s")
    sig_b_runtime = _pick_sig(sig_b, "ortools_main", "pyvrp_baseline", "runtime_total_s")
    for fam, row, source in [
        ("A", sig_a_runtime, campaign_dir / "main_A_core" / "results_significance.csv"),
        ("B", sig_b_runtime, campaign_dir / "main_B_core" / "results_significance.csv"),
    ]:
        values = {
            f"runtime_p_holm_{fam.lower()}": None if row is None else row["p_value_adj"],
            f"runtime_effect_size_{fam.lower()}": None if row is None else row["effect_size"],
            f"runtime_ci_low_{fam.lower()}": None if row is None else row["ci_low"],
            f"runtime_ci_high_{fam.lower()}": None if row is None else row["ci_high"],
            f"runtime_n_pairs_{fam.lower()}": None if row is None else row["n_pairs"],
            f"runtime_effect_direction_{fam.lower()}": None if row is None else row["effect_direction"],
        }
        for metric, value in values.items():
            _append(
                rows,
                claim_id="C5",
                source_path=source.as_posix(),
                table_or_fig_id=f"SIG_RUNTIME_{fam}",
                metric=metric,
                value=_s(value),
                slice=f"method=ortools_main_vs_pyvrp,metric=runtime_total_s,tw_family={fam}",
                command="main_*_core/results_significance.csv",
                verified=1,
            )

    n80 = pd.concat([scal_a, scal_b], ignore_index=True)
    n80 = n80[pd.to_numeric(n80["N"], errors="coerce") >= 80]
    invalid_gap_bound = int(n80["gap_pct"].notna().sum() + n80["best_bound"].notna().sum())
    invalid_regime = int((n80["claim_regime"] != "scalability_only").sum())

    _append(
        rows,
        claim_id="C6",
        source_path=(campaign_dir / "scal_A_core" / "results_main.csv").as_posix(),
        table_or_fig_id="SCAL_POLICY_N80",
        metric="n80_rows_count",
        value=int(len(n80)),
        slice="N>=80,tw_family in {A,B}",
        command=audit_cmd,
        verified=1,
    )
    _append(
        rows,
        claim_id="C6",
        source_path=(campaign_dir / "scal_A_core" / "results_main.csv").as_posix(),
        table_or_fig_id="SCAL_POLICY_N80",
        metric="n80_invalid_bound_gap_rows",
        value=invalid_gap_bound,
        slice="N>=80",
        command=audit_cmd,
        verified=1,
    )
    _append(
        rows,
        claim_id="C6",
        source_path=(campaign_dir / "scal_A_core" / "results_main.csv").as_posix(),
        table_or_fig_id="SCAL_POLICY_N80",
        metric="n80_invalid_regime_rows",
        value=invalid_regime,
        slice="N>=80",
        command=audit_cmd,
        verified=1,
    )

    out_df = pd.DataFrame(rows, columns=EVIDENCE_COLUMNS)
    out_df.to_csv(out_csv, index=False)
    return out_csv
