# Plan: SafeShift Frontend Dashboard + API Layer

## Summary
Replace the skeleton frontend/API layer with a fully functional 7-panel real-time
monitoring dashboard. The dashboard consumes a Server-Sent Events stream from a
FastAPI server and displays live driver fatigue data across panels backed by the
three Nemotron agents. Panel 7 (Policy Monitor) is the NemoClaw track's judge demo moment.

## User Story
As a hackathon judge watching the SafeShift demo,
I want to see a live dashboard that shows all three agents reasoning and acting in real time,
so that I can understand the system's autonomy and the NemoClaw privacy guardrails.

## Problem → Solution
Five files exist as docstring-only stubs with `raise NotImplementedError` / `// TODO` bodies →
Fully implemented dashboard: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
`api/events.py`, `api/server.py`, plus `AuditEntry` added to `core/models.py`.

## Metadata
- **Complexity**: Large
- **Source PRD**: N/A
- **PRD Phase**: N/A
- **Estimated Files**: 6

---

## UX Design

### Before
```
┌─────────────────────────────────┐
│  Static skeleton HTML           │
│  No live data, all TODOs        │
│  No Policy Monitor panel        │
│  SSE throws NotImplementedError │
└─────────────────────────────────┘
```

### After
```
┌──────────────────────────────────────────────────────────┐
│  header: SafeShift  ●  driver_001  shift: 00:42:17       │
├──────────────┬──────────────┬───────────────────────────┤
│ Live Metrics │ Perception   │ Safety Agent               │
│              │ Agent        │ Nemotron-Super             │
│ Eye ████░░   │ Nemotron-    │ SEVERITY: MEDIUM ●pulse    │
│ 0.55         │ Nano-Omni   │ Reason: eye 24% below...   │
│ Blink 14/min │ score ██░░░  │ ✓ intervene  ✓ companion   │
│ Gaze: fwd    │ "slight drp" │ Confidence: 0.82           │
│              │ [eyes_droop] │                            │
├──────────────┼──────────────┼───────────────────────────┤
│ Companion    │ Intervention │ Shift Info                 │
│ Agent        │ Log          │                            │
│ Nemotron-    │              │ Driver: driver_001         │
│ Super        │ [MEDIUM]     │ Shift: shift-abc-123       │
│ "Hey, you've │ alert        │ Elapsed: 00:42:17          │
│  been at it  │ In-cab alert │ ● Running                  │
│  a while..." │ [no more]    │                            │
├──────────────┴──────────────┴───────────────────────────┤
│ Policy Monitor   NemoClaw                                │
│ [All] [NemoClaw] [Safety] [Perception] [Companion]       │
│ ──────────────────────────────────────────────────────   │
│ ▌ 14:03:22 | safety      | tool_call  | check_baseline  │
│ ▌ 14:03:22 | safety      | tool_call  | get_shift_trend │
│ ▌ 14:03:22 | nemoclaw    | policy_evt | ALLOW ntfy.sh   │
│ ▌ 14:03:21 | perception  | api_call   | vlm assess      │
└──────────────────────────────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After |
|---|---|---|
| SSE connect | throws error | EventSource → /stream, auto-reconnect with backoff |
| /state on load | not implemented | pre-populates all panels before first live event |
| Panel 1 | `--` everywhere | live progress bars, colour-shifting eye bar, yawn flash |
| Panel 2 | static text | VLM score bar, flag pills, "Xs ago" ticking counter |
| Panel 3 | no content | pulsing severity badge, Nemotron reason text |
| Panel 4 | no content | chat bubble, trigger badge, "waiting..." idle state |
| Panel 5 | empty list | scrolling log, stop expansion, empty state |
| Panel 6 | "Shift active" | driver ID, shift ID, elapsed clock, live status dot |
| Panel 7 | does not exist | filterable monospace audit stream, flash on BLOCK |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `core/models.py` | all | All dataclass field names — must match exactly |
| P0 | `api/events.py` | all | Existing structure to implement |
| P0 | `api/server.py` | all | Existing structure to implement |
| P0 | `frontend/app.js` | all | Existing SSE wiring to extend |
| P1 | `frontend/styles.css` | all | Existing CSS vars and patterns to extend |
| P1 | `frontend/index.html` | all | Existing HTML structure to replace |
| P1 | `ARCHITECTURE.md` | 310–330 | AuditEntry dataclass definition |
| P2 | `config/settings.py` | all | config.driver.driver_id reference |
| P2 | `tests/conftest.py` | all | Realistic field values for validation |

## External Documentation
| Topic | Key Takeaway |
|---|---|
| Server-Sent Events (MDN) | `EventSource` reconnects automatically; named events via `event: name\ndata: ...\n\n`; unnamed via `data: ...\n\n` caught by `"message"` listener |
| FastAPI StreamingResponse | `StreamingResponse(generator(), media_type="text/event-stream")` with `Cache-Control: no-cache` header |
| asyncio + threading bridge | `loop.call_soon_threadsafe(queue.put_nowait, item)` — safe way to push from a sync agent thread into an async SSE subscriber queue |

---

## Patterns to Mirror

### PYTHON_MODULE_STRUCTURE
```python
# SOURCE: memory/shift_history.py:1-8
"""Read and write per-shift session records..."""
import json
import time

