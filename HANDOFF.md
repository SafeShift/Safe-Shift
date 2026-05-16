# SafeShift — Agent Handoff / Context Dump

> Paste this entire document at the start of a new agent conversation to get full context.
> Everything below reflects the current state of the codebase as of 2026-05-15.

---

## What This Project Is

**SafeShift** is a privacy-first, multi-agent driver-safety system built for a 24-hour
NVIDIA x UCSC hackathon. It monitors a driver via camera, detects fatigue/distraction
signals in real time, and intervenes directly with the driver — never with an employer
or fleet operator. All biometric data stays on-device. The system is a closed loop
between the hardware and the driver.

**Ethical stance (non-negotiable):** No fleet telemetry. No employer dashboard. No cloud
storage of session data. The driver is both the subject and the sole recipient of every
signal the system produces. This is enforced at the infrastructure level via a NemoClaw
access policy (`nemoclaw-policy.yaml`), not just by convention.

**GitHub repo:** https://github.com/Emilio-portal/Safe-Shift.git
**Stack:** Python, OpenClaw/NemoClaw, NVIDIA Nemotron (Nano-Omi VLM + Super reasoning),
NVIDIA Brev (cloud GPU), MediaPipe (facial landmarks), SQLite (local persistent memory),
ntfy (driver phone notifications), Nominatim/OpenStreetMap (rest-stop lookup).

---

## Hackathon Context

- **Duration:** 24 hours, building starts today
- **Hard requirement:** Must use NVIDIA Nemotron models via build.nvidia.com/models to
  qualify for prizes. Must be a live, running agent — no prototypes, no slide decks.
- **Judging criteria (1–5 each):** Creativity, Functionality, Scope of Completion,
  Presentation, Use of NVIDIA Tools, Use of NVIDIA Nemotron Models.
- **Winning patterns called out by organizers:** Multi-agent systems, ReAct pattern
  workflows, tool-calling applications, multi-modal agents (VLM + reasoning).
- **NemoClaw track:** Separate judging track for teams using NemoClaw (OpenClaw +
  OpenShell policy engine). Show policy logs and blocked requests to demonstrate guardrails.
- **Demo format:** 3 minutes with a judge, then top-5 finals. Must be live and running.

---

## Architecture Overview

Three specialized AI agents, all running under NemoClaw policy control:

| Agent | Model | Role |
|-------|-------|------|
| Perception Agent | Nemotron-3-Nano-Omi (VLM) | Analyzes raw camera frames; returns semantic fatigue description + score |
| Safety Reasoning Agent | Nemotron-Super (llama-3_3-nemotron-super-49b-v1_5) | ReAct loop: reasons over full shift history vs. baseline → InterventionDecision |
| Companion Agent | Nemotron-Super | Proactive conversation when fatigue is building — keeps driver engaged before hard intervention |

### Data Flow (text form)

```
main.py
  → start_shift(driver_id) → (shift_id, shift_start)
  → run vision loop:

  Every 2 s:   vision/pipeline.py → FrameAnalysis       (MediaPipe landmarks)
  Every ~10 s: vision/vlm_analyzer.py → VLMFrameAssessment  (Nemotron-3-Nano-Omi)

  → agent/context_builder.py
      reads: FrameAnalysis + VLMFrameAssessment + memory (recent frames, shift trend, baseline)
      writes: ShiftContext

  → Safety Reasoning Agent (reasoning/nemotron.py, ReAct loop)
      reads: ShiftContext
      writes: InterventionDecision
        .should_intervene: bool
        .severity: "none"|"low"|"medium"|"high"|"critical"
        .intervention_type: "none"|"alert"|"rest_break"|"phone_notify"
        .trigger_companion: bool

  → if trigger_companion:
      Companion Agent (agent/companion.py)
        reads: ShiftContext + prior CompanionMessages
        writes: CompanionMessage → displayed/read aloud to driver

  → if should_intervene:
      agent/orchestrator.py dispatches via OpenClaw tools:
        "alert"       → interventions/alert.py → integrations/alerting.py
        "rest_break"  → interventions/rest_break.py
                         + integrations/rest_finder.py (Nominatim lookup)
                         + integrations/notify.py (ntfy push to driver's phone)
        "phone_notify"→ interventions/phone_notify.py → integrations/notify.py

  → always: integrations/logging_service.py (local only, every cycle)
  → memory/shift_history.append_intervention(InterventionRecord)

  on shift end:
  → end_shift() → memory/driver_baseline.save_baseline() (updates rolling averages)
```

