from core.brain import AssistantBrain
from core.config import load_config

# ==========================================
# MASTER TOGGLE: Text Mode vs Voice Mode
# Flip "use_voice_mode" in config.json — no code edit needed.
# ==========================================

if __name__ == "__main__":
    config = load_config()
    assistant = AssistantBrain(use_voice_mode=config["use_voice_mode"])
    assistant.run()