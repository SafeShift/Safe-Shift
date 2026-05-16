# SafeShift — Architecture Reference

> Read this before touching any code. It is the shared contract that lets four people
> build in parallel without merge conflicts.

---

## Project Summary

SafeShift is a privacy-first, multi-agent driver-safety system. Three specialized AI
agents work in concert: a **Perception Agent** (Nemotron-3-Nano-Omi VLM) that reads the
camera feed and produces a semantic fatigue assessment from the raw scene; a **Safety
Reasoning Agent** (Nemotron-Super) that reasons across the full shift history against a
per-driver baseline and decides on graduated interventions via a ReAct loop; and a
**Companion Agent** (Nemotron-Super) that proactively engages the driver in conversation
when fatigue is building — asking questions, suggesting a break, or just keeping them
alert — before a hard intervention becomes necessary. All three agents run under
NemoClaw, which enforces a strict access policy: data stays on-device, and the agent
literally cannot contact an employer, fleet system, or third party.

**Design principle:** Driver-only, closed loop. No employer dashboard, no fleet
telemetry, no cloud storage of session data. A driver using SafeShift should feel like
it is working *for* them, not surveilling them on behalf of someone else.

**Target hardware:** A dedicated dash-cam-adjacent device (camera + compute + small
display or speaker) running under NemoClaw, pushing alerts to the driver's own phone via
a self-hosted ntfy instance. For the hackathon demo: laptop webcam + ntfy public server.

**Hackathon goal:** A live, running multi-agent system that (1) analyzes a webcam frame
with the Nemotron VLM subagent, (2) reasons over shift history with Nemotron-Super via a
ReAct loop, (3) triggers the companion agent to start a conversation, (4) calls the
rest-stop finder tool and pushes a location-aware notification to a phone via ntfy, and
(5) updates the local driver baseline — all as one observable end-to-end loop under
NemoClaw policy control, visible in real time on the demo dashboard.

---

## Team Ownership

| Person | Agent / Area | Directories |
|--------|-------------|-------------|
| **Caleb** | Perception Agent | `vision/` |
| **Kevin** | Safety Reasoning Agent + orchestration + audit recorder | `core/`, `agents/` (except companion.py), `llm/` (except companion_prompts.py), `actions/` (except rest_finder.py), `memory/`, `config/`, `main.py` |
| **Emilio** | Companion Agent | `agents/companion.py`, `llm/companion_prompts.py`, `actions/rest_finder.py` |
| **Josh** | Frontend + tests | `frontend/`, `api/`, `tests/`, `deployment/` |

**Critical path:** Kevin finalizes `core/models.py` first. Everyone reviews. Nobody edits
it after that without team coordination — all four owners depend on it from day one.

**Conflict rule:** Kevin owns `llm/client.py` (shared LLM client). Emilio imports it but
does not edit it. If Emilio needs a new parameter, ask Kevin to add it.

---

## Data Flow

```
main.py  ← generates shift_id + shift_start; drives loop; calls end_shift() on exit
        │                                      [all running under nemoclaw-policy.yaml]
        ▼
Camera / RTSP stream
        │
   ┌────┴──────────────────────────────┐
   ▼                                   ▼
 vision/pipeline.py              vision/vlm_analyzer.py
 MediaPipe landmarks →            Nemotron-3-Nano-Omi VLM →
 FrameAnalysis  (every 2 s)       VLMFrameAssessment  (every ~10 s)
   └──────────────┬────────────────────┘
                  ▼
 agents/context_builder.py   ← FrameAnalysis + VLMFrameAssessment + memory → ShiftContext
                  │
                  ▼
 ┌────────────────────────────────────────────────────────┐
 │          SAFETY REASONING AGENT  (agents/safety.py)    │
 │          Nemotron-Super via OpenClaw ReAct loop         │
 │          llm/client.py + llm/safety_prompts.py         │
 │          Reason → Act (tools) → Observe → repeat       │
 └──────────────────────┬─────────────────────────────────┘
                        │  InterventionDecision
         ┌──────────────┴──────────────────┐
         │ trigger_companion=True          │ should_intervene=True
         ▼                                 ▼
 ┌────────────────────────┐      agents/orchestrator.py
 │   COMPANION AGENT      │      dispatch via OpenClaw tools
 │   agents/companion.py  │ ┌────┴──────┬──────────────┐
 │   Nemotron-Super        │ ▼           ▼               ▼
 │   llm/companion_prompts │ actions/  actions/        actions/
 │   → CompanionMessage    │ alert.py  rest_break.py  phone_notify.py
 └──────────┬─────────────┘ │          + rest_finder        │
            │               │            (Nominatim)        │
            └──────┬────────┴───────────────┬───────────────┘
                   │                        │  InterventionRecord
                   ▼                        ▼
            display / TTS       actions/logging_client.py  (every cycle)
                                api/events.py              (publishes to frontend)
                                           │
                                           ▼
                               memory/shift_history.py    ← stays on-device
                               memory/driver_baseline.py  ← updated at end_shift
```

