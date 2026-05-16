"""ntfy push notification client for driver phone alerts.

Sends push notifications to the driver's own phone via ntfy (ntfy.sh public server
or self-hosted). The ntfy topic is treated like a password — set per-driver in .env.
No fleet or employer endpoints exist here.

Owner: Kevin
Imports from: config.settings (NTFY_TOPIC, NTFY_SERVER_URL)
"""


def send_push(title: str, message: str, priority: str = "high") -> bool:
    """Send a push notification to the driver's phone via ntfy.

    Args:
        title: notification title
        message: notification body
        priority: ntfy priority ("low" | "default" | "high" | "urgent")

    Returns:
        True if the ntfy server accepted the request
    """
    raise NotImplementedError
