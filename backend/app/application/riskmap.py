from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories import RegionRepo
from app.schemas import RegionOut

BASELINE_RISK = 0.1  # no alert history yet: quiet-conditions placeholder, not a model output


def band_for(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "elevated"
    return "low"


class RiskMapService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def get_regions(self) -> list[RegionOut]:
        async with self.session_factory() as s:
            repo = RegionRepo(s)
            regions = await repo.list_all()
            out: list[RegionOut] = []
            for r in regions:
                alert = await repo.latest_alert_for(r.id)
                score = alert.risk_score if alert else BASELINE_RISK
                out.append(
                    RegionOut(
                        id=r.id, name=r.name, province=r.province, geojson=r.geojson,
                        centroid_lat=r.centroid_lat, centroid_lon=r.centroid_lon,
                        risk_score=score, band=band_for(score),
                        degraded=alert.degraded if alert else False,
                        novel=alert.novel if alert else False,
                        last_updated=alert.created_at if alert else None,
                    )
                )
            return out