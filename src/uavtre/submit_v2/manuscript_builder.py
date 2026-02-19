from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import pandas as pd

_METHOD_LABELS: dict[str, str] = {
    "highs_exact_bound": "HiGHS (MIP)",
    "ortools_main": "OR-Tools (soft TW)",
    "pyvrp_baseline": "PyVRP (hard TW)",
}



def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
        .replace("$", "\\$")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def _fmt(x: float | int | None, nd: int) -> str:
    if x is None:
        return "--"
    try:
        v = float(x)
    except Exception:
        return "--"
    if not math.isfinite(v):
        return "--"
    return f"{v:.{nd}f}"


def _mean_std(df: pd.DataFrame, mean_col: str, std_col: str, nd_mean: int, nd_std: int) -> list[str]:
    out: list[str] = []
    for _, row in df.iterrows():
        m = row.get(mean_col)
        s = row.get(std_col)
        out.append(f"{_fmt(m, nd_mean)} ({_fmt(s, nd_std)})")
    return out


def _write_table(
    *,
    out_path: Path,
    caption: str,
    label: str,
    columns: list[str],
    rows: list[list[str]],
    notes: str | None = None,
    col_align: str | None = None,
    fit_width: bool = False,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if col_align is None:
        col_align = "l" + "r" * (len(columns) - 1)

    lines: list[str] = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append(f"\\caption{{{_latex_escape(caption)}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("{\\small")
    lines.append("\\setlength{\\tabcolsep}{4pt}")
    if fit_width:
        lines.append("\\resizebox{\\linewidth}{!}{%")
    lines.append(f"\\begin{{tabular}}{{{col_align}}}")
    lines.append("\\toprule")
    lines.append(" & ".join(_latex_escape(c) for c in columns) + r" \\")
    lines.append("\\midrule")
    for r in rows:
        lines.append(" & ".join(_latex_escape(str(c)) for c in r) + r" \\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    if fit_width:
        lines.append("}")
    if notes:
        lines.append("\\vspace{0.25em}")
        lines.append("\\begin{minipage}{0.95\\linewidth}\\footnotesize")
        lines.append(_latex_escape(notes))
        lines.append("\\end{minipage}")
    lines.append("}")
    lines.append("\\end{table}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def _prepare_kpi_table(df: pd.DataFrame) -> list[list[str]]:
    """Service KPI table rows (on-time and total tardiness)."""

    df = df.copy()

    # Keep a stable method order.
    method_order = ["highs_exact_bound", "ortools_main", "pyvrp_baseline"]
    df["method"] = df["method"].astype(str)
    df["method_rank"] = df["method"].apply(lambda m: method_order.index(m) if m in method_order else 99)
    df = df.sort_values(["N", "method_rank", "method"], ascending=[True, True, True])

    on_time = _mean_std(df, "on_time_pct_mean", "on_time_pct_std", 1, 1)
    tard = _mean_std(df, "total_tardiness_min_mean", "total_tardiness_min_std", 1, 1)

    rows: list[list[str]] = []
    for i, row in df.reset_index(drop=True).iterrows():
        rows.append(
            [
                _METHOD_LABELS.get(str(row["method"]), str(row["method"])),
                str(int(round(float(row["N"])))) if pd.notna(row.get("N")) else "--",
                on_time[i],
                tard[i],
            ]
        )
    return rows


def _prepare_cost_table(df: pd.DataFrame) -> list[list[str]]:
    """Cost proxy table rows (energy, risk, runtime)."""

    df = df.copy()

    method_order = ["highs_exact_bound", "ortools_main", "pyvrp_baseline"]
    df["method"] = df["method"].astype(str)
    df["method_rank"] = df["method"].apply(lambda m: method_order.index(m) if m in method_order else 99)
    df = df.sort_values(["N", "method_rank", "method"], ascending=[True, True, True])

    energy = _mean_std(df, "total_energy_mean", "total_energy_std", 0, 0)
    risk = _mean_std(df, "risk_mean_mean", "risk_mean_std", 3, 3)
    runtime = _mean_std(df, "runtime_total_s_mean", "runtime_total_s_std", 2, 2)

    rows: list[list[str]] = []
    for i, row in df.reset_index(drop=True).iterrows():
        rows.append(
            [
                _METHOD_LABELS.get(str(row["method"]), str(row["method"])),
                str(int(round(float(row["N"])))) if pd.notna(row.get("N")) else "--",
                energy[i],
                risk[i],
                runtime[i],
            ]
        )
    return rows


def _prepare_gap_table(df: pd.DataFrame) -> list[list[str]]:
    df = df.copy()

    method_order = ["highs_exact_bound", "ortools_main", "pyvrp_baseline"]
    df["method"] = df["method"].astype(str)
    df["method_rank"] = df["method"].apply(lambda m: method_order.index(m) if m in method_order else 99)
    df = df.sort_values(["N", "method_rank", "method"], ascending=[True, True, True])

    rows: list[list[str]] = []
    for _, r in df.iterrows():
        N = str(int(round(float(r["N"])))) if pd.notna(r.get("N")) else "NA"
        rows.append(
            [
                _METHOD_LABELS.get(str(r["method"]), str(r["method"])),
                N,
                _fmt(r.get("gap_pct_mean"), 1),
                _fmt(r.get("best_bound_mean"), 0),
                _fmt(r.get("incumbent_obj_mean"), 0),
            ]
        )
    return rows


def _prepare_feas_table(df: pd.DataFrame) -> list[list[str]]:
    df = df.copy()

    method_order = ["highs_exact_bound", "ortools_main", "pyvrp_baseline"]
    df["method"] = df["method"].astype(str)
    df["method_rank"] = df["method"].apply(lambda m: method_order.index(m) if m in method_order else 99)
    df = df.sort_values(["N", "method_rank", "method"], ascending=[True, True, True])

    rows: list[list[str]] = []
    for _, r in df.iterrows():
        rows.append(
            [
                _METHOD_LABELS.get(str(r["method"]), str(r["method"])),
                str(int(round(float(r["N"])))) if pd.notna(r.get("N")) else "NA",
                _fmt(r.get("feasible_rate"), 3),
            ]
        )
    return rows


def _scalability_summary(results_main: pd.DataFrame, family: str) -> pd.DataFrame:
    q = results_main[pd.to_numeric(results_main["N"], errors="coerce") == 80].copy()
    if q.empty:
        return pd.DataFrame(columns=[
            "tw_family",
            "method",
            "feasible_rate",
            "runtime_total_s_mean",
            "on_time_pct_mean",
            "total_tardiness_min_mean",
            "risk_mean_mean",
        ])

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


def _write_fig_scenario_overview(*, campaign_dir: Path, out_path: Path) -> Path:
    # Deliberately use one audited benchmark instance from the campaign (not re-generated).
    bench = campaign_dir / "benchmarks" / "main_A_core" / "seed1_N20_M3_D10_B7_K10_lo0.5_lt1.0_twA.json"
    if not bench.exists():
        # Fallback: pick any N=20 instance.
        candidates = sorted((campaign_dir / "benchmarks" / "main_A_core").glob("seed*_N20_*.json"))
        if not candidates:
            raise FileNotFoundError("no N=20 benchmark json found")
        bench = candidates[0]

    payload = json.loads(bench.read_text(encoding="utf-8"))
    scenario = payload["scenario"]
    depot = scenario["depot_xy"]
    clients = scenario["client_xy"]
    bs = scenario["bs_xy"]

    # Get one route from results_routes (OR-Tools, first non-trivial).
    routes_csv = campaign_dir / "main_A_core" / "results_routes.csv"
    routes = pd.read_csv(routes_csv)
    # Build run_id from spec.
    run_id = f"main_table_{payload['spec']['run_id']}_ortools_main"
    rr = routes[(routes["run_id"] == run_id) & (routes["route_node_sequence"].astype(str).str.contains("->"))]
    rr = rr[rr["route_node_sequence"].astype(str).str.count("->") >= 2]
    seq = None
    if not rr.empty:
        seq = str(rr.iloc[0]["route_node_sequence"])

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.0, 5.0))

    ax.scatter([c[0] for c in clients], [c[1] for c in clients], s=18, c="#1f77b4", label="Clients")
    ax.scatter([depot[0]], [depot[1]], s=60, c="#d62728", marker="*", label="Depot")
    ax.scatter([b[0] for b in bs], [b[1] for b in bs], s=35, c="#2ca02c", marker="s", label="Base stations")

    if seq and seq.count("->") >= 2:
        nodes = [int(x) for x in seq.split("->") if x.strip().isdigit()]
        xs: list[float] = []
        ys: list[float] = []
        for n in nodes:
            if n == 0:
                xs.append(float(depot[0]))
                ys.append(float(depot[1]))
            else:
                idx = n - 1
                if 0 <= idx < len(clients):
                    xs.append(float(clients[idx][0]))
                    ys.append(float(clients[idx][1]))
        if len(xs) >= 2:
            ax.plot(xs, ys, lw=1.8, c="#111111", alpha=0.9, label="Example route")

    ax.set_title("Example audited scenario and one OR-Tools route")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend(loc="best", frameon=False)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def _write_fig_bs_delta_effect(*, campaign_dir: Path, out_path: Path) -> Path:
    src = campaign_dir / "paper_combined" / "table_managerial_insight_support.csv"
    df = pd.read_csv(src)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = ["ortools_main", "pyvrp_baseline"]
    deltas = sorted(df["Delta_min"].dropna().unique().tolist())

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.6), sharey=True)
    for ax, method in zip(axes, methods):
        d = df[df["method"] == method].copy()
        for delta in deltas:
            dd = d[d["Delta_min"] == delta].sort_values("B")
            ax.plot(dd["B"], dd["risk_mean"], marker="o", lw=1.6, label=f"$\\Delta={delta}$")
        ax.set_title(_METHOD_LABELS.get(method, method))
        ax.set_xlabel("Number of base stations B")
        ax.grid(True, alpha=0.25)

    axes[0].set_ylabel("Mean arc outage risk")
    axes[1].legend(loc="best", frameon=False)
    fig.suptitle("Effect of base-station density and time-window tightness on risk")
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def _write_fig_lambda_tw_tradeoff(*, campaign_dir: Path, out_path: Path) -> Path:
    src = campaign_dir / "aggregated" / "main_combined.csv"
    df = pd.read_csv(src)

    # Focus on robust slices where lambda_tw was swept.
    q = df[(df["method"] == "ortools_main") & (pd.to_numeric(df["N"], errors="coerce").isin([20, 40]))].copy()
    if q.empty:
        raise RuntimeError("no ortools_main rows found in aggregated/main_combined.csv")

    q["lambda_tw"] = pd.to_numeric(q["lambda_tw"], errors="coerce")
    q = q[q["lambda_tw"].isin([0.0, 1.0, 5.0])]

    grp = (
        q.groupby(["tw_family", "N", "lambda_tw"], dropna=False)
        .agg(
            energy_mean=("total_energy", "mean"),
            tard_mean=("total_tardiness_min", "mean"),
            risk_mean=("risk_mean", "mean"),
        )
        .reset_index()
    )

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.6), sharey=True)
    for ax, fam in zip(axes, ["A", "B"]):
        d = grp[grp["tw_family"] == fam]
        for N in [20, 40]:
            dd = d[d["N"] == N].sort_values("lambda_tw")
            ax.plot(dd["tard_mean"], dd["energy_mean"], marker="o", lw=1.6, label=f"N={N}")
            for _, r in dd.iterrows():
                ax.annotate(f"$\\lambda_{{TW}}={int(r['lambda_tw'])}$", (r["tard_mean"], r["energy_mean"]), fontsize=8)
        ax.set_title(f"Family {fam}")
        ax.set_xlabel("Mean total tardiness (min)")
        ax.grid(True, alpha=0.25)

    axes[0].set_ylabel("Mean energy proxy")
    axes[1].legend(loc="best", frameon=False)
    fig.suptitle("Energy-tardiness tradeoff induced by soft time-window penalty")
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def _write_fig_scalability_summary(*, campaign_dir: Path, out_path: Path) -> Path:
    scal_a = pd.read_csv(campaign_dir / "scal_A_core" / "results_main.csv")
    scal_b = pd.read_csv(campaign_dir / "scal_B_core" / "results_main.csv")

    a = _scalability_summary(scal_a, "A")
    b = _scalability_summary(scal_b, "B")
    df = pd.concat([a, b], ignore_index=True)
    if df.empty:
        raise RuntimeError("scalability summary is empty")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(10.2, 6.2), sharex="col")

    for j, fam in enumerate(["A", "B"]):
        d = df[df["tw_family"] == fam].copy().sort_values("method")
        axes[0, j].bar([_METHOD_LABELS.get(str(m), str(m)) for m in d["method"].tolist()], d["feasible_rate"], color="#1f77b4")
        axes[0, j].set_title(f"Family {fam}: Feasibility")
        axes[0, j].set_ylim(0, 1.05)
        axes[0, j].grid(True, axis="y", alpha=0.25)

        axes[1, j].bar([_METHOD_LABELS.get(str(m), str(m)) for m in d["method"].tolist()], d["runtime_total_s_mean"], color="#ff7f0e")
        axes[1, j].set_title(f"Family {fam}: Runtime")
        axes[1, j].grid(True, axis="y", alpha=0.25)

    for ax in axes.flatten():
        ax.tick_params(axis="x", rotation=20)

    fig.suptitle("Scalability-only reporting at N=80 (no bound/gap)")
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def generate_assets(*, campaign_dir: Path, manuscript_root: Path) -> list[Path]:
    """Generate manuscript tables and figures from campaign outputs only."""

    generated_root = manuscript_root / "generated"
    tables_dir = generated_root / "tables"
    figures_dir = generated_root / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    # Tables.
    kpi_a = _load_csv(campaign_dir / "paper_A" / "table_main_kpi_summary.csv")
    kpi_b = _load_csv(campaign_dir / "paper_B" / "table_main_kpi_summary.csv")
    gap_a = _load_csv(campaign_dir / "paper_A" / "table_gap_summary.csv")
    gap_b = _load_csv(campaign_dir / "paper_B" / "table_gap_summary.csv")
    feas_a = _load_csv(campaign_dir / "paper_A" / "table_feasibility_rate.csv")
    feas_b = _load_csv(campaign_dir / "paper_B" / "table_feasibility_rate.csv")

    written.append(
        _write_table(
            out_path=tables_dir / "tab_kpi_A.tex",
            caption="Service KPIs (Family A): mean (std) across audited instances.",
            label="tab:kpi_A",
            columns=[
                "Method",
                "N",
                "On-time (%)",
                "Tardiness (min)",
            ],
            rows=_prepare_kpi_table(kpi_a),
            notes="On-time and tardiness are evaluated on returned routes.",
            col_align="p{3.0cm}rrr",
        )
    )
    written.append(
        _write_table(
            out_path=tables_dir / "tab_cost_A.tex",
            caption="Cost proxies (Family A): mean (std) across audited instances.",
            label="tab:cost_A",
            columns=[
                "Method",
                "N",
                "Energy",
                "Risk",
                "Runtime (s)",
            ],
            rows=_prepare_cost_table(kpi_a),
            notes="Energy is a distance-based proxy; risk is mean arc outage risk averaged over arcs.",
            col_align="p{3.0cm}rrrr",
        )
    )
    written.append(
        _write_table(
            out_path=tables_dir / "tab_kpi_B.tex",
            caption="Service KPIs (Family B stress): mean (std) across audited instances.",
            label="tab:kpi_B",
            columns=[
                "Method",
                "N",
                "On-time (%)",
                "Tardiness (min)",
            ],
            rows=_prepare_kpi_table(kpi_b),
            notes="Family B tightens/shifts time windows to stress service reliability.",
            col_align="p{3.0cm}rrr",
        )
    )
    written.append(
        _write_table(
            out_path=tables_dir / "tab_cost_B.tex",
            caption="Cost proxies (Family B stress): mean (std) across audited instances.",
            label="tab:cost_B",
            columns=[
                "Method",
                "N",
                "Energy",
                "Risk",
                "Runtime (s)",
            ],
            rows=_prepare_cost_table(kpi_b),
            notes="Energy is a distance-based proxy; risk is mean arc outage risk averaged over arcs.",
            col_align="p{3.0cm}rrrr",
        )
    )

    written.append(
        _write_table(
            out_path=tables_dir / "tab_gap_A.tex",
            caption="Bound-gap summary (Family A). Gap reported only for N in {20,40}.",
            label="tab:gap_A",
            columns=["Method", "N", "Gap (%)", "Best bound", "Incumbent obj."],
            rows=_prepare_gap_table(gap_a),
            notes="Bound is from HiGHS; incumbent objective is evaluated consistently across solvers.",
        )
    )
    written.append(
        _write_table(
            out_path=tables_dir / "tab_gap_B.tex",
            caption="Bound-gap summary (Family B stress). Gap reported only for N in {20,40}.",
            label="tab:gap_B",
            columns=["Method", "N", "Gap (%)", "Best bound", "Incumbent obj."],
            rows=_prepare_gap_table(gap_b),
            notes="N=80 results are scalability-only: no bound/gap values are computed or claimed.",
        )
    )

    written.append(
        _write_table(
            out_path=tables_dir / "tab_feas_A.tex",
            caption="Feasibility rates (Family A).",
            label="tab:feas_A",
            columns=["Method", "N", "Feasible rate"],
            rows=_prepare_feas_table(feas_a),
        )
    )
    written.append(
        _write_table(
            out_path=tables_dir / "tab_feas_B.tex",
            caption="Feasibility rates (Family B stress).",
            label="tab:feas_B",
            columns=["Method", "N", "Feasible rate"],
            rows=_prepare_feas_table(feas_b),
        )
    )

    # Scalability summary (derived).
    scal_a = _load_csv(campaign_dir / "scal_A_core" / "results_main.csv")
    scal_b = _load_csv(campaign_dir / "scal_B_core" / "results_main.csv")
    scal_sum = pd.concat([
        _scalability_summary(scal_a, "A"),
        _scalability_summary(scal_b, "B"),
    ], ignore_index=True)

    if not scal_sum.empty:
        rows = []
        for _, r in scal_sum.sort_values(["tw_family", "method"]).iterrows():
            rows.append(
                [
                    str(r["tw_family"]),
                    _METHOD_LABELS.get(str(r["method"]), str(r["method"])),
                    _fmt(r.get("feasible_rate"), 3),
                    _fmt(r.get("runtime_total_s_mean"), 2),
                    _fmt(r.get("on_time_pct_mean"), 1),
                    _fmt(r.get("total_tardiness_min_mean"), 1),
                    _fmt(r.get("risk_mean_mean"), 3),
                ]
            )
        written.append(
            _write_table(
                out_path=tables_dir / "tab_scalability_summary.tex",
                caption="Scalability-only summary at N=80 (no bound/gap).",
                label="tab:scalability_summary",
                columns=[
                    "TW family",
                    "Method",
                    "Feasible rate",
                    "Runtime (s)",
                    "On-time (%)",
                    "Tardiness (min)",
                    "Risk",
                ],
                rows=rows,
                notes="Per policy, N=80 does not report bounds/gaps and is used only for scalability characterization.",
                col_align="lp{2.7cm}rrrrr",
                fit_width=True,
            )
        )

    managerial = _load_csv(campaign_dir / "paper_combined" / "table_managerial_insight_support.csv")
    # Keep the managerial table compact: show risk and on-time only.
    mgr_rows = []
    for _, r in managerial.sort_values(["method", "B", "Delta_min"]).iterrows():
        mgr_rows.append(
            [
                _METHOD_LABELS.get(str(r["method"]), str(r["method"])),
                str(int(r["B"])),
                str(int(r["Delta_min"])),
                _fmt(r.get("on_time_pct"), 1),
                _fmt(r.get("risk_mean"), 3),
            ]
        )
    written.append(
        _write_table(
            out_path=tables_dir / "tab_managerial_support.tex",
            caption="Managerial insight support: effect of base-station density (B) and time-window tightness (Delta) on risk and on-time.",
            label="tab:managerial_support",
            columns=["Method", "B", "Delta_min (min)", "On-time (%)", "Risk"],
            rows=mgr_rows,
            notes="Values are aggregated over robustness slices and reported for interpretability.",
            col_align="lrrrr",
        )
    )

    risk_signal = _load_csv(campaign_dir / "paper_combined" / "table_risk_signal_check.csv")
    rs_rows = []
    for _, r in risk_signal.sort_values(["method"]).iterrows():
        rs_rows.append([_METHOD_LABELS.get(str(r["method"]), str(r["method"])), _fmt(r.get("risk_mean_avg"), 3)])
    written.append(
        _write_table(
            out_path=tables_dir / "tab_risk_signal.tex",
            caption="Risk signal check: mean risk across main tables.",
            label="tab:risk_signal",
            columns=["Method", "Mean risk"],
            rows=rs_rows,
        )
    )

    # Figures.
    written.append(
        _write_fig_scenario_overview(
            campaign_dir=campaign_dir,
            out_path=figures_dir / "fig_scenario_overview.pdf",
        )
    )
    written.append(
        _write_fig_bs_delta_effect(
            campaign_dir=campaign_dir,
            out_path=figures_dir / "fig_bs_delta_effect.pdf",
        )
    )
    written.append(
        _write_fig_lambda_tw_tradeoff(
            campaign_dir=campaign_dir,
            out_path=figures_dir / "fig_tradeoff_lambda_tw.pdf",
        )
    )
    written.append(
        _write_fig_scalability_summary(
            campaign_dir=campaign_dir,
            out_path=figures_dir / "fig_scalability_summary.pdf",
        )
    )

    return written


