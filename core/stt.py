import os
import numpy as np
import pyaudio
import re

from openwakeword.model import Model as OWWModel
from faster_whisper import WhisperModel

from core.logger import get_logger
from core.config import load_config


class STT:
    SAMPLE_RATE = 16000
    FRAME_SIZE = 1280
    FORMAT = pyaudio.paInt16
    CHANNELS = 1

    # Active-listening (command capture) tuning -- capture-behavior internals
    # rather than "which model" choices, so these stay as code constants for
    # now. Move them into config.json too if you'd rather tune them there.
    MAX_COMMAND_SECONDS = 6
    SILENCE_TIMEOUT_SECONDS = 1.2
    SILENCE_RMS_THRESHOLD = 300

    def __init__(self, config=None):
        self.logger = get_logger()
        cfg = config or load_config()

        self.wakeword_model_path = cfg["wake_word_model_path"]
        self.wakeword_threshold = cfg["wake_word_threshold"]

        print("[System] Loading wake-word model (openWakeWord)...")
        if not os.path.exists(self.wakeword_model_path):
            raise FileNotFoundError(
                f"Wake-word model not found at '{self.wakeword_model_path}'. "
                "Place your trained wednesday.onnx there, or fix "
                "'wake_word_model_path' in config.json."
            )
        self.oww_model = OWWModel(
            wakeword_models=[self.wakeword_model_path],
            inference_framework="onnx",
        )
        # openWakeWord keys its prediction dict by the model filename (no extension)
        self.wakeword_key = os.path.splitext(os.path.basename(self.wakeword_model_path))[0]
        print(f"[System] Wake-word model loaded: '{self.wakeword_key}' (threshold={self.wakeword_threshold})")

        print("[System] Loading command transcription model (faster-whisper)...")
        print("[System] (first run downloads the model once -- needs internet just this one time)")
        self.whisper_model = WhisperModel(
            cfg["whisper_model_size"],
            device="cpu",
            compute_type=cfg["whisper_compute_type"],
        )
        print("[System] faster-whisper loaded successfully.")

        self._audio = pyaudio.PyAudio()
        self.logger.info("STT initialized: openWakeWord + faster-whisper (CPU).")

    def _open_stream(self):
        return self._audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.SAMPLE_RATE,
            input=True,
            frames_per_buffer=self.FRAME_SIZE,
        )

    @staticmethod
    def _rms(frame_bytes):
        audio_int16 = np.frombuffer(frame_bytes, dtype=np.int16)
        if audio_int16.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio_int16.astype(np.float64) ** 2)))

    def listen_passive(self):
        stream = self._open_stream()
        try:
            while True:
                frame = stream.read(self.FRAME_SIZE, exception_on_overflow=False)
                audio_chunk = np.frombuffer(frame, dtype=np.int16)

                prediction = self.oww_model.predict(audio_chunk)
                score = prediction.get(self.wakeword_key, 0.0)

                if score >= self.wakeword_threshold:
                    self.logger.info(f"Wake word detected (score={score:.3f}).")
                    self.oww_model.reset()
                    return True
        except Exception as e:
            self.logger.error(f"Wake-word listening error: {e}")
            print(f"[Error] Wake-word listening error: {e}")
            return False
        finally:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass

    def listen_active(self):
        stream = self._open_stream()
        frames = []
        speech_started = False
        silence_frames = 0
        silence_frame_limit = int(self.SILENCE_TIMEOUT_SECONDS * self.SAMPLE_RATE / self.FRAME_SIZE)
        max_frames = int(self.MAX_COMMAND_SECONDS * self.SAMPLE_RATE / self.FRAME_SIZE)

        try:
            for _ in range(max_frames):
                frame = stream.read(self.FRAME_SIZE, exception_on_overflow=False)
                frames.append(frame)

                level = self._rms(frame)
                if level > self.SILENCE_RMS_THRESHOLD:
                    speech_started = True
                    silence_frames = 0
                elif speech_started:
                    silence_frames += 1
                    if silence_frames >= silence_frame_limit:
                        break
        finally:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass

        if not speech_started:
            return ""

        audio_bytes = b"".join(frames)
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        try:
            segments, _ = self.whisper_model.transcribe(audio_np, language="en", beam_size=1)
            text = " ".join(segment.text for segment in segments).strip().lower()
            text = re.sub(r'[.,!?;:]+', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            self.logger.info(f"Transcribed command: '{text}'")
            return text
        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            return ""

    def close(self):
        self._audio.terminate()


if __name__ == "__main__":
    print("[Test] Booting STT stack (openWakeWord + faster-whisper)...")
    stt = STT()

    print("\n[Test] Hunting for wake word 'wednesday'... (Ctrl+C to quit)\n")
    try:
        while True:
            detected = stt.listen_passive()
            if detected:
                print("[Test] >>> WAKE WORD DETECTED <<<")
                print("[Test] Listening for your command...")
                command = stt.listen_active()
                if command:
                    print(f'[Test] Captured command: "{command}"\n')
                else:
                    print("[Test] (heard nothing usable)\n")
                print("[Test] Hunting for wake word again...\n")
    except KeyboardInterrupt:
        print("\n[Test] Stopped by user.")
    finally:
        stt.close()
