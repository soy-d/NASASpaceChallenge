"""Offline tests: parsers run against sample API payloads, no network needed.
Run from the backend folder:  python -m pytest
"""
from app.hub import TelemetryHub
from app.models import HazardType, SourceResult
from app.sources.base import DataSource
from app.sources.enso import EnsoSource
from app.sources.eonet import EonetSource
from app.sources.usgs import UsgsSource
from app.sources.weather import OpenMeteoSource, build_grid


def test_eonet_points_and_polygons():
    data = {"events": [
        {"id": "A", "title": "Typhoon X", "categories": [{"id": "severeStorms"}],
         "geometry": [{"type": "Point", "coordinates": [130.0, 20.0], "date": "d1", "magnitudeValue": 90, "magnitudeUnit": "kts"},
                      {"type": "Point", "coordinates": [131.0, 21.0], "date": "d2", "magnitudeValue": 95, "magnitudeUnit": "kts"}]},
        {"id": "B", "title": "Ice", "categories": [{"id": "seaLakeIce"}],
         "geometry": [{"type": "Polygon", "coordinates": [[[0, 70], [10, 70], [10, 80], [0, 80], [0, 70]]], "date": "d"}]},
        {"id": "C", "title": "No geometry", "categories": [{"id": "wildfires"}], "geometry": []},
    ]}
    events = EonetSource.parse(data)
    assert [e.type for e in events] == [HazardType.TYPHOON, HazardType.SEA_ICE]
    assert (events[0].lat, events[0].lng, events[0].value) == (21.0, 131.0, 95)  # latest position wins
    assert 70 < events[1].lat < 80


def test_usgs_quake_and_tsunami_flag():
    data = {"features": [
        {"id": "q1", "properties": {"mag": 6.4, "title": "M 6.4 - Pacific", "time": 1700000000000, "tsunami": 1},
         "geometry": {"coordinates": [150.0, -10.0, 30]}},
        {"id": "q2", "properties": {"mag": 2.6, "title": "M 2.6 - CA", "time": 1700000100000, "tsunami": 0},
         "geometry": {"coordinates": [-120.0, 36.0, 5]}},
    ]}
    events = UsgsSource.parse(data)
    assert [e.type for e in events] == [HazardType.EARTHQUAKE, HazardType.TSUNAMI, HazardType.EARTHQUAKE]
    assert events[0].lng == 150.0 and events[0].lat == -10.0  # GeoJSON is [lng, lat]


def test_weather_classifies_rain_snow_and_averages():
    rows = [
        {"latitude": 0.0, "longitude": 0.0, "current": {"time": "2026-11-16T10:00", "temperature_2m": 30, "rain": 1.2, "showers": 0, "snowfall": 0}},
        {"latitude": 60.0, "longitude": 20.0, "current": {"time": "2026-11-16T10:00", "temperature_2m": -5, "rain": 0, "showers": 0, "snowfall": 0.4}},
        {"latitude": 20.0, "longitude": 40.0, "current": {"time": "2026-11-16T10:00", "temperature_2m": 25, "rain": 0, "showers": 0, "snowfall": 0}},
    ]
    result = OpenMeteoSource.parse(rows)
    kinds = [e.type for e in result.events]
    assert kinds.count(HazardType.TEMPERATURE) == 3
    assert kinds.count(HazardType.RAIN) == 1 and kinds.count(HazardType.SNOW) == 1
    assert result.meta["samples"] == 3 and 15 < result.meta["global_average_c"] < 30


def test_grid_size_stays_within_free_tier():
    assert len(build_grid(20)) == 126


def test_enso_parses_latest_row():
    text = "SEAS  YR   TOTAL  ANOM\n DJF 2025  26.1  -0.2\n SON 2026  27.0   0.7\n"
    result = EnsoSource.parse(text)
    assert result.meta["phase"] == "El Niño" and result.meta["season"] == "SON 2026"


class _Boom(DataSource):
    name, interval = "boom", 1

    async def fetch(self):
        raise RuntimeError("api down")


def test_hub_records_errors_and_snapshot_shape():
    import asyncio

    async def run():
        hub = TelemetryHub([_Boom(None)])
        await hub.start()
        await asyncio.sleep(0.05)
        snap = hub.snapshot()
        await hub.stop()
        return snap

    snap = asyncio.run(run())
    assert snap["sources"]["boom"]["status"] == "error"
    assert "api down" in snap["sources"]["boom"]["error"]
