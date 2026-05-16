"""Main per-cycle agent loop for SafeShift."""
import logging
import time

from core.models import InterventionDecision
from agents.context_builder import build_context
from actions.logging_client import log_cycle

logger = logging.getLogger(__name__)


def _no_intervention() -> InterventionDecision:
    return InterventionDecision(
        should_intervene=False, severity="none", intervention_type="none",
        trigger_companion=False, reason="Cooldown active", confidence=1.0,
        timestamp=time.time(),
    )


class Orchestrator:
    """Coordinates one analysis cycle: context → Safety Agent → Companion Agent → dispatch.

    Args:
        config:          SimpleNamespace from load_config().
        safety_agent:    SafetyAgent instance.
        companion_agent: CompanionAgent instance (agents/companion.py — Emilio).
        store:           MemoryStore instance.
    """

    def __init__(self, config, safety_agent, companion_agent, store):
        self._config    = config
        self._safety    = safety_agent
        self._companion = companion_agent
        self._store     = store
        self._prior_companion_messages: list = []  # dedup across cycles
        self._last_intervention_time: float = 0.0
        self._last_intervention_severity: str = "none"
        cooldown_min = getattr(config, "severity_escalation_minutes", 2)
        self._cooldown_seconds: float = cooldown_min * 60

    def run_cycle(self, frame, shift_id: str, shift_start: float, vlm_assessment=None) -> None:
        # 1. assemble ShiftContext
        context = build_context(frame, shift_id, shift_start, self._store, self._config, vlm_assessment)

        # 2. Safety Reasoning Agent — skip if within cooldown, unless conditions are critical
        now = time.time()
        secs_since_last = now - self._last_intervention_time
        # Override cooldown if eyes are nearly closed or eyes+yawn both dangerously low
        conditions_critical = (
            frame.eye_openness < 0.20
            or (frame.eye_openness < 0.30 and frame.yawn_detected)
        )
        within_cooldown = (secs_since_last < self._cooldown_seconds) and not conditions_critical
        if within_cooldown:
            logger.debug("Cooldown active — %ds remaining", int(self._cooldown_seconds - secs_since_last))
            decision = _no_intervention()
        else:
            decision = self._safety.run(context)
            if decision.should_intervene and decision.severity != "none":
                self._last_intervention_time = now
                self._last_intervention_severity = decision.severity

        # 3. Companion Agent — fires independently when triggered
        companion_message = None
        if decision.trigger_companion:
            try:
                companion_message = self._companion.generate(
                    context=context,
                    prior_messages=self._prior_companion_messages,
                    severity=decision.severity,
                )
                self._prior_companion_messages.append(companion_message)
            except Exception as e:
                logger.warning("Companion agent failed: %s", e)

        # 4. always log the cycle locally
        log_cycle(frame, decision, companion_message)

        # 5. publish events to frontend
        self._publish_events(frame, decision, companion_message, vlm_assessment)

    def _publish_events(self, frame, decision, companion_message, vlm_assessment) -> None:
        try:
            from api.events import publish

            publish("frame", {
                "driver_id":      frame.driver_id,
                "blink_rate":     frame.blink_rate,
                "eye_openness":   frame.eye_openness,
                "yawn_detected":  frame.yawn_detected,
                "yawn_frequency": frame.yawn_frequency,
                "gaze_direction": frame.gaze_direction,
                "confidence":     frame.confidence,
                "timestamp":      frame.timestamp,
            })
            publish("decision", {
                "severity":          decision.severity,
                "should_intervene":  decision.should_intervene,
                "intervention_type": decision.intervention_type,
                "trigger_companion": decision.trigger_companion,
                "reason":            decision.reason,
                "confidence":        decision.confidence,
            })
            if vlm_assessment:
                publish("vlm", {
                    "fatigue_score": vlm_assessment.fatigue_score,
                    "description":   vlm_assessment.description,
                    "flags":         vlm_assessment.flags,
                    "confidence":    vlm_assessment.confidence,
                })
            if companion_message:
                publish("companion", {
                    "message":          companion_message.message,
                    "trigger_reason":   companion_message.trigger_reason,
                    "severity_context": companion_message.severity_context,
                })
        except Exception as e:
            logger.debug("Event publish skipped: %s", e)
