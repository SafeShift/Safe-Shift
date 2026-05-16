# API Reference

> Placeholder — fill in as modules are implemented.

## vision.pipeline
- `run_pipeline(driver_id: str) -> Iterator[FrameAnalysis]`

## memory.driver_baseline
- `get_baseline(driver_id: str) -> DriverBaseline`
- `save_baseline(baseline: DriverBaseline) -> None`

## memory.shift_history
- `append_frame(shift_id: str, frame: FrameAnalysis) -> None`
- `append_intervention(record: InterventionRecord) -> None`
- `get_recent_frames(shift_id: str, minutes: int) -> list[FrameAnalysis]`
- `get_interventions(shift_id: str) -> list[InterventionRecord]`

## agent.context_builder
- `build_context(frame: FrameAnalysis, shift_id: str, shift_start: float) -> ShiftContext`

## reasoning.nemotron
- `analyze(context: ShiftContext) -> InterventionDecision`

## interventions.{alert, rest_break, phone_notify}
- `execute(decision: InterventionDecision, driver_id: str) -> InterventionRecord`
