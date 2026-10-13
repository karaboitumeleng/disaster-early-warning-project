# Data sources

URLs were written from memory and have NOT been verified. Confirm each URL, licence and access
route yourself, then fill in the access date and checksum. Do not ship any data whose licence you
have not read.

| Dataset | Role | URL (verify) | Licence / terms (verify) | Access date | SHA-256 |
|---|---|---|---|---|---|
| Sentinel-2 imagery | spatial features | https://dataspace.copernicus.eu | | | |
| Landsat 8 imagery | spatial features | https://earthexplorer.usgs.gov | | | |
| SAWS station data | rainfall, temperature, humidity, pressure, wind | https://www.weathersa.co.za | Access may require a formal data request | | |
| SAWS / DWS hydrology | river levels | check with SAWS and the Department of Water and Sanitation | | | |
| PSMSL tide gauges | sea level | https://psmsl.org | | | |
| SANLC land cover | land-cover statics | see the national environment department geospatial portal | | | |
| EM-DAT | historical event labels | https://www.emdat.be | Registration and terms apply | | |
| DesInventar | historical event labels | https://www.desinventar.net | | | |

## Data currently in the repository
`data/ewsa_selected.csv`, `data/ewsa_clean.csv`, `data/ewsa_tiles.npz` and
`data/ewsa_dataset_v1.npz` are **synthetic**, produced by `notebooks/common.py`. Their checksums
are in the `*.meta.json` files beside them. They contain no real observations.

## Integrity procedure for real data
1. Download to `data/raw/`; record URL, date and licence in the table above.
2. Compute SHA-256 (`Get-FileHash -Algorithm SHA256 <file>` on Windows) and record it.
3. Recompute before every training run and refuse to train on a mismatch.
