"""Main per-cycle agent loop for SafeShift."""
import logging
import time

from agents.context_builder import build_context
from actions.logging_client import log_cycle

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


class Orchestrator:
    """Coordinates one analysis cycle: context → Safety Agent → cooldown → dispatch.

    The safety agent is a pure reasoning component — it outputs a decision JSON
    but fires no actions. This orchestrator applies cooldown logic in Python and
    then dispatches actions, giving us deterministic rate limiting.

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
        self._prior_companion_messages: list = []
        self._last_intervention_time: float = 0.0
        self._last_intervention_severity: str = "none"
        self._last_companion_time: float = 0.0
        cooldown_min = getattr(config, "severity_escalation_minutes", 1)
        self._cooldown_seconds: float = cooldown_min * 60
        self._companion_min_interval: float = 45.0  # seconds between companion messages

    def _in_cooldown(self, severity: str, now: float) -> bool:
        """True if this severity is blocked by the cooldown window.

        Escalation (higher severity than last) always bypasses cooldown.
        Same or lower severity respects the window.
        """
        last_order = _SEVERITY_ORDER.get(self._last_intervention_severity, 0)
        this_order = _SEVERITY_ORDER.get(severity, 0)
        if this_order > last_order:
            return False  # escalation always fires immediately
        return (now - self._last_intervention_time) < self._cooldown_seconds

    def _dispatch(self, decision, context) -> None:
        """Fire the appropriate action and log the intervention record."""
        import time
        from core.models import InterventionDecision as _D
        from memory.shift_history import append_intervention

        _d = _D(
            should_intervene=True, severity=decision.severity,
            intervention_type=decision.intervention_type,
            trigger_companion=False, reason=decision.reason,
            confidence=decision.confidence, timestamp=time.time(),
        )
        if decision.severity in ("low", "medium"):
            from actions.alert import execute
            record = execute(_d, context.driver_id, context.shift_id)
        elif decision.severity in ("high", "critical"):
            from actions.rest_break import execute
            record = execute(_d, context.driver_id, context.shift_id)
        else:
            return

        append_intervention(record, self._store)

    def run_cycle(self, frame, shift_id: str, shift_start: float, vlm_assessment=None) -> None:
        # 1. assemble ShiftContext
        context = build_context(frame, shift_id, shift_start, self._store, self._config, vlm_assessment)

        # 2. Safety agent reasons and returns a decision (no side effects)
        decision = self._safety.run(context)

        # 3. Apply cooldown, then dispatch if allowed
        now = time.time()
        action_dispatched = False
        if decision.should_intervene and decision.severity != "none":
            if self._in_cooldown(decision.severity, now):
                logger.debug("Cooldown suppressed %s intervention", decision.severity)
                decision.should_intervene = False
            else:
                self._dispatch(decision, context)
                self._last_intervention_time = now
                self._last_intervention_severity = decision.severity
                action_dispatched = True

        # 4. Companion fires only when an action was just dispatched and enough
        #    time has passed since the last companion message.
        companion_message = None
        if (action_dispatched
                and decision.trigger_companion
                and (now - self._last_companion_time) >= self._companion_min_interval):
            try:
                companion_message = self._companion.generate(
                    context=context,
                    prior_messages=self._prior_companion_messages,
                    severity=decision.severity,
                )
                self._prior_companion_messages.append(companion_message)
                self._last_companion_time = now
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
