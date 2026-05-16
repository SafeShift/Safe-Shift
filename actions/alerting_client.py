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
    import subprocess
    import sys

    # terminal bell — audible in any terminal
    sys.stdout.write("\a")
    sys.stdout.flush()

    # macOS OS notification — visible on screen during demo
    title = f"SafeShift Alert [{severity.upper()}]"
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}"'],
            check=True, capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass  # non-macOS or osascript unavailable — bell still fired

    return True
