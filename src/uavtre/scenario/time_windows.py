from __future__ import annotations

import numpy as np


def build_time_windows(
    baseline_times_s: np.ndarray,
    delta_min: int,
    family: str,
    rng: np.random.Generator,
    family_b_shrink: float = 0.8,
    family_b_jitter_min: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    delta_s = float(delta_min) * 60.0

    tw_early = np.maximum(0.0, baseline_times_s - delta_s)
    tw_late = baseline_times_s + delta_s

    if family.upper() != "B":
        return tw_early, tw_late

    # Family B: controlled stress with tighter and jittered windows.
    width = (tw_late - tw_early) * max(0.2, min(1.0, family_b_shrink))
    center_jitter = rng.normal(0.0, family_b_jitter_min * 60.0, size=baseline_times_s.shape)

    center = baseline_times_s + center_jitter
    tw_early_b = np.maximum(0.0, center - width / 2.0)
    tw_late_b = np.maximum(tw_early_b + 60.0, center + width / 2.0)

    return tw_early_b, tw_late_b
