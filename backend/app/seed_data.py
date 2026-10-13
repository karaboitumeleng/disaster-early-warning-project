"""Placeholder demo boundaries — simplified bounding-box rectangles, NOT real SANLC/municipal
polygons. Replace with verified boundary data before any real deployment (see DATA_SOURCES.md)."""
from app.models import Region


def _box(lon_min: float, lat_min: float, lon_max: float, lat_max: float) -> dict:
    ring = [[lon_min, lat_min], [lon_max, lat_min], [lon_max, lat_max], [lon_min, lat_max], [lon_min, lat_min]]
    return {"type": "Polygon", "coordinates": [ring]}


DEMO_REGIONS: list[Region] = [
    Region(id="KZN-ETHEKWINI", name="eThekwini (Durban)", province="KwaZulu-Natal",
           geojson=_box(30.75, -30.10, 31.15, -29.60), centroid_lat=-29.85, centroid_lon=31.02),
    Region(id="KZN-UMGUNGUNDLOVU", name="uMgungundlovu", province="KwaZulu-Natal",
           geojson=_box(29.90, -29.85, 30.70, -29.20), centroid_lat=-29.60, centroid_lon=30.38),
    Region(id="KZN-KINGCETSHWAYO", name="King Cetshwayo", province="KwaZulu-Natal",
           geojson=_box(31.60, -29.10, 32.30, -28.30), centroid_lat=-28.75, centroid_lon=31.95),
    Region(id="MP-EHLANZENI", name="Ehlanzeni", province="Mpumalanga",
           geojson=_box(30.60, -25.80, 31.90, -24.60), centroid_lat=-25.20, centroid_lon=31.25),
    Region(id="MP-NKANGALA", name="Nkangala", province="Mpumalanga",
           geojson=_box(28.80, -26.20, 29.90, -25.20), centroid_lat=-25.70, centroid_lon=29.35),
]