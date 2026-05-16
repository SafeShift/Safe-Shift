"""FastAPI server — serves the dashboard and exposes the SSE event stream.

Endpoints:
  GET /       → serves frontend/monitoring-dashboard/public/dashboard.html
  GET /stream → SSE stream; agents publish events via api/events.publish()
  GET /state  → JSON snapshot of last-known value per event type (for page reload)

Call start_server() from main.py to launch uvicorn in a background daemon thread.

Owner: Josh
Imports from: api.events
"""
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

import api.events as events
import api.video as video

DASHBOARD_HTML = (
    Path(__file__).parent.parent
    / "frontend"
    / "monitoring-dashboard"
    / "public"
    / "dashboard.html"
)

app = FastAPI(title="SafeShift")


@app.on_event("startup")
async def _store_loop() -> None:
    events.set_event_loop(asyncio.get_running_loop())


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(DASHBOARD_HTML))


@app.get("/stream")
async def stream() -> StreamingResponse:
    async def _generator():
        async for chunk in events.subscribe():
            yield chunk

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/state")
async def state() -> JSONResponse:
    return JSONResponse(events.get_state())


@app.get("/video")
async def video_feed() -> StreamingResponse:
    return StreamingResponse(
        video.mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start uvicorn in a background daemon thread. Call once from main.py."""
    import threading
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    logging.info("SafeShift dashboard: http://%s:%d", host, port)
