# SafeShift — Architecture Reference

> Read this before touching any code. It is the shared contract that lets three people
> build in parallel without merge conflicts.

---

## Project Summary

SafeShift is a privacy-first, driver-only safety agent. It monitors the driver
continuously through a camera, extracts behavioral signals (eye droopiness, blink rate,
yawn frequency, gaze direction), and reasons across the full shift against a per-driver
baseline held in local persistent memory. When it detects fatigue or impairment it
intervenes directly with the driver — an immediate on-device alert, a rest-break
recommendation, and/or a push notification to the driver's own phone — with no data
ever leaving the device to a fleet operator, employer, or third party. The system is a
closed loop between the hardware and the driver: the driver is both the subject and the
sole recipient of every signal it produces.

**Design principle:** All personal biometric data stays on-device. Notifications go only
to the driver. No employer dashboard, no fleet telemetry, no cloud storage of session
data. A driver using SafeShift should feel like it is working *for* them, not
monitoring them on behalf of someone else.

**Target hardware:** A dedicated dash-cam-adjacent device (camera + compute + small
display or speaker) that runs the pipeline and pushes alerts to the driver's phone via a
self-hosted notification service (ntfy.sh or equivalent). For the hackathon demo the
laptop camera stands in for the hardware and phone notifications are delivered via ntfy.

**Hackathon goal:** A running agent — on a laptop, using the webcam — that detects a
fatigue event, makes an autonomous intervention decision via Nemotron reasoning, delivers
a notification to the driver's phone via ntfy, and updates the local per-driver baseline
memory, all within one demonstrable end-to-end loop.

---

## Data Flow

```
main.py  ← generates shift_id + shift_start; drives loop; calls end_shift() on exit
        │
        ▼
Camera / RTSP stream
        │
        ▼
 vision/capture.py          ← yields raw BGR frames
        │
        ▼
 vision/preprocess.py       ← resize, normalize, crop to face ROI
        │
        ▼
 vision/landmarks.py        ← MediaPipe FaceMesh → landmark coordinates
        │
        ▼
 vision/features.py         ← blink rate, eye openness, yawn freq, gaze
        │
        ▼
 vision/pipeline.py         ← aggregates N-frame window → FrameAnalysis
        │
        ▼
 agent/context_builder.py   ← FrameAnalysis + memory layer + ShiftTrend → ShiftContext
        │
        ▼
 reasoning/nemotron.py      ← ShiftContext rendered via prompts.py → Nemotron
        │
        ▼
 reasoning/decision.py      ← parse completion → InterventionDecision
        │
        ▼
 agent/orchestrator.py      ← dispatch via OpenClaw tools; always logs via logging_service
   ┌────┴────┬──────────────┐
   ▼         ▼              ▼
alert.py  rest_break.py  phone_notify.py   ← each returns InterventionRecord
   │         │              │
   └────┬────┴──────────────┘
        │
        ▼
 orchestrator.py calls append_intervention(record)
        │
        ├──▶ integrations/alerting.py       ← on-device audio/visual
        ├──▶ integrations/notify.py         ← driver's phone (ntfy); driver-only
        └──▶ integrations/logging_service.py  ← always-on, every cycle; local only
                │
                ▼
 memory/shift_history.py    ← write InterventionRecord  [stays on-device]
 memory/driver_baseline.py  ← update baseline at shift end (end_shift only)
```

---

## Module Breakdown

### `main.py`
Owned by Kevin. The process entry point. Reads `driver_id` from config/env, generates
`shift_id` (uuid4) and `shift_start` timestamp, then calls `start_shift()` to initialize
memory for the session. Starts `vision/pipeline.run_pipeline()` and feeds each
`FrameAnalysis` into the `agent/orchestrator` loop. On exit it calls `end_shift()`,
which triggers the `DriverBaseline` update. Nothing else should import from main.py.

### `config/`
Loads `.env` via `python-dotenv` and exposes a typed `Settings` object. Also holds
`defaults.yaml` — the starting thresholds (e.g. eye openness below 0.25 = droopy) used
before a driver has accumulated shift history. Anything that is "a number that might
change" lives here, not hardcoded.

### `vision/`
Owned entirely by Caleb. Responsible for everything up to and including producing a
`FrameAnalysis` object every N seconds. Has no knowledge of agents, memory, or
interventions. The output contract is `FrameAnalysis` (see below) — Kevin and Emilio
code against that type, not against any vision internals.

