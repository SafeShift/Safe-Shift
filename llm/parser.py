"""Parse raw Nemotron completions into typed SafeShift dataclasses.

Used by:
  agents/safety.py   → parse_intervention_decision()
  agents/companion.py → parse_companion_message()

Owner: Kevin
Imports from: core.models
"""
import json


def parse_intervention_decision(raw: str, timestamp: float) -> "InterventionDecision":
    """Extract and validate InterventionDecision from Safety Reasoning Agent completion.

    The safety agent emits a JSON block at the end of its ReAct session. This function
    finds that block, validates required fields, and returns a typed InterventionDecision.

    Args:
        raw: raw model completion string
        timestamp: unix epoch for the decision timestamp

    Returns:
        InterventionDecision

    Raises:
        ValueError: if JSON is missing, malformed, or missing required fields
    """
    raise NotImplementedError


def parse_companion_message(raw: str, driver_id: str, trigger_reason: str, severity_context: str) -> "CompanionMessage":
    """Wrap the Companion Agent's plain-text output into a CompanionMessage dataclass.

    Args:
        raw: plain-text message string from the companion completion
        driver_id: active driver ID
        trigger_reason: reason companion was triggered (e.g. "fatigue_building")
        severity_context: severity level from InterventionDecision

    Returns:
        CompanionMessage
    """
    raise NotImplementedError
