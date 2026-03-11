# QuickClaude

## What This Is

QuickClaude is a global hotkey tool (`Ctrl+Shift+Space`) that sits in the system tray and provides two modes:

1. **Task mode (default, green):** User types or speaks a task → auto-classified and created in the Notion Task List via API. No Claude Code session needed.
2. **Launch mode (amber):** User prefixes with "do it now" / "launch" / "execute" / "now" → strips the trigger phrase and launches Claude Code with that prompt in a new terminal window.

### Architecture
- Single Python script (`quick_claude.py`) using tkinter for the floating prompt bar
- `keyboard` library for global hotkey registration
- `SpeechRecognition` + `PyAudio` for voice input (optional)
- `requests` for Notion API calls
- `.env` file holds `NOTION_TOKEN` and `NOTION_TASK_DB` (gitignored)
- Runs as a background process, polls for hotkey triggers every 80ms

### Auto-Classification System

When creating Notion tasks, `_classify_task()` analyzes the input text to set:

| Field | How it's detected |
|-------|------------------|
| **Context** | Matches against `PROJECT_NAMES` dict (lowercase keyword → canonical project name) |
| **Category** | `CATEGORY_KEYWORDS` dict — counts keyword matches per category, highest score wins |
| **Priority** | Default 5. "urgent/critical" → 8, "low priority/someday" → 3 |
| **Assignee** | Claude for project work, Nathan for personal categories (Health, Shopping, Admin, Home, School) |
| **Effort** | "build/implement" → Medium, "fix/update" → Small, default Quick |

## Classification Rules (IMPORTANT)

When modifying the classification system or adding projects:

- **Context values MUST match the Notion Projects DB canonical names exactly.** See the parent `ClaudeCodeProjects/CLAUDE.md` and `tools/Notion/CLAUDE.md` for the full mapping.
- **Some projects are NOT in the Notion Projects DB** but should still be classifiable. These include: `AIP`, `SiegeRL`, `AllIn`, `PCValueAnalyzer`, `QuickClaude`, `SessionMonitor`, `Heartbeat`, `PrintForge`. When adding these as Context, Notion auto-creates the select option.
- **The `Category ` field has a trailing space** in Notion — always use `"Category "` (with space) in API calls.
- **Add new project aliases to `PROJECT_NAMES`** whenever a new project is created or when voice recognition produces alternative spellings.
- **Category detection is score-based** — if "deploy server" matches both Dev (deploy) and Ops (deploy, server), Ops wins because it has more keyword hits. Keep this behavior.
- **Default category** is `Dev` for project-context tasks, and the highest-scoring match for non-project tasks.

## Development Notes

- `.env` is gitignored — contains the Notion integration token
- Voice input auto-starts when the prompt opens and can be toggled via mic indicator
- The mic keyword ("razer") auto-selects the preferred microphone device
- Git Bash path is hardcoded to `C:\Programs\Git\bin\bash.exe` (non-standard location)
- The launch mode uses PowerShell → Git Bash → `claude --dangerously-skip-permissions`

## Dependencies

`keyboard`, `SpeechRecognition`, `PyAudio`, `requests`, `python-dotenv` — all in `requirements.txt`.
