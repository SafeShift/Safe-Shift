"""FastAPI server — serves the dashboard and exposes the SSE event stream.

Endpoints:
  GET  /        → serves frontend/monitoring-dashboard/public/dashboard.html
  GET  /stream  → SSE stream; agents publish events via api/events.publish()
  GET  /state   → JSON snapshot of last-known value per event type (for page reload)
  GET  /video   → MJPEG camera feed
  POST /ingest  → receive (FrameAnalysis, JPEG frame) from local vision node (cloud mode)

Call start_server() from main.py to launch uvicorn in a background daemon thread.

Owner: Josh
Imports from: api.events
"""
import asyncio
import logging
import queue
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

import api.events as events
import api.video as video

# Ingest queue: filled by POST /ingest in cloud mode; drained by main loop on Brev
_ingest_queue: queue.Queue = queue.Queue(maxsize=30)


def get_ingest_queue() -> queue.Queue:
    """Return the ingest queue for cloud-mode main loop to drain."""
    return _ingest_queue

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


@app.post("/ingest")
async def ingest(request: Request) -> JSONResponse:
    """Receive a FrameAnalysis + optional JPEG from the local vision node (cloud mode).

    Expected JSON body:
      {
        "analysis": { ...FrameAnalysis fields... },
        "frame_jpeg_b64": "<base64-encoded JPEG>"   # optional
      }
    """
    import base64
    import numpy as np
    import cv2
    from core.models import FrameAnalysis

    body = await request.json()

    try:
        analysis = FrameAnalysis(**body["analysis"])
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    frame_bgr = None
    if "frame_jpeg_b64" in body:
        try:
            jpeg_bytes = base64.b64decode(body["frame_jpeg_b64"])
            with video._lock:
                video._jpeg = jpeg_bytes
            buf = np.frombuffer(jpeg_bytes, np.uint8)
            frame_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception:
            pass

    try:
        _ingest_queue.put_nowait((frame_bgr, analysis))
    except queue.Full:
        pass

    return JSONResponse({"ok": True})


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start uvicorn in a background daemon thread. Call once from main.py."""
    import threading
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    logging.info("SafeShift dashboard: http://%s:%d", host, port)
