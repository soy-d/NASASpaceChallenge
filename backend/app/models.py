"""Shared data models for every hazard the dashboard can show."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class HazardType(str, Enum):
    TYPHOON = "typhoon"
    WILDFIRE = "wildfire"
    VOLCANO = "volcano"
    SEA_ICE = "sea_ice"
    EARTHQUAKE = "earthquake"
    TSUNAMI = "tsunami"
    RAIN = "rain"
    SNOW = "snow"
    TEMPERATURE = "temperature"
    EL_NINO = "el_nino"


class HazardEvent(BaseModel):
    """One point on the globe."""

    id: str
    type: HazardType
    title: str
    lat: float
    lng: float
    value: Optional[float] = None
    unit: Optional[str] = None
    date: Optional[str] = None  # ISO 8601, UTC
    source: str


class SourceResult(BaseModel):
    """What a data source returns from one fetch."""

    events: list[HazardEvent] = []
    meta: dict = {}
