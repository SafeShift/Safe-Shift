"""Facial landmark detection via MediaPipe FaceMesh; returns raw landmark coordinates per frame."""
import logging
import mediapipe as mp

class FaceLandmarkExtractor:
    def __init__(self, model_path: str):
        base_options = mp.tasks.BaseOptions(model_asset_path=model_path)
        options = mp.tasks.vision.FaceLandmarkerOptions(base_options=base_options, running_mode=mp.tasks.vision.RunningMode.VIDEO)
        self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        logging.info(f"Initialized FaceLandmarkExtractor with model: {model_path}")

    def __call__(self, img: mp.Image, timestamp_ms: int):
        """
        Run landmark detection on a single frame.

          Args:
              img: mp.Image (RGB)
              timestamp_ms: monotonically increasing timestamp in milliseconds
          Returns:
              FaceLandmarkerResult
          """
        return self.landmarker.detect_for_video(img, timestamp_ms)