from core.models import FrameAnalysis, InterventionRecord
from memory.store import get_connection
```
- Module docstring first, then stdlib imports, then project imports (absolute)
- No classes; module-level functions only

### PYTHON_LOGGING
```python
# SOURCE: (project convention per ARCHITECTURE.md)
import logging
# Never use print(); always logging.info(), logging.warning(), logging.error()
logging.info("SSE subscriber connected")
logging.warning("SSE queue full; dropping event")
```

### DATACLASS_FIELD_NAMES
```python
# SOURCE: core/models.py:17-30 (FrameAnalysis)
timestamp: float       # unix epoch
driver_id: str
blink_rate: float      # blinks/min
eye_openness: float    # 0.0–1.0
yawn_detected: bool
yawn_frequency: float  # yawns/hour
gaze_direction: str    # "forward"|"left"|"right"|"down"|"up"
gaze_deviation_deg: float
confidence: float
# VLMFrameAssessment: timestamp, driver_id, fatigue_score, description, flags, confidence
# InterventionDecision: should_intervene, severity, intervention_type, trigger_companion, reason, confidence, timestamp
# CompanionMessage: timestamp, driver_id, message, trigger_reason, severity_context
# InterventionRecord: intervention_id, driver_id, shift_id, timestamp, severity, intervention_type, action_summary, suggested_stops
# AuditEntry (from ARCHITECTURE.md): entry_id, timestamp, source, action_type, description, verdict, metadata, driver_id, shift_id
```

### CSS_VARIABLES
```css
/* SOURCE: frontend/styles.css:1-10 */
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0a0a0f; color: #e0e0e0; font-family: system-ui, sans-serif; }
/* Key existing colors: #76b900 (NVIDIA green), #111118 (panel bg), #222 (border) */
/* Severity: #1a2a1a/green=none, #2a2a00/yellow=low, #2a1a00/orange=medium,
             #2a0000/red=high, #e04040/red-bg=critical */
```

### CSS_PANEL_PATTERN
```css
/* SOURCE: frontend/styles.css:41-54 */
section {
  background: #111118;
  border: 1px solid #222;
  border-radius: 8px;
  padding: 1rem;
}
section h2 {
  font-size: 0.9rem; color: #999;
  text-transform: uppercase; letter-spacing: 0.08em;
  margin-bottom: 0.75rem;
}
```

### MODEL_TAG_PATTERN
```css
/* SOURCE: frontend/styles.css:56-66 */
.model-tag {
  background: #76b900; color: #000;
  font-size: 0.65rem; padding: 0.1em 0.4em;
  border-radius: 3px; margin-left: 0.5rem;
  font-weight: 600;
}
```

### JS_DOM_UPDATE_PATTERN
```javascript
// SOURCE: frontend/app.js:34-38
// All panel updaters receive a `data` object with dataclass fields as keys
function updateMetrics(data) {
  // data: FrameAnalysis fields
  document.getElementById("metric-eye-openness").textContent = data.eye_openness.toFixed(2);
}
```

### JS_SSE_PATTERN
```javascript
// SOURCE: frontend/app.js:15-26
const stream = new EventSource("/stream");
stream.addEventListener("message", (e) => {
  const event = JSON.parse(e.data);
  switch (event.type) {
    case "frame": updateLiveMetrics(event.data); break;
    // ...
  }
});
// Server sends: data: {"type": "frame", "data": {...}}\n\n
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `core/models.py` | UPDATE — append AuditEntry dataclass | AuditEntry referenced by events.py and frontend; must live in models per project contract |
| `api/events.py` | UPDATE — implement publish() and subscribe() | Replace NotImplementedError; thread-safe bridge between sync agents and async SSE |
| `api/server.py` | UPDATE — full FastAPI implementation | Replace empty stub; serves frontend + SSE stream + /state |
| `frontend/index.html` | UPDATE — full rewrite | Add all 7 panels, Panel 7 Policy Monitor, shift info panel |
| `frontend/styles.css` | UPDATE — full rewrite | Add all missing panel styles, progress bars, badges, audit list, animations |
| `frontend/app.js` | UPDATE — full rewrite | Implement all handlers, /state preload, reconnect backoff, audit filter |

## NOT Building
- `core/audit.py` — that's Kevin's module; we only need AuditEntry in models.py and the frontend to consume it
- TTS / audio output — out of scope for Josh's area
- Authentication or login
- WebSocket (SSE is specified)
- Any chart/sparkline libraries — plain DOM only
- Test files for this feature (conftest.py already covers fixtures; no new test files required in this plan)

---

## Step-by-Step Tasks

### Task 1: Add AuditEntry to core/models.py
- **ACTION**: Append the AuditEntry dataclass at the end of `core/models.py`
- **IMPLEMENT**:
```python
@dataclass
class AuditEntry:
    """Unified audit record produced by core/audit.py.

    source="nemoclaw" is the exclusive marker for NemoClaw policy-level entries.
    All other sources are agent-level records.

    Owner: Kevin (core/audit.py produces); Josh (frontend/api consumes)
    """
    entry_id: str       # uuid4
    timestamp: float    # unix epoch
    source: str         # "perception" | "safety" | "companion" | "nemoclaw"
    action_type: str    # "tool_call" | "api_call" | "decision" | "policy_event"
    description: str    # human-readable, e.g. "trigger_alert(severity=high)"
    verdict: str        # "allowed" | "blocked" | "info"
    metadata: dict      # open bag: tool args, token counts, model ID, etc.
    driver_id: str = ""  # empty for nemoclaw entries
    shift_id: str = ""   # empty for nemoclaw entries
```
- **MIRROR**: DATACLASS_FIELD_NAMES — field order matches ARCHITECTURE.md exactly
- **IMPORTS**: `from dataclasses import dataclass, field` already at top of file
- **GOTCHA**: `metadata: dict` has no default — this is intentional; callers must always supply it (even `{}`)
- **VALIDATE**: `python -c "from core.models import AuditEntry; print(AuditEntry.__dataclass_fields__.keys())"` should print all 9 field names

