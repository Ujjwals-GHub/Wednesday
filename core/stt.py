import os
import re
import numpy as np
import pyaudio

from openwakeword.model import Model as OWWModel
from faster_whisper import WhisperModel

from core.logger import get_logger
from core.config import load_config


class STT:
    """
    Handles local Speech-to-Text operations using openWakeWord for passive 
    wake word detection and faster-whisper for active command transcription.
    """
    SAMPLE_RATE = 16000
    FRAME_SIZE = 1280
    FORMAT = pyaudio.paInt16
    CHANNELS = 1

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
            raise FileNotFoundError(f"Wake-word model not found at '{self.wakeword_model_path}'.")
            
        self.oww_model = OWWModel(
            wakeword_models=[self.wakeword_model_path],
            inference_framework="onnx",
        )
        self.wakeword_key = os.path.splitext(os.path.basename(self.wakeword_model_path))[0]
        print(f"[System] Wake-word model loaded: '{self.wakeword_key}' (threshold={self.wakeword_threshold})")

        print("[System] Loading command transcription model (faster-whisper)...")
        self.whisper_model = WhisperModel(
            cfg["whisper_model_size"],
            device="cpu",
            compute_type=cfg["whisper_compute_type"],
        )
        print("[System] faster-whisper loaded successfully.")

        self._audio = pyaudio.PyAudio()
        self.logger.info("STT initialized: openWakeWord + faster-whisper (CPU).")

    def _open_stream(self):
        """Opens and returns a PyAudio input stream."""
        return self._audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.SAMPLE_RATE,
            input=True,
            frames_per_buffer=self.FRAME_SIZE,
        )

    def reboot_audio(self):
        """Terminates and reinitializes the PyAudio hardware interface."""
        self.logger.warning("Rebooting PyAudio hardware scan...")
        self._audio.terminate()
        self._audio = pyaudio.PyAudio()

    @staticmethod
    def _rms(frame_bytes):
        """Calculates the Root Mean Square (RMS) of an audio frame."""
        audio_int16 = np.frombuffer(frame_bytes, dtype=np.int16)
        if audio_int16.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio_int16.astype(np.float64) ** 2)))

    def listen_passive(self):
        """
        Continuously processes audio stream until the target wake word is detected.
        Returns "HARDWARE_ERROR" if the audio device is abruptly disconnected or reassigned.
        """
        stream = None
        try:
            stream = self._open_stream()
            while True:
                frame = stream.read(self.FRAME_SIZE, exception_on_overflow=False)
                audio_chunk = np.frombuffer(frame, dtype=np.int16)

                prediction = self.oww_model.predict(audio_chunk)
                score = prediction.get(self.wakeword_key, 0.0)

                if score >= self.wakeword_threshold:
                    self.logger.info(f"Wake word detected (score={score:.3f}).")
                    self.oww_model.reset()
                    return True
                    
        except OSError as e:
            self.logger.error(f"Hardware audio error: {e}")
            return "HARDWARE_ERROR"
        except Exception as e:
            self.logger.error(f"Wake-word listening error: {e}")
            return False
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass

    def listen_active(self):
        """
        Captures audio until silence is detected or the maximum duration is reached.
        """
        stream = None
        frames = []
        speech_started = False
        silence_frames = 0
        silence_frame_limit = int(self.SILENCE_TIMEOUT_SECONDS * self.SAMPLE_RATE / self.FRAME_SIZE)
        max_frames = int(self.MAX_COMMAND_SECONDS * self.SAMPLE_RATE / self.FRAME_SIZE)

        try:
            stream = self._open_stream()
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
        except Exception as e:
            self.logger.error(f"Active listening error: {e}")
            return ""
        finally:
            if stream is not None:
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
        """Terminates the PyAudio instance."""
        self._audio.terminate()
