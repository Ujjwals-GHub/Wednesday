import threading
import re
from core.tts import TTS
from core.gui import AssistantGUI
from core.logger import get_logger
from actions.windows_manager import WindowsManager
from actions.todo_list import TodoList
from core.stt import STT

class AssistantBrain:
    def __init__(self, use_voice_mode=False):
        self.use_voice = use_voice_mode
        
        mode_text = "Voice Mode" if self.use_voice else "Text Mode"
        print(f"\n[System] Booting up Wednesday AI ({mode_text})...")
        
        self.gui = AssistantGUI()
        self.windows_manager = WindowsManager()
        self.logger = get_logger()
        self.todo_list = TodoList()
        
        if self.use_voice:
            self.stt = STT()
        
        self.action_registry = {
            ("open", "launch", "start"): self.windows_manager.handle_open,
            ("close", "shut down app", "kill"): self.windows_manager.handle_close,
            ("minimize", "hide"): self.windows_manager.handle_minimize,
            ("maximize", "full screen"): self.windows_manager.handle_maximize,
            ("bring", "focus"): self.windows_manager.handle_bring_to_top,
            ("desktop", "show desktop", "go to desktop"): self.windows_manager.handle_go_to_desktop,
            
            ("add", "remember to", "new task"): self.todo_list.handle_add,
            ("read", "whats on my", "what is on my", "tell me my", "whats task"): self.todo_list.handle_read,
            ("clear", "delete", "remove", "erase"): self.todo_list.handle_clear
        }
        
        # Precompile trigger regex once, instead of rebuilding it on every
        # command in the run loop. Order matches self.action_registry so the
        # existing "earliest match wins" tie-break behavior is unchanged.
        self._compiled_actions = [
            (re.compile(r'\b' + re.escape(trigger) + r'\b'), trigger, handler)
            for triggers, handler in self.action_registry.items()
            for trigger in triggers
        ]

        self.logger.info(f"System booted successfully in {mode_text}.")

    def run(self):
        """
        Entry point called by main.py. Starts the AI logic loop on a background
        daemon thread, then hands the main thread to the Qt event loop
        (Qt widgets must live on the main thread).
        """
        worker = threading.Thread(target=self.run_logic, daemon=True)
        worker.start()
        self.gui.run()  # blocks main thread until gui.close() is triggered

    def run_logic(self):
        self.tts = TTS()
        input_type = "speech" if self.use_voice else "text input"
        self.tts.speak(f"Wednesday is online and waiting for {input_type}.")
        
        wake_words = ["hello wednesday", "hi wednesday", "wednesday"]
        
        while True:
            clean_command = ""
            
            if self.use_voice:
                # PHASE 1: Silently hunt for the wake word
                wake_check = self.stt.listen_passive()
                
                # If no wake word is found, restart the loop and keep hunting silently
                if not any(wake in wake_check for wake in wake_words):
                    continue
                    
                # PHASE 2: Wake Word Detected! Show GUI and listen for 5 seconds
                self.gui.show()
                # self.tts.speak("Yes?") # Optional: Uncomment if you want her to say "Yes?" before listening
                clean_command = self.stt.listen_active()
                
                if not clean_command:
                    self.gui.hide()
                    continue
            else:
                # TEXT MODE LOGIC (Unaffected)
                command = input("\n[Terminal] Type your command: ").strip().lower()
                if not command: continue
                
                command = command.replace(",", " ").replace(".", " ")
                
                if any(wake in command for wake in wake_words):
                    self.gui.show()
                    clean_command = command
                    
                    for wake in wake_words:
                        clean_command = clean_command.replace(wake, "").strip()
                    
                    if not clean_command:
                        clean_command = input("\n[Terminal] What would you like me to do? ").strip().lower()
                        if not clean_command:
                            self.gui.hide()
                            continue
                else:
                    print("[System] Ignored: Wake word not detected. Try starting with 'Wednesday'.")
                    continue

            # --- ROUTE THE COMMAND ---
            self.logger.info(f"Command parsed: '{clean_command}'")

            best_handler = None
            best_trigger = None
            best_pattern = None
            earliest_pos = float('inf')
            
            for pattern, trigger_word, handler_function in self._compiled_actions:
                match = pattern.search(clean_command)
                if match and match.start() < earliest_pos:
                    earliest_pos = match.start()
                    best_trigger = trigger_word
                    best_handler = handler_function
                    best_pattern = pattern

            action_handled = False
            if best_handler:
                payload = best_pattern.sub('', clean_command, count=1).strip()
                voice_reply, debug_log = best_handler(payload)
                
                self.tts.speak(voice_reply)
                
                if "error" in debug_log.lower() or "failed" in debug_log.lower():
                    self.logger.error(debug_log)
                else:
                    self.logger.info(debug_log)
                    
                action_handled = True
                    
            if not action_handled and ("stop" in clean_command or "shut down" in clean_command):
                self.tts.speak("Going offline. Goodbye.")
                self.logger.info("System shutdown triggered by user.")
                self.gui.close()
                break
                
            elif not action_handled:
                self.tts.speak("I don't know how to do that yet.")
                self.logger.warning(f"Unhandled command: '{clean_command}'")
            
            self.gui.hide()