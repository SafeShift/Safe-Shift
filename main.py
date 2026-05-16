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


def _start_vision_pipeline(config, output_queue, frame_callback=None) -> threading.Thread:
    """Start VisionPipeline in a daemon thread.

    output_queue receives (frame_bgr, FrameAnalysis) tuples on every captured frame.
    frame_callback is called on every frame for full-fps MJPEG display (optional).
    """
    pipeline = VisionPipeline(config)

    def _run_with_logging():
        try:
            pipeline.run(output_queue, frame_callback=frame_callback)
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

    # Load driver baseline for adaptive dispatch thresholds
    from memory.driver_baseline import get_baseline
    baseline = get_baseline(driver_id, store)
    logger.info("Baseline loaded  blink_rate=%.1f eye_openness=%.3f",
                baseline.avg_blink_rate, baseline.avg_eye_openness)

    # JOSH — api/server.py: FastAPI server for frontend SSE stream
    _start_api_server(config)

    # Resolve frame_callback for full-fps MJPEG feed
    try:
        from api.video import set_frame as _frame_callback
    except ImportError:
        _frame_callback = None

    # CALEB — vision/pipeline.py: runs in its own thread
    # output_queue receives (frame_bgr, FrameAnalysis) pairs on every captured frame
    output_queue = queue.Queue(maxsize=30)
    _start_vision_pipeline(config, output_queue, frame_callback=_frame_callback)

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
    def _heartbeat_loop():
        import sys
        try:
            n = 0
            while not _shutdown.is_set():
                n += 1
                names = [t.name for t in threading.enumerate()]
                vision = "alive" if "vision-pipeline" in names else "DEAD"
                print(
                    f"[hb#{n}] vision={vision} output_q={output_queue.qsize()} threads={names}",
                    flush=True, file=sys.stderr,
                )
                time.sleep(2)
        except Exception as exc:
            print(f"[HEARTBEAT CRASHED] {exc}", flush=True, file=sys.stderr)

    threading.Thread(target=_heartbeat_loop, name="heartbeat", daemon=True).start()
    print("[main] heartbeat thread launched", flush=True)

    # ── Main loop ─────────────────────────────────────────────────────────────
    # Each iteration processes one (frame_bgr, FrameAnalysis) pair from output_queue.
    #
    # Always:   publish "frame" SSE event to dashboard
    # Adaptive: call orchestrator only on trigger events (sparse mode) or every
    #           dense_mode_interval_sec when rolling stats have been elevated for
    #           dense_mode_window_sec (dense mode).
    # VLM:      fire assess_frame() every VLM_INTERVAL_SEC in a background thread.
    # ─────────────────────────────────────────────────────────────────────────

    t_dense      = getattr(config.thresholds, "dense_mode_window_sec",   20.0)
    t_interval   = getattr(config.thresholds, "dense_mode_interval_sec", 2.0)
    t_droopy     = getattr(config.thresholds, "eye_openness_droopy",      0.45)
    t_blink_high = getattr(config.thresholds, "blink_rate_high",          1.50)
    MIN_TRIGGER_SEC = 3.0  # minimum seconds between trigger-mode orchestrator calls

    latest_vlm: list = [None]
    vlm_thread: threading.Thread = None
    last_vlm_time   = 0.0
    last_orch_time  = 0.0
    elevated_since  = None
    cycle_count     = 0

    try:
        from api.events import publish as _publish_event
    except ImportError:
        _publish_event = None

    logger.info("SafeShift running. Ctrl-C to stop.")
    print("[main] entering main loop", flush=True)

    try:
        while not _shutdown.is_set():

            # Block until next (frame, analysis) pair arrives
            try:
                frame_bgr, frame_analysis = output_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            cycle_count += 1
            now = time.time()

            # ── Always: publish live metrics to dashboard (Panel 1) ──────────
            if _publish_event is not None:
                try:
                    _publish_event("frame", {
                        "timestamp":      frame_analysis.timestamp,
                        "driver_id":      frame_analysis.driver_id,
                        "eye_openness":   frame_analysis.eye_openness,
                        "blink_rate":     frame_analysis.blink_rate,
                        "yawn_detected":  frame_analysis.yawn_detected,
                        "gaze_direction": frame_analysis.gaze_direction,
                    })
                except Exception:
                    pass

            # ── VLM: fire every VLM_INTERVAL_SEC ────────────────────────────
            if (now - last_vlm_time) >= VLM_INTERVAL_SEC:
                if vlm_thread is None or not vlm_thread.is_alive():
                    latest_vlm = [None]
                    vlm_thread = threading.Thread(
                        target=_fire_vlm_async,
                        args=(frame_bgr, driver_id, now, shift_id, latest_vlm),
                        name="vlm-assess",
                        daemon=True,
                    )
                    vlm_thread.start()
                    last_vlm_time = now

            # ── Adaptive orchestrator dispatch ───────────────────────────────
            stats_elevated = (
                frame_analysis.blink_rate > t_blink_high * baseline.avg_blink_rate
                or frame_analysis.eye_openness < t_droopy
            )
            if stats_elevated:
                if elevated_since is None:
                    elevated_since = now
            else:
                elevated_since = None

            in_dense_mode = (
                elevated_since is not None
                and (now - elevated_since) >= t_dense
            )
            trigger_event = (
                frame_analysis.yawn_detected
                or frame_analysis.gaze_direction != "forward"
                or frame_analysis.eye_openness < t_droopy
            )
            should_run = (
                (in_dense_mode and (now - last_orch_time) >= t_interval)
                or (not in_dense_mode and trigger_event and (now - last_orch_time) >= MIN_TRIGGER_SEC)
            )

            if should_run:
                mode_label = "dense" if in_dense_mode else "trigger"
                logger.info("cycle %d — orchestrator (%s)  eye=%.3f blinks=%.1f yawn=%s gaze=%s",
                            cycle_count, mode_label,
                            frame_analysis.eye_openness, frame_analysis.blink_rate,
                            frame_analysis.yawn_detected, frame_analysis.gaze_direction)
                try:
                    orchestrator.run_cycle(
                        frame=frame_analysis,
                        shift_id=shift_id,
                        shift_start=shift_start,
                        vlm_assessment=latest_vlm[0],
                    )
                    last_orch_time = now
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
