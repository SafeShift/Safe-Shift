"""ntfy push notification client for driver phone alerts.

Sends push notifications to the driver's own phone via ntfy (ntfy.sh public server
or self-hosted). The ntfy topic is treated like a password — set per-driver in .env.
No fleet or employer endpoints exist here.

Owner: Kevin
Imports from: config.settings (NTFY_TOPIC, NTFY_SERVER_URL)
"""


_SEVERITY_MESSAGES = {
    "low":      ("🟡 SafeShift", "🟡 Heads up — I noticed early fatigue signs. How are you feeling?", "low"),
    "medium":   ("🟠 SafeShift", "🟠 Fatigue building. A quick break would help — be safe!", "default"),
    "high":     ("🔴 SafeShift", "🔴 High fatigue detected. Pulling over soon is strongly recommended. Check your screen for nearby stops.", "high"),
    "critical": ("🚨 SafeShift", "🚨 URGENT: Severe fatigue. Pull over immediately for your safety.", "urgent"),
}


def send_severity_push(severity: str) -> bool:
    """Send a pre-defined severity-appropriate push notification to the driver's phone."""
    title, message, priority = _SEVERITY_MESSAGES.get(severity, _SEVERITY_MESSAGES["medium"])
    return send_push(title=title, message=message, priority=priority)


def send_push(title: str, message: str, priority: str = "high") -> bool:
    """Send a push notification to the driver's phone via ntfy.

    Args:
        title: notification title
        message: notification body
        priority: ntfy priority ("low" | "default" | "high" | "urgent")

    Returns:
        True if the ntfy server accepted the request
    """
    import requests
    from config.settings import load_config
    _cfg = load_config()

    url = f"{_cfg.notifications.ntfy_server}/{_cfg.notifications.ntfy_topic}"
    try:
        resp = requests.post(
            url,
            data=message.encode(),
            headers={"Title": title, "Priority": priority},
            timeout=5,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False
