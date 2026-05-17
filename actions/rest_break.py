"""Rest break recommendation handler.

Called by agents/tools.py handle_trigger_rest_break(). Calls actions/rest_finder.py
to find nearby stops, then surfaces the recommendation on-device and returns an
InterventionRecord with suggested_stops populated.

Owner: Kevin
Imports from: core.models, actions.rest_finder, actions.alerting_client
"""


def execute(decision, driver_id: str, shift_id: str = "") -> "InterventionRecord":
    """Recommend a rest break with nearby stop suggestions.

    Args:
        decision: InterventionDecision from agents/safety.py
        driver_id: active driver ID
        shift_id: active shift UUID (injected by tool handler)
        config: config object with demo_lat and demo_lon

    Returns:
        InterventionRecord with suggested_stops populated
    """
    import os, time, uuid
    from core.models import InterventionRecord
    from actions.rest_finder import find_nearby_stops, format_stop_list
    from actions.notify_client import send_push, _SEVERITY_MESSAGES
    from actions.alerting_client import send_alert

    # critical severity: fire the audible alarm automatically before the rest stop recommendation
    if decision.severity == "critical":
        send_alert(severity="critical", message=decision.reason)

    lat = float(os.getenv("DEMO_LAT", "36.9916"))
    lon = float(os.getenv("DEMO_LON", "-122.0583"))

    stops = find_nearby_stops(latitude=lat, longitude=lon, radius_km=10, max_results=3)
    stop_text = format_stop_list(stops)
    stop_names = [s["name"] for s in stops]

    title, warning_msg, priority = _SEVERITY_MESSAGES.get(decision.severity, _SEVERITY_MESSAGES["high"])
    message = f"{warning_msg} — Nearby stops: {stop_text}"
    send_push(title=title, message=message, priority=priority)

    return InterventionRecord(
        intervention_id=str(uuid.uuid4()),
        driver_id=driver_id,
        shift_id=shift_id,
        timestamp=time.time(),
        severity=decision.severity,
        intervention_type="rest_break",
        action_summary=f"Rest break recommended. Stops: {stop_text}",
        suggested_stops=stop_names,
    )
