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
        "description": "Fire an immediate in-cab audio/visual alert to the driver.",
        "parameters": {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                "reason": {"type": "string"}
            },
            "required": ["severity", "reason"]
        }
    },
    {
        "name": "trigger_rest_break",
        "description": "Recommend a rest break; automatically finds nearby stops via rest_finder.",
        "parameters": {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["medium", "high"]},
                "reason": {"type": "string"},
                "suggested_minutes": {"type": "integer"}
            },
            "required": ["severity", "reason"]
        }
    },
    {
        "name": "trigger_phone_notify",
        "description": "Send a push notification to the driver's own phone via ntfy. Driver-only — no fleet.",
        "parameters": {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["high", "critical"]},
                "message": {"type": "string"}
            },
            "required": ["severity", "message"]
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


# --- Tool handler bindings (called by OpenClaw, not orchestrator) ---

def handle_check_baseline(driver_id: str) -> dict:
    raise NotImplementedError


def handle_get_shift_trend(shift_id: str) -> dict:
    raise NotImplementedError


def handle_get_recent_interventions(shift_id: str, last_n_minutes: int = 30) -> dict:
    raise NotImplementedError


def handle_trigger_alert(severity: str, reason: str) -> dict:
    raise NotImplementedError


def handle_trigger_rest_break(severity: str, reason: str, suggested_minutes: int = 15) -> dict:
    raise NotImplementedError


def handle_trigger_phone_notify(severity: str, message: str) -> dict:
    raise NotImplementedError


def handle_log_intervention(intervention_type: str, severity: str, action_summary: str) -> dict:
    raise NotImplementedError
