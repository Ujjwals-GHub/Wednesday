import pyaudio
import openwakeword
import numpy as np
from openwakeword.model import Model
openwakeword.utils.download_models()
# 1. Load your custom ONNX model
# The Model class automatically loads the required shared embedding/mel models
model = Model(wakeword_models=["C:\\project\\Models\\wednesday.onnx"], inference_framework="onnx")

# 2. Setup PyAudio stream (openWakeWord requires 16 kHz, mono, 16-bit)
CHUNK = 1280  # 80 ms chunks 
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

audio = pyaudio.PyAudio()
stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                    input=True, frames_per_buffer=CHUNK)

print("Listening for 'Wednesday'... (Press Ctrl+C to stop)")

try:
    while True:
        # Read audio from microphone
        pcm = stream.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(pcm, dtype=np.int16)

        # 3. Feed audio to the model
        prediction = model.predict(audio_data)
        
        # 4. Check the score for your model
        # prediction is a dictionary, e.g., {'wednesday': 0.85}
        score = prediction['wednesday']
        
        # 0.5 is a standard starting threshold
        if score > 0.5:
            print(f"*** WAKE WORD DETECTED! *** (Score: {score:.3f})")
            
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()
