"""Rest break recommendation handler.

Called by agents/tools.py handle_trigger_rest_break(). Calls actions/rest_finder.py
to find nearby stops, then surfaces the recommendation on-device and returns an
InterventionRecord with suggested_stops populated.

Owner: Kevin
Imports from: core.models, actions.rest_finder, actions.alerting_client
"""


def execute(decision, driver_id: str) -> "InterventionRecord":
    """Recommend a rest break with nearby stop suggestions.

    Args:
        decision: InterventionDecision from agents/safety.py
        driver_id: active driver ID

    Returns:
        InterventionRecord with suggested_stops populated
    """
    raise NotImplementedError
