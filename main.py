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

import threading

import config
from vision import pipeline


def main(config):
    # 1. Read driver_id from config/environment
    driver_id = get_driver_id_from_config()

    # 2. Generate shift_id and record shift_start timestamp
    shift_id = generate_shift_id()
    shift_start = time.time()

    # 3. Call start_shift() to initialize memory for the new shift
    start_shift(shift_id, driver_id, shift_start)

    # 4. Start the FastAPI server as a background thread
    start_api_server()

    # 5. Start vision pipeline and process FrameAnalysis results
    frame_queue = queue.Queue(maxsize=5)  # for visualization/debugging
    analysis_queue = queue.Queue(maxsize=5)  # for FrameAnalysis results

    vision_thread = threading.Thread(target=pipeline.run, args=(frame_queue, analysis_queue), daemon=True)
    vision_thread.start()
    try:
        vision_pipeline = pipeline.VisionPipeline(config)
        vision_pipeline.run(frame_queue, analysis_queue)
    except KeyboardInterrupt:
        pass
    finally:
        # On exit, call end_shift() to trigger DriverBaseline update
        end_shift(shift_id)


if __name__ == "__main__":
    # parse args
    main(config)