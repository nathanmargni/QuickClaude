# QuickClaude

Global hotkey (`Ctrl+Shift+Space`) for quick task capture to Notion or instant [Claude Code](https://docs.anthropic.com/en/docs/claude-code) launch.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green)

## How it works

Press `Ctrl+Shift+Space` anywhere. A floating prompt bar appears.

- **Default mode (green):** Type anything and press Enter → creates a Notion task with auto-classified category, project context, priority, and assignee.
- **Launch mode (amber):** Start with "do it now", "launch", "execute", or "now" → strips the trigger phrase and launches Claude Code with your prompt in a new terminal.

The mode indicator updates live as you type.

## Auto-classification

Tasks are automatically classified:

| Field | Detection |
|-------|-----------|
| **Context** | Matches project names in text (e.g., "fix HackRadar login" → Context: HackRadar) |
| **Category** | Keyword matching: "bug/fix" → Dev, "pricing/stripe" → Revenue, "deploy/docker" → Ops, etc. |
| **Priority** | Default 5. "urgent/critical" → 8, "low priority/someday" → 3 |
| **Assignee** | Claude for project work, Nathan for personal (health, shopping, admin) |
| **Effort** | "build/implement" → Medium, "fix/update" → Small, default Quick |

## Setup

```bash
git clone https://github.com/nathanmargni/QuickClaude.git
cd QuickClaude
setup.bat
```

Create a `.env` file:
```
NOTION_TOKEN=your_notion_integration_token
NOTION_TASK_DB=your_notion_database_id
```

## Usage

```bash
.venv\Scripts\activate
python quick_claude.py
```

### Examples

| Input | Result |
|-------|--------|
| `fix the login bug in HackRadar` | Creates Notion task: Category=Dev, Context=HackRadar, P5 |
| `urgent deploy WorldFirefighters to prod` | Creates task: Category=Ops, Context=WorldFirefighters, P8 |
| `buy new keyboard` | Creates task: Category=Shopping, Assignee=Nathan, P5 |
| `do it now fix the broken test in SpellDeck` | Launches Claude Code with "fix the broken test in SpellDeck" |
| `launch add dark mode to N1N0Labs` | Launches Claude Code with "add dark mode to N1N0Labs" |

## Voice input

Auto-starts listening when the prompt opens. Click the mic indicator to toggle. Requires `SpeechRecognition` + `PyAudio`.

## Configuration

Edit the top of `quick_claude.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOTKEY` | `ctrl+shift+space` | Global hotkey combo |
| `VOICE_LANG` | `en-US` | Speech recognition language |
| `MIC_KEYWORD` | `razer` | Auto-selects first mic matching this keyword |

## Requirements

- Python 3.10+, Windows
- Claude Code installed (for launch mode)
- Notion integration token (for task mode)

## License

MIT
