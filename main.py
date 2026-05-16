"""Process entry point for SafeShift.

Responsibilities:
- Read driver_id from config/environment.
- Generate shift_id (uuid4) and record shift_start timestamp.
- Call start_shift() to initialize memory for the new shift.
- Start vision/pipeline.run_pipeline() and feed FrameAnalysis objects into the
  agent/orchestrator loop for the duration of the shift.
- On exit (KeyboardInterrupt, signal, or shift-end condition), call end_shift() to
  trigger the DriverBaseline update via memory/driver_baseline.py.

Owner: Kevin (agent/)
"""
