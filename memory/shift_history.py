"""Read and write per-shift session records including FrameAnalysis snapshots and InterventionRecords."""
import json
import time

from core.models import FrameAnalysis, InterventionRecord
from memory.store import get_connection


def init_shift(shift_id: str, driver_id: str) -> None:
    """No-op for SQLite — tables already exist. Called by main.py at shift start."""
    pass


def append_frame(shift_id: str, frame: FrameAnalysis) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO frames (shift_id, driver_id, timestamp, blink_rate, eye_openness,
                                yawn_detected, yawn_frequency, gaze_direction,
                                gaze_deviation_deg, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            shift_id, frame.driver_id, frame.timestamp, frame.blink_rate,
            frame.eye_openness, int(frame.yawn_detected), frame.yawn_frequency,
            frame.gaze_direction, frame.gaze_deviation_deg, frame.confidence,
        ))


def append_intervention(record: InterventionRecord) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO interventions (intervention_id, driver_id, shift_id, timestamp,
                                       severity, intervention_type, action_summary, suggested_stops)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.intervention_id, record.driver_id, record.shift_id, record.timestamp,
            record.severity, record.intervention_type, record.action_summary,
            json.dumps(record.suggested_stops),
        ))


def get_recent_frames(shift_id: str, minutes: int) -> list:
    cutoff = time.time() - (minutes * 60)
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM frames WHERE shift_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """, (shift_id, cutoff)).fetchall()
    return [_row_to_frame(row) for row in rows]


def get_all_frames(shift_id: str) -> list:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM frames WHERE shift_id = ? ORDER BY timestamp ASC
        """, (shift_id,)).fetchall()
    return [_row_to_frame(row) for row in rows]


def get_interventions(shift_id: str) -> list:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM interventions WHERE shift_id = ? ORDER BY timestamp ASC
        """, (shift_id,)).fetchall()
    return [_row_to_intervention(row) for row in rows]


def _row_to_frame(row) -> FrameAnalysis:
    return FrameAnalysis(
        timestamp=row["timestamp"],
        driver_id=row["driver_id"],
        blink_rate=row["blink_rate"],
        eye_openness=row["eye_openness"],
        yawn_detected=bool(row["yawn_detected"]),
        yawn_frequency=row["yawn_frequency"],
        gaze_direction=row["gaze_direction"],
        gaze_deviation_deg=row["gaze_deviation_deg"],
        confidence=row["confidence"],
    )


def _row_to_intervention(row) -> InterventionRecord:
    return InterventionRecord(
        intervention_id=row["intervention_id"],
        driver_id=row["driver_id"],
        shift_id=row["shift_id"],
        timestamp=row["timestamp"],
        severity=row["severity"],
        intervention_type=row["intervention_type"],
        action_summary=row["action_summary"],
        suggested_stops=json.loads(row["suggested_stops"] or "[]"),
    )
