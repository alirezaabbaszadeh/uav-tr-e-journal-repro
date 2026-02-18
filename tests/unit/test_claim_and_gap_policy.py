from __future__ import annotations

from uavtre.experiments.runner import _compute_gap_pct, _is_optimal_status


def test_gap_pct_is_non_negative_for_valid_pair() -> None:
    gap = _compute_gap_pct(incumbent_obj=100.0, best_bound=90.0)
    assert gap is not None
    assert abs(gap - 10.0) < 1e-9


def test_gap_pct_rejects_inconsistent_bound() -> None:
    assert _compute_gap_pct(incumbent_obj=100.0, best_bound=110.0) is None


def test_optimal_status_detection() -> None:
    assert _is_optimal_status("Optimal")
    assert not _is_optimal_status("Time limit reached")
