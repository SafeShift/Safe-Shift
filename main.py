"""SafeShift process entry point.

Shift lifecycle:
  1. Load config + generate shift_id / shift_start
  2. Start audit recorder (core/audit.py)
  3. Start FastAPI server in background thread (api/server.py)
  4. Initialize memory for the new shift (memory/shift_history.py)
  5. Start VisionPipeline in its own thread → feeds frame_queue + analysis_queue
  6. Main loop: consume analysis_queue every cycle
       - Every ~10 s: fire VLM assessment concurrently (vision/vlm_analyzer.py)
       - Every cycle:  call orchestrator.run_cycle() with latest FrameAnalysis + VLMFrameAssessment
  7. On KeyboardInterrupt / SIGTERM: call end_shift() → update DriverBaseline

Owner: Kevin
"""

import logging
import queue
import signal
import threading
import time
import uuid

from config.settings import load_config
from memory.store import MemoryStore
from llm.client import NemotronClient
from agents.safety import SafetyAgent
from agents.orchestrator import Orchestrator

# ─────────────────────────────────────────────────────────────────────────────
# Optional imports — stubs keep main.py runnable before teammates finish
# Each stub is replaced automatically once the real module exists.
# ─────────────────────────────────────────────────────────────────────────────

# KEVIN — implement core/audit.py
# start_audit_recorder() starts the background JSONL writer + NemoClaw tail thread.
# Call signatures: record_tool_call(), record_api_call(), record_decision()
try:
    from core.audit import start_audit_recorder
except ImportError:
    def start_audit_recorder(): pass

# EMILIO — implement agents/companion.py
# CompanionAgent(config, client) — Emilio's persona agent.
# generate(context, prior_messages, severity) -> CompanionMessage
try:
    from agents.companion import CompanionAgent
except ImportError:
    class CompanionAgent:
        def __init__(self, config, client): pass
        def generate(self, context, prior_messages, severity): return None

# CALEB — implement vision/vlm_analyzer.py
# assess_frame() sends a BGR frame to Nemotron-3-Nano-Omi VLM and returns
# a VLMFrameAssessment (fatigue_score, description, flags, confidence).
# Signature: assess_frame(frame_bgr, driver_id, timestamp, shift_id) -> VLMFrameAssessment
try:
    from vision.vlm_analyzer import assess_frame
except ImportError:
    def assess_frame(frame_bgr, driver_id, timestamp, shift_id): return None

# KEVIN — implement memory/shift_history.py
# init_shift() creates the shift row in SQLite so append_frame() calls succeed.
# Signature: init_shift(shift_id, driver_id, store) -> None
try:
    from memory.shift_history import init_shift
except ImportError:
    def init_shift(shift_id, driver_id, store): pass

# KEVIN — implement memory/driver_baseline.py (already done)
# update_baseline_from_shift() reads this shift's FrameAnalysis rows and
# recalculates the rolling per-driver average, then persists it.
# Signature: update_baseline_from_shift(shift_id, driver_id, store, config) -> None
try:
    from memory.driver_baseline import update_baseline_from_shift
except ImportError:
    def update_baseline_from_shift(shift_id, driver_id, store, config): pass

# JOSH — implement api/server.py
# FastAPI app exposing GET / (frontend), GET /stream (SSE), GET /state.
# uvicorn is started in a daemon thread; the app object is imported here.
try:
    import uvicorn
    from api.server import app as fastapi_app
    _HAS_API = True
except Exception as _api_import_err:
    _HAS_API = False
    import logging as _log
    _log.getLogger("main").warning("api/server.py import failed: %s", _api_import_err)

from vision.pipeline import VisionPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# How often to fire a VLM assessment (Nemotron-nano-omi is slower than MediaPipe)
VLM_INTERVAL_SEC = 10.0


# ─────────────────────────────────────────────────────────────────────────────
# Shift lifecycle
# ─────────────────────────────────────────────────────────────────────────────

def start_shift(driver_id: str, store) -> tuple:
    """Generate shift_id + shift_start; create memory row.

    Returns:
        (shift_id: str, shift_start: float)
    """
    shift_id = str(uuid.uuid4())
    shift_start = time.time()
    init_shift(shift_id, driver_id, store)
    logger.info("Shift started  driver=%s  shift_id=%s", driver_id, shift_id)
    return shift_id, shift_start


