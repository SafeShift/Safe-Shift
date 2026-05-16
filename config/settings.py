"""Load environment variables and expose typed settings + intervention threshold constants.

Typed constants to expose (stub — implement by loading config/defaults.yaml + .env):
  # Thresholds (from defaults.yaml)
  SEVERITY_ESCALATION_MINUTES: float   # key: severity_escalation_minutes
  ANALYSIS_WINDOW_SEC: float           # key: analysis_window_sec
  RECENT_WINDOW_MINUTES: float         # key: recent_window_minutes
  EYE_OPENNESS_DROOPY: float           # key: thresholds.eye_openness_droopy
  BLINK_RATE_LOW: float                # key: thresholds.blink_rate_low
  BLINK_RATE_HIGH: float               # key: thresholds.blink_rate_high
  YAWN_FREQUENCY_ALERT: float          # key: thresholds.yawn_frequency_alert
  GAZE_OFF_FORWARD_SEC: float          # key: thresholds.gaze_off_forward_sec
  # Env vars (from .env)
  DRIVER_ID: str
  CAMERA_INDEX: int
  NEMOTRON_API_KEY: str
  NEMOTRON_BASE_URL: str
"""
