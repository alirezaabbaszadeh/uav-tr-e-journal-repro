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
    parser.add_argument("--campaign-id", default=None, help="Optional campaign id under outputs/campaigns.")
    parser.add_argument(
        "--campaign-root",
        default="outputs/campaigns",
        help="Campaign root when --campaign-id is provided.",
    )
    parser.add_argument("--main-a", default=None, help="Main-table TW-A results_main path.")
    parser.add_argument("--scal-a", default=None, help="Scalability TW-A results_main path.")
    parser.add_argument("--main-b", default=None, help="Main-table TW-B results_main path.")
    parser.add_argument("--scal-b", default=None, help="Scalability TW-B results_main path.")
    parser.add_argument("--json-out", default=None, help="Optional explicit JSON report output path.")
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit non-zero if any critical gate fails.",
    )
    parser.add_argument(
        "--fail-on-high",
        action="store_true",
        help="Exit non-zero if any high-severity gate fails.",
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
    ser = df["git_sha"].astype(str)
    return int(ser.str.contains(r"unknown|nogit-", regex=True, na=False).sum())


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


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path | None]:
    if args.campaign_id:
        camp = Path(args.campaign_root) / args.campaign_id
        main_a = Path(args.main_a) if args.main_a else camp / "main_A_core" / "results_main.csv"
        scal_a = Path(args.scal_a) if args.scal_a else camp / "scal_A_core" / "results_main.csv"
        main_b = Path(args.main_b) if args.main_b else camp / "main_B_core" / "results_main.csv"
        scal_b = Path(args.scal_b) if args.scal_b else camp / "scal_B_core" / "results_main.csv"
        return main_a, scal_a, main_b, scal_b, camp

    main_a = Path(args.main_a) if args.main_a else Path("outputs/main_table_v2_core/results_main.csv")
    scal_a = Path(args.scal_a) if args.scal_a else Path("outputs/scalability_v2_core/results_main.csv")
    main_b = Path(args.main_b) if args.main_b else Path("outputs/main_table_v2_core_B/results_main.csv")
    scal_b = Path(args.scal_b) if args.scal_b else Path("outputs/scalability_v2_core_B/results_main.csv")
    return main_a, scal_a, main_b, scal_b, None


def _paired_case_count(df: pd.DataFrame, method_a: str, method_b: str, n: int) -> int:
    key_cols = [
        "seed",
        "N",
        "M",
        "Delta_min",
        "B",
        "K",
        "lambda_out",
        "lambda_tw",
        "tw_family",
        "tw_mode",
        "profile",
    ]
    required = set(key_cols + ["method"])
    if not required.issubset(df.columns):
        return 0

    dfa = df[(df["method"] == method_a) & (pd.to_numeric(df["N"], errors="coerce") == n)]
    dfb = df[(df["method"] == method_b) & (pd.to_numeric(df["N"], errors="coerce") == n)]
    if dfa.empty or dfb.empty:
        return 0

    pa = dfa[key_cols].drop_duplicates()
    pb = dfb[key_cols].drop_duplicates()
    return int(len(pa.merge(pb, on=key_cols, how="inner")))


def _check_significance_integrity(sig_df: pd.DataFrame) -> tuple[int, int]:
    required_cols = ["p_value_adj", "effect_direction", "effect_size", "ci_low", "ci_high", "n_pairs"]
    missing_cols = [c for c in required_cols if c not in sig_df.columns]
    if missing_cols:
        return 0, int(1e9)

    invalid = sig_df.copy()
    invalid["n_pairs_num"] = pd.to_numeric(invalid["n_pairs"], errors="coerce")
    invalid_mask = (
        invalid["p_value_adj"].isna()
        | invalid["effect_direction"].isna()
        | invalid["effect_size"].isna()
        | invalid["ci_low"].isna()
        | invalid["ci_high"].isna()
        | invalid["n_pairs_num"].isna()
        | (invalid["n_pairs_num"] <= 0)
    )
    return int(len(sig_df)), int(invalid_mask.sum())


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)

    main_a_path, scal_a_path, main_b_path, scal_b_path, campaign_dir = _resolve_paths(args)

    main_a = _load_csv(main_a_path)
    scal_a = _load_csv(scal_a_path)
    main_b = _load_csv(main_b_path)
    scal_b = _load_csv(scal_b_path)

    sig_a_path = main_a_path.parent / "results_significance.csv"
    sig_b_path = main_b_path.parent / "results_significance.csv"
    sig_a = _load_csv(sig_a_path)
    sig_b = _load_csv(sig_b_path)

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
            f"TW-A main fallback git_sha rows={unknown}",
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

    if sig_a is not None:
        _gate(
            gates,
            "schema.sig_a",
            HIGH,
            list(sig_a.columns) == RESULTS_SIGNIFICANCE_COLUMNS,
            f"TW-A significance schema at {sig_a_path}",
        )
        rows, invalid = _check_significance_integrity(sig_a)
        _gate(
            gates,
            "stats.sig_a_fields",
            HIGH,
            rows > 0 and invalid == 0,
            f"TW-A significance rows={rows}, invalid_rows={invalid}",
        )
    else:
        _gate(gates, "files.sig_a_exists", HIGH, False, f"{sig_a_path} missing")

    if sig_b is not None:
        _gate(
            gates,
            "schema.sig_b",
            HIGH,
            list(sig_b.columns) == RESULTS_SIGNIFICANCE_COLUMNS,
            f"TW-B significance schema at {sig_b_path}",
        )
        rows, invalid = _check_significance_integrity(sig_b)
        _gate(
            gates,
            "stats.sig_b_fields",
            HIGH,
            rows > 0 and invalid == 0,
            f"TW-B significance rows={rows}, invalid_rows={invalid}",
        )
    else:
        _gate(gates, "files.sig_b_exists", HIGH, False, f"{sig_b_path} missing")

    if main_a is not None:
        c20 = _paired_case_count(main_a, "ortools_main", "pyvrp_baseline", 20)
        c40 = _paired_case_count(main_a, "ortools_main", "pyvrp_baseline", 40)
        _gate(
            gates,
            "stats.main_a_pair_coverage_n20_n40",
            HIGH,
            c20 > 0 and c40 > 0,
            f"TW-A pair coverage ortools-vs-pyvrp: N20={c20}, N40={c40}",
        )

    if main_b is not None:
        c20 = _paired_case_count(main_b, "ortools_main", "pyvrp_baseline", 20)
        c40 = _paired_case_count(main_b, "ortools_main", "pyvrp_baseline", 40)
        _gate(
            gates,
            "stats.main_b_pair_coverage_n20_n40",
            HIGH,
            c20 > 0 and c40 > 0,
            f"TW-B pair coverage ortools-vs-pyvrp: N20={c20}, N40={c40}",
        )

    if campaign_dir is not None:
        required_campaign_files = [
            campaign_dir / "CAMPAIGN_MANIFEST.json",
            campaign_dir / "RUN_PLAN.json",
            campaign_dir / "ENV_SNAPSHOT.json",
            campaign_dir / "COMMAND_LOG.csv",
        ]
        missing = [str(p) for p in required_campaign_files if not p.exists()]
        _gate(
            gates,
            "trace.campaign_metadata",
            HIGH,
            len(missing) == 0,
            "campaign metadata files present" if not missing else f"missing={missing}",
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
    if args.fail_on_high and high_fail:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
