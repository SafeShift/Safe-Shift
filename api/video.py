"""MJPEG frame store — vision pipeline writes, /video endpoint reads.

Call set_frame(bgr_ndarray) from any thread (vision pipeline thread).
The /video endpoint in api/server.py reads get_jpeg() to stream MJPEG.

Owner: Josh
"""
import threading
from typing import Optional

import cv2
import numpy as np

_lock = threading.Lock()
_jpeg: Optional[bytes] = None


def set_frame(bgr: np.ndarray) -> None:
    """JPEG-encode a BGR frame and store it. Safe to call from any thread."""
    global _jpeg
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if ok:
        with _lock:
            _jpeg = buf.tobytes()


def get_jpeg() -> Optional[bytes]:
    """Return the latest JPEG bytes, or None if no frame has arrived yet."""
    with _lock:
        return _jpeg


def mjpeg_generator():
    """Yield multipart MJPEG chunks for StreamingResponse."""
    import time
    boundary = b"--frame\r\n"
    while True:
        frame = get_jpeg()
        if frame is None:
            time.sleep(0.05)
            continue
        yield (
            boundary
            + b"Content-Type: image/jpeg\r\n\r\n"
            + frame
            + b"\r\n"
        )
        time.sleep(1 / 20)  # cap at 20 fps
