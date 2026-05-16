"""In-cab audio/visual alert client.

Delivers on-device alerts to the driver.
- low/medium: coloured terminal banner only
- high:       banner only (rest_break handles phone notification at this level)
- critical:   banner + terminal bell + edge-tts audible alarm played twice

Owner: Kevin
"""

_CRITICAL_MESSAGE = (
    "Warning! Warning! It looks like you are in danger of falling asleep. "
    "Please pull over immediately."
)
_CRITICAL_VOICE = "en-US-GuyNeural"


def send_alert(severity: str, message: str) -> bool:
    """Deliver an in-cab alert to the driver.

    Args:
        severity: "low" | "medium" | "high" | "critical"
        message: human-readable alert message

    Returns:
        True if delivered successfully
    """
    import subprocess
    import sys

    _colour = {
        "low":      "\033[93m",
        "medium":   "\033[91m",
        "high":     "\033[41m\033[97m",
        "critical": "\033[41m\033[97m",
    }
    reset = "\033[0m"
    colour = _colour.get(severity, "\033[91m")

    banner = f"{colour}\n{'='*60}\n"
    banner += f"  ⚠  SAFESHIFT ALERT [{severity.upper()}]\n"
    banner += f"  {message}\n"
    banner += f"{'='*60}\n{reset}"
    print(banner, flush=True)

    if severity == "critical":
        # terminal bell — works in most terminals
        sys.stdout.write("\a\a\a")
        sys.stdout.flush()
        # audible alarm via edge-tts, played twice in an authoritative voice
        _play_alarm()

    # macOS OS notification — silent fail if permissions not granted
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "SafeShift [{severity.upper()}]"'],
            capture_output=True, timeout=2,
        )
    except Exception:
        pass

    return True


def _play_alarm() -> None:
    """Play the critical alarm message twice via edge-tts in a background thread."""
    import threading

    def _run():
        try:
            import asyncio, edge_tts, tempfile, os, subprocess as sp
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tmp = tempfile.mktemp(suffix=".mp3")
            loop.run_until_complete(
                edge_tts.Communicate(_CRITICAL_MESSAGE, _CRITICAL_VOICE).save(tmp)
            )
            loop.close()
            # play twice for urgency
            sp.run(["afplay", tmp], check=True)
            sp.run(["afplay", tmp], check=True)
            os.unlink(tmp)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
