"""Compute fatigue signals from MediaPipe Face Mesh landmarks.

FaceFeatureExtractor ingests the per-frame landmark list (478 points, normalized 0–1)
and produces scalar metrics that feed FrameAnalysis:

  - eye_openness      : Eye Aspect Ratio (EAR), averaged across both eyes, 0–1
  - blink_detected    : True when EAR drops below threshold for this frame
  - yawn_detected     : True when mouth aspect ratio (MAR) exceeds threshold
  - gaze_direction    : "forward" | "left" | "right" | "up" | "down"
  - gaze_deviation_px : pixel offset of iris center from eye center

Usage
-----
    extractor = FaceFeatureExtractor()
    features = extractor(face_landmarks_list)   # list of 478 NormalizedLandmark
    # features.eye_openness, features.blink_detected, features.yawn_detected, ...

    # For shift-level aggregation, use FeatureAggregator:
    agg = FeatureAggregator(window_sec=2, fps=15)
    for frame_features in window:
        agg.update(frame_features)
    frame_analysis = agg.flush(timestamp, driver_id)
"""

import math
import time
from dataclasses import dataclass
from collections import deque
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# Landmark indices (MediaPipe Face Mesh, 478-point model)
# ──────────────────────────────────────────────────────────────────────────────

# Eye Aspect Ratio (EAR) — 6 points per eye
# Vertical pairs: p2-p6, p3-p5 | Horizontal: p1-p4
_LEFT_EYE_EAR = {
    "p1": 362, "p2": 385, "p3": 387,
    "p4": 263, "p5": 373, "p6": 380,
}
_RIGHT_EYE_EAR = {
    "p1": 33,  "p2": 160, "p3": 158,
    "p4": 133, "p5": 153, "p6": 144,
}

# Mouth Aspect Ratio (MAR) — 8 points
# Vertical pairs: A(13,14), B(82,87), C(312,317) | Horizontal: D(78,308)
_MOUTH_MAR = {
    "top": 13, "bottom": 14,
    "top_left": 82,  "bottom_left": 87,
    "top_right": 312, "bottom_right": 317,
    "left": 78, "right": 308,
}

# Face vector gaze — nose tip relative to face bounding box
_NOSE_TIP    = 1
_LEFT_CHEEK  = 234
_RIGHT_CHEEK = 454
_FOREHEAD    = 10
_CHIN        = 152

# ──────────────────────────────────────────────────────────────────────────────
# Thresholds
# ──────────────────────────────────────────────────────────────────────────────

EAR_BLINK_THRESHOLD  = 0.20  # EAR below this → blink / closed eye
MAR_YAWN_THRESHOLD   = 0.55  # MAR above this → yawn open
GAZE_OFFSET_THRESHOLD = 0.15 # normalised nose offset from face centre; >this = off-forward


# ──────────────────────────────────────────────────────────────────────────────
# Output dataclass
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class FrameFeatures:
    """Per-frame feature vector extracted from landmarks.

    Consumed by FeatureAggregator to produce FrameAnalysis over a rolling window.
    """
    eye_openness: float       # EAR averaged across both eyes, 0.0–1.0
    blink_detected: bool      # EAR dropped below threshold this frame
    yawn_detected: bool       # MAR exceeded threshold this frame
    gaze_direction: str       # "forward" | "left" | "right" | "up" | "down"
    gaze_deviation: float     # normalised distance of iris from eye centre
    confidence: float         # 1.0 if all landmarks present; 0.5 if iris missing


# ──────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ──────────────────────────────────────────────────────────────────────────────

def _dist(a, b) -> float:
    """Euclidean distance between two NormalizedLandmark objects (x, y only)."""
    return math.hypot(a.x - b.x, a.y - b.y)


def _ear(lm, indices: dict) -> float:
    """Eye Aspect Ratio from 6 landmark indices.

    EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
    Returns 0.0 if the horizontal distance is degenerate.
    """
    horiz = _dist(lm[indices["p1"]], lm[indices["p4"]])
    if horiz < 1e-6:
        return 0.0
    vert1 = _dist(lm[indices["p2"]], lm[indices["p6"]])
    vert2 = _dist(lm[indices["p3"]], lm[indices["p5"]])
    return (vert1 + vert2) / (2.0 * horiz)


