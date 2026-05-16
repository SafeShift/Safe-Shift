"""End-to-end vision pipeline: capture → landmarks → features → FrameAnalysis.

VisionPipeline.run() is a blocking loop intended to run in its own thread/process.
It writes to two queues consumed by the orchestrator:
  - frame_queue    : raw BGR frames for visualization / VLM sampling
  - analysis_queue : FrameAnalysis objects (one per analysis_window_sec)

Config expected (config.vision namespace):
  media_source, camera_index, image_dir, target_fps,
  flmk_model_path

Config expected (config.driver namespace):
  driver_id

Config expected (config root):
  analysis_window_sec
"""

import queue
import time
import logging

import cv2
from mediapipe import Image, ImageFormat

from vision.capture import MediaCapture
from vision.landmarks import FaceLandmarkExtractor
from vision.features import FaceFeatureExtractor, FeatureAggregator
from vision.preprocess import preprocess

logger = logging.getLogger(__name__)


class VisionPipeline:
    """Orchestrates the full vision stack for one driver session.

    Args:
        config: SimpleNamespace from config.settings.load_config().
                Reads config.vision.* and config.driver.driver_id.
    """

    def __init__(self, config):
        self.config = config
        v = config.vision

        self.driver_id = config.driver.driver_id
        self.window_sec = getattr(config, "analysis_window_sec", 2)

        self.capture = MediaCapture(
            media_source=v.media_source,
            camera_index=v.camera_index,
            image_dir=v.image_dir,
            target_fps=v.target_fps,
        )

        self.landmark_extractor = FaceLandmarkExtractor(model_path=v.flmk_model_path)
        t = config.thresholds
        self.feature_extractor  = FaceFeatureExtractor(
            ear_blink_threshold  =getattr(t, "ear_blink_threshold",   0.20),
            mar_yawn_threshold   =getattr(t, "mar_yawn_threshold",    0.55),
            gaze_offset_threshold=getattr(t, "gaze_offset_threshold", 0.15),
            yawn_open_sec        =getattr(t, "yawn_open_sec",         2.0),
        )
        self.aggregator         = FeatureAggregator(
            window_sec=self.window_sec,
            fps=v.target_fps,
        )

        self._last_flush = time.time()
        logger.info("VisionPipeline initialised (driver=%s, window=%ss)", self.driver_id, self.window_sec)

    def run(self, frame_queue: queue.Queue, analysis_queue: queue.Queue):
        """Main processing loop. Blocks until the capture source is exhausted or the process is killed.

        Args:
            frame_queue:    queue.Queue for raw BGR frames (maxsize recommended: 5).
            analysis_queue: queue.Queue for FrameAnalysis objects.
        """
        _frame_n = 0
        for frame in self.capture:
            time.sleep(0)  # yield GIL so other threads (heartbeat, main) can run
            _frame_n += 1
            timestamp_ms = int(time.time() * 1000)
            now = time.time()

            if _frame_n % 30 == 0:
                logger.info("pipeline: %d frames captured", _frame_n)

            # ── Landmark extraction ──────────────────────────────────────────
            preprocessed = preprocess(frame)
            result   = self.landmark_extractor(preprocessed, timestamp_ms)

            # ── Feature extraction (only when a face is detected) ────────────
            if result.face_landmarks:
                features = self.feature_extractor(result.face_landmarks[0])
                self.aggregator.update(features, timestamp=now)
            else:
                logger.debug("No face detected at t=%.3f", now)

            # ── Push mirrored raw frame for visualization / VLM sampling ──────────────
            try:
                frame_queue.put_nowait(cv2.flip(frame, 1))  # mirror for display
            except queue.Full:
                pass  # drop oldest isn't worth the lock; consumer lags behind

            # ── Flush aggregated FrameAnalysis every window_sec ─────────────
            if now - self._last_flush >= self.window_sec:
                analysis = self.aggregator.flush(timestamp=now, driver_id=self.driver_id)
                try:
                    analysis_queue.put(analysis, timeout=0.5)
                except queue.Full:
                    logger.warning("analysis_queue full — dropping FrameAnalysis at t=%.3f", now)
                self._last_flush = now
                logger.info(
                    "vision: eye=%.3f blinks/min=%.1f yawn=%s gaze=%s conf=%.2f",
                    analysis.eye_openness,
                    analysis.blink_rate,
                    analysis.yawn_detected,
                    analysis.gaze_direction,
                    analysis.confidence,
                )
