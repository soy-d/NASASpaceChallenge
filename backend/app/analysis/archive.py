# Historical archive service for ERA5 climate data and trend analysis.
"""Past-climate data from the Open-Meteo ERA5 archive, binned and analysed.

Failures raise an error; this service never substitutes generated data.
"""
import math
import time
from collections import defaultdict
from statistics import mean

import httpx

from .stats import TrendAnalyzer

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_FIELDS = ("temperature_2m_mean,precipitation_sum,snowfall_sum,"
                "wind_speed_10m_max,shortwave_radiation_sum,et0_fao_evapotranspiration")

VARIABLES = {
    "temp_mean": {"label": "Surface Air Temperature (2m)", "unit": "°C", "category": "Thermal", "color": "#e11d48",
                  "description": "Mean 2 m air temperature per time bin."},
    "temp_anomaly": {"label": "Temperature Anomaly", "unit": "°C", "category": "Thermal", "color": "#f97316",
                     "description": "Departure from the mean of the earliest 30% of bins (reference period)."},
    "precip_sum": {"label": "Total Precipitation", "unit": "mm", "category": "Hydrological", "color": "#7c3aed",
                   "description": "Rain plus snow water-equivalent summed over each bin."},
    "snowfall_sum": {"label": "Snowfall Accumulation", "unit": "cm", "category": "Cryosphere", "color": "#0284c7",
                     "description": "Total snowfall depth per bin."},
    "wind_max": {"label": "Peak 10 m Wind Speed", "unit": "m/s", "category": "Atmospheric", "color": "#0d9488",
                 "description": "Mean of daily maximum 10 m wind speed."},
    "solar_radiation": {"label": "Shortwave Solar Radiation", "unit": "MJ/m²", "category": "Atmospheric", "color": "#d97706",
                        "description": "Mean daily downwelling shortwave radiation."},
    "et0_evap": {"label": "Reference Evapotranspiration (ET₀)", "unit": "mm", "category": "Hydrological", "color": "#059669",
                 "description": "Atmospheric evaporative demand summed over each bin."},
    "moisture_balance": {"label": "Moisture Balance (P − ET₀)", "unit": "mm", "category": "Hydrological", "color": "#2563eb",
                         "description": "Precipitation minus evapotranspiration per bin."},
}

BENCHMARK_REGIONS = [
    {"id": "svalbard", "label": "Svalbard, Arctic", "lat": 78.22, "lon": 15.63, "note": "Rapid Arctic polar amplification"},
    {"id": "amazon", "label": "Central Amazon Basin", "lat": -3.47, "lon": -62.21, "note": "Tropical rainforest water balance"},
    {"id": "sierra", "label": "Sierra Nevada, California", "lat": 39.18, "lon": -120.22, "note": "Snowpack and evaporative demand"},
    {"id": "sahel", "label": "Sahel Transition Belt", "lat": 13.51, "lon": 2.12, "note": "Subtropical heat and moisture stress"},
    {"id": "tibet", "label": "Tibetan Plateau", "lat": 33.4, "lon": 88.2, "note": "High-altitude cryosphere and solar flux"},
    {"id": "north_atlantic", "label": "North Atlantic Storm Track", "lat": 51.5, "lon": -28.0, "note": "Mid-latitude jet and winds"},
    {"id": "antarctic_peninsula", "label": "Antarctic Peninsula", "lat": -64.8, "lon": -63.0, "note": "Southern Ocean warming"},
    {"id": "colombo", "label": "Colombo, Sri Lanka", "lat": 6.93, "lon": 79.85, "note": "Monsoon rainfall"},
]

_DAILY_KEYS = {
    "temp": "temperature_2m_mean", "precip": "precipitation_sum", "snow": "snowfall_sum",
    "wind": "wind_speed_10m_max", "solar": "shortwave_radiation_sum", "et0": "et0_fao_evapotranspiration",
}


