"""Seed the SQLite database with a realistic driver baseline for the demo.

Run this once before the demo to make sure "Trucker Tom" has established history.
Safe to re-run — uses upsert so it won't duplicate records.

Usage:
    python -m demo.seed_db
"""
import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import os
import sqlite3
import datetime
from core.models import DriverBaseline

DRIVER_ID = "Trucker Tom"

# Realistic baseline for an experienced long-haul driver across 8 prior shifts
BASELINE = DriverBaseline(
    driver_id=DRIVER_ID,
    avg_blink_rate=16.2,        # healthy ~15-20 blinks/min
    avg_eye_openness=0.74,      # fully alert reference
    avg_yawn_frequency=1.1,     # occasional yawn, not fatigued
    shift_count=8,
    last_updated=datetime.datetime.utcnow().isoformat(),
)


def main():
    db_path = os.getenv("DB_PATH", "./safeshift.db")
    print(f"Initialising database at {db_path}...")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS baselines (
            driver_id TEXT PRIMARY KEY,
            avg_blink_rate REAL, avg_eye_openness REAL,
            avg_yawn_frequency REAL, shift_count INTEGER, last_updated TEXT
        )
    """)
    conn.execute("""
        INSERT INTO baselines VALUES (?,?,?,?,?,?)
        ON CONFLICT(driver_id) DO UPDATE SET
            avg_blink_rate=excluded.avg_blink_rate,
            avg_eye_openness=excluded.avg_eye_openness,
            avg_yawn_frequency=excluded.avg_yawn_frequency,
            shift_count=excluded.shift_count,
            last_updated=excluded.last_updated
    """, (BASELINE.driver_id, BASELINE.avg_blink_rate, BASELINE.avg_eye_openness,
          BASELINE.avg_yawn_frequency, BASELINE.shift_count, BASELINE.last_updated))
    conn.commit()
    conn.close()
    print(f"Done. Trucker Tom has {BASELINE.shift_count} shifts on record.")
    print(f"  avg_blink_rate   : {BASELINE.avg_blink_rate}")
    print(f"  avg_eye_openness : {BASELINE.avg_eye_openness}")
    print(f"  avg_yawn_freq    : {BASELINE.avg_yawn_frequency}")


if __name__ == "__main__":
    main()
