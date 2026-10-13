"""OWML hook. Placeholder envelope check; replace with an autoencoder reconstruction-error
detector trained in notebook 04 (same interface: returns (is_novel, offending_features))."""

ENVELOPE: dict[str, tuple[float, float]] = {
    "rainfall_mm_24h": (0.0, 350.0),
    "river_level_m": (0.0, 15.0),
    "soil_moisture": (0.0, 1.0),
    "temperature_c": (-5.0, 45.0),
    "humidity_pct": (0.0, 100.0),
}


def check_novelty(features: dict[str, float | None]) -> tuple[bool, list[str]]:
    offending = [
        name
        for name, (lo, hi) in ENVELOPE.items()
        if (v := features.get(name)) is not None and not lo <= v <= hi
    ]
    return bool(offending), offending