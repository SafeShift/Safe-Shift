"""Load and expose typed config from defaults.yaml and .env."""
import os
from pathlib import Path
from types import SimpleNamespace

import yaml
from dotenv import load_dotenv

load_dotenv()


def _to_namespace(d):
    if isinstance(d, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in d.items()})
    return d


def load_config(path=None):
    if path is None:
        path = Path(__file__).parent / "defaults.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data["api"] = {
        "nemotron_api_key": os.environ["NEMOTRON_API_KEY"],
        "nemotron_base_url": os.getenv("NEMOTRON_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        "nemotron_super_model": os.getenv("NEMOTRON_SUPER_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
        "nemotron_companion_model": os.getenv("NEMOTRON_COMPANION_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
        "nemotron_vlm_model": os.getenv("NEMOTRON_VLM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"),
    }
    data["driver"] = {
        "driver_id": os.getenv("DRIVER_ID", "driver_001"),
        "db_path": os.getenv("DB_PATH", "./safeshift.db"),
        "camera_index": int(os.getenv("CAMERA_INDEX", "0")),
        "demo_lat": float(os.getenv("DEMO_LAT", "36.9916")),
        "demo_lon": float(os.getenv("DEMO_LON", "-122.0583")),
    }
    data["vision"] = {
        "flmk_model_path": data.get("vision", {}).get("flmk_model_path", "vision/models/face_landmarker.task"),
        "media_source": os.getenv("MEDIA_SOURCE", "camera"),
        "camera_index": int(os.getenv("CAMERA_INDEX", "0")),
        "image_dir": os.getenv("IMAGE_DIR", ""),
        "target_fps": int(os.getenv("TARGET_FPS", "15")),
    }
    data["notifications"] = {
        "ntfy_topic": os.getenv("NTFY_TOPIC", "safeshift-alerts"),
        "ntfy_server": os.getenv("NTFY_SERVER", "https://ntfy.sh"),
        "alert_endpoint": os.getenv("ALERT_ENDPOINT", "http://localhost:8080/alert"),
    }

    return _to_namespace(data)

config = load_config()