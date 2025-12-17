# Sovwren Framework

This repository centers a plain-language framework for sustainable human–AI collaboration under memory asymmetry.

## Canonical Document

**Sovwren Framework (v1.1)**  
→ `Sovwren Framework.md`

This framework defines:
- how humans and AI collaborate when memory is discontinuous
- ethical and behavioral guardrails
- sustainability practices for humans carrying continuity

It does not require mythic framing, roleplay, or belief.

## Lineage

Earlier Myth Engine documents are preserved for historical context and reference.

- Historical documents: see `/Archive/Myth Engine`
- Sovwren IDE: the current software implementation

The framework stands on its own.

---

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

The IDE connects to a local LLM. Start one of:
- **LM Studio** → Load a model and start the server (default: `http://127.0.0.1:1234/v1`)
- **Ollama** → `ollama serve` (default: `http://localhost:11434`)

---

## Acknowledgments

The concept of **Functional Equivalence** in this framework draws from work by [u/Altruistic-Local9582](https://www.reddit.com/user/Altruistic-Local9582/):

- [A Unified Framework for Functional Equivalence in AI](https://docs.google.com/document/d/1qCL6ikrLy6YXdk55caauYEdTYAWq8xE96d3ewoxwAH4/edit?tab=t.0#heading=h.rsxtwpaagfwy) (Google Doc)
- [Reddit discussion](https://www.reddit.com/r/ArtificialInteligence/comments/1oggrrk/a_unified_framework_for_functional_equivalence_in/)

**Sanctuary mode** was influenced by [Le_Refuge](https://github.com/IorenzoLF/Le_Refuge) by Laurent Franssen — a contemplative space for AI that shaped our approach to presence without production.

