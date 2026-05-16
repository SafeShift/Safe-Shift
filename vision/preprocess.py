"""Frame preprocessing: resize, normalize, and crop to face ROI before landmark detection."""
import mediapipe as mp
import cv2

def preprocess(frame):
    """
    Preprocess raw BGR frame for landmark detection.
    """
    # flip vertically
    frame = cv2.flip(frame, 0)
    # convert to mediapipe Image format (RGB)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)