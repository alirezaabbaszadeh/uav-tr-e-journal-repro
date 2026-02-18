from __future__ import annotations

import math
from typing import Dict

import numpy as np


def los_probability(theta_deg: np.ndarray, a: float, b: float) -> np.ndarray:
    return 1.0 / (1.0 + a * np.exp(-b * (theta_deg - a)))


def pathloss_db(
    d_3d: np.ndarray,
    theta_deg: np.ndarray,
    freq_hz: float,
    los_a: float,
    los_b: float,
    eta_los: float,
    eta_nlos: float,
) -> np.ndarray:
    c = 3e8
    fspl = 20.0 * np.log10(4.0 * math.pi * freq_hz / c) + 20.0 * np.log10(
        np.maximum(d_3d, 1.0)
    )
    p_los = los_probability(theta_deg, los_a, los_b)
    pl_los = fspl + eta_los
    pl_nlos = fspl + eta_nlos
    return p_los * pl_los + (1.0 - p_los) * pl_nlos


def edge_outage_risk(
    p1: np.ndarray,
    p2: np.ndarray,
    bs_xy: np.ndarray,
    altitude_m: float,
    k_samples: int,
    comm_params: Dict[str, float],
) -> float:
    if k_samples <= 1:
        samples = np.array([p1, p2], dtype=float)
    else:
        t = np.linspace(0.0, 1.0, k_samples)
        samples = p1[None, :] + (p2 - p1)[None, :] * t[:, None]

    tx_power_dbm = float(comm_params["tx_power_dbm"])
    noise_dbm = float(comm_params["noise_dbm"])
    snr_threshold_db = float(comm_params["snr_threshold_db"])

    los_a = float(comm_params["los_a"])
    los_b = float(comm_params["los_b"])
    eta_los = float(comm_params["eta_los"])
    eta_nlos = float(comm_params["eta_nlos"])
    freq_hz = float(comm_params["freq_hz"])

    outages = []
    for sample in samples:
        diff = bs_xy - sample[None, :]
        horiz = np.linalg.norm(diff, axis=1)
        d_3d = np.sqrt(horiz**2 + altitude_m**2)
        theta = np.degrees(np.arctan2(altitude_m, np.maximum(horiz, 1e-6)))

        pl = pathloss_db(d_3d, theta, freq_hz, los_a, los_b, eta_los, eta_nlos)
        recv_power_dbm = tx_power_dbm - pl
        snr = recv_power_dbm - noise_dbm
        best_snr = float(np.max(snr))
        outages.append(1.0 if best_snr < snr_threshold_db else 0.0)

    return float(np.mean(outages))
