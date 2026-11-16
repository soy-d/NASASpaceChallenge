"""Open-Meteo: temperature, rain and snow sampled on a global grid.

Open-Meteo has no "where is it raining right now" endpoint, so we sample a
regular grid of points around the globe in a few batched requests and report
the points where it is currently raining or snowing. The finer the grid, the
more accurate the picture, but the more API calls it costs (see .env.example).
"""
import math
import os
from datetime import datetime, timezone

from ..models import HazardEvent, HazardType, SourceResult
from .base import DataSource

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
BATCH_SIZE = 50
RAIN_THRESHOLD_MM = 0.1
SNOW_THRESHOLD_CM = 0.05


def build_grid(step: int) -> list[tuple[float, float]]:
    """(lat, lng) points every `step` degrees, from -60 to 70 latitude."""
    points = []
    lat = -60
    while lat <= 70:
        lng = -180
        while lng < 180:
            points.append((float(lat), float(lng)))
            lng += step
        lat += step
    return points


class OpenMeteoSource(DataSource):
    name = "weather"

    def __init__(self, client, grid_step: int | None = None, interval: int | None = None):
        super().__init__(client)
        self._grid = build_grid(grid_step or int(os.environ.get("WEATHER_GRID_STEP", 20)))
        self.interval = interval or int(os.environ.get("WEATHER_INTERVAL", 1800))

    async def fetch(self) -> SourceResult:
        rows = []
        for i in range(0, len(self._grid), BATCH_SIZE):
            batch = self._grid[i : i + BATCH_SIZE]
            response = await self._client.get(
                OPEN_METEO_URL,
                params={
                    "latitude": ",".join(str(p[0]) for p in batch),
                    "longitude": ",".join(str(p[1]) for p in batch),
                    "current": "temperature_2m,rain,showers,snowfall",
                },
            )
            response.raise_for_status()
            data = response.json()
            rows.extend(data if isinstance(data, list) else [data])
        return self.parse(rows)

    @staticmethod
    def parse(rows: list[dict]) -> SourceResult:
        events: list[HazardEvent] = []
        weighted_sum = weight_total = 0.0
        for row in rows:
            current = row.get("current") or {}
            lat, lng = row.get("latitude"), row.get("longitude")
            temp = current.get("temperature_2m")
            if lat is None or lng is None or temp is None:
                continue
            when = current.get("time")
            if when:
                when = datetime.fromisoformat(when).replace(tzinfo=timezone.utc).isoformat()
            key = f"{lat:.1f},{lng:.1f}"

            weight = math.cos(math.radians(lat))  # grid cells shrink toward the poles
            weighted_sum += temp * weight
            weight_total += weight
            events.append(HazardEvent(
                id=f"temp:{key}", type=HazardType.TEMPERATURE, title=f"Air temperature {temp:.1f}°C",
                lat=lat, lng=lng, value=temp, unit="°C", date=when, source="Open-Meteo"))

            snow = current.get("snowfall") or 0
            rain = (current.get("rain") or 0) + (current.get("showers") or 0)
            if snow >= SNOW_THRESHOLD_CM:
                events.append(HazardEvent(
                    id=f"snow:{key}", type=HazardType.SNOW, title=f"Snowfall {snow:.2f} cm/h",
                    lat=lat, lng=lng, value=snow, unit="cm/h", date=when, source="Open-Meteo"))
            elif rain >= RAIN_THRESHOLD_MM:
                events.append(HazardEvent(
                    id=f"rain:{key}", type=HazardType.RAIN, title=f"Rain {rain:.1f} mm/h",
                    lat=lat, lng=lng, value=rain, unit="mm/h", date=when, source="Open-Meteo"))

        average = round(weighted_sum / weight_total, 2) if weight_total else None
        return SourceResult(
            events=events,
            meta={"global_average_c": average, "samples": len(rows), "method": "area-weighted mean of sampled grid"},
        )
