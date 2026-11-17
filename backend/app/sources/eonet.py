# NASA EONET source for storm, wildfire, volcano, and sea-ice hazard events.
"""NASA EONET: typhoons, wildfires, volcanoes and sea/lake ice."""
from typing import Optional

from ..models import HazardEvent, HazardType, SourceResult
from .base import DataSource

EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

CATEGORY_TO_TYPE = {
    "severeStorms": HazardType.TYPHOON,
    "wildfires": HazardType.WILDFIRE,
    "volcanoes": HazardType.VOLCANO,
    "seaLakeIce": HazardType.SEA_ICE,
}


class EonetSource(DataSource):
    name = "nasa_eonet"
    interval = 300

    async def fetch(self) -> SourceResult:
        response = await self._client.get(
            EONET_URL,
            params={"status": "open", "category": ",".join(CATEGORY_TO_TYPE)},
        )
        response.raise_for_status()
        return SourceResult(events=self.parse(response.json()))

    @classmethod
    def parse(cls, data: dict) -> list[HazardEvent]:
        events: list[HazardEvent] = []
        for raw in data.get("events", []):
            geometries = raw.get("geometry") or []
            if not geometries:
                continue
            latest = geometries[-1]  # most recent position
            point = cls._to_point(latest.get("type"), latest.get("coordinates"))
            hazard = cls._hazard_type(raw)
            if point is None or hazard is None:
                continue
            lng, lat = point
            events.append(
                HazardEvent(
                    id=f"eonet:{raw.get('id')}",
                    type=hazard,
                    title=raw.get("title", "Unnamed event"),
                    lat=lat,
                    lng=lng,
                    value=latest.get("magnitudeValue"),
                    unit=latest.get("magnitudeUnit"),
                    date=latest.get("date"),
                    source="NASA EONET",
                )
            )
        return events

    @staticmethod
    def _hazard_type(raw: dict) -> Optional[HazardType]:
        for category in raw.get("categories", []):
            if category.get("id") in CATEGORY_TO_TYPE:
                return CATEGORY_TO_TYPE[category["id"]]
        return None

    @staticmethod
    def _to_point(geo_type: Optional[str], coords) -> Optional[tuple[float, float]]:
        """Return (lng, lat). EONET uses Points, but sea ice uses Polygons."""
        try:
            if geo_type == "Point":
                return float(coords[0]), float(coords[1])
            if geo_type == "Polygon":
                ring = coords[0]
                return (
                    sum(p[0] for p in ring) / len(ring),
                    sum(p[1] for p in ring) / len(ring),
                )
        except (TypeError, IndexError, ZeroDivisionError, ValueError):
            return None
        return None
