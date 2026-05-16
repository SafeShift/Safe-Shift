"""In-process event bus: agents publish, SSE stream delivers to frontend.

Agents call publish() after each cycle from any thread. subscribe() is an async
generator consumed by the SSE endpoint in api/server.py.

Event types:
  "frame"        → FrameAnalysis metrics
  "vlm"          → VLMFrameAssessment
  "decision"     → InterventionDecision
  "companion"    → CompanionMessage
  "intervention" → InterventionRecord
  "audit"        → AuditEntry

Owner: Josh
"""
import asyncio
import json
import logging
import threading
from typing import AsyncIterator

_lock = threading.Lock()
_subscribers: list[asyncio.Queue] = []
_last_state: dict[str, dict] = {}
_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Store the running event loop. Called once from api/server.py at startup."""
    global _loop
    _loop = loop


def publish(event_type: str, data: dict) -> None:
    """Publish an event to all active SSE subscribers. Safe to call from any thread."""
    _last_state[event_type] = data
    if _loop is None or _loop.is_closed():
        logging.debug("publish: no event loop yet, dropping event type=%s", event_type)
        return
    payload = json.dumps({"type": event_type, "data": data})
    message = f"data: {payload}\n\n"
    with _lock:
        dead = []
        for q in _subscribers:
            try:
                _loop.call_soon_threadsafe(q.put_nowait, message)
            except asyncio.QueueFull:
                logging.warning("SSE queue full, dropping event type=%s", event_type)
            except Exception as exc:
                logging.warning("SSE subscriber error: %s", exc)
                dead.append(q)
        for q in dead:
            _subscribers.remove(q)


async def subscribe() -> AsyncIterator[str]:
    """Async generator yielding SSE-formatted strings for one browser connection."""
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    with _lock:
        _subscribers.append(q)
    try:
        while True:
            yield await q.get()
    finally:
        with _lock:
            try:
                _subscribers.remove(q)
            except ValueError:
                pass


def get_state() -> dict:
    """Return last-known snapshot of every event type for the /state endpoint."""
    return dict(_last_state)
