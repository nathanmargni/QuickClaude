"""QuickClaude - Global hotkey for quick task capture (Notion) or instant Claude Code launch."""

import ctypes
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path

# DPI awareness (must be before any tkinter)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import keyboard
import requests
from dotenv import load_dotenv

# Voice support (optional)
try:
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

# Load .env from script directory
load_dotenv(Path(__file__).parent / ".env")

# --- Config ---
HOTKEY = "ctrl+shift+space"
VOICE_LANG = "en-US"
MIC_KEYWORD = "razer"

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_TASK_DB = os.getenv("NOTION_TASK_DB")

# Trigger phrases that switch to "launch Claude Code" mode
DO_IT_NOW_PATTERNS = [
    r"^do it now\b",
    r"^run it now\b",
    r"^now\b",
    r"^launch\b",
    r"^execute\b",
]

# Known project names for Context auto-detection (lowercase → canonical)
PROJECT_NAMES = {
    "spelldeck": "SpellDeck", "spell deck": "SpellDeck",
    "aitrade": "AITrade", "ai trade": "AITrade",
    "3dterrain": "3DTerrain", "3d terrain": "3DTerrain", "terrain": "3DTerrain",
    "mcpcourse": "MCPCourse", "mcp course": "MCPCourse",
    "questy": "Questy",
    "dailypilot": "DailyPilot", "daily pilot": "DailyPilot",
    "hundredlessons": "HundredLessons", "hundred lessons": "HundredLessons",
    "iteachlol": "ITeachLoL", "i teach lol": "ITeachLoL", "lol labs": "ITeachLoL",
    "n1n0": "N1N0LabsWebsite", "n1n0labs": "N1N0LabsWebsite", "n1n0labswebsite": "N1N0LabsWebsite",
    "sledescender": "sledescender", "sled": "sledescender",
    "sellautomations": "SellAutomations", "sell automations": "SellAutomations",
    "contentcreator": "ContentCreator", "content creator": "ContentCreator",
    "worldfirefighters": "WorldFirefighters", "world firefighters": "WorldFirefighters", "firefighters": "WorldFirefighters",
    "hackradar": "HackRadar", "hack radar": "HackRadar",
    "quickclaude": "QuickClaude", "quick claude": "QuickClaude",
    "allin": "AllIn", "all in": "AllIn",
    "heartbeat": "Heartbeat",
    "siegerl": "SiegeRL", "siege rl": "SiegeRL",
    "aip": "AIP",
    "printforge": "PrintForge", "print forge": "PrintForge",
    "pcvalueanalyzer": "PCValueAnalyzer", "pc value": "PCValueAnalyzer",
    "sessionmonitor": "SessionMonitor", "session monitor": "SessionMonitor",
    "notion": "NotionBridge",
}

# Category detection keywords (lowercase keywords → Category value)
CATEGORY_KEYWORDS = {
    "Dev": ["bug", "fix", "broken", "crash", "error", "feature", "add", "build", "implement",
            "refactor", "update", "upgrade", "migrate", "api", "endpoint", "database", "code",
            "test", "deploy", "ship"],
    "Revenue": ["monetize", "pricing", "payment", "stripe", "revenue", "marketing", "sales",
                "landing page", "conversion", "analytics", "seo", "ads"],
    "Research": ["research", "explore", "experiment", "prototype", "evaluate", "compare",
                 "investigate", "try", "poc", "proof of concept"],
    "Ops": ["deploy", "ci/cd", "infra", "server", "hosting", "monitor", "docker", "pipeline",
            "backup", "ssl", "domain", "dns"],
    "Admin": ["paperwork", "tax", "invoice", "bureaucracy", "legal", "insurance", "contract"],
    "Shopping": ["buy", "order", "purchase", "amazon"],
    "Health": ["doctor", "gym", "workout", "dentist", "medical", "health"],
    "Home": ["clean", "repair", "furniture", "move", "apartment", "house"],
    "Learning": ["learn", "course", "tutorial", "study", "read", "book"],
    "School": ["school", "exam", "homework", "supsi", "patente", "assignment"],
}

