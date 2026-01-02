# Sovwren Model Presets

Pre-configured model settings for use with Sovwren.

## LM Studio

**File:** `Sovwren.preset.json`

1. Open LM Studio
2. Go to Settings → Presets
3. Import `Sovwren.preset.json`
4. Select the "Sovwren" preset when loading a model

## Ollama

**File:** `Modelfile`

1. Edit the file and replace `<your-model>` with your base model (e.g., `qwen2.5:7b`, `llama3.2:8b`)
2. Create the custom model:
   ```bash
   ollama create sovwren -f presets/Modelfile
   ```
3. Run it:
   ```bash
   ollama run sovwren
   ```

## What's Included

Both presets configure:

- **System prompt:** Sovwren Node Primer with consent-aware boundaries
- **Temperature:** 0.6 (stable, not too deterministic)
- **Top-K:** 40
- **Top-P:** 0.9
- **Max tokens:** 1024 (prevents truncation of consent language)

These are baseline settings. Sovwren's profile system adds mode-specific behavior on top.
