"""SQLite connection and table initialization for SafeShift local memory."""
import sqlite3

from config.settings import load_config


def get_connection() -> sqlite3.Connection:
    config = load_config()
    conn = sqlite3.connect(config.driver.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id TEXT NOT NULL,
                driver_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                blink_rate REAL,
                eye_openness REAL,
                yawn_detected INTEGER,
                yawn_frequency REAL,
                gaze_direction TEXT,
                gaze_deviation_deg REAL,
                confidence REAL
            );

            CREATE TABLE IF NOT EXISTS interventions (
                intervention_id TEXT PRIMARY KEY,
                driver_id TEXT NOT NULL,
                shift_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                severity TEXT,
                intervention_type TEXT,
                action_summary TEXT,
                suggested_stops TEXT
            );

            CREATE TABLE IF NOT EXISTS baselines (
                driver_id TEXT PRIMARY KEY,
                avg_blink_rate REAL,
                avg_eye_openness REAL,
                avg_yawn_frequency REAL,
                shift_count INTEGER,
                last_updated TEXT
            );
        """)

# init_db() is called explicitly from main.py after config is loaded.
# Do NOT call it here — importing this module must be side-effect free.
