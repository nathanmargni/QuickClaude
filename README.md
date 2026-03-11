# QuickClaude

Global hotkey launcher for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Press `Ctrl+Shift+Space` anywhere to open a floating prompt bar, type or speak your request, and launch a new Claude Code session instantly.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Global hotkey** (`Ctrl+Shift+Space`) — works from any application
- **Voice input** — auto-starts listening when the prompt opens, appends transcribed speech to the text field
- **Auto mic selection** — finds your preferred microphone by keyword match
- **Minimal UI** — slim floating bar inspired by Spotlight/Raycast, disappears after launch
- **Instant launch** — opens a new terminal window with `claude --dangerously-skip-permissions` and your prompt

## Setup

```bash
# Clone
git clone https://github.com/nathanmargni/QuickClaude.git
cd QuickClaude

# Run setup (creates venv + installs deps)
setup.bat
```

Or manually:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
# Activate venv and run
.venv\Scripts\activate
python quick_claude.py
```

Press `Ctrl+Shift+Space` to open the prompt bar. Type or dictate your request and press `Enter`.

### Configuration

Edit the top of `quick_claude.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOTKEY` | `ctrl+shift+space` | Global hotkey combo |
| `VOICE_LANG` | `en-US` | Speech recognition language (`it-IT` for Italian) |
| `MIC_KEYWORD` | `razer` | Auto-selects first mic matching this keyword |

## Requirements

- **Python 3.10+**
- **Windows** (uses `ctypes`, `powershell`, Git Bash)
- **Claude Code** installed and on PATH
- Voice input requires `SpeechRecognition` + `PyAudio` (optional — falls back to text-only)

## License

MIT
