from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from .schema import (
    RESULTS_MAIN_COLUMNS,
    RESULTS_ROUTES_COLUMNS,
    RESULTS_SIGNIFICANCE_COLUMNS,
    RouteRecord,
    RunResult,
    SignificanceResult,
)


def _ensure_columns(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[list(columns)]


def write_results_main(output_path: Path, rows: Iterable[RunResult]) -> pd.DataFrame:
    df = pd.DataFrame([row.to_row() for row in rows])
    if df.empty:
        df = pd.DataFrame(columns=RESULTS_MAIN_COLUMNS)
    df = _ensure_columns(df, RESULTS_MAIN_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def write_results_routes(output_path: Path, rows: Iterable[RouteRecord]) -> pd.DataFrame:
    df = pd.DataFrame([row.__dict__ for row in rows])
    if df.empty:
        df = pd.DataFrame(columns=RESULTS_ROUTES_COLUMNS)
    df = _ensure_columns(df, RESULTS_ROUTES_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def write_results_significance(
    output_path: Path, rows: Iterable[SignificanceResult]
) -> pd.DataFrame:
    df = pd.DataFrame([row.to_row() for row in rows])
    if df.empty:
        df = pd.DataFrame(columns=RESULTS_SIGNIFICANCE_COLUMNS)
    df = _ensure_columns(df, RESULTS_SIGNIFICANCE_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def resolve_output_paths(main_output_path: str | Path) -> tuple[Path, Path, Path]:
    main_path = Path(main_output_path)
    base_dir = main_path.parent
    routes_path = base_dir / "results_routes.csv"
    sig_path = base_dir / "results_significance.csv"
    return main_path, routes_path, sig_path
