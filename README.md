# Wednesday

A personal, offline desktop AI assistant for Windows — built with Python and PyQt6.

Wednesday listens for its wake word, shows an animated translucent HUD, replies out loud with offline neural text-to-speech, and can control application windows and manage a to-do list.

> **Speech recognition is fully local.** Wake-word detection (a custom-trained openWakeWord model) and command transcription (faster-whisper) both run entirely on-device — no cloud speech API involved.

---

## Features

- 🎙️ **Local wake-word activation** — a custom-trained openWakeWord model listens continuously and triggers on "Hey Wednesday" / "Hi Wednesday" / "Hello Wednesday", fully offline
- 🗣️ **Local command transcription** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (`base.en`, int8) transcribes your command on CPU the instant the wake word fires. For better performance `base.en` can be swithed with `small.en` by updating `whisper_model_size` in `config.json`
- 🔌 **Self-healing microphone handling** — automatically detects audio-device disconnects/reassignments and reinitializes the input stream without crashing or requiring a restart
- 🪟 **Animated HUD** — a borderless, translucent, always-on-top orb rendered entirely with native PyQt6 drawing
- 🔊 **Offline neural text-to-speech** — powered by [Piper](https://github.com/OHF-Voice/piper1-gpl)
- 🖥️ **Window automation** — open, close, minimize, maximize, focus, and show-desktop for any app
- ✅ **To-do list** — add, read, and clear tasks by number or by name, with typo-tolerant, word-order-independent matching
- ⌨️ **Text mode or 🎤 voice mode** — one setting in `config.json`, no code changes
- 📝 **Rotating debug log** — technical detail stays out of the terminal but is captured to `wednesday_debug.log`

---

## How it works

- **Action Registry pattern** — `core/brain.py` never hardcodes `if/elif` branches for what to do. Every capability is a small class in `actions/`, mapped to one or more trigger words in a single registry.
- **Standardized returns** — every action handler returns `(voice_reply, debug_log)`, so the brain can speak the first and log the second the same way for every feature.
- **Two-stage local speech pipeline** — `core/stt.py` runs openWakeWord continuously (`listen_passive`) until your wake word clears its confidence threshold, then switches to an active capture window (`listen_active`) that records until ~1.2s of silence or a 6-second cap, and hands the audio to faster-whisper for transcription. If the microphone drops out mid-listen, the brain catches it, shows a "HARDWARE SYNC" HUD state, and reinitializes PyAudio automatically.
- **Thread-safe GUI** — Qt widgets must live on the main thread, so the assistant's listen/route loop runs on a background daemon thread instead, and a signal bridge (`GUIBridge`) is the *only* channel between the two. Nothing touches a Qt widget from the wrong thread.

```
core/brain.py (background thread)  --signals-->  core/gui.py (main thread)
        |
        v
  core/stt.py (wake word + transcription)  -->  action_registry  -->  actions/*.py  -->  (voice_reply, debug_log)  -->  core/tts.py
```

---

## Project structure

```
Wednesday/
├── main.py                          # Entry point
├── config.json                      # User settings (voice mode, wake words, STT config)
├── requirements.txt
├── wednesday-wakeup-v1.ipynb        # Kaggle notebook: trains a custom openWakeWord wake-word model
├── data/
│   └── todo.json                    # Task storage (auto-created on first run)
├── models/
│   ├── wednesday.onnx                     # Custom-trained openWakeWord wake-word model
│   ├── wednesday_training_history.json    # Training metrics for the wake-word model
│   ├── melspectrogram.onnx                # openWakeWord shared mel-spectrogram feature extractor
│   ├── embedding_model.onnx               # openWakeWord shared audio embedding model
│   ├── en_US-lessac-medium.onnx           # Piper voice model
│   └── en_US-lessac-medium.onnx.json      # Piper voice config
├── core/
│   ├── brain.py                     # Central logic router / action dispatcher
│   ├── config.py                    # Loads config.json with sane defaults
│   ├── gui.py                       # Animated translucent HUD (PyQt6)
│   ├── logger.py                    # Rotating file logger
│   ├── stt.py                       # openWakeWord wake-word detection + faster-whisper transcription
│   └── tts.py                       # Offline neural TTS (Piper)
└── actions/
    ├── windows_manager.py           # OS window automation
    └── todo_list.py                 # JSON-backed to-do list
```

---

## Requirements

- Windows 10/11
- Python 3.12+
- A Piper voice model (for text-to-speech)
- A trained openWakeWord wake-word model — `models/wednesday.onnx` ships pre-trained; see [Training your own wake word](#training-your-own-wake-word) to make your own
- ~500MB free disk space for faster-whisper's `small.en/base.en` model, which downloads automatically the first time voice mode runs (cached locally after that)

---

## Setup

1. **Clone the repo and install dependencies**
   ```
   git clone https://github.com/Ujjwals-GHub/Wednesday
   cd Wednesday
   pip install -r requirements.txt
   ```
   > `pyaudio` sometimes needs a prebuilt wheel on Windows rather than a plain `pip install`, since it links against the PortAudio C library. If it fails, search "pyaudio windows wheel" for your Python version.

2. **Configure `config.json`**
   ```json
   {
       "use_voice_mode": false,
       "wake_word_model_path": "models/wednesday.onnx",
       "wake_word_threshold": 0.5,
       "whisper_model_size": "base.en",
       "whisper_compute_type": "int8",
       "wake_words": ["hello wednesday", "hi wednesday", "hey wednesday"]
   }
   ```
   > `melspec_model_path` and `embedding_model_path` don't need to be set explicitly — they default to `models/melspectrogram.onnx` and `models/embedding_model.onnx`.

3. **Run it**
   ```
   python main.py
   ```

---

## Configuration reference

| Key | Type | Description |
|---|---|---|
| `use_voice_mode` | bool | `false` = type commands in the terminal. `true` = speak them into your microphone (openWakeWord + faster-whisper). |
| `wake_word_model_path` | str | Path to the custom openWakeWord `.onnx` wake-word model. |
| `wake_word_threshold` | float | Confidence score (0–1) the wake-word model must clear before it counts as a detection. Default `0.5`. |
| `melspec_model_path` | str | Path to openWakeWord's shared mel-spectrogram feature-extraction model. Optional — has a sensible default. |
| `embedding_model_path` | str | Path to openWakeWord's shared audio embedding model. Optional — has a sensible default. |
| `whisper_model_size` | str | faster-whisper model size used to transcribe commands after the wake word fires. Default `base.en`. |
| `whisper_compute_type` | str | faster-whisper compute precision. Default `int8` (CPU-friendly). |
| `wake_words` | list[str] | Phrases that activate the assistant in text mode. Prefer multi-word phrases (`"hey wednesday"`) over a bare name to cut down on false triggers from everyday speech. |

---

## Usage

**Text mode** — type a command starting with a wake word:
```
[Terminal] Type your command: wednesday open chrome
[Terminal] Type your command: wednesday add buy milk to my list
[Terminal] Type your command: wednesday what's on my list
[Terminal] Type your command: wednesday remove task 2
[Terminal] Type your command: wednesday stop
```

**Voice mode** — say a wake word, wait for the HUD to appear, then speak your command. Recording stops automatically after about 1.2 seconds of silence, or after 6 seconds, whichever comes first.

### Built-in commands

| Category | Say things like... |
|---|---|
| Open/launch an app | "open chrome", "launch spotify" |
| Close an app | "close chrome", "kill spotify" |
| Minimize / maximize | "minimize chrome", "maximize spotify" |
| Focus a window | "bring chrome to the top" |
| Show desktop | "go to desktop" |
| Add a task | "add buy milk to my list", "remember to call mom" |
| Read tasks | "what's on my list", "tell me my task 2" |
| Remove a task | "remove task 2", "clear buy milk", "delete everything" |
| Shut down the assistant | "stop", "shut down" |

---

## Training your own wake word

`models/wednesday.onnx` was trained with `wednesday-wakeup-v1.ipynb`, an end-to-end openWakeWord training pipeline designed to run on [Kaggle Notebooks](https://www.kaggle.com/) (free GPU tier).

The pipeline:
1. Synthesizes thousands of positive/negative TTS clips of your wake phrase(s) with `piper-sample-generator`.
2. Augments them with room impulse responses (MIT IR dataset) and real-world background noise (FMA).
3. Extracts audio features and trains a small classifier, validating against openWakeWord's ACAV100M hard-negative set to keep false positives low.
4. Ensembles the best checkpoints and exports a single `.onnx` model plus a `*_training_history.json` metrics file.

To train your own:
1. Open the notebook on Kaggle → under Settings, set **Accelerator: GPU T4 x2** and **Internet: On** *before* running any cell.
2. Edit `TARGET_PHRASE` in the training-config cell to your desired phrase(s).
3. Run all cells (roughly 1–1.5 hours of active compute, plus 20–40 minutes of downloads).
4. Click **Save Version → Save & Run All (Commit)**, then download the resulting `.onnx` and `_training_history.json` from the notebook's Output tab.
5. Drop the `.onnx` into `models/`, point `wake_word_model_path` in `config.json` at it, and update `wake_words` to match.

---

## Known limitations

- Windows-only — uses `winsound` for audio playback, PowerShell for the show-desktop trick, and `AppOpener`/`PyGetWindow` for window control.
- Voice-mode command capture is capped at 6 seconds per utterance (cut short after ~1.2s of silence) — built for quick commands, not long-form dictation.
- On its very first run, voice mode downloads the faster-whisper `base.en` model (a few hundred MB) if it isn't already cached locally. After that, voice mode runs fully offline like everything else.

---

## Roadmap

- 🧠 Wednesday is learning new tricks — more actions are being cooked.

- open an issue if you have ideas.

---

## License

MIT
