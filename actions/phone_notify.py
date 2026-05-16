"""Driver phone notification handler.

Called by agents/tools.py handle_trigger_phone_notify(). Sends a push notification
to the driver's own phone via ntfy. Driver-only — no fleet or employer endpoints.
Returns an InterventionRecord.

Owner: Kevin
Imports from: core.models, actions.notify_client
"""


def execute(decision, driver_id: str, shift_id: str = "") -> "InterventionRecord":
    """Push notification to driver's phone and return an InterventionRecord.

    Args:
        decision: InterventionDecision from agents/safety.py
        driver_id: active driver ID
        shift_id: active shift UUID (injected by tool handler)

    Returns:
        InterventionRecord
    """
    import time
    import uuid
    from core.models import InterventionRecord
    from actions.notify_client import send_push

    _priority_map = {"low": "low", "medium": "default", "high": "high", "critical": "urgent"}
    priority = _priority_map.get(decision.severity, "high")

    title = f"SafeShift - {decision.severity.upper()} alert"
    send_push(title=title, message=decision.reason, priority=priority)

    return InterventionRecord(
        intervention_id=str(uuid.uuid4()),
        driver_id=driver_id,
        shift_id=shift_id,
        timestamp=time.time(),
        severity=decision.severity,
        intervention_type="phone_notify",
        action_summary=f"Phone notification sent: {decision.reason[:100]}",
    )
