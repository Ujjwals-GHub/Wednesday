import threading
import time
import re
from core.tts import TTS
from core.gui import AssistantGUI
from core.logger import get_logger
from actions.windows_manager import WindowsManager
from actions.todo_list import TodoList
from core.stt import STT

class AssistantBrain:
    def __init__(self, config):
        self.config = config
        self.use_voice = self.config.get("use_voice_mode", False)
        
        mode_text = "Voice Mode" if self.use_voice else "Text Mode"
        print(f"\n[System] Booting up Wednesday AI ({mode_text})...")
        
        self.gui = AssistantGUI()
        self.windows_manager = WindowsManager()
        self.logger = get_logger()
        self.todo_list = TodoList()
        
        if self.use_voice:
            self.stt = STT(config=self.config)
        
        self.action_registry = {
            ("open", "launch", "start"): self.windows_manager.handle_open,
            ("close", "shut down app", "kill"): self.windows_manager.handle_close,
            ("minimize", "hide"): self.windows_manager.handle_minimize,
            ("maximize", "full screen"): self.windows_manager.handle_maximize,
            ("bring", "focus"): self.windows_manager.handle_bring_to_top,
            ("desktop", "show desktop", "go to desktop"): self.windows_manager.handle_go_to_desktop,
            ("add", "remember to", "new task"): self.todo_list.handle_add,
            ("read", "whats on my", "what is on my", "tell me my", "whats task", "ls"): self.todo_list.handle_read,
            ("clear", "delete", "remove", "erase"): self.todo_list.handle_clear
        }
        
        self._compiled_actions = [
            (re.compile(r'\b' + re.escape(trigger) + r'\b'), trigger, handler)
            for triggers, handler in self.action_registry.items()
            for trigger in triggers
        ]

        self.logger.info(f"System booted successfully in {mode_text}.")

    def run(self):
        """
        Starts the primary event loop and initializes background daemon processes.
        """
        worker = threading.Thread(target=self.run_logic, daemon=True)
        worker.start()
        self.gui.run()

    def run_logic(self):
        """
        Background loop handling STT processing, intent resolution, and action dispatch.
        """
        self.tts = TTS()
        input_type = "speech" if self.use_voice else "text input"
        self.tts.speak(f"Wednesday is online and waiting for {input_type}.")
        
        wake_words = sorted(self.config.get("wake_words", ["wednesday"]), key=len, reverse=True)
        
        while True:
            clean_command = ""
            
            if self.use_voice:
                wake_detected = self.stt.listen_passive()
                
                if wake_detected == "HARDWARE_ERROR":
                    self.gui.show()
                    self.gui.set_label("HARDWARE SYNC")
                    self.tts.speak("Microphone connection changed. Refreshing audio hardware.")
                    self.stt.reboot_audio()
                    self.gui.hide()
                    continue
                
                if not wake_detected:
                    time.sleep(2)
                    continue
                    
                self.gui.show()
                self.gui.set_label("Listening")
                
                clean_command = self.stt.listen_active()
                if not clean_command:
                    self.gui.hide()
                    continue
            else:
                command = input("\n[Terminal] Type your command: ").strip().lower()
                if not command: 
                    continue
                
                command = command.replace(",", " ").replace(".", " ")
                
                matched_wake = next((w for w in wake_words if command.startswith(w)), None)
                
                if matched_wake:
                    self.gui.show()
                    clean_command = command[len(matched_wake):].strip()
                    
                    if not clean_command:
                        clean_command = input("\n[Terminal] What would you like me to do? ").strip().lower()
                        if not clean_command:
                            self.gui.hide()
                            continue
                else:
                    print("[System] Ignored: Wake word not detected.")
                    continue

            self.logger.info(f"Command parsed: '{clean_command}'")

            best_handler = None
            best_pattern = None
            earliest_pos = float('inf')
            
            for pattern, trigger_word, handler_function in self._compiled_actions:
                match = pattern.search(clean_command)
                if match and match.start() < earliest_pos:
                    earliest_pos = match.start()
                    best_handler = handler_function
                    best_pattern = pattern

            action_handled = False
            if best_handler:
                payload = best_pattern.sub('', clean_command, count=1).strip()
                voice_reply, debug_log = best_handler(payload)
                
                self.tts.speak(voice_reply)
                
                if any(err in debug_log.lower() for err in ["error", "failed", "no matching", "couldn't"]):
                    self.logger.error(debug_log)
                else:
                    self.logger.info(debug_log)
                    
                action_handled = True
                    
            if not action_handled and any(term in clean_command for term in ["stop", "shut down", "shutdown"]):
                self.tts.speak("Going offline. Goodbye.")
                self.logger.info("System shutdown triggered by user.")
                self.gui.close()
                break
                
            elif not action_handled:
                self.tts.speak("I don't know how to do that yet.")
                self.logger.warning(f"Unhandled command: '{clean_command}'")
            
            self.gui.hide()