---

## Directory Structure

```
Safe-Shift/
│
├── core/                        # Shared dataclasses + audit recorder — EVERYONE imports from here
│   ├── models.py                # FrameAnalysis, VLMFrameAssessment, ShiftContext,
│   │                            #   InterventionDecision, CompanionMessage, AuditEntry, etc.
│   │                            # Owner: Kevin (finalize first, then freeze)
│   └── audit.py                 # Shared audit recorder — all 3 agents call this
│                                # Owner: Kevin
│
├── vision/                      # Perception Agent — Caleb
│   ├── capture.py               # webcam / RTSP frame grabber
│   ├── preprocess.py            # resize, normalize, crop to face ROI
│   ├── landmarks.py             # MediaPipe FaceMesh → landmark coords
│   ├── features.py              # blink rate, eye openness, yawn, gaze
│   ├── pipeline.py              # aggregates N-frame window → FrameAnalysis (every 2 s)
│   └── vlm_analyzer.py          # Nemotron-nano-omi → VLMFrameAssessment (every ~10 s)
│
├── agents/                      # Agent logic
│   ├── orchestrator.py          # per-cycle loop; coordinates all agents — Kevin
│   ├── context_builder.py       # builds ShiftContext from vision + memory — Kevin
│   ├── safety.py                # Safety Reasoning Agent (ReAct loop) — Kevin
│   ├── tools.py                 # OpenClaw tool registry + handlers — Kevin
│   └── companion.py             # Companion Agent — Emilio
│
├── llm/                         # LLM client layer
│   ├── client.py                # Nemotron API client (shared) — Kevin owns, Emilio imports
│   ├── safety_prompts.py        # Safety Reasoning Agent prompts — Kevin
│   ├── companion_prompts.py     # Companion Agent prompts — Emilio
│   └── parser.py                # parse completions → typed dataclasses — Kevin
│
├── actions/                     # What happens when agents decide to act
│   ├── alert.py                 # in-cab alert handler — Kevin
│   ├── rest_break.py            # rest break handler — Kevin
│   ├── phone_notify.py          # ntfy push handler — Kevin
│   ├── rest_finder.py           # Nominatim stop lookup — Emilio
│   ├── alerting_client.py       # in-cab alert HTTP client — Kevin
│   ├── notify_client.py         # ntfy HTTP client — Kevin
│   └── logging_client.py        # local JSONL session logger — Kevin
│
├── memory/                      # SQLite persistence layer — Kevin
│   ├── store.py                 # DB connection, table init
│   ├── driver_baseline.py       # get_baseline / save_baseline
│   └── shift_history.py         # append_frame, append_intervention, get_*
│
├── frontend/                    # Demo dashboard — Josh
│   ├── index.html               # dashboard layout (6 panels)
│   ├── app.js                   # SSE listener + panel updaters
│   └── styles.css               # NVIDIA-green dark theme
│
├── api/                         # FastAPI server — Josh
│   ├── server.py                # GET / (frontend), GET /stream (SSE), GET /state
│   └── events.py                # in-process event bus: agents publish, frontend subscribes
│
├── config/                      # Kevin
│   ├── settings.py              # typed Settings object from .env
│   └── defaults.yaml            # thresholds, window sizes, model IDs
│
├── deployment/                  # Josh
│   ├── nemoclaw-policy.yaml     # NemoClaw sandbox policy (allow/deny rules)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── brev.yaml
│   └── setup_brev.sh
│
├── tests/                       # Josh (fixtures) + each owner (test cases)
│   ├── conftest.py              # sample instances of every dataclass
│   ├── test_vision.py           # vision/ — Caleb
│   ├── test_agents.py           # agents/ safety + companion — Kevin + Emilio
│   ├── test_llm.py              # llm/ prompts + parser — Kevin
│   ├── test_actions.py          # actions/ handlers + clients — Kevin + Emilio
│   └── test_memory.py           # memory/ — Kevin
│
├── main.py                      # Kevin — shift lifecycle, pipeline loop, server startup
└── requirements.txt
```

