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


def build_context(frame, shift_id: str, shift_start: float, store, config, vlm_assessment=None):
    """Assemble and return a ShiftContext for the current cycle.

    Args:
        frame: FrameAnalysis from vision/pipeline.py
        shift_id: active shift UUID
        shift_start: unix epoch of shift start
        store: MemoryStore instance
        config: loaded config SimpleNamespace
        vlm_assessment: latest VLMFrameAssessment or None if not yet available

    Returns:
        ShiftContext
    """
    import time
    from core.models import ShiftContext, ShiftTrend
    from memory.driver_baseline import get_baseline
    from memory.shift_history import get_recent_frames, get_all_frames, get_interventions

    shift_elapsed_minutes = (time.time() - shift_start) / 60
    baseline = get_baseline(frame.driver_id, store, config)
    recent_window = get_recent_frames(shift_id, store, minutes=10)
    prior_interventions = get_interventions(shift_id, store)
    all_frames = get_all_frames(shift_id, store)

    trend = _compute_shift_trend(shift_id, all_frames, bucket_minutes=5.0)

    # Warm-start: FeatureAggregator cold-starts at 0.0 blink rate because no blinks
    # have been counted yet in the first window. Substitute the driver's personal
    # baseline so the safety agent doesn't see a false -100% alarm on cycle 1.
    WARMUP_MINUTES = 1.0
    if shift_elapsed_minutes < WARMUP_MINUTES and frame.blink_rate == 0.0:
        from dataclasses import replace
        frame = replace(frame, blink_rate=baseline.avg_blink_rate)

    return ShiftContext(
        driver_id=frame.driver_id,
        shift_id=shift_id,
        shift_elapsed_minutes=shift_elapsed_minutes,
        current_analysis=frame,
        shift_trend=trend,
        baseline=baseline,
        recent_window=recent_window,
        prior_interventions=prior_interventions,
        vlm_assessment=vlm_assessment,
    )


def _compute_shift_trend(shift_id: str, all_frames: list, bucket_minutes: float = 5.0) -> "ShiftTrend":
    """Bucket all shift frames into time windows and compute per-bucket averages."""
    from core.models import ShiftTrend

    if not all_frames:
        return ShiftTrend(shift_id=shift_id, trend_bucket_minutes=bucket_minutes)

    bucket_seconds = bucket_minutes * 60
    shift_start_ts = all_frames[0].timestamp
    yawn_total = sum(1 for f in all_frames if f.yawn_detected)

    # group frames into buckets by elapsed time
    buckets: dict = {}
    for f in all_frames:
        idx = int((f.timestamp - shift_start_ts) / bucket_seconds)
        buckets.setdefault(idx, []).append(f)

    avg_eye = []
    avg_blink = []
    for idx in sorted(buckets):
        bucket = buckets[idx]
        avg_eye.append(round(sum(f.eye_openness for f in bucket) / len(bucket), 3))
        avg_blink.append(round(sum(f.blink_rate for f in bucket) / len(bucket), 1))

    return ShiftTrend(
        shift_id=shift_id,
        trend_bucket_minutes=bucket_minutes,
        sample_count=len(all_frames),
        yawn_count_total=yawn_total,
        intervention_count=0,  # orchestrator updates this after each intervention
        avg_eye_openness_trend=avg_eye,
        avg_blink_rate_trend=avg_blink,
    )
