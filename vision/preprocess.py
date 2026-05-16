"""Frame preprocessing: resize, normalize, and crop to face ROI before landmark detection."""
import mediapipe as mp
import cv2

def preprocess(frame):
    """
    Preprocess raw BGR frame for landmark detection.
    """
    frame = cv2.flip(frame, 1)  # horizontal flip (mirror)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)