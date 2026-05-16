"""OpenClaw tool registry for the Safety Reasoning Agent.

Declares the JSON schema for every tool Nemotron-Super can call during its ReAct loop,
and maps each tool name to its Python handler function. OpenClaw executes handlers
automatically when the model calls a tool — agents/orchestrator.py does not dispatch
manually.

Tool categories:
  Query tools (gather information before deciding):
    - check_baseline       → memory/driver_baseline.get_baseline()
    - get_shift_trend      → memory/shift_history derived ShiftTrend
    - get_recent_interventions → memory/shift_history.get_interventions()

  Action tools (take effect in the world):
    - trigger_alert        → actions/alert.execute()
    - trigger_rest_break   → actions/rest_break.execute()  (also calls rest_finder)
    - trigger_phone_notify → actions/phone_notify.execute()
    - log_intervention     → memory/shift_history.append_intervention()

Owner: Kevin
Imports from: core.models, actions.*, memory.*
"""

TOOLS = [
    # --- Query tools ---
    {
        "name": "check_baseline",
        "description": "Retrieve the driver's historical baseline metrics to compare against current readings.",
        "parameters": {
            "type": "object",
            "properties": {
                "driver_id": {"type": "string"}
            },
            "required": ["driver_id"]
        }
    },
    {
        "name": "get_shift_trend",
        "description": "Get the full-shift degradation trend to detect gradual fatigue that short windows miss.",
        "parameters": {
            "type": "object",
            "properties": {
                "shift_id": {"type": "string"}
            },
            "required": ["shift_id"]
        }
    },
    {
        "name": "get_recent_interventions",
        "description": "Get interventions already fired this shift to avoid over-escalation.",
        "parameters": {
            "type": "object",
            "properties": {
                "shift_id": {"type": "string"},
                "last_n_minutes": {"type": "integer", "default": 30}
            },
            "required": ["shift_id"]
        }
    },
    # --- Action tools ---
    {
        "name": "trigger_alert",
        "description": "Fire an in-cab alert. At low/medium: keeps driver engaged and awake. At critical: fires an audible alarm to rouse a potentially sleeping driver — combine with trigger_rest_break.",
        "parameters": {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["low", "medium", "critical"]},
                "reason": {"type": "string"}
            },
            "required": ["severity", "reason"]
        }
    },
    {
        "name": "trigger_rest_break",
        "description": "Recommend the driver pull over immediately for their own safety. Finds nearby rest stops and sends location to driver's phone. Use at high or critical severity.",
        "parameters": {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["high", "critical"]},
                "reason": {"type": "string"},
                "suggested_minutes": {"type": "integer"}
            },
            "required": ["severity", "reason"]
        }
    },
    {
        "name": "log_intervention",
        "description": "Persist the intervention record to local memory. Always call this last.",
        "parameters": {
            "type": "object",
            "properties": {
                "intervention_type": {"type": "string"},
                "severity": {"type": "string"},
                "action_summary": {"type": "string"}
            },
            "required": ["intervention_type", "severity", "action_summary"]
        }
    }
]


# --- Tool handler bindings ---

def handle_check_baseline(driver_id: str, **_) -> dict:
    from memory.driver_baseline import get_baseline
    b = get_baseline(driver_id)
    return {
        "driver_id": b.driver_id,
        "avg_blink_rate": b.avg_blink_rate,
        "avg_eye_openness": b.avg_eye_openness,
        "avg_yawn_frequency": b.avg_yawn_frequency,
        "shift_count": b.shift_count,
        "last_updated": b.last_updated,
    }


def handle_get_shift_trend(shift_id: str, **_) -> dict:
    from memory.shift_history import get_all_frames
    frames = get_all_frames(shift_id)
    if not frames:
        return {"shift_id": shift_id, "sample_count": 0, "message": "No frames recorded yet"}
    return {
        "shift_id": shift_id,
        "sample_count": len(frames),
        "avg_eye_openness": round(sum(f.eye_openness for f in frames) / len(frames), 3),
        "avg_blink_rate": round(sum(f.blink_rate for f in frames) / len(frames), 2),
        "total_yawns": sum(1 for f in frames if f.yawn_detected),
    }


def handle_get_recent_interventions(shift_id: str, last_n_minutes: int = 30, **_) -> dict:
    import time
    from memory.shift_history import get_interventions
    cutoff = time.time() - (last_n_minutes * 60)
    all_interventions = get_interventions(shift_id)
    recent = [r for r in all_interventions if r.timestamp >= cutoff]
    return {
        "count": len(recent),
        "interventions": [
            {
                "type": r.intervention_type,
                "severity": r.severity,
                "minutes_ago": round((time.time() - r.timestamp) / 60, 1),
                "summary": r.action_summary,
            }
            for r in recent
        ],
    }


def handle_trigger_alert(severity: str, reason: str, driver_id: str = "", shift_id: str = "", **_) -> dict:
    from core.models import InterventionDecision
    from actions.alert import execute
    import time
    decision = InterventionDecision(
        should_intervene=True, severity=severity, intervention_type="alert",
        trigger_companion=False, reason=reason, confidence=1.0, timestamp=time.time(),
    )
    record = execute(decision, driver_id, shift_id)
    return {"status": "alert_fired", "severity": severity, "intervention_id": record.intervention_id}


def handle_trigger_rest_break(severity: str, reason: str, suggested_minutes: int = 15, driver_id: str = "", shift_id: str = "", **_) -> dict:
    from core.models import InterventionDecision
    from actions.rest_break import execute
    import time
    decision = InterventionDecision(
        should_intervene=True, severity=severity, intervention_type="rest_break",
        trigger_companion=False, reason=reason, confidence=1.0, timestamp=time.time(),
    )
    record = execute(decision, driver_id, shift_id)
    return {"status": "rest_break_recommended", "stops": record.suggested_stops, "intervention_id": record.intervention_id}


def handle_trigger_phone_notify(severity: str, message: str, driver_id: str = "", shift_id: str = "", **_) -> dict:
    from core.models import InterventionDecision
    from actions.phone_notify import execute
    import time
    decision = InterventionDecision(
        should_intervene=True, severity=severity, intervention_type="phone_notify",
        trigger_companion=False, reason=message, confidence=1.0, timestamp=time.time(),
    )
    record = execute(decision, driver_id, shift_id)
    return {"status": "notification_sent", "severity": severity, "intervention_id": record.intervention_id}


def handle_log_intervention(intervention_type: str, severity: str, action_summary: str, driver_id: str = "", shift_id: str = "", **_) -> dict:
    import time, uuid
    from core.models import InterventionRecord
    from memory.shift_history import append_intervention
    record = InterventionRecord(
        intervention_id=str(uuid.uuid4()),
        driver_id=driver_id,
        shift_id=shift_id,
        timestamp=time.time(),
        severity=severity,
        intervention_type=intervention_type,
        action_summary=action_summary,
    )
    append_intervention(record)
    return {"status": "logged", "intervention_id": record.intervention_id}


TOOL_HANDLERS = {
    "check_baseline": handle_check_baseline,
    "get_shift_trend": handle_get_shift_trend,
    "get_recent_interventions": handle_get_recent_interventions,
    "trigger_alert": handle_trigger_alert,
    "trigger_rest_break": handle_trigger_rest_break,
    "trigger_phone_notify": handle_trigger_phone_notify,
    "log_intervention": handle_log_intervention,
}
