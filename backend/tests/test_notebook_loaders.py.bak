import json
import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "notebooks"))
import loaders  # noqa: E402

RID = "KZN-ETHEKWINI"
COORDS = {RID: (-29.86, 31.02)}


def _make_raw(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    (raw / "tiles" / RID).mkdir(parents=True)
    days = pd.date_range("2024-01-01", periods=40, freq="D")
    rain = np.where(np.arange(40) % 9 == 0, 60.0, 2.0)
    stage = 1 + rain / 50
    stage[5] = np.nan
    pd.DataFrame({"Date": days.strftime("%Y-%m-%d"), "Rain": rain, "Stage": stage,
                  "Tmax": 28.0, "Tmin": 16.0}).to_csv(raw / "saws.csv", index=False)
    pd.DataFrame({
        "Disaster Type": ["Flood", "Drought", "Flood"], "Country": ["South Africa"] * 3,
        "Start Year": [2024, 2024, 2024], "Start Month": [1, 1, 1], "Start Day": [20, 5, 10],
        "End Year": [2024, 2024, 2024], "End Month": [1, 1, 1], "End Day": [22, 6, 11],
        "Location": ["Durban, eThekwini", "Somewhere", "Nowhere"],
    }).to_csv(raw / "events.csv", index=False)
    pd.DataFrame({"region_id": [RID], "susceptibility_idx": [0.8],
                  "impervious_frac": [0.5]}).to_csv(raw / "statics.csv", index=False)
    rng = np.random.default_rng(0)
    for d in ("2024-01-03", "2024-01-25"):
        np.save(raw / "tiles" / RID / f"{d}.npy", rng.random((4, 16, 16)).astype(np.float32))
    cfg = {
        "date_range": ["2024-01-01", "2024-02-09"],
        "stations": [{"file": "saws.csv", "region_id": RID, "columns": {
            "date": "Date", "rainfall_mm": "Rain", "river_level_m": "Stage",
            "tmax_c": "Tmax", "tmin_c": "Tmin"}}],
        "events": {
            "file": "events.csv", "filter": {"Country": "South Africa", "Disaster Type": ["Flood"]},
            "start": {"year": "Start Year", "month": "Start Month", "day": "Start Day"},
            "end": {"year": "End Year", "month": "End Month", "day": "End Day"},
            "location_columns": ["Location"], "region_keywords": {RID: ["ethekwini"]},
            "province_fallback": {}, "max_duration_days": 7, "pad_days_before": 0},
        "statics": {"file": "statics.csv"},
        "tiles": {"dir": "tiles", "max_age_days": 15, "max_nan_frac": 0.5},
    }
    (raw / "sources.json").write_text(json.dumps(cfg), encoding="utf-8")
    loaders.write_manifest(raw)
    return raw


def test_build_real_dataset(tmp_path: Path) -> None:
    raw = _make_raw(tmp_path)
    df, tiles, info = loaders.build_real_dataset(raw, COORDS)
    assert len(df) == 40 and tiles.shape == (40, 4, 16, 16)
    assert int(df["event"].sum()) == 3  # Jan 20-22; the drought row is filtered out
    assert info["events"]["unmatched_events"] == 1  # the "Nowhere" flood
    ok = ["rainfall_mm", "temperature_c", "humidity_pct", "pressure_hpa", "wind_ms", "soil_moisture"]
    assert int(df[ok].isna().sum().sum()) == 0
    assert int(df["river_level_m"].isna().sum()) == 1  # left for notebook 02 to handle
    assert float(df["temperature_c"].iloc[0]) == pytest.approx(22.0)
    assert df["soil_moisture"].between(0, 1).all()
    for d in ("2024-01-03", "2024-01-25"):
        assert int(df.loc[df["date"] == d, "tile_age_days"].iloc[0]) == 0
    assert int(df.loc[df["date"] == "2024-01-01", "tile_age_days"].iloc[0]) == -1
    assert list(df["row_id"]) == list(range(40))


def test_tampered_or_unlisted_file_rejected(tmp_path: Path) -> None:
    raw = _make_raw(tmp_path)
    (raw / "saws.csv").write_text("Date,Rain\n2024-01-01,1\n", encoding="utf-8")
    with pytest.raises(loaders.DataError):
        loaders.build_real_dataset(raw, COORDS)
    (raw / "manifest.json").unlink()
    with pytest.raises(loaders.DataError):
        loaders.build_real_dataset(raw, COORDS)
