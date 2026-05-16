"""In-cab audio/visual alert client.

Delivers on-device alerts to the driver (sound, OS notification, or terminal bell
depending on demo config). For the hackathon demo: OS notification + terminal bell.

Owner: Kevin
"""


def send_alert(severity: str, message: str) -> bool:
    """Deliver an in-cab alert to the driver.

    Args:
        severity: "low" | "medium" | "high"
        message: human-readable alert message

    Returns:
        True if delivered successfully
    """
    raise NotImplementedError
