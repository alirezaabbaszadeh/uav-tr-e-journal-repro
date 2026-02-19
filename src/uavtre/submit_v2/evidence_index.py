from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


EVIDENCE_COLUMNS_V2 = [
    "evid_id",
    "claim_id",
    "source_path",
    "table_or_fig_id",
    "metric",
    "value",
    "slice",
    "unit",
    "command",
    "verified",
]


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _safe_num(x: Any) -> float | None:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    try:
        v = float(x)
    except Exception:
        return None
    if not math.isfinite(v):
        return None
    return v


def _san(s: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in "-_" ) else "_" for ch in s)


def _evid_id(*parts: Any) -> str:
    return _san("_".join(str(p) for p in parts if p is not None and str(p) != ""))


def _append(
    rows: list[dict[str, Any]],
    *,
    evid_id: str,
    claim_id: str | None,
    source_path: str,
    table_or_fig_id: str,
    metric: str,
    value: Any,
    slice: str,
    unit: str,
    command: str,
    verified: int,
) -> None:
    rows.append(
        {
            "evid_id": evid_id,
            "claim_id": claim_id or "",
            "source_path": source_path,
            "table_or_fig_id": table_or_fig_id,
            "metric": metric,
            "value": value,
            "slice": slice,
            "unit": unit,
            "command": command,
            "verified": int(verified),
        }
    )


def _iter_table_cells(
    *,
    df: pd.DataFrame,
    table_id: str,
    source_path: str,
    slice_cols: Iterable[str],
    value_cols: Iterable[tuple[str, str]],
    unit_default: str,
    command: str,
) -> Iterable[dict[str, Any]]:
    slice_cols = list(slice_cols)
    for _, row in df.iterrows():
        parts = [f"{c}={row[c]}" for c in slice_cols if c in df.columns]
        slice_txt = ",".join(parts)
        for col, unit in value_cols:
            if col not in df.columns:
                continue
            value = row[col]
            evid = _evid_id(table_id, slice_txt, col)
            yield {
                "evid_id": evid,
                "source_path": source_path,
                "table_or_fig_id": table_id,
                "metric": col,
                "value": value,
                "slice": slice_txt,
                "unit": unit or unit_default,
                "command": command,
            }


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