---

## Repository Structure

```
Safe-Shift/
├── main.py                        # entry point — shift lifecycle, drives the loop
├── nemoclaw-policy.yaml           # NemoClaw access policy (enforces privacy at runtime)
├── ARCHITECTURE.md                # full reference doc — read this first
├── requirements.txt
├── .env.example                   # env var template (copy to .env, never commit)
├── config/
│   ├── settings.py                # typed settings + threshold constants
│   └── defaults.yaml              # tunable thresholds (eye openness, blink rate, etc.)
├── vision/
│   ├── capture.py                 # camera ingestion
│   ├── preprocess.py              # resize/normalize frames
│   ├── landmarks.py               # MediaPipe FaceMesh
│   ├── features.py                # blink rate, eye openness, yawn freq, gaze
│   ├── pipeline.py                # orchestrates capture→features→FrameAnalysis
│   └── vlm_analyzer.py            # Nemotron-3-Nano-Omi VLM → VLMFrameAssessment
├── agent/
│   ├── subagents.py               # agent role declarations + model assignments
│   ├── context_builder.py         # assembles ShiftContext from vision + memory
│   ├── orchestrator.py            # main ReAct loop + OpenClaw tool dispatch
│   ├── companion.py               # Companion Agent — generates CompanionMessage
│   └── tools.py                   # OpenClaw tool schema declarations
├── reasoning/
│   ├── nemotron.py                # Nemotron-Super API client
│   ├── prompts.py                 # prompt templates for safety reasoning
│   └── decision.py                # parse Nemotron JSON → InterventionDecision
├── interventions/
│   ├── models.py                  # ALL shared dataclasses — import from here everywhere
│   ├── alert.py                   # in-cab alert handler
│   ├── rest_break.py              # rest-break handler (calls rest_finder for location)
│   └── phone_notify.py            # phone notification handler
├── integrations/
│   ├── alerting.py                # on-device alert client
│   ├── notify.py                  # ntfy push notification client
│   ├── rest_finder.py             # Nominatim/OSM rest-stop lookup
│   └── logging_service.py         # local session logger (always-on)
├── memory/
│   ├── store.py                   # SQLite abstraction layer
│   ├── driver_baseline.py         # per-driver baseline read/write
│   └── shift_history.py           # frame snapshots + intervention records
├── tests/
│   ├── conftest.py                # shared fixtures (sample instances of all dataclasses)
│   └── test_*.py                  # one file per module
└── deployment/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── brev.yaml                  # NVIDIA Brev GPU instance config
    └── setup_brev.sh
```

---

## Interface Contracts

**Critical:** All shared dataclasses live in `interventions/models.py`.
Import from there — never redefine locally.

```python
# --- PERCEPTION OUTPUTS ---

@dataclass
class FrameAnalysis:
    """Fast MediaPipe output, every 2 s."""
    timestamp: float; driver_id: str
    blink_rate: float          # blinks/min
    eye_openness: float        # 0.0–1.0
    yawn_detected: bool
    yawn_frequency: float      # yawns/hour rolling
    gaze_direction: str        # "forward"|"left"|"right"|"down"|"up"
    gaze_deviation_deg: float
    confidence: float

@dataclass
class VLMFrameAssessment:
    """Nemotron-3-Nano-Omi semantic output, every ~10 s."""
    timestamp: float; driver_id: str
    fatigue_score: float       # 0.0 (alert) → 1.0 (severe)
    description: str           # e.g. "eyes half-closed, head drooping left"
    flags: list                # list[str] e.g. ["eyes_drooping", "yawning"]
    confidence: float

# --- MEMORY TYPES ---

@dataclass
class DriverBaseline:
    """Per-driver historical norms, updated after each shift."""
    driver_id: str
    avg_blink_rate: float; avg_eye_openness: float; avg_yawn_frequency: float
    shift_count: int; last_updated: str   # ISO-8601

@dataclass
class ShiftTrend:
    """Full-shift alertness trajectory for degradation detection."""
    shift_id: str
    trend_bucket_minutes: float           # required; from config
    sample_count: int = 0
    yawn_count_total: int = 0
    intervention_count: int = 0
    avg_eye_openness_trend: list = field(default_factory=list)  # list[float] per bucket
    avg_blink_rate_trend: list = field(default_factory=list)    # list[float] per bucket

@dataclass
class InterventionRecord:
    """Written to memory after a handler executes."""
    intervention_id: str       # uuid4
    driver_id: str; shift_id: str; timestamp: float
    severity: str              # "low"|"medium"|"high"|"critical"
    intervention_type: str     # "alert"|"rest_break"|"phone_notify"
    action_summary: str
    suggested_stops: list = field(default_factory=list)   # populated by rest_break

# --- AGENT I/O ---

@dataclass
class ShiftContext:
    """Input to Safety Reasoning Agent and Companion Agent."""
    driver_id: str; shift_id: str; shift_elapsed_minutes: float
    current_analysis: FrameAnalysis
    shift_trend: ShiftTrend
    baseline: DriverBaseline
    recent_window: list = field(default_factory=list)        # list[FrameAnalysis]
    prior_interventions: list = field(default_factory=list)  # list[InterventionRecord]
    vlm_assessment: Optional[VLMFrameAssessment] = None      # None until first VLM cycle

@dataclass
class InterventionDecision:
    """Output of Safety Reasoning Agent (Nemotron-Super, ReAct loop)."""
    should_intervene: bool
    severity: str              # "none"|"low"|"medium"|"high"|"critical"
    intervention_type: str     # "none"|"alert"|"rest_break"|"phone_notify"
    trigger_companion: bool    # True → Companion Agent also fires this cycle
    reason: str                # human-readable explanation
    confidence: float; timestamp: float

@dataclass
class CompanionMessage:
    """Output of Companion Agent; displayed or read aloud to driver."""
    timestamp: float; driver_id: str
    message: str               # what the companion says
    trigger_reason: str        # "fatigue_building"|"long_silence"|"pre_intervention"
    severity_context: str
```

