#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

import numpy as np
import pandas as pd

from uavtre.io.schema import (
    RESULTS_MAIN_COLUMNS,
    RESULTS_ROUTES_COLUMNS,
    RESULTS_SIGNIFICANCE_COLUMNS,
)


CRITICAL = "critical"
HIGH = "high"
MEDIUM = "medium"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit journal-readiness gates.")
    parser.add_argument("--output-root", default="outputs", help="Root outputs directory.")
    parser.add_argument(
        "--main-a",
        default="outputs/main_table_v2_core/results_main.csv",
        help="Main-table TW-A results_main path.",
    )
    parser.add_argument(
        "--scal-a",
        default="outputs/scalability_v2_core/results_main.csv",
        help="Scalability TW-A results_main path.",
    )
    parser.add_argument(
        "--main-b",
        default="outputs/main_table_v2_core_B/results_main.csv",
        help="Main-table TW-B results_main path.",
    )
    parser.add_argument(
        "--scal-b",
        default="outputs/scalability_v2_core_B/results_main.csv",
        help="Scalability TW-B results_main path.",
    )
    parser.add_argument("--json-out", default=None, help="Optional explicit JSON report output path.")
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit non-zero if any critical gate fails.",
    )
    return parser.parse_args()


def _gate(
    gates: List[Dict[str, object]],
    gate_id: str,
    severity: str,
    passed: bool,
    message: str,
) -> None:
    gates.append(
        {
            "gate_id": gate_id,
            "severity": severity,
            "passed": bool(passed),
            "message": message,
        }
    )


def _load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def _check_schema_main(df: pd.DataFrame) -> bool:
    return list(df.columns) == RESULTS_MAIN_COLUMNS


def _check_gap_sanity(df: pd.DataFrame) -> tuple[int, int]:
    gap = pd.to_numeric(df["gap_pct"], errors="coerce")
    neg = int((gap.dropna() < -1e-9).sum())
    inf = int(np.isinf(gap.fillna(np.nan)).sum())
    return neg, inf


def _check_exact_certification(df: pd.DataFrame) -> tuple[int, int]:
    sub = df[(df["N"] <= 10) & (df["method"] == "highs_exact_bound")]
    if sub.empty:
        return 0, 0
    exact_rows = sub[sub["claim_regime"] == "exact"]
    uncert = int(
        exact_rows["gap_pct"].isna().sum()
        + (
            pd.to_numeric(exact_rows["gap_pct"], errors="coerce")
            .fillna(0.0)
            .abs()
            > 1e-9
        ).sum()
    )
    return int(len(exact_rows)), uncert


def _check_scalability_policy(df: pd.DataFrame) -> tuple[int, int]:
    sub = df[df["N"] >= 80]
    if sub.empty:
        return 0, 0
    invalid = int(
        sub["gap_pct"].notna().sum()
        + sub["best_bound"].notna().sum()
        + (sub["claim_regime"] != "scalability_only").sum()
    )
    return int(len(sub)), invalid


def _check_git_trace(df: pd.DataFrame) -> int:
    return int(df["git_sha"].astype(str).str.contains("unknown", na=False).sum())


def _collect_families(*dfs: pd.DataFrame | None) -> List[str]:
    fam = set()
    for df in dfs:
        if df is None or "tw_family" not in df.columns:
            continue
        fam.update(df["tw_family"].dropna().astype(str).unique().tolist())
    return sorted(fam)


