"""TelemetryHub: polls every source on its own schedule and fans out snapshots.

One background task per source, so a slow or broken API never blocks the
others, and every SSE client reads the same shared state instead of causing
its own API calls.
"""
import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from .models import HazardEvent
from .sources.base import DataSource

log = logging.getLogger("telemetry")


class SourceState:
    def __init__(self, source: DataSource):
        self.source = source
        self.events: list[HazardEvent] = []
        self.meta: dict = {}
        self.status = "starting"  # starting | ok | error
        self.last_updated: Optional[str] = None
        self.error: Optional[str] = None


class TelemetryHub:
    def __init__(self, sources: list[DataSource]):
        self._states = {s.name: SourceState(s) for s in sources}
        self._subscribers: set[asyncio.Queue] = set()
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        self._tasks = [asyncio.create_task(self._poll(st)) for st in self._states.values()]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)  # slow clients only need the latest
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def snapshot(self) -> dict:
        events = [e.model_dump(mode="json") for st in self._states.values() for e in st.events]
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "events": events,
            "counts": dict(Counter(e["type"] for e in events)),
            "meta": {name: st.meta for name, st in self._states.items() if st.meta},
            "sources": {
                name: {"status": st.status, "last_updated": st.last_updated,
                       "error": st.error, "count": len(st.events)}
                for name, st in self._states.items()
            },
        }

    async def _poll(self, state: SourceState) -> None:
        while True:
            try:
                result = await state.source.fetch()
                state.events, state.meta = result.events, result.meta
                state.status, state.error = "ok", None
                state.last_updated = datetime.now(timezone.utc).isoformat()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # keep last good data, record the problem
                state.status, state.error = "error", f"{type(exc).__name__}: {exc}"
                log.warning("source %s failed: %s", state.source.name, state.error)
            self._publish()
            await asyncio.sleep(state.source.interval)

    def _publish(self) -> None:
        snap = self.snapshot()
        for queue in self._subscribers:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(snap)
