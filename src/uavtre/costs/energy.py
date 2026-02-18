from __future__ import annotations

import numpy as np


def compute_energy_matrix(distance_m: np.ndarray, energy_per_m: float) -> np.ndarray:
    return float(energy_per_m) * distance_m