def _mar(lm, indices: dict) -> float:
    """Mouth Aspect Ratio from 8 landmark indices.

    MAR = (|top-bottom| + |top_left-bottom_left| + |top_right-bottom_right|)
          / (3 * |left-right|)
    """
    horiz = _dist(lm[indices["left"]], lm[indices["right"]])
    if horiz < 1e-6:
        return 0.0
    v1 = _dist(lm[indices["top"]],       lm[indices["bottom"]])
    v2 = _dist(lm[indices["top_left"]],  lm[indices["bottom_left"]])
    v3 = _dist(lm[indices["top_right"]], lm[indices["bottom_right"]])
    return (v1 + v2 + v3) / (3.0 * horiz)


def _gaze(lm, threshold: float):
    """Compute head gaze direction from the face orientation vector.

    Uses the nose tip offset relative to the geometric centre of the face
    (midpoint of left cheek, right cheek, forehead, chin). When the head
    rotates, the nose tip shifts away from that centre — the direction of
    the shift indicates which way the head is facing.

    Offsets are normalised by face width (horizontal) and face height
    (vertical) so the threshold is scale-invariant.

    Returns (direction: str, offset: float).
    """
    nose = lm[_NOSE_TIP]

    face_cx = (lm[_LEFT_CHEEK].x + lm[_RIGHT_CHEEK].x) / 2.0
    face_cy = (lm[_FOREHEAD].y  + lm[_CHIN].y)          / 2.0

    face_w = abs(lm[_LEFT_CHEEK].x - lm[_RIGHT_CHEEK].x)
    face_h = abs(lm[_FOREHEAD].y   - lm[_CHIN].y)

    if face_w < 1e-6 or face_h < 1e-6:
        return "forward", 0.0

    dx = (nose.x - face_cx) / face_w   # positive → nose right of centre → head right
    dy = (nose.y - face_cy) / face_h   # positive → nose below centre   → head down

    offset = math.hypot(dx, dy)

    if offset < threshold:
        direction = "forward"
    elif abs(dx) >= abs(dy):
        direction = "right" if dx > 0 else "left"
    else:
        direction = "down" if dy > 0 else "up"

    return direction, offset


# ──────────────────────────────────────────────────────────────────────────────
# Main extractor
# ──────────────────────────────────────────────────────────────────────────────

