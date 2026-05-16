"""Camera / image folder frame ingestion.

Two capture sources, both iterable — yield raw BGR frames at target_fps:
  CameraCapture  — webcam (int index) or RTSP stream (URL string)
  ImageCapture   — cycles through sorted images in a folder (demo / testing)

MediaCapture wraps either source and exposes a single __iter__ interface.
Config drives which is used:
  media_source="camera"        → CameraCapture(camera_index)
  media_source="image"         → ImageCapture(image_dir)
"""

import logging
import time
from pathlib import Path

import cv2

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


class CameraCapture:
    """Webcam or RTSP stream via OpenCV. Yields BGR frames indefinitely."""

    def __init__(self, camera_source=0, target_fps: int = 15):
        """
        Args:
            camera_source: int webcam index (e.g. 0) or str RTSP URL
            target_fps: target frame yield rate
        """
        self.source = camera_source
        self.target_fps = target_fps
        self._cap = cv2.VideoCapture(camera_source)
        if not self._cap.isOpened():
            raise ValueError(f"Cannot open video source: {camera_source}")
        logging.info("CameraCapture opened source: %s", camera_source)

    def __iter__(self):
        interval = 1.0 / self.target_fps
        while True:
            ret, frame = self._cap.read()
            if not ret:
                logging.warning("CameraCapture: failed to read frame, retrying")
                time.sleep(0.1)
                continue
            yield frame
            time.sleep(interval)

    def __del__(self):
        if hasattr(self, "_cap") and self._cap.isOpened():
            self._cap.release()


class ImageCapture:
    """Yields BGR frames from sorted image files in a folder. Loops by default."""

    def __init__(self, image_dir: str, target_fps: int = 15, loop: bool = True):
        """
        Args:
            image_dir: path to folder containing images
            target_fps: target frame yield rate
            loop: if True, restart from first image after exhausting folder
        """
        self.image_dir = Path(image_dir)
        self.target_fps = target_fps
        self.loop = loop
        self._files = sorted(
            p for p in self.image_dir.iterdir()
            if p.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if not self._files:
            raise ValueError(f"No supported images found in: {image_dir}")
        logging.info("ImageCapture loaded %d images from: %s", len(self._files), image_dir)

    def __iter__(self):
        interval = 1.0 / self.target_fps
        while True:
            for path in self._files:
                frame = cv2.imread(str(path))
                if frame is None:
                    logging.warning("ImageCapture: could not read %s, skipping", path)
                    continue
                yield frame
                time.sleep(interval)
            if not self.loop:
                break


class MediaCapture:
    """Wraps CameraCapture or ImageCapture based on media_source config value."""

    def __init__(self, media_source: str = "camera", camera_index: int = 0,
                 image_dir: str = "", target_fps: int = 15):
        """
        Args:
            media_source: "camera" or "image"
            camera_index: webcam device index (used when media_source="camera")
            image_dir: path to image folder (used when media_source="image")
            target_fps: target frame yield rate
        """
        if media_source == "camera":
            self.capture = CameraCapture(camera_source=camera_index, target_fps=target_fps)
        elif media_source == "image":
            self.capture = ImageCapture(image_dir=image_dir, target_fps=target_fps)
        else:
            raise ValueError(f"Unsupported media_source: {media_source!r}. Use 'camera' or 'image'.")

    def __iter__(self):
        return iter(self.capture)
