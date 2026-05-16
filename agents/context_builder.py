"""Assembles ShiftContext from vision outputs, memory layer, and shift state.

The only module that reads from both vision output and the memory layer simultaneously.
Called once per cycle by agents/orchestrator.py before invoking either agent.

Key responsibilities:
- Merge FrameAnalysis + VLMFrameAssessment (latest available) into a single context.
- Pull DriverBaseline from memory/driver_baseline.py.
- Compute ShiftTrend from full shift history via memory/shift_history.get_all_frames().
- Return a fully populated ShiftContext ready for agents/safety.py.

Owner: Kevin
Imports from: core.models, memory.driver_baseline, memory.shift_history
"""


def build_context(frame, shift_id: str, shift_start: float, vlm_assessment=None):
    """Assemble and return a ShiftContext for the current cycle.

    Args:
        frame: FrameAnalysis from vision/pipeline.py
        shift_id: active shift UUID
        shift_start: unix epoch of shift start
        vlm_assessment: latest VLMFrameAssessment or None if not yet available

    Returns:
        ShiftContext
    """
    raise NotImplementedError
