from __future__ import annotations

import numpy as np

from uavtre.scenario.time_windows import build_time_windows


def test_tw_family_a() -> None:
    baseline = np.array([300.0, 600.0, 900.0])
    rng = np.random.default_rng(1)
    early, late = build_time_windows(baseline, delta_min=5, family="A", rng=rng)
    assert np.all(late > early)
    assert np.isclose(early[1], 300.0)
    assert np.isclose(late[1], 900.0)


def test_tw_family_b_stress() -> None:
    baseline = np.array([300.0, 600.0, 900.0])
    rng = np.random.default_rng(7)
    early, late = build_time_windows(baseline, delta_min=5, family="B", rng=rng)
    assert np.all(late > early)
    assert np.any(np.abs((late - early) - 600.0) > 1e-6)
