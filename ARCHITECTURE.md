# SafeShift — Architecture Reference

> Read this before touching any code. It is the shared contract that lets three people
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
NemoClaw policy control.

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
 agent/context_builder.py   ← FrameAnalysis + VLMFrameAssessment + memory → ShiftContext
                  │
                  ▼
 ┌────────────────────────────────────────────────────────┐
 │          SAFETY REASONING AGENT  (Nemotron-Super)      │
 │  reasoning/nemotron.py + prompts.py                    │
 │  ReAct loop: Reason → Act → Observe                    │
 │  assess shift trend → decide intervention + companion  │
 └──────────────────────┬─────────────────────────────────┘
                        │  InterventionDecision
         ┌──────────────┴──────────────────┐
         │ trigger_companion=True          │ should_intervene=True
         ▼                                 ▼
 ┌───────────────────┐         agent/orchestrator.py
 │  COMPANION AGENT  │         dispatch via OpenClaw tools
 │  agent/companion  │    ┌────┴─────┬──────────────┐
 │  (Nemotron-Super) │    ▼          ▼               ▼
 │  → CompanionMsg   │  alert.py  rest_break.py  phone_notify.py
 └────────┬──────────┘    │       + rest_finder        │
          │               │     (Nominatim lookup)      │
          └──────┬─────── ┴───────────────┬─────────────┘
                 │                        │  InterventionRecord
                 ▼                        ▼
          display / TTS        integrations/{alerting, notify, logging_service}
                                          │
                                          ▼
                             memory/shift_history.py    ← stays on-device
                             memory/driver_baseline.py  ← updated at end_shift
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
Owned entirely by Caleb. Two parallel outputs per cycle:
- `pipeline.py` — MediaPipe landmark chain (capture → preprocess → landmarks → features)
  producing a `FrameAnalysis` every ~2 s. Fast; runs every cycle.
- `vlm_analyzer.py` — Sends a raw frame to the **Nemotron-3-Nano-Omi VLM** and returns a
  `VLMFrameAssessment` with a natural-language fatigue description, score, and flags.
  Slower; runs every ~10 s to manage inference cost.

Neither sub-module knows about agents, memory, or interventions. Kevin and Emilio code
against `FrameAnalysis` and `VLMFrameAssessment` only.

### `memory/`
Owned by Emilio. Thin read/write layer over SQLite (stdlib `sqlite3`; local file only —
no remote database, no cloud sync). Two concerns: `DriverBaseline` (persists across
shifts, updated at shift end) and shift history (`FrameAnalysis` snapshots +
`InterventionRecord`s for the current shift). Exposes simple `get_baseline(driver_id)`,
`save_baseline(baseline)`, `append_frame(shift_id, frame)`, `append_intervention(record)`
functions — no ORM. The database file path is set in `.env` (default: `./safeshift.db`)
and stays on the driver's device.

### `agent/`
Owned by Kevin. Four files:

- `subagents.py` — declares the three agent roles and their model assignments
  (Perception: Nano-Omi, Safety Reasoning: Nemotron-Super, Companion: Nemotron-Super).
  Model IDs come from `config/settings.py`.
- `context_builder.py` — merges `FrameAnalysis`, the latest `VLMFrameAssessment`, and
  memory layer data into a `ShiftContext`. Only place that touches both vision and memory.
- `orchestrator.py` — per-cycle loop: build context → invoke Safety Reasoning Agent
  (ReAct: Reason → Act → Observe) → receive `InterventionDecision` → if
  `trigger_companion` dispatch Companion Agent → dispatch intervention handler via
  OpenClaw tool → write `InterventionRecord` to memory → always log via
  `integrations/logging_service`.
- `tools.py` — OpenClaw tool schema declarations; each tool wraps one
  `interventions/<type>.execute()` or `companion.generate()` call.
