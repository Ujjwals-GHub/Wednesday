import os
import wave
import winsound
from piper import PiperVoice
from core.logger import get_logger

class TTS:
    """
    Handles offline neural text-to-speech synthesis using Piper.
    """
    def __init__(self):
        self.logger = get_logger()
        print("[System] Initializing Neural Voice (Piper TTS)...")
        
        self.model_path = "models/en_US-lessac-medium.onnx"
        self.output_file = "data/reply.wav"
        
        os.makedirs("data", exist_ok=True)
        
        self.voice = None
        try:
            self.voice = PiperVoice.load(self.model_path)
            print("[System] Piper TTS initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load Piper TTS model: {e}")
            print(f"[Error] Failed to load Piper TTS model. Did you download the files? {e}")

    def speak(self, text):
        """
        Synthesizes text into a WAV file and plays it synchronously via winsound.
        """
        print(f"\n[Assistant] {text}")
        
        if self.voice is None:
            self.logger.warning("TTS voice model not loaded; skipping speech synthesis.")
            return
        
        try:
            with wave.open(self.output_file, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.voice.config.sample_rate)
                
                self.voice.synthesize_wav(text, wav_file)
            
            winsound.PlaySound(self.output_file, winsound.SND_FILENAME)
            
        except Exception as e:
            self.logger.error(f"Piper TTS synthesis/playback failed: {e}")