class ArchiveService:
    CACHE_TTL = 3600

    def __init__(self, client: httpx.AsyncClient, analyzer: TrendAnalyzer | None = None):
        self._client = client
        self._analyzer = analyzer or TrendAnalyzer()
        self._cache: dict[tuple, tuple[float, dict]] = {}

    async def fetch_daily(self, lat: float, lon: float, start_year: int, end_year: int) -> dict:
        key = (round(lat, 2), round(lon, 2), start_year, end_year)
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < self.CACHE_TTL:
            return hit[1]
        response = await self._client.get(ARCHIVE_URL, timeout=90.0, params={
            "latitude": lat, "longitude": lon,
            "start_date": f"{start_year}-01-01", "end_date": f"{end_year}-12-31",
            "daily": DAILY_FIELDS, "wind_speed_unit": "ms", "timezone": "UTC",
        })
        response.raise_for_status()
        daily = response.json().get("daily") or {}
        if not daily.get("time"):
            raise ValueError("Open-Meteo returned no daily data for this location")
        self._cache[key] = (time.time(), daily)
        return daily

    async def analyze(self, lat: float, lon: float, start_year: int, end_year: int,
                      cadence: str, variable_ids: list[str]) -> dict:
        daily = await self.fetch_daily(lat, lon, start_year, end_year)
        bins = self.aggregate(daily, cadence)
        if len(bins) < TrendAnalyzer.MIN_POINTS:
            raise ValueError("Time window too short for trend analysis")
        results = []
        for vid in variable_ids:
            series = self.variable_series(bins, vid)
            stats = self._analyzer.analyze([p["x"] for p in series], [p["value"] for p in series])
            results.append({"id": vid, **VARIABLES[vid], "series": series, "stats": stats})
        return {
            "lat": lat, "lon": lon, "cadence": cadence, "start_year": start_year, "end_year": end_year,
            "source": "Open-Meteo ERA5 historical archive", "bins": len(bins), "variables": results,
        }

    @staticmethod
    def aggregate(daily: dict, cadence: str) -> list[dict]:
        """Group daily rows into annual or quarterly bins. Bins with <80% data are dropped."""
        groups: dict[tuple, dict] = defaultdict(lambda: {"days": 0, **{k: [] for k in _DAILY_KEYS}})
        for i, day in enumerate(daily["time"]):
            year, month = int(day[:4]), int(day[5:7])
            key = (year, (month - 1) // 3 + 1) if cadence == "quarterly" else (year, 0)
            g = groups[key]
            g["days"] += 1
            for short, field in _DAILY_KEYS.items():
                values = daily.get(field) or []
                if i < len(values) and values[i] is not None:
                    g[short].append(values[i])

        bins = []
        for (year, quarter), g in sorted(groups.items()):
            expected = 90 if quarter else 360
            if g["days"] < expected:  # partial period, skip
                continue
            if any(len(g[k]) < 0.8 * g["days"] for k in _DAILY_KEYS):
                continue
            total = lambda k: mean(g[k]) * g["days"]  # scale for a few missing days
            bins.append({
                "label": f"{year} Q{quarter}" if quarter else str(year),
                "year": year, "quarter": quarter or None,
                "x": year + ((quarter - 1) / 4 if quarter else 0.0),
                "temp_mean": mean(g["temp"]), "precip_sum": total("precip"), "snowfall_sum": total("snow"),
                "wind_max": mean(g["wind"]), "solar_radiation": mean(g["solar"]), "et0_evap": total("et0"),
            })
        return bins

    @staticmethod
    def variable_series(bins: list[dict], vid: str) -> list[dict]:
        if vid == "temp_anomaly":
            ref = max(3, math.ceil(0.3 * len(bins)))
            baseline = mean(b["temp_mean"] for b in bins[:ref])
            getter = lambda b: b["temp_mean"] - baseline
        elif vid == "moisture_balance":
            getter = lambda b: b["precip_sum"] - b["et0_evap"]
        else:
            getter = lambda b: b[vid]
        return [{"label": b["label"], "year": b["year"], "quarter": b["quarter"], "x": b["x"],
                 "value": round(getter(b), 3)} for b in bins]