### Key function signatures

```python
# main.py
def start_shift(driver_id: str) -> tuple[str, float]: ...    # (shift_id, shift_start)
def end_shift(shift_id: str, driver_id: str) -> None: ...    # triggers baseline update

# vision/pipeline.py
def run_pipeline(driver_id: str) -> Iterator[FrameAnalysis]: ...

# vision/vlm_analyzer.py
def analyze_frame(frame_bgr, driver_id: str) -> VLMFrameAssessment: ...

# agent/context_builder.py
def build_context(frame, shift_id, shift_start, vlm=None) -> ShiftContext: ...

# reasoning/nemotron.py  (Safety Reasoning Agent)
def analyze(context: ShiftContext) -> InterventionDecision: ...

# agent/companion.py  (Companion Agent)
def generate(context: ShiftContext, prior_messages: list) -> CompanionMessage: ...

# integrations/rest_finder.py
def find_nearby_stops(lat: float, lon: float, radius_m: int = 5000) -> list[str]: ...

# interventions/alert.py  (rest_break.py, phone_notify.py — same signature)
def execute(decision: InterventionDecision, driver_id: str) -> InterventionRecord: ...

# memory/shift_history.py
def append_frame(shift_id, frame) -> None: ...
def append_intervention(record) -> None: ...
def get_recent_frames(shift_id, minutes) -> list[FrameAnalysis]: ...
def get_all_frames(shift_id) -> list[FrameAnalysis]: ...
def get_interventions(shift_id) -> list[InterventionRecord]: ...

# memory/driver_baseline.py
def get_baseline(driver_id) -> DriverBaseline: ...
def save_baseline(baseline) -> None: ...
```

---

## Team Ownership

| Owner | Modules | Status |
|-------|---------|--------|
| **Emilio** | `interventions/models.py` (do first — everyone blocks on it), `config/`, `memory/`, `interventions/` handlers, `integrations/` (all 4 clients) | Skeleton done, needs implementation |
| **Caleb** | All of `vision/` including `vlm_analyzer.py` | Skeleton done, needs implementation |
| **Kevin** | `main.py`, `agent/` (all files), `reasoning/`, `nemoclaw-policy.yaml` | Skeleton done, needs implementation |
| **Josh** (joining later) | `deployment/`, `tests/` | Skeleton done |

**Build order:** Emilio finalizes and commits `interventions/models.py` first. Caleb
and Kevin can then build in parallel immediately — they only import from models.py.

---

## Current State of the Codebase

**Done (skeleton):**
- Every file exists with a one-line docstring describing its responsibility.
- `interventions/models.py` has the full, real dataclass bodies (not stubs) — this is
  the one file that is implementation-ready because it's pure data definitions.
- `nemoclaw-policy.yaml` is a full illustrative policy (confirm exact syntax against
  github.com/NVIDIA/NemoClaw spec).