class FaceFeatureExtractor:
    """Extract per-frame fatigue features from a single face's landmark list.

    Args:
        ear_blink_threshold: EAR below which the eye is considered closed/blinking.
        mar_yawn_threshold:  MAR above which a yawn is detected.
    """

    def __init__(
        self,
        ear_blink_threshold:   float = EAR_BLINK_THRESHOLD,
        mar_yawn_threshold:    float = MAR_YAWN_THRESHOLD,
        gaze_offset_threshold: float = GAZE_OFFSET_THRESHOLD,
        yawn_open_sec:         float = 2.0,
    ):
        self.ear_blink_threshold   = ear_blink_threshold
        self.mar_yawn_threshold    = mar_yawn_threshold
        self.gaze_offset_threshold = gaze_offset_threshold
        self.yawn_open_sec         = yawn_open_sec
        self._mouth_open_since: Optional[float] = None   # timestamp when mouth opened
        self._yawn_active: bool = False                   # True once threshold met; stays until mouth closes

    def __call__(self, face_landmarks) -> FrameFeatures:
        """Compute features from a single face landmark list (478 NormalizedLandmark).

        Args:
            face_landmarks: iterable of 478 NormalizedLandmark objects (x, y, z attrs).

        Returns:
            FrameFeatures dataclass.
        """
        lm = list(face_landmarks)

        left_ear  = _ear(lm, _LEFT_EYE_EAR)
        right_ear = _ear(lm, _RIGHT_EYE_EAR)
        avg_ear   = (left_ear + right_ear) / 2.0

        mar = _mar(lm, _MOUTH_MAR)

        # Yawn: mouth must stay open for yawn_open_sec to trigger;
        # once triggered, fires continuously until mouth closes.
        now = time.time()
        mouth_open = mar > self.mar_yawn_threshold
        if self._yawn_active:
            # Stay active until mouth closes
            if not mouth_open:
                self._yawn_active = False
                self._mouth_open_since = None
            yawn_detected = self._yawn_active
        else:
            if mouth_open:
                if self._mouth_open_since is None:
                    self._mouth_open_since = now
                if (now - self._mouth_open_since) >= self.yawn_open_sec:
                    self._yawn_active = True
            else:
                self._mouth_open_since = None
            yawn_detected = self._yawn_active

        direction, offset = _gaze(lm, self.gaze_offset_threshold)

        return FrameFeatures(
            eye_openness   = avg_ear,
            blink_detected = avg_ear < self.ear_blink_threshold,
            yawn_detected  = yawn_detected,
            gaze_direction = direction,
            gaze_deviation = offset,
            confidence     = 1.0,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Rolling-window aggregator → FrameAnalysis
# ──────────────────────────────────────────────────────────────────────────────

class FeatureAggregator:
    """Accumulates per-frame FrameFeatures over a rolling window and flushes FrameAnalysis.

    Tracks blink rate (blinks/min), average eye openness, yawn events, and
    dominant gaze direction over the configured window.

    Args:
        window_sec: rolling window duration in seconds (default 2).
        fps:        expected frame rate (used to size the deque buffer).
    """

    def __init__(self, window_sec: float = 2.0, fps: int = 15):
        self.window_sec = window_sec
        self._fps = fps
        maxlen = int(window_sec * fps * 2)  # 2× buffer headroom
        self._frames: deque = deque(maxlen=maxlen)
        self._timestamps: deque = deque(maxlen=maxlen)

        # Blink edge detection state
        self._prev_blink: bool = False
        self._blink_events: deque = deque(maxlen=maxlen)  # timestamps of blink onsets
        self._yawn_events:  deque = deque(maxlen=maxlen)  # timestamps of yawn onsets
        self._prev_yawn: bool = False

    def update(self, features: FrameFeatures, timestamp: Optional[float] = None):
        """Add a new frame's features.

        Args:
            features:  FrameFeatures from FaceFeatureExtractor.
            timestamp: unix epoch; defaults to time.time() if None.
        """
        t = timestamp if timestamp is not None else time.time()
        self._frames.append(features)
        self._timestamps.append(t)

        # Rising-edge blink detection (closed → open transition counts one blink)
        if self._prev_blink and not features.blink_detected:
            self._blink_events.append(t)
        self._prev_blink = features.blink_detected

        # Rising-edge yawn detection
        if not self._prev_yawn and features.yawn_detected:
            self._yawn_events.append(t)
        self._prev_yawn = features.yawn_detected

        # Evict stale events outside rolling window
        cutoff = t - self.window_sec
        while self._blink_events and self._blink_events[0] < cutoff:
            self._blink_events.popleft()
        while self._yawn_events and self._yawn_events[0] < cutoff:
            self._yawn_events.popleft()

    def flush(self, timestamp: float, driver_id: str):
        """Compute aggregated FrameAnalysis from the current window.

        Imports FrameAnalysis from core.models to avoid circular imports.

        Args:
            timestamp:  unix epoch for the output record.
            driver_id:  driver identifier string.

        Returns:
            core.models.FrameAnalysis
        """
        from core.models import FrameAnalysis  # local import to avoid circular dep

        if not self._frames:
            return FrameAnalysis(
                timestamp=timestamp,
                driver_id=driver_id,
                blink_rate=0.0,
                eye_openness=0.0,
                yawn_detected=False,
                yawn_frequency=0.0,
                gaze_direction="forward",
                gaze_deviation_deg=0.0,
                confidence=0.0,
            )

        frames = list(self._frames)
        avg_ear       = sum(f.eye_openness for f in frames) / len(frames)
        avg_conf      = sum(f.confidence   for f in frames) / len(frames)
        any_yawn      = any(f.yawn_detected for f in frames)
        blinks_in_win = len(self._blink_events)
        blink_rate    = blinks_in_win * (60.0 / self.window_sec)   # scale to blinks/min
        yawn_freq     = len(self._yawn_events) * (3600.0 / self.window_sec)  # yawns/hour

        # Dominant gaze direction by vote
        gaze_counts: dict = {}
        for f in frames:
            gaze_counts[f.gaze_direction] = gaze_counts.get(f.gaze_direction, 0) + 1
        dominant_gaze = max(gaze_counts, key=gaze_counts.get)
        avg_deviation = sum(f.gaze_deviation for f in frames) / len(frames)
        # Convert normalised offset to approximate degrees (rough calibration)
        gaze_deg = avg_deviation * 90.0

        return FrameAnalysis(
            timestamp=timestamp,
            driver_id=driver_id,
            blink_rate=round(blink_rate, 2),
            eye_openness=round(avg_ear, 4),
            yawn_detected=any_yawn,
            yawn_frequency=round(yawn_freq, 2),
            gaze_direction=dominant_gaze,
            gaze_deviation_deg=round(gaze_deg, 2),
            confidence=round(avg_conf, 4),
        )
