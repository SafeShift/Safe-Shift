"""Canonical shared dataclasses: FrameAnalysis, VLMFrameAssessment, DriverBaseline, ShiftTrend, ShiftContext, InterventionDecision, InterventionRecord, CompanionMessage.

All inter-module data exchange must use these types. Import from here everywhere.

CRITICAL PATH: finalize and commit this file before any other module is implemented —
everyone imports from it on day one.

No field defaults are intentionally omitted: FrameAnalysis, DriverBaseline,
InterventionRecord, and InterventionDecision are always fully constructed at call sites —
all fields required. ShiftTrend and ShiftContext have list/counter fields that are
legitimately empty at shift start and use field(default_factory=...) accordingly.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FrameAnalysis:
    """Output of vision/pipeline.py per analysis window (default: 2 s rolling)."""
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
    Produced by vision/vlm_analyzer.py on a slower cadence than FrameAnalysis.
    """
    timestamp: float
    driver_id: str
    fatigue_score: float       # 0.0 (fully alert) → 1.0 (severely fatigued)
    description: str           # natural language from VLM, e.g. "driver's head drooping left, eyes half-closed"
    flags: list                # list[str] — e.g. ["eyes_drooping", "head_tilt", "yawning"]
    confidence: float          # VLM confidence in the assessment 0.0–1.0


@dataclass
class DriverBaseline:
    """Per-driver historical norms; persisted in memory layer and updated after each shift."""
    driver_id: str
    avg_blink_rate: float
    avg_eye_openness: float
    avg_yawn_frequency: float
    shift_count: int
    last_updated: str          # ISO-8601 datetime string


@dataclass
class ShiftTrend:
    """Shift-level alertness trajectory, computed by agent/context_builder.py from full shift history.

    Provides Nemotron with a downsampled view of the entire shift — not just the recent
    window — so the model can detect gradual degradation (e.g. slow eye-openness drift
    over 90 min) that a short rolling window would miss.
    """
    shift_id: str
    trend_bucket_minutes: float              # duration each bucket represents (e.g. 5.0); from config
    sample_count: int = 0                    # FrameAnalysis samples aggregated so far
    yawn_count_total: int = 0                # cumulative yawn events this shift
    intervention_count: int = 0             # total interventions fired this shift
    avg_eye_openness_trend: list = field(default_factory=list)  # list[float] per bucket
    avg_blink_rate_trend: list = field(default_factory=list)    # list[float] per bucket


@dataclass
class InterventionRecord:
    """Written to memory after an intervention executes; forms prior_interventions in ShiftContext."""
    intervention_id: str       # uuid4
    driver_id: str
    shift_id: str
    timestamp: float           # unix epoch
    severity: str              # "low" | "medium" | "high" | "critical"
    intervention_type: str     # "alert" | "rest_break" | "phone_notify"
    action_summary: str
    suggested_stops: list = field(default_factory=list)  # list[str] — populated by rest_break handler via rest_finder


@dataclass
class ShiftContext:
    """Assembled by agent/context_builder.py; consumed by reasoning/nemotron.py."""
    driver_id: str
    shift_id: str
    shift_elapsed_minutes: float
    current_analysis: FrameAnalysis
    shift_trend: ShiftTrend    # downsampled full-shift trajectory for degradation detection
    baseline: DriverBaseline
    recent_window: list = field(default_factory=list)        # list[FrameAnalysis] — last N minutes
    prior_interventions: list = field(default_factory=list)  # list[InterventionRecord] — this shift
    vlm_assessment: Optional[VLMFrameAssessment] = None      # latest VLM frame assessment; None until first VLM cycle


@dataclass
class InterventionDecision:
    """Parsed output of reasoning/decision.py; drives intervention handler dispatch.

    Escalation model: intervention_type is a single action per cycle. Graduated
    escalation (alert → rest_break → phone_notify) happens across loop cycles; the
    cooldown window is controlled by the `severity_escalation_minutes` key in
    config/defaults.yaml (typed access via config.settings.SEVERITY_ESCALATION_MINUTES).

    Session logging is always-on: orchestrator.py calls integrations/logging_service.py
    every cycle regardless of should_intervene. It is NOT an intervention_type value.
    """
    should_intervene: bool
    severity: str                # "none" | "low" | "medium" | "high" | "critical"
    intervention_type: str       # "none" | "alert" | "rest_break" | "phone_notify"
    trigger_companion: bool      # True if companion agent should also engage this cycle
    reason: str                  # human-readable explanation from Nemotron
    confidence: float            # 0.0–1.0
    timestamp: float             # unix epoch


@dataclass
class CompanionMessage:
    """A proactive message from the companion agent; displayed on-screen or read aloud.

    Generated by agent/companion.py when trigger_companion=True in InterventionDecision.
    The companion acts autonomously — it chooses what to say based on fatigue level,
    shift duration, and prior messages to avoid repetition.
    """
    timestamp: float
    driver_id: str
    message: str               # what the companion says, e.g. "Hey, you seem a bit tired — want to tell me about your day?"
    trigger_reason: str        # e.g. "fatigue_building" | "long_silence" | "pre_intervention"
    severity_context: str      # severity level that triggered this companion turn
