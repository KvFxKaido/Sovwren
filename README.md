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
- **Web search** — DuckDuckGo via `/search` command or F5 toggle. User-triggered only; sends query text, nothing else
- **RAG** — load local documents with source visibility. Docs never leave your machine unless you confirm a Council Brief
- **Council Gate** — hybrid local+cloud consultation for heavy reasoning tasks

Local-first. Cloud optional. Connects to LM Studio or Ollama.

## Council Gate

When your local model hits its limits, consult a cloud model without leaving the interface.

```
/council How should I structure this database schema?
```

The local model prepares a **Brief** with your current context, sends it to the cloud model (Council), and contextualizes the response. You see exactly what's happening — no silent escalation.

**Commands:**
- `F6` or cloud toggle - Enable/disable Council Gate
- `/council <query>` - Prepare a redacted Brief + preview (requires confirm)
- `/council-yes` - Send the pending Brief
- `/council-no` - Cancel the pending Brief
- `/confirm-yes` / `/confirm-no` - Confirm/cancel destructive ops (git, session deletes)
- `/seat` - List available cloud models
- `/seat <model>` - Switch Council model (e.g., `/seat deepseek`)

**Backends:**
- **CLI** (default) — Shells out to `gemini` and `codex` CLI tools directly. No cloud calls unless you toggle Council on.
- **Ollama Cloud** — Set `SOVWREN_COUNCIL_PROVIDER=ollama`. Uses Ollama to route to cloud GPUs (`ollama login` to authenticate).
- **OpenRouter** — Set `SOVWREN_COUNCIL_PROVIDER=openrouter` and `OPENROUTER_API_KEY` for access to GPT-4, Claude, etc.

## Installation

### Requirements
- Python 3.10+
- [LM Studio](https://lmstudio.ai/) or [Ollama](https://ollama.ai/) running locally
- A [Nerd Font](https://www.nerdfonts.com/) for glyph rendering (recommended: JetBrainsMono Nerd Font)

### Fonts

Sovwren uses Nerd Font glyphs for icons. Without a Nerd Font, you'll see boxes or question marks.

**Quick setup:**
1. Download a Nerd Font from [nerdfonts.com/font-downloads](https://www.nerdfonts.com/font-downloads)
2. Install it (double-click the `.ttf` files)
3. Set your terminal to use that font

**Fallback mode:** If you can't install fonts, set `USE_NERD_FONTS = False` in `glyphs.py` for ASCII fallbacks.

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

### Presets

Pre-configured model settings are available in `presets/`:

- **LM Studio** — Import `presets/Sovwren.preset.json` in Settings → Presets
- **Ollama** — Edit `presets/Sovwren.Modelfile` with your base model, then:
  ```bash
  ollama create sovwren -f presets/Sovwren.Modelfile
  ```

Presets include the Sovwren Node Primer and tuned generation parameters. See `presets/README.md` for details.

## Workspace

The `workspace/` folder is your local space. Put documents, notes, and project files there. The file explorer defaults to this folder, and contents are gitignored.

## Profiles

Sovwren uses JSON profiles to configure behavior. See `profiles/minimal.json` for the base structure.

## Acknowledgments

**Sanctuary mode** was influenced by [Le_Refuge](https://github.com/IorenzoLF/Le_Refuge) by Laurent Franssen — a contemplative space for AI that shaped our approach to presence without production.

## License

CC BY-NC 4.0
