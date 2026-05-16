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

from memory.store import init_db
from memory.driver_baseline import save_baseline
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
    print("Initialising database...")
    init_db()
    print(f"Seeding baseline for '{DRIVER_ID}'...")
    save_baseline(BASELINE)
    print(f"Done. Trucker Tom has {BASELINE.shift_count} shifts on record.")
    print(f"  avg_blink_rate   : {BASELINE.avg_blink_rate}")
    print(f"  avg_eye_openness : {BASELINE.avg_eye_openness}")
    print(f"  avg_yawn_freq    : {BASELINE.avg_yawn_frequency}")


if __name__ == "__main__":
    main()
