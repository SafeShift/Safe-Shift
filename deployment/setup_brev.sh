#!/usr/bin/env bash
# Bootstrap script for NVIDIA Brev GPU instance.
# Installs Python deps, CUDA-compatible OpenCV build, and any GPU-specific packages.
# TODO: add CUDA toolkit version pin and any GPU-specific mediapipe/onnx packages.
set -euo pipefail

pip install --upgrade pip
pip install -r requirements.txt

echo "SafeShift environment ready."
