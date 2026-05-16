"""In-cab alert handler.

Called by agents/tools.py handle_trigger_alert() when the Safety Reasoning Agent
fires an alert action. Calls actions/alerting_client.py to deliver the on-device
audio/visual alert, then returns an InterventionRecord.

Owner: Kevin
Imports from: core.models, actions.alerting_client
"""


def execute(decision, driver_id: str, shift_id: str = "") -> "InterventionRecord":
    """Fire in-cab alert and return an InterventionRecord.

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
    from actions.alerting_client import send_alert

    send_alert(severity=decision.severity, message=decision.reason)

    return InterventionRecord(
        intervention_id=str(uuid.uuid4()),
        driver_id=driver_id,
        shift_id=shift_id,
        timestamp=time.time(),
        severity=decision.severity,
        intervention_type="alert",
        action_summary=f"In-cab alert fired: {decision.reason[:100]}",
    )
