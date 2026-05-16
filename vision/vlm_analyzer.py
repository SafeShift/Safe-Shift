"""VLM fatigue analysis subagent using Nemotron-3-Nano-Omi.

Sends a raw camera frame to the Nemotron-3-Nano-Omi vision-language model and receives a
structured VLMFrameAssessment describing fatigue cues in natural language plus a numeric
score. Runs alongside the MediaPipe pipeline — MediaPipe provides fast landmark metrics,
the VLM provides richer semantic scene understanding (head tilt, micro-expressions, posture).
Called by vision/pipeline.py on a slower cadence (e.g. every 10 s) to avoid inference cost.
"""