---

## Interface Contracts

All types live in `core/models.py`. Import from there — never redefine locally.

### `FrameAnalysis`
Produced by `vision/pipeline.py` every ~2 s.

```python
@dataclass
class FrameAnalysis:
    timestamp: float
    driver_id: str
    blink_rate: float          # blinks/min
    eye_openness: float        # 0.0–1.0
    yawn_detected: bool
    yawn_frequency: float      # yawns/hour
    gaze_direction: str        # "forward"|"left"|"right"|"down"|"up"
    gaze_deviation_deg: float
    confidence: float          # 0.0–1.0
```

### `VLMFrameAssessment`
Produced by `vision/vlm_analyzer.py` every ~10 s (Nemotron-nano-omi).

```python
@dataclass
class VLMFrameAssessment:
    timestamp: float
    driver_id: str
    fatigue_score: float       # 0.0–1.0
    description: str           # natural language scene description
    flags: list                # list[str] e.g. ["eyes_drooping", "head_tilt"]
    confidence: float          # 0.0–1.0
```

### `DriverBaseline`
Persisted per driver; read at shift start, updated at shift end.

```python
@dataclass
class DriverBaseline:
    driver_id: str
    avg_blink_rate: float
    avg_eye_openness: float
    avg_yawn_frequency: float
    shift_count: int
    last_updated: str          # ISO-8601
```

### `ShiftTrend`
Computed by `agents/context_builder.py` from full shift history.

```python
@dataclass
class ShiftTrend:
    shift_id: str
    trend_bucket_minutes: float
    sample_count: int = 0
    yawn_count_total: int = 0
    intervention_count: int = 0
    avg_eye_openness_trend: list = field(default_factory=list)
    avg_blink_rate_trend: list = field(default_factory=list)
```

### `ShiftContext`
Assembled by `agents/context_builder.py`; consumed by both agents.

```python
@dataclass
class ShiftContext:
    driver_id: str
    shift_id: str
    shift_elapsed_minutes: float
    current_analysis: FrameAnalysis
    shift_trend: ShiftTrend
    baseline: DriverBaseline
    recent_window: list = field(default_factory=list)
    prior_interventions: list = field(default_factory=list)
    vlm_assessment: Optional[VLMFrameAssessment] = None
```

### `InterventionDecision`
Output of `agents/safety.py`; drives orchestrator dispatch.

```python
@dataclass
class InterventionDecision:
    should_intervene: bool
    severity: str              # "none"|"low"|"medium"|"high"|"critical"
    intervention_type: str     # "none"|"alert"|"rest_break"|"phone_notify"
    trigger_companion: bool    # independent of should_intervene
    reason: str
    confidence: float
    timestamp: float
```

### `CompanionMessage`
Output of `agents/companion.py`.

```python
@dataclass
class CompanionMessage:
    timestamp: float
    driver_id: str
    message: str
    trigger_reason: str        # "fatigue_building"|"long_silence"|"pre_intervention"
    severity_context: str
```

### `InterventionRecord`
Written to memory after an action handler executes.

```python
@dataclass
class InterventionRecord:
    intervention_id: str       # uuid4
    driver_id: str
    shift_id: str
    timestamp: float
    severity: str
    intervention_type: str
    action_summary: str
    suggested_stops: list = field(default_factory=list)
```

### `AuditEntry`
Produced by `core/audit.py`; published to frontend as `"audit"` SSE events and
written to `./logs/agent_audit.jsonl`. Unifies agent-level records (tool calls,
API hits, decisions) with surfaced NemoClaw policy events.