def _n_set(df: pd.DataFrame | None) -> Set[int]:
    if df is None or "N" not in df.columns:
        return set()
    return set(pd.to_numeric(df["N"], errors="coerce").dropna().astype(int).tolist())


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)

    main_a_path = Path(args.main_a)
    scal_a_path = Path(args.scal_a)
    main_b_path = Path(args.main_b)
    scal_b_path = Path(args.scal_b)

    main_a = _load_csv(main_a_path)
    scal_a = _load_csv(scal_a_path)
    main_b = _load_csv(main_b_path)
    scal_b = _load_csv(scal_b_path)

    gates: List[Dict[str, object]] = []

    _gate(
        gates,
        "files.main_a_exists",
        CRITICAL,
        main_a is not None,
        f"{main_a_path} {'found' if main_a is not None else 'missing'}",
    )
    _gate(
        gates,
        "files.scal_a_exists",
        CRITICAL,
        scal_a is not None,
        f"{scal_a_path} {'found' if scal_a is not None else 'missing'}",
    )

    if main_a is not None:
        _gate(
            gates,
            "schema.main_a",
            CRITICAL,
            _check_schema_main(main_a),
            "results_main schema check for TW-A main-table",
        )
        neg, inf = _check_gap_sanity(main_a)
        _gate(
            gates,
            "gap_sanity.main_a",
            CRITICAL,
            neg == 0 and inf == 0,
            f"TW-A main gap sanity: neg={neg}, inf={inf}",
        )
        exact_rows, uncert = _check_exact_certification(main_a)
        _gate(
            gates,
            "exact_cert.main_a",
            CRITICAL,
            uncert == 0,
            f"TW-A main exact rows={exact_rows}, uncertified_exact_rows={uncert}",
        )
        unknown = _check_git_trace(main_a)
        _gate(
            gates,
            "trace.main_a_git_sha",
            HIGH,
            unknown == 0,
            f"TW-A main unknown git_sha count={unknown}",
        )
        nset = _n_set(main_a)
        _gate(
            gates,
            "coverage.main_a_sizes",
            CRITICAL,
            {10, 20, 40}.issubset(nset),
            f"TW-A main observed N={sorted(nset)}",
        )

    if scal_a is not None:
        _gate(
            gates,
            "schema.scal_a",
            CRITICAL,
            _check_schema_main(scal_a),
            "results_main schema check for TW-A scalability",
        )
        rows, invalid = _check_scalability_policy(scal_a)
        _gate(
            gates,
            "policy.scal_a",
            CRITICAL,
            invalid == 0,
            f"TW-A scalability rows={rows}, invalid_policy_rows={invalid}",
        )
        nset = _n_set(scal_a)
        _gate(
            gates,
            "coverage.scal_a_size",
            CRITICAL,
            80 in nset,
            f"TW-A scalability observed N={sorted(nset)}",
        )

    if main_b is not None:
        _gate(
            gates,
            "schema.main_b",
            CRITICAL,
            _check_schema_main(main_b),
            "results_main schema check for TW-B main-table",
        )
        nset = _n_set(main_b)
        _gate(
            gates,
            "coverage.main_b_sizes",
            HIGH,
            {10, 20, 40}.issubset(nset),
            f"TW-B main observed N={sorted(nset)}",
        )
    else:
        _gate(gates, "files.main_b_exists", HIGH, False, f"{main_b_path} missing")

    if scal_b is not None:
        _gate(
            gates,
            "schema.scal_b",
            CRITICAL,
            _check_schema_main(scal_b),
            "results_main schema check for TW-B scalability",
        )
        nset = _n_set(scal_b)
        _gate(
            gates,
            "coverage.scal_b_size",
            HIGH,
            80 in nset,
            f"TW-B scalability observed N={sorted(nset)}",
        )
    else:
        _gate(gates, "files.scal_b_exists", HIGH, False, f"{scal_b_path} missing")

    families = _collect_families(main_a, scal_a, main_b, scal_b)
    _gate(
        gates,
        "robustness.tw_families",
        HIGH,
        set(families) >= {"A", "B"},
        f"observed tw_families={families}",
    )

    root_main = _load_csv(output_root / "results_main.csv")
    root_routes = _load_csv(output_root / "results_routes.csv")
    root_sig = _load_csv(output_root / "results_significance.csv")
    _gate(
        gates,
        "files.root_triplet",
        MEDIUM,
        root_main is not None and root_routes is not None and root_sig is not None,
        "root outputs/results_*.csv presence",
    )
    if root_routes is not None:
        _gate(
            gates,
            "schema.root_routes",
            MEDIUM,
            list(root_routes.columns) == RESULTS_ROUTES_COLUMNS,
            "results_routes schema",
        )
    if root_sig is not None:
        _gate(
            gates,
            "schema.root_significance",
            MEDIUM,
            list(root_sig.columns) == RESULTS_SIGNIFICANCE_COLUMNS,
            "results_significance schema",
        )

    critical_fail = [g for g in gates if g["severity"] == CRITICAL and not g["passed"]]
    high_fail = [g for g in gates if g["severity"] == HIGH and not g["passed"]]
    medium_fail = [g for g in gates if g["severity"] == MEDIUM and not g["passed"]]

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_gates": len(gates),
            "critical_failed": len(critical_fail),
            "high_failed": len(high_fail),
            "medium_failed": len(medium_fail),
            "overall_pass": len(critical_fail) == 0,
        },
        "gates": gates,
    }

    if args.json_out:
        out_path = Path(args.json_out)
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = output_root / "audit" / f"journal_readiness_{ts}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report["summary"], indent=2))
    print(f"report: {out_path}")

    if args.fail_on_critical and critical_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