- `config/defaults.yaml` has real threshold values.
- `config/settings.py` lists every typed constant that needs to be exposed.
- `deployment/` files are structurally complete stubs.

**Not yet implemented (everything else):**
All `.py` files outside of `interventions/models.py` are docstring-only stubs. No
functions, no classes, no imports beyond the module docstring.

---

## Key Design Decisions (and Why)

1. **Privacy-first, driver-only:** Pivoted away from fleet dashboard / employer
   notifications. The driver is the sole recipient of all alerts. NemoClaw policy
   enforces this at runtime — the agent literally cannot POST to an employer endpoint.

2. **Multi-agent (3 agents):** Organizers called this the top winning pattern. Perception
   Agent (VLM) + Safety Reasoning Agent (ReAct) + Companion Agent (proactive convo) maps
   cleanly to the rubric criteria for multi-step reasoning and autonomous action.

3. **Nemotron-3-Nano-Omi for VLM:** Explicitly called out in hackathon slides as ideal
   for "analyze a scene" tasks. Using it for direct frame analysis means Nemotron is
   central to both perception AND reasoning — strong for the Nemotron judging criterion.

4. **Companion Agent:** The most demo-able autonomous behavior. A judge can watch it
   decide to start a conversation and say something context-appropriate in real time.
   Also genuinely useful — keeping a drowsy driver talking is a real safety technique.

5. **Nominatim for rest-stop lookup:** Free, no API key, no data retained by the
   service. Privacy-consistent. Provides a real external tool call for the demo.

6. **ntfy for phone notifications:** Self-hostable push notification service. Driver
   installs the ntfy app, subscribes to their private topic, receives alerts. No
   third-party data broker in the loop.

7. **SQLite for memory:** Stdlib, zero setup, stays local. `memory/store.py` is the
   only file that knows it's SQLite — swap to anything else without touching callers.

8. **Escalation across cycles, not within one decision:** `intervention_type` is a
   single value per cycle (not a list). alert → rest_break → phone_notify escalation
   happens over multiple loop cycles controlled by `severity_escalation_minutes` in
   `config/defaults.yaml`. Session logging is always-on and is NOT an intervention type.

---

## Demo Goal (What Needs to Work in 3 Minutes)

1. Webcam turns on, driver in frame.
2. VLM subagent (Nano-Omi) returns a fatigue description — show it on screen.
3. Safety Reasoning Agent (Nemotron-Super, ReAct loop) processes shift context and
   decides to trigger companion + flag low-severity fatigue.
4. Companion Agent generates a message — displayed or read aloud to driver.
5. On escalation: rest_break handler calls Nominatim, returns nearby stops, sends
   ntfy notification to driver's phone. Phone dings on screen.
6. All actions logged locally. Show SQLite or log output to prove persistence.
7. (Bonus) Show NemoClaw policy log — blocked outbound request to a fake "employer"
   endpoint proves the privacy guarantee is enforced, not just promised.

---

## Open Questions (Confirm at Hackathon Start)

- **OpenClaw SDK:** exact package name + tool registration API — Kevin to confirm.
- **NemoClaw policy YAML syntax:** confirm field names against github.com/NVIDIA/NemoClaw.
- **Nemotron model IDs:** Nano-Omi VLM and Super reasoning — check build.nvidia.com/models.
- **VLM inference latency on Brev:** calibrate ~10 s cadence against real latency.
- **Rest-stop location source:** how to get lat/lon for the demo (hardcode, ask at start,
  or IP geolocation).
- **Companion output channel:** text on screen, TTS (pyttsx3), or both.
- **driver_id at shift start:** CLI arg, env var, or hardcoded for the demo.
- **ntfy:** public ntfy.sh (easy) vs. self-hosted (fully private). Topic = password.

---

## Conventions

- **Branches:** `feat/<your-name>/<feature>` e.g. `feat/caleb/vlm-analyzer`
- **Commits:** imperative, ≤72 chars e.g. `add eye openness feature extraction`
- **Secrets:** `.env` only (gitignored). Never hardcode keys or URLs.
- **All tuneable numbers:** `config/defaults.yaml` or `config/settings.py` only.
- **Imports:** absolute only (`from interventions.models import FrameAnalysis`).
- **No `print()`:** use Python `logging` throughout.
- **Cross-module rule:** import types from `interventions/models.py`; never import
  internal helpers from a sibling module.