```python
@dataclass
class AuditEntry:
    entry_id: str       # uuid4
    timestamp: float    # unix epoch
    source: str         # "perception"|"safety"|"companion"|"nemoclaw"
    action_type: str    # "tool_call"|"api_call"|"decision"|"policy_event"
    description: str    # human-readable, e.g. "trigger_alert(severity=high)"
    verdict: str        # "allowed"|"blocked"|"info"
    metadata: dict      # open bag: tool args, token counts, model ID, etc.
    driver_id: str = ""  # empty for nemoclaw entries
    shift_id: str = ""   # empty for nemoclaw entries
```

`source="nemoclaw"` is the exclusive marker for NemoClaw policy-level entries —
the frontend filter and color scheme key off this single field.

---

## Key Function Signatures

```python
# main.py
def start_shift(driver_id: str) -> tuple[str, float]: ...   # (shift_id, shift_start)
def end_shift(shift_id: str, driver_id: str) -> None: ...

# vision/pipeline.py
def run_pipeline(driver_id: str) -> Iterator[FrameAnalysis]: ...

# vision/vlm_analyzer.py
def assess_frame(frame_jpeg: bytes, driver_id: str, timestamp: float) -> VLMFrameAssessment: ...

# agents/context_builder.py
def build_context(
    frame: FrameAnalysis,
    shift_id: str,
    shift_start: float,
    vlm_assessment: Optional[VLMFrameAssessment] = None
) -> ShiftContext: ...

# agents/safety.py
def run(context: ShiftContext) -> InterventionDecision: ...

# agents/companion.py
def generate(context: ShiftContext, prior_messages: list[CompanionMessage]) -> CompanionMessage: ...

# agents/orchestrator.py
def run_cycle(frame: FrameAnalysis, shift_id: str, shift_start: float,
              vlm_assessment: Optional[VLMFrameAssessment] = None) -> None: ...

# memory/driver_baseline.py
def get_baseline(driver_id: str) -> DriverBaseline: ...
def save_baseline(baseline: DriverBaseline) -> None: ...

# memory/shift_history.py
def append_frame(shift_id: str, frame: FrameAnalysis) -> None: ...
def append_intervention(record: InterventionRecord) -> None: ...
def get_recent_frames(shift_id: str, minutes: int) -> list[FrameAnalysis]: ...
def get_all_frames(shift_id: str) -> list[FrameAnalysis]: ...
def get_interventions(shift_id: str) -> list[InterventionRecord]: ...

# actions/alert.py  (rest_break.py, phone_notify.py — same signature)
def execute(decision: InterventionDecision, driver_id: str) -> InterventionRecord: ...

# actions/rest_finder.py
def find_nearby_stops(latitude: float, longitude: float, radius_km: int, max_results: int) -> list: ...

# api/events.py
def publish(event_type: str, data: dict) -> None: ...

# core/audit.py  — fire-and-forget, never raises, all agents import these
def start_audit_recorder() -> None: ...
    # call once at main.py startup; starts writer thread + NemoClaw tail thread; idempotent
def record_tool_call(agent: str, tool_name: str, args: dict, result: dict, driver_id: str, shift_id: str) -> None: ...
def record_api_call(agent: str, endpoint: str, model: str, prompt_tokens: int, completion_tokens: int, driver_id: str, shift_id: str) -> None: ...
def record_decision(agent: str, description: str, metadata: dict, driver_id: str, shift_id: str) -> None: ...
```

---

## NemoClaw Policy

`deployment/nemoclaw-policy.yaml` controls runtime access. Show this to judges — then
show the audit log proving the guardrails fired.

```yaml
version: "1"
policy:
  filesystem:
    allow:
      - path: "./safeshift.db"
        permissions: [read, write]
      - path: "./logs/"
        permissions: [read, write]
    deny:
      - path: "~/"
      - path: "/etc/"
  network:
    allow:
      - host: "integrate.api.nvidia.com"   # Nemotron endpoints
        ports: [443]
      - host: "ntfy.sh"                     # driver phone only
        ports: [443]
      - host: "nominatim.openstreetmap.org" # rest stop finder
        ports: [443]
    deny:
      - host: "*"
  device:
    allow:
      - path: "/dev/video0"
  shell:
    deny: "*"
  audit:
    log: "./logs/audit.log"
    level: full
```

