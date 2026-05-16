"""SQLite connection and table initialization for SafeShift local memory."""
import sqlite3


class MemoryStore:
    """Manages the SQLite connection for all memory modules.

    Constructed once in main.py and passed to all memory functions.
    Calling __init__ immediately creates the tables if they don't exist.
    """

    def __init__(self, config):
        self._db_path = config.driver.db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.get_connection() as conn:
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
