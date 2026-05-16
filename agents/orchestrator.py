"""Main per-cycle agent loop for SafeShift."""
import logging

from config.settings import config
from agents.context_builder import build_context
from agents.safety import run as safety_run
from agents.companion import generate as companion_generate
from actions.logging_client import log_cycle

logger = logging.getLogger(__name__)

# companion message history — persists across cycles for deduplication
_prior_companion_messages: list = []


def run_cycle(frame, shift_id: str, shift_start: float, vlm_assessment=None) -> None:
    # 1. assemble ShiftContext
    context = build_context(frame, shift_id, shift_start, vlm_assessment)

    # 2. Safety Reasoning Agent — ReAct loop → InterventionDecision
    decision = safety_run(context)

    # 3. Companion Agent — fires independently when triggered
    companion_message = None
    if decision.trigger_companion:
        try:
            companion_message = companion_generate(
                context=context,
                prior_messages=_prior_companion_messages,
                severity=decision.severity,
                model=config.api.nemotron_companion_model,
            )
            _prior_companion_messages.append(companion_message)
        except Exception as e:
            logger.warning("Companion agent failed: %s", e)

    # 4. always log the cycle locally
    log_cycle(frame, decision, companion_message)

    # 5. publish events to frontend — wrapped so a Josh stub doesn't crash us
    _publish_events(frame, decision, companion_message, vlm_assessment)


def _publish_events(frame, decision, companion_message, vlm_assessment) -> None:
    try:
        from api.events import publish
        import dataclasses

        publish("frame", {
            "driver_id": frame.driver_id,
            "blink_rate": frame.blink_rate,
            "eye_openness": frame.eye_openness,
            "yawn_detected": frame.yawn_detected,
            "yawn_frequency": frame.yawn_frequency,
            "gaze_direction": frame.gaze_direction,
            "confidence": frame.confidence,
            "timestamp": frame.timestamp,
        })
        publish("decision", {
            "severity": decision.severity,
            "should_intervene": decision.should_intervene,
            "intervention_type": decision.intervention_type,
            "trigger_companion": decision.trigger_companion,
            "reason": decision.reason,
            "confidence": decision.confidence,
        })
        if vlm_assessment:
            publish("vlm", {
                "fatigue_score": vlm_assessment.fatigue_score,
                "description": vlm_assessment.description,
                "flags": vlm_assessment.flags,
                "confidence": vlm_assessment.confidence,
            })
        if companion_message:
            publish("companion", {
                "message": companion_message.message,
                "trigger_reason": companion_message.trigger_reason,
                "severity_context": companion_message.severity_context,
            })
    except Exception as e:
        logger.debug("Event publish skipped: %s", e)