---

## OpenClaw Tool Registry

Declared in `agents/tools.py`. These are the exact schemas Nemotron-Super sees during
the Safety Reasoning Agent ReAct loop.

**Query tools** (gather info before deciding):
- `check_baseline(driver_id)` — pulls DriverBaseline from memory
- `get_shift_trend(shift_id)` — pulls ShiftTrend from shift history
- `get_recent_interventions(shift_id, last_n_minutes)` — prevents over-escalation

**Action tools** (take effect in the world):
- `trigger_alert(severity, reason)` → `actions/alert.execute()`
- `trigger_rest_break(severity, reason, suggested_minutes)` → `actions/rest_break.execute()`
- `trigger_phone_notify(severity, message)` → `actions/phone_notify.execute()`
- `log_intervention(intervention_type, severity, action_summary)` — always called last

---

## Escalation Model

```
severity=low      → trigger_companion=True  only (Companion engages, no hard action)
severity=medium   → trigger_companion=True  + trigger_alert or rest_break
severity=high     → trigger_companion=True  + rest_break + phone_notify
severity=critical → trigger_companion=True  + all actions
```

Cooldown between same-level interventions: `severity_escalation_minutes` in
`config/defaults.yaml`. The Safety Reasoning Agent checks `get_recent_interventions`
before escalating — this is part of the ReAct loop, not hardcoded logic.

---

## Frontend Event Stream

`api/events.py` is the event bus. Agents call `publish()` after each cycle.
Josh's `api/server.py` forwards events via SSE to `frontend/app.js`.

| Event type | Source | Frontend panel |
|---|---|---|
| `"frame"` | orchestrator (every cycle) | Live Metrics |
| `"vlm"` | orchestrator (every ~10 s) | Perception Agent |
| `"decision"` | orchestrator (every cycle) | Safety Agent + severity badge |
| `"companion"` | orchestrator (when triggered) | Companion Agent |
| `"intervention"` | orchestrator (when triggered) | Intervention Log |
| `"audit"` | `core/audit.py` writer thread (continuous) | Policy Monitor |

---

## Audit Recorder (`core/audit.py`)

A shared, fire-and-forget helper that all three agents call to record their actions.
Feeds the **Policy Monitor** panel in the frontend — the key judge demo moment.

### Internal architecture

```
record_tool_call()  ─┐
record_api_call()   ─┤── _enqueue(entry) ──▶ _write_queue (bounded, maxsize=500)
record_decision()   ─┘                              │
                                           _writer_loop() [single background thread]
                                                    │
                                       ┌────────────┴────────────┐
                                       ▼                         ▼
                              ./logs/agent_audit.jsonl    api.events.publish("audit", ...)
                                                                  │
                                                          frontend Policy Monitor panel

_tail_nemoclaw_log() [daemon thread, polls ./logs/audit.log every 500 ms]
  → _parse_and_enqueue_nemoclaw_line()
  → _enqueue(AuditEntry(source="nemoclaw", ...))
```

- `_write_queue` is a module-level singleton (`queue.Queue(maxsize=500)`). If full, entries are silently dropped — never raises, never blocks an agent.
- Single writer thread — no file lock contention on the JSONL file.
- NemoClaw tail uses **polling** (not inotify) — zero extra dependencies, handles log rotation by resetting offset when file shrinks.
- `start_audit_recorder()` is idempotent — safe to call multiple times during dev.

### NemoClaw log parsing

`_parse_and_enqueue_nemoclaw_line(line)`:
1. Try JSON parse (structured audit tools emit NDJSON).
2. Fall back to regex for `ALLOW`/`DENY`/`BLOCK` keywords.
3. On parse failure: emit `verdict="info"` entry with `metadata={"raw": line}`.
4. Entire function wrapped in `try/except Exception` — never raises.

Implement the full parser **after** NemoClaw is running and its real log format is known (step 7 in the implementation order below).

### Where each agent calls the recorder

**Caleb — `vision/vlm_analyzer.py`** (2 call sites in `assess_frame()`):
```python
from core.audit import record_api_call, record_decision

# after API response received:
record_api_call("perception", endpoint, model, prompt_tokens, completion_tokens, driver_id, shift_id)

# after VLMFrameAssessment constructed:
record_decision("perception", f"VLMFrameAssessment: fatigue_score={assessment.fatigue_score:.2f}, flags={assessment.flags}",
                {"fatigue_score": assessment.fatigue_score, "flags": assessment.flags, "confidence": assessment.confidence},
                driver_id, shift_id)
```