- `companion.py` — Companion Agent: given `ShiftContext` and prior `CompanionMessage`s,
  generates a proactive, non-repetitive message to keep the driver engaged.

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
Owned by Emilio. Four thin clients:
- `alerting.py` — on-device audio/visual alert
- `notify.py` — driver phone push via ntfy (topic + server from `config/settings.py`)
- `rest_finder.py` — queries Nominatim/OpenStreetMap for nearby rest areas given
  approximate location; no API key required, no personal data retained by Nominatim
- `logging_service.py` — local-only session logger; called every cycle

No fleet or employer endpoints exist in this directory.

### `tests/`
Shared. `conftest.py` provides sample instances of every dataclass so any test file can
`from conftest import sample_frame_analysis` without re-building fixtures. Unit tests
mock external calls (camera, Nemotron API, alert endpoint). Write tests as you go, not
at the end.

### `nemoclaw-policy.yaml`
Root-level NemoClaw access policy. Defines exactly what the agent is and is not allowed
to access: camera device, local SQLite, Nemotron inference endpoint, ntfy, and Nominatim.
Denies all other outbound network and file-system access. Running SafeShift under
NemoClaw means the agent *cannot* contact an employer endpoint even if it tried — the
policy is enforced by the runtime, not just the code. This is both a privacy guarantee
and a demo moment: show a judge the blocked request log.

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

### `VLMFrameAssessment`
Produced by `vision/vlm_analyzer.py` via Nemotron-3-Nano-Omi on a ~10 s cadence.
Provides semantic scene understanding beyond landmark metrics.

```python
@dataclass
class VLMFrameAssessment:
    timestamp: float
    driver_id: str
    fatigue_score: float       # 0.0 (fully alert) → 1.0 (severely fatigued)
    description: str           # natural language, e.g. "driver's head drooping, eyes half-closed"
    flags: list                # list[str] — e.g. ["eyes_drooping", "head_tilt", "yawning"]
    confidence: float
```

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
    shift_trend: ShiftTrend    # full-shift trajectory for degradation detection
    baseline: DriverBaseline
    recent_window: list = field(default_factory=list)        # list[FrameAnalysis] — last N minutes
    prior_interventions: list = field(default_factory=list)  # list[InterventionRecord] — this shift
    vlm_assessment: Optional[VLMFrameAssessment] = None      # latest VLM result; None until first cycle
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
    trigger_companion: bool    # True → companion agent also fires this cycle
    reason: str                # human-readable explanation from Nemotron
    confidence: float          # 0.0–1.0
    timestamp: float           # unix epoch
```

### `CompanionMessage`
Generated by `agent/companion.py` when `trigger_companion=True`; displayed or read aloud.

```python
@dataclass
class CompanionMessage:
    timestamp: float
    driver_id: str
    message: str               # what the companion says
    trigger_reason: str        # "fatigue_building"|"long_silence"|"pre_intervention"
    severity_context: str      # severity level that triggered this turn
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
| `config/` | Emilio | `Settings` + threshold constants | Day 1 |
| `memory/` | Emilio | `DriverBaseline` + local shift history | Day 1 |
| `interventions/` (handlers) | Emilio | alert / rest_break / phone_notify execution | Day 1 |
| `integrations/` (all 4 clients) | Emilio | alerting, ntfy, rest_finder, logging | Day 1 |
| `vision/capture.py` + `preprocess.py` | Caleb | raw BGR frames from webcam | Day 1 |
| `vision/landmarks.py` | Caleb | MediaPipe landmark coords per frame | Day 1 |
| `vision/features.py` | Caleb | blink rate, eye openness, yawn, gaze | Day 1 |
| `vision/pipeline.py` | Caleb | `FrameAnalysis` iterator | Day 1 |
| `vision/vlm_analyzer.py` | Caleb | `VLMFrameAssessment` via Nemotron-3-Nano-Omi | Day 1 |
| `main.py` | Kevin | shift lifecycle (shift_id, start/end) | Day 1 |
| `agent/subagents.py` | Kevin | agent role + model config declarations | Day 1 |
| `agent/context_builder.py` | Kevin | `ShiftContext` (merges vision + memory) | Day 1 |
| `agent/orchestrator.py` | Kevin | ReAct loop + OpenClaw tool dispatch | Day 1 |
| `agent/companion.py` | Kevin | `CompanionMessage` generation | Day 1 |
| `agent/tools.py` | Kevin | OpenClaw tool schema | Day 1 |
| `reasoning/` | Kevin | Nemotron-Super client + prompts + `InterventionDecision` | Day 1 |
| `nemoclaw-policy.yaml` | Kevin | access policy (confirm syntax w/ NemoClaw docs) | Day 1 |
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

