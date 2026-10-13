# Real-data guide (notebook 01)

Status: loaders written against ASSUMED file layouts and never run on real data. Expect to edit
sources.json. Every loader fails loudly on missing columns and prints what it found.

## 1. Acquire and record
Put files under data/raw/ (git-ignored). Record URL, licence, date in docs/DATA_SOURCES.md, then
    python notebooks/loaders.py manifest data/raw
Notebook 01 refuses any input not in manifest.json or whose SHA-256 differs.

## 2. Configure
Copy notebooks/sources.example.json to data/raw/sources.json and match it to your files:
- stations[]: one entry per file; `columns` maps standard names (date, rainfall_mm,
  river_level_m, temperature_c or tmax_c+tmin_c, humidity_pct, pressure_hpa, wind_ms) to your
  headers; optional scale/offset for units, date_format, missing markers. Out-of-range values
  become missing (not clipped). Several stations in one region are averaged per day.
- events: filter, date columns and location columns of your export. Events are assigned to
  regions by keyword; province-level events fall back to every region in the province, which
  OVER-LABELS. Prefer district-level sources.
- statics: CSV with region_id, susceptibility_idx, impervious_frac in [0,1]. You must supply
  these (e.g. SANLC built-up fraction, terrain). Never derive them from the flood labels.
- tiles: data/raw/tiles/<REGION_ID>/<YYYY-MM-DD>.npy or .tif with 4 bands in one fixed order
  (config records band_order). Do cloud masking when exporting; tiles over 50% NaN are rejected.
  GeoTIFFs need rasterio and are block-averaged to 16x16. The band definitions must match the
  ones used to refresh data/tiles/ for live inference.

## 3. What the loader does and does not do
- Daily grid per region over date_range. Rainfall gaps: cross-station mean, else 0 (counted in
  meta; over 5% missing raises). Never interpolated.
- Temperature/humidity/pressure/wind: interpolate up to 3 days, then region/global median, then a
  documented constant if the variable is absent entirely.
- River level gaps are left for notebook 02 (interpolation + missing flag). A region with no river
  data raises.
- Soil moisture is a PROXY from antecedent precipitation (no source). It is collinear with the API
  feature.
- Tiles: latest tile at or before each day, up to max_age_days; else the region median tile
  (age -1).
- Known weakness: gauge datums differ across regions, yet the model standardises river level
  globally. Consider per-region normalisation before trusting cross-region behaviour.

## 4. Expect label problems
EM-DAT lists major events only; a decade may yield a handful per province. Notebook 03 requires
at least 20 test-split positives and will stop otherwise. That is a real finding: add DesInventar,
NDMC/municipal reports or a longer record. Rainfall/river-stage threshold labels are an option
but are circular with the input features, so do not use them to support the accuracy objective.

## 5. Then
    python scripts/train_all.py ; python scripts/register_model.py
Only metrics with data_kind = real count toward the accuracy objective in PERFORMANCE.md.