def end_shift(shift_id: str, driver_id: str, store, config) -> None:
    """Update DriverBaseline from this shift's data and close out."""
    logger.info("Shift ending   driver=%s  shift_id=%s", driver_id, shift_id)
    try:
        update_baseline_from_shift(shift_id, driver_id, store, config)
    except Exception as exc:
        logger.error("end_shift: baseline update failed: %s", exc)
    logger.info("Shift ended.")


# ─────────────────────────────────────────────────────────────────────────────
# Background thread helpers
# ─────────────────────────────────────────────────────────────────────────────

def _start_api_server(config) -> None:
    """Start FastAPI + uvicorn in a daemon thread.

    JOSH — wire api/server.py here. Add api_host / api_port to config if needed.
    """
    if not _HAS_API:
        logger.warning("api/server.py not available — skipping API server")
        return
    host = getattr(config, "api_host", "0.0.0.0")
    port = getattr(config, "api_port", 8080)
    def _run():
        import asyncio
        try:
            cfg = uvicorn.Config(fastapi_app, host=host, port=port, log_level="warning")
            server = uvicorn.Server(cfg)
            server.install_signal_handlers = lambda: None  # can't install in non-main thread
            asyncio.run(server.serve())
        except Exception as exc:
            logger.error("API server thread crashed: %s", exc, exc_info=True)
    t = threading.Thread(target=_run, name="api-server", daemon=True)
    t.start()
    logger.info("API server started on %s:%d", host, port)


def _start_vision_pipeline(config, frame_queue, analysis_queue) -> threading.Thread:
    """Start VisionPipeline in a daemon thread.

    CALEB — VisionPipeline is already implemented in vision/pipeline.py.
    frame_queue  receives raw BGR frames (for VLM sampling + display).
    analysis_queue receives FrameAnalysis objects every analysis_window_sec.
    """
    pipeline = VisionPipeline(config)

    def _run_with_logging():
        try:
            pipeline.run(frame_queue, analysis_queue)
        except Exception as exc:
            logger.error("Vision pipeline thread crashed: %s", exc, exc_info=True)

    t = threading.Thread(target=_run_with_logging, name="vision-pipeline", daemon=True)
    t.start()
    logger.info("Vision pipeline thread started")
    return t


