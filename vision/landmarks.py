"""Facial landmark detection via MediaPipe FaceMesh; returns raw landmark coordinates per frame."""

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class FaceLandmarkExtractor:
    def __init__(self, model_path):
        self.model_path = model_path
        self.base_options = python.BaseOptions(model_asset_path=self.model_path)
        self.flmk
        self.options = vision.FaceLandmarkerOptions(base_options=self.base_options, num_faces=1)
        self.extractor = vision.FaceLandmarker.create_from_options(self.options)

    def __call__(self, frame):
        # Convert BGR to RGB as MediaPipe expects RGB input
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_result = self.extractor.detect(rgb_frame)
        if mp_result.face_landmarks:
            return mp_result.face_landmarks[0]  # return landmarks for the first detected face
        else:
            return None
