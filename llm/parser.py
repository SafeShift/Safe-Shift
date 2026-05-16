"""Parse raw Nemotron completions into typed SafeShift dataclasses.

Used by:
  agents/safety.py   → parse_intervention_decision()
  agents/companion.py → parse_companion_message()

Owner: Kevin
Imports from: core.models
"""
import json


import re
import time as _time
from core.models import InterventionDecision, CompanionMessage


def parse_intervention_decision(raw: str, timestamp: float) -> InterventionDecision:
    # find the last JSON block in the completion
    matches = re.findall(r'\{[^{}]*\}', raw, re.DOTALL)
    if not matches:
        raise ValueError(f"No JSON block found in safety agent output: {raw[:200]}")

    data = None
    for candidate in reversed(matches):
        try:
            data = json.loads(candidate)
            if "should_intervene" in data:
                break
        except json.JSONDecodeError:
            continue

    if data is None:
        raise ValueError(f"No valid InterventionDecision JSON found in: {raw[:200]}")

    required = {"should_intervene", "severity", "intervention_type", "trigger_companion", "reason", "confidence"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"InterventionDecision JSON missing fields: {missing}")

    return InterventionDecision(
        should_intervene=bool(data["should_intervene"]),
        severity=data["severity"],
        intervention_type=data["intervention_type"],
        trigger_companion=bool(data["trigger_companion"]),
        reason=data["reason"],
        confidence=float(data["confidence"]),
        timestamp=timestamp,
    )


def parse_companion_message(raw: str, driver_id: str, trigger_reason: str, severity_context: str) -> CompanionMessage:
    return CompanionMessage(
        timestamp=_time.time(),
        driver_id=driver_id,
        message=raw.strip(),
        trigger_reason=trigger_reason,
        severity_context=severity_context,
    )