# vision/vlm_analyzer.py
def analyze_frame(frame_bgr, driver_id: str) -> VLMFrameAssessment: ...
    # sends frame to Nemotron-3-Nano-Omi; called every ~10 s by pipeline.py

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
def build_context(
    frame: FrameAnalysis,
    shift_id: str,
    shift_start: float,
    vlm: Optional[VLMFrameAssessment] = None,
) -> ShiftContext: ...
    # internally calls get_recent_frames + get_all_frames to compute ShiftTrend

# reasoning/nemotron.py  — Safety Reasoning Agent (Nemotron-Super, ReAct loop)
def analyze(context: ShiftContext) -> InterventionDecision: ...

# agent/companion.py  — Companion Agent (Nemotron-Super)
def generate(context: ShiftContext, prior_messages: list[CompanionMessage]) -> CompanionMessage: ...

# integrations/rest_finder.py
def find_nearby_stops(lat: float, lon: float, radius_m: int = 5000) -> list[str]: ...
    # returns list of stop name + distance strings via Nominatim

# agent/tools.py  →  interventions/ seam
# Each OpenClaw tool wraps one handler: tools.py owns the schema, handler owns the logic.
# orchestrator.py writes the returned InterventionRecord to memory.

# interventions/alert.py  (rest_break.py and phone_notify.py — same signature)
def execute(decision: InterventionDecision, driver_id: str) -> InterventionRecord: ...
    # rest_break.py also calls integrations/rest_finder to populate record.suggested_stops
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
  to confirm at hackathon start. Also confirm NemoClaw policy YAML field names match
  the spec at github.com/NVIDIA/NemoClaw.
- **Nemotron model IDs:** confirm exact model IDs for (a) Nano-Omi VLM and (b)
  Nemotron-Super reasoning. Current best guesses: `nemotron-3-nano-omi` and
  `llama-3_3-nemotron-super-49b-v1_5`. Check build.nvidia.com/models on the day.
- **VLM cadence vs. latency:** 10 s between VLM calls is a guess — calibrate against
  actual inference time on Brev to find the fastest safe interval.
- **Companion output channel:** does the CompanionMessage display as text on-screen,
  get read aloud via TTS (e.g. pyttsx3), or both? TTS is more demo-able; decide day-of.
- **Rest-stop location source:** Nominatim requires an approximate lat/lon — how does
  the demo get that? Options: hardcode a demo location, ask the driver at shift start,
  or use IP geolocation (rough but no hardware needed).
- **Driver identity at shift start:** CLI arg, env var, or hardcoded for demo? Determines
  whether `start_shift()` finds an existing baseline or cold-starts from `defaults.yaml`.
- **ntfy server:** public ntfy.sh (easy for demo) vs. self-hosted (fully private). Either
  works — treat the topic string as a password.
- **On-device alert form:** OS notification, terminal bell, or GUI widget — pick whatever
  demos most visibly on a laptop screen in 3 minutes.
- **Future extension — pilot mode:** same fatigue signals apply to aviation; the only
  changes would be camera placement, baseline profiles, and intervention thresholds.
  Architecture supports it with no structural changes.
