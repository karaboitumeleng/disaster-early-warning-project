def rescale(p: float, thr: float, alert: float) -> float:
    """Monotone piecewise-linear map so the model's tuned decision threshold `thr` lands on the
    alert threshold `alert`. This is a rescaling, NOT probability calibration."""
    thr = min(max(thr, 1e-3), 1 - 1e-3)
    alert = min(max(alert, 1e-3), 1 - 1e-3)
    p = min(max(p, 0.0), 1.0)
    if p < thr:
        return alert * p / thr
    return alert + (1 - alert) * (p - thr) / (1 - thr)
