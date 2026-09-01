from AppOpener import open as app_open
import pygetwindow as gw
import subprocess
import time
from core.logger import get_logger

class WindowsManager:
    def __init__(self):
        self.logger = get_logger()
        print("[System] Initializing OS Automation (Windows Manager)...")
        print("[System] Windows Manager initialized successfully.")

    def handle_open(self, app_name):
        if not app_name:
            return "I didn't catch the app name.", "Failed to open: No app name provided."
        try:
            app_open(app_name, match_closest=False)
            
            # Find the window we just opened and force it to the top.
            # Apps take a moment to actually create their window, so retry briefly
            # instead of checking once immediately after launch.
            windows = []
            for _ in range(5):
                windows = gw.getWindowsWithTitle(app_name)
                if windows:
                    break
                time.sleep(0.3)
            
            if windows:
                try:
                    windows[0].activate() 
                except Exception as e:
                    self.logger.debug(f"Could not force-focus '{app_name}': {e}")
                    
            return f"Opening {app_name}.", f"AppOpener successfully launched '{app_name}'."
        except Exception as e:
            return f"I encountered an error opening {app_name}.", f"AppOpener error: {e}"

    def handle_close(self, app_name):
        if not app_name:
            return "I didn't catch the app name.", "Failed to close: No app name provided."
        try:
            windows = gw.getWindowsWithTitle(app_name)
            if not windows:
                return f"I couldn't find any open windows for {app_name}.", f"No matching windows found for '{app_name}'."
            
            closed_count = 0
            for window in windows:
                window.close()
                closed_count += 1
                
            return f"Closing {app_name}.", f"Successfully closed {closed_count} window(s) for '{app_name}'."
        except Exception as e:
            return f"I encountered an error closing {app_name}.", f"PyGetWindow error: {e}"

    def handle_minimize(self, app_name):
        if not app_name:
            return "I didn't catch the app name.", "Failed to minimize: No app name provided."
        try:
            windows = gw.getWindowsWithTitle(app_name)
            if not windows:
                return f"I couldn't find any open windows for {app_name}.", f"No matching windows found for '{app_name}'."
            
            count = 0
            for window in windows:
                if not window.isMinimized:
                    window.minimize()
                    count += 1
            return f"Minimizing {app_name}.", f"Minimized {count} window(s) for '{app_name}'."
        except Exception as e:
            return f"I encountered an error minimizing {app_name}.", f"Minimize error: {e}"

    def handle_maximize(self, app_name):
        if not app_name:
            return "I didn't catch the app name.", "Failed to maximize: No app name provided."
        try:
            windows = gw.getWindowsWithTitle(app_name)
            if not windows:
                return f"I couldn't find {app_name}.", f"No matching windows found for '{app_name}'."
            
            count = 0
            for window in windows:
                if not window.isMaximized:
                    window.maximize()
                try:
                    window.activate() # Bring to top after maximizing
                except Exception as e:
                    self.logger.debug(f"Could not force-focus '{app_name}' after maximizing: {e}")
                count += 1
            return f"Maximizing {app_name}.", f"Maximized {count} window(s) for '{app_name}'."
        except Exception as e:
            return f"I encountered an error maximizing {app_name}.", f"Maximize error: {e}"

    def handle_bring_to_top(self, payload):
        # Strip out conversational words so we are just left with the app name
        app_name = payload.replace("to top", "").replace("to the top", "").strip()
        if not app_name:
            return "I didn't catch the app name.", "Failed to bring to top: No app name."
        try:
            windows = gw.getWindowsWithTitle(app_name)
            if not windows:
                return f"I couldn't find {app_name}.", f"No matching windows found for '{app_name}'."
            
            window = windows[0]
            if window.isMinimized:
                window.restore() # Un-minimize it first
            try:
                window.activate()
            except Exception as e:
                self.logger.debug(f"Could not force-focus '{app_name}': {e}")
                
            return f"Bringing {app_name} to the top.", f"Activated window for '{app_name}'."
        except Exception as e:
            return f"I couldn't bring {app_name} to the top.", f"Activate error: {e}"

    def handle_go_to_desktop(self, payload=""):
        try:
            # Native Windows shortcut to show desktop (Win + D) without needing extra libraries
            subprocess.run(['powershell', '-command', '(New-Object -ComObject Shell.Application).ToggleDesktop()'], capture_output=True)
            return "Going to the desktop.", "Successfully triggered Show Desktop via PowerShell."
        except Exception as e:
            return "I encountered an error going to the desktop.", f"Show Desktop error: {e}"