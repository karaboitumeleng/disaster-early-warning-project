# Sample Datasets — Disaster Early Warning Prototype

This folder contains small, freely downloadable sample datasets that stand in for the
production data sources in the project charter. They are real data (not synthetic) and
are small enough to train a prototype on a laptop.

## Files included

| File | Source | What it is | Coverage |
|------|--------|-----------|----------|
| `durban_kzn_daily_2021-2022.csv` | Open-Meteo Historical Weather API (reanalysis) | Daily rain, temperature, humidity, pressure, wind for Durban, KwaZulu-Natal | 2021-06-01 → 2022-06-30 (399 days). Wettest day: 2022-04-11 (100.7 mm) — the April 2022 KZN flood event. |
| `mbombela_mpumalanga_daily_2021-2022.csv` | Open-Meteo Historical Weather API (reanalysis) | Same variables for Mbombela (Nelspruit), Mpumalanga | 2021-06-01 → 2022-06-30 (399 days) |

Download command used (no API key required, free for non-commercial use):

```
https://archive-api.open-meteo.com/v1/archive?latitude=-29.85&longitude=31.02
  &start_date=2021-06-01&end_date=2022-06-30
  &daily=rain_sum,temperature_2m_mean,relative_humidity_2m_mean,pressure_msl_mean,wind_speed_10m_max
  &timezone=Africa/Johannesburg&format=csv
```

Change `latitude`/`longitude` and dates for any other SA location or period.

## How to get the remaining sample data yourself

| Charter data source | Easiest sample substitute | How to get it |
|---|---|---|
| SAWS weather-station data | NOAA GSOD (Global Surface Summary of the Day) — includes SA stations | https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/ → pick a South African station-year CSV (e.g., Durban Airport 688420). Or reuse Open-Meteo (already done above). |
| Satellite imagery (Sentinel-2 / Landsat 8) | Small Sentinel-2 tile over a KZN flood zone | Free account at https://dataspace.copernicus.eu → Data Browser → draw a box over the Tugela River catchment → download a single L2A tile (~100 MB). For lighter samples use the AWS Open Data bucket `s3://sentinel-s2-l2a` or pre-cropped images from Kaggle ("Sentinel-2 flood" datasets). |
| Historical flood records (labels) | EM-DAT (registration required, free for students) or Dartmouth Flood Observatory archive | https://www.emdat.be (register with your SPU email) → filter Country = South Africa, Disaster = Flood → export CSV. Dartmouth archive: http://floodobservatory.colorado.edu/Archives/index.html (free, no login). |
| Hydrological / river levels | Global Runoff Data Centre (GRDC) — free after registration; or DWS SA hydrology | https://www.bafg.de/GRDC — request SA station time series. Simpler stand-in: use Open-Meteo `river_discharge` variable (modelled) for the same coordinates/dates. |
| Sea-level (tide gauges) | PSMSL annual/monthly means | https://www.psmsl.org → register (free) → station data → e.g., Durban tide gauge. |
| SANLC land cover | Department of Forestry, Fisheries and the Environment geospatial portal | https://egis.environment.gov.za → download the SANLC 2018/2020 GeoTIFF or shapefile (free, no licence fee) and clip to your study region in QGIS. |
| Rainfall raster (optional, for CNN input) | CHIRPS daily precipitation | https://data.chc.ucsb.edu/products/CHIRPS-2.0/ → `africa_daily/tifs/p05/` → free, no registration, subset South Africa. |

## Honesty note for your report

If any stand-in or synthetic data is used for the demo, disclose it in the Final Project
Report under Methodology → Data (e.g., "SAWS station data was represented by NOAA GSOD /
Open-Meteo reanalysis for the prototype; satellite inputs were single-tile samples").
The charter's risk-mitigation section already anticipates data-access limitations, so this
is a defensible, documented deviation — not a shortcut.
