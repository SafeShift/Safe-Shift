"""Generate fake FrameAnalysis objects simulating gradual driver fatigue.

Produces a realistic 45-minute fatigue arc that can be fed directly into
the pipeline instead of waiting for a real camera feed. Use this to trigger
companion and intervention events on demand during the demo.

Three scenarios:
  mild     — gradual decline, triggers companion at ~30 min
  moderate — faster decline, triggers alert + companion at ~20 min
  severe   — rapid decline, triggers phone notification at ~10 min

Usage:
    from demo.simulate_fatigue import get_scenario_frames, print_scenario

    frames = get_scenario_frames("moderate")
    for frame in frames:
        # feed into orchestrator as you would a real FrameAnalysis
        pass
"""
import time
from core.models import FrameAnalysis

DRIVER_ID = "Trucker Tom"


def get_scenario_frames(scenario: str = "moderate") -> list:
    """Return a list of FrameAnalysis objects simulating a fatigue arc.

    Args:
        scenario: "mild" | "moderate" | "severe"

    Returns:
        list[FrameAnalysis] — one frame per 2-second window across the shift
    """
    scenarios = {
        # (start_eye, end_eye, start_blink, end_blink, duration_min)
        "mild":     (0.74, 0.52, 16.2, 11.0, 45),
        "moderate": (0.74, 0.41, 16.2,  9.5, 30),
        "severe":   (0.74, 0.28, 16.2,  7.0, 15),
    }
    if scenario not in scenarios:
        raise ValueError(f"Unknown scenario '{scenario}'. Choose: {list(scenarios)}")

    start_eye, end_eye, start_blink, end_blink, duration_min = scenarios[scenario]
    n_frames = int(duration_min * 60 / 2)  # one frame every 2 s
    now = time.time()
    frames = []

    for i in range(n_frames):
        t = i / n_frames  # 0.0 → 1.0 progress through shift
        # fatigue doesn't decline linearly — slow start, faster towards end
        curve = t ** 1.6

        eye_openness = start_eye - (start_eye - end_eye) * curve
        blink_rate = start_blink - (start_blink - end_blink) * curve
        yawn_detected = t > 0.5 and (i % 90 == 0)      # yawn every ~3 min past halfway
        yawn_frequency = 1.1 + (t * 4.5)                # rises from 1.1 to ~5.6/hr
        gaze_dev = 2.5 + (t * 6.0)                       # gaze drifts slightly off-center

        frames.append(FrameAnalysis(
            timestamp=now + (i * 2),
            driver_id=DRIVER_ID,
            blink_rate=round(blink_rate, 1),
            eye_openness=round(eye_openness, 3),
            yawn_detected=yawn_detected,
            yawn_frequency=round(yawn_frequency, 2),
            gaze_direction="forward",
            gaze_deviation_deg=round(gaze_dev, 1),
            confidence=0.93,
        ))

    return frames


def print_scenario(scenario: str = "moderate") -> None:
    """Print a summary of the fatigue arc so you can sanity-check it before the demo."""
    frames = get_scenario_frames(scenario)
    checkpoints = [0, len(frames) // 4, len(frames) // 2, 3 * len(frames) // 4, -1]
    print(f"\nScenario: {scenario}  ({len(frames)} frames, "
          f"{len(frames) * 2 / 60:.0f} min simulated)\n")
    print(f"{'Time':>8}  {'Eye':>6}  {'Blink':>7}  {'Yawn/hr':>8}  {'Gaze dev':>9}")
    print("-" * 48)
    for idx in checkpoints:
        f = frames[idx]
        minutes = (f.timestamp - frames[0].timestamp) / 60
        print(f"{minutes:>7.0f}m  {f.eye_openness:>6.3f}  {f.blink_rate:>6.1f}/m"
              f"  {f.yawn_frequency:>7.2f}/hr  {f.gaze_deviation_deg:>7.1f}°")


if __name__ == "__main__":
    import sys
    scenario = sys.argv[1] if len(sys.argv) > 1 else "moderate"
    print_scenario(scenario)