### Task 2: Implement api/events.py
- **ACTION**: Replace both `raise NotImplementedError` bodies with a working thread-safe event bus
- **IMPLEMENT**:
```python
"""In-process event bus: agents publish, SSE stream delivers to frontend."""
import asyncio
import json
import logging
from typing import AsyncIterator

_loop: asyncio.AbstractEventLoop | None = None
_subscribers: list[asyncio.Queue] = []
_last_state: dict[str, dict] = {}   # last known value per event_type for /state


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.get_event_loop()
    return _loop


def publish(event_type: str, data: dict) -> None:
    """Publish an event to all SSE subscribers. Safe to call from any thread."""
    _last_state[event_type] = data
    payload = json.dumps({"type": event_type, "data": data})
    message = f"data: {payload}\n\n"
    try:
        loop = _get_loop()
        dead = []
        for q in _subscribers:
            try:
                loop.call_soon_threadsafe(q.put_nowait, message)
            except asyncio.QueueFull:
                logging.warning("SSE queue full; dropping event type=%s", event_type)
            except Exception:
                dead.append(q)
        for q in dead:
            _subscribers.remove(q)
    except Exception as exc:
        logging.error("publish failed: %s", exc)


async def subscribe() -> AsyncIterator[str]:
    """Async generator yielding SSE strings for one browser connection."""
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.append(q)
    try:
        while True:
            message = await q.get()
            yield message
    finally:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


def get_state() -> dict:
    """Return last-known snapshot of all event types (for /state endpoint)."""
    return dict(_last_state)
```
- **MIRROR**: PYTHON_MODULE_STRUCTURE, PYTHON_LOGGING
- **IMPORTS**: `asyncio`, `json`, `logging`, `typing.AsyncIterator`
- **GOTCHA**: `_get_loop()` must be called at publish time, not at import time — the event loop is created by FastAPI's uvicorn startup, which happens after module import. If `get_event_loop()` fails in newer Python (3.10+), use `asyncio.get_running_loop()` inside the async context and store it via a `set_loop()` call from `server.py` startup.
- **GOTCHA**: `list` mutation while iterating — collect dead queues into a separate list, remove after the loop
- **VALIDATE**: Start the server, open `/stream` in browser, call `publish("test", {"x": 1})` from Python REPL — should see `data: {"type": "test", "data": {"x": 1}}` in browser

### Task 3: Implement api/server.py
- **ACTION**: Write full FastAPI application
- **IMPLEMENT**:
```python
"""FastAPI server — serves the frontend and exposes the SSE event stream."""
import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from api.events import subscribe, get_state

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="SafeShift")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.on_event("startup")
async def _store_loop():
    # Make the running loop available to publish() calls from agent threads
    import api.events as ev
    ev._loop = asyncio.get_running_loop()


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/stream")
async def stream():
    async def generator():
        async for chunk in subscribe():
            yield chunk
    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering if behind proxy
        },
    )


@app.get("/state")
async def state():
    return JSONResponse(get_state())


def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Start uvicorn in a background daemon thread. Call from main.py."""
    import threading
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    logging.info("SafeShift dashboard: http://%s:%d", host, port)
```
- **MIRROR**: PYTHON_MODULE_STRUCTURE, PYTHON_LOGGING
- **IMPORTS**: `fastapi`, `fastapi.responses.FileResponse/JSONResponse/StreamingResponse`, `fastapi.staticfiles.StaticFiles`, `uvicorn`
- **GOTCHA**: `StaticFiles` serves `app.js` and `styles.css` from `/static/app.js`, `/static/styles.css`. The HTML must reference them as `/static/app.js` not `app.js`. OR: serve index.html via FileResponse and let the browser load relative paths. Since `GET /` returns `index.html` as a FileResponse from the filesystem, relative paths in HTML (`src="app.js"`) will resolve to `GET /app.js` which won't match. Fix: either mount static files at `/` path OR use absolute paths in HTML (`/static/app.js`). Use the StaticFiles mount approach with updated HTML references.
- **GOTCHA**: `app.on_event("startup")` is deprecated in newer FastAPI — use `lifespan` context manager if FastAPI ≥ 0.93. For hackathon: use the deprecated form for simplicity, it still works.
- **VALIDATE**: `uvicorn api.server:app --reload` → `curl http://localhost:8000/` returns HTML, `curl http://localhost:8000/state` returns `{}`

