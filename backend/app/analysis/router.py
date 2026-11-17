# REST endpoints for the historical climate analysis dashboard views.
"""REST endpoints for the past-data analysis part of the dashboard."""
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from ..sources.enso import ONI_URL, EnsoSource, phase_for
from .archive import BENCHMARK_REGIONS, VARIABLES
from .stats import TrendAnalyzer

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

SEASON_CENTER_MONTH = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
                       "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}
_oni_cache: dict = {"at": 0.0, "text": ""}


def last_full_year() -> int:
    return datetime.now(timezone.utc).year - 1


@router.get("/variables")
def variables():
    return {
        "variables": [{"id": k, **v} for k, v in VARIABLES.items()],
        "regions": BENCHMARK_REGIONS,
        "min_year": 1960,
        "max_year": last_full_year(),
    }


@router.get("/timeseries")
async def timeseries(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    variables: str = Query("temp_mean,precip_sum"),
    cadence: str = Query("annual", pattern="^(annual|quarterly)$"),
    start_year: int = Query(2000, ge=1960),
    end_year: int | None = Query(None),
):
    end_year = min(end_year or last_full_year(), last_full_year())
    if end_year - start_year < 4:
        raise HTTPException(400, "Choose a window of at least 5 years")
    ids = [v for v in dict.fromkeys(x.strip() for x in variables.split(",")) if v in VARIABLES]
    if not ids:
        raise HTTPException(400, "No valid variables requested")
    try:
        return await request.app.state.archive.analyze(
            max(-85, min(85, lat)), lon, start_year, end_year, cadence, ids)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Open-Meteo archive request failed: {type(exc).__name__}: {exc}")
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.get("/enso")
async def enso_history(request: Request, start_year: int = Query(1980, ge=1950)):
    """Oceanic Niño Index history (NOAA CPC) with trend statistics."""
    if time.time() - _oni_cache["at"] > 6 * 3600:
        try:
            response = await request.app.state.http.get(ONI_URL, timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"NOAA ONI request failed: {type(exc).__name__}: {exc}")
        _oni_cache.update(at=time.time(), text=response.text)
    rows = [r for r in EnsoSource.parse_rows(_oni_cache["text"]) if r[1] >= start_year and r[0] in SEASON_CENTER_MONTH]
    if len(rows) < TrendAnalyzer.MIN_POINTS:
        raise HTTPException(422, "Not enough ONI data in this window")
    series = [{"label": f"{s} {y}", "year": y, "x": y + (SEASON_CENTER_MONTH[s] - 0.5) / 12,
               "value": a, "phase": phase_for(a)} for s, y, a in rows]
    stats = TrendAnalyzer().analyze([p["x"] for p in series], [p["value"] for p in series])
    stats["trend_line"] = stats["trend_line"][:: max(1, len(series) // 120)]  # keep payload small
    el_nino = sum(p["phase"] == "El Niño" for p in series)
    la_nina = sum(p["phase"] == "La Niña" for p in series)
    return {"source": "NOAA CPC Oceanic Niño Index", "start_year": start_year, "series": series,
            "stats": stats, "counts": {"El Niño": el_nino, "La Niña": la_nina, "Neutral": len(series) - el_nino - la_nina}}