**Kevin — `agents/tools.py`** (1 call site per `handle_*` function, 7 total):
```python
from core.audit import record_tool_call

# at the end of each handle_* function, after tool executes:
record_tool_call("safety", tool_name, args_dict, result_dict, driver_id, shift_id)
```

**Kevin — `agents/safety.py`** (2 call sites):
```python
from core.audit import record_api_call, record_decision

# after each complete_with_tools() call in ReAct loop:
record_api_call("safety", endpoint, model, prompt_tokens, completion_tokens, driver_id, shift_id)

# after final InterventionDecision produced:
record_decision("safety", f"InterventionDecision: severity={decision.severity}, type={decision.intervention_type}",
                {"severity": decision.severity, "intervention_type": decision.intervention_type,
                 "should_intervene": decision.should_intervene, "confidence": decision.confidence},
                driver_id, shift_id)
```

**Emilio — `agents/companion.py`** (2 call sites in `generate()`):
```python
from core.audit import record_api_call, record_decision

# after complete() returns:
record_api_call("companion", endpoint, model, prompt_tokens, completion_tokens, driver_id, shift_id)

# after CompanionMessage constructed:
record_decision("companion", f"CompanionMessage: trigger={msg.trigger_reason}, severity={msg.severity_context}",
                {"trigger_reason": msg.trigger_reason, "severity_context": msg.severity_context,
                 "message_preview": msg.message[:80]},
                driver_id, shift_id)
```

### Frontend — Policy Monitor (Panel 7)

Panel 7 spans the full dashboard width (3 columns) at the bottom. Entries are
prepended (newest at top), capped at 200 DOM nodes.

**`frontend/index.html`** — add after Panel 6 inside `<main>`:
```html
<section id="policy-monitor">
  <h2>Policy Monitor <span class="model-tag">NemoClaw</span></h2>
  <div id="audit-filter">
    <button class="audit-filter-btn active" data-filter="all">All</button>
    <button class="audit-filter-btn" data-filter="nemoclaw">NemoClaw</button>
    <button class="audit-filter-btn" data-filter="safety">Safety Agent</button>
    <button class="audit-filter-btn" data-filter="perception">Perception</button>
    <button class="audit-filter-btn" data-filter="companion">Companion</button>
  </div>
  <ul id="audit-list"></ul>
</section>
```

**`frontend/app.js`** — add to switch + implement handlers:
```javascript
case "audit": appendAuditEntry(event.data); break;

function appendAuditEntry(data) {
  // data: AuditEntry fields as JSON
  // prepend <li> with: timestamp | source badge | action_type | description | verdict badge
  // li.dataset.source = data.source  ← used by filter buttons
  // cap list at 200 items
  // call applyAuditFilter() after insert
}

function applyAuditFilter() {
  const active = document.querySelector(".audit-filter-btn.active").dataset.filter;
  document.querySelectorAll("#audit-list li").forEach(li => {
    li.style.display = (active === "all" || li.dataset.source === active) ? "" : "none";
  });
}
// wire filter buttons + call initAuditFilter() at bottom of file
```

**`frontend/styles.css`** — add:
- `#policy-monitor { grid-column: 1 / -1; }` — full-width bottom strip
- `#audit-list` — monospace font, 180px max-height, scroll
- `.audit-allowed` — green left border (`#76b900`)
- `.audit-blocked` — red left border (`#e04040`)
- `.audit-info` — grey left border (`#555`)
- `.audit-source-perception/safety/companion/nemoclaw` — per-agent color badges
- `.verdict-allowed/blocked/info` — matching verdict badge colors
- `.audit-filter-btn` / `.active` — filter button styles

### Demo moment for judges

