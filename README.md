# Wednesday

A personal, offline-first desktop AI assistant for Windows — built with Python and PyQt6.

Wednesday listens for its wake word, shows an animated translucent HUD, replies out loud with offline neural text-to-speech, and can control application windows and manage a to-do list.

---

## Features

- 🎙️ **Wake-word activation** — "Wednesday", "Hi Wednesday", "Hello Wednesday", "Hey Wednesday"
- 🪟 **Animated HUD** — a borderless, translucent, always-on-top orb rendered entirely with native PyQt6 drawing
- 🗣️ **Offline neural text-to-speech** — powered by [Piper](https://github.com/OHF-Voice/piper1-gpl)
- 🖥️ **Window automation** — open, close, minimize, maximize, focus, and show-desktop for any app
- ✅ **To-do list** — add, read, and clear tasks by number or by name, with typo-tolerant, word-order-independent matching
- ⌨️ **Text mode or 🎤 voice mode** — one setting in `config.json`, no code changes
- 📝 **Rotating debug log** — technical detail stays out of the terminal but is captured to `wednesday_debug.log`

---

## How it works

- **Action Registry pattern** — `core/brain.py` never hardcodes `if/elif` branches for what to do. Every capability is a small class in `actions/`, mapped to one or more trigger words in a single registry.
- **Standardized returns** — every action handler returns `(voice_reply, debug_log)`, so the brain can speak the first and log the second the same way for every feature.
- **Thread-safe GUI** — Qt widgets must live on the main thread, so the assistant's listen/route loop runs on a background daemon thread instead, and a signal bridge (`GUIBridge`) is the *only* channel between the two. Nothing touches a Qt widget from the wrong thread.

```
core/brain.py (background thread)  --signals-->  core/gui.py (main thread)
        |
        v
  action_registry  -->  actions/*.py  -->  (voice_reply, debug_log)
```

---

## Project structure

```
Wednesday/
├── main.py                     # Entry point
├── config.json                 # User settings (voice mode, wake words)
├── requirements.txt
├── data/
│   └── todo.json               # Task storage (auto-created on first run)
├── models/
│   ├── en_US-lessac-medium.onnx        # Piper voice model
│   └── en_US-lessac-medium.onnx.json   # Piper voice config
├── core/
│   ├── brain.py                 # Central logic router / action dispatcher
│   ├── config.py                # Loads config.json with sane defaults
│   ├── gui.py                   # Animated translucent HUD (PyQt6)
│   ├── logger.py                # Rotating file logger
│   ├── stt.py                   # Speech-to-text
│   └── tts.py                   # Offline neural TTS (Piper)
└── actions/
    ├── windows_manager.py       # OS window automation
    └── todo_list.py             # JSON-backed to-do list
```

---

## Requirements

- Windows 10/11
- Python 3.12+
- A Piper voice model 

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
       "stt_model_path": "models/vosk-model-small-en-us-0.15",
       "wake_words": ["hello wednesday", "hi wednesday", "wednesday"]
   }
   ```

3. **Run it**
   ```
   python main.py
   ```

---

## Configuration reference

| Key | Type | Description |
|---|---|---|
| `use_voice_mode` | bool | `false` = type commands in the terminal. `true` = speak them into your microphone. |
| `wake_words` | list[str] | Phrases that activate the assistant. Prefer multi-word phrases (`"hey wednesday"`) over a bare name to cut down on false triggers from everyday speech. |
| `stt_model_path` | str | Reserved for the upcoming local speech-to-text pipeline — not yet wired up (see Roadmap). |

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

**Voice mode** — say a wake word, wait for the HUD to appear, then speak your command within the listening window.

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

## Roadmap

- **STT overhaul** — replace the current dependency on Google's free web speech recognizer with a fully local pipeline: [openWakeWord](https://github.com/dscripka/openWakeWord) for passive wake-word detection, [Moonshine](https://github.com/usefulsensors/moonshine) (ONNX, CPU-only) as the primary transcription engine, with `faster-whisper` (small.en, int8) as a fallback.
- **Custom wake-word model** — `train.ipynb` trains an openWakeWord model on your own wake-word phrases (designed to run on Google Colab).

---

## Known limitations

- Windows-only — uses `winsound` for audio playback, PowerShell for the show-desktop trick, and `AppOpener`/`PyGetWindow` for window control.
- Voice mode's transcription currently calls Google's free web speech API, so voice mode needs an internet connection even though text mode and the TTS replies themselves are fully offline. This is what the STT overhaul above is meant to fix.

---

## License

MIT