# Priority keywords
PRIORITY_KEYWORDS = {
    8: ["urgent", "asap", "critical", "immediately", "important"],
    3: ["low priority", "someday", "maybe", "when possible", "nice to have"],
}


def _find_mic_index():
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


def _classify_task(text):
    """Classify text into Notion task fields."""
    lower = text.lower()

    # Detect Context (project)
    context = None
    for keyword, project in PROJECT_NAMES.items():
        if keyword in lower:
            context = project
            break

    # Detect Category
    category = "Dev" if context else None
    best_score = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > best_score:
            best_score = score
            category = cat

    # If no category matched and no project context, default to general
    if not category:
        category = "Dev"

    # Detect Priority
    priority = 5
    for prio, keywords in PRIORITY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            priority = prio
            break

    # Detect Assignee — default Claude for dev, Nathan for personal
    if context:
        assignee = "Claude"
    elif category in ("Admin", "Shopping", "Health", "Home", "School"):
        assignee = "Nathan"
    else:
        assignee = "Claude"

    # Effort guess
    effort = "Quick (< 30min)"
    if any(w in lower for w in ["build", "implement", "create", "migrate", "redesign"]):
        effort = "Medium (< 1 day)"
    elif any(w in lower for w in ["add", "fix", "update", "refactor"]):
        effort = "Small (< 2h)"

    return {
        "context": context,
        "category": category,
        "priority": priority,
        "assignee": assignee,
        "effort": effort,
    }


def _create_notion_task(name, classification):
    """Create a task in Notion Task List via API."""
    if not NOTION_TOKEN or not NOTION_TASK_DB:
        print("ERROR: NOTION_TOKEN or NOTION_TASK_DB not set in .env")
        return False

    properties = {
        "Name": {"title": [{"text": {"content": name}}]},
        "Status": {"select": {"name": "To Do"}},
        "Category ": {"select": {"name": classification["category"]}},
        "Priorit\u00e0": {"number": classification["priority"]},
        "Assignee": {"select": {"name": classification["assignee"]}},
        "Effort": {"select": {"name": classification["effort"]}},
    }

    if classification["context"]:
        properties["Context"] = {"select": {"name": classification["context"]}}

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        json={"parent": {"database_id": NOTION_TASK_DB}, "properties": properties},
        timeout=10,
    )

    if resp.status_code == 200:
        ctx = classification["context"] or "general"
        print(f"Task created: [{classification['category']}] {name} (P{classification['priority']}, {ctx})")
        return True
    else:
        print(f"Notion API error {resp.status_code}: {resp.text[:200]}")
        return False


