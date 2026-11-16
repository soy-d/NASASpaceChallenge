import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# .env lives in the project root: backend/app/main.py -> parents[2]
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from .analysis.archive import ArchiveService  # noqa: E402
from .analysis.router import router as analysis_router  # noqa: E402
from .hub import TelemetryHub  # noqa: E402
from .sources.enso import EnsoSource  # noqa: E402
from .sources.eonet import EonetSource  # noqa: E402
from .sources.usgs import UsgsSource  # noqa: E402
from .sources.weather import OpenMeteoSource  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": "earth-system-trend-detective"}) as client:
        hub = TelemetryHub([EonetSource(client), UsgsSource(client), OpenMeteoSource(client), EnsoSource(client)])
        app.state.hub = hub
        app.state.http = client
        app.state.archive = ArchiveService(client)
        await hub.start()
        yield
        await hub.stop()


app = FastAPI(title="Earth System API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(analysis_router)


@app.get("/")
def read_root():
    return {"status": "Backend is online."}


@app.get("/api/telemetry/snapshot")
def snapshot():
    return app.state.hub.snapshot()


@app.get("/api/telemetry/stream")
async def stream_telemetry():
    hub: TelemetryHub = app.state.hub

    async def events():
        queue = hub.subscribe()
        try:
            # send what we have immediately, then every update
            yield {"event": "telemetry", "data": json.dumps(hub.snapshot())}
            while True:
                snap = await queue.get()
                yield {"event": "telemetry", "data": json.dumps(snap)}
        except asyncio.CancelledError:
            raise
        finally:
            hub.unsubscribe(queue)

    return EventSourceResponse(events(), ping=15)
