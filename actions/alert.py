"""In-cab alert handler.

Called by agents/tools.py handle_trigger_alert() when the Safety Reasoning Agent
fires an alert action. Calls actions/alerting_client.py to deliver the on-device
audio/visual alert, then returns an InterventionRecord.

Owner: Kevin
Imports from: core.models, actions.alerting_client
"""


def execute(decision, driver_id: str) -> "InterventionRecord":
    """Fire in-cab alert and return an InterventionRecord.

    Args:
        decision: InterventionDecision from agents/safety.py
        driver_id: active driver ID

    Returns:
        InterventionRecord
    """
    raise NotImplementedError