# Colors (GitHub dark theme + purple accent)
BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#e6edf3"
ACCENT = "#7c3aed"
TASK_COLOR = "#22c55e"  # Green for task mode
LAUNCH_COLOR = "#f59e0b"  # Amber for launch mode
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
        self.icon_label = None
        self.mode_label = None
        self.recognizer = sr.Recognizer() if VOICE_AVAILABLE else None
        self._trigger = threading.Event()
        self._placeholder_active = False
        self._mic_index = None

        if VOICE_AVAILABLE:
            result = _find_mic_index()
            if result:
                self._mic_index, mic_name = result
                print(f"Microphone: {mic_name} (index {self._mic_index})")
            else:
                print(f"Warning: No mic matching '{MIC_KEYWORD}' found, using system default")

        keyboard.add_hotkey(HOTKEY, self._on_hotkey)
        self._poll()

        print(f"QuickClaude ready. Press {HOTKEY} to open.")
        print("Default: create Notion task. Say 'do it now' to launch Claude Code.")
        if not VOICE_AVAILABLE:
            print("(Voice disabled - install SpeechRecognition + PyAudio for mic support)")

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

        w, h = 660, 52
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = (screen_w - w) // 2
        y = screen_h // 4
        self.window.geometry(f"{w}x{h}+{x}+{y}")

        outer = tk.Frame(self.window, bg=BORDER, padx=1, pady=1)
        outer.pack(fill="both", expand=True)

        inner = tk.Frame(outer, bg=BG)
        inner.pack(fill="both", expand=True)

        # Mode icon (changes color based on mode)
        self.icon_label = tk.Label(inner, text="\u25B6", font=("Segoe UI", 11), bg=BG, fg=TASK_COLOR)
        self.icon_label.pack(side="left", padx=(10, 4))

        # Text entry
        self.entry = tk.Entry(
            inner, font=("Segoe UI", 13), bg=BG, fg=TEXT,
            insertbackground=TEXT, relief="flat", border=0,
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=(2, 4), pady=8)

        self._set_placeholder()
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<Key>", self._on_key)
        self.entry.bind("<KeyRelease>", self._update_mode_indicator)

        if VOICE_AVAILABLE:
            self.mic_label = tk.Label(
                inner, text="\u25CF", font=("Segoe UI", 11),
                bg=BG, fg=MIC_INACTIVE, cursor="hand2",
            )
            self.mic_label.pack(side="right", padx=(2, 4))
            self.mic_label.bind("<Button-1>", lambda e: self._toggle_listen())

        # Mode label (shows current mode)
        self.mode_label = tk.Label(inner, text="task", font=("Segoe UI", 8), bg=BG, fg=TASK_COLOR)
        self.mode_label.pack(side="right", padx=(2, 10))

        self.entry.bind("<Return>", self._on_submit)
        self.entry.bind("<Escape>", self._close)

        self.window.after(50, self._force_focus)

        if VOICE_AVAILABLE:
            self._start_listening()

    def _force_focus(self):
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            if self.entry:
                self.entry.focus_force()

    # --- Mode detection ---

    def _is_launch_mode(self, text):
        lower = text.strip().lower()
        return any(re.match(p, lower) for p in DO_IT_NOW_PATTERNS)

    def _strip_trigger(self, text):
        for pattern in DO_IT_NOW_PATTERNS:
            text = re.sub(pattern, "", text.strip(), flags=re.IGNORECASE).strip()
        return text

    def _update_mode_indicator(self, event=None):
        if not self.entry or not self.mode_label or not self.icon_label:
            return
        text = self.entry.get() if not self._placeholder_active else ""
        if self._is_launch_mode(text):
            self.mode_label.config(text="run", fg=LAUNCH_COLOR)
            self.icon_label.config(fg=LAUNCH_COLOR)
        else:
            self.mode_label.config(text="task", fg=TASK_COLOR)
            self.icon_label.config(fg=TASK_COLOR)

    # --- Placeholder ---

    def _set_placeholder(self):
        self.entry.insert(0, "Task... or 'do it now' to run Claude")
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
        self._update_mode_indicator()

    # --- Submit ---

    def _on_submit(self, event=None):
        if not self.entry or self._placeholder_active:
            return
        text = self.entry.get().strip()
        if not text:
            return

        if self._is_launch_mode(text):
            prompt = self._strip_trigger(text)
            if prompt:
                self._close()
                self._launch_claude(prompt)
            return

        # Default: create Notion task
        self._close()
        threading.Thread(target=self._create_task, args=(text,), daemon=True).start()

    def _create_task(self, text):
        classification = _classify_task(text)
        success = _create_notion_task(text, classification)
        if not success:
            print(f"FALLBACK — task not saved: {text}")

    def _launch_claude(self, prompt):
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
        self.icon_label = None
        self.mode_label = None


if __name__ == "__main__":
    try:
        QuickClaude()
    except KeyboardInterrupt:
        print("\nQuickClaude stopped.")
        sys.exit(0)
