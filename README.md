<p align="center">
  <img src="Media/Sovwren_Logo_2.jpg" alt="Sovwren" width="500">
</p>

# Sovwren

A terminal-based IDE for working with local LLMs. Surfaces what chat interfaces hide.

## Why

Most AI interfaces obscure critical state:
- what the model can see
- what it remembers
- when context is saturated
- when behavior changes due to mode or constraint

Sovwren makes these states explicit.

## Features

- **Context load tracking** — see when you're approaching limits, get warnings before degradation
- **Mode switching** — Workshop (building), Sanctuary (reflection), Idle (presence without output)
- **Session bookmarks** — preserve what matters across resets
- **Shared file tree** — see what the model sees
- **Web search** — DuckDuckGo integration, no API key required
- **RAG** — load local documents with source visibility
- **Council Gate** — hybrid local+cloud consultation for heavy reasoning tasks

Local-first. Cloud optional. Connects to LM Studio or Ollama.

## Council Gate

When your local model hits its limits, consult a cloud model without leaving the interface.

```
/council How should I structure this database schema?
```

The local model (NeMo) prepares a **Brief** with your current context, sends it to the cloud model (Council), and contextualizes the response. You see exactly what's happening — no silent escalation.

**Commands:**
- `F6` or ☁️ toggle - Enable/disable Council Gate
- `/council <query>` - Prepare a redacted Brief + preview (requires confirm)
- `/council-yes` - Send the pending Brief
- `/council-no` - Cancel the pending Brief
- `/confirm-yes` / `/confirm-no` - Confirm/cancel destructive ops (git, session deletes)
- `/seat` - List available cloud models
- `/seat <model>` - Switch Council model (e.g., `/seat deepseek`)

**Backends:**
- **Ollama Cloud** (default) — Uses your local Ollama to route to cloud GPUs. Run `ollama login` to authenticate.
- **OpenRouter** — Set `SOVWREN_COUNCIL_PROVIDER=openrouter` and `OPENROUTER_API_KEY` for access to GPT-4, Claude, etc.

## Installation

### Requirements
- Python 3.10+
- [LM Studio](https://lmstudio.ai/) or [Ollama](https://ollama.ai/) running locally

### Setup

```bash
# Clone and run
git clone https://github.com/KvFxKaido/Sovwren.git
cd Sovwren
pip install -r requirements.txt
python sovwren_ide.py
```

Windows shortcut: pin `run-sovwren.bat` (not a `.lnk` inside the repo) to Start/Taskbar via Explorer.

### LLM Backend

Start one of:
- **LM Studio** — Load a model and start the server (default: `http://127.0.0.1:1234/v1`)
- **Ollama** — `ollama serve` (default: `http://localhost:11434`)

## Workspace

The `workspace/` folder is your local space. Put documents, notes, and project files there. The file explorer defaults to this folder, and contents are gitignored.

## Profiles

Sovwren uses JSON profiles to configure behavior. See `profiles/minimal.json` for the base structure.

## Acknowledgments

**Sanctuary mode** was influenced by [Le_Refuge](https://github.com/IorenzoLF/Le_Refuge) by Laurent Franssen — a contemplative space for AI that shaped our approach to presence without production.

## License

CC BY-NC 4.0
