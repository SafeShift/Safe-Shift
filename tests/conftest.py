"""Shared pytest fixtures: sample instances of every dataclass in core/models.py.

Any test file can do:
  from tests.conftest import sample_frame_analysis, sample_shift_context

All fixtures use realistic but non-personal values. External calls (Nemotron API,
ntfy, Nominatim) are mocked at the integration boundary.

Owner: Josh
Imports from: core.models
"""
import time
import pytest
from core.models import (
    FrameAnalysis,
    VLMFrameAssessment,
    DriverBaseline,
    ShiftTrend,
    ShiftContext,
    InterventionDecision,
    InterventionRecord,
    CompanionMessage,
)

DRIVER_ID = "driver_test_001"
SHIFT_ID  = "shift-0000-0000-0000-test"


@pytest.fixture
def sample_frame_analysis():
    return FrameAnalysis(
        timestamp=time.time(),
        driver_id=DRIVER_ID,
        blink_rate=14.0,
        eye_openness=0.55,
        yawn_detected=False,
        yawn_frequency=1.2,
        gaze_direction="forward",
        gaze_deviation_deg=3.5,
        confidence=0.91,
    )


@pytest.fixture
def sample_vlm_assessment():
    return VLMFrameAssessment(
        timestamp=time.time(),
        driver_id=DRIVER_ID,
        fatigue_score=0.35,
        description="Driver appears alert; slight eye droopiness noted.",
        flags=["slight_eye_droopiness"],
        confidence=0.88,
    )


@pytest.fixture
def sample_baseline():
    return DriverBaseline(
        driver_id=DRIVER_ID,
        avg_blink_rate=16.0,
        avg_eye_openness=0.72,
        avg_yawn_frequency=0.5,
        shift_count=4,
        last_updated="2026-05-14T08:00:00Z",
    )


@pytest.fixture
def sample_shift_trend():
    return ShiftTrend(
        shift_id=SHIFT_ID,
        trend_bucket_minutes=5.0,
        sample_count=24,
        yawn_count_total=2,
        intervention_count=0,
        avg_eye_openness_trend=[0.72, 0.70, 0.67, 0.61, 0.55],
        avg_blink_rate_trend=[16.0, 15.5, 14.8, 14.2, 14.0],
    )


@pytest.fixture
def sample_shift_context(sample_frame_analysis, sample_vlm_assessment, sample_baseline, sample_shift_trend):
    return ShiftContext(
        driver_id=DRIVER_ID,
        shift_id=SHIFT_ID,
        shift_elapsed_minutes=42.0,
        current_analysis=sample_frame_analysis,
        shift_trend=sample_shift_trend,
        baseline=sample_baseline,
        recent_window=[sample_frame_analysis],
        prior_interventions=[],
        vlm_assessment=sample_vlm_assessment,
    )


@pytest.fixture
def sample_intervention_decision():
    return InterventionDecision(
        should_intervene=True,
        severity="medium",
        intervention_type="alert",
        trigger_companion=True,
        reason="Eye openness 24% below baseline; steady decline over 40 min.",
        confidence=0.82,
        timestamp=time.time(),
    )


@pytest.fixture
def sample_intervention_record():
    return InterventionRecord(
        intervention_id="record-0000-test",
        driver_id=DRIVER_ID,
        shift_id=SHIFT_ID,
        timestamp=time.time(),
        severity="medium",
        intervention_type="alert",
        action_summary="In-cab audio alert delivered.",
        suggested_stops=[],
    )


@pytest.fixture
def sample_companion_message():
    return CompanionMessage(
        timestamp=time.time(),
        driver_id=DRIVER_ID,
        message="Hey, you've been at it a while — what's your favourite rest stop?",
        trigger_reason="fatigue_building",
        severity_context="medium",
    )
