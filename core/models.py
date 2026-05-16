"""Canonical shared dataclasses for SafeShift.

ALL inter-module data exchange uses these types. Every module imports from here.
Nobody redefines these elsewhere.

CRITICAL PATH: Kevin finalizes and commits this file before anyone else writes a
function signature. After that, changes require team coordination — everyone
depends on these types on day one.

Owner: Kevin
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FrameAnalysis:
    """Output of vision/pipeline.py per analysis window (default: 2 s rolling).

    Owner: Caleb (vision/)
    """
    timestamp: float           # unix epoch
    driver_id: str
    blink_rate: float          # blinks/min in rolling window
    eye_openness: float        # 0.0 (fully closed) → 1.0 (fully open), avg over window
    yawn_detected: bool        # yawn event in this window
    yawn_frequency: float      # yawns/hour rolling estimate
    gaze_direction: str        # "forward" | "left" | "right" | "down" | "up"
    gaze_deviation_deg: float  # degrees off-center
    confidence: float          # overall detection confidence 0.0–1.0


@dataclass
class VLMFrameAssessment:
    """Rich fatigue assessment from Nemotron-3-Nano-Omi VLM analysis of a raw camera frame.

    Complements FrameAnalysis (fast MediaPipe metrics) with semantic scene understanding:
    head tilt, micro-expressions, posture, and natural-language description.
    Produced by vision/vlm_analyzer.py on a slower cadence (~10 s) than FrameAnalysis.

    Owner: Caleb (vision/)
    """
    timestamp: float
    driver_id: str
    fatigue_score: float       # 0.0 (fully alert) → 1.0 (severely fatigued)
    description: str           # natural language, e.g. "driver's head drooping left, eyes half-closed"
    flags: list                # list[str] — e.g. ["eyes_drooping", "head_tilt", "yawning"]
    confidence: float          # VLM confidence in the assessment 0.0–1.0


@dataclass
class DriverBaseline:
    """Per-driver historical norms; persisted in memory layer and updated after each shift.

    Owner: Kevin (memory/)
    """
    driver_id: str
    avg_blink_rate: float
    avg_eye_openness: float
    avg_yawn_frequency: float
    shift_count: int
    last_updated: str          # ISO-8601 datetime string


@dataclass
class ShiftTrend:
    """Shift-level alertness trajectory, computed by agents/context_builder.py from full shift history.

    Gives the Safety Reasoning Agent a downsampled view of the entire shift — not just
    the recent window — so it can detect gradual degradation (e.g. slow eye-openness
    drift over 90 min) that a short rolling window would miss.

    Owner: Kevin (agents/context_builder.py)
    """
    shift_id: str
    trend_bucket_minutes: float              # duration each bucket represents (e.g. 5.0)
    sample_count: int = 0                    # FrameAnalysis samples aggregated so far
    yawn_count_total: int = 0               # cumulative yawn events this shift
    intervention_count: int = 0            # total interventions fired this shift
    avg_eye_openness_trend: list = field(default_factory=list)  # list[float] per bucket
    avg_blink_rate_trend: list = field(default_factory=list)    # list[float] per bucket


@dataclass
class InterventionRecord:
    """Written to memory after an intervention executes; forms prior_interventions in ShiftContext.

    Owner: Kevin (actions/ handlers populate, memory/ persists)
    """
    intervention_id: str       # uuid4
    driver_id: str
    shift_id: str
    timestamp: float           # unix epoch
    severity: str              # "low" | "medium" | "high" | "critical"
    intervention_type: str     # "alert" | "rest_break" | "phone_notify"
    action_summary: str
    suggested_stops: list = field(default_factory=list)  # list[str] — populated by rest_break via rest_finder


@dataclass
class ShiftContext:
    """Full per-cycle context assembled by agents/context_builder.py.

    Consumed by agents/safety.py (Safety Reasoning Agent) and agents/companion.py
    (Companion Agent). Single source of truth for what the agents know each cycle.

    Owner: Kevin (agents/context_builder.py)
    """
    driver_id: str
    shift_id: str
    shift_elapsed_minutes: float
    current_analysis: FrameAnalysis
    shift_trend: ShiftTrend
    baseline: DriverBaseline
    recent_window: list = field(default_factory=list)        # list[FrameAnalysis] — last N minutes
    prior_interventions: list = field(default_factory=list)  # list[InterventionRecord] — this shift
    vlm_assessment: Optional[VLMFrameAssessment] = None      # latest VLM assessment; None until first VLM cycle


@dataclass
class InterventionDecision:
    """Output of agents/safety.py (Safety Reasoning Agent); drives orchestrator dispatch.

    trigger_companion is independent of should_intervene — companion can engage at
    low severity before a hard intervention is needed. Escalation across cycles is
    controlled by severity_escalation_minutes in config/defaults.yaml.

    Owner: Kevin (agents/safety.py produces, agents/orchestrator.py consumes)
    """
    should_intervene: bool
    severity: str                # "none" | "low" | "medium" | "high" | "critical"
    intervention_type: str       # "none" | "alert" | "rest_break" | "phone_notify"
    trigger_companion: bool      # True → spawn Companion Agent this cycle (independent of should_intervene)
    reason: str                  # human-readable reasoning trace from Nemotron
    confidence: float            # 0.0–1.0
    timestamp: float             # unix epoch


@dataclass
class CompanionMessage:
    """A proactive message generated by the Companion Agent (agents/companion.py).

    Displayed on-screen or read aloud via TTS. The companion acts autonomously —
    chooses what to say based on fatigue level, shift duration, and prior messages
    to avoid repetition.

    Owner: Emilio (agents/companion.py produces, agents/orchestrator.py dispatches)
    """
    timestamp: float
    driver_id: str
    message: str               # e.g. "Hey, you seem a bit tired — want to tell me about your day?"
    trigger_reason: str        # "fatigue_building" | "long_silence" | "pre_intervention"
    severity_context: str      # severity level that triggered this companion turn
