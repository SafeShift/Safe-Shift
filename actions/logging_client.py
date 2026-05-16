"""Local session logger — always-on, every cycle.

Called by agents/orchestrator.py every cycle regardless of should_intervene.
Writes FrameAnalysis + InterventionDecision to the local session log (not SQLite —
append-only JSONL file for easy tail/grep during demo). Stays on-device.

Owner: Kevin
Imports from: config.settings (LOG_FILE_PATH)
"""


def log_cycle(frame, decision, companion_message=None, log_path: str = "./safeshift_session.log") -> None:
    """Append one cycle's data to the local session log.

    Args:
        frame: FrameAnalysis from vision/pipeline.py
        decision: InterventionDecision from agents/safety.py
        companion_message: CompanionMessage if companion fired this cycle, else None
    """
    import json
    from datetime import datetime

    entry = {
        "ts": datetime.utcnow().isoformat(),
        "driver_id": frame.driver_id,
        "eye_openness": frame.eye_openness,
        "blink_rate": frame.blink_rate,
        "yawn_detected": frame.yawn_detected,
        "gaze": frame.gaze_direction,
        "severity": decision.severity,
        "should_intervene": decision.should_intervene,
        "intervention_type": decision.intervention_type,
        "trigger_companion": decision.trigger_companion,
        "reason": decision.reason,
        "companion": companion_message.message if companion_message else None,
    }

    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