def _fire_vlm_async(frame_bgr, driver_id: str, timestamp: float,
                    shift_id: str, result_holder: list) -> None:
    """Run assess_frame() in a thread; store result in result_holder[0].

    CALEB — once vision/vlm_analyzer.py is implemented, this calls it automatically.
    result_holder[0] is read by the main loop on the next cycle.
    """
    try:
        result_holder[0] = assess_frame(frame_bgr, driver_id, timestamp, shift_id)
    except Exception as exc:
        logger.warning("VLM assessment failed: %s", exc)
        result_holder[0] = None


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    config    = load_config()
    driver_id = config.driver.driver_id
    logger.info("config OK  driver=%s  db=%s  camera=%s",
                driver_id, config.driver.db_path, config.vision.camera_index)

    # ── Construct all agents/services with injected config ────────────────────
    store = MemoryStore(config)
    logger.info("MemoryStore OK  db=%s", store._db_path)

    client = NemotronClient(config)
    logger.info("NemotronClient OK  base_url=%s", config.api.nemotron_base_url)

    safety = SafetyAgent(config, client)
    logger.info("SafetyAgent OK  model=%s", safety._model)

    companion = CompanionAgent(config, client)
    logger.info("CompanionAgent OK")

    orchestrator = Orchestrator(config, safety, companion, store)
    logger.info("Orchestrator OK")

    # KEVIN — core/audit.py: starts background JSONL writer + NemoClaw tail thread
    start_audit_recorder()

    # KEVIN — memory/shift_history.py: creates shift row; returns shift_id + shift_start
    shift_id, shift_start = start_shift(driver_id, store)

    # JOSH — api/server.py: FastAPI server for frontend SSE stream
    _start_api_server(config)

    # CALEB — vision/pipeline.py: runs in its own thread, fills both queues
    frame_queue    = queue.Queue(maxsize=5)   # raw BGR frames (for VLM + display)
    analysis_queue = queue.Queue(maxsize=5)   # FrameAnalysis (one per window)
    _start_vision_pipeline(config, frame_queue, analysis_queue)

    _shutdown = threading.Event()

    def _handle_signal(sig, frame):
        logger.info("Signal %s received — shutting down", sig)
        _shutdown.set()

    # SIGINT (Ctrl-C): let Python's default KeyboardInterrupt propagate —
    # the try/finally below handles cleanup. Overriding it on Windows breaks Ctrl-C.
    try:
        signal.signal(signal.SIGTERM, _handle_signal)  # graceful kill from OS
    except (OSError, ValueError):
        pass  # SIGTERM not available on all Windows configurations

    # ── Independent heartbeat thread ─────────────────────────────────────────
    # Uses print(flush=True) — bypasses any logging buffering on Windows threads.
    def _heartbeat_loop():
        import sys
        try:
            n = 0
            while not _shutdown.is_set():
                n += 1
                names = [t.name for t in threading.enumerate()]
                vision = "alive" if "vision-pipeline" in names else "DEAD"
                print(
                    f"[hb#{n}] vision={vision} frame_q={frame_queue.qsize()} "
                    f"analysis_q={analysis_queue.qsize()} threads={names}",
                    flush=True, file=sys.stderr,
                )
                time.sleep(2)
        except Exception as exc:
            print(f"[HEARTBEAT CRASHED] {exc}", flush=True, file=sys.stderr)

    threading.Thread(target=_heartbeat_loop, name="heartbeat", daemon=True).start()
    print("[main] heartbeat thread launched", flush=True)

    # ── Main loop ─────────────────────────────────────────────────────────────
    # Each iteration:
    #   1. Drain latest raw frame (non-blocking) for VLM
    #   2. Wait for next FrameAnalysis from vision pipeline
    #   3. Every VLM_INTERVAL_SEC: fire assess_frame() in background thread
    #   4. Call orchestrator.run_cycle() — agents run here
    # ─────────────────────────────────────────────────────────────────────────

    latest_vlm: list = [None]          # holds latest VLMFrameAssessment or None
    vlm_thread: threading.Thread = None
    last_vlm_time = 0.0
    latest_frame_bgr = None
    cycle_count = 0

    logger.info("SafeShift running. Ctrl-C to stop.")
    print("[main] entering main loop", flush=True)

    try:
        while not _shutdown.is_set():

            # Drain latest raw frame for VLM + dashboard video feed (non-blocking)
            try:
                latest_frame_bgr = frame_queue.get_nowait()
                from api.video import set_frame as _set_video_frame
                _set_video_frame(latest_frame_bgr)
            except queue.Empty:
                pass

            # Block until next FrameAnalysis arrives (timeout keeps shutdown snappy)
            # KeyboardInterrupt (Ctrl-C) will interrupt this call on all platforms.
            try:
                frame_analysis = analysis_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            cycle_count += 1
            logger.info("cycle %d — FrameAnalysis received  eye=%.3f blinks=%.1f yawn=%s gaze=%s",
                        cycle_count, frame_analysis.eye_openness, frame_analysis.blink_rate,
                        frame_analysis.yawn_detected, frame_analysis.gaze_direction)

            now = time.time()

            # CALEB — vision/vlm_analyzer.py
            # Fire assess_frame() every VLM_INTERVAL_SEC in a background thread.
            # Result lands in latest_vlm[0] and is picked up by run_cycle() next cycle.
            vlm_due = (now - last_vlm_time) >= VLM_INTERVAL_SEC
            if vlm_due and latest_frame_bgr is not None:
                if vlm_thread is None or not vlm_thread.is_alive():
                    latest_vlm = [None]
                    vlm_thread = threading.Thread(
                        target=_fire_vlm_async,
                        args=(latest_frame_bgr, driver_id, now, shift_id, latest_vlm),
                        name="vlm-assess",
                        daemon=True,
                    )
                    vlm_thread.start()
                    last_vlm_time = now

            # KEVIN — agents/orchestrator.py
            # run_cycle() does: build ShiftContext → Safety Agent ReAct loop →
            # optionally Companion Agent → dispatch action handlers → log to memory
            # → publish SSE events to frontend.
            # vlm_assessment is None until the first VLM cycle completes (~10 s in).
            try:
                logger.info("cycle %d — calling orchestrator.run_cycle", cycle_count)
                orchestrator.run_cycle(
                    frame=frame_analysis,
                    shift_id=shift_id,
                    shift_start=shift_start,
                    vlm_assessment=latest_vlm[0],
                )
                logger.info("cycle %d — run_cycle done", cycle_count)
            except Exception as exc:
                logger.error("orchestrator.run_cycle error: %s", exc, exc_info=True)

    except KeyboardInterrupt:
        logger.info("Ctrl-C received — shutting down")
        _shutdown.set()
    finally:
        # KEVIN — memory/driver_baseline.py
        # Recalculates per-driver rolling average from this shift and persists it.
        end_shift(shift_id, driver_id, store, config)
        logger.info("Goodbye.")


if __name__ == "__main__":
    main()
