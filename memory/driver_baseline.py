"""Read and write DriverBaseline records; updates rolling averages after each shift."""
import datetime

from config.settings import config
from core.models import DriverBaseline
from memory.store import get_connection


def get_baseline(driver_id: str) -> DriverBaseline:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM baselines WHERE driver_id = ?", (driver_id,)
        ).fetchone()

    if row is None:
        return DriverBaseline(
            driver_id=driver_id,
            avg_blink_rate=config.driver_baseline_defaults.avg_blink_rate,
            avg_eye_openness=config.driver_baseline_defaults.avg_eye_openness,
            avg_yawn_frequency=config.driver_baseline_defaults.avg_yawn_frequency,
            shift_count=0,
            last_updated=datetime.datetime.utcnow().isoformat(),
        )

    return DriverBaseline(
        driver_id=row["driver_id"],
        avg_blink_rate=row["avg_blink_rate"],
        avg_eye_openness=row["avg_eye_openness"],
        avg_yawn_frequency=row["avg_yawn_frequency"],
        shift_count=row["shift_count"],
        last_updated=row["last_updated"],
    )


def save_baseline(baseline: DriverBaseline) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO baselines (driver_id, avg_blink_rate, avg_eye_openness,
                                   avg_yawn_frequency, shift_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(driver_id) DO UPDATE SET
                avg_blink_rate   = excluded.avg_blink_rate,
                avg_eye_openness = excluded.avg_eye_openness,
                avg_yawn_frequency = excluded.avg_yawn_frequency,
                shift_count      = excluded.shift_count,
                last_updated     = excluded.last_updated
        """, (
            baseline.driver_id,
            baseline.avg_blink_rate,
            baseline.avg_eye_openness,
            baseline.avg_yawn_frequency,
            baseline.shift_count,
            baseline.last_updated,
        ))
