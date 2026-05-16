"""In-process event bus: agents publish, SSE stream delivers to frontend.

Agents (orchestrator, companion) call publish() after each cycle. The SSE stream
in api/server.py subscribes and forwards events to the browser in real time.

Event types:
  "frame"         → FrameAnalysis metrics (eye openness, blink rate, gaze)
  "vlm"           → VLMFrameAssessment (fatigue score, description, flags)
  "decision"      → InterventionDecision (severity, type, reason, confidence)
  "companion"     → CompanionMessage (message text, trigger reason)
  "intervention"  → InterventionRecord (what action was taken)

Owner: Josh
"""
import asyncio
from typing import AsyncIterator


_subscribers: list = []


def publish(event_type: str, data: dict) -> None:
    """Publish an event to all active SSE subscribers.

    Called from agents/orchestrator.py after each cycle. Thread-safe.

    Args:
        event_type: one of "frame" | "vlm" | "decision" | "companion" | "intervention"
        data: JSON-serializable dict of event payload
    """
    raise NotImplementedError


async def subscribe() -> AsyncIterator[str]:
    """Async generator yielding SSE-formatted strings for an active browser connection.

    Used by api/server.py GET /stream endpoint.

    Yields:
        SSE-formatted strings, e.g. "data: {...}\\n\\n"
    """
    raise NotImplementedError
