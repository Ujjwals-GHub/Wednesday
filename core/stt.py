import speech_recognition as sr

class STT:
    def __init__(self):
        """Initializes the microphone for two-phase listening."""
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        
        print("\n[System] Calibrating microphone for background noise...")
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print("[System] Ears initialized successfully (Free Google Cloud STT).")

    def listen_passive(self):
        """
        PHASE 1: THE HUNTER
        Listens silently in the background for short bursts.
        Uses a very short pause threshold so it reacts quickly.
        """
        self.recognizer.pause_threshold = 0.5 
        with self.mic as source:
            try:
                # We only need 3 seconds to capture a wake word
                audio = self.recognizer.listen(source, phrase_time_limit=3)
                return self.recognizer.recognize_google(audio).strip().lower()
            except:
                # Ignore all background noise and errors while hunting
                return ""

    def listen_active(self):
        """
        PHASE 2: THE CATCHER
        Opens a strict 5-second window for the actual command.
        """
        self.recognizer.pause_threshold = 1.5 # Gives you time to breathe while speaking
        with self.mic as source:
            try:
                # timeout=5: Waits up to 5 seconds for you to start speaking
                # phrase_time_limit=5: Cuts off recording after 5 seconds of speaking
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                return self.recognizer.recognize_google(audio).strip().lower()
            except sr.WaitTimeoutError:
                return ""
            except:
                return ""

# ==========================================
# TESTING BLOCK
# ==========================================
if __name__ == "__main__":
    my_ears = STT()
    print("\n[System] Hunting for 'wednesday'...")
    
    while True:
        wake_check = my_ears.listen_passive()
        
        if "wednesday" in wake_check:
            print("\n[System] WAKE WORD DETECTED! --> GUI SHOWS UP <--")
            print("[System] Listening for your command for 5 seconds...")
            
            command = my_ears.listen_active()
            print(f"---> Command captured: '{command}'\n")
            print("[System] Hunting for 'wednesday' again...")
            
            if "stop" in command or "exit" in command:
                break