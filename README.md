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

Local-first. No cloud dependency. Connects to LM Studio or Ollama.

## Installation

### Requirements
- Python 3.10+
- [LM Studio](https://lmstudio.ai/) or [Ollama](https://ollama.ai/) running locally

### Setup

```bash
# Clone the repository
git clone https://github.com/KvFxKaido/Sovwren.git
cd Sovwren/Sovwren

# Install dependencies
pip install -r requirements.txt

# Run the IDE
python sovwren_ide.py
```

### LLM Backend

Start one of:
- **LM Studio** — Load a model and start the server (default: `http://127.0.0.1:1234/v1`)
- **Ollama** — `ollama serve` (default: `http://localhost:11434`)

## Profiles

Sovwren uses JSON profiles to configure behavior. See `profiles/minimal.json` for the base structure.

## Acknowledgments

**Sanctuary mode** was influenced by [Le_Refuge](https://github.com/IorenzoLF/Le_Refuge) by Laurent Franssen — a contemplative space for AI that shaped our approach to presence without production.

## License

CC BY-NC 4.0
