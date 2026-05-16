"""Camera / RTSP stream ingestion: open device, yield raw BGR frames at target FPS."""
import cv2
import time

class MediaCapture:
    def __init__(self, source=0)
        
class CameraCapture:
    def __init__(self, source=0, target_fps=30):
        self.source = source
        self.target_fps = target_fps
        self.capture = None
        cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
        if not cap.isOpened():
            raise ValueError(f"Unable to open video source: {self.source}")
        
        while True:
            ok, frame = cap.read()
            if not ok:
                print(f"Failed to read from source: {self.source}")
                break
        
            cv2.imshow("Camera:", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()


class RTSPCapture:
    def __init__(self, stream_path):
        self.stream_path = stream_path