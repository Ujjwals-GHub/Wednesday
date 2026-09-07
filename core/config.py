import json
import os

DEFAULT_CONFIG = {
    "use_voice_mode": False,
    "wake_word_model_path": "models/wednesday.onnx",
    "wake_word_threshold": 0.5,
    "whisper_model_size": "small.en",
    "whisper_compute_type": "int8",
    "wake_words": ["hello wednesday", "hi wednesday", "wednesday"]
}

def load_config(path="config.json"):
    """
    Loads config.json and merges it over DEFAULT_CONFIG.
    Ensures missing files or keys fallback gracefully to stable defaults.
    """
    config = DEFAULT_CONFIG.copy()

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            config.update(user_config)
        except json.JSONDecodeError as e:
            print(f"[Warning] config.json is malformed, using defaults: {e}")
    else:
        print(f"[Warning] {path} not found, using default config.")

    return config