### Task 4: Rewrite frontend/index.html
- **ACTION**: Full rewrite — keep the semantic HTML structure, add all 7 panels
- **IMPLEMENT** the full structure:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SafeShift — Driver Safety Monitor</title>
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <header>
    <div class="header-left">
      <h1>SafeShift</h1>
      <span class="header-subtitle">Driver Safety Monitor</span>
    </div>
    <div class="header-right">
      <span id="status-dot" class="status-dot running" title="SSE connected"></span>
      <span id="shift-elapsed">00:00:00</span>
    </div>
  </header>

  <main>
    <!-- Panel 1: Live Metrics -->
    <section id="metrics-panel">
      <h2>Live Metrics</h2>
      <div class="metric-row">
        <label>Eye Openness</label>
        <div class="progress-bar-wrap">
          <div id="eye-bar" class="progress-bar" style="width:0%"></div>
        </div>
        <span id="metric-eye-openness" class="metric-value">--</span>
      </div>
      <div class="metric-row">
        <label>Blink Rate</label>
        <span id="metric-blink-rate" class="metric-value">--</span>
        <span class="metric-unit">bpm</span>
      </div>
      <div class="metric-row">
        <label>Gaze</label>
        <span id="metric-gaze" class="metric-value badge-gaze">--</span>
      </div>
      <div class="metric-row">
        <label>Yawn</label>
        <span id="metric-yawn" class="metric-value">--</span>
      </div>
      <div class="metric-footer">
        <span id="metrics-confidence" class="confidence-label">conf: --</span>
        <span id="metrics-timestamp" class="timestamp-label">--</span>
      </div>
    </section>

    <!-- Panel 2: Perception Agent -->
    <section id="perception-panel">
      <h2>Perception Agent <span class="model-tag">Nemotron-3-Nano-Omni</span></h2>
      <div class="metric-row">
        <label>Fatigue Score</label>
        <div class="progress-bar-wrap">
          <div id="fatigue-bar" class="progress-bar" style="width:0%"></div>
        </div>
        <span id="vlm-fatigue-score" class="metric-value">--</span>
      </div>
      <p id="vlm-description" class="vlm-desc">Waiting for first VLM frame...</p>
      <div id="vlm-flags" class="flag-list"></div>
      <div class="metric-footer">
        <span id="vlm-confidence" class="confidence-label">conf: --</span>
        <span id="vlm-age" class="timestamp-label">--</span>
      </div>
    </section>

    <!-- Panel 3: Safety Agent -->
    <section id="safety-panel">
      <h2>Safety Agent <span class="model-tag">Nemotron-Super</span></h2>
      <div id="severity-badge" class="severity-badge" data-severity="none">NONE</div>
      <p id="decision-reason" class="reason-text">Waiting for first decision...</p>
      <div class="pill-row">
        <span id="pill-intervene" class="pill off">intervene</span>
        <span id="pill-companion" class="pill off">companion</span>
        <span id="decision-type" class="pill neutral">--</span>
      </div>
      <div class="metric-footer">
        <span id="decision-confidence" class="confidence-label">conf: --</span>
      </div>
    </section>

    <!-- Panel 4: Companion Agent -->
    <section id="companion-panel">
      <h2>Companion Agent <span class="model-tag">Nemotron-Super</span></h2>
      <div id="companion-messages">
        <p class="waiting-state">Waiting for companion message...</p>
      </div>
    </section>

    <!-- Panel 5: Intervention Log -->
    <section id="intervention-log">
      <h2>Intervention Log</h2>
      <ul id="log-list">
        <li class="empty-state">No interventions this shift</li>
      </ul>
    </section>

    <!-- Panel 6: Shift Info -->
    <section id="shift-info">
      <h2>Shift Info</h2>
      <div class="info-row"><label>Driver</label><span id="info-driver">--</span></div>
      <div class="info-row"><label>Shift ID</label><span id="info-shift" class="mono">--</span></div>
      <div class="info-row"><label>Elapsed</label><span id="info-elapsed">--</span></div>
      <div class="info-row">
        <label>Status</label>
        <span id="info-status" class="status-text">
          <span id="info-dot" class="status-dot running"></span> Running
        </span>
      </div>
    </section>

    <!-- Panel 7: Policy Monitor (full width) -->
    <section id="policy-monitor">
      <h2>Policy Monitor <span class="model-tag nemoclaw-tag">NemoClaw</span></h2>
      <div id="audit-filter">
        <button class="audit-filter-btn active" data-filter="all">All</button>
        <button class="audit-filter-btn" data-filter="nemoclaw">NemoClaw</button>
        <button class="audit-filter-btn" data-filter="safety">Safety Agent</button>
        <button class="audit-filter-btn" data-filter="perception">Perception</button>
        <button class="audit-filter-btn" data-filter="companion">Companion</button>
      </div>
      <ul id="audit-list"></ul>
    </section>
  </main>

  <script src="/static/app.js"></script>
</body>
</html>
```
- **MIRROR**: Semantic HTML first (sections, h2, ul, li, label, span)
- **GOTCHA**: JS and CSS must reference `/static/app.js` and `/static/styles.css` (absolute paths) because `GET /` returns a FileResponse — relative paths would resolve to `/app.js` which isn't mounted
- **VALIDATE**: Open in browser with server running — all 7 sections visible, no JS errors

### Task 5: Rewrite frontend/styles.css
- **ACTION**: Full rewrite extending the existing color palette with all missing panel styles
- **KEY ADDITIONS to implement** (preserve existing variables):
```css
/* CSS variables — define at :root */
:root {
  --color-bg: #0a0a0f;
  --color-panel: #111118;
  --color-border: #222;
  --color-text: #e0e0e0;
  --color-muted: #666;
  --color-accent: #76b900;  /* NVIDIA green */
  --color-red: #e04040;
  --color-amber: #e08000;
  --color-blue: #4080e0;
  --color-purple: #9040e0;
  --color-teal: #40c0b0;
  --font-mono: 'Courier New', Courier, monospace;
}

/* Grid: 3 cols for panels 1-6, panel 7 full width */
main {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1rem;
  padding: 1rem 2rem;
}
#policy-monitor { grid-column: 1 / -1; }