def build_evidence_index(
    *,
    campaign_dir: Path,
    campaign_id: str,
    out_csv: Path,
    audit_json: Path | None,
) -> Path:
    """Build a manuscript-facing, campaign-locked evidence index.

    Notes:
    - This is a *post-processing* index; it does not rerun solvers.
    - We keep claim metrics (C1..C6) compatible with submit_v1 claim guard.
    - We also include additional rows for manuscript tables/figures.
    """

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    audit_cmd = (
        "PYTHONPATH=src .venv/bin/python scripts/audit_journal_readiness.py "
        f"--campaign-id {campaign_id} --campaign-root outputs/campaigns "
        f"--json-out outputs/audit/journal_readiness_{campaign_id}.json "
        "--fail-on-critical --fail-on-high"
    )

    # Core campaign artifacts.
    main_a = _load_csv(campaign_dir / "main_A_core" / "results_main.csv")
    main_b = _load_csv(campaign_dir / "main_B_core" / "results_main.csv")
    scal_a = _load_csv(campaign_dir / "scal_A_core" / "results_main.csv")
    scal_b = _load_csv(campaign_dir / "scal_B_core" / "results_main.csv")

    # Paper-ready summary tables produced by v3 campaign scripts.
    kpi_a = _load_csv(campaign_dir / "paper_A" / "table_main_kpi_summary.csv")
    kpi_b = _load_csv(campaign_dir / "paper_B" / "table_main_kpi_summary.csv")
    gap_a = _load_csv(campaign_dir / "paper_A" / "table_gap_summary.csv")
    gap_b = _load_csv(campaign_dir / "paper_B" / "table_gap_summary.csv")
    feas_a = _load_csv(campaign_dir / "paper_A" / "table_feasibility_rate.csv")
    feas_b = _load_csv(campaign_dir / "paper_B" / "table_feasibility_rate.csv")

    managerial = _load_csv(campaign_dir / "paper_combined" / "table_managerial_insight_support.csv")
    risk_signal = _load_csv(campaign_dir / "paper_combined" / "table_risk_signal_check.csv")

    sig_a = _load_csv(campaign_dir / "main_A_core" / "results_significance.csv")
    sig_b = _load_csv(campaign_dir / "main_B_core" / "results_significance.csv")

    audit_overall_pass = 0
    if audit_json and audit_json.exists():
        payload = json.loads(audit_json.read_text(encoding="utf-8"))
        audit_overall_pass = int(bool(payload.get("summary", {}).get("overall_pass", False)))

    rows: list[dict[str, Any]] = []

    # C1: audit pass + core coverage.
    _append(
        rows,
        evid_id=_evid_id("AUDIT", "overall_pass"),
        claim_id="C1",
        source_path=(audit_json.as_posix() if audit_json else f"outputs/audit/journal_readiness_{campaign_id}.json"),
        table_or_fig_id="AUDIT_SUMMARY",
        metric="audit_overall_pass",
        value=audit_overall_pass,
        slice="summary",
        unit="bool",
        command=audit_cmd,
        verified=1,
    )

    def _coverage_ok(df: pd.DataFrame, required: set[int]) -> int:
        found = set(pd.to_numeric(df["N"], errors="coerce").dropna().astype(int).tolist())
        return int(required.issubset(found))

    _append(
        rows,
        evid_id=_evid_id("COVERAGE", "main_A", "10_20_40"),
        claim_id="C1",
        source_path=(campaign_dir / "main_A_core" / "results_main.csv").as_posix(),
        table_or_fig_id="MAIN_A_COVERAGE",
        metric="coverage_main_a_10_20_40",
        value=_coverage_ok(main_a, {10, 20, 40}),
        slice="N in {10,20,40}",
        unit="bool",
        command=audit_cmd,
        verified=1,
    )
    _append(
        rows,
        evid_id=_evid_id("COVERAGE", "main_B", "10_20_40"),
        claim_id="C1",
        source_path=(campaign_dir / "main_B_core" / "results_main.csv").as_posix(),
        table_or_fig_id="MAIN_B_COVERAGE",
        metric="coverage_main_b_10_20_40",
        value=_coverage_ok(main_b, {10, 20, 40}),
        slice="N in {10,20,40}",
        unit="bool",
        command=audit_cmd,
        verified=1,
    )

    # C6: enforce N=80 scalability-only reporting.
    n80 = pd.concat([scal_a, scal_b], ignore_index=True)
    n80 = n80[pd.to_numeric(n80["N"], errors="coerce") >= 80]
    invalid_gap_bound = int(n80["gap_pct"].notna().sum() + n80["best_bound"].notna().sum())
    invalid_regime = int((n80["claim_regime"] != "scalability_only").sum())

    _append(
        rows,
        evid_id=_evid_id("SCAL", "n80_rows_count"),
        claim_id="C6",
        source_path=(campaign_dir / "scal_A_core" / "results_main.csv").as_posix(),
        table_or_fig_id="SCAL_POLICY_N80",
        metric="n80_rows_count",
        value=int(len(n80)),
        slice="N>=80,tw_family in {A,B}",
        unit="count",
        command=audit_cmd,
        verified=1,
    )
    _append(
        rows,
        evid_id=_evid_id("SCAL", "n80_invalid_bound_gap_rows"),
        claim_id="C6",
        source_path=(campaign_dir / "scal_A_core" / "results_main.csv").as_posix(),
        table_or_fig_id="SCAL_POLICY_N80",
        metric="n80_invalid_bound_gap_rows",
        value=invalid_gap_bound,
        slice="N>=80",
        unit="count",
        command=audit_cmd,
        verified=1,
    )
    _append(
        rows,
        evid_id=_evid_id("SCAL", "n80_invalid_regime_rows"),
        claim_id="C6",
        source_path=(campaign_dir / "scal_A_core" / "results_main.csv").as_posix(),
        table_or_fig_id="SCAL_POLICY_N80",
        metric="n80_invalid_regime_rows",
        value=invalid_regime,
        slice="N>=80",
        unit="count",
        command=audit_cmd,
        verified=1,
    )

    # C2/C3/C4: extract key cells (backward compatible metrics).
    def _pick(df: pd.DataFrame, method: str, N: int) -> pd.Series | None:
        q = df[(df["method"] == method) & (pd.to_numeric(df["N"], errors="coerce") == N)]
        if q.empty:
            return None
        return q.iloc[0]

    ort20_a = _pick(kpi_a, "ortools_main", 20)
    ort20_b = _pick(kpi_b, "ortools_main", 20)

    _append(
        rows,
        evid_id=_evid_id("C2", "A", "N20", "on_time"),
        claim_id="C2",
        source_path=(campaign_dir / "paper_A" / "table_main_kpi_summary.csv").as_posix(),
        table_or_fig_id="TAB_KPI_A",
        metric="on_time_pct_a_n20_ortools",
        value=(None if ort20_a is None else _safe_num(ort20_a.get("on_time_pct_mean"))),
        slice="method=ortools_main,N=20,tw_family=A",
        unit="percent",
        command="scripts/make_paper_tables_v2.sh",
        verified=1,
    )
    _append(
        rows,
        evid_id=_evid_id("C2", "B", "N20", "on_time"),
        claim_id="C2",
        source_path=(campaign_dir / "paper_B" / "table_main_kpi_summary.csv").as_posix(),
        table_or_fig_id="TAB_KPI_B",
        metric="on_time_pct_b_n20_ortools",
        value=(None if ort20_b is None else _safe_num(ort20_b.get("on_time_pct_mean"))),
        slice="method=ortools_main,N=20,tw_family=B",
        unit="percent",
        command="scripts/make_paper_tables_v2.sh",
        verified=1,
    )
    _append(
        rows,
        evid_id=_evid_id("C2", "A", "N20", "tardiness"),
        claim_id="C2",
        source_path=(campaign_dir / "paper_A" / "table_main_kpi_summary.csv").as_posix(),
        table_or_fig_id="TAB_KPI_A",
        metric="tardiness_min_a_n20_ortools",
        value=(None if ort20_a is None else _safe_num(ort20_a.get("total_tardiness_min_mean"))),
        slice="method=ortools_main,N=20,tw_family=A",
        unit="min",
        command="scripts/make_paper_tables_v2.sh",
        verified=1,
    )
    _append(
        rows,
        evid_id=_evid_id("C2", "B", "N20", "tardiness"),
        claim_id="C2",
        source_path=(campaign_dir / "paper_B" / "table_main_kpi_summary.csv").as_posix(),
        table_or_fig_id="TAB_KPI_B",
        metric="tardiness_min_b_n20_ortools",
        value=(None if ort20_b is None else _safe_num(ort20_b.get("total_tardiness_min_mean"))),
        slice="method=ortools_main,N=20,tw_family=B",
        unit="min",
        command="scripts/make_paper_tables_v2.sh",
        verified=1,
    )

    # feasibility @ N=40.
    feas40_ort_a = _pick(feas_a, "ortools_main", 40)
    feas40_ort_b = _pick(feas_b, "ortools_main", 40)
    feas40_pyv_a = _pick(feas_a, "pyvrp_baseline", 40)
    feas40_pyv_b = _pick(feas_b, "pyvrp_baseline", 40)

    for metric, value, fam, source in [
        ("feasible_rate_a_n40_ortools", None if feas40_ort_a is None else _safe_num(feas40_ort_a.get("feasible_rate")), "A", campaign_dir / "paper_A" / "table_feasibility_rate.csv"),
        ("feasible_rate_b_n40_ortools", None if feas40_ort_b is None else _safe_num(feas40_ort_b.get("feasible_rate")), "B", campaign_dir / "paper_B" / "table_feasibility_rate.csv"),
        ("feasible_rate_a_n40_pyvrp", None if feas40_pyv_a is None else _safe_num(feas40_pyv_a.get("feasible_rate")), "A", campaign_dir / "paper_A" / "table_feasibility_rate.csv"),
        ("feasible_rate_b_n40_pyvrp", None if feas40_pyv_b is None else _safe_num(feas40_pyv_b.get("feasible_rate")), "B", campaign_dir / "paper_B" / "table_feasibility_rate.csv"),
    ]:
        _append(
            rows,
            evid_id=_evid_id("C3", fam, "N40", metric),
            claim_id="C3",
            source_path=source.as_posix(),
            table_or_fig_id=f"TAB_FEAS_{fam}",
            metric=metric,
            value=value,
            slice=f"N=40,tw_family={fam}",
            unit="rate",
            command="scripts/make_paper_tables_v2.sh",
            verified=1,
        )

    # gap @ N=20.
    gap20_ort_a = _pick(gap_a, "ortools_main", 20)
    gap20_ort_b = _pick(gap_b, "ortools_main", 20)
    gap20_pyv_a = _pick(gap_a, "pyvrp_baseline", 20)
    gap20_pyv_b = _pick(gap_b, "pyvrp_baseline", 20)

    for metric, value, fam, source in [
        ("gap_pct_a_n20_ortools", None if gap20_ort_a is None else _safe_num(gap20_ort_a.get("gap_pct_mean")), "A", campaign_dir / "paper_A" / "table_gap_summary.csv"),
        ("gap_pct_b_n20_ortools", None if gap20_ort_b is None else _safe_num(gap20_ort_b.get("gap_pct_mean")), "B", campaign_dir / "paper_B" / "table_gap_summary.csv"),
        ("gap_pct_a_n20_pyvrp", None if gap20_pyv_a is None else _safe_num(gap20_pyv_a.get("gap_pct_mean")), "A", campaign_dir / "paper_A" / "table_gap_summary.csv"),
        ("gap_pct_b_n20_pyvrp", None if gap20_pyv_b is None else _safe_num(gap20_pyv_b.get("gap_pct_mean")), "B", campaign_dir / "paper_B" / "table_gap_summary.csv"),
    ]:
        _append(
            rows,
            evid_id=_evid_id("C4", fam, "N20", metric),
            claim_id="C4",
            source_path=source.as_posix(),
            table_or_fig_id=f"TAB_GAP_{fam}",
            metric=metric,
            value=value,
            slice=f"N=20,tw_family={fam}",
            unit="percent",
            command="scripts/make_paper_tables_v2.sh",
            verified=1,
        )

    # C5: runtime significance (Holm-adjusted) for OR-Tools vs PyVRP.
    sig_a_runtime = _pick_sig(sig_a, "ortools_main", "pyvrp_baseline", "runtime_total_s")
    sig_b_runtime = _pick_sig(sig_b, "ortools_main", "pyvrp_baseline", "runtime_total_s")

    for fam, row, source in [
        ("A", sig_a_runtime, campaign_dir / "main_A_core" / "results_significance.csv"),
        ("B", sig_b_runtime, campaign_dir / "main_B_core" / "results_significance.csv"),
    ]:
        if row is None:
            continue
        # Keep the legacy metric names used by submit_v1 claims.
        pairs = {
            f"runtime_p_holm_{fam.lower()}": row.get("p_value_adj"),
            f"runtime_effect_size_{fam.lower()}": row.get("effect_size"),
            f"runtime_ci_low_{fam.lower()}": row.get("ci_low"),
            f"runtime_ci_high_{fam.lower()}": row.get("ci_high"),
            f"runtime_n_pairs_{fam.lower()}": row.get("n_pairs"),
            f"runtime_effect_direction_{fam.lower()}": row.get("effect_direction"),
        }
        for metric, value in pairs.items():
            _append(
                rows,
                evid_id=_evid_id("C5", fam, metric),
                claim_id="C5",
                source_path=source.as_posix(),
                table_or_fig_id=f"SIG_RUNTIME_{fam}",
                metric=metric,
                value=(
                    str(value)
                    if "effect_direction" in metric
                    else _safe_num(value)
                ),
                slice=f"comparison=ortools_main_vs_pyvrp_baseline,metric=runtime_total_s,tw_family={fam}",
                unit="mixed",
                command="main_*_core/results_significance.csv",
                verified=1,
            )

    # Additional manuscript evidence: full KPI/gap/feas tables (means only).
    kpi_value_cols = [
        ("on_time_pct_mean", "percent"),
        ("total_tardiness_min_mean", "min"),
        ("total_energy_mean", "energy"),
        ("risk_mean_mean", "rate"),
        ("runtime_total_s_mean", "s"),
    ]
    for fam, df, table_id, src in [
        ("A", kpi_a, "TAB_KPI_A", campaign_dir / "paper_A" / "table_main_kpi_summary.csv"),
        ("B", kpi_b, "TAB_KPI_B", campaign_dir / "paper_B" / "table_main_kpi_summary.csv"),
    ]:
        for cell in _iter_table_cells(
            df=df,
            table_id=table_id,
            source_path=src.as_posix(),
            slice_cols=["method", "N"],
            value_cols=kpi_value_cols,
            unit_default="",
            command="scripts/make_paper_tables_v2.sh",
        ):
            _append(
                rows,
                evid_id=cell["evid_id"],
                claim_id="",
                source_path=cell["source_path"],
                table_or_fig_id=cell["table_or_fig_id"],
                metric=cell["metric"],
                value=_safe_num(cell["value"]),
                slice=f"tw_family={fam},{cell['slice']}",
                unit=cell["unit"],
                command=cell["command"],
                verified=1,
            )

    gap_value_cols = [
        ("gap_pct_mean", "percent"),
        ("best_bound_mean", "obj"),
        ("incumbent_obj_mean", "obj"),
    ]
    for fam, df, table_id, src in [
        ("A", gap_a, "TAB_GAP_A", campaign_dir / "paper_A" / "table_gap_summary.csv"),
        ("B", gap_b, "TAB_GAP_B", campaign_dir / "paper_B" / "table_gap_summary.csv"),
    ]:
        for cell in _iter_table_cells(
            df=df,
            table_id=table_id,
            source_path=src.as_posix(),
            slice_cols=["method", "N"],
            value_cols=gap_value_cols,
            unit_default="",
            command="scripts/make_paper_tables_v2.sh",
        ):
            _append(
                rows,
                evid_id=cell["evid_id"],
                claim_id="",
                source_path=cell["source_path"],
                table_or_fig_id=cell["table_or_fig_id"],
                metric=cell["metric"],
                value=_safe_num(cell["value"]),
                slice=f"tw_family={fam},{cell['slice']}",
                unit=cell["unit"],
                command=cell["command"],
                verified=1,
            )

    feas_value_cols = [("feasible_rate", "rate")]
    for fam, df, table_id, src in [
        ("A", feas_a, "TAB_FEAS_A", campaign_dir / "paper_A" / "table_feasibility_rate.csv"),
        ("B", feas_b, "TAB_FEAS_B", campaign_dir / "paper_B" / "table_feasibility_rate.csv"),
    ]:
        for cell in _iter_table_cells(
            df=df,
            table_id=table_id,
            source_path=src.as_posix(),
            slice_cols=["method", "N"],
            value_cols=feas_value_cols,
            unit_default="",
            command="scripts/make_paper_tables_v2.sh",
        ):
            _append(
                rows,
                evid_id=cell["evid_id"],
                claim_id="",
                source_path=cell["source_path"],
                table_or_fig_id=cell["table_or_fig_id"],
                metric=cell["metric"],
                value=_safe_num(cell["value"]),
                slice=f"tw_family={fam},{cell['slice']}",
                unit=cell["unit"],
                command=cell["command"],
                verified=1,
            )

    # Managerial insight support table cells.
    for cell in _iter_table_cells(
        df=managerial,
        table_id="TAB_MANAGERIAL_SUPPORT",
        source_path=(campaign_dir / "paper_combined" / "table_managerial_insight_support.csv").as_posix(),
        slice_cols=["method", "B", "Delta_min"],
        value_cols=[("on_time_pct", "percent"), ("total_tardiness_min", "min"), ("risk_mean", "rate")],
        unit_default="",
        command="scripts/make_paper_tables_v2.sh",
    ):
        _append(
            rows,
            evid_id=cell["evid_id"],
            claim_id="",
            source_path=cell["source_path"],
            table_or_fig_id=cell["table_or_fig_id"],
            metric=cell["metric"],
            value=_safe_num(cell["value"]),
            slice=cell["slice"],
            unit=cell["unit"],
            command=cell["command"],
            verified=1,
        )

    # Risk signal check.
    for _, row in risk_signal.iterrows():
        method = str(row.get("method"))
        _append(
            rows,
            evid_id=_evid_id("RISK_SIGNAL", method),
            claim_id="",
            source_path=(campaign_dir / "paper_combined" / "table_risk_signal_check.csv").as_posix(),
            table_or_fig_id="TAB_RISK_SIGNAL",
            metric="risk_mean_avg",
            value=_safe_num(row.get("risk_mean_avg")),
            slice=f"method={method}",
            unit="rate",
            command="scripts/make_paper_tables_v2.sh",
            verified=1,
        )

    # Scalability aggregate evidence (N=80 only). Derived from results_main.
    def _scal_summary(df: pd.DataFrame, family: str) -> pd.DataFrame:
        q = df[pd.to_numeric(df["N"], errors="coerce") == 80].copy()
        if q.empty:
            return pd.DataFrame()
        q["feasible_flag"] = pd.to_numeric(q["feasible_flag"], errors="coerce").fillna(0.0)
        grouped = q.groupby("method", dropna=False)
        out = grouped.agg(
            feasible_rate=("feasible_flag", "mean"),
            runtime_total_s_mean=("runtime_total_s", "mean"),
            on_time_pct_mean=("on_time_pct", "mean"),
            total_tardiness_min_mean=("total_tardiness_min", "mean"),
            risk_mean_mean=("risk_mean", "mean"),
        ).reset_index()
        out.insert(0, "tw_family", family)
        return out

    scal_summary = pd.concat(
        [_scal_summary(scal_a, "A"), _scal_summary(scal_b, "B")],
        ignore_index=True,
    )

    if not scal_summary.empty:
        # Add each cell as evidence.
        for cell in _iter_table_cells(
            df=scal_summary,
            table_id="TAB_SCAL_SUMMARY",
            source_path=(campaign_dir / "scal_A_core" / "results_main.csv").as_posix(),
            slice_cols=["tw_family", "method"],
            value_cols=[
                ("feasible_rate", "rate"),
                ("runtime_total_s_mean", "s"),
                ("on_time_pct_mean", "percent"),
                ("total_tardiness_min_mean", "min"),
                ("risk_mean_mean", "rate"),
            ],
            unit_default="",
            command="derived:scalability_summary_from_results_main",
        ):
            _append(
                rows,
                evid_id=cell["evid_id"],
                claim_id="",
                source_path=cell["source_path"],
                table_or_fig_id=cell["table_or_fig_id"],
                metric=cell["metric"],
                value=_safe_num(cell["value"]),
                slice=cell["slice"],
                unit=cell["unit"],
                command=cell["command"],
                verified=1,
            )

    out_df = pd.DataFrame(rows, columns=EVIDENCE_COLUMNS_V2)

    # Deterministic order for stable diffs.
    out_df = out_df.sort_values(["claim_id", "table_or_fig_id", "slice", "metric", "evid_id"]).reset_index(drop=True)
    out_df.to_csv(out_csv, index=False)
    return out_csv
