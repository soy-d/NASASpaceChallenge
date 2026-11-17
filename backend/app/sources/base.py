# Base contract for all remote data providers that feed the live global telemetry stream.
"""Abstract base class that every data source implements."""
from abc import ABC, abstractmethod

import httpx

from ..models import SourceResult


class DataSource(ABC):
    #: unique key, used in the snapshot ("sources" and "meta" sections)
    name: str = "source"
    #: seconds between refreshes
    interval: int = 60

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    @abstractmethod
    async def fetch(self) -> SourceResult:
        """Fetch fresh data. Raise on failure; the hub records the error
        and keeps serving the last good data."""