### `memory/`
Owned by Emilio. Thin read/write layer over SQLite (stdlib `sqlite3`; local file only —
no remote database, no cloud sync). Two concerns: `DriverBaseline` (persists across
shifts, updated at shift end) and shift history (`FrameAnalysis` snapshots +
`InterventionRecord`s for the current shift). Exposes simple `get_baseline(driver_id)`,
`save_baseline(baseline)`, `append_frame(shift_id, frame)`, `append_intervention(record)`
functions — no ORM. The database file path is set in `.env` (default: `./safeshift.db`)
and stays on the driver's device.

### `agent/`
Owned by Kevin. `orchestrator.py` is the per-cycle loop: pull `FrameAnalysis`, call
`context_builder.py` to assemble `ShiftContext` (including `ShiftTrend` from full shift
history), invoke Nemotron reasoning, receive `InterventionDecision`, dispatch the correct
handler (alert / rest_break / phone_notify) via an OpenClaw tool call, take the returned
`InterventionRecord`, and call `memory.shift_history.append_intervention(record)`.
`orchestrator.py` also calls `integrations/logging_service` every cycle regardless of
`should_intervene`. `tools.py` declares the OpenClaw tool schema; each tool wraps one
`interventions/<type>.execute()` call — tools.py owns the OpenClaw binding, the handler
owns the execution logic. `context_builder.py` is the only module that reads from both
vision output and the memory layer simultaneously.

### `reasoning/`
Owned by Kevin. `nemotron.py` wraps the NVIDIA Nemotron API (OpenAI-compatible
endpoint). `prompts.py` renders a `ShiftContext` into the system + user prompt that asks
Nemotron to return structured JSON. `decision.py` validates and parses that JSON into an
`InterventionDecision`. The prompt format and JSON schema are defined here and nowhere
else.

### `interventions/`
Owned by Emilio. **`models.py` is the critical-path file — finalize and commit it first,
before any other module is implemented, because every other module imports from it.**
Each handler (`alert.py`, `rest_break.py`, `phone_notify.py`) receives an
`InterventionDecision`, calls the appropriate integration client, and returns an
`InterventionRecord`. Handlers are deliberately thin — no business logic, just routing.

Escalation model: `intervention_type` is a single action per cycle. Graduated escalation
(alert → rest_break → phone_notify) happens across loop cycles using
`severity_escalation_minutes` from `config/defaults.yaml`. Session logging is always-on
(called every cycle by orchestrator.py) and is NOT an `intervention_type` value.

All interventions target the driver directly. No data is sent to any fleet operator,
employer, or external service.

### `integrations/`
Owned by Emilio. Thin HTTP clients for: in-cab alert (`alerting.py`), driver phone
notification via ntfy (`notify.py`), and local session logging (`logging_service.py`).
Each client exposes one or two functions with typed signatures. The ntfy topic and server
URL come from `config/settings.py` (set per-driver in `.env`). No fleet or employer
endpoints exist here.

### `tests/`
Shared. `conftest.py` provides sample instances of every dataclass so any test file can
`from conftest import sample_frame_analysis` without re-building fixtures. Unit tests
mock external calls (camera, Nemotron API, alert endpoint). Write tests as you go, not
at the end.

### `deployment/`
Owned by Josh. `Dockerfile` + `docker-compose.yml` for local dev. `brev.yaml` declares
the GPU instance config for NVIDIA Brev; `setup_brev.sh` bootstraps the environment.

---

## Interface Contracts

All types are defined in [`interventions/models.py`](interventions/models.py).
Import from there — never redefine these types locally.

> **Critical path:** `interventions/models.py` must be finalized and committed before
> anyone else writes a function signature. Josh owns it; if you need a field change,
> coordinate before building against it.

### `FrameAnalysis`
Produced by `vision/pipeline.py` once per analysis window (default 2 s).

