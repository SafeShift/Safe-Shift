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
    driver_profile = data.get("driver_profile", {})
    demo = data.get("demo", {})
    vision_yaml = data.get("vision", {})

    data["driver"] = {
        # driver_id is int in yaml (0, 1, …); cast to str to match model type annotations
        "driver_id": str(driver_profile.get("driver_id", 0)),
        "driver_name": driver_profile.get("driver_name", "Driver"),
        # DB path stays env-overrideable — path differs per machine (WSL vs Windows)
        "db_path": os.getenv("DB_PATH", "./safeshift.db"),
        "demo_lat": demo.get("demo_lat", 36.9916),
        "demo_lon": demo.get("demo_lon", -122.0583),
    }
    data["vision"] = {
        "flmk_model_path": vision_yaml.get("flmk_model_path", "vision/models/face_landmarker.task"),
        "media_source":    vision_yaml.get("media_source", "camera"),
        "camera_index":    int(vision_yaml.get("camera_index", 0)),
        "image_dir":       vision_yaml.get("image_dir", ""),
        "target_fps":      int(vision_yaml.get("target_fps", 15)),
    }
    data["notifications"] = {
        "ntfy_topic": os.getenv("NTFY_TOPIC", "safeshift-alerts"),
        "ntfy_server": os.getenv("NTFY_SERVER", "https://ntfy.sh"),
        "alert_endpoint": os.getenv("ALERT_ENDPOINT", "http://localhost:8080/alert"),
    }

    return _to_namespace(data)


config = load_config()