def compile_manuscript(*, root: Path, manuscript_root: Path, outdir: Path, variant: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)

    if variant not in {"anonymous", "camera_ready"}:
        raise ValueError(f"unknown variant: {variant}")

    # `main.tex` is camera-ready by default; anonymous wrapper hides author identifiers.
    main_tex = manuscript_root / ("main_anonymous.tex" if variant == "anonymous" else "main.tex")
    if not main_tex.exists():
        raise FileNotFoundError(main_tex)

    cmd = [
        "latexmk",
        "-pdf",
        "-g",
        "-cd",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-outdir={outdir.resolve().as_posix()}",
        main_tex.relative_to(root).as_posix(),
    ]

    proc = subprocess.run(cmd, cwd=root, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        log = outdir / "latexmk_submit_v2.log"
        log.write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")
        raise RuntimeError(f"latexmk failed for {variant} (see {log.as_posix()})")

    pdf = outdir / "main.pdf"
    if not pdf.exists():
        # latexmk uses jobname derived from input; normalize to main.pdf.
        # For the anonymous wrapper, output will still be main.pdf because file is main_anonymous.tex.
        # We copy if needed.
        candidates = list(outdir.glob("*.pdf"))
        if candidates:
            candidates[0].replace(pdf)
        if not pdf.exists():
            raise FileNotFoundError(pdf)

    return pdf