/* Progress bars */
.progress-bar-wrap { flex: 1; background: #1a1a22; border-radius: 3px; height: 8px; margin: 0 0.5rem; }
.progress-bar { height: 100%; border-radius: 3px; transition: width 0.3s, background 0.3s; background: var(--color-accent); }
.progress-bar.warn  { background: var(--color-amber); }
.progress-bar.alert { background: var(--color-red); }
.progress-bar.fatigue-low  { background: var(--color-accent); }
.progress-bar.fatigue-mid  { background: var(--color-amber); }
.progress-bar.fatigue-high { background: var(--color-red); }

/* Severity badge */
.severity-badge { display: inline-block; padding: 0.3em 1em; border-radius: 4px;
  font-weight: 700; font-size: 1.3rem; text-transform: uppercase; margin-bottom: 0.5rem; }
.severity-badge[data-severity="none"]     { background: #1a2a1a; color: var(--color-accent); }
.severity-badge[data-severity="low"]      { background: #1a1a2a; color: var(--color-blue); }
.severity-badge[data-severity="medium"]   { background: #2a1a00; color: var(--color-amber); }
.severity-badge[data-severity="high"]     { background: #2a0000; color: var(--color-red); }
.severity-badge[data-severity="critical"] { background: var(--color-red); color: #fff; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
.severity-badge.pulse { animation: pulse 0.8s ease-in-out 3; }

/* Gaze badge */
.badge-gaze { padding: 0.1em 0.5em; border-radius: 3px; background: #1a2a1a; color: var(--color-accent); }
.badge-gaze.off-forward { background: #2a0000; color: var(--color-red); }

/* Yawn flash badge */
.yawn-active { background: var(--color-red) !important; color: #fff !important;
  animation: pulse 0.5s ease-in-out infinite; }

/* Pills */
.pill { display: inline-block; padding: 0.15em 0.6em; border-radius: 10px;
  font-size: 0.75rem; margin-right: 0.3rem; }
.pill.on  { background: #1a2a1a; color: var(--color-accent); border: 1px solid var(--color-accent); }
.pill.off { background: #1a1a1a; color: #555; border: 1px solid #333; }
.pill.neutral { background: #1a1a2a; color: #999; border: 1px solid #333; }

/* VLM description */
.vlm-desc { font-style: italic; font-size: 0.85rem; color: #bbb; margin: 0.5rem 0; min-height: 2.5em; }

/* Flag pills */
.flag-list { display: flex; flex-wrap: wrap; gap: 0.3rem; margin: 0.3rem 0; }
.flag-pill { background: #2a1a00; color: var(--color-amber); font-size: 0.72rem;
  padding: 0.1em 0.5em; border-radius: 10px; }

/* Companion chat */
.companion-bubble { background: #1a1a2e; border-left: 3px solid var(--color-accent);
  padding: 0.5rem 0.75rem; border-radius: 0 6px 6px 0; font-size: 0.9rem; margin-bottom: 0.4rem; }
.companion-trigger { font-size: 0.7rem; color: #666; margin-top: 0.2rem; }
.waiting-state { color: #444; font-style: italic; font-size: 0.85rem; }

/* Intervention log */
#log-list { list-style: none; max-height: 180px; overflow-y: auto; }
#log-list li { padding: 0.35rem 0; border-bottom: 1px solid #1a1a1a; font-size: 0.8rem; color: #bbb; }
.empty-state { color: #444; font-style: italic; }
.stops-list { padding-left: 1rem; font-size: 0.75rem; color: #666; }

/* Shift info */
.info-row { display: flex; justify-content: space-between; padding: 0.3rem 0;
  border-bottom: 1px solid #1a1a1a; font-size: 0.85rem; }
.info-row label { color: var(--color-muted); }
.mono { font-family: var(--font-mono); font-size: 0.78rem; color: #aaa; }

/* Status dot */
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 0.3rem; }
.status-dot.running { background: var(--color-accent); }
.status-dot.disconnected { background: var(--color-red); }

/* Header */
header { display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 2rem; background: #111118; border-bottom: 1px solid #222; }
.header-right { display: flex; align-items: center; gap: 0.75rem;
  font-size: 0.85rem; font-family: var(--font-mono); color: #aaa; }

/* Policy Monitor */
#audit-filter { margin-bottom: 0.5rem; display: flex; gap: 0.3rem; flex-wrap: wrap; }
.audit-filter-btn { background: #1a1a22; border: 1px solid #333; color: #888;
  padding: 0.2em 0.7em; border-radius: 3px; font-size: 0.75rem; cursor: pointer; }
.audit-filter-btn.active { border-color: var(--color-accent); color: var(--color-accent); }
#audit-list { list-style: none; max-height: 180px; overflow-y: auto;
  font-family: var(--font-mono); font-size: 0.75rem; }
#audit-list li { display: flex; align-items: baseline; gap: 0.5rem;
  padding: 0.2rem 0.4rem; border-left: 3px solid #333; margin-bottom: 1px; }
.audit-allowed { border-left-color: var(--color-accent) !important; }
.audit-blocked  { border-left-color: var(--color-red) !important; }
.audit-info     { border-left-color: #555 !important; }
@keyframes flash-block { 0%{background:#3a0000} 100%{background:transparent} }
.audit-blocked { animation: flash-block 1s ease-out; }
.audit-time { color: #555; white-space: nowrap; }
.audit-source { padding: 0.05em 0.35em; border-radius: 2px; font-size: 0.68rem; white-space: nowrap; }
.src-perception { background: #2a0a4a; color: var(--color-purple); }
.src-safety     { background: #0a1a3a; color: var(--color-blue); }
.src-companion  { background: #0a2a2a; color: var(--color-teal); }
.src-nemoclaw   { background: #1a2a0a; color: var(--color-accent); }
.audit-desc { flex: 1; color: #ccc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.audit-verdict { padding: 0.05em 0.35em; border-radius: 2px; font-size: 0.68rem; white-space: nowrap; }
.verdict-allowed { color: var(--color-accent); }
.verdict-blocked { color: var(--color-red); font-weight: bold; }
.verdict-info    { color: #666; }

/* Metric rows */
.metric-row { display: flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0;
  border-bottom: 1px solid #1a1a1a; font-size: 0.85rem; }
.metric-row label { color: var(--color-muted); min-width: 80px; flex-shrink: 0; }
.metric-value { font-weight: 600; }
.metric-unit { color: #555; font-size: 0.78rem; }
.metric-footer { display: flex; justify-content: space-between; margin-top: 0.4rem; }
.confidence-label { font-size: 0.72rem; color: #444; }
.timestamp-label { font-size: 0.72rem; color: #444; font-family: var(--font-mono); }
.reason-text { font-size: 0.82rem; color: #bbb; min-height: 2em; margin: 0.4rem 0; }
.pill-row { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.3rem; }
.nemoclaw-tag { background: var(--color-accent) !important; }
```
- **MIRROR**: CSS_VARIABLES, CSS_PANEL_PATTERN, MODEL_TAG_PATTERN
- **GOTCHA**: `transition: width 0.3s` on progress bars requires the element to already exist in DOM with an initial `style="width:0%"` — set in HTML
- **VALIDATE**: Open dashboard, verify grid is 3 columns with panel 7 full-width at bottom

### Task 6: Rewrite frontend/app.js
- **ACTION**: Full rewrite — SSE connection, /state preload, all 6 panel updaters, reconnect, audit filter
- **IMPLEMENT** the complete file:

```javascript
/**
 * SafeShift Demo Dashboard — SSE event handler
 * Owner: Josh
 */

// --- State ---
let _shiftStart = null;       // unix epoch from /state or first frame event
let _vlmLastTs = null;        // unix epoch of last VLM event
let _prevSeverityRank = 0;    // for pulse animation on escalation
let _yawnTimer = null;        // auto-clear yawn badge
let _retryDelay = 1000;       // SSE reconnect backoff ms

const SEVERITY_RANK = { none: 0, low: 1, medium: 2, high: 3, critical: 4 };

// --- SSE connection ---
let stream;

function connectSSE() {
  stream = new EventSource("/stream");

  stream.addEventListener("message", (e) => {
    const event = JSON.parse(e.data);
    _retryDelay = 1000;  // reset backoff on successful message
    setStatus(true);
    switch (event.type) {
      case "frame":        updateLiveMetrics(event.data);   break;
      case "vlm":          updatePerceptionAgent(event.data); break;
      case "decision":     updateSafetyAgent(event.data);  break;
      case "companion":    updateCompanionAgent(event.data); break;
      case "intervention": appendIntervention(event.data);  break;
      case "audit":        appendAuditEntry(event.data);    break;
    }
  });

  stream.onerror = () => {
    setStatus(false);
    stream.close();
    setTimeout(connectSSE, _retryDelay);
    _retryDelay = Math.min(_retryDelay * 2, 30000);
  };
}

function setStatus(connected) {
  const dot1 = document.getElementById("status-dot");
  const dot2 = document.getElementById("info-dot");
  const infoStatus = document.getElementById("info-status");
  [dot1, dot2].forEach(d => {
    if (!d) return;
    d.className = "status-dot " + (connected ? "running" : "disconnected");
  });
  if (infoStatus) infoStatus.innerHTML = (connected
    ? '<span class="status-dot running"></span> Running'
    : '<span class="status-dot disconnected"></span> Disconnected');
}

// --- /state preload ---
async function preloadState() {
  try {
    const res = await fetch("/state");
    const state = await res.json();
    if (state.frame)        updateLiveMetrics(state.frame);
    if (state.vlm)          updatePerceptionAgent(state.vlm);
    if (state.decision)     updateSafetyAgent(state.decision);
    if (state.companion)    updateCompanionAgent(state.companion);
    if (state.intervention) appendIntervention(state.intervention);
  } catch (_) { /* server not ready yet */ }
}

// --- Elapsed clock ---
function startElapsedClock() {
  setInterval(() => {
    if (!_shiftStart) return;
    const sec = Math.floor(Date.now() / 1000 - _shiftStart);
    const h = String(Math.floor(sec / 3600)).padStart(2, "0");
    const m = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
    const s = String(sec % 60).padStart(2, "0");
    const t = `${h}:${m}:${s}`;
    const el = document.getElementById("shift-elapsed");
    const el2 = document.getElementById("info-elapsed");
    if (el) el.textContent = t;
    if (el2) el2.textContent = t;
  }, 1000);
}

// --- VLM age counter ---
function startVlmAgeTicker() {
  setInterval(() => {
    if (!_vlmLastTs) return;
    const ago = Math.round(Date.now() / 1000 - _vlmLastTs);
    const el = document.getElementById("vlm-age");
    if (el) el.textContent = `${ago}s ago`;
  }, 1000);
}

// --- Panel 1: Live Metrics ---
function updateLiveMetrics(data) {
  // data: FrameAnalysis fields
  if (!_shiftStart && data.timestamp) _shiftStart = data.timestamp;

  // Eye openness bar
  const openness = data.eye_openness ?? 0;
  const eyeBar = document.getElementById("eye-bar");
  if (eyeBar) {
    eyeBar.style.width = `${Math.round(openness * 100)}%`;
    eyeBar.className = "progress-bar" +
      (openness < 0.4 ? " alert" : openness < 0.6 ? " warn" : "");
  }
  setText("metric-eye-openness", openness.toFixed(2));

  // Blink rate
  setText("metric-blink-rate", (data.blink_rate ?? 0).toFixed(1));

  // Gaze direction badge
  const gazeEl = document.getElementById("metric-gaze");
  if (gazeEl) {
    gazeEl.textContent = data.gaze_direction ?? "--";
    gazeEl.className = "metric-value badge-gaze" +
      (data.gaze_direction !== "forward" ? " off-forward" : "");
  }

  // Yawn
  const yawnEl = document.getElementById("metric-yawn");
  if (yawnEl) {
    if (data.yawn_detected) {
      yawnEl.textContent = "YAWN";
      yawnEl.classList.add("yawn-active");
      clearTimeout(_yawnTimer);
      _yawnTimer = setTimeout(() => {
        yawnEl.textContent = "--";
        yawnEl.classList.remove("yawn-active");
      }, 3000);
    }
  }

  setText("metrics-confidence", `conf: ${(data.confidence ?? 0).toFixed(2)}`);
  setText("metrics-timestamp", fmtTime(data.timestamp));
}

// --- Panel 2: Perception Agent ---
function updatePerceptionAgent(data) {
  // data: VLMFrameAssessment fields
  _vlmLastTs = data.timestamp ?? (Date.now() / 1000);

  const score = data.fatigue_score ?? 0;
  const fatigueBar = document.getElementById("fatigue-bar");
  if (fatigueBar) {
    fatigueBar.style.width = `${Math.round(score * 100)}%`;
    fatigueBar.className = "progress-bar" +
      (score > 0.7 ? " fatigue-high" : score > 0.4 ? " fatigue-mid" : " fatigue-low");
  }
  setText("vlm-fatigue-score", score.toFixed(2));
  setText("vlm-description", data.description ?? "");
  setText("vlm-confidence", `conf: ${(data.confidence ?? 0).toFixed(2)}`);

  const flagsEl = document.getElementById("vlm-flags");
  if (flagsEl) {
    flagsEl.innerHTML = (data.flags ?? [])
      .map(f => `<span class="flag-pill">${f}</span>`)
      .join("");
  }
}

// --- Panel 3: Safety Agent ---
function updateSafetyAgent(data) {
  // data: InterventionDecision fields
  const severity = data.severity ?? "none";
  const badge = document.getElementById("severity-badge");
  if (badge) {
    const prevRank = _prevSeverityRank;
    const newRank = SEVERITY_RANK[severity] ?? 0;
    badge.textContent = severity.toUpperCase();
    badge.setAttribute("data-severity", severity);
    if (newRank > prevRank) {
      badge.classList.remove("pulse");
      void badge.offsetWidth;  // force reflow to restart animation
      badge.classList.add("pulse");
    }
    _prevSeverityRank = newRank;
  }

  setText("decision-reason", data.reason ?? "--");
  setText("decision-confidence", `conf: ${(data.confidence ?? 0).toFixed(2)}`);
  setText("decision-type", data.intervention_type ?? "--");

  setPill("pill-intervene", data.should_intervene);
  setPill("pill-companion", data.trigger_companion);
}

// --- Panel 4: Companion Agent ---
function updateCompanionAgent(data) {
  // data: CompanionMessage fields
  const container = document.getElementById("companion-messages");
  if (!container) return;

  // Remove waiting state
  container.querySelector(".waiting-state")?.remove();

  const bubble = document.createElement("div");
  bubble.className = "companion-bubble";
  bubble.innerHTML = `
    <div>${esc(data.message ?? "")}</div>
    <div class="companion-trigger">${esc(data.trigger_reason ?? "")} · ${fmtTime(data.timestamp)}</div>
  `;
  container.prepend(bubble);

  // Cap at 20 bubbles
  while (container.children.length > 20) container.lastChild.remove();
}

// --- Panel 5: Intervention Log ---
function appendIntervention(data) {
  const list = document.getElementById("log-list");
  if (!list) return;

  list.querySelector(".empty-state")?.remove();

  const li = document.createElement("li");
  const stops = (data.suggested_stops ?? []);
  li.innerHTML = `
    <span class="pill severity-${data.severity}">${esc(data.severity)}</span>
    <strong>${esc(data.intervention_type)}</strong> — ${esc(data.action_summary)}
    <span style="color:#555;margin-left:0.3rem">${fmtTime(data.timestamp)}</span>
    ${stops.length ? `<ul class="stops-list">${stops.map(s => `<li>${esc(s)}</li>`).join("")}</ul>` : ""}
  `;
  list.prepend(li);
  while (list.children.length > 50) list.lastChild.remove();
}

// --- Panel 7: Policy Monitor ---
function appendAuditEntry(data) {
  const list = document.getElementById("audit-list");
  if (!list) return;

  const li = document.createElement("li");
  li.dataset.source = data.source ?? "info";
  const verdictClass = `audit-${data.verdict ?? "info"}`;
  li.className = verdictClass;

  li.innerHTML = `
    <span class="audit-time">${fmtTime(data.timestamp)}</span>
    <span class="audit-source src-${data.source ?? "info"}">${esc(data.source ?? "")}</span>
    <span style="color:#555">${esc(data.action_type ?? "")}</span>
    <span class="audit-desc">${esc(data.description ?? "")}</span>
    <span class="audit-verdict verdict-${data.verdict ?? "info"}">${esc(data.verdict ?? "")}</span>
  `;
  list.prepend(li);
  while (list.children.length > 200) list.lastChild.remove();
  applyAuditFilter();
}

function applyAuditFilter() {
  const activeBtn = document.querySelector(".audit-filter-btn.active");
  const filter = activeBtn ? activeBtn.dataset.filter : "all";
  document.querySelectorAll("#audit-list li").forEach(li => {
    li.style.display = (filter === "all" || li.dataset.source === filter) ? "" : "none";
  });
}

function initAuditFilter() {
  document.querySelectorAll(".audit-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".audit-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      applyAuditFilter();
    });
  });
}

// --- Utilities ---
function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setPill(id, active) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = "pill " + (active ? "on" : "off");
}

function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtTime(ts) {
  if (!ts) return "--";
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], { hour12: false });
}

// --- Startup ---
preloadState();
connectSSE();
startElapsedClock();
startVlmAgeTicker();
initAuditFilter();
```
- **MIRROR**: JS_DOM_UPDATE_PATTERN, JS_SSE_PATTERN
- **GOTCHA**: `void badge.offsetWidth` is required to restart CSS animation — removing and re-adding the class alone doesn't restart it without a forced reflow
- **GOTCHA**: `esc()` helper is critical — audit descriptions and companion messages come from LLM output which may contain `<`, `>`, `&`
- **GOTCHA**: `EventSource` auto-reconnects by default, but the default backoff is slow and doesn't update the status dot — close and re-open manually for controlled backoff
- **VALIDATE**: Open browser devtools → Network → EventSource tab; verify `data:` frames arrive every ~2s. Check all panels update.

---

## Testing Strategy

### Manual Validation (primary — no unit tests needed for pure DOM/SSE code)
1. Start server: `uvicorn api.server:app --reload`
2. Open `http://localhost:8000` — all 7 panels visible, no console errors
3. From Python REPL:
   ```python
   from api.events import publish
   import time
   publish("frame", {"timestamp": time.time(), "driver_id": "d1", "blink_rate": 14.0,
     "eye_openness": 0.35, "yawn_detected": True, "yawn_frequency": 3.0,
     "gaze_direction": "left", "gaze_deviation_deg": 12.0, "confidence": 0.9})
   publish("vlm", {"timestamp": time.time(), "driver_id": "d1", "fatigue_score": 0.72,
     "description": "Driver eyes drooping, head tilting left", "flags": ["eyes_drooping","head_tilt"], "confidence": 0.85})
   publish("decision", {"timestamp": time.time(), "should_intervene": True,
     "severity": "high", "intervention_type": "rest_break", "trigger_companion": True,
     "reason": "24% below baseline, steady decline", "confidence": 0.82})
   publish("companion", {"timestamp": time.time(), "driver_id": "d1",
     "message": "You've been driving for a while — let's find a rest stop.",
     "trigger_reason": "fatigue_building", "severity_context": "high"})
   publish("intervention", {"timestamp": time.time(), "driver_id": "d1", "shift_id": "s1",
     "intervention_id": "r1", "severity": "high", "intervention_type": "rest_break",
     "action_summary": "Rest break recommended", "suggested_stops": ["Aptos Rest Area", "Capitola Truck Stop"]})
   publish("audit", {"entry_id": "a1", "timestamp": time.time(), "source": "nemoclaw",
     "action_type": "policy_event", "description": "DENY outbound to fleet-server.corp",
     "verdict": "blocked", "metadata": {}, "driver_id": "d1", "shift_id": "s1"})
   ```
4. Verify: eye bar turns red at 0.35, yawn badge flashes and auto-clears after 3s, gaze badge turns red for "left"
5. Verify: severity badge pulses on escalation (none→medium→high)
6. Verify: blocked audit entry has red left border and flash animation
7. Verify: audit filter buttons hide/show entries by source correctly
8. Verify: `GET /state` returns all last-known values as JSON

### Edge Cases Checklist
- [ ] SSE disconnect (kill server) → red dot appears, reconnect on restart
- [ ] Empty `flags: []` on VLM event → no flag pills, no crash
- [ ] Empty `suggested_stops: []` on intervention → no stops list shown
- [ ] `yawn_detected: false` after `true` → yawn badge stays cleared until next true
- [ ] severity escalation: none→low→medium→high → pulse fires on each escalation step
- [ ] severity de-escalation: high→low → badge updates but no pulse
- [ ] 201 audit entries → oldest DOM node dropped, cap respected
- [ ] XSS in LLM output: `message: "<script>alert(1)</script>"` → escaped, no XSS

---

## Validation Commands

```bash
# Server starts without import errors
cd Safe-Shift && python -c "from api.server import app; print('ok')"

# AuditEntry importable
python -c "from core.models import AuditEntry; a = AuditEntry('id',1.0,'safety','tool_call','test','allowed',{}) ; print(a)"

# Server runs
uvicorn api.server:app --port 8000
# Then: curl http://localhost:8000/ → HTML, curl http://localhost:8000/state → {}
```

---

## Acceptance Criteria
- [ ] `AuditEntry` importable from `core.models`
- [ ] `publish("frame", {...})` from any thread updates the browser in <100ms
- [ ] `GET /state` returns last-known event payload for each event type
- [ ] All 7 panels render with no JS console errors
- [ ] Eye openness bar shifts green→yellow→red at thresholds 0.6 and 0.4
- [ ] Severity badge pulses on escalation, not de-escalation
- [ ] Yawn badge auto-clears after 3s
- [ ] Blocked audit entries flash on insert and have red left border
- [ ] Audit filter buttons show/hide by source without re-rendering
- [ ] SSE disconnect shows red dot; reconnect restores green dot
- [ ] Companion XSS input is escaped — no script execution
- [ ] Intervention log stops list expands when `suggested_stops` non-empty

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| asyncio loop not running when publish() first called | Medium | `publish()` silently drops event | Store loop in `_store_loop` startup handler; log warning on loop miss |
| FastAPI static file path on different OS | Low | 404 for JS/CSS | Use `Path(__file__).parent.parent / "frontend"` — always relative to server.py |
| NemoClaw runs main loop in separate process | Low | `publish()` won't reach SSE | Document: agents must be co-process with the FastAPI server |
| Browser EventSource doesn't support named events by default | Low | Filter switch breaks | Keep existing unnamed `"message"` listener; parse `event.type` from JSON |

## Notes
- `core/audit.py` is Kevin's — we only need `AuditEntry` in `core/models.py` and the
  frontend's `appendAuditEntry()` handler. The audit events will arrive on the SSE
  stream as `{"type": "audit", "data": <AuditEntry fields>}` once Kevin implements `core/audit.py`.
- The `/static/` mount means `styles.css` and `app.js` are at `/static/styles.css` and
  `/static/app.js` respectively — HTML `<link>` and `<script>` tags must use those paths.
- Demo script for judges: Panel 7 filter → NemoClaw → show the BLOCK entry from the fake
  fleet-server call. This is the most differentiated moment in the 3-minute window.
