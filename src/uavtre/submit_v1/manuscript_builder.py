from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd


def _load(path: Path) -> pd.DataFrame:
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


def _fmt_cell(value) -> str:
    if value is None or pd.isna(value):
        return "NA"
    if isinstance(value, (int, float)):
        return f"{value:.4f}"
    return _latex_escape(str(value))


def _to_latex_table(df: pd.DataFrame, caption: str, label: str) -> str:
    cols = [str(c) for c in df.columns]
    aligns = "l" * len(cols)

    lines: list[str] = []
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append(f"\\caption{{{_latex_escape(caption)}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append(f"\\begin{{tabular}}{{{aligns}}}")
    lines.append("\\toprule")
    lines.append(" & ".join(_latex_escape(c) for c in cols) + r" \\")
    lines.append("\\midrule")

    for _, row in df.iterrows():
        values = [_fmt_cell(row[c]) for c in df.columns]
        lines.append(" & ".join(values) + r" \\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def generate_assets(*, campaign_dir: Path, generated_root: Path) -> list[Path]:
    tables_dir = generated_root / "tables"
    figures_dir = generated_root / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    sources = {
        "table_main_kpi_combined.tex": (
            campaign_dir / "paper_combined" / "table_main_kpi_summary.csv",
            "Main KPI summary (combined families)",
            "tab:main_kpi_combined",
        ),
        "table_gap_combined.tex": (
            campaign_dir / "paper_combined" / "table_gap_summary.csv",
            "Gap summary (combined families)",
            "tab:gap_combined",
        ),
        "table_feasibility_combined.tex": (
            campaign_dir / "paper_combined" / "table_feasibility_rate.csv",
            "Feasibility rates (combined families)",
            "tab:feasibility_combined",
        ),
        "table_scalability_combined.tex": (
            campaign_dir / "paper_combined" / "table_scalability_raw.csv",
            "Scalability raw records (combined families)",
            "tab:scalability_combined",
        ),
        "table_significance_A.tex": (
            campaign_dir / "main_A_core" / "results_significance.csv",
            "Significance summary (Family A)",
            "tab:significance_a",
        ),
        "table_significance_B.tex": (
            campaign_dir / "main_B_core" / "results_significance.csv",
            "Significance summary (Family B)",
            "tab:significance_b",
        ),
    }

    for out_name, (src, caption, label) in sources.items():
        df = _load(src)
        if "table_scalability_raw" in out_name and len(df) > 40:
            df = df.head(40)
        latex = _to_latex_table(df, caption, label)
        out_path = tables_dir / out_name
        out_path.write_text(latex, encoding="utf-8")
        written.append(out_path)

    fig_specs = [
        ("fig_performance.tex", "Performance overview from table_main_kpi_summary.csv", "fig:performance"),
        ("fig_gap.tex", "Gap trend from table_gap_summary.csv", "fig:gap"),
        ("fig_feasibility.tex", "Feasibility from table_feasibility_rate.csv", "fig:feasibility"),
        ("fig_scalability.tex", "Scalability profile from table_scalability_raw.csv", "fig:scalability"),
    ]
    for name, text, label in fig_specs:
        fig_tex = (
            "\\begin{figure}[htbp]\n"
            "\\centering\n"
            "\\fbox{\\parbox{0.9\\linewidth}{\\centering "
            + _latex_escape(text)
            + "}}\n"
            + f"\\caption{{{_latex_escape(text)}}}\n"
            + f"\\label{{{label}}}\n"
            + "\\end{figure}\n"
        )
        out_path = figures_dir / name
        out_path.write_text(fig_tex, encoding="utf-8")
        written.append(out_path)

    return written


def compile_manuscript(*, root: Path, manuscript_root: Path, outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    main_tex = manuscript_root / "main.tex"
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
        log = outdir / "latexmk_submit_v1.log"
        log.write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")
        raise RuntimeError(f"latexmk failed (see {log.as_posix()})")

    pdf = outdir / "main.pdf"
    if not pdf.exists():
        raise FileNotFoundError(pdf)
    return pdf
