"""QuickClaude - Global hotkey launcher for Claude Code with voice + text input."""

import ctypes
import os
import subprocess
import sys
import threading
import tkinter as tk

# DPI awareness (must be before any tkinter)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import keyboard

# Voice support (optional)
try:
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

# --- Config ---
HOTKEY = "ctrl+shift+space"
VOICE_LANG = "en-US"  # Change to "it-IT" for Italian
MIC_KEYWORD = "razer"  # Auto-selects first mic matching this (case-insensitive)


def _find_mic_index():
    """Find microphone device index by keyword match."""
    if not VOICE_AVAILABLE:
        return None
    try:
        names = sr.Microphone.list_microphone_names()
        for i, name in enumerate(names):
            if MIC_KEYWORD.lower() in name.lower():
                return i, name
    except Exception:
        pass
    return None

# Colors (GitHub dark theme + purple accent)
BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#e6edf3"
ACCENT = "#7c3aed"
MIC_ACTIVE = "#ef4444"
MIC_INACTIVE = "#6b7280"
HINT = "#484f58"
PLACEHOLDER = "#484f58"


class QuickClaude:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.window = None
        self.entry = None
        self.listening = False
        self.mic_label = None
        self.recognizer = sr.Recognizer() if VOICE_AVAILABLE else None
        self._trigger = threading.Event()
        self._placeholder_active = False
        self._mic_index = None

        # Find preferred microphone
        if VOICE_AVAILABLE:
            result = _find_mic_index()
            if result:
                self._mic_index, mic_name = result
                print(f"Microphone: {mic_name} (index {self._mic_index})")
            else:
                print(f"Warning: No mic matching '{MIC_KEYWORD}' found, using system default")

        # Register global hotkey
        keyboard.add_hotkey(HOTKEY, self._on_hotkey)

        # Poll for trigger from hotkey thread
        self._poll()

        print(f"QuickClaude ready. Press {HOTKEY} to open.")
        print("Press Ctrl+C in this window to quit.")
        if not VOICE_AVAILABLE:
            print("(Voice disabled - install SpeechRecognition + PyAudio for mic support)")
            print("(Tip: Press Win+H in the popup to use Windows built-in dictation)")

        self.root.mainloop()

    def _on_hotkey(self):
        self._trigger.set()

    def _poll(self):
        if self._trigger.is_set():
            self._trigger.clear()
            if self.window and self.window.winfo_exists():
                self._close()
            else:
                self._show_window()
        self.root.after(80, self._poll)

    # --- Window ---

    def _show_window(self):
        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=BORDER)

        # Size and position: center horizontally, upper third vertically
        w, h = 620, 52
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = (screen_w - w) // 2
        y = screen_h // 4
        self.window.geometry(f"{w}x{h}+{x}+{y}")

        # Outer border frame
        outer = tk.Frame(self.window, bg=BORDER, padx=1, pady=1)
        outer.pack(fill="both", expand=True)

        # Inner frame
        inner = tk.Frame(outer, bg=BG)
        inner.pack(fill="both", expand=True)

        # Purple arrow icon
        icon = tk.Label(inner, text="\u25B6", font=("Segoe UI", 11), bg=BG, fg=ACCENT)
        icon.pack(side="left", padx=(10, 4))

        # Text entry
        self.entry = tk.Entry(
            inner,
            font=("Segoe UI", 13),
            bg=BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            border=0,
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=(2, 4), pady=8)

        # Placeholder
        self._set_placeholder()
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<Key>", self._on_key)

        # Mic indicator (if voice available)
        if VOICE_AVAILABLE:
            self.mic_label = tk.Label(
                inner, text="\u25CF", font=("Segoe UI", 11),
                bg=BG, fg=MIC_INACTIVE, cursor="hand2",
            )
            self.mic_label.pack(side="right", padx=(2, 4))
            self.mic_label.bind("<Button-1>", lambda e: self._toggle_listen())

        # Enter hint
        hint = tk.Label(inner, text="Enter \u21B5", font=("Segoe UI", 8), bg=BG, fg=HINT)
        hint.pack(side="right", padx=(2, 10))

        # Key bindings
        self.entry.bind("<Return>", self._launch)
        self.entry.bind("<Escape>", self._close)

        # Focus
        self.window.after(50, self._force_focus)

        # Auto-start voice
        if VOICE_AVAILABLE:
            self._start_listening()

    def _force_focus(self):
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            if self.entry:
                self.entry.focus_force()

    # --- Placeholder ---

    def _set_placeholder(self):
        self.entry.insert(0, "Ask Claude anything...")
        self.entry.config(fg=PLACEHOLDER)
        self._placeholder_active = True

    def _clear_placeholder(self, event=None):
        if self._placeholder_active:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=TEXT)
            self._placeholder_active = False

    def _on_key(self, event):
        if self._placeholder_active and event.keysym not in ("Escape", "Return", "Tab"):
            self._clear_placeholder()

    # --- Voice ---

    def _toggle_listen(self):
        if self.listening:
            self._stop_listening()
        else:
            self._start_listening()

    def _start_listening(self):
        if not VOICE_AVAILABLE or self.listening:
            return
        self.listening = True
        if self.mic_label:
            self.mic_label.config(fg=MIC_ACTIVE)
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _stop_listening(self):
        self.listening = False
        if self.mic_label:
            self.mic_label.config(fg=MIC_INACTIVE)

    def _listen_loop(self):
        try:
            mic = sr.Microphone(device_index=self._mic_index)
            with mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self.recognizer.energy_threshold = max(self.recognizer.energy_threshold, 300)
                print(f"Mic active (threshold: {self.recognizer.energy_threshold:.0f})")
                while self.listening and self.window and self.window.winfo_exists():
                    try:
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=30)
                        text = self.recognizer.recognize_google(audio, language=VOICE_LANG)
                        if text and self.window and self.window.winfo_exists():
                            print(f"Heard: {text}")
                            self.root.after(0, lambda t=text: self._append_text(t))
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError as e:
                        print(f"Speech API error: {e}")
                        break
        except Exception as e:
            print(f"Microphone error: {e}")
        finally:
            self.listening = False
            if self.mic_label:
                self.root.after(0, lambda: self.mic_label.config(fg=MIC_INACTIVE))
            print("Mic stopped")

    def _append_text(self, text):
        if not self.entry:
            return
        if self._placeholder_active:
            self._clear_placeholder()
        current = self.entry.get()
        if current and not current.endswith(" "):
            self.entry.insert(tk.END, " " + text)
        else:
            self.entry.insert(tk.END, text)

    # --- Launch ---

    def _launch(self, event=None):
        if not self.entry:
            return
        if self._placeholder_active:
            return

        prompt = self.entry.get().strip()
        if not prompt:
            return

        self._close()

        # Write a temp bash script that launches claude (same pattern as dispatch)
        import tempfile
        escaped_prompt = prompt.replace("'", "'\\''")
        script_content = f"""#!/bin/bash
export CLAUDE_CODE_GIT_BASH_PATH='C:\\Programs\\Git\\bin\\bash.exe'
unset CLAUDECODE
claude --dangerously-skip-permissions '{escaped_prompt}'
"""
        script_path = os.path.join(tempfile.gettempdir(), "quickclaude_launch.sh")
        with open(script_path, "w", newline="\n") as f:
            f.write(script_content)

        # Launch in a new window via PowerShell → Git Bash
        bash_path = r"C:\Programs\Git\bin\bash.exe"
        ps_cmd = f"""Start-Process '{bash_path}' -ArgumentList '--login','{script_path.replace(chr(92), "/")}'"""
        subprocess.Popen(["powershell", "-Command", ps_cmd])

        print(f"Launched: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")

    def _close(self, event=None):
        self.listening = False
        if self.window and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
        self.entry = None
        self.mic_label = None


if __name__ == "__main__":
    try:
        QuickClaude()
    except KeyboardInterrupt:
        print("\nQuickClaude stopped.")
        sys.exit(0)