```python
@dataclass
class FrameAnalysis:
    timestamp: float           # unix epoch
    driver_id: str
    blink_rate: float          # blinks/min in rolling window
    eye_openness: float        # 0.0 (fully closed) → 1.0 (fully open)
    yawn_detected: bool        # any yawn event in this window
    yawn_frequency: float      # yawns/hour rolling estimate
    gaze_direction: str        # "forward"|"left"|"right"|"down"|"up"
    gaze_deviation_deg: float  # degrees off center
    confidence: float          # overall detection confidence 0.0–1.0
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
Computed by `agent/context_builder.py` from full shift history in memory; gives Nemotron
a shift-level degradation signal rather than just a recent snapshot vs. static baseline.

```python
@dataclass
class ShiftTrend:
    shift_id: str
    sample_count: int              # FrameAnalysis samples aggregated
    avg_eye_openness_trend: list   # list[float] — mean eye_openness per time bucket
    avg_blink_rate_trend: list     # list[float] — mean blink_rate per bucket
    yawn_count_total: int          # cumulative yawn events this shift
    intervention_count: int        # total interventions fired this shift
    trend_bucket_minutes: float    # duration each bucket represents (e.g. 5.0)
```

### `ShiftContext`
Assembled by `agent/context_builder.py`; passed to `reasoning/nemotron.py`.

```python
@dataclass
class ShiftContext:
    driver_id: str
    shift_id: str              # uuid4, generated at shift start
    shift_elapsed_minutes: float
    current_analysis: FrameAnalysis
    recent_window: list        # list[FrameAnalysis] — last N minutes
    shift_trend: ShiftTrend    # full-shift trajectory for degradation detection
    baseline: DriverBaseline
    prior_interventions: list  # list[InterventionRecord] — this shift only
```

### `InterventionDecision`
Returned by `reasoning/decision.py` after parsing Nemotron JSON output.

`intervention_type` is a **single value per cycle** — graduated escalation happens
across cycles, not within one decision. Session logging is always-on and is not
represented here; `orchestrator.py` calls `integrations/logging_service` every cycle
independent of `should_intervene`. All interventions are driver-addressed only.

```python
@dataclass
class InterventionDecision:
    should_intervene: bool
    severity: str              # "none"|"low"|"medium"|"high"|"critical"
    intervention_type: str     # "none"|"alert"|"rest_break"|"phone_notify"
    reason: str                # human-readable explanation from model
    confidence: float          # 0.0–1.0
    timestamp: float           # unix epoch
```

### `InterventionRecord`
Written to `memory/shift_history.py` immediately after a handler executes.

```python
@dataclass
class InterventionRecord:
    intervention_id: str       # uuid4
    driver_id: str
    shift_id: str
    timestamp: float           # unix epoch
    severity: str              # mirrors InterventionDecision.severity
    intervention_type: str     # mirrors InterventionDecision.intervention_type
    action_summary: str        # brief description of what was actually done
```

---

## Ownership Split

Build order priority: **Emilio → models.py first** (everyone else blocks on it),
then Caleb and Kevin can build in parallel immediately.

| Module | Owner | Key output | Build priority |
|--------|-------|-----------|----------------|
| `interventions/models.py` | **Emilio** | **critical-path** — all shared dataclasses | **Do first** |
| `config/` | Emilio | `Settings` object; threshold constants | Day 1 |
| `memory/` | Emilio | `DriverBaseline` + local shift history | Day 1 |
| `interventions/` (handlers) | Emilio | alert / rest_break / phone_notify execution | Day 1 |
| `integrations/` | Emilio | alerting + ntfy notify + local logging clients | Day 1 |
| `vision/capture.py` + `preprocess.py` | Caleb | raw frames from laptop cam | Day 1 |
| `vision/landmarks.py` | Caleb | MediaPipe landmark coords per frame | Day 1 |
| `vision/features.py` | Caleb | blink rate, eye openness, yawn, gaze | Day 1 |
| `vision/pipeline.py` | Caleb | `FrameAnalysis` iterator | Day 1 |
| `main.py` | Kevin | shift lifecycle: shift_id, shift_start, end_shift | Day 1 |
| `agent/orchestrator.py` | Kevin | main loop + tool dispatch | Day 1 |
| `agent/tools.py` + `context_builder.py` | Kevin | OpenClaw tools; `ShiftContext` assembly | Day 1 |
| `reasoning/` | Kevin | Nemotron client + prompts + `InterventionDecision` | Day 1 |
| `deployment/` | Josh | Docker, Brev, hardware setup | Later |
| `tests/` | Josh | full test suite with shared fixtures | Later |

**Rule:** you may read any module's public types but do not import from a sibling's
_internal_ helpers. Cross-module communication happens only through the dataclasses
above and the function signatures below.

### Key cross-module function signatures

```python
# main.py
def start_shift(driver_id: str) -> tuple[str, float]: ...
    # returns (shift_id: uuid4 str, shift_start: unix epoch float)