1. Point at the Policy Monitor — live color-coded stream running during the demo
2. Filter to **NemoClaw** → show green ALLOWED entries (Nemotron API, ntfy, Nominatim) and a red BLOCKED entry (add a fake fleet-server tool call to prove it)
3. Filter to **Safety Agent** → show the full ReAct tool call sequence: `check_baseline → get_shift_trend → trigger_rest_break`
4. Show `./logs/audit.log` in terminal — raw NemoClaw policy log
5. Show `./logs/agent_audit.jsonl` — structured agent audit trail for post-demo review

---

## Implementation Order

Build in this sequence to unblock parallel work as fast as possible.

### Step 1 — Kevin: `AuditEntry` in `core/models.py`
Add the dataclass at the end of the file. Team reviews. Freeze.
**Everyone else is unblocked for audit integration after this.**

### Step 2 — Kevin: `core/audit.py` skeleton
Implement the queue, writer thread, JSONL write, and `api.events.publish("audit", ...)`.
The NemoClaw tail thread can be a `pass` loop at first — fill it in at step 7.
Smoke-test:
```bash
python -c "
from core.audit import start_audit_recorder, record_decision
start_audit_recorder()
record_decision('safety', 'test', {}, 'd1', 's1')
import time; time.sleep(0.2)
" && cat ./logs/agent_audit.jsonl
```

### Step 3 — Josh (parallel with step 2): Frontend Panel 7
Add `<section id="policy-monitor">` to `index.html`, styles to `styles.css`,
and `appendAuditEntry()` + filter logic to `app.js`.
Test independently by publishing a fake audit event from a Python shell:
```python
from api.events import publish
publish("audit", {"source": "safety", "action_type": "tool_call",
                  "description": "trigger_alert(severity=high)", "verdict": "allowed",
                  "timestamp": 1234567890, "metadata": {}})
```

### Step 4 — Kevin: integrate into `agents/safety.py` + `agents/tools.py`
Highest demo value — tool calls are the most visually interesting events.
Add `record_tool_call` to all 7 `handle_*` functions in `tools.py`.
Add `record_api_call` + `record_decision` in `safety.py`.

### Step 5 — Caleb: integrate into `vision/vlm_analyzer.py`
Two call sites at the end of `assess_frame()`.

### Step 6 — Emilio: integrate into `agents/companion.py`
Two call sites inside `generate()`.

### Step 7 — Kevin: implement `_tail_nemoclaw_log()` fully
Do this last — run the system end-to-end first, observe the actual NemoClaw log
format, then calibrate `_parse_and_enqueue_nemoclaw_line()` to match it.
The demo works without this step; agent-level entries already populate the panel.

### Step 8 — Kevin: `start_audit_recorder()` in `main.py`
One line before `run_pipeline()`. Activates the tail thread and writer loop.

---

## Conventions

**Branches:** `feat/<name>/<description>` — e.g. `feat/emilio/companion-prompts`

**Commits:** imperative mood, ≤ 72 chars

**Secrets:** `.env` only (gitignored). `.env.example` has placeholder keys.

**Config:** all tuneable values in `config/settings.py` or `config/defaults.yaml`.

**Imports:** absolute only — `from core.models import FrameAnalysis`

**No `print()`:** use `logging.info(...)` so log level is controllable.

**`llm/client.py`:** Kevin owns; Emilio imports only. Ask before adding parameters.

---

## Open Questions / TBD

- **OpenClaw SDK:** exact package name and session API — Kevin confirms at hackathon start.
- **Nemotron-nano-omi endpoint:** confirm model ID and whether it accepts base64 JPEG
  in the same `integrate.api.nvidia.com/v1` endpoint or a separate one.
- **VLM frame rate:** if `assess_frame()` latency > 10 s, increase VLM cadence or
  run it on every Nth pipeline cycle.
- **Location for rest_finder:** hackathon demo uses a hardcoded city as location proxy
  (no GPS on laptop). Set `DEMO_LOCATION_LAT` / `DEMO_LOCATION_LON` in `.env`.
- **ntfy topic:** use ntfy.sh public server with a random topic string (treated like
  a password). Set `NTFY_TOPIC` in `.env`.
- **On-device alert:** for demo, OS notification + terminal bell. Decide day-of.
- **Baseline cold-start:** placeholder values in `config/defaults.yaml` for new drivers.
- **NemoClaw install:** `curl -fsSL https://nvidia.com/nemoclaw.sh | bash` — confirm
  on event Wi-Fi before relying on it.
