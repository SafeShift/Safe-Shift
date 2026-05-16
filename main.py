"""Process entry point for SafeShift.

Responsibilities:
- Read driver_id from config/environment.
- Generate shift_id (uuid4) and record shift_start timestamp.
- Call start_shift() to initialize memory for the new shift.
- Start the FastAPI server (api/server.py) as a background thread.
- Start vision/pipeline.run_pipeline() and for each FrameAnalysis:
    - If a VLM cycle is due (every ~10 s), call vision/vlm_analyzer.assess_frame()
      concurrently to get VLMFrameAssessment.
    - Feed both into agents/orchestrator.run_cycle().
- On exit (KeyboardInterrupt or signal), call end_shift() to trigger
  DriverBaseline update via memory/driver_baseline.py.

Owner: Kevin
Imports from: core.models, config.settings, vision.pipeline, vision.vlm_analyzer,
              agents.orchestrator, memory.driver_baseline, memory.shift_history, api.server
"""
