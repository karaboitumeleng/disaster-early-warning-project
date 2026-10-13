# Data sources

## What's real, right now
| # | Region | Source | Coverage | File |
|---|---|---|---|---|
| 1 | KZN-ETHEKWINI (Durban) | Open-Meteo Historical Weather API (reanalysis), free, no key required, non-commercial use | 2021-06-01 to 2022-06-30, 395 daily rows, 0 missing | `data/raw/source_downloads/durban_kzn_daily_2021-2022.xlsx` |
| 2 | MP-EHLANZENI (Mbombela) | Open-Meteo Historical Weather API (reanalysis) | 2021-06-01 to 2022-06-30, 395 daily rows, 0 missing | `data/raw/source_downloads/mbombela_mpumalanga_daily_2021-2022_csv.xlsx` |

Fields present in the real data: `rain_sum (mm)`, `temperature_2m_mean (°C)`,
`relative_humidity_2m_mean (%)`, `pressure_msl_mean (hPa)`, `wind_speed_10m_max (km/h)`.
Pressure and wind are carried through `station_readings.csv` but **not yet fed into the
trained model** — see `notebooks/01_selection.ipynb`'s header cell for why.

**Format note:** both files are Open-Meteo's CSV export saved as `.xlsx` workbooks — each row
is one text cell (metadata line, lat/lon line, blank, header, data), not a normal spreadsheet.
`load_openmeteo_xlsx()` in notebook 01 parses this specific layout.

Durban's real data independently reproduces the known April 2022 KZN flood
(2022-04-11, 100.7mm) and a second spike on 2022-05-21/22 (117.8mm/93.7mm) — both dates are
forced to `flood_label=1` regardless of the threshold rule, as a ground-truth anchor.

## What's still synthetic, and why
| Data | Status | Reason |
|---|---|---|
| River level, soil moisture (all 5 regions, real regions included) | Modelled proxy from antecedent precipitation index | Open-Meteo has no river-level or soil-moisture field; no GRDC/DWS access in this environment |
| 3 of 5 regions' weather (`KZN-UMGUNGUNDLOVU`, `KZN-KINGCETSHWAYO`, `MP-NKANGALA`) | Fully synthetic | No real data supplied for these regions |
| Satellite tiles (all 5 regions) | Synthetic | No Copernicus/USGS/GEE network access in this environment |
| SANLC land cover (all 5 regions) | Synthetic | No egis.environment.gov.za access in this environment |
| Flood labels for the real regions | Heuristic threshold (rainfall ≥50mm/24h or 3-day ≥80mm), plus 2 forced anchor dates from public reporting | No EM-DAT export was available; this is **not** verified EM-DAT/DesInventar ground truth |

## Known limitation: extreme class imbalance on real data
With the heuristic above, the real data has **7 positive days for Durban and 2 for Mbombela
out of 395 each** (~1.1% combined). `notebooks/05_interpretation.ipynb` reports a separate
`real_data_only` metric block precisely so this small, imbalanced sample's accuracy isn't
silently blended into the headline ≥80% figure without disclosure. Treat the real-data-only
numbers as indicative, not conclusive — 9 positive days total is not enough to draw a
reliable accuracy estimate from.

## Region boundaries on the risk map
Still simplified placeholder rectangles (`backend/app/seed_data.py`), unrelated to the weather
data above. Do not present as authoritative in front of NDMC.

## Before any real deployment
1. Replace the 2 real regions' heuristic labels with an actual EM-DAT/DesInventar/gazette
   export (README's suggested path: register at emdat.be, filter Country=South Africa,
   Disaster=Flood).
2. Get real river-level data (GRDC or DWS hydrology) instead of the API-derived proxy.
3. Get real data for the other 3 regions (Open-Meteo works with no key — same download
   pattern as the two files already used, per `Dataset_README.md`).
4. Pull real Sentinel-2 tiles and SANLC land cover per `Dataset_README.md`'s substitute list.
5. Re-run notebooks 02-05 and update `docs/PERFORMANCE.md` with the real numbers.