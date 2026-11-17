# NOAA CPC Oceanic Niño Index (ONI) source for the ENSO phase overlay.
"""NOAA CPC Oceanic Niño Index (ONI): El Niño / La Niña status.

El Niño is not a point event. It is a Pacific-wide sea-surface-temperature
pattern, so we show it as one marker over the Niño 3.4 region, coloured by
the current phase. ONI is published monthly with about a month of lag.
"""
from ..models import HazardEvent, HazardType, SourceResult
from .base import DataSource

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
NINO34_CENTER = (0.0, -145.0)  # lat, lng


def phase_for(anomaly: float) -> str:
    if anomaly >= 0.5:
        return "El Niño"
    if anomaly <= -0.5:
        return "La Niña"
    return "Neutral"


class EnsoSource(DataSource):
    name = "enso"
    interval = 6 * 3600

    async def fetch(self) -> SourceResult:
        response = await self._client.get(ONI_URL)
        response.raise_for_status()
        return self.parse(response.text)

    @staticmethod
    def parse_rows(text: str) -> list[tuple[str, int, float]]:
        """All (season, year, anomaly) rows of the NOAA ONI table."""
        rows = []
        for line in text.splitlines():
            parts = line.split()
            if len(parts) == 4 and parts[1].isdigit():
                try:
                    rows.append((parts[0], int(parts[1]), float(parts[3])))
                except ValueError:
                    continue
        return rows

    @classmethod
    def parse(cls, text: str) -> SourceResult:
        rows = cls.parse_rows(text)
        if not rows:
            raise ValueError("No ONI rows found in NOAA response")
        season, year, anomaly = rows[-1]
        phase = phase_for(anomaly)
        event = HazardEvent(
            id="enso:nino34", type=HazardType.EL_NINO,
            title=f"ENSO: {phase} (ONI {anomaly:+.2f}°C, {season} {year})",
            lat=NINO34_CENTER[0], lng=NINO34_CENTER[1], value=anomaly, unit="°C anomaly",
            date=f"{season} {year}", source="NOAA CPC",
        )
        return SourceResult(events=[event], meta={"phase": phase, "oni": anomaly, "season": f"{season} {year}"})
