import json
import os

# Fallback values used if config.json is missing a key, missing entirely,
# or fails to parse.
DEFAULT_CONFIG = {
    "use_voice_mode": False,
    "stt_model_path": "models/vosk-model-small-en-us-0.15",
    "wake_words": ["hello wednesday", "hi wednesday", "wednesday"]
}


def load_config(path="config.json"):
    """
    Loads config.json and merges it over DEFAULT_CONFIG, so a missing file
    or a partially-filled-in file still produces a complete, usable config.
    """
    config = DEFAULT_CONFIG.copy()

    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                user_config = json.load(f)
            config.update(user_config)
        except json.JSONDecodeError as e:
            print(f"[Warning] config.json is malformed, using defaults: {e}")
    else:
        print(f"[Warning] {path} not found, using default config.")

    return config