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

    _colour = {"low": "\033[93m", "medium": "\033[91m", "high": "\033[41m\033[97m"}
    reset = "\033[0m"
    colour = _colour.get(severity, "\033[91m")

    # big coloured banner — always visible in any terminal, great demo moment
    banner = f"{colour}"
    banner += f"\n{'='*60}\n"
    banner += f"  ⚠  SAFESHIFT ALERT [{severity.upper()}]\n"
    banner += f"  {message}\n"
    banner += f"{'='*60}\n"
    banner += reset
    print(banner, flush=True)

    # macOS OS notification as bonus — silent fail if permissions not granted
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "SafeShift [{severity.upper()}]"'],
            capture_output=True, timeout=2,
        )
    except Exception:
        pass

    return True
