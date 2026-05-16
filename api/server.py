"""FastAPI server — serves the frontend and exposes the SSE event stream.

Endpoints:
  GET /          → serves frontend/index.html
  GET /stream    → SSE stream; agents publish events via api/events.py
  GET /state     → latest snapshot of driver state (JSON) for initial page load

The server runs as a background thread alongside main.py so agents can publish
events without blocking the vision pipeline.

Owner: Josh
Imports from: api.events, config.settings
"""
