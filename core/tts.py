import os
import wave
import winsound
from piper import PiperVoice

class TTS:
    def __init__(self):
        """
        Initializes the offline neural text-to-speech engine (Piper).
        """
        print("[System] Initializing Neural Voice (Piper TTS)...")
        
        self.model_path = "models/en_US-lessac-medium.onnx"
        self.output_file = "data/reply.wav"
        
        # Ensure the data folder exists so we can save the temporary audio file
        os.makedirs("data", exist_ok=True)
        
        self.voice = None
        try:
            # Load the neural network into memory
            self.voice = PiperVoice.load(self.model_path)
            print("[System] Piper TTS initialized successfully.")
        except Exception as e:
            print(f"[Error] Failed to load Piper TTS model. Did you download the files? {e}")

    def speak(self, text):
        """
        Synthesizes the text into a WAV file and plays it natively on Windows.
        """
        print(f"\n[Assistant] {text}")
        
        if self.voice is None:
            print("[Error] TTS voice model not loaded — skipping speech.")
            return
        
        try:
            # 1. Open the temporary WAV file
            with wave.open(self.output_file, 'wb') as wav_file:
                
                # --- THE BULLETPROOF BUG FIX ---
                # Manually configure the wave file format so Python never panics
                wav_file.setnchannels(1)                               # Mono audio
                wav_file.setsampwidth(2)                               # 16-bit audio
                wav_file.setframerate(self.voice.config.sample_rate)   # Piper model's native sample rate
                
                # Use the official synthesize_wav method to safely write the audio
                self.voice.synthesize_wav(text, wav_file)
            
            # 2. Play the audio file natively
            winsound.PlaySound(self.output_file, winsound.SND_FILENAME)
            
        except Exception as e:
            print(f"[Error] Piper TTS failed to speak: {e}")