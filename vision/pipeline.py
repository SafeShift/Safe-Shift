"""End-to-end vision pipeline: orchestrates capture → preprocess → landmarks → features → FrameAnalysis output."""

import queue
import time

from vision.capture import MediaCapture

class FrameAnalysis:
    def __init__(self, timestamp, driver_id, features):
        self.timestamp = timestamp
        self.driver_id = driver_id
        self.

class VisionPipeline:
    def __init__(self, config):
        # vision related configs
        self.config = config

        # initialize capture module or RTSP stream
        self.capture = MediaCapture(config.media_source)

        # initialize landmark extractor
        self.flmk_extractor = FaceLandmarkExtractor(config.landmark_model)
        self.flmk_featurizer = FaceFeatureExtractor(config.feature_model)

    def run(self, frame_queue, analysis_queue):
        # main loop to process frames
        for frame in self.capture:
            # preprocess frame (resize, normalize, etc.)
            preprocessed = self.preprocess(frame)

            # extract landmarks (pose, face, hands)
            landmarks = self.flmk_extractor(preprocessed)

            # compute features from landmarks
            features = self.flmk_featurizer(landmarks)

            # output FrameAnalysis results
            frame_analysis = FrameAnalysis( 
                timestamp=time.time(),
                driver_id=self.config.driver_id,
                features=features
            )
            try:
                frame_queue.put_nowait(frame)  # for visualization or debugging
                analysis_queue.put(frame_analysis)
            except queue.Full:
                pass
            