def end_shift(shift_id: str, driver_id: str) -> None: ...
    # triggers memory/driver_baseline.save_baseline() with updated rolling averages

# vision/pipeline.py
def run_pipeline(driver_id: str) -> Iterator[FrameAnalysis]: ...

# memory/driver_baseline.py
def get_baseline(driver_id: str) -> DriverBaseline: ...
def save_baseline(baseline: DriverBaseline) -> None: ...

# memory/shift_history.py
def append_frame(shift_id: str, frame: FrameAnalysis) -> None: ...
def append_intervention(record: InterventionRecord) -> None: ...
def get_recent_frames(shift_id: str, minutes: int) -> list[FrameAnalysis]: ...
def get_all_frames(shift_id: str) -> list[FrameAnalysis]: ...   # used by context_builder for ShiftTrend
def get_interventions(shift_id: str) -> list[InterventionRecord]: ...

# agent/context_builder.py
def build_context(frame: FrameAnalysis, shift_id: str, shift_start: float) -> ShiftContext: ...
    # internally calls get_recent_frames + get_all_frames to compute ShiftTrend

# reasoning/nemotron.py
def analyze(context: ShiftContext) -> InterventionDecision: ...

# agent/tools.py  →  interventions/ seam
# Each OpenClaw tool in tools.py wraps one handler call:
#   tools.py declares the tool schema; the tool body calls interventions/<type>.execute()
#   orchestrator.py takes the returned InterventionRecord and calls append_intervention()

# interventions/alert.py  (and rest_break.py, phone_notify.py — same signature)
def execute(decision: InterventionDecision, driver_id: str) -> InterventionRecord: ...
```

---

## Conventions

**Branches:** `feat/<your-name>/<short-description>` — e.g. `feat/emilio/vision-pipeline`

**Commits:** imperative mood, ≤ 72 chars — e.g. `add eye openness feature extraction`

**Secrets:** all secrets in `.env` (gitignored). `.env.example` holds the keys with
placeholder values. Never hardcode keys or URLs.

**Config:** all tuneable numbers (thresholds, window sizes, API URLs) go in
`config/settings.py` or `config/defaults.yaml`, not inline.

**Imports:** use absolute imports (`from interventions.models import FrameAnalysis`),
not relative.

**No `print()`:** use Python `logging` (e.g. `logging.info(...)`) so log level is
controllable from config.

---

## Open Questions / TBD

- **OpenClaw SDK:** exact package name, import path, and tool-registration API — Kevin
  to confirm at hackathon start.
- **Nemotron endpoint:** confirm base URL and model ID for the reasoning/vision model
  (currently `https://integrate.api.nvidia.com/v1`).
- **NVIDIA Brev:** instance type availability and whether camera passthrough is possible
  on cloud GPU (may need to run vision locally and push `FrameAnalysis` objects to Brev
  over a queue/websocket).
- **Phone notification channel:** ntfy.sh is the current plan (self-hosted or public
  server). Confirm: do we use ntfy.sh public server for the demo (convenient) or run a
  local ntfy instance (fully private)? ntfy topic should be treated like a password.
- **On-device alert form factor:** for the laptop demo, does the alert surface as a
  sound, a terminal bell, an OS notification, or a GUI widget? Decide day-of based on
  what's easiest to demo visually.
- **Data retention policy:** decide whether shift history is purged after N days or kept
  indefinitely; default to indefinite for the hackathon. This only affects `memory/store.py`.
- **Storage backend:** SQLite is fine for the hackathon demo; if concurrent writes become
  an issue, swap `memory/store.py` implementation without touching callers.
- **Baseline cold-start:** what defaults to use for a first-time driver with no history.
  Placeholder values in `config/defaults.yaml`; decide real numbers day-of.
- **Frame window size:** 2 s hardcoded in `.env.example`; tune based on camera FPS and
  latency observed during testing.
- **Driver identity at shift start:** how is `driver_id` provided to `main.py` — CLI
  argument, env var, or hardcoded for the demo? Determines whether `start_shift()` can
  look up an existing baseline or always cold-starts.
