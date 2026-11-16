"""USGS earthquakes (last 2.5 days) and USGS tsunami flags."""
from datetime import datetime, timezone

from ..models import HazardEvent, HazardType, SourceResult
from .base import DataSource

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"


class UsgsSource(DataSource):
    name = "usgs"
    interval = 60

    async def fetch(self) -> SourceResult:
        response = await self._client.get(USGS_URL)
        response.raise_for_status()
        return SourceResult(events=self.parse(response.json()))

    @staticmethod
    def parse(data: dict) -> list[HazardEvent]:
        events: list[HazardEvent] = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            coords = (feature.get("geometry") or {}).get("coordinates")
            if not coords or len(coords) < 2:
                continue
            lng, lat = float(coords[0]), float(coords[1])
            when = None
            if props.get("time") is not None:
                when = datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc).isoformat()
            mag = props.get("mag")
            title = props.get("title") or f"Earthquake M{mag}"
            events.append(
                HazardEvent(
                    id=f"usgs:{feature.get('id')}",
                    type=HazardType.EARTHQUAKE,
                    title=title,
                    lat=lat,
                    lng=lng,
                    value=mag,
                    unit="M",
                    date=when,
                    source="USGS",
                )
            )
            # USGS sets tsunami=1 when the quake is oceanic and a tsunami
            # message may have been issued. It means "potential", not "confirmed".
            if props.get("tsunami") == 1:
                events.append(
                    HazardEvent(
                        id=f"usgs-tsunami:{feature.get('id')}",
                        type=HazardType.TSUNAMI,
                        title=f"Tsunami potential flagged: {title}",
                        lat=lat,
                        lng=lng,
                        value=mag,
                        unit="M",
                        date=when,
                        source="USGS",
                    )
                )
        return events
