"""Local session logger — always-on, every cycle.

Called by agents/orchestrator.py every cycle regardless of should_intervene.
Writes FrameAnalysis + InterventionDecision to the local session log (not SQLite —
append-only JSONL file for easy tail/grep during demo). Stays on-device.

Owner: Kevin
Imports from: config.settings (LOG_FILE_PATH)
"""


def log_cycle(frame, decision, companion_message=None) -> None:
    """Append one cycle's data to the local session log.

    Args:
        frame: FrameAnalysis from vision/pipeline.py
        decision: InterventionDecision from agents/safety.py
        companion_message: CompanionMessage if companion fired this cycle, else None
    """
    raise NotImplementedError
