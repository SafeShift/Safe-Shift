"""Read and write DriverBaseline records; updates rolling averages after each shift."""
import datetime

from core.models import DriverBaseline
from memory.store import MemoryStore
from config.settings import config as _config

_store = MemoryStore(_config)


def update_baseline_from_shift(shift_id: str, driver_id: str, store=None, config=None) -> None:
    store = store or _store
    config = config or _config
    from memory.shift_history import get_all_frames
    frames = get_all_frames(shift_id)
    if not frames:
        return

    existing = get_baseline(driver_id)
    n = len(frames)

    new_baseline = DriverBaseline(
        driver_id=driver_id,
        avg_blink_rate=round(sum(f.blink_rate for f in frames) / n, 2),
        avg_eye_openness=round(sum(f.eye_openness for f in frames) / n, 3),
        avg_yawn_frequency=round(sum(f.yawn_frequency for f in frames) / n, 2),
        shift_count=existing.shift_count + 1,
        last_updated=datetime.datetime.utcnow().isoformat(),
    )
    save_baseline(new_baseline)


def get_baseline(driver_id: str, store=None, config=None) -> DriverBaseline:
    store = store or _store
    config = config or _config
    with store.get_connection() as conn:
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


def save_baseline(baseline: DriverBaseline, store=None) -> None:
    store = store or _store
    with store.get_connection() as conn:
        conn.execute("""
            INSERT INTO baselines (driver_id, avg_blink_rate, avg_eye_openness,
                                   avg_yawn_frequency, shift_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(driver_id) DO UPDATE SET
                avg_blink_rate     = excluded.avg_blink_rate,
                avg_eye_openness   = excluded.avg_eye_openness,
                avg_yawn_frequency = excluded.avg_yawn_frequency,
                shift_count        = excluded.shift_count,
                last_updated       = excluded.last_updated
        """, (
            baseline.driver_id,
            baseline.avg_blink_rate,
            baseline.avg_eye_openness,
            baseline.avg_yawn_frequency,
            baseline.shift_count,
            baseline.last_updated,
        ))
